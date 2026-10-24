"""Historical handoff confirmation must be current-lease and strictly read-only."""
from contextlib import closing
from dataclasses import replace
import hashlib
import importlib
from pathlib import Path
import sqlite3
import tempfile
import struct
from unittest.mock import patch
import uuid

from accounts import AccountStore
from inspect_client import OUT, write_json
import runtime_storage
import world_transfer_storage as storage
from world_catalog import maps
from world_owner import Location, MapAddress, MapOwner, MoveCommand


def readonly(db, action):
    denied = []
    allowed = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION}

    def authorize(kind, a, b, database, origin):
        if kind in allowed:
            return sqlite3.SQLITE_OK
        denied.append((kind, a, b))
        return sqlite3.SQLITE_DENY

    changes = db.total_changes
    db.set_authorizer(authorize)
    try:
        return action()
    finally:
        db.set_authorizer(None)
        assert db.in_transaction and db.total_changes == changes and not denied


def refused(action):
    try:
        action()
    except ValueError:
        return
    raise AssertionError('Missing, stale or inconsistent committed receipt accepted')


def source_hashes():
    return {name: hashlib.sha256(Path(importlib.import_module(name).__file__).read_bytes()).hexdigest()
        for name in ('world_transfer_storage', 'world_owner', 'accounts', 'runtime_storage',
                     'verify_world_committed_transfer_read')}


