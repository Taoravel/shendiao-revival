"""Public map/member contract checks; no shared runtime, DB, wire or GUI."""
import argparse
from dataclasses import replace
import hashlib
import importlib
import json
from pathlib import Path
import struct
import sys

if __name__ == '__main__':
    bootstrap = argparse.ArgumentParser(add_help=False)
    bootstrap.add_argument('--domain-source', type=Path)
    selected, _ = bootstrap.parse_known_args()
    if selected.domain_source is not None:
        source = selected.domain_source.resolve(strict=True)
        if not all((source/name).is_file() for name in ('world_owner.py', 'world_roles.py')):
            raise ValueError('Both exact World domain files required')
        sys.path.insert(0, str(source))

from world_owner import MapOwner, MapAddress, Location, MoveCommand
from world_roles import RoleScene
from world_role_delivery import bind_role_view
from world_role_protocol import RoleBasic
from world_roles import RoleDelivery
from unittest.mock import patch


CATALOG = {mid: dict(available=True, width=1024, height=1024, portals={}) for mid in (7, 8)}
ADDRESS = MapAddress(7, 71, 0)


def admission():
    owner = MapOwner(ADDRESS, CATALOG, capacity=3, transfer_capacity=2, mailbox_capacity=2)
    members = owner.member_projection(role_capacity=2)
    first = Location(1, 'member-a', ADDRESS, 1, 100, 100)
    other = replace(first, role_id=2, login_epoch='member-b')
    a, aj = owner.join_with_view(first, None, members)
    b, bj = owner.join_with_view(other, None, members)
    assert (a, b) == (first, other)
    assert aj.presence.appearance is None and bj.presence.appearance is None
    assert not aj.deliveries and not bj.deliveries
    assert members.visible_ids(1) == members.visible_ids(2) == ()
    assert owner.join_with_view(first, None, members)[1] == aj
    third = replace(first, role_id=3, login_epoch='member-c')
    try:
        owner.join_with_view(third, None, members)
    except ValueError:
        pass
    else:
        raise AssertionError('Metadata capacity admitted a third role')
    assert owner.location(3) is None and members.snapshot(3) is None


def movement():
    owner = MapOwner(ADDRESS, CATALOG, capacity=2, transfer_capacity=2, mailbox_capacity=2)
    members = owner.member_projection(role_capacity=2)
    first = Location(1, 'member-a', ADDRESS, 1, 100, 100)
    _, joined = owner.join_with_view(first, None, members)
    binding = bind_role_view(joined.presence, 1)
    stop = b'\0'+struct.pack('>hhQ', 104, 100, 7)
    moved, change = owner.move_with_view(MoveCommand(first, 'move', 100, 0xc0faa, stop), 1, members)
    assert moved.checkpoint and moved.location.position == (7, 104, 100)
    assert change.presence.location == owner.location(1) == moved.location
    assert change.presence.appearance is None and not change.deliveries
    assert change.presence.revision > joined.presence.revision
    assert bind_role_view(change.presence, 1) == binding
    assert bind_role_view(change.presence, 2) == replace(binding, connection_generation=2)
    stale, rejected = owner.move_with_view(MoveCommand(first, 'late', 100, 0xc0faa, stop), 1, members)
    assert stale.rejection and rejected is None and members.snapshot(1) == change.presence


def departure():
    owner = MapOwner(ADDRESS, CATALOG, capacity=2, transfer_capacity=2, mailbox_capacity=2)
    members = owner.member_projection(role_capacity=2)
    first = Location(1, 'same-epoch', ADDRESS, 1, 100, 100)
    _, old = owner.join_with_view(first, None, members)
    departed, change = owner.leave_with_view(first, members)
    assert departed == first and change.presence is None and not change.deliveries
    assert owner.location(1) is None and members.snapshot(1) is None
    assert not owner.leave_with_view(first, members)[1].deliveries
    _, current = owner.join_with_view(first, None, members)
    assert current.presence.location == old.presence.location
    assert current.presence.membership_revision != old.presence.membership_revision
    try:
        members.leave(old.presence)
    except ValueError:
        pass
    else:
        raise AssertionError('Old presence removed exact-location replacement')
    assert members.snapshot(1) == current.presence and owner.location(1) == first
    cold_owner = MapOwner(ADDRESS, CATALOG, capacity=2, transfer_capacity=2, mailbox_capacity=2)
    cold = cold_owner.member_projection(role_capacity=2)
    cold_presence = cold_owner.join_with_view(first, None, cold)[1].presence
    assert bind_role_view(cold_presence, 1) != bind_role_view(current.presence, 1)


