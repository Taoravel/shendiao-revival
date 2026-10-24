"""Frozen NPC v2 predicate -> original-maze birth/approach -> domain visit.

Static path witnesses and explicit Location fixtures, not natural role travel,
runtime lifecycle, OS mouse input, GUI, or production activation.
"""
from dataclasses import asdict, replace
import hashlib
import struct
from unittest.mock import patch

from inspect_client import OUT, write_json
from npc_interaction import load_npc_interaction_rules
from world_catalog import maps, maze_grids, valid_position
from world_collision import maze_clear, maze_segment_clear
from world_newbie import load_newbie_routes, check_birth_site, validate_birth_sites
from world_npcs import load_placements, load_npc_definitions, NpcScene
from world_owner import MapAddress, Location


def verify_goal(route, witness, catalog, grids, placements, definitions, rules):
    assert witness.status == 'reachable' and witness.path[0] == route.cinematic_endpoint[1:]
    grid = grids[route.home_map_id]
    assert all(valid_position((route.home_map_id, *p), catalog) and maze_clear(grid, *p, mask=1)
               for p in witness.path)
    assert all(maze_segment_clear(grid, a, b, mask=1) for a, b in zip(witness.path, witness.path[1:]))
    npc = next(p for p in placements[route.home_map_id] if p.placement_id == witness.placement_id)
    assert npc.npc_id == route.first_npc_id
    current = Location(1, 'offline-policy-witness', MapAddress(route.home_map_id, route.home_map_id, 0),
                       1, *witness.path[-1])
    assert rules.allows(npc, current.position)
    scene = NpcScene(current.address, placements[route.home_map_id], catalog,
                     interaction_radius=None, binding_capacity=1, interaction_rules=rules)
    key = (route.home_map_id << 32) | npc.placement_id
    scene.spawn(((key, npc.placement_id),), definitions, batch_size=1)
    proof = scene.interact(struct.pack('>q', key), current, current,
                           request_id='frozen-policy-goal', deadline_ms=2, now_ms=1)
    assert proof.npc_id == route.first_npc_id and proof.placement_id == witness.placement_id
    return {'character_id': route.character_id, 'school_id': route.school_id,
            'map_id': route.home_map_id, 'npc_id': npc.npc_id, **asdict(witness)}


def main():
    names = ('world_newbie.py', 'npc_interaction.py', 'world_npcs.py',
             'world_catalog.py', 'world_collision.py', 'world_grids.py',
             'design/npc-interaction-v2.json', 'verify_world_newbie_interaction_policy.py')
    before = {name: hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in names}
    catalog, grids = maps(), maze_grids()
    placements, definitions = load_placements(), load_npc_definitions()
    rules = load_npc_interaction_rules(placements, definitions, OUT/'design/npc-interaction-v2.json')
    assert rules.revision == '2026-10-23.npc-interaction.2'
    routes = load_newbie_routes()
    with patch('builtins.open', side_effect=AssertionError('Witness hot policy read')), \
         patch('pathlib.Path.open', side_effect=AssertionError('Witness hot path read')):
        approved = validate_birth_sites(routes, catalog, grids, placements, state_byte=0,
            interaction_radius=None, interaction_allowed=rules.allows, max_visited=100000)
    rows = [verify_goal(route, approved[key], catalog, grids, placements, definitions, rules)
            for key, route in routes.items()]
    assert len(rows) == 43
    bloodmark = replace(routes[(9, 11)], home_map_id=1006, first_npc_id=10498,
                        cinematic_endpoint=(1006, 360, 2264))
    target = tuple(p for p in placements[1006] if p.placement_id == 13)
    legacy = check_birth_site(bloodmark, catalog, grids[1006], target, state_byte=0,
                              interaction_radius=32, max_visited=100000)
    assert legacy.status == 'no_witness' and legacy.visited == 44928
    witness = check_birth_site(bloodmark, catalog, grids[1006], target, state_byte=0,
        interaction_radius=None, interaction_allowed=rules.allows, max_visited=100000)
    bloodmark_result = verify_goal(bloodmark, witness, catalog, grids, placements, definitions, rules)
    after = {name: hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in names}
    assert before == after, 'Source changed during frozen predicate verification'
    result = dict(passed=[
        'all43 original creation routes reach goals admitted by the same frozen NPCv2 predicate',
        'every returned point and edge retains normal mask1/native-proven DDA clearance',
        'each43 goal passes actual NpcScene spawn/interact with original placement identity',
        'legacy bloodmark32 remains no_witness44928; frozen v2 reaches an admitted clear point',
        'preloaded startup goal validation performs no file reads'],
        source_sha256=before, inputs_stable=True, policy_revision=rules.revision,
        routes=rows, bloodmark=bloodmark_result, legacy_bloodmark=asdict(legacy),
        location_fixtures=True, natural_runtime_travel_verified=False,
        shared_modified=False, native_gui_verified=False, live_server_changed=False)
    write_json(OUT/'evidence/world-newbie-interaction-policy-verification.json', result)
    print({'routes': len(rows), 'bloodmark_endpoint': witness.path[-1],
           'legacy_status': legacy.status, 'policy': rules.revision, 'inputs_stable': True})


if __name__ == '__main__':
    main()
