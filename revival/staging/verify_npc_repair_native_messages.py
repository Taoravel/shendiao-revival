"""Real paid legacy receipt -> current native equipment adapter in repair Tx.

Public NPC plan/repair, Inventory and wallet interfaces are the test seams.
The old receipt is produced by the separate published Owner/Peer fixture.
No service, real role, production store, fake receipt or replacement runtime.
"""
import argparse
from contextlib import closing
from dataclasses import asdict,is_dataclass
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
STABLE='npc-column-real-legacy-paid4'


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    global ROOT
    parser=argparse.ArgumentParser()
    parser.add_argument('--workspace-root',type=Path,default=ROOT)
    parser.add_argument('--context',type=Path,required=True)
    parser.add_argument('--database',type=Path,required=True)
    parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--npc-module',type=Path)
    args=parser.parse_args()
    ROOT=args.workspace_root.resolve()
    context=args.context.resolve();db_path=args.database.resolve();output=args.report.resolve()
    assert db_path.name=='disposable.sqlite3' and db_path.is_relative_to(ROOT/'evidence') and db_path.exists()
    assert output.is_relative_to(ROOT/'evidence') and not output.exists()
    manifest=json.loads((context.parent/'manifest.json').read_text(encoding='utf8'))
    override=args.npc_module.resolve() if args.npc_module else None
    override_sha=sha(override) if override else None
    def verify():
        for name,digest in manifest['files'].items():assert sha(context/name)==digest,name
        for name,digest in manifest['inputs'].items():assert sha(Path(name))==digest,name
        if override:assert sha(override)==override_sha
    verify()
    sys.path.insert(0,str(context))
    import inspect_client
    inspect_client.ROOT,inspect_client.OUT=ROOT.parent,context
    if override:
        spec=importlib.util.spec_from_file_location('npc_repairs',override)
        module=importlib.util.module_from_spec(spec);sys.modules['npc_repairs']=module;spec.loader.exec_module(module)
    from accounts import AccountStore
    from inventory import Inventory,AssetChange
    from currency import read_wallet
    from equipment_gems import GemState
    from equipment_gem_score import GemScoreBasis
    from native_gameplay_probe import probe
    from world_owner import MapAddress,Location
    from world_npcs import NpcScene
    import equipment_native_columns as native
    import equipment_gem_storage as sockets
    import equipment_gem_score_storage as scores
    import npc_repairs
    import runtime_storage
    import verify_npc_equipped_repair_runtime as equipped
    store=AccountStore(db_path);prepared=runtime_storage.prepare(store)
    role,=store.roles(1111);rid=role['id'];epoch=store.acquire_lease(1111,rid)
    inv=Inventory(store.leased(1111,rid,epoch),1111,rid)
    with closing(store.connect()) as db,db:sockets.prepare(db);scores.prepare(db)
    rules=native.NativeEquipmentRules.load()
    placement=next(p for ps in store.npc_resources[0].values() for p in ps if p.npc_id==10004)
    address=MapAddress(placement.map_id,placement.map_id,0)
    location=Location(rid,epoch,address,1,placement.x,placement.y)
    scene=NpcScene(address,(placement,),prepared[3],interaction_radius=32,binding_capacity=1)
    npc_key=(placement.map_id<<32)|placement.placement_id;scene.bind(npc_key,placement.placement_id)
    item,=inv.immutable_snapshot().items;key=item.id
    assert item.equipment_slot==0 and item.template_id==49009
    checked=[]
    def intent(request,column=3,item_key=key):
        now=int(time.monotonic()*1000)
        proof=scene.interact(struct.pack('>q',npc_key),location,location,
            request_id=request,deadline_ms=now+10000,now_ms=now)
        return npc_repairs.plan(store.npc_gameplay,struct.pack('>iqii',2,npc_key,column,item_key),proof,location,
            request_id=request,now_ms=now,deadline_ms=now+10000)
    def state():
        with closing(inv.accounts.connect()) as db:
            db.execute('BEGIN')
            return inv.immutable_snapshot_transaction(db),read_wallet(db,1111,rid,epoch,store.currency_rules)
    def cash(snapshot):return next(row.balance for row in snapshot[1] if row.currency=='cash')
    def current(db,inventory,item_key):return native.item_messages(db,inventory,rules,item_key)
    def final(db,inventory,snapshot):return runtime_storage.equipment_projection_messages(db,store,inventory,snapshot)
    def repair(command,**kwargs):
        return npc_repairs.repair(store,inv,command,final,equipment_messages=current,**kwargs)
    def forbidden_draw(bound):raise AssertionError('Paid replay invoked randomness')
    def native_result(messages,column,item_key=key):
        selected=tuple(row for row in messages if row[0] in (0xc03fe,0xc0412,0xc0414))
        assert tuple(kind for kind,_ in selected)==(0xc03fe,0xc0412,0xc0414)
        assert struct.unpack_from('>ii',selected[0][1])==(column,item_key)
        assert struct.unpack_from('>i',selected[1][1])[0]==column
        assert struct.unpack_from('>ii',selected[2][1])==(column,item_key)
        probe(0xd9c110,0xe4e5c0,0xe0a240,payload=selected[0][1])
        probe(0xef9850,0xefa210,0xefa2a0,payload=selected[1][1])
        probe(0xd9dfb0,0xe4e950,0xd9e050,payload=selected[2][1])
        return selected
    def wear(request,loss,item_key=key):
        with closing(inv.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');condition=inv.equipment_condition(db,item_key)
            inv.wear_equipment(db,item_key,request,condition.version,loss)
    before=state()
    for column in (4,3):
        messages=repair(intent(STABLE,column),draw_source=forbidden_draw)
        native_result(messages,3);equipped.attributes(messages);assert state()==before
    checked.append('actual published paid4 on a new lease returns current native3, no mutation/RNG/fee')
    wear('native-provider-later-wear',5)
    damaged=state();old=damaged[0].items[0].condition
    for column in (4,3):
        messages=repair(intent(STABLE,column),draw_source=forbidden_draw)
        selected=native_result(messages,3)
        assert selected[1][1]==struct.pack('>iBii',3,1,key,old.current)
        assert state()==damaged
    checked.append('historical paid output reflects newer damage, not original receipt state')
    fresh=intent('native-provider-fresh')
    messages=repair(fresh,draw_source=lambda bound:0);selected=native_result(messages,3);equipped.attributes(messages)
    saved=state();condition=saved[0].items[0].condition
    assert condition.current==condition.maximum and condition.version==old.version+1
    assert cash(damaged)-cash(saved)==2*(old.maximum-old.current)
    assert selected[1][1]==struct.pack('>iBii',3,1,key,condition.current)
    assert repair(fresh,draw_source=forbidden_draw)==messages and state()==saved
    checked.append('fresh3 repairs/charges once with original codecs and complete final20 role attributes')
    wear('native-provider-later-rollback',3)
    before=state()
    # A real persisted, explicitly incomplete source must fail inside native
    # encoding after repair mutation. No mocked producer or SQL receipt exists.
    with closing(inv.accounts.connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        sockets.initialize(db,inv,rules.gems,key,GemState(0,(),rules.gems.revision),0,'explicit_known_socket_profile')
    before=state();command=intent('native-provider-source-rollback')
    try:repair(command,draw_source=lambda bound:0)
    except ValueError as error:assert str(error)=='Exact current gem and explicit score sources required',str(error)
    else:raise AssertionError('Incomplete gem score source was accepted')
    assert state()==before
    # Complete the missing trusted source publicly, then retry the SAME command.
    # Success proves the failed encoding did not persist a domain/repair receipt.
    current_item=before[0].items[0]
    with closing(inv.accounts.connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        scores.initialize(db,inv,rules.score,rules.gems,
            GemScoreBasis(rid,key,rules.score.revision,current_item.detail.score,'known-NPC-repair-base-score'),
            'explicit_known_pre_gem_score')
    retry_before=state();messages=repair(command,draw_source=lambda bound:0)
    native_result(messages,3);equipped.attributes(messages)
    after=state();assert cash(retry_before)-cash(after)==6
    assert after[0].items[0].condition.current==after[0].items[0].condition.maximum
    checked.append('real native incomplete-source failure rolls back fee/condition/receipts; same-ID retry repairs for6')
    # A malformed trusted adapter is an encoding seam failure, not an invitation
    # to partially commit a valid repair. Keep this separate from the real-source test.
    wear('native-provider-shape-wear',2);before=state();command=intent('native-provider-shape-rollback')
    def invalid(db,inventory,item_key):return list(current(db,inventory,item_key))
    try:npc_repairs.repair(store,inv,command,final,draw_source=lambda bound:0,equipment_messages=invalid)
    except ValueError as error:assert str(error)=='Repair equipment producer must return immutable encoded logical messages'
    else:raise AssertionError('Mutable adapter result was accepted')
    assert state()==before
    messages=repair(command,draw_source=lambda bound:0);native_result(messages,3);assert cash(before)-cash(state())==4
    checked.append('mutable producer result rolls back fee/receipts and same-ID retry charges4 once')
    with closing(inv.accounts.connect()) as db,db:
        db.execute('BEGIN IMMEDIATE');inv.unequip_transaction(db,key,0,epoch,'native-provider-unequip')
    wear('native-provider-carried-wear',1);before=state()
    for column in (4,3):
        messages=repair(intent(STABLE,column),draw_source=forbidden_draw)
        selected=native_result(messages,1)
        assert selected[1][1]==struct.pack('>iBii',1,1,key,before[0].items[0].condition.current)
        assert state()==before
    checked.append('paid4/3 after removal returns current carried1 and preserves subsequent damage/cash')
    for request,column in (('native-provider-new4',4),('native-provider-wrong3',3)):
        try:repair(intent(request,column),draw_source=forbidden_draw)
        except ValueError:pass
        else:raise AssertionError('Fresh wrong location/legacy4 accepted')
        assert state()==before
    checked.append('fresh4/wrong-location3 refused before randomness and asset changes')
    messages=repair(intent('native-provider-carried1',1),draw_source=lambda bound:0)
    native_result(messages,1);assert cash(before)-cash(state())==2
    checked.append('fresh carried1 remains supported and charges2')
    old_intent=intent('native-provider-expired-lease',1);store.acquire_lease(1111,rid)
    try:repair(old_intent,draw_source=forbidden_draw)
    except ValueError:pass
    else:raise AssertionError('Old lease reached repair')
    checked.append('replaced role lease refused before randomness')
    # The same selected adapter also participates in the sole migrated resource
    # contract. Use the published L21 fixture and its real wear transition.
    from verify_resource_owner_runtime import fixture as resource_fixture
    from verify_resource_npc_care_runtime import change_fixture,complete_map
    from role_equipment_storage import current_resource_profile
    from role_resource_storage import read_role_resources
    role=store.create_role(1111,'修理原列单资源',11,1010109);rid=role['id']
    weapon,_=resource_fixture(store,role,placement)
    epoch=store.acquire_lease(1111,rid)
    inv=Inventory(store.leased(1111,rid,epoch),1111,rid,
        resource_rules=store.resource_rules,equipment_attribute_rules=store.equipment_attribute_rules)
    location=Location(rid,epoch,address,1,placement.x,placement.y)
    def resources():
        with closing(inv.accounts.connect()) as db:
            db.execute('BEGIN');snapshot=inv.immutable_snapshot_transaction(db)
            current_resource_profile(db,1111,rid,epoch,snapshot,
                equipment_rules=store.equipment_attribute_rules,resource_rules=store.resource_rules)
            return read_role_resources(db,1111,rid,epoch,store.resource_rules)
    change_fixture(store,inv,'native-provider-migrated-wear',wear=weapon)
    before=state();resource_before=resources()
    command=intent('native-provider-migrated-repair',3,weapon)
    arguments=dict(draw_source=lambda bound:0,resource_rules=store.resource_rules,
        equipment_rules=store.equipment_attribute_rules,equipment_messages=current)
    def late_invalid(db,inventory,snapshot):return list(final(db,inventory,snapshot))
    try:npc_repairs.repair(store,inv,command,late_invalid,**arguments)
    except ValueError as error:assert str(error)=='Repair precommit must return immutable encoded logical messages'
    else:raise AssertionError('Invalid final profile encoded after partial commit')
    assert state()==before and resources()==resource_before
    messages=npc_repairs.repair(store,inv,command,final,**arguments)
    native_result(messages,3,weapon);complete_map(messages)
    after=state();resource_after=resources()
    assert cash(before)-cash(after)==20
    assert (resource_after.hp,resource_after.mp,resource_after.version)==(10,20,resource_before.version)
    assert next(i for i in after[0].items if i.id==weapon).condition.current==100
    checked.append('migrated current source/HP10 MP20/version survive late encode rollback; same-ID repair charges20')
    arguments['draw_source']=forbidden_draw
    messages=npc_repairs.repair(store,inv,command,final,**arguments)
    native_result(messages,3,weapon);complete_map(messages)
    assert state()==after and resources()==resource_after
    checked.append('migrated paid reply reads current source and native3 without resettlement or second debit')
    verify();origins={}
    for name,module in tuple(sys.modules.items()):
        if name=='__main__':continue
        file=getattr(module,'__file__',None)
        if file and Path(file).resolve().is_relative_to(ROOT):
            actual=Path(file).resolve()
            assert actual.is_relative_to(context) or (name=='npc_repairs' and actual==override),str(actual)
            origins[name]=str(actual)
    result=dict(passed=checked,source_manifest_sha256=sha(context.parent/'manifest.json'),
        npc_module_sha256=override_sha or sha(context/'npc_repairs.py'),actual_module_origins=origins,
        actual_legacy_receipt_producer='separate exact published Owner/Peer process',
        actual_shared_provider_injection=False,encrypted_delivery_for_this_provider=False,
        actual_migrated_HPMP_source_combination=True,full_gem_role_projection=False,
        service_or_real_database_or_GUI_access=False)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('PASS real NPC repair/native adapter:',len(checked),'public behavior groups')


if __name__=='__main__':main()
