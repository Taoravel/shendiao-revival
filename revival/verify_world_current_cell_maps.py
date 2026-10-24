"""Current-cell admission on every original resource map, with native oracle.

States are explicit offline fixtures, not inferred production authority. This
does not test continuous paths, natural access, scene readiness or the GUI.
"""
import argparse
from dataclasses import replace
import hashlib
import importlib
from pathlib import Path
import struct

from inspect_client import OUT, ROOT, write_json
from native_inspect import BASE, DATA
from pfs import PfsArchive
from world_catalog import maps, maze_grids, valid_position
from world_grids import maze_grid
from world_movement import ROLE_MOVE, CHECK_MOVE, ROLE_STOP
from world_owner import Location, MapAddress, MapOwner, MoveCommand
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ESP, UC_X86_REG_EIP


class NativePoint:
    """Original 6284f0 predicate; no host replacement for its instructions."""
    stack, stop, wrapper, layout, cells = 0x5001000, 0x500f000, 0x5002000, 0x5002100, 0x6000000

    def __init__(self):
        self.machine = Uc(UC_ARCH_X86, UC_MODE_32)
        self.machine.mem_map(BASE, (len(DATA)+4095)&~4095)
        self.machine.mem_write(BASE, DATA)
        self.machine.mem_map(0x5000000, 0x10000)
        self.machine.mem_map(self.cells, 0x1000000)
        self.put(self.wrapper, 0, self.layout)

    def put(self, address, *values):
        self.machine.mem_write(address, struct.pack('<'+'I'*len(values), *values))

    def install(self, grid, mask):
        self.machine.mem_write(self.cells, grid.cells)
        self.put(self.layout, grid.width, grid.height, self.cells, mask,
                 0, 0, grid.width, grid.height)

    def clear(self, x, y):
        self.put(self.stack, self.stop, self.wrapper, y)
        self.machine.reg_write(UC_X86_REG_ESP, self.stack)
        self.machine.reg_write(UC_X86_REG_EAX, x)
        self.machine.emu_start(0x6284f0, self.stop, count=1000)
        assert self.machine.reg_read(UC_X86_REG_EIP) == self.stop
        return bool(self.machine.reg_read(UC_X86_REG_EAX)&255)


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def sources():
    names = ('world_owner', 'world_movement', 'world_catalog', 'world_grids',
             'world_collision', 'pfs', 'native_inspect', 'verify_world_current_cell_maps')
    paths = {name: Path(importlib.import_module(name).__file__).resolve() for name in names}
    paths.update({name: OUT/name for name in ('catalogs/world.json',
        'catalogs/scene-content.json', 'evidence/world-recovery.json', 'evidence/native-image.bin')})
    return {name: dict(path=str(path), sha256=digest(path)) for name, path in paths.items()}


def sample_cells(grid, row):
    """One usable nonportal cell for each original flag byte, without rewriting it."""
    samples = []
    absent = []
    for flag in sorted(set(grid.cells)):
        index = grid.cells.find(bytes([flag]))
        while index >= 0:
            gx, gy = index % grid.width, index // grid.width
            x, y = gx*16, gy*16
            if x < min(row['width'], 32768) and y < min(row['height'], 32768) and (gx, gy) not in row['portals']:
                samples.append(dict(flag=flag, point=(min(x+8, row['width']-1, 32767),
                                                      min(y+8, row['height']-1, 32767))))
                break
            index = grid.cells.find(bytes([flag]), index+1)
        else:
            absent.append(flag)
    return samples, absent


