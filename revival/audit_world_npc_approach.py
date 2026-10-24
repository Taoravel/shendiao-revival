"""Read-only exact interaction-disk audit, not a navigation/GUI acceptance test.

An empty disk proves no normal-state integer arrival can satisfy the current
distance rule. A nonempty disk only proves a possible standing point exists;
it does not prove connectivity, automatic travel or quest eligibility.
"""
from collections import Counter, defaultdict
from dataclasses import asdict
import hashlib
import json
import struct

from bxml import decode
from inspect_client import OUT, ROOT, write_json, sha256
from npc_interaction import load_npc_interaction_rules
from pfs import PfsArchive
from world_catalog import maps, maze_grids, valid_position
from world_collision import character_movement_mask, maze_clear
from world_grids import maze_grid
from world_npcs import load_placements, load_npc_definitions, NpcScene
from world_owner import MapAddress, Location


def nearest_clear(grid, row, npc, *, mask, limit):
    """Exact nearest integer point within a bounded disk, via cell rectangles.

    Native clearance is constant within a nonnegative 16x16 maze cell. Clamping
    the NPC point into each clear, map-clipped rectangle gives its exact minimum
    squared distance. Checking all intersecting cells therefore covers every
    possible integer standing point, including partial cells on map edges.
    """
    width, height = min(row['width'], 32768), min(row['height'], 32768)
    checked, best = 0, None
    for cy in range(max(0, (npc.y-limit)//16), min(grid.height-1, (npc.y+limit)//16)+1):
        for cx in range(max(0, (npc.x-limit)//16), min(grid.width-1, (npc.x+limit)//16)+1):
            left, top = cx*16, cy*16
            right, bottom = min(left+15, width-1), min(top+15, height-1)
            if right < left or bottom < top:
                continue
            checked += 1
            if grid.cell(cx, cy) & mask:
                continue
            x, y = min(max(npc.x, left), right), min(max(npc.y, top), bottom)
            distance = (x-npc.x)**2+(y-npc.y)**2
            if distance <= limit**2:
                candidate = (distance, x, y, cx, cy)
                if best is None or candidate < best:
                    best = candidate
    return best, checked


def main():
    names = ('audit_world_npc_approach.py', 'world_npcs.py', 'npc_interaction.py',
             'world_catalog.py', 'world_collision.py', 'world_grids.py',
             'catalogs/world.json', 'catalogs/tasks.json',
             'catalogs/knight.gsp.npc.cnpcconfig.json', 'design/npc-interaction-v1.json',
             'catalogs/scene-content.json', 'evidence/world-recovery.json',
             'pfs.py', 'bxml.py', 'inspect_client.py', '../artres/map.pfs', '../artres/config.pfs')
    before = {name: sha256(OUT/name) if (OUT/name).is_file() else None for name in names}
    catalog, grids = maps(), maze_grids()
    placements, definitions = load_placements(), load_npc_definitions()
    # This audit deliberately preserves the historical v1 circle baseline.
    # Current non-circular v2 goals use the frozen rules.allows witness seam.
    rules = load_npc_interaction_rules(placements, definitions, OUT/'design/npc-interaction-v1.json')
    tasks = defaultdict(list)
    for task in json.loads((OUT/'catalogs/tasks.json').read_text(encoding='utf-8'))['missions']:
        target = task['target']
        tasks[(target['map_id'], target['npc_id'])].append(task['id'])
    archive = PfsArchive(ROOT/'artres/map.pfs')
    paths = {name.casefold(): name for name in archive.entries}
    if len(paths) != len(archive.entries):
        raise ValueError('Ambiguous original resource names')
    config_archive = PfsArchive(ROOT/'artres/config.pfs')
    config_name = 'autoconfig/knight.gsp.npc.cnpcconfig.xml'
    config_payload = config_archive.read(config_name)
    assert {int(p.attrib['id']): dict(p.attrib) for p in decode(config_payload)} == dict(definitions)
    resources = {config_name: {'sha256': hashlib.sha256(config_payload).hexdigest(),
                              'crc32': f'{config_archive.entries[config_name].crc:08x}',
                              'archive': 'config.pfs', 'kind': 'NPC definitions'}}
    results, counts = [], Counter()
    mask = character_movement_mask(0)
    for map_id, originals in placements.items():
        row = catalog[map_id]
        npc_name = paths.get((row['resdir']+'/npc.xml').casefold())
        if npc_name is None:
            assert not originals, (map_id, 'Derived placement without original npc.xml')
        else:
            payload = archive.read(npc_name)
            raw = tuple((i+1, int(p.attrib['id']), int(p.attrib['posx']),
                         int(p.attrib['posy']), int(p.attrib.get('dir', 0)))
                        for i, p in enumerate(decode(payload)))
            assert raw == tuple((p.placement_id, p.npc_id, p.x, p.y, p.direction) for p in originals)
            resources[npc_name] = {'sha256': hashlib.sha256(payload).hexdigest(),
                                   'crc32': f'{archive.entries[npc_name].crc:08x}', 'kind': 'placements'}
        if not originals:
            continue
        grid = grids.get(map_id)
        if grid is not None:
            maze_name = paths[(row['resdir']+'/maze.dat').casefold()]
            payload = archive.read(maze_name)
            assert maze_grid(payload) == grid
            resources[maze_name] = {'sha256': hashlib.sha256(payload).hexdigest(),
                                    'crc32': f'{archive.entries[maze_name].crc:08x}', 'kind': 'maze'}
        address = MapAddress(map_id, map_id, 0)
        scene = NpcScene(address, originals, catalog, interaction_radius=rules.default_radius,
                         binding_capacity=max(1, len(originals)), interaction_rules=rules)
        for npc in originals:
            radius = rules.radius_for(map_id, npc.placement_id, npc.npc_id)
            result = dict(map_name=row['name'], **asdict(npc),
                          npc_name=definitions.get(npc.npc_id, {}).get('name'), radius=radius,
                          npc_type=definitions.get(npc.npc_id, {}).get('npctype'),
                          hidden=definitions.get(npc.npc_id, {}).get('hide'),
                          referenced_task_ids=tasks[(map_id, npc.npc_id)])
            if grid is None or not row['available']:
                result['status'] = 'unavailable_map'
            elif not valid_position((map_id, npc.x, npc.y), catalog):
                result['status'] = 'invalid_placement'
            elif npc.npc_id not in definitions:
                result['status'] = 'missing_definition'
            else:
                nearest, checked = nearest_clear(grid, row, npc, mask=mask, limit=radius)
                result['intersecting_cells_checked'] = checked
                if nearest is None:
                    result['status'] = 'no_legal_integer_point_in_interaction_disk'
                    nearby, _ = nearest_clear(grid, row, npc, mask=mask, limit=128)
                    result['diagnostic_search_radius'] = 128
                    result['nearest_clear_within_diagnostic_disk'] = (None if nearby is None else
                        {'distance_squared': nearby[0], 'point': nearby[1:3], 'cell': nearby[3:]})
                    other_state, _ = nearest_clear(grid, row, npc,
                        mask=character_movement_mask(1), limit=radius)
                    result['diagnostic_mask8_point'] = (None if other_state is None else
                        {'distance_squared': other_state[0], 'point': other_state[1:3],
                         'cell': other_state[3:]})
                else:
                    _, x, y, cx, cy = nearest
                    assert valid_position((map_id, x, y), catalog) and maze_clear(grid, x, y, mask=mask)
                    key = (map_id << 32) | npc.placement_id
                    packets = scene.spawn(((key, npc.placement_id),), definitions, batch_size=1)
                    assert len(packets) == 1
                    location = Location(1, 'offline-disk-audit', address, 1, x, y)
                    proof = scene.interact(struct.pack('>q', key), location, location,
                                           request_id='disk-audit', deadline_ms=2, now_ms=1)
                    assert (proof.npc_id, proof.placement_id) == (npc.npc_id, npc.placement_id)
                    result.update(status='legal_point_and_current_domain_visit', point=(x, y),
                                  cell=(cx, cy), distance_squared=nearest[0])
            counts[result['status']] += 1
            results.append(result)
    after = {name: sha256(OUT/name) if (OUT/name).is_file() else None for name in names}
    assert before == after, 'Audit inputs changed during execution; rerun this same snapshot'
    assert len(results) == sum(map(len, placements.values()))
    bloodmark = next(r for r in results if (r['map_id'], r['placement_id'], r['npc_id']) == (1006, 13, 10498))
    assert bloodmark['status'] == 'legal_point_and_current_domain_visit'
    assert bloodmark['point'] == (1668, 1008) and bloodmark['distance_squared'] == 1444
    report = dict(audit_completed=True, interaction_policy=rules.revision, state_byte=0, movement_mask=mask,
                  total_placements=len(results), maps_with_placements=sum(bool(v) for v in placements.values()),
                  counts=dict(counts), inputs_sha256=before, inputs_stable=True,
                  original_resource_entries=resources, placements=results,
                  scope='Exact integer-disk feasibility and current NpcScene public spawn/interact; isolated location fixtures',
                  navigation_connectivity_verified=False, native_client_automatic_approach_verified=False,
                  native_gui_verified=False, shared_runtime_injection_verified=False,
                  live_server_changed=False, policy_changed=False)
    write_json(OUT/'evidence/world-npc-approach-audit.json', report)
    print({key: report[key] for key in ('audit_completed', 'total_placements', 'maps_with_placements', 'counts', 'inputs_stable')})


if __name__ == '__main__':
    main()
