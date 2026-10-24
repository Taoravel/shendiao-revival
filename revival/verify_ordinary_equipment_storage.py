"""Real six-slot inventory/resource transactions under explicit v2 injection.

Disposable roles with explicitly known baselines, not shared activation or GUI.
"""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
import tempfile

from accounts import AccountStore
from inventory import Inventory,AssetChange
from inspect_client import OUT,write_json
from role_attribute_storage import initialize_attribute_baseline
from role_attribute_protocol import growth_refresh,role_detail_profile
from role_equipment import EquipmentAttributeBasis,load_ordinary_equipment_attribute_rules,resource_caps_from_projection
from role_equipment_storage import (initialize_equipment_attribute_basis,current_equipment_totals,
    current_resource_profile,synchronize_inventory_resource_source)
from role_growth import initialize_growth,read_growth,auto_credit_profile,GrowthResourceContext
from role_resource_plan import load_resource_rules,plan_resource_caps
from role_resource_storage import migrate_role_resources,read_role_resources,apply_resource_transition
from world_newbie import load_newbie_routes
import runtime_storage


def main():
    gear=load_ordinary_equipment_attribute_rules();rules=load_resource_rules()
    school=next(school for character,school in load_newbie_routes() if character==1)
    with tempfile.TemporaryDirectory(prefix='ordinary-six-slot-') as directory:
        store=AccountStore(Path(directory)/'state.sqlite3');runtime_storage.prepare(store)
        # Explicit test deployment injection, never the default production loader.
        store.equipment_attribute_rules=gear
        def fixture(name,large_five=False):
            role=store.create_role(1111,name,school,1010101);rid=role['id'];epoch=store.acquire_lease(1111,rid)
            inv=Inventory(store.leased(1111,rid,epoch),1111,rid)
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                growth=initialize_growth(db,1111,rid,epoch,store.growth_rules,expected_level=1,free_points=0)
                p=store.attribute_rules.initial_profile;baseline=p.baseline(rid)
                if large_five:baseline=replace(baseline,five_stats=(32768,10,10,10,10))
                old=initialize_attribute_baseline(db,1111,rid,epoch,baseline,growth,store.attribute_rules,
                    replace(p.vitals(rid),hp=70,mp=40)).vitals
                initialize_equipment_attribute_basis(db,1111,rid,epoch,
                    EquipmentAttributeBasis(rid,1,0,gear.revision,0,'known-explicit-six-slot',seal_resistance=0),gear)
                caps=resource_caps_from_projection(current_equipment_totals(db,1111,rid,epoch,
                    inv.immutable_snapshot_transaction(db),gear))
                migrate_role_resources(db,1111,rid,epoch,old,caps,origin='explicit_migration',
                    migration_id='known-six-slot',rules=rules,equipment_rules=gear)
                inv.apply_settlement(db,AssetChange('six-clean-fixture',grants=tuple(
                    (template,1,1) for template in (49001,42000,43000,44000,45000,46000))))
                synchronize_inventory_resource_source(db,1111,rid,epoch,inv.immutable_snapshot_transaction(db),
                    'six-clean-fixture',resource_rules=rules,equipment_rules=gear,replayed=False)
            return role,epoch,inv
        def equip(db,role,epoch,inv,key,slot,request):
            before=read_role_resources(db,1111,role['id'],epoch,rules)
            event=inv.equip_transaction(db,key,slot,epoch,request)
            assets=inv.immutable_snapshot_transaction(db)
            if not event.replayed:
                caps=resource_caps_from_projection(current_equipment_totals(db,1111,role['id'],epoch,assets,gear))
                apply_resource_transition(db,1111,role['id'],epoch,
                    plan_resource_caps(before,caps,'equip',rules),'resources:'+request,
                    rules=rules,equipment_rules=gear)
            return current_resource_profile(db,1111,role['id'],epoch,assets,equipment_rules=gear,resource_rules=rules)
        def wear_all(db,role,epoch,inv):
            assets=inv.immutable_snapshot_transaction(db)
            slots={49001:0,42000:1,43000:2,44000:3,45000:4,46000:5}
            for item in assets.items:
                final=equip(db,role,epoch,inv,item.id,slots[item.template_id],f'wear:{item.template_id}')
            growth=read_growth(db,1111,role['id'])
            growth_refresh(growth,final)
            role_detail_profile(growth,final)
            return final
        bad,bad_epoch,bad_inv=fixture('六槽回滚',True)
        try:
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                wear_all(db,bad,bad_epoch,bad_inv)
        except ValueError as error:assert 'five stats exceed' in str(error),str(error)
        else:raise AssertionError('Real native signed16 five-stat overflow committed six-slot writes')
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            assert all(i.equipment_slot is None for i in bad_inv.immutable_snapshot_transaction(db).items)
            assert read_role_resources(db,1111,bad['id'],bad_epoch,rules).version==0
            rolled_back=current_resource_profile(db,1111,bad['id'],bad_epoch,
                bad_inv.immutable_snapshot_transaction(db),equipment_rules=gear,resource_rules=rules)
            assert (rolled_back.vitals.hp,rolled_back.vitals.max_hp,rolled_back.vitals.mp,
                rolled_back.vitals.max_mp,rolled_back.seal_resistance)==(70,100,40,100,0)
        role,epoch,inv=fixture('六槽事务')
        try:
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                wear_all(db,role,epoch,inv)
                raise RuntimeError('controlled caller failure after actual final encoding')
        except RuntimeError as error:assert str(error)=='controlled caller failure after actual final encoding'
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            assert all(i.equipment_slot is None for i in inv.immutable_snapshot_transaction(db).items)
            assert read_role_resources(db,1111,role['id'],epoch,rules).version==0
            final=wear_all(db,role,epoch,inv)
            assert (final.vitals.hp,final.vitals.max_hp,final.vitals.mp,final.vitals.max_mp,
                final.vitals.version,final.seal_resistance)==(70,120,40,110,3,6)
            assets=inv.immutable_snapshot_transaction(db)
            assert {i.slot for i in assets.items}==set(range(-6,0))
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            current=current_resource_profile(db,1111,role['id'],epoch,inv.immutable_snapshot_transaction(db),
                equipment_rules=gear,resource_rules=rules)
            assert current==final
            assets=inv.immutable_snapshot_transaction(db)
            grown=auto_credit_profile(db,1111,role['id'],120,store.growth_rules,store.attribute_rules,epoch,
                resource_context=GrowthResourceContext(assets,gear,rules))
            final=current_resource_profile(db,1111,role['id'],epoch,assets,equipment_rules=gear,resource_rules=rules)
            assert (grown.level,grown.experience,grown.free_points)==(2,31,5)
            assert (final.vitals.hp,final.vitals.max_hp,final.vitals.mp,final.vitals.max_mp,final.vitals.version)==(80,130,46,116,4)
            first=next(i for i in assets.items if i.template_id==49001)
            replay=equip(db,role,epoch,inv,first.id,0,'wear:49001')
            assert replay==final
            growth_refresh(grown,final)
        fresh_epoch=store.acquire_lease(1111,role['id'])
        fresh_inventory=Inventory(store.leased(1111,role['id'],fresh_epoch),1111,role['id'])
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            restored=current_resource_profile(db,1111,role['id'],fresh_epoch,
                fresh_inventory.immutable_snapshot_transaction(db),equipment_rules=gear,resource_rules=rules)
            assert restored==final
    report=dict(passed=['actual six-slot equip uses real negative bag slots, current metadata and one resource carrier',
        'known70/40 remains70/40 with120/110 caps; three actual numeric cap transitions advance resource version3',
        'actual120XP same gear grows80/130HP46/116MP,version4,L2/31/free5; old weapon receipt reads current final profile',
        'real final native signed16 overflow rolls back all six equipped items, cap/source writes and resource versions',
        'late caller failure rolls whole six-slot transaction back; the same aborted equipment/resource identities later commit once',
        'new lease reload retains exact v2 final profile without healing'],
        database='disposable',shared_runtime_verified=False,automatic_activation=False,
        native_gui_verified=False,live_server_changed=False,battle_executed=False)
    write_json(OUT/'evidence/ordinary-equipment-storage-verification.json',report);print(report)


if __name__=='__main__':main()
