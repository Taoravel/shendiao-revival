"""Public fenced unequip transaction joins current snapshot and replies."""
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from dataclasses import FrozenInstanceError,replace
import sqlite3
import struct

from accounts import AccountStore
from inventory import Inventory,EquipmentEvent
from inventory_test_support import known_cash_context
from inspect_client import OUT,write_json


def refused(action):
    try:action()
    except ValueError:return
    raise AssertionError('Invalid or obsolete unequip intent accepted')


def main():
    with TemporaryDirectory() as tmp:
        store=AccountStore(Path(tmp)/'state.sqlite3')
        role=store.create_role(1111,'卸装事务',12,1010101)
        config=Inventory.prepare(store)
        store.inventory_config=config
        inv=Inventory(store,1111,role['id'],config,
            **known_cash_context(store,1111,role['id'],balances=(91,0,0,0)))
        inv.grant_item(40200,binding=1)
        key=inv.snapshot()['items'][0]['id']
        original_item=inv.immutable_snapshot().items[0]
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            inv.equip_transaction(db,key,0,inv.epoch,'unequip:setup')
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            with patch.object(store,'connect',side_effect=AssertionError('Nested unequip connection')):
                event=inv.unequip_transaction(db,key,-1,inv.epoch,'unequip:first')
                current=inv.immutable_snapshot_transaction(db,epoch=inv.epoch)
                replies=inv.equipment_bag_messages(db,inv.epoch)
            assert current.items[0].equipment_slot is None and current.items[0].slot==0
            assert current.items[0].binding==1
            assert current.items[0].detail==original_item.detail and current.items[0].condition==original_item.condition
            assert event.previous_equipment_slot==0 and event.target_slot==0
            assert event.inventory_revision==current.inventory_revision and not event.replayed
            assert len(replies)==2
            assert struct.unpack_from('>Q',replies[0][1],4)[0]==91
            assert not isinstance(event,EquipmentEvent), 'Removal must not become a type59 equip fact'
            try:event.target_slot=9
            except FrozenInstanceError:pass
            else:raise AssertionError('Mutable unequip event')
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            replay=inv.unequip_transaction(db,key,-1,inv.epoch,'unequip:first')
            assert replay.replayed and replace(replay,replayed=False)==event
            refused(lambda:inv.unequip_transaction(db,key,3,inv.epoch,'unequip:first'))
            refused(lambda:inv.equip_transaction(db,key,0,inv.epoch,'unequip:first'))
            inv.equip_transaction(db,key,0,inv.epoch,'unequip:reequip')
        before=inv.immutable_snapshot()
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            assert inv.unequip_transaction(db,key,-1,inv.epoch,'unequip:first').replayed
            refused(lambda:inv.unequip_transaction(db,key,-1,inv.epoch,'unequip:setup'))
        assert inv.immutable_snapshot()==before  # history cannot remove later equipment
        try:
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                inv.unequip_transaction(db,key,3,inv.epoch,'unequip:outer-failure')
                inv.immutable_snapshot_transaction(db)
                inv.equipment_bag_messages(db,inv.epoch)
                raise RuntimeError('downstream attribute projection/encoding failed')
        except RuntimeError:pass
        assert inv.immutable_snapshot()==before
        # The failed command key can still succeed after the outer failure.
        with closing(store.connect()) as db:
            db.execute("CREATE TRIGGER fail_unequip_receipt BEFORE INSERT ON inventory_equipment_commands BEGIN SELECT RAISE(ABORT,'receipt failure'); END")
        try:
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                inv.unequip_transaction(db,key,3,inv.epoch,'unequip:outer-failure')
        except sqlite3.IntegrityError:pass
        else:raise AssertionError('Actual unequip receipt save failure did not execute')
        assert inv.immutable_snapshot()==before
        with closing(store.connect()) as db:db.execute('DROP TRIGGER fail_unequip_receipt')
        unknown=Inventory(store,1111,role['id'],config,epoch=inv.epoch)
        try:
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                unknown.unequip_transaction(db,key,3,inv.epoch,'unequip:no-wallet')
                unknown.equipment_bag_messages(db,inv.epoch)
        except ValueError:pass
        else:raise AssertionError('Unknown wallet did not reject staged replies')
        assert inv.immutable_snapshot()==before
        # Only the public command validates request context; no private calls.
        inv.grant_item(31000)
        carried=next(i for i in inv.snapshot()['items'] if i['template_id']==31000)
        before=inv.immutable_snapshot()
        limited=Inventory(store,1111,role['id'],replace(config,policy=dict(config.policy,bag_capacity=1)),
                          epoch=inv.epoch,currency_rules=inv.currency_rules)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            refused(lambda:limited.unequip_transaction(db,key,-1,inv.epoch,'unequip:full-bag'))
            for bad in (True,False,None,'','x'*129,0,-1,2**63,'wrong'):
                refused(lambda bad=bad:inv.unequip_transaction(db,key,-1,bad,'unequip:bad-epoch'))
            for target in (True,-2,inv.policy['bag_capacity'],carried['slot']):
                refused(lambda target=target:inv.unequip_transaction(db,key,target,inv.epoch,'unequip:bad-slot'))
            for bad_key in (True,0,-1,2**63,carried['id']):
                refused(lambda bad_key=bad_key:inv.unequip_transaction(db,bad_key,-1,inv.epoch,'unequip:bad-key'))
        assert inv.immutable_snapshot()==before
        with closing(store.connect()) as db:
            refused(lambda:inv.unequip_transaction(db,key,-1,inv.epoch,'unequip:no-txn'))
        other_role=store.create_role(1111,'他人装备',12,1010101)
        other=Inventory(store,1111,other_role['id'],config)
        other.grant_item(40200);foreign=other.snapshot()['items'][0]['id'];other.equip(foreign,0)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            refused(lambda:inv.unequip_transaction(db,foreign,-1,inv.epoch,'unequip:foreign'))
        assert inv.immutable_snapshot()==before
        # A replacement opaque token can acknowledge old history with its
        # original token retained, and execute new commands in real fenced DB.
        token='卸装所有者:00007'
        with closing(store.connect()) as db,db:
            db.execute('UPDATE role_leases SET epoch=? WHERE role_id=?',(token,role['id']))
        active=Inventory(store.leased(1111,role['id'],token),1111,role['id'],config,
            epoch=token,currency_rules=inv.currency_rules)
        with closing(active.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            refused(lambda:inv.unequip_transaction(db,key,-1,inv.epoch,'unequip:stale'))
            old=active.unequip_transaction(db,key,-1,token,'unequip:first')
            assert old.replayed and old.login_epoch==inv.epoch
            final=active.unequip_transaction(db,key,3,token,'unequip:outer-failure')
            assert final.login_epoch==token and final.target_slot==3 and not final.replayed
            staged=active.immutable_snapshot_transaction(db)
            assert next(i for i in staged.items if i.id==key).equipment_slot is None
            assert staged.inventory_revision==final.inventory_revision
            active.equipment_bag_messages(db,token)
        assert Inventory(AccountStore(store.path),1111,role['id'],config).snapshot()==active.snapshot()
    report={'passed':['public unequip joins exact caller transaction, current immutable snapshot and actual cash replies',
        'removal event is frozen and distinct from type59 equip facts',
        'historical replay never removes later equipment; conflicting target or equip intent rejected',
        'outer encoding failure, real receipt abort and unknown wallet roll back item/revision/receipt',
        'invalid target, unavailable/carried/foreign item and missing transaction refused',
        'opaque current lease retained; replaced lease refused; current token can acknowledge old history',
        'explicit bag target and reopen preserve current slot/binding/detail'],
        'shared_role_projection_connected':False,'native_gui_tested':False}
    write_json(OUT/'evidence/unequip-transaction-verification.json',report)
    print('PASS:',', '.join(report['passed']))


if __name__=='__main__':main()
