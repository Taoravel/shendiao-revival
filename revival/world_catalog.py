"""Shipped map bounds and exact portal cells, shared by travel and scene encoding."""
from functools import lru_cache
import json
from types import MappingProxyType
from inspect_client import OUT, ROOT
from pfs import PfsArchive
from world_grids import maze_grid


@lru_cache(maxsize=1)
def maps():
    rows = json.loads((OUT/'catalogs/world.json').read_text(encoding='utf-8'))
    scene_path = OUT/'catalogs/scene-content.json'
    resources = ({row['resdir'].casefold(): row for row in json.loads(
        scene_path.read_text(encoding='utf-8'))['resources']} if scene_path.exists() else {})
    missing = {int(row['map']) for row in json.loads(
        (OUT/'evidence/world-recovery.json').read_text(encoding='utf-8'))['issues']
        if row['issue'] == 'missing map.rmp'}
    return MappingProxyType({int(row['attributes']['id']): MappingProxyType({
        'name': row['attributes']['mapName'],
        'resdir': row['attributes']['resdir'],
        # Native scene loader projects logical X by 1.5; Y is unchanged.
        'width': (int(resources.get(row['attributes']['resdir'].casefold(), {}).get(
            'width', row['attributes']['width']))*2+2)//3,
        'height': int(resources.get(row['attributes']['resdir'].casefold(), {}).get(
            'height', row['attributes']['height'])),
        'bounds_source': 'RMP' if row['attributes']['resdir'].casefold() in resources else 'config',
        'available': int(row['attributes']['id']) not in missing,
        'portals': MappingProxyType({(int(p['posx']), int(p['posy'])):
                    (int(p['destmap']), int(p['destx'])*16, int(p['desty'])*16)
                    for p in row['portal_cells']})})
        for row in rows})


@lru_cache(maxsize=1)
def maze_grids():
    """Startup-only immutable collision grids for resource-backed map IDs.

    Load this beside maps() before accepting commands. Missing configured maps
    remain unavailable; a present map with a missing maze is a startup error.
    PFS length/CRC validation remains in the archive Adapter.
    """
    archive = PfsArchive(ROOT/'artres/map.pfs')
    paths = {p.casefold(): p for p in archive.entries}
    if len(paths) != len(archive.entries):
        raise ValueError('Case-insensitive collision resource ambiguity')
    loaded, result = {}, {}
    for map_id, row in maps().items():
        if not row['available']:
            continue
        name = paths.get((row['resdir']+'/maze.dat').casefold())
        if name is None:
            raise ValueError(f'Available map {map_id} has no collision grid')
        if name not in loaded:
            loaded[name] = maze_grid(archive.read(name))
        result[map_id] = loaded[name]
    return MappingProxyType(result)


def valid_position(position, catalog=None):
    map_id, x, y = position
    row = (maps() if catalog is None else catalog).get(map_id)
    return bool(row and row['available'] and 0 <= x < min(row['width'], 32768)
                and 0 <= y < min(row['height'], 32768))