def refused(action):
    try:
        action()
    except ValueError:
        return
    raise AssertionError('Stale or foreign membership was accepted')


def binding_issuance():
    owner = MapOwner(ADDRESS, CATALOG, capacity=2, transfer_capacity=2, mailbox_capacity=2)
    members = owner.member_projection(role_capacity=2)
    first = Location(1, 1, ADDRESS, 1, 100, 100)
    _, joined = owner.join_with_view(first, None, members)
    binding = owner.role_binding(joined.presence, members, 1)
    assert binding == bind_role_view(joined.presence, 1)
    refused(lambda: owner.role_binding(replace(joined.presence, owner_generation='old'), members, 1))
    refused(lambda: owner.role_binding(joined.presence, members, True))
    owner.leave_with_view(first, members)
    _, replacement = owner.join_with_view(first, None, members)
    refused(lambda: owner.role_binding(joined.presence, members, 1))
    assert owner.role_binding(replacement.presence, members, 1) != binding
    target = MapOwner(MapAddress(8, 81, 0), CATALOG, capacity=2, transfer_capacity=2, mailbox_capacity=2)
    offer = owner.prepare_transfer(first, (8, 50, 50), request_id='freeze', deadline_ms=100, now_ms=1)
    owner.freeze(target.reserve(offer, 2), 3)
    assert members.snapshot(1) == replacement.presence
    refused(lambda: owner.role_binding(replacement.presence, members, 1))


def fencing():
    owner = MapOwner(ADDRESS, CATALOG, capacity=2, transfer_capacity=2, mailbox_capacity=2)
    members = owner.member_projection(role_capacity=2)
    first = Location(1, 1, ADDRESS, 1, 100, 100)
    _, joined = owner.join_with_view(first, None, members)
    other = replace(first, role_id=2, login_epoch=2)
    _, neighbor = owner.join_with_view(other, None, members)
    original = owner.role_binding(joined.presence, members, 1)
    fenced = owner.fence_role_binding(joined.presence, members)
    assert owner.location(1) == first and fenced.location == first
    assert fenced.membership_revision != joined.presence.membership_revision
    assert owner.role_binding(fenced, members, 1) != original
    assert members.snapshot(2) == neighbor.presence
    refused(lambda: owner.fence_role_binding(joined.presence, members))
    refused(lambda: owner.fence_role_binding(replace(fenced, membership_revision=True), members))
    refused(lambda: owner.fence_role_binding(replace(fenced, location=replace(first, login_epoch=True)), members))
    assert members.snapshot(1) == fenced
    owner.leave_with_view(first, members)
    _, new = owner.join_with_view(first, None, members)
    refused(lambda: owner.fence_role_binding(fenced, members))
    assert members.snapshot(1) == new.presence
    visible_owner = MapOwner(ADDRESS, CATALOG, capacity=1, transfer_capacity=1, mailbox_capacity=1)
    visible = RoleScene(ADDRESS, CATALOG, radius=64, role_capacity=1, pair_capacity=0, batch_size=1)
    _, legacy = visible_owner.join_with_view(first, RoleBasic(1, '旧同屏夹具', 9, 100, 100, 0x71), visible)
    refused(lambda: visible_owner.fence_role_binding(legacy.presence, visible))
    assert visible.snapshot(1) == legacy.presence


