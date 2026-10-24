"""Offline checks of designed birth candidates against original map resources."""
from collections import Counter
from dataclasses import asdict
from inspect_client import OUT, write_json
from world_newbie import load_newbie_routes, validate_birth_sites
from world_catalog import maps, maze_grids, valid_position
from world_npcs import load_placements
from world_collision import maze_clear, maze_segment_clear


def main():
    routes, catalog, grids, placements = load_newbie_routes(), maps(), maze_grids(), load_placements()
    approved = validate_birth_sites(routes,catalog,grids,placements,state_byte=0,
                                    interaction_radius=32,max_visited=100000)
    cache, rows = {}, []
    for route in routes.values():
        key = (route.home_map_id,route.cinematic_endpoint,route.first_npc_id)
        if key not in cache:
            check = approved[(route.character_id,route.school_id)]
            # Independently recheck every witness using the original predicates.
            if check.status == 'reachable':
                assert check.path[0] == route.cinematic_endpoint[1:]
                assert all(valid_position((route.home_map_id,*p),catalog)
                           and maze_clear(grids[route.home_map_id],*p,mask=1) for p in check.path)
                assert all(maze_segment_clear(grids[route.home_map_id],a,b,mask=1)
                           for a,b in zip(check.path,check.path[1:]))
                target = next(p for p in placements[route.home_map_id]
                              if p.placement_id == check.placement_id)
                assert target.npc_id == route.first_npc_id
                assert sum((a-b)**2 for a,b in zip(check.path[-1],(target.x,target.y))) <= 32**2
            cache[key] = check
        check = cache[key]
        rows.append(dict(character_id=route.character_id,school_id=route.school_id,
            home_map_id=route.home_map_id,intro_task_id=route.intro_task_id,
            first_npc_id=route.first_npc_id,candidate=route.cinematic_endpoint,
            **asdict(check)))
    report = dict(schema=1,route_count=len(rows),distinct_site_checks=len(cache),
        statuses=dict(Counter(r['status'] for r in rows)),
        coordinates='logical signed16 pixels before 1.5 horizontal render projection',
        source='original movie actor endpoint and scene NPC placement, CRC-checked PFS maze',
        spawn_selection_provenance='designed; original server spawn remains unknown',
        movement_state_byte=0,movement_mask=1,
        interaction_radius=32,interaction_radius_provenance='explicit local runtime design',
        search='bounded 8-neighbor witness search; every edge uses original DDA predicate',
        max_visited_per_site=100000,routes=rows,
        limits=['A witness proves a sampled native-clear route, not the original pathfinder',
                'No witness or budget exhaustion does not prove native global unreachability',
                'Static clearance does not prove client input gates or rendered visibility'],
        server_changed=False,live_role_changed=False,client_launched=False,gui_verified=False)
    write_json(OUT/'evidence/newbie-birth-sites-audit.json',report)
    print({k:report[k] for k in ('route_count','distinct_site_checks','statuses')})
    assert len(rows) == 43 and report['statuses'] == {'reachable':43}, report['statuses']


if __name__ == '__main__':
    main()
