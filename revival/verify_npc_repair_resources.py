"""Explicitly migrated repair joins condition/fee/caps and final encoding."""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
import struct
import tempfile
import time
from accounts import AccountStore
from inventory import Inventory,AssetChange
from role_growth import initialize_growth,read_growth
from role_attribute_storage import initialize_attribute_baseline,read_attribute_snapshot
from role_equipment import EquipmentAttributeBasis,resource_caps_from_projection
from role_equipment_storage import (initialize_equipment_attribute_basis,current_equipment_totals,
    current_resource_profile)
from role_resource_plan import load_resource_rules,plan_resource_values,plan_resource_caps
from role_resource_storage import migrate_role_resources,read_role_resources,apply_resource_transition
from role_attribute_protocol import growth_refresh
from currency import initialize_wallet,read_wallet
from world_owner import MapAddress,Location
from world_npcs import NpcScene
from inspect_client import OUT,write_json
import runtime_storage
import npc_repairs


def main():
    rules=load_resource_rules()
    with tempfile.TemporaryDirectory() as temp:
        store=AccountStore(Path(temp)/'npc-repair-resources.sqlite3')
        roles={name:store.create_role(1111,name,11,1010109) for name in ('修理新资源','旧修理重放','修理编码回滚')}
        prepared=runtime_storage.prepare(store);gear=store.equipment_attribute_rules
        npc=next(p for ps in store.npc_resources[0].values() for p in ps if p.npc_id==10004)
        address=MapAddress(npc.map_id,npc.map_id,0);npc_key=(npc.map_id<<32)|npc.placement_id
        scene=NpcScene(address,(npc,),prepared[3],interaction_radius=32,binding_capacity=1)
        scene.bind(npc_key,npc.placement_id)
        def fixture(name,*,migrate=True,bad_hit=False):
            role=roles[name];epoch=store.acquire_lease(1111,role['id'])
            inv=Inventory(store.leased(1111,role['id'],epoch),1111,role['id'])
            with closing(inv.accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                p=store.attribute_rules.initial_profile
                growth=initialize_growth(db,1111,inv.role_id,epoch,store.growth_rules,expected_level=1,free_points=0)
                basis=p.baseline(inv.role_id)
                if bad_hit:basis=replace(basis,values=(*basis.values[:4],16777217,*basis.values[5:]))
                before=initialize_attribute_baseline(db,1111,inv.role_id,epoch,basis,growth,
                    store.attribute_rules,replace(p.vitals(inv.role_id),hp=70,mp=40)).vitals
                initialize_equipment_attribute_basis(db,1111,inv.role_id,epoch,
                    EquipmentAttributeBasis(inv.role_id,9,0,gear.revision,11,'explicit-repair-resource-fixture'),gear)
                initialize_wallet(db,1111,inv.role_id,epoch,(1000,0,0,0),'explicit_migration',store.currency_rules)
                inv.apply_settlement(db,AssetChange('known-repair-weapon',grants=((49009,1,1),)))
                item=inv.immutable_snapshot_transaction(db).items[0]
                inv.equip_transaction(db,item.id,0,epoch,'known-repair-equip')
                condition=inv.equipment_condition(db,item.id)
                inv.wear_equipment(db,item.id,'known-repair-wear',condition.version,20)
                if migrate:
                    totals=current_equipment_totals(db,1111,inv.role_id,epoch,inv.immutable_snapshot_transaction(db),gear)
                    migrate_role_resources(db,1111,inv.role_id,epoch,before,resource_caps_from_projection(totals),
                        origin='explicit_migration',migration_id='explicit-repair-profile',rules=rules,equipment_rules=gear)
            return inv,item.id
        def intent(inv,key,identity):
            now=int(time.monotonic()*1000);loc=Location(inv.role_id,inv.epoch,address,1,npc.x,npc.y)
            proof=scene.interact(struct.pack('>q',npc_key),loc,loc,request_id=identity,now_ms=now,deadline_ms=now+10000)
            return npc_repairs.plan(store.npc_gameplay,struct.pack('>iqii',2,npc_key,4,key),proof,loc,
                request_id=identity,now_ms=now,deadline_ms=now+10000)
        def state(inv):
            with closing(inv.accounts.connect()) as db:
                db.execute('BEGIN')
                snapshot=inv.immutable_snapshot_transaction(db)
                resources=read_role_resources(db,1111,inv.role_id,inv.epoch,rules)
                assert resources.caps.source.inventory_revision==snapshot.inventory_revision
                wallet=read_wallet(db,1111,inv.role_id,inv.epoch,store.currency_rules)
                counts=tuple(db.execute('SELECT COUNT(*) FROM '+table+' WHERE role_id=?',(inv.role_id,)).fetchone()[0]
                    for table in ('role_resource_receipts','role_wallet_receipts','npc_command_receipts','inventory_equipment_receipts'))
                return snapshot,resources,wallet,counts
        def final(db,inv,snapshot):
            profile=current_resource_profile(db,1111,inv.role_id,inv.epoch,snapshot,equipment_rules=gear,resource_rules=rules)
            return (growth_refresh(read_growth(db,1111,inv.role_id),profile),)
        def refused(action,*,message=None):
            try:action()
            except ValueError as error:
                if message is not None:assert str(error)==message
                return
            raise AssertionError('Unsafe repair accepted')
        def forbidden_draw(bound):raise AssertionError('Paid repair replay invoked randomness')
        def resource_fixture(inv,identity,*,hp=None,mp=None,wear_key=None):
            with closing(inv.accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                before=read_role_resources(db,1111,inv.role_id,inv.epoch,rules)
                if wear_key is not None:
                    condition=inv.equipment_condition(db,wear_key)
                    inv.wear_equipment(db,wear_key,identity,condition.version,10)
                totals=current_equipment_totals(db,1111,inv.role_id,inv.epoch,
                    inv.immutable_snapshot_transaction(db),gear)
                caps=resource_caps_from_projection(totals)
                transition=(plan_resource_caps(before,caps,'equipment_wear',rules) if wear_key is not None else
                    plan_resource_values(before,hp,mp,'medicine',rules,current_caps=caps))
                return apply_resource_transition(db,1111,inv.role_id,inv.epoch,transition,identity,
                    rules=rules,equipment_rules=gear)
        inv,key=fixture('修理新资源');cmd=intent(inv,key,'repair-once');before=state(inv)
        result=npc_repairs.repair(store,inv,cmd,final,draw_source=lambda bound:0,resource_rules=rules,equipment_rules=gear)
        after=state(inv)
        assert any(k==0xc32c8 for k,b in result)
        assert after[2][0].balance==960 and (after[1].hp,after[1].mp,after[1].version)==(70,40,0)
        assert after[1].caps.source.inventory_revision>before[1].caps.source.inventory_revision
        npc_repairs.repair(store,inv,cmd,final,draw_source=forbidden_draw,resource_rules=rules,equipment_rules=gear)
        assert state(inv)==after
        resource_fixture(inv,'later-resources',hp=50,mp=30)
        hurt=state(inv)
        npc_repairs.repair(store,inv,cmd,final,draw_source=forbidden_draw,resource_rules=rules,equipment_rules=gear)
        assert state(inv)==hurt
        refused(lambda:npc_repairs.repair(store,inv,cmd,resource_rules=rules,equipment_rules=gear))
        refused(lambda:npc_repairs.repair(store,inv,cmd,final,resource_rules=rules))
        assert state(inv)==hurt
        resource_fixture(inv,'later-wear',wear_key=key)
        late=intent(inv,key,'late-repair');before_late=state(inv)
        def fail_after_final(db,inventory,snapshot):
            final(db,inventory,snapshot)
            raise ValueError('Controlled failure after repair resource CAS and native encoding')
        refused(lambda:npc_repairs.repair(store,inv,late,fail_after_final,draw_source=lambda bound:0,
            resource_rules=rules,equipment_rules=gear))
        assert state(inv)==before_late
        npc_repairs.repair(store,inv,late,final,draw_source=lambda bound:0,resource_rules=rules,equipment_rules=gear)
        paid=state(inv);assert paid[2][0].balance==940 and (paid[1].hp,paid[1].mp)==(50,30)
        new_epoch=store.acquire_lease(1111,inv.role_id)
        current=Inventory(store.leased(1111,inv.role_id,new_epoch),1111,inv.role_id)
        current_before=state(current)
        refused(lambda:npc_repairs.repair(store,inv,late,final,draw_source=forbidden_draw,
            resource_rules=rules,equipment_rules=gear))
        assert state(current)==current_before
        npc_repairs.repair(store,current,intent(current,key,'late-repair'),final,draw_source=forbidden_draw,
            resource_rules=rules,equipment_rules=gear)
        assert state(current)==current_before
        legacy,legacy_key=fixture('旧修理重放',migrate=False)
        legacy_cmd=intent(legacy,legacy_key,'legacy-paid')
        npc_repairs.repair(store,legacy,legacy_cmd,draw_source=lambda bound:0,resource_rules=rules,equipment_rules=gear)
        with closing(legacy.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            old=read_attribute_snapshot(db,1111,legacy.role_id,legacy.epoch).vitals
            totals=current_equipment_totals(db,1111,legacy.role_id,legacy.epoch,
                legacy.immutable_snapshot_transaction(db),gear)
            migrate_role_resources(db,1111,legacy.role_id,legacy.epoch,old,resource_caps_from_projection(totals),
                origin='explicit_migration',migration_id='legacy-paid-now-migrated',rules=rules,equipment_rules=gear)
        resource_fixture(legacy,'legacy-later-values',hp=55,mp=35)
        old_paid=state(legacy)
        npc_repairs.repair(store,legacy,legacy_cmd,final,draw_source=forbidden_draw,resource_rules=rules,equipment_rules=gear)
        assert state(legacy)==old_paid and old_paid[2][0].balance==960
        with closing(legacy.accounts.connect()) as db:
            assert db.execute("SELECT COUNT(*) FROM role_resource_receipts WHERE role_id=? AND cause='equipment_repair'",
                (legacy.role_id,)).fetchone()[0]==0
        bad,bad_key=fixture('修理编码回滚',bad_hit=True);bad_before=state(bad)
        try:npc_repairs.repair(store,bad,intent(bad,bad_key,'float-refusal'),final,draw_source=lambda bound:0,
            resource_rules=rules,equipment_rules=gear)
        except ValueError as error:assert 'float' in str(error).lower(),str(error)
        else:raise AssertionError('Native hit16777217 failure committed repair')
        assert state(bad)==bad_before
        report={'passed':['fresh ordinary repair captures unique before and applies equipment_repair source/caps in same transaction',
            'native fee40 and final encoded profile preserve HP70/MP40/version0',
            'paid replay preserves later HP50/MP30 with no draw, fee, new source or resource receipt',
            'late post-encoding failure rolls condition/cash/source/receipts back; same command later succeeds',
            'new lease retains current state; stale owner refused and fresh proof replay only reads current',
            'legacy-paid repair after explicit profile migration never creates a retrospective equipment_repair transition',
            'real native float32 hit16777217 failure rolls repair/resources/fee/all receipts back',
            'missing final hook or half-injected rules refuse migrated repair'],
            'shared_wire_route_verified':False,'native_gui_verified':False,'live_database_modified':False}
    write_json(OUT/'evidence/npc-repair-resources.json',report);print(report)


if __name__=='__main__':main()
