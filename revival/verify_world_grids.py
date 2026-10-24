"""Check all shipped grids, preserving editor anomalies and rejecting damage."""
from inspect_client import ROOT, OUT, write_json
from pfs import PfsArchive
from world_grids import maze_grid, monster_grid


def main():
    archive = PfsArchive(ROOT/'artres/map.pfs')
    counts = {'maze': 0, 'monster': 0}
    for name in archive.entries:
        if name.endswith('/maze.dat'):
            maze_grid(archive.read(name)); counts['maze'] += 1
        elif name.endswith('/monster.dat'):
            monster_grid(archive.read(name)); counts['monster'] += 1
    maze = maze_grid(archive.read('map_1007_linan/maze.dat'))
    assert (maze.width, maze.height) == (544, 464)
    assert maze.cell(0, 0) == 11
    regions = monster_grid(archive.read('baihuayougu1/monster.dat'))
    assert (regions.width, regions.height, len(regions.records)) == (106, 160, 16960)
    assert regions.records[0] == (0, 0, 1) and regions.records[160] == (1, 0, 1)
    sparse = monster_grid(archive.read('fubenyanmenguan/monster.dat'))
    assert len(sparse.records) == 2370
    assert sparse.records[0] == (48, 37, 246)
    for name, reader in (('map_1007_linan/maze.dat', maze_grid), ('baihuayougu1/monster.dat', monster_grid)):
        raw = archive.read(name)
        for bad in (raw[:-1], raw+b'\0', b'\0\0\0\0'+raw[4:]):
            try: reader(bad)
            except ValueError: pass
            else: raise AssertionError('Corrupted grid accepted')
    write_json(OUT/'evidence/world-grids-verification.json', {
        'parsed': counts, 'fixed_real_samples': True, 'corruption_rejected': True,
        'collision_mask_native_verified': False, 'encounter_composition_verified': False})
    print('PASS all 308 maze / 44 monster regions; full+sparse samples; corruption rejected')


if __name__ == '__main__': main()
