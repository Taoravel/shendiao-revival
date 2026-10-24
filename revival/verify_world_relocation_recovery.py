"""Immutable old-member inspection and new-lease relocation cleanup."""
from dataclasses import replace
from contextlib import closing
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import struct
import traceback
from unittest.mock import patch

from verify_world_relocation import fixture, refused


def snapshot_case():
    owner, view, offer = fixture(paired=True)
    before = owner.inspect_relocation(1, offer.transfer_id, view=view)
    assert before.location == offer.source and before.prepared is None
    assert type(before.membership_id) is str and before.membership_id
    assert before.projection_generation == view.owner_generation
    assert before.presence == view.snapshot(1)
    prepared = owner.freeze_relocation(offer, 1, movement_state=0, view=view)
    frozen = owner.inspect_relocation(1, offer.transfer_id, view=view)
    assert frozen.location == prepared.frozen and frozen.prepared == prepared
    assert frozen.membership_id == before.membership_id and frozen.result is None
    assert owner.inspect_relocations(1, view=view) == (frozen,)
    receipt, _ = owner.commit_relocation(prepared, view=view)
    loading = owner.inspect_relocation(1, offer.transfer_id, view=view)
    assert loading.result == receipt and loading.location == prepared.target
    assert loading.membership_id != frozen.membership_id
    assert loading.presence is None and loading.projection_generation == before.projection_generation
    active, _ = owner.ready_with_view(receipt.location, None, view)
    ready = owner.inspect_relocation(1, offer.transfer_id, view=view)
    assert ready.membership_id == loading.membership_id and ready.location == active
    owner.leave_with_view(active, view)
    left = owner.inspect_relocation(1, offer.transfer_id, view=view)
    assert left.location is None and left.membership_id is None and left.detached
    owner.retire_relocation(receipt)
    assert owner.inspect_relocations(1, view=view) == ()


def retire_case():
    from world_owner import RelocationRecoveryDecision
    owner, view, offer = fixture(paired=True)
    prepared = owner.freeze_relocation(offer, 1, movement_state=0, view=view)
    snapshot = owner.inspect_relocation(1, offer.transfer_id, view=view)
    authority = replace(prepared.target, login_epoch='new-recovery-lease', state='active')
    decision = RelocationRecoveryDecision(prepared, authority, True)
    retired, change = owner.retire_recovered_relocation(snapshot, decision, view=view)
    assert retired.removed == prepared.frozen and retired.record_removed
    assert retired.authority == authority and not change.deliveries
    assert owner.location(1) is None and view.snapshot(1) is None
    assert owner.inspect_relocations(1, view=view) == ()
    repeated, change = owner.retire_recovered_relocation(snapshot, decision, view=view)
    assert repeated.removed is None and not repeated.record_removed and change.presence is None
    owner.join_with_view(authority, None, view)
    current = view.snapshot(1)
    refused(lambda: owner.retire_recovered_relocation(snapshot, decision, view=view))
    assert owner.location(1) == authority and view.snapshot(1) == current