def main():
    before = source_hashes()
    groups = []
    with tempfile.TemporaryDirectory(prefix='world-read-committed-') as directory:
        store = AccountStore(Path(directory)/'state.sqlite3')
        role = store.create_role(1111, '只读历史传送', 12, 1010101)
        runtime_storage.prepare(store)
        rid = role['id']
        # Randomness is the external seam. The real lease transaction still
        # installs the valid integer epoch1, exposing Python numeric aliases.
        with patch('accounts.uuid.uuid4', return_value=uuid.UUID(int=1 << 65)):
            epoch = store.acquire_lease(1111, rid)
        assert type(epoch) is int and epoch == 1
        # Explicit same-template portal fixture exercises changing instance,
        # not a claim that original housing/special portal rules are restored.
        catalog = dict(maps())
        catalog[1006] = dict(catalog[1006], portals={(38, 221): (1006, 624, 3536)})
        source = MapOwner(MapAddress(1007, 111, 3), catalog,
            capacity=1, transfer_capacity=2, mailbox_capacity=1)
        target = MapOwner(MapAddress(1006, 222, 7), catalog,
            capacity=1, transfer_capacity=2, mailbox_capacity=1)
        location = source.join(Location(rid, epoch, source.address, 2, 8480, 6976))
        assert store.save_checkpoint(1111, rid, epoch, location.position, location.version)
        with closing(store.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            storage.bind_map_instance_transaction(db, 1111, rid, epoch, location)
        offer = source.prepare_transfer(location, (1006, 576, 3536),
            request_id='read-committed', deadline_ms=10000, now_ms=0)
        storage.begin(store, 1111, rid, epoch, offer)
        receipt = target.activate(source.freeze(target.reserve(offer, 0), 0), 0)
        with closing(store.connect()) as db, db:
            db.execute('BEGIN')
            refused(lambda: readonly(db, lambda: storage.load_committed_transfer_transaction(
                db, 1111, rid, epoch, receipt)))
        groups.append('actual prepared journal refuses SELECT confirmation without committing or cancelling it')
        with closing(store.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            assert storage.commit_transfer_transaction(db, 1111, rid, epoch, receipt)
        with closing(store.connect()) as db, db:
            db.execute('BEGIN')
            historical, current = readonly(db, lambda: storage.load_committed_transfer_transaction(
                db, 1111, rid, epoch, receipt))
            assert historical == receipt
            assert current.address == target.address and current.position == (1006, 576, 3536)
            assert current.version == current.entry_version == 4 and current.transfer_id == offer.transfer_id
            reservation = receipt.frozen.reservation
            for numeric_alias in (True, 1.0):
                aliased_offer = replace(offer, source=replace(offer.source, login_epoch=numeric_alias))
                aliased = replace(receipt, frozen=replace(receipt.frozen,
                    reservation=replace(reservation, offer=aliased_offer),
                    source=replace(receipt.frozen.source, login_epoch=numeric_alias)),
                    location=replace(receipt.location, login_epoch=numeric_alias))
                refused(lambda: readonly(db, lambda: storage.load_committed_transfer_transaction(
                    db, 1111, rid, epoch, aliased)))
            groups.append('integer epoch1 rejects whole-receipt bool/float aliases under SELECT-only authorizer')
            conflicting = [replace(receipt, frozen=replace(receipt.frozen, reservation=replace(
                reservation, offer=replace(offer, **change)))) for change in (
                    dict(deadline_ms=10001), dict(transfer_id='unknown-historical-id'))]
            for aid, lease, candidate in ((9999, epoch, receipt), (1111, 'not-current', receipt),
                (1111, epoch, None), (1111, epoch, replace(receipt, location=replace(receipt.location, x=577))),
                (1111, epoch, replace(receipt, location=replace(receipt.location, login_epoch=True))),
                *((1111, epoch, candidate) for candidate in conflicting)):
                refused(lambda: readonly(db, lambda: storage.load_committed_transfer_transaction(
                    db, aid, rid, lease, candidate)))
        groups.append('same-lease exact historical receipt/full checkpoint; foreign account, stale lease and wrong receipt refuse')
        source.finalize(receipt)
        active = target.ready(receipt.location)
        walked = target.move(MoveCommand(active, 'after-history-walk', 10000, 0xc0faa,
            b'\0'+struct.pack('>hhQ', 592, 3536, 0)), 1).location
        assert walked.version == 6 and store.save_checkpoint(1111, rid, epoch, walked.position, 6)
        with closing(store.connect()) as db, db:
            db.execute('BEGIN')
            historical, current = readonly(db, lambda: storage.load_committed_transfer_transaction(
                db, 1111, rid, epoch, receipt))
            assert historical == receipt and current.position == (1006, 592, 3536)
            assert current.version == 6 and current.entry_version == 4 and target.location(rid) == walked
        groups.append('later legitimate checkpoint remains current and historical target is never replayed')
        second = MapOwner(MapAddress(1006, 333, 9), catalog,
            capacity=1, transfer_capacity=2, mailbox_capacity=1)
        moved = target.move(MoveCommand(walked, 'same-template-later-entry', 10000, 0xc0faa,
            b'\0'+struct.pack('>hhQ', 608, 3536, 0)), 2)
        assert moved.offer is not None and store.save_checkpoint(1111, rid, epoch,
                                                               moved.location.position, moved.location.version)
        storage.begin(store, 1111, rid, epoch, moved.offer)
        newer = second.activate(target.freeze(second.reserve(moved.offer, 2), 2), 2)
        with closing(store.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            assert storage.commit_transfer_transaction(db, 1111, rid, epoch, newer)
        with closing(store.connect()) as db, db:
            db.execute('BEGIN')
            historical, current = readonly(db, lambda: storage.load_committed_transfer_transaction(
                db, 1111, rid, epoch, receipt))
            assert historical == receipt and current.address == MapAddress(1006, 333, 9)
            assert current.position == (1006, 624, 3536) and current.version == current.entry_version == 9
            assert current.transfer_id == moved.offer.transfer_id
        groups.append('later same-template different-instance entry preserves exact full address and provenance')
        with closing(store.connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute("UPDATE world_handoffs SET stage='ready' WHERE transfer_id IN (?,?)",
                       (offer.transfer_id, moved.offer.transfer_id))
            historical, current = readonly(db, lambda: storage.load_committed_transfer_transaction(
                db, 1111, rid, epoch, receipt))
            assert historical == receipt and current.address == second.address and current.version == 9
            db.rollback()
        groups.append('explicit ready-stage fixture confirms both historical and current-entry receipts without writes')
        # Deliberately corrupt durable inputs only inside rolled-back fixture
        # transactions. Confirmation itself is always under the SQL authorizer.
        corruptions = [
            ("UPDATE world_handoffs SET stage='cancelled' WHERE transfer_id=?", (offer.transfer_id,)),
            ("UPDATE world_handoffs SET transfer_id='missing-original' WHERE transfer_id=?", (offer.transfer_id,)),
            ("UPDATE world_handoffs SET offer='{}' WHERE transfer_id=?", (offer.transfer_id,)),
            ("UPDATE world_handoffs SET receipt='{}' WHERE transfer_id=?", (offer.transfer_id,)),
            ("UPDATE world_handoffs SET source='{}' WHERE transfer_id=?", (offer.transfer_id,)),
            ("UPDATE world_handoffs SET epoch='wrong-original-epoch' WHERE transfer_id=?", (offer.transfer_id,)),
            ("UPDATE world_instance_positions SET instance_id=999 WHERE role_id=?", (rid,)),
            ("UPDATE world_instance_positions SET transfer_id='unknown-current-entry' WHERE role_id=?", (rid,)),
            ("UPDATE world_instance_positions SET entry_version=4 WHERE role_id=?", (rid,)),
            ("UPDATE role_positions SET x=625 WHERE role_id=?", (rid,)),
            ("UPDATE position_versions SET version=3 WHERE role_id=?", (rid,)),
            ("DELETE FROM world_instance_positions WHERE role_id=?", (rid,)),
            ("UPDATE world_handoffs SET stage='prepared' WHERE transfer_id=?", (moved.offer.transfer_id,)),
        ]
        for sql, values in corruptions:
            with closing(store.connect()) as db:
                db.execute('BEGIN IMMEDIATE')
                db.execute(sql, values)
                refused(lambda: readonly(db, lambda: storage.load_committed_transfer_transaction(
                    db, 1111, rid, epoch, receipt)))
                db.rollback()
        groups.append('13 explicit rolled-back missing/cancelled/corrupt historical or current-entry cases refuse without read-side writes')
        new_epoch = store.acquire_lease(1111, rid)
        with closing(store.connect()) as db, db:
            db.execute('BEGIN')
            refused(lambda: readonly(db, lambda: storage.load_committed_transfer_transaction(
                db, 1111, rid, epoch, receipt)))
            historical, current = readonly(db, lambda: storage.load_committed_transfer_transaction(
                db, 1111, rid, new_epoch, receipt))
            assert historical == receipt and historical.location.login_epoch == epoch
            assert current.login_epoch == new_epoch and current.address == second.address
            assert current.position == (1006, 624, 3536) and current.version == 9
        groups.append('new current lease confirms old-epoch receipt; old lease remains fenced')
        with closing(store.connect()) as db:
            assert not db.in_transaction
            refused(lambda: storage.load_committed_transfer_transaction(db, 1111, rid, new_epoch, receipt))
        assert source_hashes() == before
        groups.append('caller transaction required; source files stable; no implicit transaction or connection')
        report = dict(all_passed=True, passed=groups, source_sha256=before,
            inputs_stable=True, explicit_initial_checkpoint_fixture=True,
            controlled_same_template_portal_fixture=True, corruptions_rolled_back=len(corruptions),
            sql_authorizer='only SELECT/READ/FUNCTION allowed on all confirmation successes and refusals',
            caller_task_paid_integration_verified=False, gui_verified=False, live_server_changed=False)
        write_json(OUT/'evidence/world-committed-transfer-read-verification.json', report)
        print(report)


if __name__ == '__main__':
    main()
