"""Original NPC proof and real leased inventory; disposable read-only queries."""
import importlib
from contextlib import closing
from dataclasses import replace,FrozenInstanceError
import json
from pathlib import Path
import struct
import tempfile
import time
from unittest.mock import patch
from types import SimpleNamespace
from accounts import AccountStore
from inventory import Inventory
from inspect_client import OUT,write_json
from research_npc_identification import roundtrip
from native_gameplay_probe import probe
from wire import compact
import npc_depot
from world_npcs import NpcScene
from world_owner import MapAddress,Location
from npc_services import NpcServices
import runtime_storage


def consume_original_response(body,states,entity_key):
    """Run the actual decoded response through 10934a0.

    Owned-item lookup/UI opening are explicit offline Adapters, not GUI proof.
    """
    from unicorn import UC_HOOK_CODE
    from unicorn.x86_const import UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP,UC_X86_REG_EAX
    seen=[]
    def observe(uc,obj):
        read=lambda p:struct.unpack('<I',uc.mem_read(p,4))[0]
        write=lambda p,*v:uc.mem_write(p,struct.pack('<'+'I'*len(v),*v))
        wrappers={key:(0x5301000+i*0x1000,0x5301800+i*0x1000)
            for i,key in enumerate(dict(states))}
        for wrapper,bean in wrappers.values():write(wrapper,bean);write(bean+0x58,77)
        write(0x2944628,0x5300000)
        def hook(uc,address,size,user):
            sp=uc.reg_read(UC_X86_REG_ESP)
            if address==0x1091670:
                key,column=read(sp+4),read(sp+8)
                assert column==1 and key in wrappers
                seen.append(key)
                uc.reg_write(UC_X86_REG_EAX,wrappers[key][0])
                uc.reg_write(UC_X86_REG_ESP,sp+12);uc.reg_write(UC_X86_REG_EIP,read(sp))
            elif address==0x10831b0:
                assert [read(sp+i) for i in (4,8,12,16)]==[entity_key&0xffffffff,entity_key>>32,0,10]
                assert {key:read(bean+0x58) for key,(_,bean) in wrappers.items()}==dict(states)
                seen.append('opened');uc.emu_stop()
        uc.hook_add(UC_HOOK_CODE,hook)
        write(0x5100000,0x500f000,0,0)
        uc.reg_write(UC_X86_REG_ESP,0x5100000);uc.reg_write(UC_X86_REG_ECX,obj)
        uc.emu_start(0x10934a0,0x500f000,count=100000)
    probe(0xf04490,0xf04e70,0xf04f10,payload=body,observer=observe)
    assert seen==[key for key,state in states]+['opened']


