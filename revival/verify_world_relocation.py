"""Same-instance relocation through actual MapOwner and original 1627 data.

Explicit offline role/checkpoint fixture, not natural client traversal.
"""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import struct
from unittest.mock import patch

from world_catalog import maps, maze_grids
from world_collision import maze_clear
from world_owner import MapOwner, MapAddress, Location, MoveCommand
from verify_world_resource_handoffs import approach
from inspect_client import ROOT
from pfs import PfsArchive
from bxml import decode


def refused(action):
    try:
        action()
    except ValueError:
        return
    raise AssertionError('Stale, conflicting or malformed relocation accepted')


def fixture(*, paired=False, capacity=2, lifecycle=False, instance_id=1627):
    catalog, grids = maps(), maze_grids()
    address = MapAddress(1627, instance_id, 0)
    owner = MapOwner(address, catalog, capacity=capacity, transfer_capacity=1,
                     mailbox_capacity=2, maze=grids[1627])
    if lifecycle:
        owner.configure_lifecycle(scene_delivery_capacity=1, actor_state='static_original')
    view = owner.member_projection(role_capacity=capacity) if paired else None
    for cell, target in sorted(catalog[1627]['portals'].items()):
        leg = approach(1627, cell, catalog, grids[1627])
        if (leg is not None and target[0] == 1627
                and maze_clear(grids[1627], *leg[1], mask=1)
                and maze_clear(grids[1627], *target[1:], mask=1)):
            break
    else:
        raise AssertionError('Original 1627 lacks a clear same-instance witness')
    assert leg == ((1816,1304),(1832,1304))
    source = Location(1, 'relocation-fixture', address, 1, *leg[0])
    if view is None:
        owner.join(source)
    else:
        owner.join_with_view(source, None, view)
    command = MoveCommand(source, 'original-1627', 1000, 0xc0faa,
        b'\0'+struct.pack('>hhQ', *leg[1], 1627), 0, 'native_current')
    result = owner.move(command, 0) if view is None else owner.move_with_view(command, 0, view)[0]
    assert not result.rejection and result.offer is not None
    assert result.offer.target_position == (1627, 1616, 1840)
    return owner, view, result.offer


def freeze_case():
    owner, view, offer = fixture()
    refused(lambda: owner.reserve(offer, 0))
    frozen = owner.freeze_relocation(offer, 1, movement_state=0)
    assert owner.location(1) == frozen.frozen
    assert frozen.frozen.position == offer.source.position
    assert frozen.frozen.state == 'frozen' and frozen.frozen.version == 3
    assert frozen.target.position == (1627, 1616, 1840)
    assert frozen.target.state == 'loading' and frozen.target.version == 4
    blocked = owner.move(MoveCommand(frozen.frozen, 'while-frozen', 1000,
        0xc0faa, b'\0'+struct.pack('>hhQ', 1616, 1840, 1627), 0, 'native_current'), 2)
    assert blocked.rejection == 'movement_frozen'


def commit_case():
    owner, view, offer = fixture(paired=True, capacity=1)
    original = owner.role_binding(view.snapshot(1), view, 7)
    prepared = owner.freeze_relocation(offer, 1, movement_state=0, view=view)
    receipt, change = owner.commit_relocation(prepared, view=view)
    assert owner.location(1) == receipt.location == prepared.target
    assert receipt.location.address == offer.source.address
    assert view.snapshot(1) is None and not change.deliveries
    again, change = owner.commit_relocation(prepared, view=view)
    assert again == receipt and change.presence is None
    active, change = owner.ready_with_view(receipt.location, None, view)
    assert active.position == (1627, 1616, 1840) and active.version == 5
    assert owner.role_binding(change.presence, view, 7) != original
    command = MoveCommand(active, 'after-relocation', 1000, 0xc0faa,
        b'\0'+struct.pack('>hhQ', 1617, 1840, 1627), 0, 'native_current')
    moved, _ = owner.move_with_view(command, 3, view)
    assert not moved.rejection and moved.location.position == (1627, 1617, 1840)
    refused(lambda: owner.commit_relocation(prepared, view=view))
    assert owner.location(1) == moved.location


