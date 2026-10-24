"""Original merchant query4 -> scoped current readonly buyback listing.

Exact published context, optional one NPC-owned module candidate. Wallet,
Inventory, NPC plan and caller-transaction listing are public test seams.
"""
import argparse
from contextlib import closing
from dataclasses import replace
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import struct
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
RELEASE=ROOT/'runtime/deployments/npc-repair-20261024T023920Z'


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    global ROOT,RELEASE
    parser=argparse.ArgumentParser();parser.add_argument('--npc-module',type=Path)
    parser.add_argument('--workspace-root',type=Path,default=ROOT)
    parser.add_argument('--label',required=True);args=parser.parse_args()
    ROOT=args.workspace_root.resolve();RELEASE=ROOT/'runtime/deployments/npc-repair-20261024T023920Z'
    assert args.label.replace('_','').isalnum()
    output=ROOT/'evidence/npc-buyback-query-verification'/args.label
    assert not output.exists(),'Use new output labels';output.mkdir(parents=True)
    published=json.loads((RELEASE/'manifest.json').read_text(encoding='utf8'))
    harness=json.loads((RELEASE/'candidate.json').read_text(encoding='utf8'))
    source,helpers=RELEASE/'source',RELEASE/'harness'
    override=args.npc_module.resolve() if args.npc_module else None
    inputs={}
    for directory,entries in ((source,published['sha256']),(helpers,harness['harness_sha256']),
            (helpers,harness['harness_resource_sha256']),(helpers/'workspace',harness['workspace_sha256'])):
        inputs.update({str(directory/name):digest for name,digest in entries.items()})
    if override:inputs[str(override)]=sha(override)
    def verify():
        for name,digest in inputs.items():assert sha(Path(name))==digest,name
    verify();sys.path[:0]=[str(helpers),str(source)]
    import inspect_client
    inspect_client.ROOT,inspect_client.OUT=ROOT.parent,helpers/'workspace'
    if override:
        spec=importlib.util.spec_from_file_location('npc_shop_sales',override)
        module=importlib.util.module_from_spec(spec);sys.modules['npc_shop_sales']=module;spec.loader.exec_module(module)
    from accounts import AccountStore
    from inventory import Inventory,AssetChange
    from currency import read_wallet,WalletNotInitialized
    from runtime_core import StaleEpoch
    from world_owner import MapAddress,Location
    from world_npcs import NpcScene
    from native_gameplay_probe import probe
    from native_inspect import u32
    from wire import compact,read_compact
    import runtime_storage
    import npc_shop_sales as sales
    checked=[];passed=False;failure=None
    try:
        with tempfile.TemporaryDirectory(prefix='npc-query-readonly-') as directory:
            store=AccountStore(Path(directory)/'disposable.sqlite3');prepared=runtime_storage.prepare(store)
            role=store.create_role(1111,'回购只读查询',11,1010109);rid=role['id'];epoch=store.acquire_lease(1111,rid)
            inv=Inventory(store.leased(1111,rid,epoch),1111,rid)
            runtime_storage.initialize_role_wallet(store,1111,rid,epoch,(1000,0,0,0),'explicit_migration')
            def scope(npc_id,request,inventory=inv):
                npc=next(p for entries in store.npc_resources[0].values() for p in entries if p.npc_id==npc_id)
                address=MapAddress(npc.map_id,npc.map_id,0)
                location=Location(inventory.role_id,inventory.epoch,address,1,npc.x,npc.y)
                scene=NpcScene(address,(npc,),prepared[3],interaction_radius=32,binding_capacity=1)
                key=(npc.map_id<<32)|npc.placement_id;scene.bind(key,npc.placement_id)
                now=int(time.monotonic()*1000)
                proof=scene.interact(struct.pack('>q',key),location,location,
                    request_id=request,deadline_ms=now+30000,now_ms=now)
                return key,proof,location,now
            def command(npc_id,request,*,body=None,inventory=inv):
                key,proof,location,now=scope(npc_id,request,inventory)
                return sales.plan_query(store.npc_gameplay,body if body is not None else struct.pack('>iQ',4,key),
                    proof,location,request_id=request,now_ms=now,deadline_ms=now+30000)
            def sale_command(npc_id,request,kind,keys):
                key,proof,location,now=scope(npc_id,request)
                body=struct.pack('>q',key)+(compact(len(keys))+struct.pack('>'+'i'*len(keys),*keys)
                    if kind==sales.SELL_ITEMS else struct.pack('>i',keys[0]))
                return sales.plan(store.npc_gameplay,kind,body,proof,location,
                    request_id=request,now_ms=now,deadline_ms=now+30000)
            def state():
                with closing(inv.accounts.connect()) as db:
                    db.execute('BEGIN')
                    return inv.immutable_snapshot_transaction(db),read_wallet(db,1111,rid,epoch,store.currency_rules)
            def readonly(query,inventory=inv,rules=None):
                with closing(store.connect()) as db:
                    db.execute('BEGIN')
                    db.set_authorizer(lambda action,*args:sqlite3.SQLITE_DENY if action in
                        (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE,
                         sqlite3.SQLITE_CREATE_TABLE,sqlite3.SQLITE_ALTER_TABLE,sqlite3.SQLITE_DROP_TABLE) else sqlite3.SQLITE_OK)
                    return sales.query_listing(db,inventory,query,rules=rules or store.npc_sale_rules,
                        currency_rules=store.currency_rules)
            def listing(messages):
                assert type(messages) is tuple and len(messages)==1 and messages[0][0]==sales.REPURCHASE_ITEMS
                body=messages[0][1];count,offset=read_compact(body,12);items=[]
                for index in range(count):
                    pos=offset+48*index;template,flags,key,slot=struct.unpack_from('>4i',body,pos)
                    quantity=struct.unpack_from('>i',body,pos+24)[0]
                    items.append((template,key,slot,quantity,flags))
                offset+=48*count;prices,offset=read_compact(body,offset)
                assert prices==count and len(body)==offset+8*prices
                values=dict(struct.unpack_from('>ii',body,offset+8*i) for i in range(prices))
                assert probe(0xef64e0,u32(0x2284258),u32(0x228425c),payload=body)[0]==body
                return struct.unpack_from('>Qi',body),tuple(items),values
            before=state();query=command(10004,'query-empty-weapon-shop')
            assert query.service.service_id==2 and query.service.handler=='shop.open'
            messages=readonly(query)
            expected=(sales.REPURCHASE_ITEMS,struct.pack('>QiBB',1000,20,0,0))
            assert messages==(expected,),'Query4 must clear the real empty buyback container, not fabricate stock'
            assert probe(0xef64e0,u32(0x2284258),u32(0x228425c),payload=messages[0][1])[0]==messages[0][1]
            assert state()==before
            assert sales.query(store,inv,query)==messages and state()==before
            checked.append('actual ordinary shop service2 query4 returns native empty real cache under SQL write denial')
            with closing(inv.accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                inv.apply_settlement(db,AssetChange('query-real-sale-grants',grants=((40200,1,1),(40204,1,0),(32000,2,0))))
            original=inv.immutable_snapshot();keys=tuple(item.id for item in original.items)
            sale=sale_command(10011,'query-real-original-sale',sales.SELL_ITEMS,keys)
            sold=sales.settle(store,inv,sale)
            before=state();query=command(10011,'query-real-market-cache')
            current=readonly(query);decoded=listing(current)
            assert current==(next(row for row in sold if row[0]==sales.REPURCHASE_ITEMS),)
            by_template={item.template_id:item for item in original.items}
            assert decoded[0]==(8000,20) and len(decoded[1])==3
            assert decoded[2]=={by_template[40200].id:250,by_template[40204].id:7000,by_template[32000].id:150}
            assert [(row[0],row[1],row[3]) for row in decoded[1]]==[(item.template_id,item.id,item.quantity) for item in original.items]
            assert sales.query(store,inv,query)==current and state()==before
            checked.append('real public sale creates three preserved instances; readonly query returns actual keys/quantities/current cash and exact original codec')
            # System-boundary source faults ONLY: derive from a real sale row,
            # alter it in an uncommitted disposable transaction, deny request
            # writes, require rejection, then rollback the injected fault.
            def rejected_source(value=None,*,field=None,price=None):
                with closing(store.connect()) as db:
                    db.execute('BEGIN IMMEDIATE')
                    raw=db.execute('SELECT record FROM npc_buyback_items WHERE item_key=?',(keys[0],)).fetchone()[0]
                    if field is not None:
                        changed=json.loads(raw);changed[field]=value;raw=json.dumps(changed)
                    elif value is not None:raw=value
                    db.execute('UPDATE npc_buyback_items SET record=?,cash_price=COALESCE(?,cash_price) WHERE item_key=?',
                        (raw,price,keys[0]))
                    db.set_authorizer(lambda action,*args:sqlite3.SQLITE_DENY if action in
                        (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE) else sqlite3.SQLITE_OK)
                    try:sales.query_listing(db,inv,query,rules=store.npc_sale_rules,currency_rules=store.currency_rules)
                    except ValueError:pass
                    else:raise AssertionError('Malformed persisted buyback source was encoded')
                    db.rollback()
                assert readonly(query)==current and state()==before
            rejected_source('[]')
            checked.append('non-object persisted cache record is rejected without repair or request writes')
            for field,value in (('template_id',[]),('id',keys[0]+1000),('role_id',rid+1000),
                    ('quantity',0),('quantity',2),('binding',2)):
                rejected_source(value,field=field)
            rejected_source('{invalid-json')
            rejected_source(price=2**31)
            checked.append('malformed JSON/template/key/owner/quantity/binding/native price source faults are refused under SQL write denial')
            try:readonly(query,rules=replace(store.npc_sale_rules,capacity=2))
            except ValueError as error:assert str(error)=='Unsupported current NPC buyback cache'
            else:raise AssertionError('Selected query budget silently truncated cached instances')
            assert readonly(query)==current and state()==before
            checked.append('selected result capacity is bounded without silently truncating cached instances')
            for _ in range(2):assert readonly(query)==current and state()==before
            weapon=command(10004,'query-other-shop-empty')
            assert listing(readonly(weapon))[1:]==((),{}) and state()==before
            checked.append('repeated query does not mutate; another ordinary shop receives empty rather than another NPC cache or local stock')
            try:sale_command(10004,'query-cannot-grant-sale',sales.SELL_ITEMS,keys)
            except ValueError as error:assert str(error)=='NPC service is not authorized'
            else:raise AssertionError('Readonly shop2 query granted service214 sale')
            checked.append('shop2 query grants no service214 sale permission')
            for column,target in ((1,query.service.entity_key),(3,query.service.entity_key),(4,0),(4,rid),(4,2**63)):
                try:command(10011,'query-malformed-'+str(column)+'-'+str(target),body=struct.pack('>iQ',column,target))
                except ValueError:pass
                else:raise AssertionError('Own/wrong namespace or target accepted')
            for body in (b'',struct.pack('>iQ',4,query.service.entity_key)+b'\0'):
                try:command(10011,'query-malformed-length-'+str(len(body)),body=body)
                except ValueError:pass
                else:raise AssertionError('Truncated/trailing query accepted')
            nonshop=next(p.npc_id for entries in store.npc_resources[0].values() for p in entries
                if (p.npc_id,2) not in store.npc_gameplay.services.bindings)
            try:command(nonshop,'query-nonshop-binding')
            except ValueError as error:assert str(error)=='NPC service is not authorized'
            else:raise AssertionError('NPC without a service2 binding authorized query4')
            key,proof,location,now=scope(10011,'query-stale-current')
            for changed in (replace(location,version=2),replace(location,address=replace(location.address,instance_id=location.address.instance_id+1))):
                try:sales.plan_query(store.npc_gameplay,struct.pack('>iQ',4,key),proof,changed,
                    request_id='query-stale-current',now_ms=now,deadline_ms=now+30000)
                except ValueError:pass
                else:raise AssertionError('Stale NPC scope authorized query')
            assert state()==before
            checked.append('exact length/native namespace/full NPC key and current complete map/position/shop permissions are required')
            other=store.create_role(1111,'另一回购角色',11,1010109);other_epoch=store.acquire_lease(1111,other['id'])
            other_inv=Inventory(store.leased(1111,other['id'],other_epoch),1111,other['id'])
            runtime_storage.initialize_role_wallet(store,1111,other['id'],other_epoch,(500,0,0,0),'explicit_migration')
            try:readonly(query,other_inv)
            except ValueError as error:assert str(error)=='NPC buyback query owner or shop mismatch'
            else:raise AssertionError('Other role consumed owner query')
            other_query=command(10011,'other-real-query',inventory=other_inv)
            assert listing(readonly(other_query,other_inv))==((500,20),(),{})
            assert state()==before
            checked.append('another role cannot reuse owner intent or read owner cached instances')
            unknown=store.create_role(1111,'回购未知钱包',11,1010109);unknown_epoch=store.acquire_lease(1111,unknown['id'])
            unknown_inv=Inventory(store.leased(1111,unknown['id'],unknown_epoch),1111,unknown['id'])
            unknown_query=command(10011,'query-unknown-wallet',inventory=unknown_inv)
            try:readonly(unknown_query,unknown_inv)
            except WalletNotInitialized:pass
            else:raise AssertionError('Unknown wallet silently projected a balance')
            checked.append('unknown wallet remains unknown and is not initialized or shown as zero')
            expired=replace(query,service=replace(query.service,deadline_ms=int(time.monotonic()*1000)-1))
            try:readonly(expired)
            except ValueError as error:assert str(error)=='NPC buyback query expired'
            else:raise AssertionError('Expired query executed')
            assert state()==before
            # Selected short test retention; no timestamp/cache SQL fabrication.
            time.sleep(1.1)
            assert listing(readonly(query,rules=replace(store.npc_sale_rules,ttl_seconds=1)))[1:]==((),{})
            assert readonly(query)==current and state()==before
            checked.append('expiry is filtered readonly under SQL DML denial; retained valid original-policy rows remain intact')
            bought=sale_command(10011,'query-real-buyback-once',sales.REPURCHASE,(by_template[40200].id,))
            sales.settle(store,inv,bought)
            restored=inv.immutable_snapshot().items
            assert len(restored)==1 and restored[0]==by_template[40200]
            remaining=listing(readonly(command(10011,'query-after-real-buyback')))
            assert remaining[0]==(7750,20) and len(remaining[1])==2 and by_template[40200].id not in remaining[2]
            checked.append('actual existing-policy repurchase restores exact item and subsequent query reads current remaining rows/cash')
            before=state();stale=command(10011,'query-old-role-lease')
            store.acquire_lease(1111,rid)
            try:readonly(stale)
            except ValueError:pass
            else:raise AssertionError('Old role lease read cache')
            try:sales.query(store,inv,stale)
            except StaleEpoch:pass
            else:raise AssertionError('Bounded reader accepted expired storage lease')
            checked.append('old role lease cannot read current cache')
        passed=True
    except Exception as error:
        failure=type(error).__name__+': '+str(error)
        raise
    finally:
        verify();origins={}
        for name,module in tuple(sys.modules.items()):
            if name=='__main__':continue
            file=getattr(module,'__file__',None)
            if file and Path(file).resolve().is_relative_to(ROOT):
                actual=Path(file).resolve()
                assert actual.parent in (source,helpers) or (name=='npc_shop_sales' and actual==override),str(actual)
                origins[name]=str(actual)
        result=dict(passed=passed,failure=failure,checked=checked,probe_sha256=sha(Path(__file__)),
            candidate_sha256=sha(override) if override else None,fixed_inputs=len(inputs),
            actual_project_module_origins=origins,shared_query4_route_changed=False,
            display_debit_policy_changed=False,live_database_or_service_or_GUI_access=False)
        (output/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('PASS NPC readonly buyback query:',len(checked),'public groups')


if __name__=='__main__':main()
