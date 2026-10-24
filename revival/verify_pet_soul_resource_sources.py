"""Pet soul source CAS joins each supported sole role-resource source hook."""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import sqlite3
from accounts import AccountStore
from inventory import Inventory
from item_effects import VitalState
from role_attributes import AttributeBaseline
from role_attribute_storage import initialize_attribute_baseline
from role_growth import initialize_growth
from role_equipment import EquipmentAttributeBasis,load_ordinary_equipment_attribute_rules,resource_caps_from_projection
from role_equipment_storage import (initialize_equipment_attribute_basis,current_equipment_totals,
    current_resource_profile,synchronize_inventory_resource_source)
from role_resource_storage import migrate_role_resources,read_role_resources
from role_equipment_gems import GemEquipmentRules,GemExtraBasis
import role_equipment_gem_storage as gem_roles
from pet_souls import SoulRules,SoulProfile,SoulBean
import pet_soul_storage as souls
import runtime_storage


def main():
    with TemporaryDirectory(prefix='soul-sole-resource-') as tmp:
        store=AccountStore(Path(tmp)/'state.sqlite3');runtime_storage.prepare(store)
        soul_rules=SoulRules.load();gems=GemEquipmentRules.load();ordinary=load_ordinary_equipment_attribute_rules()
        with closing(store.connect()) as db:souls.prepare(db);gem_roles.prepare(db)
        for mode in ('ordinary','gem'):
            gear=gems.carrier_rules if mode=='gem' else ordinary
            shape=next(k for k,v in gear.shape_characters.items() if v==1)
            role=store.create_role(1111,'元魂普通资源' if mode=='ordinary' else '元魂宝石资源',min(store.choices[shape]),shape)
            rid=role['id'];epoch=store.acquire_lease(1111,rid);inv=Inventory(store.leased(1111,rid,epoch),1111,rid)
            def totals(db):
                return (gem_roles.read_totals(db,inv,gems).core if mode=='gem' else current_equipment_totals(
                    db,1111,rid,epoch,inv.immutable_snapshot_transaction(db),gear))
            def profile(db):
                return (gem_roles.read_profile(db,inv,gems,store.resource_rules).core if mode=='gem' else
                    current_resource_profile(db,1111,rid,epoch,inv.immutable_snapshot_transaction(db),
                        equipment_rules=gear,resource_rules=store.resource_rules))
            def sync(db,identity,replayed=False):
                return (gem_roles.synchronize_inventory_source(db,inv,gems,store.resource_rules,identity,replayed=replayed)
                    if mode=='gem' else synchronize_inventory_resource_source(db,1111,rid,epoch,
                        inv.immutable_snapshot_transaction(db),identity,equipment_rules=gear,
                        resource_rules=store.resource_rules,replayed=replayed))
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE');db.execute('INSERT INTO role_progress VALUES(?,0)',(rid,))
                growth=initialize_growth(db,1111,rid,epoch,store.growth_rules,expected_level=1,free_points=0)
                old=initialize_attribute_baseline(db,1111,rid,epoch,
                    AttributeBaseline(rid,1,0,(10,)*5,(100,100,20,10,50,10,10,20,10)),growth,
                    store.attribute_rules,VitalState(rid,0,70,100,40,100)).vitals
                basis=EquipmentAttributeBasis(rid,1,0,gear.revision,0,'explicit-soul-root-'+mode,seal_resistance=0)
                initialize_equipment_attribute_basis(db,1111,rid,epoch,basis,gear)
                if mode=='gem':gem_roles.initialize_extra(db,inv,gems,GemExtraBasis(rid,0,gems.revision,basis.source_id,
                    ((350,0),(360,0),(370,0),(380,0),(1130,0),(1530,0))),'explicit_known_ungemmed_extras')
                migrate_role_resources(db,1111,rid,epoch,old,resource_caps_from_projection(totals(db)),
                    origin='explicit_migration',migration_id='known-soul-root-'+mode,
                    rules=store.resource_rules,equipment_rules=gear)
            pet=inv.grant_pet(500001)
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                initial=SoulProfile(rid,pet,0,soul_rules.revision,'explicit-soul-fixture',((1,SoulBean(31276,61,0,104,-105,106)),))
                souls.initialize(db,inv,soul_rules,initial,'explicit_known_pet_souls')
                sync(db,'known-soul-import')
                before_resources=read_role_resources(db,1111,rid,epoch,store.resource_rules)
                assert (before_resources.hp,before_resources.mp,before_resources.caps.hp_max)==(70,40,100)
                before_profile=profile(db)
            def state():
                with closing(store.connect()) as db:
                    db.execute('BEGIN')
                    return inv.immutable_snapshot_transaction(db),souls.read(db,inv,soul_rules,pet),profile(db)
            before=state()
            with closing(store.connect()) as db:
                db.execute("CREATE TRIGGER soul_resource_fault BEFORE INSERT ON role_resource_receipts BEGIN SELECT RAISE(ABORT,'soul-resource-fault'); END");db.commit()
            try:
                with closing(store.connect()) as db,db:
                    db.execute('BEGIN IMMEDIATE')
                    souls.replace_profile(db,inv,soul_rules,before[1],replace(initial,version=1,entries=()))
                    sync(db,'known-soul-change')
            except sqlite3.IntegrityError as error:assert 'soul-resource-fault' in str(error)
            else:raise AssertionError('Expected actual resource receipt failure after soul CAS')
            finally:
                with closing(store.connect()) as db:db.execute('DROP TRIGGER soul_resource_fault');db.commit()
            assert state()==before
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                changed=souls.replace_profile(db,inv,soul_rules,before[1],replace(initial,version=1,entries=()))
                try:sync(db,'paid-cannot-repair',replayed=True)
                except ValueError:pass
                else:raise AssertionError('Paid root hook repaired pending soul source')
                after=sync(db,'known-soul-change')
                assert (after.hp,after.mp,after.caps.hp_max,after.caps.mp_max,after.version)==(70,40,100,100,before_resources.version)
                assert after.caps.source.inventory_revision==changed.inventory_revision
                assert profile(db).attributes==before_profile.attributes
            with closing(store.connect()) as db:
                db.execute('BEGIN')
                db.set_authorizer(lambda action,*args:sqlite3.SQLITE_DENY if action in
                    (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE) else sqlite3.SQLITE_OK)
                assert sync(db,'known-soul-change',replayed=True)==after
                assert souls.read(db,inv,soul_rules,pet).profile.entries==()
        print('PASS real ordinary-v2 and complete-gem root source hooks join soul CAS; '
            'resource receipt failure rolls all back;70HP/40MP and resource version preserved; paid strict readonly')


if __name__=='__main__':main()