def metadata_never_authorizes_aoi():
    owner = MapOwner(ADDRESS, CATALOG, capacity=1, transfer_capacity=1, mailbox_capacity=1)
    members = owner.member_projection(role_capacity=1)
    first = Location(1, 1, ADDRESS, 1, 100, 100)
    _, joined = owner.join_with_view(first, None, members)
    fabricated = RoleDelivery(ADDRESS, joined.presence.owner_generation, 1, 1,
        joined.presence.membership_revision, 1, ())
    assert not members.delivery_is_current(fabricated), 'Metadata identity must not authorize AOI delivery'


def transfer_lifecycle():
    owner = MapOwner(ADDRESS, CATALOG, capacity=2, transfer_capacity=2, mailbox_capacity=2)
    members = owner.member_projection(role_capacity=2)
    target_address = MapAddress(8, 81, 0)
    target = MapOwner(target_address, CATALOG, capacity=2, transfer_capacity=2, mailbox_capacity=2)
    target_members = target.member_projection(role_capacity=2)
    first = Location(1, 'lease', ADDRESS, 1, 100, 100)
    _, joined = owner.join_with_view(first, None, members)
    before = owner.role_binding(joined.presence, members, 1)
    fenced = owner.fence_role_binding(joined.presence, members)
    offer = owner.prepare_transfer(first, (8, 50, 50), request_id='cancel', deadline_ms=100, now_ms=1)
    reservation = target.reserve(offer, 2)
    owner.freeze(reservation, 3)
    refused(lambda: owner.role_binding(fenced, members, 1))
    refused(lambda: owner.fence_role_binding(fenced, members))
    cancelled = target.cancel(reservation)
    active, resumed = owner.resume_with_view(cancelled, members)
    assert not resumed.deliveries and resumed.presence.location == active
    assert owner.role_binding(resumed.presence, members, 1) != before
    assert owner.role_binding(resumed.presence, members, 1) == bind_role_view(fenced, 1)
    assert owner.resume_with_view(cancelled, members)[1] == resumed
    refused(lambda: owner.role_binding(joined.presence, members, 1))

    next_fence = owner.fence_role_binding(resumed.presence, members)
    offer = owner.prepare_transfer(active, (8, 50, 50), request_id='commit', deadline_ms=100, now_ms=4)
    reservation = target.reserve(offer, 5)
    receipt = target.activate(owner.freeze(reservation, 6), 7)
    assert target_members.snapshot(1) is None
    refused(lambda: target_members.join(receipt.location, None))
    owner.finalize_with_view(receipt, members)
    assert owner.location(1) is None and members.snapshot(1) is None
    assert not owner.finalize_with_view(receipt, members)[1].deliveries
    ready, target_change = target.ready_with_view(receipt.location, None, target_members)
    assert target_change.presence.location == ready and not target_change.deliveries
    assert target.role_binding(target_change.presence, target_members, 1).address == target_address
    refused(lambda: owner.role_binding(next_fence, members, 1))
    target.leave_with_view(ready, target_members)
    returned = replace(first, version=ready.version+1)
    _, replacement = owner.join_with_view(returned, None, members)
    refused(lambda: owner.finalize_with_view(receipt, members))
    assert owner.role_binding(replacement.presence, members, 1) != before


