"""Nine unchanged blocked exit landings -> original input/MOVE/actor/CHECK.

Offline only. Fixture mouse goal is not a proposed landing or server policy.
"""
import hashlib
import json
import struct
from pathlib import Path

from bxml import decode
from native_inspect import DATA
from pfs import PfsArchive
from world_grids import maze_grid
from verify_world_click_check_native import ClickCheckProbe
from research_world_portal_exit_sources import PAIRS
from unicorn.x86_const import UC_X86_REG_ESP

ROOT = Path(__file__).resolve().parent


class ExitClickProbe(ClickCheckProbe):
    # Large map 1007 requires 252416 maze bytes. The inherited small-map
    # fixture starts at 5031000 and would overwrite mouse/session objects at
    # 5040000. Relocate raw maze storage only; preserve every original byte.
    maze_cells = 0x5080000

    def __init__(self,*args,**kwargs):
        self.exit_path_entries=[]
        super().__init__(*args,**kwargs)

    def hook(self,emu,addr,size,user):
        if addr == 0x11f8800:
            sp=emu.reg_read(UC_X86_REG_ESP)
            caller=self.read(sp)
            if 0x12143b0 <= caller < 0x1214b00:
                self.exit_path_entries.append({'caller_return':hex(caller),
                'goal':struct.unpack('<ii',emu.mem_read(sp+4,8)),
                'adjusted_source_local':struct.unpack('<ii',emu.mem_read(sp+0x44,8)),
                'original_current_local':struct.unpack('<ii',emu.mem_read(sp+0x4c,8)),
                'actor_projected':struct.unpack('<ff',emu.mem_read(self.path+8,8))})
        super().hook(emu,addr,size,user)


