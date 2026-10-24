"""Explicit NPC-heal resource/fee Seam, no NPC authority or live service."""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from accounts import AccountStore
from currency import CurrencyChange,apply_currency,initialize_wallet,read_wallet
from inventory import Inventory
from inspect_client import OUT,write_json
from role_attribute_storage import initialize_attribute_baseline
from role_attribute_protocol import growth_refresh,role_detail_profile
from role_equipment import EquipmentAttributeBasis,resource_caps_from_projection
from role_equipment_storage import (initialize_equipment_attribute_basis,current_equipment_totals,
    current_resource_profile)
from role_growth import initialize_growth,read_growth
from role_resource_plan import (load_resource_rules,ResourceProjection,ResourceCaps,RoleResources,
    plan_resource_values,plan_combat_resources)
from role_resource_storage import migrate_role_resources,apply_resource_transition
import runtime_storage


def refused(action):
    try:action()
    except ValueError:return
    raise AssertionError('Unauthorized NPC-heal resource or fee accepted')


def main():
    rules=load_resource_rules()
    source=ResourceProjection(41,0,0,'attributes.known',0,0,'equipment.known')
    before=RoleResources(0,70,40,ResourceCaps(source,100,100),rules.revision)
    transition=plan_resource_values(before,100,100,'npc_heal',rules)
    assert (transition.after.hp,transition.after.mp,transition.after.version)==(100,100,1)
    assert transition.after.caps==before.caps
    refused(lambda:plan_resource_values(replace(before,hp=0),100,100,'npc_heal',rules))
    refused(lambda:plan_resource_values(before,101,100,'npc_heal',rules))
    refused(lambda:plan_resource_values(before,100,100,'npc_heal',rules,
        current_caps=replace(before.caps,hp_max=101)))
    refused(lambda:plan_resource_values(before,100,100,'npc_heal',
        replace(rules,resource_causes=frozenset({'medicine','inn_rest'}))))
    with TemporaryDirectory(prefix='npc-heal-resource-') as folder:
        store=AccountStore(Path(folder)/'roles.sqlite3')
        role=store.create_role(1111,'人物治疗数值',11,1010109);runtime_storage.prepare(store)
        epoch=store.acquire_lease(1111,role['id']);gear=store.equipment_attribute_rules
        inv=Inventory(store.leased(1111,role['id'],epoch),1111,role['id'])
        def profile(db,lease=epoch):
            return current_resource_profile(db,1111,role['id'],lease,inv.immutable_snapshot_transaction(db),
                equipment_rules=gear,resource_rules=rules)
        def balances(db,lease=epoch):
            return {w.currency:w.balance for w in read_wallet(db,1111,role['id'],lease,store.currency_rules)}
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            growth=initialize_growth(db,1111,role['id'],epoch,store.growth_rules,expected_level=1,free_points=0)
            initial=store.attribute_rules.initial_profile
            legacy=initialize_attribute_baseline(db,1111,role['id'],epoch,initial.baseline(role['id']),growth,
                store.attribute_rules,replace(initial.vitals(role['id']),hp=70,mp=40)).vitals
            initialize_equipment_attribute_basis(db,1111,role['id'],epoch,
                EquipmentAttributeBasis(role['id'],9,0,gear.revision,0,'known-npc-heal-fixture'),gear)
            initialize_wallet(db,1111,role['id'],epoch,(1000,500,0,0),'explicit_migration',store.currency_rules)
            totals=current_equipment_totals(db,1111,role['id'],epoch,inv.immutable_snapshot_transaction(db),gear)
            known=migrate_role_resources(db,1111,role['id'],epoch,legacy,resource_caps_from_projection(totals),
                origin='explicit_migration',migration_id='npc-heal-known',rules=rules,equipment_rules=gear)
        heal=plan_resource_values(known,100,100,'npc_heal',rules)
        fee=CurrencyChange('npc-heal-fee-once','npc_role_heal','controlled-service294-level1',(('cash',-30),))
        def settle(db):
            apply_currency(db,1111,role['id'],epoch,fee,store.currency_rules)
            result=apply_resource_transition(db,1111,role['id'],epoch,heal,'npc-heal-once',rules=rules,equipment_rules=gear)
            current=profile(db);growth=read_growth(db,1111,role['id'])
            growth_refresh(growth,current)
            assert role_detail_profile(growth,current).values[:5]==(100,100,100,100,100)
            return result
        try:
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE');settle(db)
                raise RuntimeError('late caller failure after native healing projection')
        except RuntimeError as error:assert str(error)=='late caller failure after native healing projection'
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            assert (profile(db).vitals.hp,profile(db).vitals.mp)==(70,40) and balances(db)['cash']==1000
            done=settle(db)
            assert not done.replayed and (done.resources.hp,done.resources.mp,done.resources.version)==(100,100,1)
            assert balances(db)==dict(cash=970,bound_silver=500,yuanbao=0,bound_yuanbao=0)
            refused(lambda:apply_currency(db,1111,role['id'],epoch,
                replace(fee,settlement_id='bound-not-healing',deltas=(('bound_silver',-30),)),store.currency_rules))
            # Trusted consume-only resource fixture; no battle engine executes.
            later=plan_combat_resources(done.resources,80,60,rules)
            apply_resource_transition(db,1111,role['id'],epoch,later,'later-known-consumption',rules=rules,equipment_rules=gear)
            paid=apply_resource_transition(db,1111,role['id'],epoch,heal,'npc-heal-once',rules=rules,equipment_rules=gear)
            apply_currency(db,1111,role['id'],epoch,fee,store.currency_rules)
            assert paid.replayed and (paid.resources.hp,paid.resources.mp,paid.resources.version)==(80,60,2)
            assert balances(db)['cash']==970
            refused(lambda:apply_resource_transition(db,1111,role['id'],epoch,heal,'stale-heal',rules=rules,equipment_rules=gear))
        new_epoch=store.acquire_lease(1111,role['id'])
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            refused(lambda:apply_resource_transition(db,1111,role['id'],epoch,heal,'npc-heal-once',rules=rules,equipment_rules=gear))
            paid=apply_resource_transition(db,1111,role['id'],new_epoch,heal,'npc-heal-once',rules=rules,equipment_rules=gear)
            assert (paid.resources.hp,paid.resources.mp,paid.resources.version)==(80,60,2)
            assert balances(db,new_epoch)['cash']==970
    result=dict(passed=['explicit npc_heal cause, same caps/source, no revival/overflow or cap replacement',
        'real role transaction heals70/40 to100/100 and cash1000 to970; bound500 unchanged',
        'actual final native projection then caller failure rolls fee/resource/receipts back; failed ID succeeds once',
        'paid preserves later80/60/version2 and current cash970; stale full-before/old lease reject; new lease keeps current'],
        npc_admission_or_full_fee_rule_verified=False,native_gui_verified=False,live_server_changed=False,battle_executed=False)
    write_json(OUT/'evidence/role-resource-healing-verification.json',result);print(result)


if __name__=='__main__':main()