def strict_identity_and_modes():
    owner = MapOwner(ADDRESS, CATALOG, capacity=2, transfer_capacity=2, mailbox_capacity=2)
    members = owner.member_projection(role_capacity=2)
    first = Location(1, 1, ADDRESS, 1, 100, 100)
    _, joined = owner.join_with_view(first, None, members)
    aliases = [replace(joined.presence, revision=True),
        replace(joined.presence, membership_revision=True),
        replace(joined.presence, location=None)]
    for location in (replace(first, login_epoch=True), replace(first, login_epoch=1.0),
                     replace(first, role_id=True), replace(first, version=True),
                     replace(first, x=100.0), replace(first, address=replace(ADDRESS, partition_id=False))):
        aliases.append(replace(joined.presence, location=location))
    for expected in aliases:
        refused(lambda: owner.role_binding(expected, members, 1))
        refused(lambda: owner.fence_role_binding(expected, members))
        refused(lambda: members.fence_binding(expected))
        assert members.snapshot(1) == joined.presence and owner.location(1) == first
    for generation in (0, -1, True, 1.0):
        refused(lambda: owner.role_binding(joined.presence, members, generation))
    for capacity in (0, -1, True, 1.0):
        refused(lambda: RoleScene.membership_only(ADDRESS, CATALOG, role_capacity=capacity))
    empty = MapOwner(ADDRESS, CATALOG, capacity=1, transfer_capacity=1, mailbox_capacity=1)
    empty_members = empty.member_projection(role_capacity=1)
    refused(lambda: empty.join_with_view(first, RoleBasic(1, '不造外观', 9, 100, 100, 0x71), empty_members))
    assert empty.location(1) is None and empty_members.snapshot(1) is None
    full = RoleScene(ADDRESS, CATALOG, radius=64, role_capacity=1, pair_capacity=0, batch_size=1)
    refused(lambda: empty.join_with_view(first, None, full))
    assert empty.location(1) is None and full.snapshot(1) is None


def hot_path_no_io():
    # External file-system seam only; no internal World Module is mocked.
    with patch('builtins.open', side_effect=AssertionError('Hot path disk access')), \
         patch('io.open', side_effect=AssertionError('Hot path disk access')):
        owner = MapOwner(ADDRESS, CATALOG, capacity=1, transfer_capacity=1, mailbox_capacity=1)
        members = owner.member_projection(role_capacity=1)
        first = Location(1, 'lease', ADDRESS, 1, 100, 100)
        _, joined = owner.join_with_view(first, None, members)
        owner.role_binding(joined.presence, members, 1)
        fenced = owner.fence_role_binding(joined.presence, members)
        stop = b'\0'+struct.pack('>hhQ', 104, 100, 7)
        moved, change = owner.move_with_view(MoveCommand(first, 'step', 100, 0xc0faa, stop), 1, members)
        assert change.presence.membership_revision == fenced.membership_revision
        owner.role_binding(change.presence, members, 1)
        owner.leave_with_view(moved.location, members)


def full_instance_identity():
    identities = (MapAddress(7, 2**62+5, 0), MapAddress(7, 2**62+6, 0), MapAddress(7, 2**62+5, 1))
    records = []
    for address in identities:
        owner = MapOwner(address, CATALOG, capacity=1, transfer_capacity=1, mailbox_capacity=1)
        members = owner.member_projection(role_capacity=1)
        location = Location(1, 'same-lease', address, 1, 100, 100)
        _, change = owner.join_with_view(location, None, members)
        records.append((owner, members, change.presence, owner.role_binding(change.presence, members, 1)))
    assert len({binding for _, _, _, binding in records}) == 3
    for owner, members, expected, _ in records:
        for other_owner, other_members, other_presence, _ in records:
            if other_owner is not owner:
                refused(lambda: owner.role_binding(other_presence, members, 1))
                refused(lambda: owner.fence_role_binding(expected, other_members))
        assert members.snapshot(1) == expected
    original_owner, original_members, expected, binding = records[0]
    rebuilt = MapOwner(identities[0], CATALOG, capacity=1, transfer_capacity=1, mailbox_capacity=1)
    rebuilt_members = rebuilt.member_projection(role_capacity=1)
    _, current = rebuilt.join_with_view(expected.location, None, rebuilt_members)
    refused(lambda: rebuilt.role_binding(expected, rebuilt_members, 1))
    assert rebuilt.role_binding(current.presence, rebuilt_members, 1) != binding
    assert original_members.snapshot(1) == expected and original_owner.location(1) == expected.location