def main():
    with tempfile.TemporaryDirectory(prefix='npc-identification-query-') as directory:
        store=AccountStore(Path(directory)/'state.sqlite3')
        prepared=runtime_storage.prepare(store)
        try:module=importlib.import_module('npc_identification_query')
        except ModuleNotFoundError:
            raise AssertionError('NPC identification has no current-proof read-only query Module') from None
        resources=store.npc_resources;services=store.npc_gameplay.services
        rules=module.prepare(store)
        assert (rules.revision,rules.npc_id,rules.map_id,rules.placement_id,rules.max_items)==(
            '2026-10-24.npc-identification-query.1',10890,1007,75,128)
        assert rules.detail_rules is store.inventory_config.detail_rules
        assert store.npc_resources is resources and store.npc_gameplay.services is services
        assert (10890,495) not in services.bindings
        def rejected_startup(action):
            try:action()
            except ValueError:return
            raise AssertionError('Unsupported identification startup policy accepted')
        policy=json.loads((OUT/'design/npc-identification-query-v1.json').read_text(encoding='utf-8'))
        invalid=[]
        fields=('revision','npc_id','map_id','placement_id','placement_position','service_id',
                'handler','mode','max_items','request_type','response_type','key_minimum','key_maximum')
        for field in fields:
            candidate=dict(policy);del candidate[field];invalid.append(candidate)
        for field in ('npc_id','map_id','placement_id','service_id','mode','max_items',
                      'request_type','response_type','key_minimum','key_maximum'):
            for value in (True,float(policy[field]),policy[field]+1):
                invalid.append(dict(policy,**{field:value}))
        invalid.extend((dict(policy,placement_position=[3972.0,5299]),dict(policy,revision='future'),
                        dict(policy,handler='equipment.identify'),[],None))
        path=Path(directory)/'query-policy.json'
        for candidate in invalid:
            path.write_text(json.dumps(candidate),encoding='utf-8')
            rejected_startup(lambda:module.load_query_rules(*resources,services,rules.detail_rules,path=path))
        path.write_text(json.dumps(policy),encoding='utf-8')
        frozen=module.load_query_rules(*resources,services,rules.detail_rules,path=path)
        path.write_text('{}',encoding='utf-8');assert frozen==rules
        npc=next(p for p in resources[0][1007] if p.placement_id==75)
        bad_places=({1007:()},
                    {1007:(npc,npc)},{1007:(replace(npc,x=3972.0),)},
                    {1007:(replace(npc,npc_id=10380),)})
        for places in bad_places:
            rejected_startup(lambda:module.load_query_rules(places,resources[1],services,rules.detail_rules))
        for definitions in ({},{10890:{'id':'10380'}}):
            rejected_startup(lambda:module.load_query_rules(resources[0],definitions,services,rules.detail_rules))
        for changed in (None,replace(rules.detail_rules,revision='unknown')):
            rejected_startup(lambda:module.load_query_rules(*resources,services,changed))
        labels=dict(services.labels);labels[495]='unverified'
        rejected_startup(lambda:module.load_query_rules(*resources,NpcServices(labels),rules.detail_rules))
        rejected_startup(lambda:module.prepare(SimpleNamespace(npc_identification_query_rules=rules)))
        try:rules.max_items=129
        except FrozenInstanceError:pass
        else:raise AssertionError('Identification query budget can change after startup')
        role=store.create_role(1111,'鉴定只读',12,1010101)
        epoch=store.acquire_lease(1111,role['id'])
        inventory=Inventory(store.leased(1111,role['id'],epoch),1111,role['id'])
        inventory.grant_item(40200,binding=1)
        identified=inventory.immutable_snapshot().items[0]
        with closing(inventory.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            # Explicit legacy clean fixture, initialized via public migration.
            key=db.execute('INSERT INTO inventory_items(role_id,template_id,quantity,slot,binding) '
                'VALUES(?,?,1,1,0)',(role['id'],40200)).lastrowid
            inventory.initialize_equipment_condition(db,key,100,100,1)
            inventory.initialize_equipment_detail(db,key,replace(rules.detail_rules.generate(40200),identified=0))
        address=MapAddress(1007,1007,0);entity_key=(1007<<32)|75
        scene=NpcScene(address,(npc,),prepared[3],
            binding_capacity=1,interaction_rules=store.npc_interaction_rules)
        scene.bind(entity_key,75)
        now=int(time.monotonic()*1000)
        location=Location(role['id'],epoch,address,1,npc.x,npc.y)
        proof=scene.interact(struct.pack('>q',entity_key),location,location,
            request_id='identification-query',deadline_ms=now+60000,now_ms=now)
        before=inventory.immutable_snapshot()
        body=b'\3'+struct.pack('>3iQi',key,identified.id,key,entity_key,1)
        assert hasattr(module,'plan_query'), 'NPC identification cannot plan an actual local495 status query'
        intent=module.plan_query(body,proof,location,before.inventory_revision,rules=rules,
            now_ms=now,deadline_ms=now+60000)
        assert hasattr(module,'query_states'), 'NPC identification has no leased read-only state transaction'
        messages=module.query_states(inventory,intent)
        expected=struct.pack('>Q',entity_key)+b'\3'+struct.pack('>7i',key,0,identified.id,1,key,0,1)
        assert messages==((0xc04cd,expected),)
        roundtrip(0xf04490,0xf04e70,0xf04f10,expected)
        consume_original_response(messages[0][1],((key,0),(identified.id,1),(key,0)),entity_key)
        assert inventory.immutable_snapshot()==before

        def database():
            with closing(store.connect()) as db:return tuple(db.iterdump())
        def refused(action):
            state=inventory.immutable_snapshot();rows=database()
            try:action()
            except ValueError:pass
            else:raise AssertionError('Stale or unsupported identification query accepted')
            assert inventory.immutable_snapshot()==state and database()==rows
        def planned(keys,*,npc_key=entity_key,mode=1,p=proof,loc=location):
            body=compact(len(keys))+b''.join(struct.pack('>i',k) for k in keys)+struct.pack('>Qi',npc_key,mode)
            return module.plan_query(body,p,loc,inventory.immutable_snapshot().inventory_revision,
                rules=rules,now_ms=now,deadline_ms=now+60000)
        rows=database()
        for keys in ((),(key,)*128):
            answer=module.query_states(inventory,planned(keys))
            assert answer[0][1]==struct.pack('>Q',entity_key)+compact(len(keys))+b''.join(
                struct.pack('>ii',k,0) for k in keys)+struct.pack('>i',1)
            roundtrip(0xf04490,0xf04e70,0xf04f10,answer[0][1])
        assert database()==rows and inventory.immutable_snapshot()==before
        for keys in ((key,)*129,(0,),(-1,)):
            refused(lambda:planned(keys))
        for mode in (0,2):refused(lambda:planned((key,),mode=mode))
        for wrong in (entity_key^1,entity_key^(1<<32)):
            refused(lambda:planned((key,),npc_key=wrong))
        for loc in (replace(location,version=2),replace(location,login_epoch='obsolete'),
                    replace(location,address=MapAddress(1007,1008,0)),
                    replace(location,address=MapAddress(1007,1007,1)),replace(location,state='loading')):
            refused(lambda:planned((key,),loc=loc))
        for p in (replace(proof,npc_id=10380),replace(proof,placement_id=74),
                  replace(proof,kind='client-assertion'),replace(proof,position_version=True)):
            refused(lambda:planned((key,),p=p))
        refused(lambda:module.query_states(inventory,replace(intent,item_keys=(key,)*129)))
        refused(lambda:module.query_states(inventory,replace(intent,inventory_revision=before.inventory_revision+1)))
        refused(lambda:module.query_states(inventory,replace(intent,deadline_ms=now)))
        refused(lambda:module.plan_query(body[:-1],proof,location,before.inventory_revision,
            rules=rules,now_ms=now,deadline_ms=now+60000))
        inventory.grant_item(32000,quantity=2)
        refused(lambda:module.query_states(inventory,intent))
        consumable=next(item for item in inventory.immutable_snapshot().items if item.template_id==32000)
        refused(lambda:module.query_states(inventory,planned((consumable.id,))))
        with closing(inventory.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            unknown=db.execute('INSERT INTO inventory_items(role_id,template_id,quantity,slot,binding) '
                'VALUES(?,?,1,3,0)',(role['id'],40200)).lastrowid
        refused(lambda:module.query_states(inventory,planned((unknown,))))
        inventory.equip(identified.id,0)
        refused(lambda:module.query_states(inventory,planned((identified.id,))))
        inventory.grant_item(40200)
        stored=next(item for item in inventory.immutable_snapshot().items
            if item.template_id==40200 and item.id not in (key,identified.id,unknown))
        with closing(inventory.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');npc_depot.initialize(db,inventory,0,'explicit_migration')
            npc_depot.move(db,inventory,struct.pack('>6iq',1,stored.id,stored.slot,2,0,0,0),40)
        refused(lambda:module.query_states(inventory,planned((stored.id,))))
        foreign=store.create_role(1111,'鉴定他物',11,1010109)
        foreign_epoch=store.acquire_lease(1111,foreign['id'])
        other=Inventory(store.leased(1111,foreign['id'],foreign_epoch),1111,foreign['id'])
        other.grant_item(40200);foreign_key=other.immutable_snapshot().items[0].id
        refused(lambda:module.query_states(inventory,planned((foreign_key,))))
        refused(lambda:module.query_states(other,planned((key,))))

        fresh=planned((key,));rows=database();assets=inventory.immutable_snapshot()
        with patch('builtins.open',side_effect=AssertionError('Query hot-path file read')), \
             patch('io.open',side_effect=AssertionError('Query hot-path file read')):
            assert module.query_states(inventory,fresh)[0][0]==0xc04cd
        with patch('struct.pack',side_effect=MemoryError('controlled serialization allocation failure')):
            try:module.query_states(inventory,fresh)
            except MemoryError:pass
            else:raise AssertionError('Late serialization fault returned a query response')
        with patch('time.monotonic',side_effect=[now/1000,(fresh.deadline_ms+1)/1000]):
            try:module.query_states(inventory,fresh)
            except ValueError:pass
            else:raise AssertionError('Query returned after its deadline')
        assert database()==rows and inventory.immutable_snapshot()==assets
        new_epoch=store.acquire_lease(1111,role['id'])
        current_inventory=Inventory(store.leased(1111,role['id'],new_epoch),1111,role['id'])
        rows=database()
        for target in (inventory,current_inventory):
            try:module.query_states(target,fresh)
            except ValueError:pass
            else:raise AssertionError('Obsolete role lease authorized identification query')
        assert current_inventory.immutable_snapshot()==assets and database()==rows
        result={'passed':['strict startup freezes the approved original NPC and current detail rules without registry mutation',
            'actual local495 query uses fresh map proof and returns known0/1 in original ordered vector',
            'exact role-produced response is consumed by original decoder and state handler',
            'empty and128 duplicate keys preserve order and count;129 and unsupported wire modes reject',
            'full address, role epoch, position version, original NPC and all entity-key bits are fenced',
            'stale asset revision, unknown, quantity, worn, warehouse and foreign keys reject without writes',
            'hot query reads no files; late serialization allocation and deadline faults yield no response or writes',
            'new lease invalidates old intent; no data, source, wallet or receipt mutation',
            'strict startup rejects changed/missing recipes, original sources and unknown detail rules'],
            'invalid_startup_policy_cases':len(invalid),
            'original_consumer_adapters':'owned-item lookup and UI opening only; no GUI',
            'serialization_failure':'controlled stdlib serialization allocation fault',
            'original_npc_query_binding_fixture':True,
            'shared_runtime_integrated':False,'paid_identification_restored':False,
            'live_database_modified':False,'native_gui_verified':False}
        write_json(OUT/'evidence/npc-identification-query-verification.json',result)
        print(result)


if __name__=='__main__':main()