def sql_recovery_case():
    import world_relocation_storage as storage
    from verify_world_relocation_storage import fixture as sql_fixture, CallerDatabase
    from world_owner import Location, MoveCommand, RelocationRecoveryDecision
    for mode in ('freeze-gap', 'prepared', 'committed', 'loading', 'ready', 'cancelled', 'later-walking'):
        with tempfile.TemporaryDirectory(prefix='world-relocation-live-recovery-') as folder:
            store, rid, epoch, owner, proof, before = sql_fixture(folder)
            if mode != 'freeze-gap':
                with closing(store.connect()) as db, db:
                    db.execute('BEGIN IMMEDIATE')
                    caller = CallerDatabase(db)
                    storage.begin_relocation_transaction(caller, 1111, rid, epoch, proof, now_ms=2)
                    if mode not in ('prepared', 'cancelled'):
                        storage.commit_relocation_transaction(caller, 1111, rid, epoch, proof, now_ms=3)
                    elif mode == 'cancelled':
                        storage.cancel_relocation_transaction(caller, 1111, rid, epoch, proof)
            if mode in ('loading', 'ready', 'later-walking'):
                receipt, _ = owner.commit_relocation(proof)
                if mode != 'loading':
                    active = owner.ready(receipt.location)
                    if mode == 'later-walking':
                        moved = owner.move(MoveCommand(active, 'last-old-walking', 20000, 0xc0faa,
                            b'\0'+struct.pack('>hhQ', 1617, 1840, 1627), 0, 'native_current'), 4)
                        assert not moved.rejection
                        store.save_checkpoint(1111, rid, epoch, moved.location.position, moved.location.version)
            elif mode == 'cancelled':
                owner.cancel_relocation(proof)
            snapshot = owner.inspect_relocation(rid, proof.offer.transfer_id)
            if mode == 'freeze-gap':
                discovered = owner.inspect_relocations(rid)
                assert discovered == (snapshot,) and discovered[0].prepared == proof
            fresh_epoch = store.acquire_lease(1111, rid)
            with closing(store.connect()) as db, db:
                db.execute('BEGIN IMMEDIATE')
                record = storage.prepare_relocation_recovery_transaction(CallerDatabase(db), 1111, rid,
                    fresh_epoch, proof.offer.transfer_id,
                    expected_prepared=snapshot.prepared if mode == 'freeze-gap' else None)
            cp = record.checkpoint
            authority = Location(rid, fresh_epoch, cp.address, cp.version, *cp.position[1:])
            decision = RelocationRecoveryDecision(record.prepared, authority, record.stage == 'committed')
            retired, _ = owner.retire_recovered_relocation(snapshot, decision)
            assert retired.removed == snapshot.location and owner.location(rid) is None
            assert owner.inspect_relocations(rid) == ()
            # Use the SAME in-process map owner after removing the old member.
            # No duplicate owner or guessed replacement instance is created.
            owner.join(authority)
            moved = owner.move(MoveCommand(authority, 'new-lease-walking', 20000, 0xc0faa,
                b'\0'+struct.pack('>hhQ', authority.x+1, authority.y, 1627), 0, 'native_current'), 5)
            assert not moved.rejection
            assert store.save_checkpoint(1111, rid, fresh_epoch, moved.location.position, moved.location.version)
            refused(lambda: owner.retire_recovered_relocation(snapshot, decision))
            assert owner.location(rid) == moved.location


def member_aba_case():
    from world_owner import RelocationRecoveryDecision
    for paired in (False, True):
        owner, view, offer = fixture(paired=paired)
        proof = owner.freeze_relocation(offer, 1, movement_state=0, view=view)
        receipt, _ = owner.commit_relocation(proof, view=view)
        active = owner.ready(receipt.location) if view is None else owner.ready_with_view(receipt.location, None, view)[0]
        owner.retire_relocation(receipt)
        old = owner.inspect_relocation(1, offer.transfer_id, view=view)
        # No operation record remains: the relation identity must still catch
        # equal-coordinate/epoch/version re-entry, including the bare owner.
        if view is None:
            owner.leave(active)
            owner.join(active)
        else:
            owner.leave_with_view(active, view)
            owner.join_with_view(active, None, view)
        current = owner.inspect_relocation(1, offer.transfer_id, view=view)
        assert current.location == old.location and current.membership_id != old.membership_id
        decision = RelocationRecoveryDecision(proof,
            replace(proof.target, state='active', login_epoch='fenced-new-epoch'), True)
        refused(lambda: owner.retire_recovered_relocation(old, decision, view=view))
        assert owner.inspect_relocation(1, offer.transfer_id, view=view) == current


