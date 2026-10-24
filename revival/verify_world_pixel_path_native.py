"""Integer-pixel planning versus original mode0/zero-limit wrapper output."""
import random
from inspect_client import OUT,write_json
from world_grids import SceneGrid
from world_pathfinding import find_pixel_path
from verify_world_native_pathfinding import NativePath


def main():
    rng=random.Random(1601)
    fixtures=[]
    for index in range(180):
        width,height=rng.randrange(2,17),rng.randrange(2,13)
        cells=bytes(rng.choices((0,1,8,9),weights=(8,2,2,1),k=width*height))
        start=(rng.randrange(width*16),rng.randrange(height*16))
        end=(rng.randrange(width*16),rng.randrange(height*16))
        fixtures.append((f'random-{index}',width,height,cells,start,end,(0,1,8,9)[index%4]))
    long_wall=bytes(1 if x==18 and y<4 else 0 for y in range(6) for x in range(32))
    fixtures.append(('long-wall-search',32,6,long_wall,(24,40),(456,40),1))
    snake=bytearray(40*12)
    for x in range(5,36,5):
        for y in range(12):
            if (y<10 if (x//5)%2 else y>=2):snake[y*40+x]=1
    fixtures.append(('long-alternating-walls',40,12,bytes(snake),(24,40),(616,40),1))
    fixtures.extend((
        ('DDA-corner-shortcut',2,2,bytes((0,1,1,0)),(8,8),(24,24),1),
        ('same-integer-point',2,2,bytes(4),(8,8),(8,8),1),
        ('clear-noncenter-target',8,6,bytes(48),(25,41),(89,41),1)))
    rows=[]
    for name,width,height,cells,start,end,mask in fixtures:
        original=NativePath(width,height,cells,mask).wrapper(start,end)
        actual=find_pixel_path(SceneGrid(width,height,cells,12),start,end,mask=mask,
            max_expansions=width*height,max_nodes=width*height,max_samples=1000000)
        expected=tuple(tuple(p) for p in original['float_path'])
        case=dict(case=name,width=width,height=height,cells_hex=cells.hex(),
            start=start,end=end,mask=mask,native_result=original['return_EAX'],
            native_points=expected,native_expanded=original['expanded_nodes'],
            actual_result=actual.native_result,actual_points=actual.points,
            actual_expanded=actual.expanded_nodes,sample_budget_used=actual.sample_budget_used)
        if (actual.native_result!=original['return_EAX'] or actual.points!=expected
                or actual.expanded_nodes!=original['expanded_nodes']):
            write_json(OUT/'evidence/world-pixel-path-native-first-failure.json',case)
            raise AssertionError(case)
        if name.startswith('long-'):
            assert original['kernel_calls']==1 and original['expanded_nodes']>=25,original
        rows.append(case)
    report=dict(seed=1601,native_differential_cases=len(rows),cases=rows,
        compared=['native return code','ordered compressed pixel positions','expanded node count'],
        scope='nonnegative integer starts/endpoints, original wrapper parameter3=0 parameter6=0 parameter7=0',
        deltas_and_height_projected=False,actor_click_adjustment_integrated=False,
        shared_runtime_integrated=False,gui_verified=False,live_server_changed=False)
    write_json(OUT/'evidence/world-pixel-path-native-verification.json',report)
    print({k:report[k] for k in ('seed','native_differential_cases','compared','scope')})


if __name__=='__main__':main()
