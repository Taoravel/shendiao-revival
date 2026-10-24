"""MapOwner must reject blocked reported points before changing authority."""
from dataclasses import replace
import struct
from unittest.mock import patch
from world_catalog import maps, maze_grids
from world_grids import SceneGrid
from world_owner import Location, MapAddress, MapOwner, MoveCommand


def main():
    address = MapAddress(7, 1, 0)
    catalog = {7: dict(available=True, width=32, height=32, portals={})}
    # Cell (1,0) blocks native state0/mask1, (0,1) blocks nonzero/mask8.
    maze = SceneGrid(2, 2, bytes([0, 1, 8, 0]), 12)
    owner = MapOwner(address, catalog, capacity=2, transfer_capacity=2,
                     mailbox_capacity=2, maze=maze)
    role = owner.join(Location(1, 'collision', address, 1, 0, 0))
    stop = b'\0'+struct.pack('>hhQ', 16, 0, 0)
    command = MoveCommand(role, 'blocked', 100, 0xc0faa, stop, movement_state=0)
    rejected = owner.move(command, now_ms=1)
    assert rejected.rejection == 'Movement enters blocked maze cell'
    assert owner.location(1) == role and rejected.checkpoint is None and rejected.offer is None
    no_state = owner.move(replace(command, request_id='missing', movement_state=None), now_ms=1)
    assert no_state.rejection == 'Authoritative movement state required for maze query'
    allowed = owner.move(replace(command, request_id='allowed', movement_state=1), now_ms=1)
    assert not allowed.rejection and allowed.location.position == (7, 16, 0)
    other = owner.join(Location(2, 'collision-2', address, 1, 0, 0))
    path = b'\1'+struct.pack('>hhhhQ', 16, 0, 16, 16, 0)
    path_result = owner.move(MoveCommand(other, 'path', 100, 0xc0faa, path,
                                         movement_state=0), now_ms=1)
    assert path_result.rejection == 'Movement enters blocked maze cell'
    assert owner.location(2) == other
    catalog, grids = maps(), maze_grids()
    assert len(grids) == 302 and 1302 not in grids and 1307 not in grids
    try: grids[1007] = maze
    except TypeError: pass
    else: raise AssertionError('Mutable collision catalog')
    address = MapAddress(1007, 91, 0)
    real = MapOwner(address, catalog, capacity=2, transfer_capacity=2,
                    mailbox_capacity=2, maze=grids[1007])
    role = real.join(Location(1, 'original-maze', address, 1, 8480, 6976))
    portal_stop = b'\0'+struct.pack('>hhQ', 8592, 7104, 0)
    with patch('builtins.open', side_effect=AssertionError('Hot-path file access')), \
         patch('io.open', side_effect=AssertionError('Hot-path file access')):
        result = real.move(MoveCommand(role, 'portal', 100, 0xc0faa, portal_stop,
                                       movement_state=0), now_ms=1)
    assert result.offer.target_position == (1014, 896, 3776)
    print('PASS native-mask node rejection, explicit mode, 302 grids and no-I/O portal proposal')


if __name__ == '__main__':
    main()