def typed_and_stale_case():
    from world_owner import RelocationRecoveryDecision
    owner, view, offer = fixture(paired=True)
    proof = owner.freeze_relocation(offer, 1, movement_state=0, view=view)
    snapshot = owner.inspect_relocation(1, offer.transfer_id, view=view)
    authority = replace(proof.target, state='active', login_epoch='fenced-new-epoch')
    decision = RelocationRecoveryDecision(proof, authority, True)
    bad = (replace(decision, committed=1),
        replace(decision, authority=replace(authority, login_epoch=offer.source.login_epoch)),
        replace(decision, authority=replace(authority, role_id=True)),
        replace(decision, authority=replace(authority, version=True)),
        replace(decision, authority=replace(authority, x=authority.x+1)),
        replace(decision, authority=replace(authority,
            address=replace(authority.address, instance_id=authority.address.instance_id+1))))
    for invalid in bad:
        refused(lambda: owner.retire_recovered_relocation(snapshot, invalid, view=view))
        assert owner.inspect_relocation(1, offer.transfer_id, view=view) == snapshot
    refused(lambda: owner.retire_recovered_relocation(replace(snapshot, role_id=True), decision, view=view))
    refused(lambda: owner.retire_recovered_relocation(replace(snapshot, membership_id=True), decision, view=view))
    refused(lambda: owner.retire_recovered_relocation(replace(snapshot,
        address=replace(snapshot.address, partition_id=0.0)), decision, view=view))
    cold, cold_view, _ = fixture(paired=True)
    refused(lambda: cold.retire_recovered_relocation(snapshot, decision, view=cold_view))
    assert owner.inspect_relocation(1, offer.transfer_id, view=view) == snapshot


def projection_identity_case():
    from world_owner import RelocationRecoveryDecision
    from world_roles import RoleScene
    from world_role_protocol import RoleBasic
    owner, _, offer = fixture()
    view = RoleScene(owner.address, owner.catalog, radius=64, role_capacity=2, pair_capacity=1, batch_size=1)
    shape = RoleBasic(1, 'projection-fixture', 9, offer.source.x, offer.source.y, 0x71)
    owner.join_with_view(offer.source, shape, view)
    proof = owner.freeze_relocation(offer, 1, movement_state=0, view=view)
    owner.commit_relocation(proof, view=view)
    snapshot = owner.inspect_relocation(1, offer.transfer_id, view=view)
    assert snapshot.presence is None
    decision = RelocationRecoveryDecision(proof,
        replace(proof.target, state='active', login_epoch='new-projection-lease'), True)
    foreign = RoleScene(owner.address, owner.catalog, radius=64, role_capacity=2, pair_capacity=1, batch_size=1)
    refused(lambda: owner.retire_recovered_relocation(snapshot, decision, view=foreign))
    refused(lambda: owner.retire_recovered_relocation(snapshot, decision))
    assert owner.inspect_relocation(1, offer.transfer_id, view=view) == snapshot
    retired, _ = owner.retire_recovered_relocation(snapshot, decision, view=view)
    assert retired.record_removed and owner.location(1) is None
    repeated, _ = owner.retire_recovered_relocation(snapshot, decision, view=view)
    assert repeated.removed is None and not repeated.record_removed
    refused(lambda: owner.retire_recovered_relocation(snapshot, decision, view=foreign))
    refused(lambda: owner.retire_recovered_relocation(snapshot, decision))


def unrelated_member_case():
    from world_owner import Location, MoveCommand, RelocationRecoveryDecision
    owner, view, offer = fixture(paired=True)
    proof = owner.freeze_relocation(offer, 1, movement_state=0, view=view)
    snapshot = owner.inspect_relocation(1, offer.transfer_id, view=view)
    other = Location(2, 'other-role-lease', owner.address, 1, 1832, 1304)
    owner.join_with_view(other, None, view)
    other_before = owner.inspect_relocation(2, 'other-inspection', view=view)
    moved, _ = owner.move_with_view(MoveCommand(other, 'other-movement', 1000, 0xc0faa,
        b'\0'+struct.pack('>hhQ', 1833, 1304, 1627), 0, 'native_current'), 2, view)
    assert not moved.rejection
    authority = replace(proof.target, login_epoch='new-one-lease', state='active')
    retired, _ = owner.retire_recovered_relocation(snapshot,
        RelocationRecoveryDecision(proof, authority, True), view=view)
    assert retired.removed == proof.frozen and owner.location(1) is None
    other_after = owner.inspect_relocation(2, 'other-inspection', view=view)
    assert other_after.location == moved.location and other_after.membership_id == other_before.membership_id
    assert view.snapshot(2).location == moved.location


