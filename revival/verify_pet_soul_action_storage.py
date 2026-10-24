"""Actual soul wear joins Inventory/map/source/resource/receipt in one role Tx."""
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from fractions import Fraction
from dataclasses import replace
import sqlite3
import struct
from accounts import AccountStore
from inventory import Inventory,AssetChange
from currency import initialize_wallet,read_wallet
from item_effects import VitalState
from role_attributes import AttributeBaseline
from role_attribute_storage import initialize_attribute_baseline
from role_growth import initialize_growth
from role_equipment import EquipmentAttributeBasis,load_ordinary_equipment_attribute_rules,resource_caps_from_projection
from role_equipment_storage import (initialize_equipment_attribute_basis,current_equipment_totals,
    current_resource_profile,synchronize_inventory_resource_source)
from role_resource_storage import migrate_role_resources,read_role_resources
from role_resource_storage import apply_resource_transition
from role_resource_plan import plan_resource_values,plan_combat_resources
from pet_souls import SoulProfile,SoulBean
from pet_soul_item_storage import OrbSource
from pet_soul_item_data import OrbTips
from pet_soul_actions import SoulActionRules,SoulActionAuthority
import pet_soul_storage as souls
import pet_soul_item_storage as orbs
import pet_soul_action_storage as actions
import runtime_storage
from native_gameplay_probe import probe