def domain_generation_ownership():
    owner = MapOwner(ADDRESS, CATALOG, capacity=2, transfer_capacity=2, mailbox_capacity=2)
    members = owner.member_projection(role_capacity=2)
    first = Location(1, 'same', ADDRESS, 1, 100, 100)
    _, joined = owner.join_with_view(first, None, members)
    binding = owner.role_binding(joined.presence, members, 1)
    assert binding.owner_generation == owner.inspect_lifecycle(0).owner_generation
    assert owner.member_projection(role_capacity=2) is members
    refused(lambda: owner.member_projection(role_capacity=1))
    refused(lambda: owner.member_projection(role_capacity=True))
    assert members.snapshot(1) == joined.presence

    rebuilt = MapOwner(ADDRESS, CATALOG, capacity=2, transfer_capacity=2, mailbox_capacity=2)
    rebuilt.join(first)
    refused(lambda: rebuilt.role_binding(joined.presence, members, 1))
    refused(lambda: rebuilt.member_projection(role_capacity=2))
    rebuilt.leave(first)
    current_members = rebuilt.member_projection(role_capacity=2)
    _, current = rebuilt.join_with_view(first, None, current_members)
    current_binding = rebuilt.role_binding(current.presence, current_members, 1)
    assert current_binding.owner_generation == rebuilt.inspect_lifecycle(0).owner_generation
    assert current_binding.owner_generation != binding.owner_generation
    refused(lambda: rebuilt.role_binding(joined.presence, members, 1))
    refused(lambda: rebuilt.role_binding(joined.presence, current_members, 1))
    refused(lambda: rebuilt.fence_role_binding(joined.presence, members))
    assert rebuilt.location(1) == first and current_members.snapshot(1) == current.presence

    # Even matching scalar generation cannot attach a second mutable view.
    unregistered = RoleScene.membership_only(ADDRESS, CATALOG, role_capacity=2,
        owner_generation=current_binding.owner_generation)
    duplicate = unregistered.join(first, None).presence
    assert duplicate == current.presence
    refused(lambda: rebuilt.role_binding(duplicate, unregistered, 1))
    refused(lambda: rebuilt.fence_role_binding(duplicate, unregistered))
    refused(lambda: rebuilt.leave(first))
    refused(lambda: rebuilt.join(replace(first, role_id=2)))
    assert rebuilt.location(1) == first and rebuilt.location(2) is None
    assert current_members.snapshot(1) == current.presence


def loading_ready_capacity():
    source = MapOwner(ADDRESS, CATALOG, capacity=1, transfer_capacity=2, mailbox_capacity=1)
    members = source.member_projection(role_capacity=1)
    first = Location(1, 'lease', ADDRESS, 1, 100, 100)
    _, joined = source.join_with_view(first, None, members)
    source.fence_role_binding(joined.presence, members)
    address = MapAddress(8, 81, 0)
    target = MapOwner(address, CATALOG, capacity=2, transfer_capacity=2, mailbox_capacity=1)
    target_members = target.member_projection(role_capacity=1)
    occupant = Location(2, 'other', address, 1, 70, 70)
    target.join_with_view(occupant, None, target_members)
    offer = source.prepare_transfer(first, (8, 50, 50), request_id='capacity', deadline_ms=100, now_ms=1)
    receipt = target.activate(source.freeze(target.reserve(offer, 2), 3), 4)
    refused(lambda: target.ready(receipt.location))
    refused(lambda: target.ready_with_view(receipt.location, None, target_members))
    assert target.location(1) == receipt.location and target.location(1).state == 'loading'
    assert target_members.snapshot(1) is None and target.location(2) == occupant
    target.leave_with_view(occupant, target_members)
    active, change = target.ready_with_view(receipt.location, None, target_members)
    assert active.state == 'active' and target.role_binding(change.presence, target_members, 1)
    source.finalize_with_view(receipt, members)


