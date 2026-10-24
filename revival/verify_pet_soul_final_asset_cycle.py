"""Actual wear/remove assets + final pet totals/sole resources/root source."""
from pathlib import Path
from tempfile import TemporaryDirectory
from contextlib import closing
from dataclasses import replace
import sqlite3
import struct
from accounts import AccountStore
from inventory import Inventory,pet_record
from currency import initialize_wallet,read_wallet
from item_effects import VitalState
from role_attributes import AttributeBaseline
from role_attribute_storage import initialize_attribute_baseline
from role_growth import initialize_growth
from role_equipment import EquipmentAttributeBasis,load_ordinary_equipment_attribute_rules,resource_caps_from_projection
from role_equipment_storage import initialize_equipment_attribute_basis,current_equipment_totals,synchronize_inventory_resource_source
from role_resource_storage import migrate_role_resources,read_role_resources
from pet_souls import SoulProfile
from pet_soul_item_data import OrbTips
from pet_soul_item_storage import OrbSource
from pet_soul_actions import SoulActionRules
from pet_soul_totals import PetSoulTotalsRules,PetSoulExtraBasis
from native_gameplay_probe import probe
import pet_soul_storage as souls
import pet_soul_item_storage as orbs
import pet_soul_action_storage as actions
import pet_soul_authority as authority
import pet_soul_totals_storage as totals
import role_mingwen as mingwen
import runtime_storage


