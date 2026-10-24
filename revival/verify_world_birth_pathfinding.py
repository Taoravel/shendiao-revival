"""Ported native planning on real birth mazes toward verified NPC approaches."""
import json
from inspect_client import OUT,write_json
from world_newbie import load_newbie_routes
from world_catalog import maps,maze_grids,valid_position
from world_npcs import load_placements
from world_collision import maze_clear,maze_segment_clear
from world_pathfinding import find_pixel_path


def main():
    routes,catalog,grids,placements=load_newbie_routes(),maps(),maze_grids(),load_placements()
    witness=json.loads((OUT/'evidence/newbie-birth-sites-audit.json').read_text(encoding='utf-8'))
    assert witness['movement_mask']==1 and witness['interaction_radius']==32
    checks={};rows=[]
    for row in witness['routes']:
        route=routes[(row['character_id'],row['school_id'])]
        assert (route.home_map_id,route.first_npc_id,route.cinematic_endpoint)==(
            row['home_map_id'],row['first_npc_id'],tuple(row['candidate']))
        key=(route.home_map_id,route.cinematic_endpoint,route.first_npc_id,row['placement_id'])
        if key not in checks:
            mid=route.home_map_id;grid=grids[mid]
            start=route.cinematic_endpoint[1:];goal=tuple(row['path'][-1])
            npc=next(p for p in placements[mid] if p.placement_id==row['placement_id'])
            assert npc.npc_id==route.first_npc_id
            assert valid_position((mid,*goal),catalog)
            assert maze_clear(grid,*start,mask=1) and maze_clear(grid,*goal,mask=1)
            result=find_pixel_path(grid,start,goal,mask=1,max_expansions=100000,
                max_nodes=100000,max_samples=10000000)
            assert result.native_result in (0,3),(key,result)
            path=(start,*result.points)
            assert all(valid_position((mid,*p),catalog) and maze_clear(grid,*p,mask=1) for p in path)
            assert all(maze_segment_clear(grid,a,b,mask=1) for a,b in zip(path,path[1:]))
            assert (path[-1][0]-npc.x)**2+(path[-1][1]-npc.y)**2<=32**2
            checks[key]=dict(home_map_id=mid,first_npc_id=route.first_npc_id,
                placement_id=npc.placement_id,npc_position=(npc.x,npc.y),
                start=start,goal=goal,path=path,native_result=result.native_result,
                expanded_nodes=result.expanded_nodes,discovered_nodes=result.discovered_nodes,
                sample_budget_used=result.sample_budget_used)
        rows.append(dict(character_id=route.character_id,school_id=route.school_id,
            home_map_id=route.home_map_id,first_npc_id=route.first_npc_id,status='reachable'))
    assert len(rows)==43 and len(checks)==10
    report=dict(route_count=len(rows),distinct_real_maze_paths=len(checks),
        cases=list(checks.values()),routes=rows,all_legs_native_DDA_clear=True,
        all_final_points_within_designed_NPC_radius=True,
        target_selection='Previously verified approach point, not NPC center or an invented nearest-clear policy',
        budgets='explicit offline fixture caps, not production defaults',
        scope='pure port on actual mazes; not original emulator on full maps or real client navigation',
        shared_runtime_integrated=False,gui_verified=False,client_launched=False,live_server_changed=False)
    write_json(OUT/'evidence/world-birth-pathfinding-verification.json',report)
    print({k:report[k] for k in ('route_count','distinct_real_maze_paths',
        'all_legs_native_DDA_clear','all_final_points_within_designed_NPC_radius')})


if __name__=='__main__':main()
