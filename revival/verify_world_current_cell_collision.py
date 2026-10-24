"""Explicit current-cell collision seam, preserving legacy node policy.

Original quantizers supply a history/current boundary counterexample; this does
not establish a complete mouse/trajectory or assign production movement state.
"""
import hashlib
import struct

from inspect_client import OUT, write_json
from verify_world_movement_quantization_intervals import QuantizationProbe, current_x_interval
from world_grids import SceneGrid
from world_movement import ROLE_MOVE, CHECK_MOVE, ROLE_STOP, plan_movement
from world_owner import MapOwner, MapAddress, Location, MoveCommand


def main():
    catalog = {1: dict(available=True, width=48, height=48, portals={})}
    grid = SceneGrid(3, 3, b'\0\0\0\0\1\0\0\0\0', 12)
    original = QuantizationProbe()
    history = original.reached(15.75, 20.)
    current = original.current_quantized(23.625, 20.)
    assert history == (16, 20) and current == (15, 20)
    body = b'\1'+struct.pack('>hhhhQ', *history, *current, 1)
    try:
        plan_movement((1, 8, 20), (0, 1), ROLE_STOP, body, catalog,
            maze=grid, movement_state=0)
    except ValueError as error:
        assert str(error) == 'Movement enters blocked maze cell'
    else:
        raise AssertionError('Legacy reported-node policy changed without opt-in')
    plan = plan_movement((1, 8, 20), (0, 1), ROLE_STOP, body, catalog,
        maze=grid, movement_state=0, collision_points='native_current')
    assert plan.position == (1, 15, 20) and plan.checkpoint
    rows = ['original history/current boundary; legacy unchanged; explicit current policy accepts clear cell']

    owner = MapOwner(MapAddress(1, 1, 0), catalog, maze=grid,
                     capacity=1, transfer_capacity=1, mailbox_capacity=2)
    location = owner.join(Location(1, 'current-cell', owner.address, 1, 8, 20))
    result = owner.move(MoveCommand(location, 'native-history', 1000, ROLE_STOP, body,
        movement_state=0, collision_points='native_current'), 1)
    assert not result.rejection and result.location.position == plan.position
    blocked = owner.move(MoveCommand(result.location, 'blocked-current', 1000, ROLE_STOP,
        b'\0'+struct.pack('>hhQ', 16, 20, 1), movement_state=0,
        collision_points='native_current'), 2)
    assert blocked.rejection == 'Movement enters blocked maze cell'
    assert owner.location(1) == result.location
    rows.append('public MapOwner rejects blocked current without version/checkpoint mutation')

    intent = plan_movement((1, 15, 20), (0, 1), ROLE_MOVE,
        struct.pack('>hhhhQ', 15, 20, 16, 20, 1), catalog,
        maze=grid, movement_state=0, collision_points='native_current')
    assert not intent.checkpoint and intent.position == (1, 15, 20)
    rows.append('blocked intention is not authoritative arrival; subsequent blocked STOP was refused')
    check_body = struct.pack('>hh', *current)+b'\1'+struct.pack('>hhQ', *history, 1)
    checked = plan_movement((1, 8, 20), (0, 1), CHECK_MOVE, check_body, catalog,
        maze=grid, movement_state=0, collision_points='native_current')
    assert checked.position == (1, *current) and checked.checkpoint
    rows.append('CHECK uses its current prefix rather than a rounded history node')

    for kwargs, expected in ((dict(collision_points='unknown'), 'Unknown movement collision point policy'),
        (dict(collision_points='native_current'), 'Native current policy requires an explicit maze'),
        (dict(maze=grid, collision_points='native_current'), 'Authoritative movement state required for maze query')):
        try:
            plan_movement((1, 8, 20), (0, 1), ROLE_STOP, body, catalog, **kwargs)
        except ValueError as error:
            assert str(error) == expected
        else:
            raise AssertionError(('Invalid authority accepted', kwargs))
    rows.append('unknown policy, absent maze and absent trusted state refuse explicit current validation')
    bad_history = b'\1'+struct.pack('>hhhhQ', -1, 20, 15, 20, 1)
    try:
        plan_movement((1, 8, 20), (0, 1), ROLE_STOP, bad_history, catalog,
            maze=grid, movement_state=0, collision_points='native_current')
    except ValueError as error:
        assert str(error) == 'Movement outside map bounds'
    else:
        raise AssertionError('Current-only collision bypassed path bounds')
    rows.append('all reported coordinates retain exact bounds validation')

    # Exhaust the positive unwrapped wire range using the independently
    # native-validated projected preimages, with open upper endpoints.
    for wire_x in range(1, 32768):
        low, _, high, _ = current_x_interval(wire_x)
        assert low//24 == wire_x//16
        assert (high.numerator-1)//(24*high.denominator) == wire_x//16
    rows.append('all positive ordinary X preimages occupy the same native cell as the reported current')
    names = ('world_movement.py', 'world_owner.py', 'verify_world_current_cell_collision.py',
             'verify_world_movement_quantization_intervals.py')
    write_json(OUT/'evidence/world-current-cell-collision-verification.json',
        dict(all_passed=True, passed=rows, original_history=history, original_current=current,
            source_sha256={name: hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in names},
            source_scope='explicit pure planner/MapOwner seam; no runtime state assignment',
            native_gui_verified=False, live_server_changed=False))
    print(dict(all_passed=True, groups=len(rows)))


if __name__ == '__main__':
    main()
