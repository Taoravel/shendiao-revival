"""Real caller transactions for same-instance relocation and recovery."""
from contextlib import closing
import argparse
import hashlib
import json
from dataclasses import replace
from pathlib import Path
import struct
import sqlite3
import tempfile
import traceback

from accounts import AccountStore
import runtime_storage
from world_catalog import maps, maze_grids
from world_owner import MapOwner, MapAddress, Location, MoveCommand
from world_transfer_storage import bind_map_instance_transaction, load_map_instance_transaction
import world_transfer_storage
import world_relocation_storage as storage


class CallerDatabase:
    def __init__(self, db):
        self.db = db

    @property
    def in_transaction(self):
        return self.db.in_transaction

    def execute(self, sql, args=()):
        assert sql.lstrip().split(None, 1)[0].upper() not in (
            'BEGIN', 'COMMIT', 'ROLLBACK', 'SAVEPOINT', 'RELEASE', 'CREATE', 'ALTER', 'DROP')
        return self.db.execute(sql, args)


class ReadOnlyDatabase(CallerDatabase):
    def execute(self, sql, args=()):
        assert sql.lstrip().split(None, 1)[0].upper() == 'SELECT'
        return super().execute(sql, args)


def refused(action):
    try:
        action()
    except ValueError:
        return
    raise AssertionError('Stale or conflicting relocation transaction accepted')


