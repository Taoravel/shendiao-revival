"""Differential public grid planning against actual original instructions."""
import random
from inspect_client import OUT,write_json
from world_grids import SceneGrid
from world_pathfinding import find_grid_path
from verify_world_native_pathfinding import NativePath


def main():
    rng=random.Random(601)
    rows=[]
    for index in range(320):
        width,height=rng.randrange(2,13),rng.randrange(2,13)
        cells=bytes(rng.choices((0,1,8,9),weights=(7,2,2,1),k=width*height))
        start=(rng.randrange(width),rng.randrange(height))
        goal=(rng.randrange(width),rng.randrange(height))
        mask=(0,1,8,9)[index%4]
        original=NativePath(width,height,cells,mask).kernel(start,goal)
        planned=find_grid_path(SceneGrid(width,height,cells,12),start,goal,mask=mask,
            max_expansions=width*height,max_nodes=width*height)
        expected=tuple(tuple(p) for p in original['grid_path'])
        case=dict(index=index,width=width,height=height,mask=mask,start=start,goal=goal,
            cells_hex=cells.hex(),native_success=bool(original['return_AL']),
            native_path=expected,native_expanded=original['expanded_nodes'],
            actual_status=planned.status,actual_path=planned.path,actual_expanded=planned.expanded_nodes)
        if (bool(original['return_AL'])!=(planned.status=='found')
                or planned.path!=expected or planned.expanded_nodes!=original['expanded_nodes']):
            write_json(OUT/'evidence/world-pathfinding-native-first-failure.json',case)
            raise AssertionError(case)
        rows.append(case)
    report=dict(seed=601,native_differential_cases=len(rows),cases=rows,
        compared=['success/failure','complete ordered path','expanded node count'],
        scope='full dense-grid kernel with explicit mask, adequate caller budgets; not pixel/click wrapper',
        original_host_adapters=['allocation/free','security cookie','memset','memcpy'],
        shared_runtime_integrated=False,gui_verified=False,live_server_changed=False)
    write_json(OUT/'evidence/world-pathfinding-native-verification.json',report)
    print({k:report[k] for k in ('seed','native_differential_cases','compared','scope')})


if __name__=='__main__':main()