def cancel_case():
    owner, view, offer = fixture(paired=True)
    before = view.snapshot(1)
    old_binding = owner.role_binding(before, view, 7)
    prepared = owner.freeze_relocation(offer, 1, movement_state=0, view=view)
    refused(lambda: owner.commit_relocation(prepared))
    refused(lambda: owner.cancel_relocation(prepared))
    refused(lambda: owner.role_binding(before, view, 7))
    cancelled, change = owner.cancel_relocation(prepared, view=view)
    assert cancelled.location == owner.location(1) == replace(offer.source, version=4)
    assert change.presence.location == cancelled.location
    assert owner.role_binding(change.presence, view, 7).membership_revision != old_binding.membership_revision
    again, change = owner.cancel_relocation(prepared, view=view)
    assert again == cancelled and not change.deliveries
    refused(lambda: owner.commit_relocation(prepared, view=view))


def replay_state_case():
    owner, view, offer = fixture()
    prepared = owner.freeze_relocation(offer, 1, movement_state=0)
    assert owner.freeze_relocation(offer, 1001, movement_state=0) == prepared
    refused(lambda: owner.freeze_relocation(offer, 2, movement_state=True))
    refused(lambda: owner.freeze_relocation(offer, 2, movement_state=8))
    refused(lambda: owner.commit_relocation(replace(prepared,
        target=replace(prepared.target, version=True))))
    cold, _, _ = fixture()
    refused(lambda: cold.commit_relocation(prepared))
    assert owner.location(1) == prepared.frozen


def receipt_lifecycle_case():
    owner, _, offer = fixture(lifecycle=True)
    prepared = owner.freeze_relocation(offer, 1, movement_state=0)
    refused(lambda: owner.retire_relocation(prepared))
    cancelled, _ = owner.cancel_relocation(prepared)
    owner.leave(cancelled.location)
    busy = owner.inspect_lifecycle(2)
    assert busy.members == 0 and busy.relocations == 1 and not busy.idle
    assert owner.retire_relocation(cancelled)
    assert not owner.retire_relocation(cancelled)
    empty = owner.inspect_lifecycle(3)
    assert empty.relocations == 0 and empty.idle
    owner.retire_idle(empty, 4, minimum_idle_ms=1)
    assert not owner.retire_relocation(cancelled)
    refused(lambda: owner.freeze_relocation(offer, 5, movement_state=0))


def receipt_capacity_case():
    owner, _, offer = fixture()
    prepared = owner.freeze_relocation(offer, 1, movement_state=0)
    cancelled, _ = owner.cancel_relocation(prepared)
    second = replace(offer.source, role_id=2, x=1816, y=1304, version=1)
    owner.join(second)
    result = owner.move(MoveCommand(second, 'second-offer', 1000, 0xc0faa,
        b'\0'+struct.pack('>hhQ', offer.source.x, offer.source.y, 1627), 0, 'native_current'), 2)
    assert result.offer is not None
    refused(lambda: owner.freeze_relocation(result.offer, 3, movement_state=0))
    assert owner.location(2) == result.location and owner.location(1) == cancelled.location
    other, _, other_offer = fixture(instance_id=2)
    assert other.freeze_relocation(other_offer, 3, movement_state=0).frozen.address.instance_id == 2
    assert owner.retire_relocation(cancelled)
    assert owner.freeze_relocation(result.offer, 4, movement_state=0).frozen.role_id == 2


def full_projection_case():
    from world_roles import RoleScene
    from world_role_protocol import RoleBasic
    owner, _, offer = fixture()
    view = RoleScene(owner.address, owner.catalog, radius=64,
        role_capacity=2, pair_capacity=0, batch_size=1)
    appearance = RoleBasic(1, 'offline-appearance', 9, offer.source.x, offer.source.y, 0x71)
    owner.join_with_view(offer.source, appearance, view)
    neighbor = Location(2, 'offline-neighbor', owner.address, 1, 1616, 1840)
    owner.join_with_view(neighbor, replace(appearance, role_id=2, x=1616, y=1840), view)
    prepared = owner.freeze_relocation(offer, 1, movement_state=0, view=view)
    receipt, _ = owner.commit_relocation(prepared, view=view)
    destination_appearance = replace(appearance, x=1616, y=1840)
    refused(lambda: owner.ready_with_view(receipt.location, destination_appearance, view))
    assert owner.location(1) == receipt.location and view.snapshot(1) is None
    owner.leave_with_view(neighbor, view)
    active, change = owner.ready_with_view(receipt.location, destination_appearance, view)
    assert active.version == 5 and change.presence.location == active
    refused(lambda: owner.cancel_relocation(prepared, view=view))


