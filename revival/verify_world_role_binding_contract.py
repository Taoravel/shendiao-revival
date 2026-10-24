"""Current public membership contract witnesses for proposed runtime wiring.

Uses real pure map/view Modules with an explicit synthetic two-map catalog.
No proposed interface is implemented or passed off as already available.
"""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import struct

from world_owner import MapOwner, MapAddress, Location, MoveCommand
from world_role_protocol import RoleBasic
from world_roles import RoleScene
from world_role_delivery import bind_role_view


def check():
    catalog = {mid: dict(available=True, width=1024, height=1024, portals={}) for mid in (7, 8)}
    address = MapAddress(7, 71, 0)
    owner = MapOwner(address, catalog, capacity=2, transfer_capacity=2, mailbox_capacity=2)
    view = RoleScene(address, catalog, radius=64, role_capacity=2, pair_capacity=1, batch_size=2)
    first = Location(1, 'same-lease', address, 1, 100, 100)
    appearance = RoleBasic(1, '绑定夹具', 9, 100, 100, 0x71)
    _, joined = owner.join_with_view(first, appearance, view)
    binding = bind_role_view(joined.presence, 1)
    stop = b'\0'+struct.pack('>hhQ', 104, 100, 7)
    moved, changed = owner.move_with_view(MoveCommand(first, 'step', 100, 0xc0faa, stop), 1, view)
    assert moved.checkpoint and moved.location.version == 2
    assert changed.presence.revision > joined.presence.revision
    assert changed.presence.membership_revision == joined.presence.membership_revision
    assert bind_role_view(changed.presence, 1) == binding
    assert bind_role_view(changed.presence, 2) == replace(binding, connection_generation=2)
    observations = dict(position_version_changes_without_binding_change=True,
        projection_revision_is_not_membership_revision=True,
        connection_generation_changes_binding_without_new_membership=True)

    target_address = MapAddress(8, 81, 0)
    target = MapOwner(target_address, catalog, capacity=2, transfer_capacity=2, mailbox_capacity=2)
    target_view = RoleScene(target_address, catalog, radius=64, role_capacity=2, pair_capacity=1, batch_size=2)
    offer = owner.prepare_transfer(moved.location, (8, 50, 50), request_id='trusted-offer', deadline_ms=100, now_ms=1)
    reserved = target.reserve(offer, 2)
    frozen = owner.freeze(reserved, 3)
    assert owner.location(1).state == 'frozen'
    # Existing projection intentionally remains visible until source finalize.
    assert view.snapshot(1) == changed.presence
    assert bind_role_view(view.snapshot(1), 1) == binding
    assert view.snapshot(1).location != owner.location(1)
    observations['freeze_requires_authority_recheck_beyond_standalone_bind'] = True
    receipt = target.activate(frozen, 4)
    assert target_view.snapshot(1) is None
    owner.finalize_with_view(receipt, view)
    assert owner.location(1) is None and view.snapshot(1) is None
    ready, ready_change = target.ready_with_view(receipt.location,
        replace(appearance, x=50, y=50), target_view)
    assert bind_role_view(ready_change.presence, 1).address == target_address
    observations['loading_has_no_presence_and_ready_creates_target_binding'] = True

    # Re-enter same address under SAME epoch; old membership cannot resurrect.
    target.leave_with_view(ready, target_view)
    returned = replace(first, version=ready.version+1)
    _, rejoined = owner.join_with_view(returned, appearance, view)
    assert rejoined.presence.owner_generation == joined.presence.owner_generation
    assert rejoined.presence.membership_revision != joined.presence.membership_revision
    assert bind_role_view(rejoined.presence, 1) != binding
    observations['same_epoch_same_address_rejoin_changes_membership'] = True

    # pair_capacity=0 does not provide metadata-only mode: nearby second role
    # is correctly rejected by the existing AOI contract, without map mutation.
    zero_owner = MapOwner(address, catalog, capacity=2, transfer_capacity=2, mailbox_capacity=2)
    zero_view = RoleScene(address, catalog, radius=64, role_capacity=2, pair_capacity=0, batch_size=2)
    zero_owner.join_with_view(first, appearance, zero_view)
    other = replace(first, role_id=2, login_epoch='other')
    try:
        zero_owner.join_with_view(other, replace(appearance, role_id=2), zero_view)
    except ValueError as error:
        assert str(error) == 'Player visibility pair capacity'
    else:
        raise AssertionError('Existing AOI cannot be silently treated as metadata-only')
    assert zero_owner.location(2) is None and zero_view.snapshot(2) is None
    observations['zero_pair_capacity_is_not_metadata_only'] = True

    # Location equality alone cannot identify a map visit. These public
    # Interfaces allow an exact Location leave/rejoin with a new member token.
    old_presence = zero_view.snapshot(1)
    zero_owner.leave_with_view(first, zero_view)
    same, replacement = zero_owner.join_with_view(first, appearance, zero_view)
    assert same == old_presence.location
    assert replacement.presence.membership_revision != old_presence.membership_revision
    assert bind_role_view(replacement.presence, 1) != bind_role_view(old_presence, 1)
    observations['location_only_expected_aliases_replacement'] = True
    observations['captured_presence_detects_equal_location_rejoin'] = (
        replacement.presence != old_presence and zero_view.snapshot(1) == replacement.presence)
    assert observations['captured_presence_detects_equal_location_rejoin']
    return observations


def main():
    base = Path(__file__).parent
    names = ('verify_world_role_binding_contract.py', 'world_owner.py', 'world_roles.py',
             'world_role_delivery.py', 'world_role_protocol.py', 'world_movement.py')
    def sources():
        return {name: hashlib.sha256((base/name).read_bytes()).hexdigest() for name in names}
    before = sources()
    observations = check()
    assert before == sources()
    result = dict(all_passed=True, observations=observations, source_sha256=before,
        inputs_stable=True, proposed_interface_implemented=False, shared_modified=False,
        native_gui_verified=False, live_server_changed=False,
        scope='public pure domain/view Interfaces; synthetic catalog/appearance; no runtime wiring, queues, storage or GPU')
    (base/'evidence/world-role-binding-contract-verification.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps(dict(all_passed=True, observations=len(observations), inputs_stable=True)))


if __name__ == '__main__':
    main()
