"""Explicitly migrated inn consumer, actual same-transaction unique carrier.

Temporary database and real map proof; no shared loading/profile activation,
GUI or battle. Both resource/equipment rules are injected after startup reads.
"""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
import struct
import tempfile
import time
from unittest.mock import patch
from accounts import AccountStore
from inventory import Inventory,AssetChange
from item_effects import VitalState
from role_attributes import AttributeBaseline
from role_growth import initialize_growth
from role_attribute_storage import initialize_attribute_baseline,read_attribute_snapshot
from role_equipment import EquipmentAttributeBasis,resource_caps_from_projection
from role_equipment_storage import (initialize_equipment_attribute_basis,current_equipment_totals,
    current_resource_profile)
from role_resource_plan import load_resource_rules,plan_resource_values
from role_resource_storage import (migrate_role_resources,read_role_resources,apply_resource_transition,
    ResourceNotInitialized)
from currency import initialize_wallet,read_wallet,apply_currency,CurrencyChange
from world_owner import MapAddress,Location
from world_npcs import NpcScene
from inspect_client import OUT,write_json
from wire import read_compact
import runtime_storage
import npc_recovery
import role_vigor


def main():
    resource_rules=load_resource_rules()
    with tempfile.TemporaryDirectory() as temp:
        store=AccountStore(Path(temp)/'inn-resources.sqlite3')
        roles={name:store.create_role(1111,name,11,1010109) for name in ('迁移客栈','编码回滚','旧档客栈')}
        with closing(store.connect()) as db,db:db.execute('UPDATE roles SET level=21')
        prepared=runtime_storage.prepare(store);gear_rules=store.equipment_attribute_rules
        npc=next(p for ps in store.npc_resources[0].values() for p in ps if p.npc_id==10157)
        address=MapAddress(npc.map_id,npc.map_id,0);key=(npc.map_id<<32)|npc.placement_id
        scene=NpcScene(address,(npc,),prepared[3],interaction_radius=32,binding_capacity=1)
        scene.bind(key,npc.placement_id)
        def fixture(name,*,seal=11,hit=40,migrated=True):
            role=roles[name];epoch=store.acquire_lease(1111,role['id'])
            inv=Inventory(store.leased(1111,role['id'],epoch),1111,role['id'])
            with closing(inv.accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                growth=initialize_growth(db,1111,inv.role_id,epoch,store.growth_rules,expected_level=21,free_points=0)
                baseline=AttributeBaseline(inv.role_id,21,0,(10,10,10,10,10),(500,1000,20,5,hit,20,10,20,5))
                old=initialize_attribute_baseline(db,1111,inv.role_id,epoch,baseline,growth,store.attribute_rules,
                    VitalState(inv.role_id,0,10,500,20,1000)).vitals
                initialize_wallet(db,1111,inv.role_id,epoch,(2000,0,0,0),'explicit_migration',store.currency_rules)
                if migrated:
                    initialize_equipment_attribute_basis(db,1111,inv.role_id,epoch,
                        EquipmentAttributeBasis(inv.role_id,9,0,gear_rules.revision,seal,'explicit-inn-resource-fixture'),gear_rules)
                    inv.apply_settlement(db,AssetChange('known-inn-weapon',grants=((49009,1,1),)))
                    item=inv.immutable_snapshot_transaction(db).items[0]
                    inv.equip_transaction(db,item.id,0,epoch,'known-inn-equip')
                    totals=current_equipment_totals(db,1111,inv.role_id,epoch,inv.immutable_snapshot_transaction(db),gear_rules)
                    migrate_role_resources(db,1111,inv.role_id,epoch,old,resource_caps_from_projection(totals),
                        origin='explicit_migration',migration_id='known-inn-profile',rules=resource_rules,equipment_rules=gear_rules)
            role_vigor.initialize_profile(store,inv,100,100,'explicit_migration',int(time.monotonic()*1000))
            return inv
        def intent(inv,request):
            now=int(time.monotonic()*1000)
            loc=Location(inv.role_id,inv.epoch,address,1,npc.x,npc.y)
            proof=scene.interact(struct.pack('>q',key),loc,loc,request_id=request,now_ms=now,deadline_ms=now+10000)
            return npc_recovery.plan(store.npc_gameplay,struct.pack('>qi',key,1),proof,loc,
                request_id=request,now_ms=now,deadline_ms=now+10000)
        def state(inv):
            with closing(inv.accounts.connect()) as db:
                db.execute('BEGIN')
                resources=read_role_resources(db,1111,inv.role_id,inv.epoch,resource_rules)
                wallet=read_wallet(db,1111,inv.role_id,inv.epoch,store.currency_rules)
                vigor=role_vigor.read(db,inv,store.vigor_rules)
                counts=tuple(db.execute('SELECT COUNT(*) FROM '+table+' WHERE role_id=?',(inv.role_id,)).fetchone()[0]
                    for table in ('role_resource_receipts','role_wallet_receipts','npc_recovery_receipts','npc_command_receipts'))
                return resources,wallet,vigor,counts
        def settle(inv,cmd):
            return npc_recovery.settle(store,inv,cmd,resource_rules=resource_rules,equipment_rules=gear_rules)
        def damage(inv,request,hp=50,mp=60):
            # Trusted disposable resource fixture, no actual battle or legacy
            # vital writer. Use the canonical value transition in the same DB.
            with closing(inv.accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                current=read_role_resources(db,1111,inv.role_id,inv.epoch,resource_rules)
                totals=current_equipment_totals(db,1111,inv.role_id,inv.epoch,
                    inv.immutable_snapshot_transaction(db),gear_rules)
                transition=plan_resource_values(current,hp,mp,'medicine',resource_rules,
                    current_caps=resource_caps_from_projection(totals))
                return apply_resource_transition(db,1111,inv.role_id,inv.epoch,transition,request,
                    rules=resource_rules,equipment_rules=gear_rules).resources
        def values(messages):
            maps=[]
            for kind,body in messages:
                if kind==0xc32c8:
                    count,pos=read_compact(body)
                    result=dict(struct.unpack_from('>if',body,pos+i*8) for i in range(count))
                    if 60 in result:maps.append(result)
            assert len(maps)==1
            return maps[0]
        def refused(action):
            try:action()
            except ValueError:return
            raise AssertionError('Unsafe inn request accepted')
        inv=fixture('迁移客栈');cmd=intent(inv,'inn-once');before=state(inv)
        result=values(settle(inv,cmd));after=state(inv)
        assert len(result)==20 and (result[60],result[70],result[140],result[150],result[1230])==(500,1000,500,1000,19)
        assert (after[0].hp,after[0].mp,after[0].version)==(500,1000,before[0].version+1)
        assert after[1][0].balance==1500 and after[2].value==85 and after[3]==(1,1,1,1)
        damage(inv,'later-resources')
        wounded=state(inv)
        replay=values(settle(inv,cmd))
        assert (replay[60],replay[70])==(50,60) and state(inv)==wounded
        with closing(inv.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            inv.apply_settlement(db,AssetChange('later-carried-asset',grants=((32000,1,1),)))
        # A real carried-item revision may be folded into this real resource
        # write, only while final caps stay the same. Reads alone never fold it.
        result=values(settle(inv,intent(inv,'inn-second')))
        assert (result[60],result[70])==(500,1000)
        assert state(inv)[1][0].balance==1000 and state(inv)[2].value==70
        full=state(inv)
        refused(lambda:settle(inv,intent(inv,'full-no-effect')))
        assert state(inv)==full
        damage(inv,'later-again',70,30)
        safe=state(inv)
        refused(lambda:npc_recovery.settle(store,inv,intent(inv,'missing-injection')))
        refused(lambda:npc_recovery.settle(store,inv,intent(inv,'half-injection'),resource_rules=resource_rules))
        refused(lambda:npc_recovery.settle(store,inv,intent(inv,'bad-policy'),
            resource_rules=replace(resource_rules,revision='unknown-resource-policy'),equipment_rules=gear_rules))
        assert state(inv)==safe
        def funding(delta,request):
            with closing(inv.accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                apply_currency(db,1111,inv.role_id,inv.epoch,
                    CurrencyChange(request,'npc_shop','explicit-disposable-funding-fixture',(('cash',delta),)),store.currency_rules)
        funding(-1000,'fixture-deplete')
        unpaid=intent(inv,'insufficient-later-retry');empty=state(inv)
        refused(lambda:settle(inv,unpaid))
        assert state(inv)==empty
        funding(1000,'fixture-restore-funds')
        with patch('builtins.open',side_effect=AssertionError('Inn hot path file read')), \
             patch('io.open',side_effect=AssertionError('Inn hot path file read')):
            assert values(settle(inv,unpaid))[60]==500
        assert state(inv)[1][0].balance==500 and state(inv)[2].value==55
        damage(inv,'before-new-lease',70,30)
        epoch=store.acquire_lease(1111,inv.role_id)
        new=Inventory(store.leased(1111,inv.role_id,epoch),1111,inv.role_id)
        role_vigor.login(store,new,int(time.monotonic()*1000))
        new_before=state(new)
        refused(lambda:settle(inv,cmd))
        assert state(new)==new_before
        current=values(settle(new,intent(new,'inn-once')))
        assert (current[60],current[70])==(70,30) and state(new)==new_before
        assert values(settle(new,intent(new,'new-owner-fresh')))[60]==500
        assert state(new)[1][0].balance==0 and state(new)[2].value==40
        damage(new,'controlled-zero-hp',0,30)
        dead=state(new)
        refused(lambda:settle(new,intent(new,'no-role-revival')))
        assert values(settle(new,intent(new,'inn-once')))[60]==0 and state(new)==dead

        bad=fixture('编码回滚',hit=16777217)
        bad_before=state(bad)
        try:settle(bad,intent(bad,'real-float-encoding-refusal'))
        except ValueError as error:assert 'float' in str(error).lower(),str(error)
        else:raise AssertionError('Unencodable final hit16777217 committed paid rest')
        assert state(bad)==bad_before
        legacy=fixture('旧档客栈',migrated=False)
        old=values(settle(legacy,intent(legacy,'legacy-with-injected-rules')))
        assert len(old)==2 and (old[60],old[70])==(500,1000)
        with closing(legacy.accounts.connect()) as db:
            db.execute('BEGIN')
            assert read_attribute_snapshot(db,1111,legacy.role_id,legacy.epoch).vitals.hp==500
            try:read_role_resources(db,1111,legacy.role_id,legacy.epoch,resource_rules)
            except ResourceNotInitialized:pass
            else:raise AssertionError('Inn silently activated a legacy resource profile')
        report={'passed':['explicit migrated inn consumes current final profile and writes sole resource carrier',
            'cash2000->1500, vigor100->85 and resource version advance commit with NPC receipts',
            'one complete20entry final map500/1000 and sealing19',
            'accepted retry preserves later HP50/MP60 and all current balances/versions',
            'fresh paid rest folds current carried revision into same-cap resource transition',
            'no-op/missing or partial injection/unknown policy reject without state change',
            'insufficient cash rolls vigor/resources/receipts back; same request succeeds after trusted funding',
            'new lease retains current wounds and balances; stale owner refuses and historical replay never heals',
            'fresh new-owner rest charges once; ordinary inn rejects HP0 and historical replay preserves death',
            'real final-map float32 hit16777217 refusal rolls back fee/vigor/unique resources/all receipts',
            'legacy role without gear basis retains two-field refresh with no implicit resource activation',
            'no inn hot-path rule file reads'],
            'shared_runtime_migrated_profile_verified':False,'automatic_profile_activation':False,
            'native_gui_verified':False,'live_database_modified':False}
    write_json(OUT/'evidence/npc-inn-resources.json',report);print(report)


if __name__=='__main__':main()
