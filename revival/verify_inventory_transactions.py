"""Verify injected startup state and caller-owned atomic/idempotent settlements."""
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from dataclasses import FrozenInstanceError
from accounts import AccountStore
from inventory import Inventory, AssetChange
from inspect_client import OUT, write_json


def rejects(call, error_type=ValueError):
    try:
        call()
    except error_type:
        return
    raise AssertionError('Invalid operation accepted')


def main():
    with TemporaryDirectory() as tmp:
        store = AccountStore(Path(tmp) / 'state.sqlite3')
        role = store.create_role(1111, '结算角色', 12, 1010101)
        # Integration calls this once at startup and injects the result.
        store.inventory_config = Inventory.prepare(store)
        with patch.object(Inventory, 'prepare', side_effect=AssertionError('Hot path schema/config access')):
            inv = Inventory(store, 1111, role['id'])
        rejects(lambda: inv.items[31000].__setitem__('maxNum', '500'), AttributeError)
        with closing(store.connect()) as db:
            rejects(lambda: inv.apply_settlement(db, AssetChange('no-transaction')))
        rejects(lambda: AssetChange('mutable', grants=[(31000, 1)]))
        command = AssetChange('task:fixture:1', grants=((31000, 100),), pets=(500001,))
        with closing(store.connect()) as db, db:
            db.execute('CREATE TABLE task_fixture_claims (id TEXT PRIMARY KEY)')
        # A task-side error after asset writes must roll back both in one commit.
        try:
            with closing(store.connect()) as db, db:
                db.execute('BEGIN IMMEDIATE')
                db.execute('INSERT INTO task_fixture_claims VALUES(?)', (command.settlement_id,))
                inv.apply_settlement(db, command)
                raise ValueError('Injected task failure after inventory write')
        except ValueError:
            pass
        assert inv.snapshot()['items'] == [] and inv.snapshot()['pets'] == []
        with closing(store.connect()) as db:
            assert db.execute('SELECT COUNT(*) FROM task_fixture_claims').fetchone()[0] == 0
        with closing(store.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('INSERT INTO task_fixture_claims VALUES(?)', (command.settlement_id,))
            receipt = inv.apply_settlement(db, command)
            # This method must leave commit ownership with the caller.
            assert db.in_transaction
        first = inv.snapshot()
        frozen = inv.immutable_snapshot()
        assert frozen.inventory_revision == first['inventory_revision'] > 0
        def mutate():
            frozen.items[0].quantity = 999
        rejects(mutate, FrozenInstanceError)
        assert [x['quantity'] for x in first['items']] == [99, 1]
        assert len(first['pets']) == 1
        # Replay after reopening returns the prior pet keys, never new assets.
        reopened = AccountStore(store.path)
        reopened.inventory_config = store.inventory_config
        inv = Inventory(reopened, 1111, role['id'])
        with closing(store.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            assert inv.apply_settlement(db, command) == receipt
        assert inv.snapshot() == first
        with closing(store.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            rejects(lambda: inv.apply_settlement(db, AssetChange(command.settlement_id, grants=((31000, 1),))))
        # A late invalid pet cancels earlier item grants and writes no receipt.
        failed = AssetChange('task:fixture:2', grants=((31000, 5),), pets=(-1,))
        try:
            with closing(store.connect()) as db, db:
                db.execute('BEGIN IMMEDIATE')
                inv.apply_settlement(db, failed)
        except ValueError:
            pass
        else:
            raise AssertionError('Unknown pet accepted')
        assert inv.snapshot() == first
        with closing(store.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            inv.apply_settlement(db, AssetChange(failed.settlement_id, grants=((31000, 5),)))
        assert sum(x['quantity'] for x in inv.snapshot()['items']) == 105
        other = store.create_role(1111, '另个结算', 12, 1010101)
        another = Inventory(store, 1111, other['id'])
        with closing(store.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            another.apply_settlement(db, command)
        assert sum(x['quantity'] for x in another.snapshot()['items']) == 100
    result = {'passed': ['startup config injected without schema/config reload',
                        'read-only catalog snapshot', 'immutable settlement command',
                        'caller transaction required and not committed internally',
                        'task plus assets rollback together', 'reopen replay is idempotent',
                        'settlement payload conflict rejected', 'late invalid grant rollback',
                        'same settlement ID isolated by role', 'versioned immutable domain snapshot'],
              'runtime_owner_routing_integrated': False,
              'login_epoch_enforced_here': False,
              'concurrency_or_capacity_tested': False}
    write_json(OUT / 'evidence/inventory-transactions-verification.json', result)
    print('PASS:', ', '.join(result['passed']))


if __name__ == '__main__':
    main()