def hot_path_case():
    owner, view, offer = fixture(paired=True)
    with patch('builtins.open', side_effect=AssertionError('hot file access')), \
            patch.object(Path, 'open', side_effect=AssertionError('hot path access')):
        prepared = owner.freeze_relocation(offer, 1, movement_state=0, view=view)
        receipt, _ = owner.commit_relocation(prepared, view=view)
        owner.ready_with_view(receipt.location, None, view)
        owner.retire_relocation(receipt)


def member_rejoin_case():
    for paired in (False, True):
        for commit in (False, True):
            owner, view, offer = fixture(paired=paired)
            prepared = owner.freeze_relocation(offer, 1, movement_state=0, view=view)
            if commit:
                receipt, _ = owner.commit_relocation(prepared, view=view)
                active = (owner.ready(receipt.location) if view is None else
                          owner.ready_with_view(receipt.location, None, view)[0])
            else:
                receipt, _ = owner.cancel_relocation(prepared, view=view)
                active = receipt.location
            if view is None:
                owner.leave(active)
                owner.join(active)
            else:
                owner.leave_with_view(active, view)
                owner.join_with_view(active, None, view)
            action = owner.commit_relocation if commit else owner.cancel_relocation
            refused(lambda: action(prepared, view=view))
            assert owner.location(1) == active
            if view is not None:
                assert view.snapshot(1).location == active
            assert owner.retire_relocation(receipt)


def retired_request_aba_case():
    owner, _, offer = fixture()
    old = owner.freeze_relocation(offer, 1, movement_state=0)
    cancelled, _ = owner.cancel_relocation(old)
    owner.leave(cancelled.location)
    owner.retire_relocation(cancelled)
    # Controlled ABA: even an equal request/location recreated after retirement
    # must not resurrect a callback from the previous accepted operation.
    start = replace(offer.source, version=1, x=1816, y=1304)
    owner.join(start)
    result = owner.move(MoveCommand(start, offer.transfer_id, 1000, 0xc0faa,
        b'\0'+struct.pack('>hhQ', 1832, 1304, 1627), 0, 'native_current'), 2)
    assert result.offer == offer
    fresh = owner.freeze_relocation(result.offer, 3, movement_state=0)
    assert fresh != old
    refused(lambda: owner.commit_relocation(old))
    refused(lambda: owner.cancel_relocation(old))
    assert owner.location(1) == fresh.frozen


def main():
    root = Path(__file__).resolve().parent
    inputs = ('world_owner.py', 'world_roles.py', 'world_catalog.py', 'world_collision.py',
              'world_movement.py', 'verify_world_relocation.py', 'verify_world_resource_handoffs.py',
              'catalogs/world.json', 'catalogs/scene-content.json', 'evidence/world-recovery.json')
    hashes = {name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in inputs}
    archive = PfsArchive(ROOT/'artres/map.pfs')
    directory = maps()[1627]['resdir']
    raw = {name:archive.read(directory+'/'+name) for name in ('goto.xml','maze.dat')}
    portals = [dict(row.attrib) for row in decode(raw['goto.xml'])]
    assert len(portals) == 25
    assert any((int(row['posx']),int(row['posy']),int(row['destmap']),
        int(row['destx']),int(row['desty'])) == (114,81,1627,101,115) for row in portals)
    cases = (freeze_case, commit_case, cancel_case, replay_state_case,
             receipt_lifecycle_case, receipt_capacity_case, full_projection_case, hot_path_case,
             member_rejoin_case, retired_request_aba_case)
    passed = []
    for case in cases:
        case()
        passed.append(case.__name__)
    assert hashes == {name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in inputs}
    assert raw == {name:archive.read(directory+'/'+name) for name in raw}
    report = dict(all_passed=True, groups=passed, source_sha256=hashes, inputs_stable=True,
        original_resource_sha256={directory+'/'+name:hashlib.sha256(body).hexdigest() for name,body in raw.items()},
        original_witness=dict(map_id=1627, approach=[1816,1304], portal=[1832,1304], target=[1616,1840]),
        role_source_checkpoint_fixture=True, full_projection_appearance_fixture=True,
        database_transaction_verified=False, crash_recovery_verified=False,
        actual_send_barrier_verified=False, shared_runtime_integrated=False,
        live_server_changed=False, native_gui_verified=False, goal_complete=False)
    (root/'evidence/world-relocation-domain-verification.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps(dict(all_passed=True, groups=passed, shared_runtime_integrated=False)))


if __name__ == '__main__':
    main()