def fixture(folder, *, adopted=True, prior_entry=False):
    store = AccountStore(Path(folder)/'state.sqlite3')
    role = store.create_role(1111, '同图事务', 11, 1010109)
    runtime_storage.prepare(store)
    with closing(store.connect()) as db, db:
        storage.prepare(db)
    epoch = store.acquire_lease(1111, role['id'])
    address = MapAddress(1627, 2**40+7, 3)
    owner = MapOwner(address, maps(), capacity=2, transfer_capacity=2,
        mailbox_capacity=2, maze=maze_grids()[1627])
    version = store.position_version(role['id'])+1
    if prior_entry:
        original_address = MapAddress(1007, 1007, 0)
        original = MapOwner(original_address, maps(), capacity=2, transfer_capacity=2,
            mailbox_capacity=2, maze=maze_grids()[1007])
        start = original.join(Location(role['id'], epoch, original_address, version, 8480, 6976))
        assert store.save_checkpoint(1111, role['id'], epoch, start.position, start.version)
        with closing(store.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            bind_map_instance_transaction(db, 1111, role['id'], epoch, start)
        offer = original.prepare_transfer(start, (1627,1816,1304),
            request_id='earlier-cross-instance-entry', deadline_ms=10000, now_ms=0)
        world_transfer_storage.begin(store, 1111, role['id'], epoch, offer)
        reservation = owner.reserve(offer, 0)
        receipt = owner.activate(original.freeze(reservation, 0), 0)
        with closing(store.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            world_transfer_storage.commit_transfer_transaction(db, 1111, role['id'], epoch, receipt)
        original.finalize(receipt)
        source = owner.ready(receipt.location)
    else:
        source = Location(role['id'], epoch, address, version, 1816, 1304)
        assert store.save_checkpoint(1111, role['id'], epoch, source.position, source.version)
        owner.join(source)
    move = owner.move(MoveCommand(source, 'same-instance-storage', 10000, 0xc0faa,
        b'\0'+struct.pack('>hhQ', 1832, 1304, 1627), 0, 'native_current'), 0)
    assert move.offer is not None and not move.rejection
    assert store.save_checkpoint(1111, role['id'], epoch, move.location.position, move.location.version)
    with closing(store.connect()) as db, db:
        db.execute('BEGIN IMMEDIATE')
        before = (bind_map_instance_transaction(db, 1111, role['id'], epoch, move.location)
                  if adopted else load_map_instance_transaction(db, 1111, role['id'], epoch))
    proof = owner.freeze_relocation(move.offer, 1, movement_state=0)
    return store, role['id'], epoch, owner, proof, before


def committed_case():
    with tempfile.TemporaryDirectory(prefix='world-relocation-sql-') as folder:
        store, rid, epoch, owner, proof, before = fixture(folder)
        with closing(store.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            caller = CallerDatabase(db)
            assert storage.begin_relocation_transaction(caller, 1111, rid, epoch, proof, now_ms=2) == 'prepared'
        with closing(store.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            assert storage.commit_relocation_transaction(CallerDatabase(db), 1111, rid, epoch, proof, now_ms=3)
        assert store.position(1111, rid) == (1627, 1616, 1840)
        with closing(store.connect()) as db, db:
            db.execute('BEGIN')
            record = storage.load_relocation_transaction(CallerDatabase(db), 1111, rid, epoch, proof.offer.transfer_id)
            assert record.stage == 'committed' and record.prepared == proof
            assert record.checkpoint.position == proof.target.position
            assert record.checkpoint.address == before.address
            assert record.checkpoint.entry_version == before.entry_version
            assert record.checkpoint.transfer_id == before.transfer_id
            refused(lambda: storage.cancel_relocation_transaction(ReadOnlyDatabase(db), 1111, rid, epoch, proof))
        receipt, _ = owner.commit_relocation(proof)
        active = owner.ready(receipt.location)
        assert active.position == (1627, 1616, 1840)


def replay_case():
    with tempfile.TemporaryDirectory(prefix='world-relocation-replay-') as folder:
        store, rid, epoch, owner, proof, before = fixture(folder)
        with closing(store.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            caller = CallerDatabase(db)
            storage.begin_relocation_transaction(caller, 1111, rid, epoch, proof, now_ms=2)
            assert storage.commit_relocation_transaction(caller, 1111, rid, epoch, proof, now_ms=3)
        receipt, _ = owner.commit_relocation(proof)
        active = owner.ready(receipt.location)
        moved = owner.move(MoveCommand(active, 'later-walking', 20000, 0xc0faa,
            b'\0'+struct.pack('>hhQ', 1617, 1840, 1627), 0, 'native_current'), 4)
        assert not moved.rejection
        assert store.save_checkpoint(1111, rid, epoch, moved.location.position, moved.location.version)
        with closing(store.connect()) as db, db:
            db.execute('BEGIN')
            caller = ReadOnlyDatabase(db)
            assert not storage.commit_relocation_transaction(caller, 1111, rid, epoch, proof, now_ms=10001)
            assert storage.begin_relocation_transaction(caller, 1111, rid, epoch, proof, now_ms=10001) == 'committed'
            record = storage.load_relocation_transaction(caller, 1111, rid, epoch, proof.offer.transfer_id)
            assert record.checkpoint.position == (1627, 1617, 1840)
            assert record.checkpoint.version == moved.location.version
        fresh_epoch = store.acquire_lease(1111, rid)
        with closing(store.connect()) as db, db:
            db.execute('BEGIN')
            caller = ReadOnlyDatabase(db)
            refused(lambda: storage.commit_relocation_transaction(caller, 1111, rid, epoch, proof, now_ms=4))
            refused(lambda: storage.commit_relocation_transaction(caller, 1111, rid, fresh_epoch, proof, now_ms=4))
            record = storage.load_relocation_transaction(caller, 1111, rid, fresh_epoch, proof.offer.transfer_id)
            assert record.prepared.offer.source.login_epoch == epoch
            assert record.checkpoint.login_epoch == fresh_epoch
            assert record.checkpoint.position == moved.location.position


def late_rollback_case():
    with tempfile.TemporaryDirectory(prefix='world-relocation-rollback-') as folder:
        store, rid, epoch, owner, proof, before = fixture(folder)
        with closing(store.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            storage.begin_relocation_transaction(CallerDatabase(db), 1111, rid, epoch, proof, now_ms=2)
        with closing(store.connect()) as db, db:
            db.execute('CREATE TABLE caller_probe(value TEXT NOT NULL)')
            db.execute("INSERT INTO caller_probe VALUES('before')")
            db.execute("CREATE TRIGGER refuse_target BEFORE UPDATE OF stage ON world_relocations "
                "WHEN NEW.stage='committed' BEGIN SELECT RAISE(ABORT,'late-target-fault'); END")
        try:
            with closing(store.connect()) as db, db:
                db.execute('BEGIN IMMEDIATE')
                db.execute("UPDATE caller_probe SET value='changed'")
                storage.commit_relocation_transaction(CallerDatabase(db), 1111, rid, epoch, proof, now_ms=3)
        except sqlite3.IntegrityError as error:
            assert 'late-target-fault' in str(error)
        else:
            raise AssertionError('Late decision write fault did not abort caller transaction')
        with closing(store.connect()) as db, db:
            db.execute('BEGIN')
            record = storage.load_relocation_transaction(ReadOnlyDatabase(db), 1111, rid, epoch, proof.offer.transfer_id)
            assert record.stage == 'prepared'
            assert record.checkpoint.position == proof.offer.source.position
            assert record.checkpoint.version == proof.offer.source.version
            assert db.execute('SELECT value FROM caller_probe').fetchone() == ('before',)
        assert owner.location(rid) == proof.frozen


def cancelled_case():
    with tempfile.TemporaryDirectory(prefix='world-relocation-cancel-') as folder:
        store, rid, epoch, owner, proof, before = fixture(folder)
        with closing(store.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            caller = CallerDatabase(db)
            storage.begin_relocation_transaction(caller, 1111, rid, epoch, proof, now_ms=2)
            assert storage.cancel_relocation_transaction(caller, 1111, rid, epoch, proof)
        cancelled, _ = owner.cancel_relocation(proof)
        assert store.position(1111, rid) == cancelled.location.position == proof.offer.source.position
        assert store.position_version(rid) == cancelled.location.version
        with closing(store.connect()) as db, db:
            db.execute('BEGIN')
            caller = ReadOnlyDatabase(db)
            assert not storage.cancel_relocation_transaction(caller, 1111, rid, epoch, proof)
            refused(lambda: storage.commit_relocation_transaction(caller, 1111, rid, epoch, proof, now_ms=3))
            record = storage.load_relocation_transaction(caller, 1111, rid, epoch, proof.offer.transfer_id)
            assert record.stage == 'cancelled' and record.checkpoint.address == before.address
            assert record.checkpoint.position == proof.offer.source.position


def recovery_case():
    for mode in ('prepared', 'committed', 'not_journalled'):
        with tempfile.TemporaryDirectory(prefix='world-relocation-recovery-') as folder:
            store, rid, epoch, owner, proof, before = fixture(folder)
            if mode != 'not_journalled':
                with closing(store.connect()) as db, db:
                    db.execute('BEGIN IMMEDIATE')
                    caller = CallerDatabase(db)
                    storage.begin_relocation_transaction(caller, 1111, rid, epoch, proof, now_ms=2)
                    if mode == 'committed':
                        storage.commit_relocation_transaction(caller, 1111, rid, epoch, proof, now_ms=3)
            fresh_epoch = store.acquire_lease(1111, rid)
            with closing(store.connect()) as db, db:
                db.execute('BEGIN IMMEDIATE')
                recovered = storage.prepare_relocation_recovery_transaction(CallerDatabase(db),
                    1111, rid, fresh_epoch, proof.offer.transfer_id,
                    expected_prepared=proof if mode == 'not_journalled' else None)
                expected = proof.target.position if mode == 'committed' else proof.offer.source.position
                assert recovered.stage == ('committed' if mode == 'committed' else 'cancelled')
                assert recovered.prepared == proof and recovered.checkpoint.position == expected
                assert recovered.checkpoint.version == proof.target.version
                assert recovered.checkpoint.address == before.address
                assert recovered.checkpoint.entry_version == before.entry_version
                assert recovered.checkpoint.transfer_id == before.transfer_id
            with closing(store.connect()) as db, db:
                db.execute('BEGIN')
                caller = ReadOnlyDatabase(db)
                assert storage.prepare_relocation_recovery_transaction(caller, 1111, rid,
                    fresh_epoch, proof.offer.transfer_id) == recovered
                refused(lambda: storage.commit_relocation_transaction(caller, 1111, rid, epoch, proof, now_ms=4))
            # This is a fresh Domain rebuild, not a shared-runtime reconnect or
            # retirement of the old in-process frozen member (still pending).
            cp = recovered.checkpoint
            cold = MapOwner(cp.address, maps(), capacity=2, transfer_capacity=2,
                mailbox_capacity=2, maze=maze_grids()[1627])
            location = cold.join(Location(rid, fresh_epoch, cp.address, cp.version, *cp.position[1:]))
            moved = cold.move(MoveCommand(location, 'cold-step', 20000, 0xc0faa,
                b'\0'+struct.pack('>hhQ', location.x+1, location.y, 1627), 0, 'native_current'), 4)
            assert not moved.rejection and moved.location.position == (1627, location.x+1, location.y)
            assert owner.location(rid) == proof.frozen


def identity_guards_case():
    with tempfile.TemporaryDirectory(prefix='world-relocation-identity-') as folder:
        store, rid, epoch, owner, proof, before = fixture(folder)
        with closing(store.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            caller = CallerDatabase(db)
            refused(lambda: storage.begin_relocation_transaction(caller, 9999, rid, epoch, proof, now_ms=2))
            refused(lambda: storage.begin_relocation_transaction(caller, 1111, rid, epoch,
                replace(proof, movement_state=True), now_ms=2))
            refused(lambda: storage.begin_relocation_transaction(caller, 1111, rid, epoch,
                replace(proof, target=replace(proof.target,
                    address=replace(proof.target.address, partition_id=4))), now_ms=2))
            refused(lambda: storage.begin_relocation_transaction(caller, 1111, rid, epoch, proof, now_ms=True))
            assert storage.begin_relocation_transaction(caller, 1111, rid, epoch, proof, now_ms=2) == 'prepared'
            refused(lambda: storage.begin_relocation_transaction(caller, 1111, rid, epoch,
                replace(proof, preparation_id='second-prepare',
                    offer=replace(proof.offer, transfer_id='second-request')), now_ms=2))
            refused(lambda: storage.begin_relocation_transaction(caller, 1111, rid, epoch,
                replace(proof, preparation_id='different-preparation'), now_ms=2))
            refused(lambda: storage.commit_relocation_transaction(caller, 1111, rid, epoch,
                replace(proof, owner_generation='different-map-lifetime'), now_ms=3))
            refused(lambda: storage.commit_relocation_transaction(caller, 1111, rid, epoch, proof, now_ms=10000))
            record = storage.load_relocation_transaction(ReadOnlyDatabase(db), 1111, rid, epoch, proof.offer.transfer_id)
            assert record.stage == 'prepared' and record.checkpoint == before
        with closing(store.connect()) as db:
            refused(lambda: storage.load_relocation_transaction(CallerDatabase(db), 1111, rid, epoch, proof.offer.transfer_id))
        with closing(store.connect()) as db, db:
            db.execute('BEGIN')
            refused(lambda: storage.prepare_relocation_recovery_transaction(ReadOnlyDatabase(db),
                1111, rid, epoch, proof.offer.transfer_id))
        later = replace(proof.offer.source, x=1833, version=proof.offer.source.version+4)
        assert store.save_checkpoint(1111, rid, epoch, later.position, later.version)
        with closing(store.connect()) as db, db:
            db.execute('BEGIN')
            refused(lambda: storage.commit_relocation_transaction(CallerDatabase(db), 1111, rid, epoch, proof, now_ms=3))
        fresh_epoch = store.acquire_lease(1111, rid)
        with closing(store.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            record = storage.prepare_relocation_recovery_transaction(CallerDatabase(db), 1111, rid,
                fresh_epoch, proof.offer.transfer_id)
            assert record.stage == 'cancelled' and record.checkpoint.position == later.position
            assert record.checkpoint.version == later.version


def provenance_case():
    with tempfile.TemporaryDirectory(prefix='world-relocation-entry-') as folder:
        store, rid, epoch, owner, proof, before = fixture(folder, prior_entry=True)
        assert before.transfer_id == 'earlier-cross-instance-entry'
        assert before.entry_version < proof.offer.source.version
        with closing(store.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            storage.begin_relocation_transaction(CallerDatabase(db), 1111, rid, epoch, proof, now_ms=2)
        def changed_entry(column, value):
            with closing(store.connect()) as db, db:
                db.execute('BEGIN IMMEDIATE')
                assert column in ('partition_id', 'transfer_id')
                db.execute('UPDATE world_instance_positions SET '+column+'=? WHERE role_id=?', (value, rid))
                storage.commit_relocation_transaction(CallerDatabase(db), 1111, rid, epoch, proof, now_ms=3)
        refused(lambda: changed_entry('partition_id', 4))
        refused(lambda: changed_entry('transfer_id', 'another-entering-event'))
        with closing(store.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            caller = CallerDatabase(db)
            assert storage.commit_relocation_transaction(caller, 1111, rid, epoch, proof, now_ms=3)
            record = storage.load_relocation_transaction(ReadOnlyDatabase(db), 1111, rid, epoch, proof.offer.transfer_id)
            assert record.checkpoint.address == before.address
            assert record.checkpoint.entry_version == before.entry_version
            assert record.checkpoint.transfer_id == before.transfer_id
    with tempfile.TemporaryDirectory(prefix='world-relocation-unknown-') as folder:
        store, rid, epoch, owner, proof, before = fixture(folder, adopted=False)
        assert before is None
        with closing(store.connect()) as db, db:
            db.execute('BEGIN')
            caller = ReadOnlyDatabase(db)
            refused(lambda: storage.begin_relocation_transaction(caller, 1111, rid, epoch, proof, now_ms=2))
            refused(lambda: storage.load_relocation_transaction(caller, 1111, rid, epoch, proof.offer.transfer_id))
            assert load_map_instance_transaction(caller, 1111, rid, epoch) is None


def no_history_case():
    with tempfile.TemporaryDirectory(prefix='world-relocation-no-history-') as folder:
        store, rid, epoch, owner, proof, before = fixture(folder, adopted=False)
        fresh_epoch = store.acquire_lease(1111, rid)
        with closing(store.connect()) as db, db:
            db.execute('BEGIN')
            caller = ReadOnlyDatabase(db)
            assert storage.prepare_relocation_recovery_transaction(caller, 1111, rid, fresh_epoch) is None
            refused(lambda: storage.prepare_relocation_recovery_transaction(caller, 9999, rid, fresh_epoch))
            refused(lambda: storage.prepare_relocation_recovery_transaction(caller, 1111, rid,
                fresh_epoch, expected_prepared=proof))
            assert load_map_instance_transaction(caller, 1111, rid, fresh_epoch) is None
        assert owner.location(rid) == proof.frozen


def recovery_rollback_case():
    with tempfile.TemporaryDirectory(prefix='world-relocation-recovery-rollback-') as folder:
        store, rid, epoch, owner, proof, before = fixture(folder)
        fresh_epoch = store.acquire_lease(1111, rid)
        with closing(store.connect()) as db, db:
            db.execute('CREATE TABLE caller_probe(value TEXT NOT NULL)')
            db.execute("INSERT INTO caller_probe VALUES('before')")
            db.execute("CREATE TRIGGER refuse_recovery BEFORE UPDATE OF stage ON world_relocations "
                "WHEN NEW.stage='cancelled' BEGIN SELECT RAISE(ABORT,'late-recovery-fault'); END")
        try:
            with closing(store.connect()) as db, db:
                db.execute('BEGIN IMMEDIATE')
                db.execute("UPDATE caller_probe SET value='changed'")
                storage.prepare_relocation_recovery_transaction(CallerDatabase(db), 1111, rid,
                    fresh_epoch, expected_prepared=proof)
        except sqlite3.IntegrityError as error:
            assert 'late-recovery-fault' in str(error)
        else:
            raise AssertionError('Late recovery fault did not abort caller transaction')
        with closing(store.connect()) as db, db:
            db.execute('BEGIN')
            caller = ReadOnlyDatabase(db)
            assert storage.load_relocation_transaction(caller, 1111, rid, fresh_epoch, proof.offer.transfer_id) is None
            checkpoint = load_map_instance_transaction(caller, 1111, rid, fresh_epoch)
            assert checkpoint.position == before.position and checkpoint.version == before.version
            assert db.execute('SELECT value FROM caller_probe').fetchone() == ('before',)
        assert owner.location(rid) == proof.frozen


GROUPS = dict(committed=committed_case, replay=replay_case,
              late_rollback=late_rollback_case, cancelled=cancelled_case, recovery=recovery_case,
              identity_guards=identity_guards_case, provenance=provenance_case,
              no_history=no_history_case, recovery_rollback=recovery_rollback_case)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--group', choices=tuple(GROUPS))
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    names = ('world_relocation_storage.py', 'verify_world_relocation_storage.py', 'world_owner.py',
        'world_transfer_storage.py', 'accounts.py', 'runtime_storage.py', 'world_catalog.py',
        'world_collision.py', 'world_grids.py', 'world_movement.py', 'catalogs/world.json',
        'catalogs/scene-content.json', 'evidence/world-recovery.json')
    def sources():
        return {name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in names}
    before = sources()
    result = dict(all_passed=False, passed=[], full_group_scope=args.group is None,
        source_sha256=before, current_workspace_test=True, caller_transactions_real_sqlite=True,
        role_and_authorized_source_fixture=True,
        old_in_process_member_retirement_verified=False, shared_runtime_integrated=False,
        actual_network_send_verified=False, native_gui_verified=False, live_server_changed=False,
        goal_complete=False)
    try:
        for name, test in GROUPS.items():
            if args.group is None or args.group == name:
                test()
                result['passed'].append(name)
                print('PASS '+name, flush=True)
        result['all_passed'] = True
    except Exception as error:
        result.update(error=repr(error), traceback=traceback.format_exc())
        raise
    finally:
        result['inputs_stable'] = before == sources()
        result['cold_owner_rebuild_fixture_verified'] = 'recovery' in result['passed']
        suffix = '-'+args.group if args.group else ''
        path = args.report or root/('evidence/world-relocation-storage-verification'+suffix+'.json')
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf8')
    assert result['inputs_stable']


if __name__ == '__main__':
    main()
