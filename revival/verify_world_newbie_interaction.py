"""Public birth-witness seam with a trusted, non-circular interaction goal."""
from dataclasses import replace
import hashlib
from unittest.mock import patch
from inspect_client import OUT, write_json
from world_grids import SceneGrid
from world_newbie import NewbieRoute, check_birth_site, validate_birth_sites
from world_npcs import NpcPlacement


def refused(action):
    try:
        action()
    except ValueError:
        return
    raise AssertionError('Ambiguous or invalid interaction goal was accepted')


def main():
    route = NewbieRoute(9, 11, 7, 100101, 11001, 100186, 20005, 999, (7, 8, 8))
    catalog = {7: {'available': True, 'width': 64, 'height': 48}}
    maze = SceneGrid(4, 3, bytes(12), 12)
    npc = NpcPlacement(1, 999, 7, 40, 8, 0)
    observed = []

    def allowed(placement, position):
        assert placement is npc and type(position) is tuple and len(position) == 3
        observed.append(position)
        return position == (7, 24, 24)

    result = check_birth_site(route, catalog, maze, (npc,), state_byte=0,
        interaction_radius=None, interaction_allowed=allowed, max_visited=20)
    assert result.status == 'reachable' and result.path[-1] == (24, 24)
    assert observed[0] == (7, 8, 8) and result.placement_id == 1
    approved = validate_birth_sites({(9, 11): route}, catalog, {7: maze}, {7: (npc,)},
        state_byte=0, interaction_radius=None, interaction_allowed=allowed, max_visited=20)
    assert approved[(9, 11)] == result
    legacy = check_birth_site(route, catalog, maze, (npc,), state_byte=0,
        interaction_radius=1, max_visited=20)
    assert legacy.status == 'reachable' and legacy.path[-1] == (40, 8)
    assert legacy != result
    limited = check_birth_site(route, catalog, maze, (npc,), state_byte=0,
        interaction_allowed=allowed, max_visited=1)
    assert limited.status == 'search_budget' and limited.visited == 1
    all_false = check_birth_site(route, catalog, maze, (npc,), state_byte=0,
        interaction_allowed=lambda p, pos: False, max_visited=20)
    assert all_false.status == 'no_witness' and not all_false.path
    blocked = replace(maze, cells=b'\1'+bytes(11))
    assert check_birth_site(route, catalog, blocked, (npc,), state_byte=0,
        interaction_allowed=lambda p, pos: True, max_visited=20).status == 'blocked_start'
    goal_blocked = replace(maze, cells=bytes(5)+b'\1'+bytes(6))
    assert check_birth_site(route, catalog, goal_blocked, (npc,), state_byte=0,
        interaction_allowed=allowed, max_visited=20).status == 'no_witness'
    kwargs = dict(state_byte=0, max_visited=20)
    for bad in ({}, {'interaction_radius': True}, {'interaction_radius': -1},
                {'interaction_allowed': object()},
                {'interaction_allowed': allowed, 'interaction_radius': 1},
                {'interaction_allowed': allowed, 'max_visited': True}):
        refused(lambda bad=bad: check_birth_site(route, catalog, maze, (npc,), **(kwargs | bad)))
    for truthy in (1, 'yes', (), None):
        refused(lambda truthy=truthy: check_birth_site(route, catalog, maze, (npc,),
            **kwargs, interaction_allowed=lambda p, pos: truthy))
    with patch('builtins.open', side_effect=AssertionError('Hot interaction witness file read')), \
         patch('pathlib.Path.open', side_effect=AssertionError('Hot interaction witness path read')):
        assert check_birth_site(route, catalog, maze, (npc,), **kwargs, interaction_allowed=allowed) == result
    report = dict(passed=[
        'non-circular predicate receives the exact placement and full(map_id,x,y) tuple',
        'startup birth validation forwards the same trusted predicate and witness',
        'legacy explicit radius preserves its different original goal',
        'predicate cannot bypass search budget or original blocked-start/goal collision',
        'ambiguous/missing/invalid goals and non-bool predicate results reject',
        'preloaded predicate witness performs no file reads'],
        source_sha256={name: hashlib.sha256((OUT/name).read_bytes()).hexdigest()
                       for name in ('world_newbie.py', 'verify_world_newbie_interaction.py')},
        fixture='controlled clear/blocking maze and non-circular exact-point predicate',
        frozen_npc_v2_verified=False, shared_modified=False, native_gui_verified=False)
    write_json(OUT/'evidence/world-newbie-interaction-verification.json', report)
    print({'passed': report['passed'], 'frozen_npc_v2_verified': False})


if __name__ == '__main__':
    main()
