"""Native movement decoding and confirmed positions, behind one session interface.

Only client-reported check/stop positions are saved. Move targets are intentions,
not arrival. An explicitly supplied maze checks reported nodes with the native
state mask. Native float-to-report quantization can make a legal move fail a
recomputed integer segment; continuous-travel rejection needs reconciliation.
"""
import struct
from dataclasses import dataclass
from wire import NeedMoreData, read_compact
from world_catalog import maps, valid_position
from world_collision import maze_clear, character_movement_mask

ROLE_MOVE, CHECK_MOVE, ROLE_STOP = 0xc0fa1, 0xc0fa3, 0xc0faa
MOVEMENT_TYPES = (ROLE_MOVE, CHECK_MOVE, ROLE_STOP)


def decode_movement(kind, body):
    """Decode report points and the original opaque q64 context.

    Original CRoleMove, timed CCheckMove and natural CRoleStop producers copy
    Scene+30/+34 into that q64; it is not a travel timestamp.
    Routing/epoch/version still come from the trusted server command.
    """
    if kind not in MOVEMENT_TYPES:
        raise ValueError('Unsupported movement type')
    def pos(offset): return struct.unpack_from('>hh', body, offset)
    try:
        if kind == ROLE_MOVE:
            if len(body) != 16: raise ValueError('Invalid movement size')
            points = (pos(0), pos(4))
            return points[0], points, struct.unpack_from('>Q', body, 8)[0]
        offset = 4 if kind == CHECK_MOVE else 0
        count, offset = read_compact(body, offset)
        if count > 4096 or len(body) != offset+count*4+(8 if kind == CHECK_MOVE else 12):
            raise ValueError('Invalid movement path size')
        path = tuple(pos(offset+i*4) for i in range(count))
        current = pos(0) if kind == CHECK_MOVE else pos(offset+count*4)
        return current, (*path, current), struct.unpack_from('>Q', body, len(body)-8)[0]
    except (NeedMoreData, struct.error):
        raise ValueError('Truncated movement') from None


@dataclass(frozen=True)
class MovementPlan:
    source: tuple
    reported: tuple
    position: tuple
    arrival_cell: tuple
    path_points: int
    checkpoint: bool
    transfer_target: tuple | None
    unavailable_portal: bool


def plan_movement(position, arrival_cell, kind, body, catalog, *, maze=None, movement_state=None,
                  collision_points='reported_nodes'):
    """Pure decision for the map owner, with a preloaded read-only catalog.

    A transfer target is a proposal: the runtime must reserve/freeze/handoff
    before making it authoritative. This function performs no storage or send.
    The caller validates role epoch, map ownership and position version first.
    Default collision checks retain the legacy reported-node contract. The
    explicit native_current policy checks only the ordinary, unwrapped current
    getter's cell; rounded history and intention targets are not arrivals.
    It requires a supplied maze and trusted state, and proves no trajectory.
    """
    if collision_points not in ('reported_nodes', 'native_current'):
        raise ValueError('Unknown movement collision point policy')
    if collision_points == 'native_current' and maze is None:
        raise ValueError('Native current policy requires an explicit maze')
    current, points, _native_context = decode_movement(kind, body)
    map_id = position[0]
    if any(not valid_position((map_id, x, y), catalog) for x, y in points):
        raise ValueError('Movement outside map bounds')
    if maze is not None:
        if movement_state is None:
            raise ValueError('Authoritative movement state required for maze query')
        mask = character_movement_mask(movement_state)
        checked = points if collision_points == 'reported_nodes' else (current,)
        if any(not maze_clear(maze, x, y, mask=mask) for x, y in checked):
            raise ValueError('Movement enters blocked maze cell')
    checkpoint = kind != ROLE_MOVE
    target = None
    unavailable = False
    result = position
    next_cell = arrival_cell
    if checkpoint:
        result = (map_id, *current)
        cell = (current[0]//16, current[1]//16)
        candidate = catalog[map_id]['portals'].get(cell)
        if cell != arrival_cell and candidate:
            if valid_position(candidate, catalog):
                target = candidate
                result = target
            else:
                unavailable = True
        next_cell = (result[1]//16, result[2]//16)
    return MovementPlan(position, (map_id, *current), result, next_cell,
                        len(points), checkpoint, target, unavailable)


class WorldMovement:
    """Legacy synchronous Adapter; replace at the map-owner runtime Seam.

    Its direct checkpoint and immediate transfer remain migration work.
    """
    def __init__(self, accounts, account_id, role_id):
        self.accounts, self.account_id, self.role_id = accounts, account_id, role_id
        self.catalog = maps()
        self.position = accounts.position(account_id, role_id)
        if not valid_position(self.position):
            raise ValueError('Stored position outside available world')
        self.arrival_cell = (self.position[1]//16, self.position[2]//16)

    def receive(self, kind, body):
        plan = plan_movement(self.position, self.arrival_cell, kind, body, self.catalog)
        if plan.checkpoint:
            self.accounts.save_position(self.account_id, self.role_id, plan.position)
            self.position, self.arrival_cell = plan.position, plan.arrival_cell
        return {'event': 'world_movement', 'type': kind, 'role_id': self.role_id,
                'map': self.position[0], 'x': self.position[1], 'y': self.position[2],
                'reported_map': plan.reported[0], 'reported_x': plan.reported[1], 'reported_y': plan.reported[2],
                'path_points': plan.path_points, 'persisted': plan.checkpoint,
                'transferred': plan.transfer_target is not None, 'unavailable_portal': plan.unavailable_portal}
