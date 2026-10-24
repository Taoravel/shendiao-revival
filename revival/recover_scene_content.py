"""Recover all scene resources and entities without inventing spawn tables."""
from collections import Counter
import hashlib
import json
import struct
from inspect_client import ROOT, OUT, write_json
from pfs import PfsArchive
from world_grids import maze_grid, monster_grid


def rows(name):
    return json.loads((OUT/'catalogs'/('knight.gsp.'+name+'.json')).read_text(encoding='utf-8'))


def main():
    archive = PfsArchive(ROOT/'artres/map.pfs')
    lookup = {name.casefold(): name for name in archive.entries}
    if len(lookup) != len(archive.entries):
        raise ValueError('Case-insensitive archive path collision')
    map_rows = rows('map.cmapconfig')
    npc_defs = {int(r['attributes']['id']): r for r in rows('npc.cnpcconfig')}
    shapes = {int(r['attributes']['id']) for r in rows('npc.cnpcshape')}
    bases = {int(r['attributes']['id']): r for r in rows('npc.cscenenpcbase')}
    placements = rows('npc.cscenenpcconfig')
    monsters = rows('npc.cmonsterconfig')
    issues, resources = [], []
    configured_dirs = {r['attributes']['resdir'].casefold() for r in map_rows}
    for name in sorted(n for n in archive.entries if n.endswith('/map.rmp')):
        directory = name.rsplit('/', 1)[0]
        rmp = archive.read(name)
        if rmp[:4] != b'RMAP' or len(rmp) < 16:
            raise ValueError('Invalid RMP header: '+name)
        version, width, height = struct.unpack_from('<III', rmp, 4)
        item = dict(resdir=directory, configured=directory.casefold() in configured_dirs,
                    rmp_version=version, width=width, height=height,
                    rmp_sha256=hashlib.sha256(rmp).hexdigest(), grids={})
        for suffix, parser in (('maze.dat', maze_grid), ('monster.dat', monster_grid)):
            path = lookup.get((directory+'/'+suffix).casefold())
            if path is None:
                continue
            raw = archive.read(path)
            try:
                grid = parser(raw)
            except ValueError as error:
                issues.append(dict(resource=path, issue=str(error)))
                continue
            values = grid.cells if grid.present is None else [v for v, present in zip(grid.cells, grid.present) if present]
            item['grids'][suffix] = dict(width=grid.width, height=grid.height,
                version=grid.format_version, populated_cells=len(values), values=dict(Counter(values)), sha256=hashlib.sha256(raw).hexdigest())
            if suffix == 'monster.dat':
                duplicates = len(grid.records)-len({(x, y) for x, y, value in grid.records})
                outside = sum(x >= grid.width or y >= grid.height for x, y, value in grid.records)
                item['grids'][suffix].update(duplicate_records=duplicates, outside_declared_dimensions=outside)
                target = OUT/'extracted/maps'/path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
                if duplicates or outside:
                    issues.append(dict(resource=path, issue='monster region editor anomalies preserved', duplicates=duplicates, outside=outside))
        resources.append(item)
    available = {r['resdir'].casefold() for r in resources}
    for row in map_rows:
        attrs = row['attributes']
        path = attrs['resdir']+'/map.rmp'
        if attrs['resdir'].casefold() not in available:
            issues.append(dict(map=attrs['id'], resdir=attrs['resdir'], issue='missing configured RMP'))
        elif path not in archive.entries:
            issues.append(dict(map=attrs['id'], requested=path, resolved=lookup[path.casefold()], issue='path case mismatch'))
    entities = []
    known_maps = {int(r['attributes']['id']) for r in map_rows}
    for row in placements:
        attrs = row['attributes']; base = bases.get(int(attrs['baseid']))
        if base is None:
            issues.append(dict(scene_npc=attrs['id'], issue='scene base missing'))
        elif int(base['attributes']['shapeid']) not in shapes:
            issues.append(dict(scene_npc=attrs['id'], issue='scene shape missing', shape=base['attributes']['shapeid']))
        if int(attrs['mapid']) not in known_maps:
            issues.append(dict(scene_npc=attrs['id'], map=attrs['mapid'], issue='unconfigured scene map'))
        entities.append(dict(placement=attrs, base=base, source='npc.cscenenpcconfig/cscenenpcbase'))
    for row in monsters:
        attrs = row['attributes']
        if int(attrs['modelID']) not in shapes:
            issues.append(dict(monster=attrs['id'], shape=attrs['modelID'], issue='monster shape missing'))
    world = json.loads((OUT/'catalogs/world.json').read_text(encoding='utf-8'))
    result = dict(resources=resources, scene_entities=entities, monster_templates=monsters,
                  scene_bases=list(bases.values()), npc_templates=list(npc_defs.values()),
                  walking_schedules=rows('npc.cnpcwalk'),
                  encounter_area_labels=rows('map.cmineareainfo'))
    write_json(OUT/'catalogs/scene-content.json', result)
    summary = dict(configured_maps=len(map_rows), resource_directories=len(resources),
        maps_with_case_resolved_resources=sum(r['attributes']['resdir'].casefold() in available for r in map_rows),
        unconfigured_resource_directories=sum(not r['configured'] for r in resources),
        maze_grids=sum('maze.dat' in r['grids'] for r in resources),
        monster_region_grids=sum('monster.dat' in r['grids'] for r in resources),
        static_npc_placements=sum(len(r['npc_placements']) for r in world),
        scene_entity_placements=len(entities), scene_bases=len(bases),
        monster_templates=len(monsters), npc_templates=len(npc_defs),
        walking_schedules=len(result['walking_schedules']))
    write_json(OUT/'evidence/scene-content-recovery.json', dict(summary=summary, issues=issues,
        limits=['Grid byte semantics/monster encounter composition not yet native-verified',
                'Scene entities may be scenery, timed or transparent; not all are monsters',
                'Monster templates do not contain server spawn/HP/attack/drop tables'],
        runtime_verified=False))
    print(json.dumps(dict(summary=summary, issues_by_type=dict(Counter(i['issue'] for i in issues)))))


if __name__ == '__main__': main()