def foreign_operation_case():
    from world_owner import RelocationRecoveryDecision
    owner, _, offer = fixture()
    proof = owner.freeze_relocation(offer, 1, movement_state=0)
    receipt, _ = owner.commit_relocation(proof)
    active = owner.ready(receipt.location)
    owner.prepare_transfer(active, (1007,8480,6976), request_id='another-cross-operation',
                           deadline_ms=1000, now_ms=2)
    snapshot = owner.inspect_relocation(1, offer.transfer_id)
    decision = RelocationRecoveryDecision(proof,
        replace(proof.target, login_epoch='new-operation-lease', state='active'), True)
    refused(lambda: owner.retire_recovered_relocation(snapshot, decision))
    assert owner.inspect_relocation(1, offer.transfer_id) == snapshot


def transfer_relation_case():
    from world_catalog import maps, maze_grids
    from world_owner import MapOwner, MapAddress, MoveCommand
    owner, _, offer = fixture()
    source = owner.move(MoveCommand(offer.source, 'clear-old-offer', 1000, 0xc0faa,
        b'\0'+struct.pack('>hhQ', 1832, 1304, 1627), 0, 'native_current'), 1).location
    original = owner.inspect_relocation(1, 'no-relocation')
    cross = owner.prepare_transfer(source, (1007,8480,6976), request_id='cross-relation',
                                   deadline_ms=1000, now_ms=2)
    target = MapOwner(MapAddress(1007, 7, 0), maps(), capacity=2, transfer_capacity=2,
                      mailbox_capacity=2, maze=maze_grids()[1007])
    reserved = target.reserve(cross, 2)
    frozen = owner.freeze(reserved, 2)
    assert owner.inspect_relocation(1, 'no-relocation').membership_id == original.membership_id
    receipt = target.activate(frozen, 2)
    loading = target.inspect_relocation(1, 'no-relocation')
    assert loading.location == receipt.location and loading.membership_id
    owner.finalize(receipt)
    assert owner.inspect_relocation(1, 'no-relocation').membership_id is None
    active = target.ready(receipt.location)
    assert target.inspect_relocation(1, 'no-relocation').membership_id == loading.membership_id
    target.leave(active)
    assert target.inspect_relocation(1, 'no-relocation').membership_id is None


