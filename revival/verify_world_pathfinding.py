"""Public bounded grid search, checked against original kernel results."""
from inspect_client import OUT,write_json
from world_grids import SceneGrid
from world_pathfinding import find_grid_path,find_pixel_path
from unittest.mock import patch


def main():
    grid=SceneGrid(8,6,bytes(48),12)
    result=find_grid_path(grid,(1,2),(5,2),mask=1,max_expansions=48,max_nodes=48)
    assert result.status=='found'
    assert result.path==((2,2),(3,2),(4,2),(5,2))
    assert result.expanded_nodes==4
    wall=bytearray(48)
    for y in range(4):wall[y*8+3]=1
    result=find_grid_path(SceneGrid(8,6,bytes(wall),12),(1,2),(5,2),
        mask=1,max_expansions=48,max_nodes=48)
    assert result.status=='found'
    assert result.path==((2,3),(2,4),(3,4),(4,4),(4,3),(5,2)),result
    assert result.expanded_nodes==16,result
    pixel=find_pixel_path(SceneGrid(8,6,bytes(wall),12),(24,40),(89,41),
        mask=1,max_expansions=48,max_nodes=48,max_samples=10000)
    assert pixel.native_result==0 and pixel.status=='found'
    assert pixel.points==((56,72),(88,40)),pixel
    assert pixel.expanded_nodes==16
    direct=find_pixel_path(grid,(25,41),(89,41),mask=1,
        max_expansions=48,max_nodes=48,max_samples=10000)
    assert direct.points==((89,41),) and direct.expanded_nodes==0
    short=find_pixel_path(grid,(8,8),(8,8),mask=1,
        max_expansions=48,max_nodes=48,max_samples=1)
    assert short.native_result==3 and not short.points and short.sample_budget_used==0
    shortcut=find_pixel_path(SceneGrid(2,2,bytes((0,1,1,0)),12),(8,8),(24,24),
        mask=1,max_expansions=4,max_nodes=4,max_samples=100)
    assert shortcut.native_result==0 and shortcut.points==((24,24),) and shortcut.expanded_nodes==0
    for samples,expected_expanded in ((1,0),(65,16)):
        exhausted=find_pixel_path(SceneGrid(8,6,bytes(wall),12),(24,40),(89,41),
            mask=1,max_expansions=48,max_nodes=48,max_samples=samples)
        assert exhausted.status=='budget' and exhausted.native_result is None and not exhausted.points
        assert exhausted.expanded_nodes==expected_expanded and exhausted.sample_budget_used<=samples
    full=bytes(1 if x==3 else 0 for y in range(6) for x in range(8))
    blocked=find_grid_path(SceneGrid(8,6,full,12),(1,2),(5,2),
        mask=1,max_expansions=48,max_nodes=48)
    assert blocked.status=='not_found' and not blocked.path and blocked.expanded_nodes==18
    corner=find_grid_path(SceneGrid(2,2,bytes((0,1,1,0)),12),(0,0),(1,1),
        mask=1,max_expansions=4,max_nodes=4)
    assert corner.status=='not_found' and corner.expanded_nodes==1
    native_start=bytearray(48);native_start[2*8+1]=1
    from_blocked=find_grid_path(SceneGrid(8,6,bytes(native_start),12),(1,2),(5,2),
        mask=1,max_expansions=48,max_nodes=48)
    assert from_blocked.status=='found' and from_blocked.path==((2,2),(3,2),(4,2),(5,2))
    native_start[2*8+5]=1
    at_goal=find_grid_path(SceneGrid(8,6,bytes(native_start),12),(1,2),(5,2),
        mask=1,max_expansions=48,max_nodes=48)
    assert at_goal.status=='blocked_goal' and not at_goal.path and at_goal.expanded_nodes==0
    same=find_grid_path(grid,(1,2),(1,2),mask=1,max_expansions=48,max_nodes=48)
    assert same.status=='same_cell' and not same.path and same.expanded_nodes==0
    switched=find_grid_path(SceneGrid(8,6,bytes(wall),12),(1,2),(5,2),
        mask=8,max_expansions=48,max_nodes=48)
    assert switched.path==((2,2),(3,2),(4,2),(5,2))
    with patch('builtins.open',side_effect=AssertionError('Search file I/O')), \
         patch('io.open',side_effect=AssertionError('Search file I/O')):
        limited=find_grid_path(grid,(1,2),(5,2),mask=1,max_expansions=1,max_nodes=48)
        memory=find_grid_path(grid,(1,2),(5,2),mask=1,max_expansions=48,max_nodes=2)
        retry=find_grid_path(grid,(1,2),(5,2),mask=1,max_expansions=48,max_nodes=48)
    assert limited.status=='budget' and not limited.path and limited.expanded_nodes==1
    assert memory.status=='budget' and not memory.path and memory.discovered_nodes==2
    assert retry.path==((2,2),(3,2),(4,2),(5,2)) and retry.expanded_nodes==4
    for changed in ({'mask':True},{'max_expansions':0},{'max_nodes':True}):
        args=dict(mask=1,max_expansions=48,max_nodes=48);args.update(changed)
        try:find_grid_path(grid,(1,2),(5,2),**args)
        except ValueError:pass
        else:raise AssertionError('Missing explicit valid mask/budget accepted')
    for invalid_grid in (SceneGrid(1921,1,bytes(1921),12),
            SceneGrid(2,2,bytes(4),12,bytes((1,1,0,1))),SceneGrid(2,2,b'\0',12)):
        try:find_grid_path(invalid_grid,(0,0),(1,0),mask=1,max_expansions=4,max_nodes=4)
        except ValueError:pass
        else:raise AssertionError('Unsupported or incomplete grid accepted')
    report=dict(passed=['original clear-grid path and target-before-pop behavior',
        'original around-wall path and expansion count',
        'original pixel compression keeps cell-center search target; direct shortcut keeps exact requested pixel',
        'pixel same-point and original DDA corner shortcut are distinct from kernel behavior',
        'conservative DDA work budget refuses both before search and during smoothing without a partial route',
        'closed wall and kernel diagonal-corner refusal',
        'native blocked-start behavior retained; blocked-goal and same-cell return no route',
        'explicit mask changes actual maze flags',
        'expansion and node caps return no partial route; fresh retry has no shared residue',
        'invalid masks/budgets and incomplete/oversized grids refused',
        'no search file I/O'],
        shared_runtime_integrated=False,gui_verified=False,live_server_changed=False)
    write_json(OUT/'evidence/world-pathfinding-verification.json',report)
    print(report)


if __name__=='__main__':main()
