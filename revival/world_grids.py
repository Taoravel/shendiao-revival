"""Strict readers for shipped scene grids; flag semantics remain uninterpreted.

The legacy format_version field stores the observed first word (12/16).
Native loader research identifies maze's word as its data/header offset.
"""
from dataclasses import dataclass
import struct


@dataclass(frozen=True)
class SceneGrid:
    width: int
    height: int
    cells: bytes
    format_version: int
    present: bytes | None = None

    def cell(self, x, y):
        if not 0 <= x < self.width or not 0 <= y < self.height:
            raise ValueError('Grid coordinate outside bounds')
        index = y*self.width+x
        return self.cells[index] if self.present is None or self.present[index] else None


def maze_grid(data):
    if len(data) < 12:
        raise ValueError('Truncated maze header')
    version, width, height = struct.unpack_from('<III', data)
    if version != 12 or not width or not height or width*height > 16000000:
        raise ValueError('Unsupported maze dimensions/version')
    if len(data) != 12+width*height:
        raise ValueError('Maze size mismatch')
    return SceneGrid(width, height, bytes(data[12:]), version)


@dataclass(frozen=True)
class MonsterRegions:
    width: int
    height: int
    records: tuple
    format_version: int = 16
    present: None = None

    @property
    def cells(self):
        return bytes(value for x, y, value in self.records)


def monster_grid(data):
    if len(data) < 16:
        raise ValueError('Truncated monster grid')
    version, width, height, count = struct.unpack_from('<IIII', data)
    if version != 16 or not width or not height or width*height > 16000000 or count > 16000000:
        raise ValueError('Unsupported monster grid dimensions/version')
    if len(data) != 16+count*5:
        raise ValueError('Monster grid size mismatch')
    records = []
    for record in range(count):
        y, x, value = struct.unpack_from('<HHB', data, 16+record*5)
        # Original editor files contain duplicate cells and stale dimensions.
        # Preserve every record rather than choosing an unverified winner.
        records.append((x, y, value))
    return MonsterRegions(width, height, tuple(records))
