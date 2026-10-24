"""The public frozen inventory snapshot joins the actual equipment transaction."""
from contextlib import closing
from dataclasses import FrozenInstanceError
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from accounts import AccountStore
from inventory import Inventory
from inspect_client import OUT, write_json


def refused(action):
    try:
        action()
    except ValueError:
        return
    raise AssertionError('Untrusted inventory snapshot context accepted')


def main():
    with TemporaryDirectory() as tmp:
        store = AccountStore(Path(tmp) / 'state.sqlite3')
        role = store.create_role(1111, '事务资产', 12, 1010101)
        config = Inventory.prepare(store)
        epoch = store.acquire_lease(1111, role['id'])
        inv = Inventory(store, 1111, role['id'], config, epoch=epoch)
        inv.grant_item(40200, binding=1)
        inv.grant_pet(500001)
        before = inv.immutable_snapshot()
        key = before.items[0].id
        with closing(store.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            with patch.object(store, 'connect', side_effect=AssertionError('Nested snapshot connection')):
                event = inv.equip_transaction(db, key, 0, epoch, 'snapshot:equip')
                changes = db.total_changes
                current = inv.immutable_snapshot_transaction(db)
                assert db.total_changes == changes
            assert current.inventory_revision == event.inventory_revision
            assert current.items[0].equipment_slot == 0 and before.items[0].equipment_slot is None
            assert current.items[0].condition == before.items[0].condition
            assert current.items[0].detail == before.items[0].detail
            assert current.pets == before.pets and current.pets[0].progress is not None and current.pets[0].care is not None
            for change in (lambda: setattr(current, 'role_id', 99),
                           lambda: setattr(current.items[0].detail, 'score', 99),
                           lambda: setattr(current.pets[0].care, 'loyalty', 1)):
                try:
                    change()
                except FrozenInstanceError:
                    pass
                else:
                    raise AssertionError('Snapshot contains mutable state')
        assert inv.immutable_snapshot() == current
        try:
            with closing(store.connect()) as db, db:
                db.execute('BEGIN IMMEDIATE')
                inv._unequip(db, key, 3)
                staged = inv.immutable_snapshot_transaction(db)
                assert staged.items[0].equipment_slot is None and staged.items[0].slot == 3
                raise RuntimeError('projection/encoding rejected')
        except RuntimeError:
            pass
        assert inv.immutable_snapshot() == current
        other_role = store.create_role(1111, '他人快照', 12, 1010101)
        other = Inventory(store, 1111, other_role['id'], config, epoch=epoch)
        with closing(store.connect()) as db:
            refused(lambda: inv.immutable_snapshot_transaction(db))
            db.execute('BEGIN')
            refused(lambda: inv.immutable_snapshot_transaction(db, epoch=True))
            refused(lambda: inv.immutable_snapshot_transaction(db, epoch=0))
            refused(lambda: other.immutable_snapshot_transaction(db))
        replacement = store.acquire_lease(1111, role['id'])
        with closing(store.connect()) as db:
            db.execute('BEGIN')
            refused(lambda: inv.immutable_snapshot_transaction(db))
            assert inv.immutable_snapshot_transaction(db, epoch=replacement) == current
        store.release_lease(role['id'], replacement)
        with closing(store.connect()) as db:
            db.execute('BEGIN')
            refused(lambda: inv.immutable_snapshot_transaction(db, epoch=replacement))
    result = {'passed': ['current uncommitted equipment fact and frozen snapshot share one exact revision',
        'no nested connection, commit, config load or state write during transaction snapshot',
        'all items, condition, details, pets, growth and care returned as frozen values',
        'outer failure rolls back staged unequip; previous snapshot remains frozen',
        'missing transaction, bool/zero/foreign/obsolete/inactive lease rejected',
        'trusted replacement epoch reads current state without mutating history'],
        'task_or_role_projection_connected_here': False, 'live_client_tested': False}
    write_json(OUT / 'evidence/inventory-snapshot-transaction-verification.json', result)
    print('PASS:', ', '.join(result['passed']))


if __name__ == '__main__':
    main()