def main():
    with TemporaryDirectory(prefix='full-soul-asset-resource-') as tmp:
        store=AccountStore(Path(tmp)/'state.sqlite3');runtime_storage.prepare(store)
        rules=SoulActionRules.load();trules=PetSoulTotalsRules.load();gear=load_ordinary_equipment_attribute_rules()
        role=store.create_role(1111,'元魂实际全结算',12,1010101);rid=role['id'];epoch=store.acquire_lease(1111,rid)
        inv=Inventory(store.leased(1111,rid,epoch),1111,rid)
        context=actions.SoulResourceRules(store.resource_rules,gear)
        with closing(store.connect()) as db:
            souls.prepare(db);orbs.prepare(db);mingwen.prepare(db);actions.prepare(db)
        def root_sync(db,inventory,*,replayed,request_id):
            return synchronize_inventory_resource_source(db,1111,rid,inventory.epoch,inventory.immutable_snapshot_transaction(db),
                request_id,equipment_rules=gear,resource_rules=store.resource_rules,replayed=replayed)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');db.execute('UPDATE roles SET level=5 WHERE id=?',(rid,))
            db.execute('INSERT INTO role_progress VALUES(?,0)',(rid,))
            growth=initialize_growth(db,1111,rid,epoch,store.growth_rules,expected_level=5,free_points=0)
            old=initialize_attribute_baseline(db,1111,rid,epoch,AttributeBaseline(rid,5,0,(10,)*5,
                (100,100,20,10,50,10,10,20,10)),growth,store.attribute_rules,VitalState(rid,0,70,100,40,100)).vitals
            initialize_equipment_attribute_basis(db,1111,rid,epoch,EquipmentAttributeBasis(rid,1,0,gear.revision,0,
                'known-final-soul-role',seal_resistance=0),gear)
            rtotals=current_equipment_totals(db,1111,rid,epoch,inv.immutable_snapshot_transaction(db),gear)
            migrate_role_resources(db,1111,rid,epoch,old,resource_caps_from_projection(rtotals),origin='explicit_migration',
                migration_id='known-final-soul-role',rules=store.resource_rules,equipment_rules=gear)
            initialize_wallet(db,1111,rid,epoch,(1000,0,0,0),'explicit_migration',store.currency_rules)
        pet=inv.grant_pet(500001);inv.fight_pet(pet);inv.grant_item(31286);inv.grant_item(38045,3,binding=1)
        item=next(i for i in inv.immutable_snapshot().items if i.template_id==31286)
        tool=next(i for i in inv.immutable_snapshot().items if i.template_id==38045)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            inv.change_pet_growth(db,pet,'known-pet-L1',0,'experience',50)
            inv.change_pet_growth(db,pet,'known-pet-damage',1,'resources',(80,30))
            souls.initialize(db,inv,rules.orbs.souls,SoulProfile(rid,pet,0,rules.orbs.souls.revision,'known-final-empty',()),'explicit_known_pet_souls')
            orbs.initialize(db,inv,rules.orbs,OrbSource(rid,item.id,31286,0,rules.orbs.revision,
                'known-final-solar',OrbTips(0,0,0,0),0,None),'explicit_known_orb_instance')
            mingwen.initialize(db,inv,trules.mingwen,mingwen.MingwenState(rid,0,trules.mingwen.revision,
                'known-final-inscriptions',tuple(mingwen.MingwenEntry(i,0,0,0) for i in range(1,23))),'explicit_known_mingwen_ledger')
            extra=PetSoulExtraBasis(rid,pet,trules.revision,'known-final-seven-extras',
                ((110,100,1),(120,80,1),(740,-1,10),(1550,1,100),(1560,0,1),(1580,0,1),(1590,0,1)))
            totals.initialize(db,inv,trules,extra,'explicit_known_pet_soul_extras')
        config=replace(store.inventory_config,growth_rules=replace(store.inventory_config.growth_rules,totals_rules=trules))
        inv=Inventory(store.leased(1111,rid,epoch),1111,rid,config)
        # Current world/operation and full material flags are explicit external
        # fixtures; actual Mingwen and all assets/resources are real stores.
        flags={tool.id:0}
        def external(db,inventory,pet_id,keys):
            return authority.SoulOperationClearance(rid,pet_id,inventory.epoch,'explicit-final-world-fixture',1,True,
                tuple((key,flags[key]) for key in keys))
        def reader(db,inventory,pet_id,keys):
            return authority.resolve(db,inventory,trules.mingwen,pet_id,keys,clearance_reader=external)
        def capture(request,kind,body):
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE');root_sync(db,inv,replayed=False,request_id='capture:'+request)
                before=totals.read_profile(db,inv,trules,pet)
                command=actions.admit(db,inv,rules,request,kind,body,deadline_ms=1000,clock_ms=lambda:100,authority_reader=reader)
                return before,command
        def perform(before,command,*,late_failure=False,readonly=False):
            def finalize(db,inventory,snapshot,*,replayed,request_id):
                if replayed:totals.read_profile(db,inventory,trules,pet)
                else:totals.settle_source(db,inventory,trules,before,'pet:'+request_id)
                root_sync(db,inventory,replayed=replayed,request_id=request_id)
            with closing(store.connect()) as db,db:
                db.execute('BEGIN' if readonly else 'BEGIN IMMEDIATE')
                if readonly:db.set_authorizer(lambda action,*args:sqlite3.SQLITE_DENY if action in
                    (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE) else sqlite3.SQLITE_OK)
                result=actions.apply(db,inv,rules,store.currency_rules,command,resource_context=context,
                    clock_ms=lambda:100,authority_reader=reader,precommit=finalize)
                snapshot=inv.immutable_snapshot_transaction(db)
                record=pet_record(vars(snapshot.pets[0]));probe(0xf9d7b0,0xf9d840,0xf9d880,payload=record)
                if late_failure:raise RuntimeError('late final pet native failure')
                return result,totals.read_profile(db,inv,trules,pet)
        def current():
            with closing(store.connect()) as db:
                db.execute('BEGIN');snapshot=inv.immutable_snapshot_transaction(db)
                orb_sources=tuple(orbs.read(db,inv,rules.orbs,i.id) for i in snapshot.items if i.template_id in rules.orbs.souls.souls)
                return (snapshot,totals.read_profile(db,inv,trules,pet),souls.read(db,inv,rules.orbs.souls,pet),
                    orb_sources,read_role_resources(db,1111,rid,epoch,store.resource_rules),read_wallet(db,1111,rid,epoch,store.currency_rules))
        def faults(before,command,tables):
            baseline=current()
            for table,operation in tables:
                with closing(store.connect()) as db,db:
                    db.execute(f"CREATE TRIGGER final_soul_fault BEFORE {operation} ON {table} BEGIN SELECT RAISE(ABORT,'final-soul-fault'); END")
                try:perform(before,command)
                except sqlite3.IntegrityError as error:assert 'final-soul-fault' in str(error)
                else:raise AssertionError('Actual final pet SQL fault did not execute '+table)
                finally:
                    with closing(store.connect()) as db,db:db.execute('DROP TRIGGER final_soul_fault')
                assert current()==baseline,table
            try:perform(before,command,late_failure=True)
            except RuntimeError as error:assert str(error)=='late final pet native failure'
            else:raise AssertionError('Late native fault did not execute')
            assert current()==baseline
        before,wear=capture('final-wear',0xc03ff,struct.pack('>iiq',item.id,1,pet))
        faults(before,wear,(('inventory_pet_soul_totals','UPDATE'),('inventory_pet_soul_resource_receipts','INSERT'),('role_resource_profiles','UPDATE')))
        worn,full=perform(before,wear)
        assert not worn.replayed and all(i.id!=item.id for i in worn.snapshot.items)
        assert (full.progress.state.hp,full.progress.state.mp,full.progress.attributes.max_hp)==(80,30,202)
        assert (worn.resources.hp,worn.resources.mp,worn.resources.caps.hp_max)==(70,40,100)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');healed=totals.change_resources(db,inv,trules,full,'known-real-pet-medicine',(195,30),cause='medicine')
            root_sync(db,inv,replayed=False,request_id='known-real-pet-medicine')
        before_remove,remove=capture('final-remove',0xc0805,struct.pack('>ii',pet,1))
        faults(before_remove,remove,(('inventory_pet_growth','UPDATE'),('inventory_pet_soul_totals','UPDATE'),
            ('inventory_pet_soul_resource_receipts','INSERT'),('role_resource_profiles','UPDATE')))
        removed,clipped=perform(before_remove,remove)
        assert not removed.replayed and removed.basis.profile.entries==()
        assert (clipped.progress.state.hp,clipped.progress.state.mp,clipped.progress.attributes.max_hp)==(157,30,157)
        assert next(i.quantity for i in removed.snapshot.items if i.id==tool.id)==1
        with closing(store.connect()) as db:
            db.execute('BEGIN');returned=orbs.read(db,inv,rules.orbs,removed.returned_item_key)
            assert returned.source.tips==OrbTips(0,0,0,0) and returned.source.retained_raw6==0
        # Historical medicine cannot heal above the later removed cap.
        with closing(store.connect()) as db:
            db.execute('BEGIN');db.set_authorizer(lambda action,*args:sqlite3.SQLITE_DENY if action in
                (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE) else sqlite3.SQLITE_OK)
            paid=totals.change_resources(db,inv,trules,full,'known-real-pet-medicine',(195,30),cause='medicine')
            assert (paid.progress.state.hp,paid.progress.attributes.max_hp)==(157,157)
            paid_source=totals.settle_source(db,inv,trules,before,'pet:final-wear')
            assert (paid_source.progress.state.hp,paid_source.progress.attributes.max_hp)==(157,157)
        old_paid,live=perform(before,wear,readonly=True)
        assert old_paid.replayed and (live.progress.state.hp,live.progress.attributes.max_hp)==(157,157)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');dead=totals.change_resources(db,inv,trules,live,'known-pet-terminal-combat',(0,20),cause='combat')
            root_sync(db,inv,replayed=False,request_id='known-pet-terminal-combat')
        before_rewear,rewear=capture('final-dead-rewear',0xc03ff,struct.pack('>iiq',returned.item.id,1,pet))
        dead_result,dead_worn=perform(before_rewear,rewear)
        assert (dead_worn.progress.state.hp,dead_worn.progress.state.mp,dead_worn.progress.attributes.max_hp)==(0,20,202)
        baseline=current()
        try:
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE');totals.change_resources(db,inv,trules,dead_worn,'forbidden-pet-revive',(10,20),cause='medicine')
        except ValueError:pass
        else:raise AssertionError('Ordinary pet medicine revived a dead pet')
        assert current()==baseline
        epoch2=store.acquire_lease(1111,rid)
        current_inv=Inventory(store.leased(1111,rid,epoch2),1111,rid,config)
        with closing(store.connect()) as db:
            db.execute('BEGIN');db.set_authorizer(lambda action,*args:sqlite3.SQLITE_DENY if action in
                (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE) else sqlite3.SQLITE_OK)
            paid=totals.settle_source(db,current_inv,trules,before,'pet:final-wear')
            assert (paid.progress.state.hp,paid.progress.attributes.max_hp)==(0,202)
            try:totals.settle_source(db,current_inv,trules,dead_worn,'old-lease-new-source')
            except ValueError as error:assert 'stale' in str(error)
            else:raise AssertionError('Old-lease new resource mutation accepted')
        print('PASS actual soul wear/debit→202 cap/no heal, real sole-state medicine195, remove2 tools/unique return→157 cap/HP clip, '
            'old paid SQL readonly/current-only/no re-heal, death0→wear no revive;7 SQL+2 native faults full rollback; '
            'old-epoch paid current/unpaid stale; human70/40/100 unchanged; external clearance fixture')


if __name__=='__main__':main()
