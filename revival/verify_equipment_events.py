"""Fenced transaction-joining equip facts for task qualification."""
from contextlib import closing
from dataclasses import FrozenInstanceError,replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import struct
from accounts import AccountStore
from inventory import Inventory,EquipmentEvent
from inspect_client import OUT,write_json
from inventory_test_support import known_cash_context


def main():
    with TemporaryDirectory() as tmp:
        store=AccountStore(Path(tmp)/'state.sqlite3')
        role=store.create_role(1111,'装备事实',12,1010101);epoch=store.acquire_lease(1111,role['id'])
        config=Inventory.prepare(store)
        inv=Inventory(store,1111,role['id'],config,
            **known_cash_context(store,1111,role['id'],epoch=epoch,balances=(27,0,0,0)))
        inv.grant_item(40200,binding=1);first=inv.snapshot()['items'][0]['id']
        with closing(store.connect()) as db,db:
            db.execute('CREATE TABLE equip_task_fixture (request_id TEXT PRIMARY KEY)')
            db.execute('BEGIN IMMEDIATE')
            with patch.object(store,'connect',side_effect=AssertionError('Nested equipment connection')):
                fact=inv.equip_transaction(db,first,0,epoch,'equip:first')
                replies=inv.equipment_bag_messages(db,epoch)
                current=inv.immutable_snapshot_transaction(db)
            assert [struct.unpack_from('>i',body)[0] for kind,body in replies]==[1,4]
            assert struct.unpack_from('>Q',replies[0][1],4)[0]==27
            assert isinstance(fact,EquipmentEvent) and not fact.replayed
            assert (fact.role_id,fact.login_epoch,fact.item_key,fact.template_id,fact.equipment_slot)==(
                role['id'],epoch,first,40200,0)
            assert fact.inventory_revision==db.execute('SELECT revision FROM inventory_versions WHERE role_id=?',(role['id'],)).fetchone()[0]
            assert current.inventory_revision==fact.inventory_revision
            assert current.items[0].id==first and current.items[0].equipment_slot==0
            assert current.items[0].condition.current==100 and current.items[0].detail.score==0
            assert db.execute('SELECT equipment_slot FROM inventory_items WHERE id=?',(first,)).fetchone()==(0,)
            db.execute('INSERT INTO equip_task_fixture VALUES(?)',(fact.request_id,))
            try:fact.template_id=999999
            except FrozenInstanceError:pass
            else:raise AssertionError('Equipment fact is mutable')
        before=inv.snapshot()
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            replay=inv.equip_transaction(db,first,0,epoch,'equip:first')
            assert replay.replayed and replace(replay,replayed=False)==fact
            try:inv.equip_transaction(db,first,1,epoch,'equip:first')
            except ValueError:pass
            else:raise AssertionError('Equipment request key reused for a different slot')
        assert inv.snapshot()==before
        inv.unequip(first)
        before=inv.snapshot()
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            assert inv.equip_transaction(db,first,0,epoch,'equip:first').replayed
        assert inv.snapshot()==before  # a receipt does not re-equip a removed item.
        try:
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                event=inv.equip_transaction(db,first,0,epoch,'equip:rollback')
                db.execute('INSERT INTO equip_task_fixture VALUES(?)',(event.request_id,))
                raise RuntimeError('task validation/save failed')
        except RuntimeError:pass
        assert inv.snapshot()==before
        with closing(store.connect()) as db:
            assert not db.execute('SELECT 1 FROM inventory_equipment_commands WHERE request_id=?',('equip:rollback',)).fetchone()
            assert not db.execute('SELECT 1 FROM equip_task_fixture WHERE request_id=?',('equip:rollback',)).fetchone()
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');inv.equip_transaction(db,first,0,epoch,'equip:again')
        inv.grant_item(40200)
        second=next(x['id'] for x in inv.snapshot()['items'] if x['id']!=first)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            replacement=inv.equip_transaction(db,second,0,epoch,'equip:replace')
            assert replacement.replaced_item_key==first and not replacement.replayed
        items=inv.snapshot()['items']
        assert len(items)==2 and next(x for x in items if x['id']==first)['binding']==1
        assert next(x for x in items if x['id']==first)['equipment_slot'] is None
        inv.grant_item(40100)
        incompatible=next(x['id'] for x in inv.snapshot()['items'] if x['template_id']==40100)
        other_role=store.create_role(1111,'别人武器',12,1010101)
        other=Inventory(store,1111,other_role['id'],config)
        other.grant_item(40200);foreign=other.snapshot()['items'][0]['id']
        before=inv.snapshot()
        for key,slot in ((incompatible,0),(foreign,0),(first,3)):
            try:
                with closing(store.connect()) as db,db:
                    db.execute('BEGIN IMMEDIATE');inv.equip_transaction(db,key,slot,epoch,f'invalid:{key}:{slot}')
            except ValueError:pass
            else:raise AssertionError('Invalid equip created an authoritative fact')
            assert inv.snapshot()==before
        new_epoch=store.acquire_lease(1111,role['id'])
        try:
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE');inv.equip_transaction(db,first,0,epoch,'expired')
        except ValueError:pass
        else:raise AssertionError('Expired real lease created an equipment fact')
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            history=inv.equip_transaction(db,first,0,new_epoch,'equip:first')
            assert history.replayed and history.login_epoch==epoch
        assert inv.snapshot()==before
        with closing(store.connect()) as db:
            try:inv.equip_transaction(db,first,0,new_epoch,'no-transaction')
            except ValueError:pass
            else:raise AssertionError('Equipment fact opened its own transaction')
    report={'passed':['equip joins existing transaction without nested connection',
        'frozen role/epoch/key/template/slot/revision fact matches committed state',
        'both bag replies stage in the same transaction with actual cash',
        'same command replay is marked history and does not mutate',
        'conflicting request intent rejected','old receipt does not re-equip later removed item',
        'outer task-like save failure rolls back equip revision fact and marker',
        'replacement fact identifies old item and preserves binding/quantity',
        'foreign incompatible and wrong-slot equipment never create facts',
        'replaced real lease rejected','new lease can acknowledge old history without a fresh fact',
        'no transaction is rejected'],
        'actual_type59_task_connected':False,'live_client_tested':False,'mentor_reward_template_or_binding_selected':False}
    write_json(OUT/'evidence/equipment-events-verification.json',report)
    print('PASS:',', '.join(report['passed']))


if __name__=='__main__':main()