def later_instance_case():
    import world_relocation_storage as storage
    import world_transfer_storage as transfers
    from verify_world_relocation_storage import fixture as sql_fixture, CallerDatabase
    from world_catalog import maps, maze_grids
    from world_owner import MapOwner, MapAddress, Location, MoveCommand, RelocationRecoveryDecision
    with tempfile.TemporaryDirectory(prefix='world-relocation-later-instance-') as folder:
        store, rid, epoch, owner, proof, _ = sql_fixture(folder)
        with closing(store.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            caller = CallerDatabase(db)
            storage.begin_relocation_transaction(caller, 1111, rid, epoch, proof, now_ms=2)
            storage.commit_relocation_transaction(caller, 1111, rid, epoch, proof, now_ms=3)
        receipt, _ = owner.commit_relocation(proof)
        active = owner.ready(receipt.location)
        assert store.save_checkpoint(1111, rid, epoch, active.position, active.version)
        destination = MapAddress(1007, 2**40+99, 4)
        target = MapOwner(destination, maps(), capacity=2, transfer_capacity=2,
                          mailbox_capacity=2, maze=maze_grids()[1007])
        offer = owner.prepare_transfer(active, (1007,8480,6976), request_id='later-complete-instance',
                                       deadline_ms=20000, now_ms=4)
        transfers.begin(store, 1111, rid, epoch, offer)
        cross = target.activate(owner.freeze(target.reserve(offer, 4), 4), 4)
        with closing(store.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            transfers.commit_transfer_transaction(CallerDatabase(db), 1111, rid, epoch, cross)
        owner.finalize(cross)
        target.ready(cross.location)
        fresh_epoch = store.acquire_lease(1111, rid)
        with closing(store.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            caller = CallerDatabase(db)
            cross_decision = transfers.prepare_transfer_recovery_transaction(caller, 1111, rid,
                fresh_epoch, offer.transfer_id)
            record = storage.prepare_relocation_recovery_transaction(caller, 1111, rid,
                fresh_epoch, proof.offer.transfer_id)
        owner.retire_recovered_transfer(owner.inspect_transfer(rid, offer.transfer_id), cross_decision)
        target.retire_recovered_transfer(target.inspect_transfer(rid, offer.transfer_id), cross_decision)
        assert target.inspect_relocation(rid, 'unrelated-inspection').membership_id is None
        cp = record.checkpoint
        assert cp.address == destination and cp.position == (1007,8480,6976)
        authority = Location(rid, fresh_epoch, cp.address, cp.version, *cp.position[1:])
        snapshot = owner.inspect_relocation(rid, proof.offer.transfer_id)
        retired, _ = owner.retire_recovered_relocation(snapshot,
            RelocationRecoveryDecision(record.prepared, authority, True))
        assert retired.record_removed and retired.removed is None and owner.location(rid) is None
        assert target.location(rid) is None
        target.join(authority)
        result = target.move(MoveCommand(authority, 'later-new-login-step', 20000, 0xc0faa,
            b'\0'+struct.pack('>hhQ', 8481, 6976, 1007), 0, 'native_current'), 5)
        assert not result.rejection and result.location.address == destination
        assert store.position(1111, rid) == cp.position


def hot_path_case():
    from world_owner import RelocationRecoveryDecision
    owner, view, offer = fixture(paired=True)
    proof = owner.freeze_relocation(offer, 1, movement_state=0, view=view)
    decision = RelocationRecoveryDecision(proof,
        replace(proof.target, state='active', login_epoch='hot-new-lease'), True)
    with patch('builtins.open', side_effect=AssertionError('hot file access')), \
            patch.object(Path, 'open', side_effect=AssertionError('hot path access')):
        snapshot = owner.inspect_relocation(1, offer.transfer_id, view=view)
        assert owner.inspect_relocations(1, view=view) == (snapshot,)
        retired, _ = owner.retire_recovered_relocation(snapshot, decision, view=view)
        assert retired.removed == proof.frozen
        owner.join_with_view(decision.authority, None, view)
        refused(lambda: owner.retire_recovered_relocation(snapshot, decision, view=view))


GROUPS = dict(snapshot=snapshot_case, retirement=retire_case, sql_windows=sql_recovery_case,
    member_aba=member_aba_case, typed_stale=typed_and_stale_case, projection=projection_identity_case,
    unrelated=unrelated_member_case, foreign=foreign_operation_case,
    cross_relation=transfer_relation_case, later_instance=later_instance_case, hot_path=hot_path_case)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--group', choices=tuple(GROUPS))
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    names = ('world_owner.py', 'world_roles.py', 'world_relocation_storage.py', 'world_transfer_storage.py',
        'verify_world_relocation_recovery.py', 'verify_world_relocation.py', 'verify_world_relocation_storage.py',
        'accounts.py', 'runtime_storage.py', 'world_catalog.py', 'world_collision.py',
        'world_movement.py', 'world_grids.py', 'catalogs/world.json', 'catalogs/scene-content.json',
        'evidence/world-recovery.json')
    def sources():
        return {name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in names}
    before = sources()
    result = dict(all_passed=False, passed=[], full_group_scope=args.group is None,
        source_sha256=before, real_sqlite_transactions=True, actual_map_owner_reused=True,
        sql_actor_and_checkpoint_fixture=True, full_projection_appearance_fixture=True,
        shared_runtime_integrated=False, actual_network_send_verified=False,
        native_gui_verified=False, live_server_changed=False, goal_complete=False)
    try:
        for name, check in GROUPS.items():
            if args.group is None or args.group == name:
                check()
                result['passed'].append(name)
                print('PASS '+name, flush=True)
        result['all_passed'] = True
    except Exception as error:
        result.update(error=repr(error), traceback=traceback.format_exc())
        raise
    finally:
        result['inputs_stable'] = before == sources()
        suffix = '-'+args.group if args.group else ''
        path = args.report or root/('evidence/world-relocation-recovery-verification'+suffix+'.json')
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf8')
    assert result['inputs_stable']


if __name__ == '__main__':
    main()