def retirement_and_rebuild():
    owner = MapOwner(ADDRESS, CATALOG, capacity=1, transfer_capacity=1, mailbox_capacity=1)
    owner.configure_lifecycle(scene_delivery_capacity=1, actor_state='static_original')
    members = owner.member_projection(role_capacity=1)
    first = Location(1, 'lease', ADDRESS, 1, 100, 100)
    _, joined = owner.join_with_view(first, None, members)
    old = owner.role_binding(joined.presence, members, 1)
    owner.leave_with_view(first, members)
    idle = owner.inspect_lifecycle(0)
    owner.retire_idle(idle, 60000, minimum_idle_ms=60000)
    refused(lambda: owner.member_projection(role_capacity=1))
    refused(lambda: owner.join_with_view(first, None, members))
    refused(lambda: owner.role_binding(joined.presence, members, 1))
    rebuilt = MapOwner(ADDRESS, CATALOG, capacity=1, transfer_capacity=1, mailbox_capacity=1)
    new_members = rebuilt.member_projection(role_capacity=1)
    _, new = rebuilt.join_with_view(first, None, new_members)
    assert rebuilt.role_binding(new.presence, new_members, 1) != old
    refused(lambda: rebuilt.role_binding(joined.presence, members, 1))


def paired_dequeue_preserves_admitted():
    owner = MapOwner(ADDRESS, CATALOG, capacity=1, transfer_capacity=1, mailbox_capacity=1)
    members = owner.member_projection(role_capacity=1)
    first = Location(1, 'lease', ADDRESS, 1, 100, 100)
    owner.join_with_view(first, None, members)
    stop = b'\0'+struct.pack('>hhQ', 104, 100, 7)
    command = MoveCommand(first, 'queued', 100, 0xc0faa, stop)
    assert owner.submit(command, 1) == 'accepted'
    assert owner.inspect_lifecycle(1).queued_movements == 1
    refused(lambda: owner.process_one(2))
    assert owner.inspect_lifecycle(2).queued_movements == 1, 'Wrong consumer discarded an accepted command'
    moved, change = owner.process_one_with_view(3, members)
    assert moved.checkpoint and moved.location.position == (7, 104, 100)
    assert owner.location(1) == change.presence.location and not change.deliveries
    assert owner.inspect_lifecycle(3).queued_movements == 0


GROUPS = {'admission': admission, 'movement': movement, 'departure': departure,
          'binding_issuance': binding_issuance, 'fencing': fencing,
          'metadata_never_authorizes_aoi': metadata_never_authorizes_aoi,
          'transfer_lifecycle': transfer_lifecycle, 'strict_identity_and_modes': strict_identity_and_modes,
          'hot_path_no_io': hot_path_no_io, 'full_instance_identity': full_instance_identity,
          'domain_generation_ownership': domain_generation_ownership,
          'loading_ready_capacity': loading_ready_capacity, 'retirement_and_rebuild': retirement_and_rebuild,
          'paired_dequeue_preserves_admitted': paired_dequeue_preserves_admitted}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--group', choices=tuple(GROUPS))
    parser.add_argument('--domain-source', type=Path)
    parser.add_argument('--report', type=Path,
        default=Path(__file__).parent/'evidence/world-member-metadata-verification.json')
    args = parser.parse_args()
    root = Path(__file__).parent
    names = ('world_owner.py', 'world_roles.py', 'world_role_delivery.py', 'world_role_protocol.py',
             'world_movement.py', 'verify_world_member_metadata.py')
    paths = {n: Path(__file__).resolve() if n == Path(__file__).name else
             Path(importlib.import_module(n[:-3]).__file__).resolve() for n in names}
    def sources():
        return {n: hashlib.sha256(path.read_bytes()).hexdigest() for n, path in paths.items()}
    before = sources()
    result = dict(all_passed=False, passed=[], shared_modified=False,
        live_server_changed=False, native_gui_verified=False,
        scope='actual public pure WorldDomain/RoleScene; explicit synthetic catalog and leases only')
    try:
        for name, check in GROUPS.items():
            if args.group is None or args.group == name:
                check()
                result['passed'].append(name)
        result['all_passed'] = True
    except Exception as error:
        result['error'] = repr(error)
        raise
    finally:
        result.update(source_sha256=before, source_paths={n: str(p) for n, p in paths.items()},
            inputs_stable=before == sources())
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf8')
    assert result['inputs_stable']
    print(json.dumps(dict(all_passed=True, groups=result['passed'], inputs_stable=True)))


if __name__ == '__main__':
    main()
