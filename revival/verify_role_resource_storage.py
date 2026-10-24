"""Single actual resource carrier and explicit migration in caller transactions."""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
import tempfile

from accounts import AccountStore
from inventory import Inventory,AssetChange
from inspect_client import OUT,write_json
from role_attribute_storage import (initialize_attribute_baseline,read_attribute_snapshot,
    read_naked_attributes,update_role_vitals,sync_growth_attributes)
from role_equipment import EquipmentAttributeBasis
from role_equipment_storage import (initialize_equipment_attribute_basis,current_equipment_projection,
    resource_caps_from_projection)
from role_growth import initialize_growth
from role_resource_plan import load_resource_rules,plan_resource_values,plan_resource_source
from role_resource_storage import (prepare_resource_storage,migrate_role_resources,read_role_resources,
    apply_resource_transition)
import runtime_storage
from currency import initialize_wallet,read_wallet,apply_currency,CurrencyChange
from role_attribute_protocol import growth_refresh,role_detail_profile


def refused(call):
    try:call()
    except ValueError:return
    raise AssertionError('An unsafe or stale resource operation was accepted')


def main():
    rules=load_resource_rules()
    with tempfile.TemporaryDirectory(prefix='role-resource-storage-') as directory:
        store=AccountStore(Path(directory)/'state.sqlite3')
        role=store.create_role(1111,'唯一人物资源',11,1010109)
        unknown=store.create_role(1111,'未知资源旧角色',11,1010109)
        runtime_storage.prepare(store)
        with closing(store.connect()) as db:
            prepare_resource_storage(db)
        epoch=store.acquire_lease(1111,role['id'])
        inv=Inventory(store.leased(1111,role['id'],epoch),1111,role['id'])
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            growth=initialize_growth(db,1111,role['id'],epoch,store.growth_rules,expected_level=1,free_points=0)
            p=store.attribute_rules.initial_profile
            before=initialize_attribute_baseline(db,1111,role['id'],epoch,p.baseline(role['id']),growth,
                store.attribute_rules,replace(p.vitals(role['id']),hp=70,mp=40)).vitals
            refused(lambda:read_role_resources(db,1111,role['id'],epoch,rules))
            initialize_wallet(db,1111,role['id'],epoch,(100,0,0,0),'explicit_migration',store.currency_rules)
            gear=store.equipment_attribute_rules
            initialize_equipment_attribute_basis(db,1111,role['id'],epoch,
                EquipmentAttributeBasis(role['id'],9,0,gear.revision,0,'explicit-known-resource-fixture'),gear)
            inv.apply_settlement(db,AssetChange('resource-known-weapon',grants=((49009,1,1),)))
            key=inv.immutable_snapshot_transaction(db).items[0].id
            inv.equip_transaction(db,key,0,epoch,'resource-known-equip')
            final=current_equipment_projection(db,1111,role['id'],epoch,inv.immutable_snapshot_transaction(db),gear)
            caps=resource_caps_from_projection(final)
            kwargs=dict(origin='explicit_migration',migration_id='known-resource-profile',rules=rules,equipment_rules=gear)
            migrated=migrate_role_resources(db,1111,role['id'],epoch,before,caps,**kwargs)
            assert (migrated.hp,migrated.mp,migrated.caps.hp_max,migrated.caps.mp_max,migrated.version)==(70,40,100,100,0)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            assert read_role_resources(db,1111,role['id'],epoch,rules)==migrated
            assert migrate_role_resources(db,1111,role['id'],epoch,before,caps,**kwargs)==migrated
            from role_equipment_storage import current_equipment_totals,current_resource_profile
            totals=current_equipment_totals(db,1111,role['id'],epoch,inv.immutable_snapshot_transaction(db),gear)
            assert (totals.attributes.physical_attack,totals.attributes.magic_attack,totals.seal_strength)==(45,35,8)
            profile=current_resource_profile(db,1111,role['id'],epoch,inv.immutable_snapshot_transaction(db),
                equipment_rules=gear,resource_rules=rules)
            assert (profile.vitals.hp,profile.vitals.mp,profile.vitals.version)==(70,40,0)
            assert read_naked_attributes(db,1111,role['id'],epoch).hp_max==100
            refused(lambda:read_attribute_snapshot(db,1111,role['id'],epoch))
            refused(lambda:update_role_vitals(db,1111,role['id'],epoch,before,replace(before,version=1,hp=71)))
            refused(lambda:sync_growth_attributes(db,1111,growth,epoch,store.attribute_rules))
            assert read_role_resources(db,1111,role['id'],epoch,rules)==migrated
            first=plan_resource_values(migrated,80,50,'medicine',rules)
            result=apply_resource_transition(db,1111,role['id'],epoch,first,'medicine-once',rules=rules,equipment_rules=gear)
            assert (result.resources.hp,result.resources.mp,result.resources.version,result.replayed)==(80,50,1,False)
            second=plan_resource_values(result.resources,85,50,'medicine',rules)
            current=apply_resource_transition(db,1111,role['id'],epoch,second,'medicine-later',rules=rules,equipment_rules=gear)
            replay=apply_resource_transition(db,1111,role['id'],epoch,first,'medicine-once',rules=rules,equipment_rules=gear)
            assert replay.replayed and replay.resources==current.resources
            assert (replay.resources.hp,replay.resources.version)==(85,2)
            refused(lambda:apply_resource_transition(db,1111,role['id'],epoch,first,'stale-medicine',rules=rules,equipment_rules=gear))
            refused(lambda:apply_resource_transition(db,1111,role['id'],epoch,second,'medicine-once',rules=rules,equipment_rules=gear))
            assert migrate_role_resources(db,1111,role['id'],epoch,before,caps,**kwargs)==current.resources
        def caller_transaction(db):
            inv.apply_settlement(db,AssetChange('resource-outer-goods',grants=((32000,2,1),)))
            apply_currency(db,1111,role['id'],epoch,
                CurrencyChange('resource-outer-fee','npc_shop','controlled-caller-fixture',(('cash',-10),)),store.currency_rules)
            # A read cannot silently refresh pending source metadata or heal.
            refused(lambda:current_resource_profile(db,1111,role['id'],epoch,
                inv.immutable_snapshot_transaction(db),equipment_rules=gear,resource_rules=rules))
            assert read_role_resources(db,1111,role['id'],epoch,rules)==current.resources
            # Derive current final caps from actual assets, without fabricating
            # a naked VitalState just to enter the old equipment calculator.
            latest=resource_caps_from_projection(current_equipment_totals(db,1111,role['id'],epoch,
                inv.immutable_snapshot_transaction(db),gear))
            transition=plan_resource_values(current.resources,90,50,'medicine',rules,current_caps=latest)
            result=apply_resource_transition(db,1111,role['id'],epoch,transition,'resource-outer-heal',
                rules=rules,equipment_rules=gear)
            final=current_resource_profile(db,1111,role['id'],epoch,inv.immutable_snapshot_transaction(db),
                equipment_rules=gear,resource_rules=rules)
            growth_refresh(growth,final)
            detail=role_detail_profile(growth,final)
            assert detail.values[:5]==(90,100,100,50,100)
            assert (detail.values[8],detail.values[12],detail.values[14])==(45,35,8)
            return result
        try:
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                caller_transaction(db)
                raise RuntimeError('controlled late caller failure')
        except RuntimeError as error:
            assert str(error)=='controlled late caller failure'
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            assert read_role_resources(db,1111,role['id'],epoch,rules)==current.resources
            assert next(v.balance for v in read_wallet(db,1111,role['id'],epoch,store.currency_rules) if v.currency=='cash')==100
            assert all(i.template_id!=32000 for i in inv.immutable_snapshot_transaction(db).items)
            paid=caller_transaction(db)
            assert (paid.resources.hp,paid.resources.version)==(90,3)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            assert read_role_resources(db,1111,role['id'],epoch,rules)==paid.resources
            assert next(v.balance for v in read_wallet(db,1111,role['id'],epoch,store.currency_rules) if v.currency=='cash')==90
            assert next(i.quantity for i in inv.immutable_snapshot_transaction(db).items if i.template_id==32000)==2
            next_heal=plan_resource_values(paid.resources,95,50,'medicine',rules)
            forged=replace(next_heal,cause='unequip')
            refused(lambda:apply_resource_transition(db,1111,role['id'],epoch,forged,'false-unequip-heal',
                rules=rules,equipment_rules=gear))
            stale_caps=replace(next_heal.after.caps,source=replace(next_heal.after.caps.source,
                inventory_revision=next_heal.after.caps.source.inventory_revision-1))
            stale=replace(next_heal,after=replace(next_heal.after,caps=stale_caps))
            refused(lambda:apply_resource_transition(db,1111,role['id'],epoch,stale,'stale-source-heal',
                rules=rules,equipment_rules=gear))
            refused(lambda:migrate_role_resources(db,1111,role['id'],epoch,replace(before,hp=69),caps,**kwargs))
            assert read_role_resources(db,1111,role['id'],epoch,rules)==paid.resources
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            inv.apply_settlement(db,AssetChange('resource-source-only-goods',grants=((32000,1,1),)))
            latest=resource_caps_from_projection(current_equipment_totals(db,1111,role['id'],epoch,
                inv.immutable_snapshot_transaction(db),gear))
            source_plan=plan_resource_source(paid.resources,latest,'inventory_change',rules)
            from role_equipment_storage import synchronize_inventory_resource_source
            refused(lambda:synchronize_inventory_resource_source(db,1111,role['id'],epoch,
                inv.immutable_snapshot_transaction(db),'source-only-replayed',resource_rules=rules,
                equipment_rules=gear,replayed=True))
            refused(lambda:apply_resource_transition(db,1111,role['id'],epoch,
                replace(source_plan,after=replace(source_plan.after,hp=91)),
                'false-source-only-heal',rules=rules,equipment_rules=gear))
            latest_resources=synchronize_inventory_resource_source(db,1111,role['id'],epoch,
                inv.immutable_snapshot_transaction(db),'resource-source-only',resource_rules=rules,
                equipment_rules=gear,replayed=False)
            assert (latest_resources.hp,latest_resources.mp,latest_resources.version)==(90,50,3)
            assert synchronize_inventory_resource_source(db,1111,role['id'],epoch,
                inv.immutable_snapshot_transaction(db),'resource-source-only',resource_rules=rules,
                equipment_rules=gear,replayed=True)==latest_resources
            refused(lambda:synchronize_inventory_resource_source(db,1111,role['id'],epoch,
                inv.immutable_snapshot_transaction(db),'bad-domain-replay-flag',resource_rules=rules,
                equipment_rules=gear,replayed=0))
            profile=current_resource_profile(db,1111,role['id'],epoch,inv.immutable_snapshot_transaction(db),
                equipment_rules=gear,resource_rules=rules)
            assert profile.inventory_revision==latest.source.inventory_revision and profile.vitals.hp==90
        unknown_epoch=store.acquire_lease(1111,unknown['id'])
        unknown_inventory=Inventory(store.leased(1111,unknown['id'],unknown_epoch),1111,unknown['id'])
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            refused(lambda:read_role_resources(db,1111,unknown['id'],unknown_epoch,rules))
            unknown_assets=unknown_inventory.immutable_snapshot_transaction(db)
            assert synchronize_inventory_resource_source(db,1111,unknown['id'],unknown_epoch,
                unknown_assets,'unknown-legacy-source',resource_rules=rules,
                equipment_rules=gear,replayed=False) is None
            refused(lambda:synchronize_inventory_resource_source(db,1111,unknown['id'],unknown_epoch,
                unknown_assets,'missing-prepared-gear',resource_rules=rules,
                equipment_rules=None,replayed=False))
        new_epoch=store.acquire_lease(1111,role['id'])
        reconnected_inventory=Inventory(store.leased(1111,role['id'],new_epoch),1111,role['id'])
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            refused(lambda:read_role_resources(db,1111,role['id'],epoch,rules))
            refused(lambda:apply_resource_transition(db,1111,role['id'],epoch,first,'medicine-once',
                rules=rules,equipment_rules=gear))
            assert read_role_resources(db,1111,role['id'],new_epoch,rules)==latest_resources
            reloaded_inventory=reconnected_inventory.immutable_snapshot_transaction(db)
            current_profile=current_resource_profile(db,1111,role['id'],new_epoch,reloaded_inventory,
                equipment_rules=gear,resource_rules=rules)
            assert (current_profile.vitals.hp,current_profile.vitals.mp,current_profile.vitals.version)==(90,50,3)
            refused(lambda:current_resource_profile(db,1111,role['id'],epoch,reloaded_inventory,
                equipment_rules=gear,resource_rules=rules))
    report=dict(passed=['actual worn starter source and known70/40 migrate explicitly without healing',
        'same migration intent replays and current resource state reloads',
        'naked attributes stay readable; legacy mixed snapshots and vital/growth writers refuse a migrated profile',
        'complete-before resource CAS and retry receipts; later85 is never overwritten by old heal or migration replay',
        'actual carried-goods/fee/resource/source/receipts share one caller rollback; same aborted keys later commit90 once',
        'migrated final profile uses independent equipment totals and current resources; pending asset source refuses without healing',
        'precommit refresh/detail share current90/50 and45/35/8; a fresh lease reloads identical profile and old lease refuses',
        'actual carried grant source-only settlement preserves90/50/version3; retry reads current and forged source-only healing refuses',
        'shared source helper requires explicit domain replay bool; paid pending source rejects and unknown legacy needs no invented gear basis',
        'unknown profiles, conflicting migrations, forged unequip heals and stale cap sources refuse'],
        database='disposable',native_gui_verified=False,live_server_changed=False,
        scope='storage Interface only; no automatic role activation or six-slot runtime')
    write_json(OUT/'evidence/role-resource-storage-verification.json',report);print(report)


if __name__=='__main__':main()
