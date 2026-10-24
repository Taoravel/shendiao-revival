"""Explicit basis, real asset transaction and projection rollback in a temp DB."""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
import tempfile

from accounts import AccountStore
from inventory import Inventory, AssetChange
from inspect_client import OUT,write_json
from role_attribute_storage import initialize_attribute_baseline
from role_attribute_protocol import growth_refresh
from role_equipment import EquipmentAttributeBasis,load_equipment_attribute_rules
from role_equipment_storage import (prepare_equipment_attribute_storage,read_equipment_attribute_basis,
    initialize_equipment_attribute_basis,current_equipment_projection)
from role_growth import initialize_growth,read_growth
import runtime_storage


def refused(action):
    try:
        action()
    except ValueError:
        return
    raise AssertionError('Invalid equipment basis or stale assets accepted')


def main():
    rules=load_equipment_attribute_rules()
    with tempfile.TemporaryDirectory(prefix='role-equipment-') as directory:
        store=AccountStore(Path(directory)/'state.sqlite3')
        role=store.create_role(1111,'装备基准',11,1010109)  # legacy: no automatic provenance
        runtime_storage.prepare(store)
        epoch=store.acquire_lease(1111,role['id'])
        inventory=Inventory(store.leased(1111,role['id'],epoch),1111,role['id'])
        with closing(store.connect()) as db:
            prepare_equipment_attribute_storage(db)
        profile=store.attribute_rules.initial_profile
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            growth=initialize_growth(db,1111,role['id'],epoch,store.growth_rules,expected_level=1,free_points=0)
            initialize_attribute_baseline(db,1111,role['id'],epoch,profile.baseline(role['id']),growth,
                store.attribute_rules,replace(profile.vitals(role['id']),hp=70,mp=40))
            assert read_equipment_attribute_basis(db,1111,role['id'],epoch,rules) is None
            refused(lambda:current_equipment_projection(db,1111,role['id'],epoch,
                inventory.immutable_snapshot_transaction(db),rules))
            basis=EquipmentAttributeBasis(role['id'],9,0,rules.revision,11,'explicit-known-legacy-sealing')
            initialize_equipment_attribute_basis(db,1111,role['id'],epoch,basis,rules)
            refused(lambda:initialize_equipment_attribute_basis(db,1111,role['id'],epoch,replace(basis,seal_strength=0),rules))
            refused(lambda:initialize_equipment_attribute_basis(db,1111,role['id'],epoch,replace(basis,character_id=1),rules))
            inventory.apply_settlement(db,AssetChange('starter-fixture',grants=((49009,1,1),)))
            before=inventory.immutable_snapshot_transaction(db)
            key=before.items[0].id
            event=inventory.equip_transaction(db,key,0,epoch,'equip-once')
            current=inventory.immutable_snapshot_transaction(db)
            refused(lambda:current_equipment_projection(db,1111,role['id'],epoch,before,rules))
            final=current_equipment_projection(db,1111,role['id'],epoch,current,rules)
            assert (final.attributes.physical_attack,final.attributes.magic_attack,final.seal_strength)==(45,35,19)
            assert (final.vitals.hp,final.vitals.mp)==(70,40)
            growth_refresh(growth,final)  # pre-commit encoding constraint
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            assert initialize_equipment_attribute_basis(db,1111,role['id'],epoch,basis,rules)==basis
            replay=inventory.equip_transaction(db,key,0,epoch,'equip-once')
            assert replay.replayed and replay.item_key==event.item_key
            inventory.apply_settlement(db,AssetChange('other-weapon',grants=((49006,1,1),)))
            other=next(item.id for item in inventory.immutable_snapshot_transaction(db).items if item.template_id==49006)
        try:
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                inventory.equip_transaction(db,other,0,epoch,'equip-rollback')
                projected=current_equipment_projection(db,1111,role['id'],epoch,
                    inventory.immutable_snapshot_transaction(db),rules)
                growth_refresh(read_growth(db,1111,role['id']),projected)
                raise RuntimeError('Controlled later task/receipt failure')
        except RuntimeError:
            pass
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            assert not db.execute('SELECT 1 FROM inventory_equipment_commands WHERE role_id=? AND request_id=?',
                                  (role['id'],'equip-rollback')).fetchone()
            current=inventory.immutable_snapshot_transaction(db)
            assert next(item.id for item in current.items if item.equipment_slot==0)==key
            assert current_equipment_projection(db,1111,role['id'],epoch,current,rules).seal_strength==19
            # An encoding failure also rolls back the explicit basis and asset command.
            db.execute('DELETE FROM role_equipment_attribute_bases WHERE role_id=?',(role['id'],))
        try:
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                bad=replace(basis,seal_strength=16777209,source_id='explicit-inexact-test-basis')
                initialize_equipment_attribute_basis(db,1111,role['id'],epoch,bad,rules)
                inventory.equip_transaction(db,other,0,epoch,'equip-inexact')
                current_equipment_projection(db,1111,role['id'],epoch,
                    inventory.immutable_snapshot_transaction(db),rules)
        except ValueError:
            pass
        else:
            raise AssertionError('Inexact final seal strength committed')
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            assert read_equipment_attribute_basis(db,1111,role['id'],epoch,rules) is None
            assert not db.execute('SELECT 1 FROM inventory_equipment_commands WHERE role_id=? AND request_id=?',
                                  (role['id'],'equip-inexact')).fetchone()
            initialize_equipment_attribute_basis(db,1111,role['id'],epoch,basis,rules)
        newer=store.acquire_lease(1111,role['id'])
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            refused(lambda:read_equipment_attribute_basis(db,1111,role['id'],epoch,rules))
            assert read_equipment_attribute_basis(db,1111,role['id'],newer,rules)==basis
            db.execute('UPDATE role_leases SET epoch=? WHERE role_id=?',('00007',role['id']))
            assert read_equipment_attribute_basis(db,1111,role['id'],'00007',rules)==basis
            refused(lambda:read_equipment_attribute_basis(db,1111,role['id'],7,rules))
            refused(lambda:read_equipment_attribute_basis(db,1111,role['id'],'7',rules))
            refused(lambda:read_equipment_attribute_basis(db,1111,role['id'],True,rules))
    result=dict(passed=[
        'startup creates schema but legacy has no inferred sealing basis',
        'explicit known legacy11 is preserved; reset and mismatched character refuse',
        'same-transaction equip and assets give final45/35/19 without healing70HP/40MP',
        'old inventory revision refuses, historical equip replay does not apply again',
        'late outer task failure rolls back replacement and equip receipt together',
        'inexact native result rolls back explicit basis, equip and command receipt',
        'new lease reads persisted basis while old lease is rejected; opaque00007 never aliases7'],
        database='disposable',shared_runtime_tested=False,native_gui_verified=False,
        live_server_changed=False,battle_executed=False)
    write_json(OUT/'evidence/role-equipment-storage-verification.json',result)
    print(result)


if __name__=='__main__':
    main()
