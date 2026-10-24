"""Actual soul controller reads persisted Mingwen22, never a flag fixture."""
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from dataclasses import replace
from fractions import Fraction
import sqlite3
import struct
from accounts import AccountStore
from inventory import Inventory
from currency import initialize_wallet
from item_effects import VitalState
from role_attributes import AttributeBaseline
from role_attribute_storage import initialize_attribute_baseline
from role_growth import initialize_growth
from role_equipment import EquipmentAttributeBasis,load_ordinary_equipment_attribute_rules,resource_caps_from_projection
from role_equipment_storage import initialize_equipment_attribute_basis,current_equipment_totals,synchronize_inventory_resource_source
from role_resource_storage import migrate_role_resources
from pet_souls import SoulProfile
from pet_soul_item_data import OrbTips
from pet_soul_item_storage import OrbSource
from pet_soul_actions import SoulActionRules
import role_mingwen as mingwen
import pet_soul_authority as authority
import pet_soul_storage as souls
import pet_soul_item_storage as orbs
import pet_soul_action_storage as actions
import runtime_storage


def main():
    with TemporaryDirectory(prefix='mingwen-real-soul-actions-') as tmp:
        store=AccountStore(Path(tmp)/'state.sqlite3');runtime_storage.prepare(store)
        rules=SoulActionRules.load();mrules=mingwen.MingwenRules.load();gear=load_ordinary_equipment_attribute_rules()
        role=store.create_role(1111,'真实铭文元魂',12,1010101);rid=role['id'];epoch=store.acquire_lease(1111,rid)
        inv=Inventory(store.leased(1111,rid,epoch),1111,rid)
        context=actions.SoulResourceRules(store.resource_rules,gear)
        with closing(store.connect()) as db:
            mingwen.prepare(db);souls.prepare(db);orbs.prepare(db);actions.prepare(db)
        def sync(db,inventory,snapshot,*,replayed,request_id):
            return synchronize_inventory_resource_source(db,1111,rid,inventory.epoch,snapshot,request_id,
                equipment_rules=gear,resource_rules=store.resource_rules,replayed=replayed)
        # Only external world/operation clearance is a fixture. There is no
        # flag22 in it; actual inscription activation comes from real storage.
        permission=[1,True]
        def external(db,inventory,pet,material_keys):
            return authority.SoulOperationClearance(rid,pet,inventory.epoch,'explicit-world-fixture',permission[0],permission[1],())
        def reader(db,inventory,pet,material_keys):
            return authority.resolve(db,inventory,mrules,pet,material_keys,clearance_reader=external)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');db.execute('INSERT INTO role_progress VALUES(?,0)',(rid,))
            growth=initialize_growth(db,1111,rid,epoch,store.growth_rules,expected_level=1,free_points=0)
            old=initialize_attribute_baseline(db,1111,rid,epoch,AttributeBaseline(rid,1,0,(10,)*5,
                (100,100,20,10,50,10,10,20,10)),growth,store.attribute_rules,VitalState(rid,0,70,100,40,100)).vitals
            initialize_equipment_attribute_basis(db,1111,rid,epoch,EquipmentAttributeBasis(rid,1,0,gear.revision,0,
                'known-mingwen-role',seal_resistance=0),gear)
            totals=current_equipment_totals(db,1111,rid,epoch,inv.immutable_snapshot_transaction(db),gear)
            migrate_role_resources(db,1111,rid,epoch,old,resource_caps_from_projection(totals),origin='explicit_migration',
                migration_id='known-mingwen-role',rules=store.resource_rules,equipment_rules=gear)
            initialize_wallet(db,1111,rid,epoch,(1000,0,0,0),'explicit_migration',store.currency_rules)
        pet=inv.grant_pet(500001);inv.fight_pet(pet);inv.grant_item(31276)
        key=inv.immutable_snapshot().items[0].id
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            souls.initialize(db,inv,rules.orbs.souls,SoulProfile(rid,pet,0,rules.orbs.souls.revision,'known-empty-mingwen-pet',()),'explicit_known_pet_souls')
            orbs.initialize(db,inv,rules.orbs,OrbSource(rid,key,31276,0,rules.orbs.revision,'known-mingwen-orb',
                OrbTips(140,0,1,2),0,None),'explicit_known_orb_instance')
            try:reader(db,inv,pet,())
            except ValueError:pass
            else:raise AssertionError('Missing Mingwen ledger was treated as inactive')
            state=mingwen.MingwenState(rid,0,mrules.revision,'known-explicit-ledger',
                tuple(mingwen.MingwenEntry(i,0,0,1 if i==22 else 0) for i in range(1,23)))
            mingwen.initialize(db,inv,mrules,state,'explicit_known_mingwen_ledger')
            sync(db,inv,inv.immutable_snapshot_transaction(db),replayed=False,request_id='known-mingwen-sources')
            command=actions.admit(db,inv,rules,'mingwen-wear',0xc03ff,struct.pack('>iiq',key,1,pet),
                deadline_ms=1000,clock_ms=lambda:100,authority_reader=reader)
            result=actions.apply(db,inv,rules,store.currency_rules,command,resource_context=context,
                clock_ms=lambda:100,authority_reader=reader,precommit=sync)
            assert result.effects==((1,31276,3,2,81,1,Fraction(32)),)
            assert result.authority.known_flag22==1
        # Actual later ledger change: the old paid command must read current
        # inactive cap1 instead of replaying the old active cap2.
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');before=mingwen.read(db,inv,mrules)
            after=replace(before.state,version=1,entries=before.state.entries[:-1]+(mingwen.MingwenEntry(22,0,0,2),))
            mingwen.replace_state(db,inv,mrules,before,after)
            sync(db,inv,inv.immutable_snapshot_transaction(db),replayed=False,request_id='known-mingwen-later-source')
        permission[:]=[2,False]
        with closing(store.connect()) as db:
            db.execute('BEGIN');db.set_authorizer(lambda action,*args:sqlite3.SQLITE_DENY if action in
                (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE) else sqlite3.SQLITE_OK)
            paid=actions.apply(db,inv,rules,store.currency_rules,command,resource_context=context,
                clock_ms=lambda:2000,authority_reader=reader,precommit=sync)
            assert paid.replayed and paid.effects==((1,31276,3,1,81,1,Fraction(11)),)
            assert paid.authority.known_flag22==0 and paid.authority.allowed is False
            assert paid.authority.policy!=result.authority.policy
            assert (paid.resources.hp,paid.resources.mp)==(70,40)
        permission[:]=[3,True]
        inv.grant_item(31278)
        second=next(i for i in inv.immutable_snapshot().items if i.template_id==31278)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            orbs.initialize(db,inv,rules.orbs,OrbSource(rid,second.id,31278,0,rules.orbs.revision,
                'known-second-mingwen-orb',OrbTips(140,0,0,0),0,None),'explicit_known_orb_instance')
            sync(db,inv,inv.immutable_snapshot_transaction(db),replayed=False,request_id='second-mingwen-orb-source')
            unpaid=actions.admit(db,inv,rules,'mingwen-stale-unpaid',0xc03ff,struct.pack('>iiq',second.id,1,pet),
                deadline_ms=1000,clock_ms=lambda:100,authority_reader=reader)
            assert unpaid.authority.known_flag22==0
            before=mingwen.read(db,inv,mrules)
            after=replace(before.state,version=2,entries=before.state.entries[:-1]+(mingwen.MingwenEntry(22,0,0,1),))
            mingwen.replace_state(db,inv,mrules,before,after)
            sync(db,inv,inv.immutable_snapshot_transaction(db),replayed=False,request_id='actual-inscription-reactivated')
        unchanged=inv.immutable_snapshot()
        with closing(store.connect()) as db:
            db.execute('BEGIN');db.set_authorizer(lambda action,*args:sqlite3.SQLITE_DENY if action in
                (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE) else sqlite3.SQLITE_OK)
            try:actions.apply(db,inv,rules,store.currency_rules,unpaid,resource_context=context,
                clock_ms=lambda:100,authority_reader=reader,precommit=sync)
            except ValueError:pass
            else:raise AssertionError('Unpaid command ignored changed real Mingwen source')
        assert inv.immutable_snapshot()==unchanged
        with closing(store.connect()) as db:
            db.execute('BEGIN')
            try:authority.resolve(db,inv,mrules,pet,(second.id,),clearance_reader=external)
            except ValueError:pass
            else:raise AssertionError('Incomplete actual material flags accepted')
            async def unknown_async(*args):return None
            try:authority.resolve(db,inv,mrules,pet,(),clearance_reader=unknown_async)
            except ValueError as error:assert 'synchronously' in str(error)
            else:raise AssertionError('Awaitable operation clearance accepted')
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            fresh=actions.admit(db,inv,rules,'mingwen-new-after-change',0xc03ff,struct.pack('>iiq',second.id,1,pet),
                deadline_ms=1000,clock_ms=lambda:100,authority_reader=reader)
            second_result=actions.apply(db,inv,rules,store.currency_rules,fresh,resource_context=context,
                clock_ms=lambda:100,authority_reader=reader,precommit=sync)
            assert second_result.authority.known_flag22==1 and not second_result.replayed
            assert len(second_result.basis.profile.entries)==2
        print('PASS actual soul asset controller uses persisted Mingwen22 active cap2/scalar32; later rawActive2→inactive cap1/scalar11; '
            'paid current-only SQL readonly/current70HP40MP; changed-ledger unpaid refusal/new intent succeeds; '
            'missing material/async reader refuses; no flag fixture, external world clearance remains explicit fixture')


if __name__=='__main__':main()
