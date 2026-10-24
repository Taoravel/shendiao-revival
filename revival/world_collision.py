"""Pure native-proven maze queries. The caller must supply its movement mask.

No persistence, owner state or guessed mask selection lives here. Coordinates
are native logical pixels (16 per cell), before the 1.5 horizontal rendering
projection. Native signed division truncates toward zero, including negatives.
"""
from world_grids import SceneGrid


def _trunc16(value: int) -> int:
    return value // 16 if value >= 0 else -((-value) // 16)


def maze_clear(grid: SceneGrid, x: int, y: int, *, mask: int) -> bool:
    """Mirror 0x6284f0 full-grid predicate, requiring an explicit byte mask.

    This answers whether the selected bits are clear, not which character
    movement mode uses which mask. SceneGrid must contain the full dense maze.
    """
    if not all(type(v) is int for v in (x, y, mask)):
        raise TypeError('Coordinates and mask must be integers')
    if not -(1 << 31) <= x < (1 << 31) or not -(1 << 31) <= y < (1 << 31):
        raise ValueError('Native coordinates must fit int32')
    if not 0 <= mask <= 255:
        raise ValueError('Collision mask must fit one byte')
    gx, gy = _trunc16(x), _trunc16(y)
    if not 0 <= gx < grid.width or not 0 <= gy < grid.height:
        return False
    value = grid.cell(gx, gy)
    if value is None:
        raise ValueError('Sparse grids cannot establish native maze clearance')
    return (value & mask) == 0


def character_movement_mask(state_byte: int) -> int:
    """Native CCharacter +0x218 selector: zero -> 1; nonzero -> 8.

    State's gameplay name (e.g. flying) is deliberately not guessed. Callers
    must establish that they have the matching native character state.
    """
    if type(state_byte) is not int or not 0 <= state_byte <= 255:
        raise ValueError('Native character movement state must fit a byte')
    return 8 if state_byte else 1


def _i32(value: int) -> int:
    value &= 0xffffffff
    return value if value < 0x80000000 else value-0x100000000


def _segment_samples(start, end):
    """Exact 0x626b40 16.16 DDA samples, excluding start, including end."""
    x0, y0 = start
    x1, y1 = end
    dx, dy = _i32(x1-x0), _i32(y1-y0)
    y_major = abs(dy) > abs(dx)
    major, minor = (dy, dx) if y_major else (dx, dy)
    origin_major, origin_minor = (y0, x0) if y_major else (x0, y0)
    if major == 0:
        return
    numerator = _i32(minor << 16)
    slope = (abs(numerator)//abs(major)) * (-1 if (numerator<0) != (major<0) else 1)
    slope = _i32(slope + int(slope < 0))
    accumulator = _i32(origin_minor << 16)
    direction = 1 if major > 0 else -1
    accumulator = _i32(accumulator + slope + 0x7fff) if direction > 0 else _i32(accumulator-slope+0x8000)
    for index in range(1, abs(major)+1):
        coordinate = _i32(origin_major+direction*index)
        secondary = accumulator >> 16
        yield (secondary, coordinate) if y_major else (coordinate, secondary)
        accumulator = _i32(accumulator+direction*slope)


def maze_segment_result(grid: SceneGrid, start: tuple[int, int], end: tuple[int, int], *, mask: int) -> int:
    """Mirror native 0x626b40: 0 clear, 1 blocked, 3 same point.

    Coordinates are logical native pixels before horizontal rendering projection.
    The start is NOT sampled; identical points return 3 without a point query.
    Callers must first check their authoritative start and every reported node.
    Pixel coordinates must fit the original signed short position range, bounding
    each call to 65,535 samples. This is line validation, not A* path finding.
    """
    if len(start) != 2 or len(end) != 2:
        raise ValueError('Each position must contain two native coordinates')
    if any(type(v) is not int or not -32768 <= v <= 32767 for v in (*start, *end)):
        raise ValueError('Segment coordinates must fit original signed short position')
    if type(mask) is not int or not 0 <= mask <= 255:
        raise ValueError('Collision mask must fit one byte')
    start, end = tuple(start), tuple(end)
    if start == end:
        return 3
    for x, y in _segment_samples(start, end):
        if not maze_clear(grid, x, y, mask=mask):
            return 1
    return 0


def maze_segment_clear(grid: SceneGrid, start: tuple[int, int], end: tuple[int, int], *, mask: int) -> bool:
    """Convenience predicate; same-point native result 3 counts as clear.

    See maze_segment_result for the required separate start/node point check.
    """
    return maze_segment_result(grid, start, end, mask=mask) != 1
