"""Read-only world checks for the original chapter after the first mentor."""
from dataclasses import asdict, replace
import json
from inspect_client import OUT, write_json
from world_catalog import maps, maze_grids, valid_position
from world_collision import maze_clear
from world_newbie import load_newbie_routes, validate_birth_sites, check_birth_site
from world_npcs import load_placements


def main():
    original = json.loads((OUT/'evidence/newbie-origin-client.json').read_text(encoding='utf-8'))
    equipment = json.loads((OUT/'catalogs/newbie-equipment-sources.json').read_text(encoding='utf-8'))
    nodes = {n['id']:n for b in original['branches'] for n in b['chapter_missions']}
    routes, catalog, grids, placements = load_newbie_routes(), maps(), maze_grids(), load_placements()
    births = validate_birth_sites(routes,catalog,grids,placements,state_byte=0,
                                  interaction_radius=32,max_visited=100000)
    equipment_routes = {(r['role_id'],r['school_id']):r for r in equipment['routes']}
    carriage, cache = [], {}
    for key, route in routes.items():
        after = equipment_routes[key]
        assert after['mentor_task_id'] == route.successor_task_id
        next_ids = after['post_equipment_task_ids']
        assert len(next_ids) == 1, 'Branch selection needs an explicit task policy'
        task_id = next_ids[0]
        a = nodes[task_id]['attributes']
        assert int(a['ActiveInfoMapID']) == route.home_map_id
        npc_id = int(a['ActiveInfoNpcID'])
        start = (route.home_map_id,*births[key].path[-1])
        signature = (start,npc_id)
        if signature not in cache:
            check_route = replace(route,first_npc_id=npc_id,cinematic_endpoint=start)
            cache[signature] = check_birth_site(check_route,catalog,grids[route.home_map_id],
                placements[route.home_map_id],state_byte=0,interaction_radius=32,max_visited=100000)
        carriage.append(dict(character_id=route.character_id,school_id=route.school_id,
            equipment_task_id=after['equipment_task_id'],carriage_task_id=task_id,
            carriage_npc_id=npc_id,start=start,**asdict(cache[signature])))
    jumps = []
    for task_id, node in sorted(nodes.items()):
        a = node['attributes']
        jump_type = int(a.get('RewardMapJumpType',0))
        if not jump_type:
            continue
        mid = int(a['RewardMapID'])
        cell = (int(a['RewardMapXPos']),int(a['RewardMapYPos']))
        candidate = (mid,cell[0]*16,cell[1]*16)
        bounded = valid_position(candidate,catalog)
        clear = bounded and mid in grids and maze_clear(grids[mid],*candidate[1:],mask=1)
        jumps.append(dict(task_id=task_id,original_jump_type=jump_type,
            original_target_map=mid,original_config_xy=cell,
            candidate_logical_pixels=candidate,in_bounds=bounded,mask1_clear=clear,
            source_xml_line=node['source_line']))
    result = dict(schema=1,original_chapter_nodes=len(nodes),
        first_carriage_routes=carriage,distinct_first_carriage_checks=len(cache),
        first_carriage_reachable=sum(r['status']=='reachable' for r in carriage),
        task_jump_rows=jumps,task_jump_count=len(jumps),
        candidate_jump_clear_count=sum(r['mask1_clear'] for r in jumps),
        jump_normalization=dict(formula='original config X/Y * 16',
            status='inferred; scene and portal grid convention',
            task_specific_native_consumer_verified=False,
            automatic_transfer_policy_applied=False),
        conditions=dict(native_character_state_byte=0,movement_mask=1,
                        interaction_radius=32,max_visited=100000),
        limits=['Carriage path begins at the verified approach point for the first mentor',
                'Static paths do not prove input is unlocked or client pathfinding succeeds',
                'Reward-map coordinates are preserved; task-specific unit/trigger needs native proof or design',
                'A committed task continuation must use the existing durable map handoff'],
        live_server_changed=False,live_role_changed=False,client_launched=False,gui_verified=False)
    write_json(OUT/'evidence/newbie-world-continuations-audit.json',result)
    print({k:result[k] for k in ('original_chapter_nodes','first_carriage_reachable',
        'distinct_first_carriage_checks','task_jump_count','candidate_jump_clear_count')})
    assert len(carriage) == 43 and result['first_carriage_reachable'] == 43


if __name__ == '__main__':
    main()
