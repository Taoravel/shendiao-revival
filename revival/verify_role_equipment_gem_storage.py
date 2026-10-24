"""Actual root HP/MP carrier consumes complete current worn gem totals."""
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
from role_growth import initialize_growth,read_growth
from role_equipment import EquipmentAttributeBasis,resource_caps_from_projection
from role_equipment_storage import initialize_equipment_attribute_basis
from role_resource_storage import migrate_role_resources,read_role_resources,apply_resource_transition
from role_resource_plan import plan_resource_values,plan_combat_resources
from currency import initialize_wallet
from role_equipment_gems import GemEquipmentRules,GemExtraBasis
from equipment_gems import GemState,embed
from equipment_gem_score import GemScoreBasis,project
import equipment_gem_storage as sockets
import equipment_gem_score_storage as scores
import equipment_gem_presentation as presentation
import role_equipment_gem_storage as role_gems
from role_equipment_gem_protocol import growth_refresh
import runtime_storage


def main():
    with TemporaryDirectory(prefix='gem-root-resources-') as tmp:
        store=AccountStore(Path(tmp)/'state.sqlite3');runtime_storage.prepare(store)
        rules=GemEquipmentRules.load();resource_rules=store.resource_rules
        with closing(store.connect()) as db:
            sockets.prepare(db);scores.prepare(db);role_gems.prepare(db)
        shape=next(shape for shape,char in rules.carrier_rules.shape_characters.items() if char==2)
        role=store.create_role(1111,'宝石唯一资源',min(store.choices[shape]),shape);rid=role['id'];epoch=store.acquire_lease(1111,rid)
        inv=Inventory(store.leased(1111,rid,epoch),1111,rid)
        with closing(inv.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('UPDATE roles SET level=10 WHERE id=?',(rid,))
            db.execute('INSERT INTO role_progress VALUES(?,0)',(rid,))
            growth=initialize_growth(db,1111,rid,epoch,store.growth_rules,expected_level=10,free_points=0)
            old=initialize_attribute_baseline(db,1111,rid,epoch,
                AttributeBaseline(rid,10,0,(10,10,10,10,10),(100,100,20,10,50,10,10,20,10)),
                growth,store.attribute_rules,VitalState(rid,0,70,100,40,100)).vitals
            basis=EquipmentAttributeBasis(rid,2,0,rules.revision,0,'explicit-known-gem-role',seal_resistance=0)
            initialize_equipment_attribute_basis(db,1111,rid,epoch,basis,rules.carrier_rules)
            extra=GemExtraBasis(rid,0,rules.revision,basis.source_id,((350,0),(360,0),(370,0),(380,0),(1130,0),(1530,0)))
            assert role_gems.read_extra(db,inv,rules) is None
            try:role_gems.read_totals(db,inv,rules)
            except ValueError:pass
            else:raise AssertionError('Missing extras silently became zero')
            role_gems.initialize_extra(db,inv,rules,extra,'explicit_known_ungemmed_extras')
            totals=role_gems.read_totals(db,inv,rules)
            migrate_role_resources(db,1111,rid,epoch,old,resource_caps_from_projection(totals.core),
                origin='explicit_migration',migration_id='complete-known-gem-fixture',rules=resource_rules,equipment_rules=rules.carrier_rules)
            initialize_wallet(db,1111,rid,epoch,(10000,0,0,0),'explicit_migration',store.currency_rules)
        inv.grant_item(45001);inv.grant_item(35005,2)
        with closing(inv.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            belt=next(i for i in inv.immutable_snapshot_transaction(db).items if i.template_id==45001)
            sockets.initialize(db,inv,rules.gem_rules,belt.id,GemState(0,(),rules.gem_rules.revision),0,'explicit_known_socket_profile')
            score_basis=GemScoreBasis(rid,belt.id,rules.score_rules.revision,0,'known-belt-before-gems')
            scores.initialize(db,inv,rules.score_rules,rules.gem_rules,score_basis,'explicit_known_pre_gem_score')
            role_gems.synchronize_inventory_source(db,inv,rules,resource_rules,'known-gem-fixture',replayed=False)
            before=read_role_resources(db,1111,rid,epoch,resource_rules)
            inv.equip_transaction(db,belt.id,4,epoch,'known-wear-belt')
            equipped=role_gems.settle_equipment(db,inv,rules,resource_rules,before,'known-wear-belt')
            assert (equipped.core.vitals.hp,equipped.core.vitals.max_hp,equipped.core.vitals.mp)==(70,148,40)
        with closing(inv.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            resources_before=read_role_resources(db,1111,rid,epoch,resource_rules)
            before=sockets.read(db,inv,rules.gem_rules,belt.id)
            material=next(i for i in inv.immutable_snapshot_transaction(db).items if i.template_id==35005)
            plan=embed(rules.gem_rules,before.item,before.state,material,0,flags=(0,0))
            score_change=project(rules.score_rules,rules.gem_rules,before.item,before.state,plan.after,score_basis)
            saved=sockets.replace_state(db,inv,rules.gem_rules,before,plan.after)
            presentation.apply(db,inv,rules.gem_rules,rules.score_rules,before,saved,score_change)
            result=role_gems.settle_equipment(db,inv,rules,resource_rules,resources_before,'known-worn-green-gem')
            assert (result.core.vitals.hp,result.core.vitals.max_hp,result.core.vitals.mp,result.core.vitals.max_mp)==(70,203,40,100)
        with closing(store.connect()) as db:
            db.execute('BEGIN');assert role_gems.read_profile(db,inv,rules,resource_rules).core.vitals==result.core.vitals
        def refused(action):
            try:action()
            except ValueError:return
            raise AssertionError('Unsafe gem resource operation accepted')
        def state():
            with closing(store.connect()) as db:
                db.execute('BEGIN')
                return (inv.immutable_snapshot_transaction(db),role_gems.read_profile(db,inv,rules,resource_rules),
                    role_gems.read_extra(db,inv,rules))
        saved_state=state()
        # Exact extra initialization and paid source retry must be SQL read-only.
        with closing(store.connect()) as db:
            db.execute('BEGIN')
            writes=[]
            def readonly(action,*args):
                if action in (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE):
                    writes.append(args);return sqlite3.SQLITE_DENY
                return sqlite3.SQLITE_OK
            db.set_authorizer(readonly)
            assert role_gems.initialize_extra(db,inv,rules,extra,'explicit_known_ungemmed_extras')==extra
            role_gems.synchronize_inventory_source(db,inv,rules,resource_rules,'known-worn-green-gem',replayed=True)
            assert role_gems.read_profile(db,inv,rules,resource_rules)==saved_state[1]
            refused(lambda:role_gems.initialize_extra(db,inv,rules,replace(extra,source_ref='guessed'),
                'explicit_known_ungemmed_extras'))
            assert writes==[]
        # SQL faults AFTER a real durability mutation roll all asset/resource
        # writes back. State is observed through the same public Interfaces.
        for table,operation in (('role_attribute_snapshots','UPDATE'),('role_resource_profiles','UPDATE'),
                                ('role_resource_receipts','INSERT')):
            with closing(store.connect()) as db:
                db.execute(f"CREATE TRIGGER gem_resource_fault BEFORE {operation} ON {table} BEGIN SELECT RAISE(ABORT,'gem-resource-fault'); END")
                db.commit()
            try:
                with closing(store.connect()) as db,db:
                    db.execute('BEGIN IMMEDIATE')
                    resources=read_role_resources(db,1111,rid,epoch,resource_rules)
                    condition=inv.equipment_condition(db,belt.id)
                    inv.wear_equipment(db,belt.id,'fault-'+table,condition.version,condition.current)
                    role_gems.settle_equipment(db,inv,rules,resource_rules,resources,'fault-'+table)
            except sqlite3.IntegrityError as error:assert 'gem-resource-fault' in str(error)
            else:raise AssertionError('Expected actual resource SQL fault')
            finally:
                with closing(store.connect()) as db:
                    db.execute('DROP TRIGGER gem_resource_fault');db.commit()
            assert state()==saved_state
        # Caller failure after final projection likewise rolls back all writes.
        try:
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                resources=read_role_resources(db,1111,rid,epoch,resource_rules)
                condition=inv.equipment_condition(db,belt.id)
                inv.wear_equipment(db,belt.id,'late-encode',condition.version,condition.current)
                refused(lambda:role_gems.read_profile(db,inv,rules,resource_rules))
                refused(lambda:role_gems.synchronize_inventory_source(db,inv,rules,resource_rules,'paid',replayed=True))
                late=role_gems.settle_equipment(db,inv,rules,resource_rules,resources,'late-encode')
                assert growth_refresh(read_growth(db,1111,rid),late)[0]==0xc32c8
                raise ValueError('controlled caller encoding failure')
        except ValueError as error:assert str(error)=='controlled caller encoding failure'
        assert state()==saved_state
        # Explicit trusted medicine fixture, then break and repair the actual
        # gemmed belt. This is a resource test, not medicine/repair UI admission.
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');resources=read_role_resources(db,1111,rid,epoch,resource_rules)
            apply_resource_transition(db,1111,rid,epoch,plan_resource_values(resources,180,40,'medicine',resource_rules),
                'known-test-medicine',rules=resource_rules,equipment_rules=rules.carrier_rules)
            resources=read_role_resources(db,1111,rid,epoch,resource_rules)
            condition=inv.equipment_condition(db,belt.id)
            inv.wear_equipment(db,belt.id,'break-gem-belt',condition.version,condition.current)
            broken=role_gems.settle_equipment(db,inv,rules,resource_rules,resources,'break-gem-belt')
            assert (broken.core.vitals.hp,broken.core.vitals.max_hp)==(100,100)
            assert sockets.read(db,inv,rules.gem_rules,belt.id).state.templates==(35005,)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');resources=read_role_resources(db,1111,rid,epoch,resource_rules)
            condition=inv.equipment_condition(db,belt.id)
            inv.repair_equipment(db,belt.id,epoch,'repair-gem-belt',condition.version,0,store.currency_rules)
            repaired=role_gems.settle_equipment(db,inv,rules,resource_rules,resources,'repair-gem-belt')
            assert (repaired.core.vitals.hp,repaired.core.vitals.max_hp)==(100,203)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');resources=read_role_resources(db,1111,rid,epoch,resource_rules)
            apply_resource_transition(db,1111,rid,epoch,plan_combat_resources(resources,0,30,resource_rules),
                'known-test-death',rules=resource_rules,equipment_rules=rules.carrier_rules)
            resources=read_role_resources(db,1111,rid,epoch,resource_rules)
            inv.unequip_transaction(db,belt.id,0,epoch,'dead-unequip')
            dead=role_gems.settle_equipment(db,inv,rules,resource_rules,resources,'dead-unequip')
            assert (dead.core.vitals.hp,dead.core.vitals.max_hp,dead.core.vitals.mp)==(0,100,30)
            resources=read_role_resources(db,1111,rid,epoch,resource_rules)
            inv.equip_transaction(db,belt.id,4,epoch,'dead-equip')
            dead=role_gems.settle_equipment(db,inv,rules,resource_rules,resources,'dead-equip')
            assert (dead.core.vitals.hp,dead.core.vitals.max_hp,dead.core.vitals.mp)==(0,203,30)
        new_epoch=store.acquire_lease(1111,rid)
        with closing(store.connect()) as db:
            db.execute('BEGIN');refused(lambda:role_gems.read_profile(db,inv,rules,resource_rules))
            current=Inventory(store.leased(1111,rid,new_epoch),1111,rid)
            assert role_gems.read_profile(db,current,rules,resource_rules).core.vitals==dead.core.vitals
        print('PASS actual sole root carrier: HP caps100/148/203; no healing; downward clip; death preserved; '
            '3 SQL faults and late caller rollback; strict paid readonly; stale lease refusal')


if __name__=='__main__':main()