def check_state(map_id, row, grid, samples, native, state, fault):
    # Explicit fixture mapping already proved by the original selector; it is
    # deliberately independent of world_collision.character_movement_mask.
    mask = 1 if state == 0 else 8
    native.install(grid, mask)
    observed = [dict(sample, native_clear=native.clear(*sample['point'])) for sample in samples]
    clear = next((sample for sample in observed if sample['native_clear']), None)
    blocked = next((sample for sample in observed if not sample['native_clear']), None)
    address = MapAddress(map_id, map_id+100000, 0)
    injected = replace(grid, cells=bytes(value & ~mask for value in grid.cells)) if fault else grid
    owner = MapOwner(address, {map_id: row}, maze=injected,
                     capacity=1, transfer_capacity=1, mailbox_capacity=2)
    # Some original maps block every nonportal cell for mask8. Keep that
    # observation rather than manufacturing a legal source for this state.
    source = clear or blocked
    location = owner.join(Location(1, 'fixture-state-'+str(state), address, 1, *source['point']))
    operations = 0

    def apply(kind, body):
        nonlocal location, operations
        result = owner.move(MoveCommand(location, 'map-audit-'+str(operations), 10000,
            kind, body, movement_state=state, collision_points='native_current'), 1)
        operations += 1
        if not result.rejection:
            location = result.location
        return result

    if clear:
        accepted = apply(ROLE_STOP, b'\0'+struct.pack('>hhQ', *clear['point'], map_id))
        assert not accepted.rejection and accepted.checkpoint == location and location.version == 2
        assert accepted.offer is None and location.position == (map_id, *clear['point'])
    if blocked:
        before = location
        for kind, body in (
            (ROLE_STOP, b'\0'+struct.pack('>hhQ', *blocked['point'], map_id)),
            (CHECK_MOVE, struct.pack('>hh', *blocked['point'])+b'\0'+struct.pack('>Q', map_id))):
            refused = apply(kind, body)
            assert refused.rejection == 'Movement enters blocked maze cell', (map_id, state, kind, refused)
            assert refused.checkpoint is None and refused.offer is None and owner.location(1) == before
        if clear:
            # A wall target is only an intention; it must not alter authority.
            intended = apply(ROLE_MOVE, struct.pack('>hhhhQ', *clear['point'], *blocked['point'], map_id))
            assert not intended.rejection and intended.checkpoint is None and location == before
            assert owner.location(1) == before
            # A rounded history is not a current position. This artificial body
            # checks producer selection, not feasibility of a native trajectory.
            history = apply(ROLE_STOP, b'\1'+struct.pack('>hhhhQ', *blocked['point'], *clear['point'], map_id))
            assert not history.rejection and history.checkpoint == location and location.version == before.version+1
    before = location
    outside = apply(ROLE_STOP, b'\0'+struct.pack('>hhQ', -1, source['point'][1], map_id))
    assert outside.rejection == 'Movement outside map bounds' and owner.location(1) == before
    assert outside.checkpoint is None and outside.offer is None
    return dict(state_fixture=state, mask=mask, native_samples=observed,
        source=source['point'], clear_control_available=clear is not None,
        blocked_target=blocked['point'] if blocked else None,
        operations=operations, blocked_current_checked=blocked is not None,
        no_blocked_sample_reason=None if blocked else 'No blocked nonportal in-bounds original flag cell',
        production_state_authority_established=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--maps', help='Optional diagnostic subset')
    parser.add_argument('--fault-clear-walls', action='store_true')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    report_path = args.report or OUT/('evidence/world-current-cell-maps-fault.json'
        if args.fault_clear_walls else 'evidence/world-current-cell-maps-verification.json')
    before = sources()
    archive_path = ROOT/'artres/map.pfs'
    asset_before = digest(archive_path)
    assert before['evidence/native-image.bin']['sha256'] == hashlib.sha256(DATA).hexdigest() == '2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791'
    catalog, grids = maps(), maze_grids()
    available = sorted(mid for mid, row in catalog.items() if row['available'])
    selected = sorted(set(map(int, args.maps.split(',')))) if args.maps else available
    assert selected and set(selected) <= set(available)
    archive = PfsArchive(archive_path)
    names = {name.casefold(): name for name in archive.entries}
    native = NativePoint()
    result = dict(all_passed=False, maps=[], source=before, asset_sha256=asset_before,
        selected_maps=selected, complete_available_map_scope=selected == available,
        unavailable_maps=sorted(set(catalog)-set(available)), fault_clear_walls=args.fault_clear_walls,
        state_source='Explicit 0/1/2/255 fixtures, original selector mapping; not runtime lifecycle authority',
        scope='public MapOwner native_current admission, original 6284f0 point oracle on fresh full original grids',
        runtime_wiring_verified=False, trajectory_verified=False, native_gui_verified=False,
        live_server_changed=False)
    try:
        for map_id in selected:
            row = catalog[map_id]
            entry = names[(row['resdir']+'/maze.dat').casefold()]
            raw = archive.read(entry)
            grid = maze_grid(raw)
            assert grid == grids[map_id], ('Startup grid differs from fresh original', map_id)
            samples, absent = sample_cells(grid, row)
            assert samples and all(valid_position((map_id, *sample['point']), catalog) for sample in samples)
            record = dict(map_id=map_id, entry=entry, entry_sha256=hashlib.sha256(raw).hexdigest(),
                crc_checked=True, raw_flags_without_nonportal_inbounds_sample=absent, states=[])
            result['maps'].append(record)
            for state in (0, 1, 2, 255):
                record['states'].append(check_state(map_id, row, grid, samples, native, state,
                                                   args.fault_clear_walls))
        result['inputs_stable'] = before == sources() and asset_before == digest(archive_path)
        assert result['inputs_stable'], 'Source or original archive changed during verification'
        result['all_passed'] = True
    except Exception as error:
        result['error'] = repr(error)
        raise
    finally:
        write_json(report_path, result)
    print(dict(all_passed=True, maps=len(result['maps']), states=sum(len(row['states']) for row in result['maps']),
               operations=sum(state['operations'] for row in result['maps'] for state in row['states'])))


if __name__ == '__main__':
    main()
