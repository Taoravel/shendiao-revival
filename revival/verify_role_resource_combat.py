"""Trusted terminal values at the resource Seam; never run a battle or GUI."""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from accounts import AccountStore
from currency import initialize_wallet,read_wallet,apply_currency,CurrencyChange
from inventory import Inventory
from role_attribute_storage import initialize_attribute_baseline
from role_attribute_protocol import growth_refresh,role_detail_profile
from role_equipment import EquipmentAttributeBasis,resource_caps_from_projection
from role_equipment_storage import initialize_equipment_attribute_basis,current_equipment_totals,current_resource_profile
from role_growth import initialize_growth,read_growth
from role_resource_plan import (load_resource_rules,ResourceProjection,ResourceCaps,RoleResources,
    plan_combat_resources,plan_resource_values)
from role_resource_storage import migrate_role_resources,read_role_resources,apply_resource_transition
from inspect_client import OUT,write_json
import runtime_storage


def refused(action):
    try:action()
    except ValueError:return
    raise AssertionError('Unsupported combat resource change accepted')


def main():
    rules=load_resource_rules()
    assert rules.combat_causes==frozenset({'battle_terminal'})
    source=ResourceProjection(41,0,0,'attributes.known',0,0,'equipment.known')
    before=RoleResources(7,70,40,ResourceCaps(source,100,100),rules.revision)
    plan=plan_combat_resources(before,61,35,rules)
    assert (plan.after.hp,plan.after.mp,plan.after.version)==(61,35,8)
    assert plan.after.caps==before.caps and plan.cause=='battle_terminal'
    assert plan_combat_resources(before,70,40,rules).after is before
    assert plan_combat_resources(before,0,0,rules).after.hp==0
    for hp,mp in ((71,40),(70,41),(-1,0),(0,-1),(True,0),(1.0,0)):
        refused(lambda:plan_combat_resources(before,hp,mp,rules))
    dead=replace(before,hp=0)
    refused(lambda:plan_combat_resources(dead,1,0,rules))
    refused(lambda:plan_combat_resources(before,61,35,replace(rules,combat_causes=frozenset())))
    refused(lambda:replace(rules,combat_causes=['battle_terminal']))

    with TemporaryDirectory(prefix='resource-terminal-') as directory:
        store=AccountStore(Path(directory)/'state.sqlite3')
        role=store.create_role(1111,'终局数值接缝',11,1010109)
        runtime_storage.prepare(store)
        epoch=store.acquire_lease(1111,role['id'])
        gear=store.equipment_attribute_rules
        inv=Inventory(store.leased(1111,role['id'],epoch),1111,role['id'])
        def current(db,lease=epoch):
            return current_resource_profile(db,1111,role['id'],lease,inv.immutable_snapshot_transaction(db),
                equipment_rules=gear,resource_rules=rules)
        def balance(db):
            return next(w.balance for w in read_wallet(db,1111,role['id'],epoch,store.currency_rules) if w.currency=='cash')
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            g=initialize_growth(db,1111,role['id'],epoch,store.growth_rules,expected_level=1,free_points=0)
            p=store.attribute_rules.initial_profile
            legacy=initialize_attribute_baseline(db,1111,role['id'],epoch,p.baseline(role['id']),g,
                store.attribute_rules,replace(p.vitals(role['id']),hp=70,mp=40))
            initialize_equipment_attribute_basis(db,1111,role['id'],epoch,
                EquipmentAttributeBasis(role['id'],9,0,gear.revision,0,'known-terminal-fixture'),gear)
            initialize_wallet(db,1111,role['id'],epoch,(100,0,0,0),'explicit_migration',store.currency_rules)
            totals=current_equipment_totals(db,1111,role['id'],epoch,inv.immutable_snapshot_transaction(db),gear)
            known=migrate_role_resources(db,1111,role['id'],epoch,legacy.vitals,
                resource_caps_from_projection(totals),origin='explicit_migration',migration_id='terminal-known',
                rules=rules,equipment_rules=gear)
        terminal=plan_combat_resources(known,61,35,rules)
        def settle(db):
            result=apply_resource_transition(db,1111,role['id'],epoch,terminal,'terminal-once',rules=rules,equipment_rules=gear)
            apply_currency(db,1111,role['id'],epoch,CurrencyChange('terminal-fee','npc_shop','controlled-atomic-fixture',
                (('cash',-10),)),store.currency_rules)
            profile=current(db)
            growth_refresh(read_growth(db,1111,role['id']),profile)
            assert role_detail_profile(read_growth(db,1111,role['id']),profile).values[:5]==(61,100,100,35,100)
            return result
        try:
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE');settle(db)
                raise RuntimeError('controlled caller failure after actual native encoding')
        except RuntimeError as error:
            assert str(error)=='controlled caller failure after actual native encoding'
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            assert current(db).vitals.hp==70 and balance(db)==100
            result=settle(db)
            assert not result.replayed and (result.resources.hp,result.resources.mp,result.resources.version)==(61,35,1)
            later=plan_resource_values(result.resources,65,35,'medicine',rules)
            apply_resource_transition(db,1111,role['id'],epoch,later,'later-known-heal',rules=rules,equipment_rules=gear)
            paid=apply_resource_transition(db,1111,role['id'],epoch,terminal,'terminal-once',rules=rules,equipment_rules=gear)
            assert paid.replayed and (paid.resources.hp,paid.resources.mp,paid.resources.version)==(65,35,2)
            refused(lambda:apply_resource_transition(db,1111,role['id'],epoch,terminal,'stale-terminal',rules=rules,equipment_rules=gear))
            forged=replace(plan_combat_resources(paid.resources,60,30,rules),
                after=replace(paid.resources,hp=60,mp=30,version=3,caps=replace(paid.resources.caps,hp_max=101)))
            refused(lambda:apply_resource_transition(db,1111,role['id'],epoch,forged,'forged-caps',rules=rules,equipment_rules=gear))
        new_epoch=store.acquire_lease(1111,role['id'])
        new_inv=Inventory(store.leased(1111,role['id'],new_epoch),1111,role['id'])
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            refused(lambda:apply_resource_transition(db,1111,role['id'],epoch,terminal,'terminal-once',rules=rules,equipment_rules=gear))
            paid=apply_resource_transition(db,1111,role['id'],new_epoch,terminal,'terminal-once',rules=rules,equipment_rules=gear)
            restored=current_resource_profile(db,1111,role['id'],new_epoch,new_inv.immutable_snapshot_transaction(db),
                equipment_rules=gear,resource_rules=rules)
            assert paid.replayed and (restored.vitals.hp,restored.vitals.mp,restored.vitals.version)==(65,35,2)
    report=dict(passed=['explicit frozen combat cause; consume-only exact native values; no revive or cap/source change',
        'same actual carrier CAS and native final projection; caller late failure rolls fee/resource/receipts back',
        'same failed key later succeeds; paid returns later65/35/version2, stale/forged caps/old lease refuse',
        'new lease reads current paid terminal without repeating damage'],actual_battle_executed=False,
        native_gui_verified=False,live_database_modified=False)
    write_json(OUT/'evidence/role-resource-combat-verification.json',report)
    print(report)


if __name__=='__main__':main()
