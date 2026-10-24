"""Explicit resource-aware growth through real caller transactions only."""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
import tempfile

from accounts import AccountStore
from inventory import Inventory,AssetChange
from inspect_client import OUT,write_json
from role_attribute_storage import initialize_attribute_baseline
from role_equipment import EquipmentAttributeBasis,resource_caps_from_projection
from role_equipment_storage import (initialize_equipment_attribute_basis,current_equipment_totals,
    current_resource_profile)
from role_growth import initialize_growth,read_growth,plan_growth_credit,apply_growth_plan,auto_credit_profile
from role_resource_plan import load_resource_rules,plan_resource_source
from role_resource_storage import migrate_role_resources,read_role_resources,apply_resource_transition
from role_attribute_protocol import growth_refresh,role_detail_profile
from role_growth_actions import allocation_transaction,manual_level_transaction
import runtime_storage


def refused(call):
    try:call()
    except ValueError:return
    raise AssertionError('Invalid or stale resource growth operation accepted')


def main():
    from role_growth import GrowthResourceContext
    rules=load_resource_rules()
    with tempfile.TemporaryDirectory(prefix='role-resource-growth-') as directory:
        store=AccountStore(Path(directory)/'state.sqlite3')
        role=store.create_role(1111,'单资源成长',11,1010109)
        runtime_storage.prepare(store)
        epoch=store.acquire_lease(1111,role['id'])
        inv=Inventory(store.leased(1111,role['id'],epoch),1111,role['id'])
        gear=store.equipment_attribute_rules
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            growth=initialize_growth(db,1111,role['id'],epoch,store.growth_rules,expected_level=1,free_points=0)
            p=store.attribute_rules.initial_profile
            legacy=initialize_attribute_baseline(db,1111,role['id'],epoch,p.baseline(role['id']),growth,
                store.attribute_rules,replace(p.vitals(role['id']),hp=70,mp=40))
            initialize_equipment_attribute_basis(db,1111,role['id'],epoch,
                EquipmentAttributeBasis(role['id'],9,0,gear.revision,0,'known-growth-fixture'),gear)
            inv.apply_settlement(db,AssetChange('growth-weapon',grants=((49009,1,1),)))
            key=inv.immutable_snapshot_transaction(db).items[0].id
            inv.equip_transaction(db,key,0,epoch,'growth-equip')
            assets=inv.immutable_snapshot_transaction(db)
            caps=resource_caps_from_projection(current_equipment_totals(db,1111,role['id'],epoch,assets,gear))
            migrate_role_resources(db,1111,role['id'],epoch,legacy.vitals,caps,origin='explicit_migration',
                migration_id='known-growth-profile',rules=rules,equipment_rules=gear)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            context=GrowthResourceContext(inv.immutable_snapshot_transaction(db),gear,rules)
            plan=plan_growth_credit(read_growth(db,1111,role['id']),120,store.growth_rules)
            grown=apply_growth_plan(db,1111,role['id'],epoch,plan,'growth-credit',store.growth_rules,
                store.attribute_rules,resource_context=context)
            assert (grown.level,grown.experience,grown.free_points)==(2,31,5)
            profile=current_resource_profile(db,1111,role['id'],epoch,inv.immutable_snapshot_transaction(db),
                equipment_rules=gear,resource_rules=rules)
            assert (profile.vitals.hp,profile.vitals.max_hp,profile.vitals.mp,profile.vitals.max_mp,profile.vitals.version)==(80,110,46,106,1)
            assert (profile.attributes.physical_attack,profile.attributes.magic_attack,profile.seal_strength)==(49,38,8)
            growth_refresh(grown,profile)
            assert role_detail_profile(grown,profile).values[:5]==(80,110,110,46,106)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            resources=read_role_resources(db,1111,role['id'],epoch,rules)
            assert apply_growth_plan(db,1111,role['id'],epoch,plan,'growth-credit',store.growth_rules,
                store.attribute_rules,resource_context=context)==grown
            assert read_role_resources(db,1111,role['id'],epoch,rules)==resources
            auto_credit_profile(db,1111,role['id'],0,store.growth_rules,store.attribute_rules,epoch,
                resource_context=context)
            inv.apply_settlement(db,AssetChange('growth-carried',grants=((32000,1,1),)))
            context=GrowthResourceContext(inv.immutable_snapshot_transaction(db),gear,rules)
            caps=resource_caps_from_projection(current_equipment_totals(db,1111,role['id'],epoch,
                context.inventory_snapshot,gear))
            updated=apply_resource_transition(db,1111,role['id'],epoch,
                plan_resource_source(resources,caps,'inventory_change',rules),'growth-carried-source',
                rules=rules,equipment_rules=gear).resources
            auto_credit_profile(db,1111,role['id'],0,store.growth_rules,store.attribute_rules,epoch,
                resource_context=context)
            assert read_role_resources(db,1111,role['id'],epoch,rules)==updated
            allocation=allocation_transaction(db,1111,role['id'],epoch,(1,0,0,0,0),'growth-one-vitality',
                store.growth_rules,store.attribute_rules,resource_context=context)
            assert (allocation.attributes.vitals.hp,allocation.attributes.vitals.max_hp,
                allocation.attributes.vitals.version,allocation.growth.free_points)==(90,120,2,4)
            saved_growth=allocation.growth
            saved_resources=read_role_resources(db,1111,role['id'],epoch,rules)
        try:
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                allocation_transaction(db,1111,role['id'],epoch,(1,0,0,0,0),'growth-rollback',
                    store.growth_rules,store.attribute_rules,resource_context=context)
                raise RuntimeError('controlled caller failure after actual final encoding')
        except RuntimeError as error:
            assert str(error)=='controlled caller failure after actual final encoding'
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            assert read_growth(db,1111,role['id'])==saved_growth
            assert read_role_resources(db,1111,role['id'],epoch,rules)==saved_resources
            later=allocation_transaction(db,1111,role['id'],epoch,(1,0,0,0,0),'growth-rollback',
                store.growth_rules,store.attribute_rules,resource_context=context)
            assert (later.growth.free_points,later.attributes.vitals.hp,later.attributes.vitals.max_hp,
                later.attributes.vitals.version)==(3,100,130,3)
            replay=allocation_transaction(db,1111,role['id'],epoch,(1,0,0,0,0),'growth-one-vitality',
                store.growth_rules,store.attribute_rules,resource_context=context)
            assert replay.growth==later.growth and replay.attributes==later.attributes
            refused(lambda:allocation_transaction(db,1111,role['id'],epoch,(2,0,0,0,0),'growth-one-vitality',
                store.growth_rules,store.attribute_rules,resource_context=context))
        # Missing explicit context still refuses this migrated profile and the
        # caller rollback retains both growth and resource state.
        try:
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                apply_growth_plan(db,1111,role['id'],epoch,
                    plan_growth_credit(read_growth(db,1111,role['id']),1,store.growth_rules),
                    'growth-no-context',store.growth_rules,store.attribute_rules)
        except ValueError:pass
        else:raise AssertionError('Migrated growth ran through the legacy writer')
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            assert read_growth(db,1111,role['id'])==later.growth
            assert read_role_resources(db,1111,role['id'],epoch,rules).version==3
            inv.apply_settlement(db,AssetChange('growth-stale-assets',grants=((32000,1,1),)))
            refused(lambda:apply_growth_plan(db,1111,role['id'],epoch,
                plan_growth_credit(later.growth,1,store.growth_rules),'growth-stale-context',
                store.growth_rules,store.attribute_rules,resource_context=context))
            assert read_growth(db,1111,role['id'])==later.growth
            db.rollback()
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            # Controlled earned-XP fixture, not a claim of natural quest level10.
            credit=sum(store.growth_rules.costs[level] for level in range(2,10))-31+store.growth_rules.costs[10]
            auto_credit_profile(db,1111,role['id'],credit,store.growth_rules,store.attribute_rules,epoch,
                resource_context=context)
            ten=current_resource_profile(db,1111,role['id'],epoch,context.inventory_snapshot,
                equipment_rules=gear,resource_rules=rules)
            assert (ten.attributes.level,ten.vitals.hp,ten.vitals.max_hp,ten.vitals.mp,ten.vitals.max_mp)==(10,180,210,94,154)
            eleven=manual_level_transaction(db,1111,role['id'],epoch,0,'resource-manual-level',
                store.growth_rules,store.attribute_rules,resource_context=context)
            assert (eleven.growth.level,eleven.growth.experience,eleven.growth.free_points)==(11,0,48)
            assert (eleven.attributes.vitals.hp,eleven.attributes.vitals.max_hp,
                eleven.attributes.vitals.mp,eleven.attributes.vitals.max_mp)==(190,220,100,160)
            assert manual_level_transaction(db,1111,role['id'],epoch,0,'resource-manual-level',
                store.growth_rules,store.attribute_rules,resource_context=context).attributes==eleven.attributes
            refused(lambda:manual_level_transaction(db,1111,role['id'],epoch,0,'resource-manual-insufficient',
                store.growth_rules,store.attribute_rules,resource_context=context))
        fresh_epoch=store.acquire_lease(1111,role['id'])
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            refused(lambda:allocation_transaction(db,1111,role['id'],epoch,(1,0,0,0,0),'growth-late-epoch',
                store.growth_rules,store.attribute_rules,resource_context=context))
            assert read_role_resources(db,1111,role['id'],fresh_epoch,rules).hp==190
    report=dict(passed=['actual equipped migrated70/40 grows120XP toL2/31XP/free5 and80/110HP46/106MP once',
        'current49/38/8, resource version1 and final entry/refresh share one profile; paid replay does not heal',
        'zeroXP before/after actual carried grant changes no resources and does not collide on an invented no-op receipt',
        'actual vitality allocation keeps wounds; late caller failure rolls points, naked attributes, resources and receipts back',
        'same aborted allocation key later commits100/130/version3 once; earlier paid replay returns current profile',
        'controlled XP stops auto at10; actual manual request gives11,190/220HP100/160MP/free48 once and insufficient XP refuses',
        'missing context, changed intent, stale assets and obsolete login lease refuse'],
        database='disposable',shared_runtime_tested=False,native_gui_verified=False,
        live_server_changed=False,battle_executed=False)
    write_json(OUT/'evidence/role-resource-growth-verification.json',report);print(report)


if __name__=='__main__':main()