def main():
    with TemporaryDirectory(prefix='soul-real-action-') as tmp:
        store=AccountStore(Path(tmp)/'state.sqlite3');runtime_storage.prepare(store)
        rules=SoulActionRules.load();gear=load_ordinary_equipment_attribute_rules()
        resource_context=actions.SoulResourceRules(store.resource_rules,gear)
        time_state=[100]
        clock=lambda:time_state[0]
        with closing(store.connect()) as db:
            souls.prepare(db);orbs.prepare(db);actions.prepare(db)
            # Explicit external-owner test fixture, not real world/privilege
            # integration or a mock of any implementation under test.
            db.execute('CREATE TABLE test_soul_clearance(role_id INTEGER PRIMARY KEY,version INTEGER,allowed INTEGER,flag22 INTEGER)')
            db.execute('CREATE TABLE test_soul_material_flags(role_id INTEGER,item_key INTEGER,flags INTEGER,PRIMARY KEY(role_id,item_key))')
        role=store.create_role(1111,'元魂实际穿戴',12,1010101);rid=role['id'];epoch=store.acquire_lease(1111,rid)
        inv=Inventory(store.leased(1111,rid,epoch),1111,rid)
        def sync(db,inventory,snapshot,*,replayed,request_id):
            return synchronize_inventory_resource_source(db,1111,rid,inventory.epoch,snapshot,request_id,
                equipment_rules=gear,resource_rules=store.resource_rules,replayed=replayed)
        def authority(db,inventory,pet_id,material_keys):
            row=db.execute('SELECT version,allowed,flag22 FROM test_soul_clearance WHERE role_id=?',(inventory.role_id,)).fetchone()
            if row is None or row[1] not in (0,1):raise ValueError('Unknown fixture clearance')
            flags=tuple((key,db.execute('SELECT flags FROM test_soul_material_flags WHERE role_id=? AND item_key=?',
                (inventory.role_id,key)).fetchone()) for key in material_keys)
            if any(value is None for _,value in flags):raise ValueError('Unknown fixture material flags')
            return SoulActionAuthority(inventory.role_id,pet_id,inventory.epoch,'explicit-fixture-soul-context',
                row[0],row[1]==1,row[2],tuple((key,value[0]) for key,value in flags))
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');db.execute('INSERT INTO role_progress VALUES(?,0)',(rid,))
            growth=initialize_growth(db,1111,rid,epoch,store.growth_rules,expected_level=1,free_points=0)
            old=initialize_attribute_baseline(db,1111,rid,epoch,
                AttributeBaseline(rid,1,0,(10,)*5,(100,100,20,10,50,10,10,20,10)),growth,
                store.attribute_rules,VitalState(rid,0,70,100,40,100)).vitals
            initialize_equipment_attribute_basis(db,1111,rid,epoch,
                EquipmentAttributeBasis(rid,1,0,gear.revision,0,'known-soul-action-role',seal_resistance=0),gear)
            totals=current_equipment_totals(db,1111,rid,epoch,inv.immutable_snapshot_transaction(db),gear)
            migrate_role_resources(db,1111,rid,epoch,old,resource_caps_from_projection(totals),origin='explicit_migration',
                migration_id='known-soul-action-role',rules=store.resource_rules,equipment_rules=gear)
            initialize_wallet(db,1111,rid,epoch,(1000,0,0,0),'explicit_migration',store.currency_rules)
            db.execute('INSERT INTO test_soul_clearance VALUES(?,1,1,0)',(rid,))
        pet=inv.grant_pet(500001);inv.fight_pet(pet);inv.grant_item(31276,binding=1)
        key=inv.immutable_snapshot().items[0].id
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            souls.initialize(db,inv,rules.orbs.souls,SoulProfile(rid,pet,0,rules.orbs.souls.revision,'known-empty-soul-map',()),'explicit_known_pet_souls')
            orbs.initialize(db,inv,rules.orbs,OrbSource(rid,key,31276,0,rules.orbs.revision,'known-orb-action',
                OrbTips(140,10001,-205,204),0,-2),'explicit_known_orb_instance')
            sync(db,inv,inv.immutable_snapshot_transaction(db),replayed=False,request_id='soul-fixture')
            try:actions.admit(db,inv,rules,'expired-new',0xc03ff,struct.pack('>iiq',key,1,pet),
                authority_reader=authority,deadline_ms=50,clock_ms=lambda:100)
            except ValueError:pass
            else:raise AssertionError('Already expired soul admission accepted')
            command=actions.admit(db,inv,rules,'wear-once',0xc03ff,struct.pack('>iiq',key,1,pet),authority_reader=authority,deadline_ms=1000,clock_ms=clock)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            result=actions.apply(db,inv,rules,store.currency_rules,command,resource_context=resource_context,clock_ms=clock,authority_reader=authority,precommit=sync)
            assert result.replayed is False and result.operation=='wear' and result.slot==1
            assert result.basis.profile.entries==((1,SoulBean(31276,140,10001,204,-205,-2)),)
            assert result.effects==((1,31276,3,2,81,1,Fraction(32)),)
            assert all(item.id!=key for item in result.snapshot.items)
            role_profile=current_resource_profile(db,1111,rid,epoch,result.snapshot,equipment_rules=gear,resource_rules=store.resource_rules)
            assert (role_profile.vitals.hp,role_profile.vitals.mp,role_profile.vitals.max_hp)==(70,40,100)
            assert read_wallet(db,1111,rid,epoch,store.currency_rules)[0].balance==1000
            assert tuple(kind for kind,_ in result.messages)==(0xc03f3,0xc0803)
        with closing(store.connect()) as db,db:
            db.execute('UPDATE test_soul_clearance SET version=2,allowed=0,flag22=1 WHERE role_id=?',(rid,))
        def forbidden_paid_clock():
            raise AssertionError('A committed payment must not recheck its historical deadline')
        with closing(store.connect()) as db:
            db.execute('BEGIN')
            db.set_authorizer(lambda action,*args:sqlite3.SQLITE_DENY if action in
                (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE) else sqlite3.SQLITE_OK)
            replay=actions.apply(db,inv,rules,store.currency_rules,command,resource_context=resource_context,clock_ms=forbidden_paid_clock,authority_reader=authority,precommit=sync)
            assert replay.replayed is True and replay.basis.profile==result.basis.profile
            assert replay.effects==((1,31276,3,3,81,1,Fraction(62)),)
            assert replay.authority.version==2 and replay.authority.allowed is False
        inv.grant_item(38045,1,binding=1);inv.grant_item(38045,6)
        tools=tuple(i for i in inv.immutable_snapshot().items if i.template_id==38045)
        bound=next(i.id for i in tools if i.binding==1);unbound=next(i.id for i in tools if i.binding==0)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('UPDATE test_soul_clearance SET version=3,allowed=1,flag22=1 WHERE role_id=?',(rid,))
            db.executemany('INSERT INTO test_soul_material_flags VALUES(?,?,0)',((rid,i.id) for i in tools))
            sync(db,inv,inv.immutable_snapshot_transaction(db),replayed=False,request_id='known-removal-tools')
            remove=actions.admit(db,inv,rules,'remove-once',0xc0805,struct.pack('>ii',pet,1),authority_reader=authority,deadline_ms=1000,clock_ms=clock)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            removed=actions.apply(db,inv,rules,store.currency_rules,remove,resource_context=resource_context,clock_ms=clock,authority_reader=authority,precommit=sync)
            assert removed.operation=='remove' and removed.replayed is False and removed.basis.profile.entries==()
            assert all(i.id!=bound for i in removed.snapshot.items)
            assert next(i.quantity for i in removed.snapshot.items if i.id==unbound)==3
            returned=orbs.read(db,inv,rules.orbs,removed.returned_item_key)
            assert returned.item.binding==1 and returned.source.tips==OrbTips(140,10001,-205,204)
            assert returned.source.nonbinding_flags==0 and returned.source.retained_raw6==-2
            assert returned.item.id!=key and returned.item.template_id==31276 and returned.item.quantity==1
            assert tuple(kind for kind,_ in removed.messages)==(0xc03f3,0xc03fe,0xc0803)
            assert read_wallet(db,1111,rid,epoch,store.currency_rules)[0].balance==1000
        with closing(store.connect()) as db:
            db.execute('BEGIN');db.set_authorizer(lambda action,*args:sqlite3.SQLITE_DENY if action in
                (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE) else sqlite3.SQLITE_OK)
            paid_remove=actions.apply(db,inv,rules,store.currency_rules,remove,resource_context=resource_context,clock_ms=clock,authority_reader=authority,precommit=sync)
            assert paid_remove.replayed and paid_remove.returned_item_key==returned.item.id
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            wear_again=actions.admit(db,inv,rules,'wear-returned',0xc03ff,
                struct.pack('>iiq',returned.item.id,1,pet),authority_reader=authority,deadline_ms=1000,clock_ms=clock)
            reworn=actions.apply(db,inv,rules,store.currency_rules,wear_again,resource_context=resource_context,clock_ms=clock,authority_reader=authority,precommit=sync)
            assert reworn.basis.profile.entries==((1,SoulBean(31276,140,10001,204,-205,-2)),)
            assert all(i.id!=returned.item.id for i in reworn.snapshot.items)
        with closing(store.connect()) as db:
            db.execute('BEGIN');db.set_authorizer(lambda action,*args:sqlite3.SQLITE_DENY if action in
                (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE) else sqlite3.SQLITE_OK)
            late_remove=actions.apply(db,inv,rules,store.currency_rules,remove,resource_context=resource_context,clock_ms=clock,authority_reader=authority,precommit=sync)
            assert late_remove.replayed and late_remove.basis.profile==reworn.basis.profile
            assert all(i.id!=returned.item.id for i in late_remove.snapshot.items)
        def refused(action):
            try:action()
            except ValueError:return
            raise AssertionError('Unsafe or incomplete soul action accepted')
        # Second known orb for real write-fault/cancellation tests. Existing
        # basic/advanced templates are distinct under the explicit ID policy.
        inv.grant_item(31277)
        advanced=next(i for i in inv.immutable_snapshot().items if i.template_id==31277)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            orbs.initialize(db,inv,rules.orbs,OrbSource(rid,advanced.id,31277,0,rules.orbs.revision,
                'known-advanced-orb',OrbTips(120,0,327,-328),0,None),'explicit_known_orb_instance')
            sync(db,inv,inv.immutable_snapshot_transaction(db),replayed=False,request_id='known-advanced-fixture')
            fault_command=actions.admit(db,inv,rules,'wear-faults',0xc03ff,
                struct.pack('>iiq',advanced.id,1,pet),authority_reader=authority,deadline_ms=1000,clock_ms=clock)
        def state():
            with closing(store.connect()) as db:
                db.execute('BEGIN');snapshot=inv.immutable_snapshot_transaction(db)
                return (snapshot,souls.read(db,inv,rules.orbs.souls,pet),
                    current_resource_profile(db,1111,rid,inv.epoch,snapshot,equipment_rules=gear,resource_rules=store.resource_rules),
                    read_wallet(db,1111,rid,inv.epoch,store.currency_rules))
        before_faults=state()
        time_state[0]=2000
        try:
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                actions.apply(db,inv,rules,store.currency_rules,fault_command,
                    resource_context=resource_context,clock_ms=clock,authority_reader=authority,precommit=sync)
        except ValueError as error:assert 'deadline' in str(error)
        else:raise AssertionError('Expired unpaid command committed')
        finally:time_state[0]=100
        assert state()==before_faults
        def expiring_finalizer(db,inventory,snapshot,*,replayed,request_id):
            sync(db,inventory,snapshot,replayed=replayed,request_id=request_id)
            time_state[0]=2000
        try:
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                actions.apply(db,inv,rules,store.currency_rules,fault_command,
                    resource_context=resource_context,clock_ms=clock,authority_reader=authority,precommit=expiring_finalizer)
        except ValueError as error:assert 'deadline' in str(error)
        else:raise AssertionError('Deadline expiry after real source writes committed')
        finally:time_state[0]=100
        assert state()==before_faults
        try:
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                actions.apply(db,inv,rules,store.currency_rules,fault_command,
                    resource_context=resource_context,clock_ms=clock,authority_reader=authority,precommit=lambda *args,**kwargs:None)
        except ValueError:pass
        else:raise AssertionError('No-op finalizer allowed a pending source to commit')
        assert state()==before_faults
        async def invalid_async_result():return None
        try:
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                actions.apply(db,inv,rules,store.currency_rules,fault_command,resource_context=resource_context,clock_ms=clock,
                    authority_reader=authority,precommit=lambda *args,**kwargs:invalid_async_result())
        except ValueError as error:assert 'synchronously' in str(error)
        else:raise AssertionError('Awaitable finalizer escaped caller transaction')
        assert state()==before_faults
        def healing_finalizer(db,inventory,snapshot,*,replayed,request_id):
            sync(db,inventory,snapshot,replayed=replayed,request_id=request_id)
            current=read_role_resources(db,1111,rid,inventory.epoch,store.resource_rules)
            transition=plan_resource_values(current,100,100,'medicine',store.resource_rules)
            apply_resource_transition(db,1111,rid,inventory.epoch,transition,'forbidden-soul-heal',
                rules=store.resource_rules,equipment_rules=gear)
        try:
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                actions.apply(db,inv,rules,store.currency_rules,fault_command,resource_context=resource_context,clock_ms=clock,
                    authority_reader=authority,precommit=healing_finalizer)
        except ValueError as error:assert 'human resources' in str(error)
        else:raise AssertionError('Soul finalizer silently healed human resources')
        assert state()==before_faults
        failures=(('inventory_pet_souls','UPDATE',''),('inventory_versions','UPDATE',''),
            ('inventory_items','DELETE',f'WHEN OLD.id={advanced.id}'),('inventory_settlements','INSERT',''),
            ('pet_soul_action_receipts','INSERT',''),('role_attribute_snapshots','UPDATE',''),
            ('role_resource_profiles','UPDATE',''),('role_resource_receipts','INSERT',''))
        for table,operation,condition in failures:
            with closing(store.connect()) as db:
                db.execute(f"CREATE TRIGGER soul_action_fault BEFORE {operation} ON {table} {condition} BEGIN SELECT RAISE(ABORT,'soul-action-fault'); END");db.commit()
            try:
                with closing(store.connect()) as db,db:
                    db.execute('BEGIN IMMEDIATE');actions.apply(db,inv,rules,store.currency_rules,fault_command,
                        resource_context=resource_context,clock_ms=clock,authority_reader=authority,precommit=sync)
            except sqlite3.IntegrityError as error:assert 'soul-action-fault' in str(error)
            else:raise AssertionError('Expected actual soul action SQL fault at '+table)
            finally:
                with closing(store.connect()) as db:db.execute('DROP TRIGGER soul_action_fault');db.commit()
            assert state()==before_faults,table
        try:
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                staged=actions.apply(db,inv,rules,store.currency_rules,fault_command,resource_context=resource_context,clock_ms=clock,authority_reader=authority,precommit=sync)
                for kind,body in staged.messages:
                    if kind==0xc03f3:probe(0xef6220,0xef62d0,0xef6350,payload=body)
                    elif kind==0xc0803:probe(0xf9df90,0xf9e0b0,0xf9e140,payload=body)
                raise ValueError('controlled failure after complete native action encoding')
        except ValueError as error:assert str(error)=='controlled failure after complete native action encoding'
        assert state()==before_faults
        with closing(store.connect()) as db:
            db.execute('BEGIN')
            for kind,body in ((0xc0804,bytes(16)),(0xc03ff,struct.pack('>iiq',advanced.id,2,pet)),
                    (0xc03ff,struct.pack('>iiq',advanced.id,1,pet)+b'\0'),(0xc0805,struct.pack('>ii',pet,0))):
                refused(lambda kind=kind,body=body:actions.admit(db,inv,rules,'bad-wire',kind,body,authority_reader=authority,deadline_ms=1000,clock_ms=clock))
            conflicting=replace(command,orb=replace(command.orb,source=replace(command.orb.source,retained_raw6=1)))
            refused(lambda:actions.apply(db,inv,rules,store.currency_rules,conflicting,resource_context=resource_context,clock_ms=clock,authority_reader=authority,precommit=sync))
        # Old admitted commands cannot pay after lease replacement; historical
        # paid commands still return CURRENT state under the new valid lease.
        epoch=store.acquire_lease(1111,rid);inv=Inventory(store.leased(1111,rid,epoch),1111,rid)
        with closing(store.connect()) as db:
            db.execute('BEGIN')
            refused(lambda:actions.apply(db,inv,rules,store.currency_rules,fault_command,resource_context=resource_context,clock_ms=clock,authority_reader=authority,precommit=sync))
        assert state()==before_faults
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            final_command=actions.admit(db,inv,rules,'advanced-after-lease',0xc03ff,
                struct.pack('>iiq',advanced.id,1,pet),authority_reader=authority,deadline_ms=1000,clock_ms=clock)
            final=actions.apply(db,inv,rules,store.currency_rules,final_command,resource_context=resource_context,clock_ms=clock,authority_reader=authority,precommit=sync)
            assert not final.replayed and tuple(slot for slot,_ in final.basis.profile.entries)==(1,2)
        with closing(store.connect()) as db:
            db.execute('BEGIN');db.set_authorizer(lambda action,*args:sqlite3.SQLITE_DENY if action in
                (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE) else sqlite3.SQLITE_OK)
            paid_old_epoch=actions.apply(db,inv,rules,store.currency_rules,command,resource_context=resource_context,clock_ms=clock,authority_reader=authority,precommit=sync)
            assert paid_old_epoch.replayed and paid_old_epoch.basis.profile==final.basis.profile
        # A source-only pending change must not be silently repaired by paid.
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');basis=souls.read(db,inv,rules.orbs.souls,pet)
            souls.replace_profile(db,inv,rules.orbs.souls,basis,replace(basis.profile,version=basis.profile.version+1))
        with closing(store.connect()) as db:
            db.execute('BEGIN');pending=read_role_resources(db,1111,rid,epoch,store.resource_rules)
            db.set_authorizer(lambda action,*args:sqlite3.SQLITE_DENY if action in
                (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE) else sqlite3.SQLITE_OK)
            refused(lambda:actions.apply(db,inv,rules,store.currency_rules,command,resource_context=resource_context,clock_ms=clock,authority_reader=authority,precommit=sync))
            assert read_role_resources(db,1111,rid,epoch,store.resource_rules)==pending
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');sync(db,inv,inv.immutable_snapshot_transaction(db),replayed=False,request_id='explicit-pending-source')
            removal_faults=actions.admit(db,inv,rules,'remove-advanced-faults',0xc0805,
                struct.pack('>ii',pet,2),authority_reader=authority,deadline_ms=1000,clock_ms=clock)
        before_remove_faults=state()
        removal_failures=(('inventory_items','DELETE',f'WHEN OLD.id={unbound}'),
            ('inventory_items','INSERT','WHEN NEW.template_id=31277'),('inventory_pet_soul_items','INSERT',''),
            ('inventory_versions','UPDATE',f'WHEN EXISTS(SELECT 1 FROM inventory_pet_soul_items s JOIN inventory_items i ON i.id=s.item_key WHERE i.role_id={rid} AND i.template_id=31277)'),
            ('pet_soul_action_receipts','INSERT',''),('role_resource_receipts','INSERT',''))
        for table,operation,condition in removal_failures:
            with closing(store.connect()) as db:
                db.execute(f"CREATE TRIGGER soul_remove_fault BEFORE {operation} ON {table} {condition} BEGIN SELECT RAISE(ABORT,'soul-remove-fault'); END");db.commit()
            try:
                with closing(store.connect()) as db,db:
                    db.execute('BEGIN IMMEDIATE');actions.apply(db,inv,rules,store.currency_rules,removal_faults,
                        resource_context=resource_context,clock_ms=clock,authority_reader=authority,precommit=sync)
            except sqlite3.IntegrityError as error:assert 'soul-remove-fault' in str(error)
            else:raise AssertionError('Expected actual removal SQL fault at '+table)
            finally:
                with closing(store.connect()) as db:db.execute('DROP TRIGGER soul_remove_fault');db.commit()
            assert state()==before_remove_faults,table
        try:
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE');staged=actions.apply(db,inv,rules,store.currency_rules,removal_faults,
                    resource_context=resource_context,clock_ms=clock,authority_reader=authority,precommit=sync)
                for kind,body in staged.messages:
                    if kind==0xc03f3:probe(0xef6220,0xef62d0,0xef6350,payload=body)
                    elif kind==0xc03fe:probe(0xd9c110,0xe4e5c0,0xe0a240,payload=body)
                    elif kind==0xc0803:probe(0xf9df90,0xf9e0b0,0xf9e140,payload=body)
                raise ValueError('controlled failure after native removal encoding')
        except ValueError as error:assert str(error)=='controlled failure after native removal encoding'
        assert state()==before_remove_faults
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');removed_advanced=actions.apply(db,inv,rules,store.currency_rules,removal_faults,
                resource_context=resource_context,clock_ms=clock,authority_reader=authority,precommit=sync)
            assert not removed_advanced.replayed and tuple(slot for slot,_ in removed_advanced.basis.profile.entries)==(1,)
            preserved_zero=orbs.read(db,inv,rules.orbs,removed_advanced.returned_item_key)
            assert preserved_zero.source.retained_raw6==0 and type(preserved_zero.source.retained_raw6) is int
            assert preserved_zero.source.tips==OrbTips(120,0,327,-328)
        # Current damage is retained by old paid commands, never replaced with
        # the resource values that existed when their command was admitted.
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');current=read_role_resources(db,1111,rid,epoch,store.resource_rules)
            apply_resource_transition(db,1111,rid,epoch,plan_combat_resources(current,50,30,store.resource_rules),
                'known-later-damage',rules=store.resource_rules,equipment_rules=gear)
        with closing(store.connect()) as db:
            db.execute('BEGIN');db.set_authorizer(lambda action,*args:sqlite3.SQLITE_DENY if action in
                (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE) else sqlite3.SQLITE_OK)
            damaged=actions.apply(db,inv,rules,store.currency_rules,command,resource_context=resource_context,clock_ms=clock,
                authority_reader=authority,precommit=sync)
            assert (damaged.resources.hp,damaged.resources.mp)==(50,30)
        # Full bag, partial tool debit: the failed return must restore both the
        # worn soul and all4 tools. Freeing one real slot then admits a new ID.
        inv.grant_item(38045,5)
        full_tool=next(i for i in inv.immutable_snapshot().items if i.template_id==38045)
        inv.grant_item(49001,38)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('INSERT INTO test_soul_material_flags VALUES(?,?,0)',(rid,full_tool.id))
            snapshot=inv.immutable_snapshot_transaction(db);assert len(snapshot.items)==40
            sync(db,inv,snapshot,replayed=False,request_id='known-full-bag-fixture')
            full_remove=actions.admit(db,inv,rules,'full-bag-remove',0xc0805,struct.pack('>ii',pet,1),authority_reader=authority,deadline_ms=1000,clock_ms=clock)
        full_before=state()
        try:
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE');actions.apply(db,inv,rules,store.currency_rules,full_remove,
                    resource_context=resource_context,clock_ms=clock,authority_reader=authority,precommit=sync)
        except ValueError as error:assert 'full' in str(error).lower()
        else:raise AssertionError('Full bag removal returned an untracked orb')
        assert state()==full_before
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            free_key=next(i.id for i in inv.immutable_snapshot_transaction(db).items if i.template_id==49001)
            inv.apply_settlement(db,AssetChange('known-free-one-slot',debits=((free_key,1),)))
            sync(db,inv,inv.immutable_snapshot_transaction(db),replayed=False,request_id='known-free-one-slot')
            available=actions.admit(db,inv,rules,'remove-after-space',0xc0805,struct.pack('>ii',pet,1),authority_reader=authority,deadline_ms=1000,clock_ms=clock)
            freed=actions.apply(db,inv,rules,store.currency_rules,available,resource_context=resource_context,clock_ms=clock,
                authority_reader=authority,precommit=sync)
            assert freed.basis.profile.entries==() and len(freed.snapshot.items)==40
            assert next(i.quantity for i in freed.snapshot.items if i.id==full_tool.id)==1
            assert orbs.read(db,inv,rules.orbs,freed.returned_item_key).source.retained_raw6==-2
            assert (freed.resources.hp,freed.resources.mp)==(50,30)
        # Controlled orphan receipt fixture: it must reject, never debit again
        # to reconstruct the missing asset payment record.
        with closing(store.connect()) as db,db:
            db.execute('DELETE FROM inventory_settlements WHERE rowid IN '
                '(SELECT rowid FROM inventory_settlements WHERE role_id=? ORDER BY rowid LIMIT 1)',(rid,))
        orphan_state=state()
        with closing(store.connect()) as db:
            db.execute('BEGIN');db.set_authorizer(lambda action,*args:sqlite3.SQLITE_DENY if action in
                (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE) else sqlite3.SQLITE_OK)
            refused(lambda:actions.apply(db,inv,rules,store.currency_rules,command,resource_context=resource_context,clock_ms=clock,authority_reader=authority,precommit=sync))
        assert state()==orphan_state
        print('PASS actual wear/remove/rewear asset cycle, original4 removal tools38045 debit bound-first, unique returned source/exact raw6, '
            'unchanged human resources/cash;14 SQL faults+2 late original native rollbacks; no-op/heal finalizers refused; '
            'full-bag return rollback and real freed-slot success; deadline cancellation rollback/paid no historical clock; '
            'strict paid/current50HP/30MP/old-epoch/orphan guards; clearance fixture only')


if __name__=='__main__':main()
