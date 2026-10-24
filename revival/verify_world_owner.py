"""Behavior checks at the map owner's message/snapshot Interface."""
from dataclasses import replace
import struct
from unittest.mock import patch
from inspect_client import OUT, write_json
from world_catalog import maps
from world_owner import MapAddress, Location, MoveCommand, MapOwner


def stop(x=8496, y=6992):
    return b'\0'+struct.pack('>hhQ', x, y, 0)


def main():
    catalog = maps()
    source = MapOwner(MapAddress(1007, 1, 0), catalog, capacity=2, transfer_capacity=2, mailbox_capacity=2)
    initial = Location(1, 10, source.address, 1, 8480, 6976)
    source.join(initial)
    cmd = MoveCommand(initial, 'move-1', 100, 0xc0faa, stop())
    moved = source.move(cmd, now_ms=1)
    assert moved.location.position == (1007, 8496, 6992)
    assert moved.location.version == 2 and moved.checkpoint == moved.location
    assert source.move(cmd, now_ms=1).rejection == 'stale_position'
    old_login = replace(cmd, expected=replace(moved.location, login_epoch=9))
    assert source.move(old_login, now_ms=1).rejection == 'stale_epoch'
    expired = replace(cmd, expected=moved.location, deadline_ms=0)
    assert source.move(expired, now_ms=1).rejection == 'deadline'
    assert source.location(1) == moved.location
    print('PASS map owner fences stale epoch/version and expired commands')
    portal_cmd = MoveCommand(moved.location, 'portal-1', 100, 0xc0faa, stop(8592, 7104))
    portal = source.move(portal_cmd, now_ms=2)
    assert portal.offer is not None, 'Portal must produce a reservable transfer offer'
    assert source.location(1).position == (1007, 8592, 7104), 'Source changed before handoff'
    target = MapOwner(MapAddress(1014, 2, 0), catalog, capacity=2, transfer_capacity=2, mailbox_capacity=2)
    reservation = target.reserve(portal.offer, now_ms=3)
    assert target.location(1) is None, 'Reservation became active prematurely'
    frozen = source.freeze(reservation, now_ms=4)
    while_frozen = MoveCommand(frozen.source, 'late-source', 100, 0xc0faa, stop())
    assert source.move(while_frozen, now_ms=5).rejection == 'movement_frozen'
    committed = target.activate(frozen, now_ms=6)
    assert target.activate(frozen, now_ms=6) == committed
    assert committed.location.position == (1014, 896, 3776)
    assert committed.location.state == 'loading'
    source.finalize(committed)
    source.finalize(committed)
    assert source.location(1) is None
    target_move = MoveCommand(committed.location, 'target-before-ready', 100, 0xc0faa, stop(900, 3776))
    assert target.move(target_move, now_ms=7).rejection == 'movement_frozen'
    ready = target.ready(committed.location)
    assert ready.version > committed.location.version and ready.state == 'active'
    assert target.move(target_move, now_ms=7).rejection == 'stale_position'
    print('PASS reserve/freeze/activate/finalize; loading fence; duplicate commit')
    rollback_source = MapOwner(MapAddress(1007, 3, 0), catalog, capacity=2, transfer_capacity=2, mailbox_capacity=1)
    rollback_initial = replace(initial, address=rollback_source.address)
    rollback_source.join(rollback_initial)
    offer = rollback_source.move(MoveCommand(rollback_initial, 'rollback-1', 100,
                                              0xc0faa, stop(8592, 7104)), now_ms=1).offer
    rollback_target = MapOwner(MapAddress(1014, 4, 0), catalog, capacity=1, transfer_capacity=2, mailbox_capacity=1)
    reserved = rollback_target.reserve(offer, now_ms=1)
    freeze = rollback_source.freeze(reserved, now_ms=2)
    cancelled = rollback_target.cancel(reserved)
    resumed = rollback_source.resume(cancelled)
    assert resumed.state == 'active' and resumed.position == (1007, 8592, 7104)
    assert resumed.version > freeze.source.version
    assert rollback_source.resume(cancelled) == resumed
    try:
        rollback_target.activate(freeze, now_ms=3)
    except ValueError:
        pass
    else:
        raise AssertionError('Cancelled target activated')
    try:
        target.cancel(reservation)
    except ValueError:
        pass
    else:
        raise AssertionError('Committed target rolled back')
    print('PASS cancelled reservations thaw source; commit cannot roll back')
    mailbox = MapOwner(MapAddress(1007, 5, 0), catalog, capacity=1, transfer_capacity=1, mailbox_capacity=1)
    occupant = replace(initial, address=mailbox.address)
    mailbox.join(occupant)
    message = MoveCommand(occupant, 'queued-1', 100, 0xc0faa, stop())
    assert mailbox.submit(message, now_ms=1) == 'accepted'
    assert mailbox.submit(message, now_ms=1) == 'backpressure'
    # Another partition advances with the first mailbox full and unprocessed.
    other = MapOwner(MapAddress(1007, 6, 0), catalog, capacity=1, transfer_capacity=1, mailbox_capacity=1)
    other_initial = replace(initial, role_id=2, address=other.address)
    other.join(other_initial)
    with patch('builtins.open', side_effect=AssertionError('Owner disk access')), \
         patch('io.open', side_effect=AssertionError('Owner disk access')):
        assert other.move(MoveCommand(other_initial, 'other-1', 100, 0xc0faa, stop()), now_ms=1).checkpoint
        assert mailbox.process_one(now_ms=2).checkpoint
    assert mailbox.process_one(now_ms=2) is None
    assert mailbox.submit(message, now_ms=2) == 'accepted'
    assert mailbox.process_one(now_ms=2).rejection == 'stale_position'
    previous = mailbox.location(1)
    mailbox.leave(previous)
    replacement = replace(previous, login_epoch=11, version=1)
    mailbox.join(replacement)
    assert mailbox.submit(replace(message, expected=previous), now_ms=3) == 'accepted'
    assert mailbox.process_one(now_ms=3).rejection == 'stale_epoch'
    try:
        mailbox.leave(previous)
    except ValueError:
        pass
    else:
        raise AssertionError('Old disconnect removed new login')
    assert mailbox.location(1) == replacement
    print('PASS bounded independent mailboxes; dequeue rechecks version; no hot-path file access')
    timeout_source = MapOwner(MapAddress(1007, 7, 0), catalog, capacity=1, transfer_capacity=1, mailbox_capacity=1)
    timeout_initial = replace(initial, address=timeout_source.address)
    timeout_source.join(timeout_initial)
    timeout_offer = timeout_source.move(MoveCommand(timeout_initial, 'timeout-1', 10,
                                                   0xc0faa, stop(8592, 7104)), now_ms=1).offer
    timeout_target = MapOwner(MapAddress(1014, 8, 0), catalog, capacity=1, transfer_capacity=1, mailbox_capacity=1)
    timeout_reservation = timeout_target.reserve(timeout_offer, now_ms=2)
    timeout_frozen = timeout_source.freeze(timeout_reservation, now_ms=3)
    try:
        timeout_target.activate(timeout_frozen, now_ms=10)
    except ValueError:
        pass
    else:
        raise AssertionError('Expired target activated')
    assert timeout_source.location(1).state == 'frozen'
    timeout_source.resume(timeout_target.cancel(timeout_reservation))
    assert timeout_source.location(1).state == 'active'
    print('PASS timeout keeps source frozen until target cancellation')
    next_offer = replace(timeout_offer, transfer_id='capacity-2', deadline_ms=100,
                         source=replace(timeout_offer.source, role_id=2))
    try:
        timeout_target.reserve(next_offer, now_ms=11)
    except ValueError as error:
        assert str(error) == 'Transfer receipt capacity'
    else:
        raise AssertionError('Unbounded transfer receipts')
    timeout_target.retire_receipt(timeout_target.cancel(timeout_reservation))
    assert timeout_target.reserve(next_offer, now_ms=11).offer == next_offer
    print('PASS transfer receipt backpressure and explicit retirement')
    write_json(OUT/'evidence/world-owner-verification.json', {
        'passed': ['epoch/version/deadline fencing', 'bounded independent mailboxes',
                   'dequeue state revalidation', 'source stays until target reservation',
                   'freeze/activate/finalize', 'duplicate commit and finalize', 'loading fence',
                   'idempotent cancellation/resume', 'committed target rejects cancellation',
                   'expired target cannot activate', 'timeout does not auto-thaw source',
                   'owner hot path no file access', 'bounded receipt retention/retirement'],
        'runtime_integrated': False, 'durable_handoff_journal': False,
        'live_client_verified': False, 'capacity_benchmark_performed': False})


if __name__ == '__main__': main()