def main():
    config = PfsArchive(ROOT.parent/'artres/config.pfs')
    maps = PfsArchive(ROOT.parent/'artres/map.pfs')
    configs = {int(e.attrib['id']):dict(e.attrib) for e in decode(
        config.read('autoconfig/knight.gsp.map.cmapconfig.xml'))}
    cases = []
    for source,target in PAIRS.items():
        goto_name = configs[source]['resdir']+'/goto.xml'
        goto_raw = maps.read(goto_name)
        goto = next(iter(decode(goto_raw))).attrib
        assert int(goto['destmap']) == target
        current = (int(goto['destx'])*16,int(goto['desty'])*16)
        maze_name,rmp_name = (configs[target]['resdir']+'/'+n for n in ('maze.dat','map.rmp'))
        maze,rmp = maps.read(maze_name),maps.read(rmp_name)
        grid = maze_grid(maze)
        cx,cy = (v//16 for v in current)
        assert grid.cell(cx,cy) == 11
        # Deterministic click-only fixture search. Never changes current/landing.
        # Host picks a clear goal so this tests blocked-start handling, not the
        # already-researched blocked-goal adjustment or original server spawn.
        candidates = [(max(abs(x-cx),abs(y-cy)),y,x)
            for y in range(max(0,cy-24),min(grid.height,cy+25))
            for x in range(max(0,cx-24),min(grid.width,cx+25)) if not grid.cell(x,y)&1]
        assert candidates
        _,gy,gx = min(candidates)
        goal = (gx*16,gy*16)
        assert len(grid.cells) < 0x80000
        run = ExitClickProbe(grid.width,grid.height,grid.cells,current,
            render_size=struct.unpack_from('<II',rmp,8))
        run.w(run.scene+0x30,target,0)
        camera = (goal[0]*3//2-48,goal[1]-48)
        run.w(run.canvas+0x488,*camera,0,0)
        result = {'source_map':source,'target_map':target,'unchanged_landing':current,
            'landing_maze_byte':grid.cell(cx,cy),'controlled_mouse_goal':goal,
            'fixture_goal_cell':(gx,gy),'fixture_goal_byte':grid.cell(gx,gy),
            'fixture_camera_projected':camera,'raw_mouse':run.mouse_position,
            'sources':[{'entry':n,'sha256':hashlib.sha256(raw).hexdigest(),'CRC_checked':True}
                for n,raw in ((goto_name,goto_raw),(maze_name,maze),(rmp_name,rmp))]}
        try:
            result['before_input'] = run.snapshot()
            result['input'] = run.input_tick()
            result['after_input'] = run.snapshot()
            run.call(0x6529b0,(0x3f800000,),ecx=run.actor)
            result['first_actor_tick'] = run.actor_tick(1001,1)
            run.call(0x12179a0,(1500,500))
            result['after_timed_check'] = run.snapshot()
            steps = []
            for tick in range(1,65):
                state = run.actor_tick(1500+tick*64,64)
                steps.append(state)
                if not state['future_engine']:
                    break
            result['bounded_actor_ticks'] = steps
            result['messages'] = run.messages
            result['native_goal_queries'] = run.queries
            result['native_path_entries'] = run.exit_path_entries
            result['native_DDA_samples'] = run.dda_trace
            result['native_trace'] = sorted(set(run.visited+run.arrival_trace))
            result['first_move_source_equals_landing'] = (tuple(run.role_moves[0]['start']) == current) if run.role_moves else None
            result['actor_changed'] = tuple(result['first_actor_tick']['current']) != current
            result['stop_seen'] = any(m['kind']==0xc0faa for m in run.messages)
        except Exception as exc:
            result.update(error=repr(exc),recent=run.recent,messages=run.messages)
        cases.append(result)
        # Persist partial evidence after each independent source case.
        output = {'image_sha256':hashlib.sha256(DATA).hexdigest(),'cases':cases,
            'scope':'offline original held-input -> path -> first MOVE -> actor ticks -> timed CHECK/STOP',
            'adapters':['Host supplies original target map bytes, exact rawgoto*16 landing, scene context and object graph.',
                'Mouse device, camera, held latch, clock budgets and speed multiplier 1.0 are controlled fixtures.',
                'Rendering, allocator/STL and send-sink adapters are inherited from named native probes; original sender-built objects marshal before destruction.',
                'No OS input, full scene loader, socket transport, original server coordinate or production policy claim.'],
            'no_production_changes':True}
        (ROOT/'evidence/world-blocked-exit-click-native.json').write_text(json.dumps(output,indent=2),encoding='utf-8')
        print(json.dumps({k:result.get(k) for k in ('source_map','target_map','unchanged_landing','controlled_mouse_goal','first_move_source_equals_landing','actor_changed','stop_seen','error')}),flush=True)
    assert len(cases)==9 and all('error' not in c for c in cases)
    assert [c['source_map'] for c in cases if c['messages']] == [1301,1305]
    for case in cases:
        assert case['input']['mouse_reads']==1
        assert tuple(case['after_input']['current']) == tuple(case['unchanged_landing'])
        if case['messages']:
            assert case['first_move_source_equals_landing'] and case['actor_changed'] and case['stop_seen']
            assert [m['kind'] for m in case['messages']] == [0xc0fa1,0xc0fa3,0xc0faa]
        else:
            assert len(case['native_goal_queries'])==66
            assert all(q['blocked'] for q in case['native_goal_queries'][1:])
            assert not case['actor_changed'] and not case['stop_seen']
    output['all_expected_observations_passed']=True
    output['dependency_sha256']={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest()
        for n in ('verify_world_blocked_exit_click_native.py','verify_world_click_check_native.py',
            'verify_world_click_arrival_native.py','verify_world_click_move_native.py',
            'verify_world_blocked_goal_adjustment.py','verify_world_movement_reconciliation_native.py',
            'verify_movement_reports_native.py','pfs.py','bxml.py','world_grids.py')}
    (ROOT/'evidence/world-blocked-exit-click-native.json').write_text(json.dumps(output,indent=2),encoding='utf-8')


if __name__ == '__main__':
    main()
