"""Two real persisted equipment contracts in one caller-owned database.

No shared rule switch, implicit basis/profile upgrade, game GUI or battle.
"""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from types import MappingProxyType
from unittest.mock import patch
import sqlite3

from accounts import AccountStore
from inventory import Inventory
from role_attribute_storage import initialize_attribute_baseline
from role_attribute_protocol import growth_refresh
from role_equipment import EquipmentAttributeBasis,load_equipment_attribute_policies,resource_caps_from_projection
from role_equipment_storage import (initialize_equipment_attribute_basis,equipment_attribute_rules_transaction,
    current_equipment_totals,current_resource_profile,EquipmentBasisNotInitialized)
from role_growth import initialize_growth,read_growth
from role_resource_storage import migrate_role_resources
from inspect_client import OUT,write_json
from verify_growth_runtime import role_values
import runtime_storage


def refused(action,exception=ValueError):
    try:action()
    except exception:return
    raise AssertionError('Unknown, foreign or mixed equipment policy accepted')


def main():
    policies=load_equipment_attribute_policies()
    assert type(policies) is MappingProxyType and len(policies)==2
    v1=policies['2026-10-23.role-equipment.1']
    v2=policies['2026-10-23.role-equipment.2']
    assert len(v1.templates)==10 and len(v2.templates)==973
    with TemporaryDirectory(prefix='equipment-policy-') as directory:
        store=AccountStore(Path(directory)/'state.sqlite3')
        roles=[store.create_role(1111,name,11,1010109) for name in ('旧装备政策','新装备政策','未知装备基线')]
        runtime_storage.prepare(store)
        epochs=[store.acquire_lease(1111,r['id']) for r in roles]
        for role,epoch,gear,resistance in zip(roles,epochs,(v1,v2),(None,0)):
            inv=Inventory(store.leased(1111,role['id'],epoch),1111,role['id'])
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                g=initialize_growth(db,1111,role['id'],epoch,store.growth_rules,expected_level=1,free_points=0)
                p=store.attribute_rules.initial_profile
                old=initialize_attribute_baseline(db,1111,role['id'],epoch,p.baseline(role['id']),g,
                    store.attribute_rules,replace(p.vitals(role['id']),hp=70,mp=40))
                initialize_equipment_attribute_basis(db,1111,role['id'],epoch,
                    EquipmentAttributeBasis(role['id'],9,0,gear.revision,0,'explicit-known-policy',resistance),gear)
                selected=equipment_attribute_rules_transaction(db,1111,role['id'],epoch,policies)
                assert selected is gear
                caps=resource_caps_from_projection(current_equipment_totals(db,1111,role['id'],epoch,
                    inv.immutable_snapshot_transaction(db),selected))
                migrate_role_resources(db,1111,role['id'],epoch,old.vitals,caps,origin='explicit_migration',
                    migration_id='known-policy-fixture',rules=store.resource_rules,equipment_rules=selected)
            with closing(store.connect()) as db,db:
                db.execute('BEGIN')
                writes={sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE,
                    sqlite3.SQLITE_CREATE_TABLE,sqlite3.SQLITE_ALTER_TABLE}
                db.set_authorizer(lambda action,*args:sqlite3.SQLITE_DENY if action in writes else sqlite3.SQLITE_OK)
                with patch.object(Path,'read_text',side_effect=AssertionError('hot-path file read')),patch.object(
                        store,'connect',side_effect=AssertionError('nested policy connection')):
                    selected=equipment_attribute_rules_transaction(db,1111,role['id'],epoch,policies)
                    final=current_resource_profile(db,1111,role['id'],epoch,inv.immutable_snapshot_transaction(db),
                        equipment_rules=selected,resource_rules=store.resource_rules)
                    assert final.seal_resistance is resistance
                    assert (final.vitals.hp,final.vitals.mp,final.vitals.version)==(70,40,0)
                    messages=growth_refresh(read_growth(db,1111,role['id']),final)
                    assert len(role_values((messages,)))==(20 if resistance is None else 21)
                db.set_authorizer(None)
                refused(lambda:equipment_attribute_rules_transaction(db,2222,role['id'],epoch,policies))
                refused(lambda:equipment_attribute_rules_transaction(db,1111,role['id'],'stale',policies))
                refused(lambda:equipment_attribute_rules_transaction(db,1111,role['id'],epoch,dict(policies)))
        assert store.equipment_attribute_rules.revision==v1.revision
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            unknown=roles[2]
            refused(lambda:equipment_attribute_rules_transaction(db,1111,unknown['id'],epochs[2],policies),EquipmentBasisNotInitialized)
            only_v1=MappingProxyType({v1.revision:v1})
            refused(lambda:equipment_attribute_rules_transaction(db,1111,roles[1]['id'],epochs[1],only_v1))
        new_epoch=store.acquire_lease(1111,roles[1]['id'])
        with closing(store.connect()) as db,db:
            db.execute('BEGIN')
            refused(lambda:equipment_attribute_rules_transaction(db,1111,roles[1]['id'],epochs[1],policies))
            assert equipment_attribute_rules_transaction(db,1111,roles[1]['id'],new_epoch,policies) is v2
    report=dict(passed=['startup freezes both actual v1 ten-template and v2 973-template rule sets',
        'two explicit persisted bases in one database select their exact policy; legacyNone stays unknown',
        'strict current70/40/version0 yields native20 vs21 maps without source or resource writes',
        'SQL-denied-write read path has no file read/nested connection; missing/foreign/stale/unknown policy refuses',
        'fresh lease preserves explicit v2 policy; global prepared default remains v1'],
        shared_policy_switch_enabled=False,automatic_basis_upgrade=False,native_gui_verified=False,battle_executed=False)
    write_json(OUT/'evidence/equipment-policy-selection-verification.json',report)
    print(report)


if __name__=='__main__':main()
