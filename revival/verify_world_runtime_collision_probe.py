"""Real runtime MapOwner/SerialOwner node collision admission, no gameplay I/O.

Default safety assertion is red on the missing-maze/trusted-state wiring.
--expect-gap verifies that precise gap. Reports are saved before assertions.
"""
import argparse
import asyncio
import hashlib
import importlib
import json
from pathlib import Path
import struct
import sys

if __name__=='__main__':
    bootstrap=argparse.ArgumentParser(add_help=False)
    bootstrap.add_argument('--runtime-source',type=Path)
    selected,_=bootstrap.parse_known_args()
    if selected.runtime_source is not None:
        source=selected.runtime_source.resolve()
        if not (source/'game_runtime.py').is_file():raise ValueError('Runtime source directory required')
        sys.path.insert(0,str(source))

from game_runtime import MapOwner,Position
from world_owner import MapOwner as Domain,MapAddress,Location,MoveCommand
from world_catalog import maps,valid_position
from world_grids import maze_grid
from world_collision import maze_clear
from world_movement import ROLE_STOP
from pfs import PfsArchive
from inspect_client import ROOT

SOURCE=(360,2264)
TARGETS={'same_cell_clear':(361,2264),'blocked_original':(1664,960),'outside_bounds':(32767,32767)}


def source_hashes():
    result={}
    for name in ('game_runtime','runtime_core','world_owner','world_movement','world_catalog',
            'world_grids','world_collision','pfs'):
        path=Path(importlib.import_module(name).__file__).resolve()
        result[name]={'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    return result


async def check():
    sources=source_hashes()
    catalog=maps()
    entry='map_1006_jiaxing/maze.dat'
    raw=PfsArchive(ROOT/'artres/map.pfs').read(entry)
    grid=maze_grid(raw)
    assert valid_position((1006,*SOURCE),catalog) and maze_clear(grid,*SOURCE,mask=1)
    assert maze_clear(grid,*TARGETS['same_cell_clear'],mask=1)
    assert not maze_clear(grid,*TARGETS['blocked_original'],mask=1)
    assert not valid_position((1006,*TARGETS['outside_bounds']),catalog)
    rows=[]
    for name,target in TARGETS.items():
        address=MapAddress(1006,1006,0)
        owner=MapOwner(address,catalog)
        try:
            joined=await owner.mailbox.call('join',Position(1,1,(1006,*SOURCE),1,(22,141)))
            before=await owner.mailbox.call('location',1,1)
            assert before.position==joined.value and before.version==1
            body=b'\0'+struct.pack('>hhQ',*target,1006)
            rejection=''
            try:
                position,result=await owner.mailbox.call('move_for_encounter',1,1,1,ROLE_STOP,body)
                assert result.location.position==position.value
            except ValueError as error:
                rejection=str(error)
            after=await owner.mailbox.call('location',1,1)
            # Separate explicit state0/grid reference. This is NOT injected
            # into production or assumed for every map/scene branch.
            domain=Domain(address,catalog,capacity=1,transfer_capacity=1,mailbox_capacity=1,maze=grid)
            initial=domain.join(Location(1,1,address,1,*SOURCE))
            reference=domain.move(MoveCommand(initial,'reference-'+name,10000,ROLE_STOP,body,
                movement_state=0),1)
            rows.append({'case':name,'source':SOURCE,'target':target,
                'source_in_bounds':valid_position((1006,*SOURCE),catalog),
                'target_in_bounds':valid_position((1006,*target),catalog),
                'source_original_maze_byte':grid.cell(SOURCE[0]//16,SOURCE[1]//16),
                'target_original_maze_byte':grid.cell(target[0]//16,target[1]//16)
                    if 0<=target[0]//16<grid.width and 0<=target[1]//16<grid.height else None,
                'factory_maze_is_none':owner.domain.maze is None,
                'runtime_rejection':rejection,'runtime_after':after.position,'runtime_version':after.version,
                'explicit_state0_reference_rejection':reference.rejection})
        finally:await owner.mailbox.close()
    return {'sources':sources,'sources_stable':sources==source_hashes(),
        'probe_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'maze_source':{'archive':str(ROOT/'artres/map.pfs'),'entry':entry,
            'sha256':hashlib.sha256(raw).hexdigest(),'CRC_checked':True,'width':grid.width,'height':grid.height},
        'fixture':{'map_id':1006,'full_address':[1006,1006,0],'role_id':1,'epoch':1,'version':1,
            'checkpoint_source':'explicit trusted in-memory Position, not database/login/scene readiness',
            'movement_state_reference':0,
            'state_source':'WORLD_SCENE_MOVEMENT_STATE_RESEARCH ordinary successful A0 branch; explicit reference only, not all-map default',
            'catalog_source':'current world_catalog.maps immutable snapshot','npc_resources':None},
        'results':rows,'scope':'actual runtime MapOwner + real SerialOwner join/move_for_encounter/location; separate explicit grid/state0 Domain reference; no RoleOwner/wild_move/battle/DB/socket/GUI',
        'safe_blocked_rejection':bool(rows[1]['runtime_rejection'])}


def assert_expected(report,*,expect_gap=False):
    assert report['sources_stable'],'Source changed during probe'
    clear,blocked,bounds=report['results']
    assert clear['runtime_rejection']=='' and tuple(clear['runtime_after'][1:])==TARGETS['same_cell_clear']
    assert clear['runtime_version']==2 and clear['explicit_state0_reference_rejection']==''
    assert bounds['runtime_rejection'] and tuple(bounds['runtime_after'][1:])==SOURCE and bounds['runtime_version']==1
    assert blocked['explicit_state0_reference_rejection']=='Movement enters blocked maze cell'
    if expect_gap:
        assert blocked['factory_maze_is_none'] and blocked['runtime_rejection']==''
        assert tuple(blocked['runtime_after'][1:])==TARGETS['blocked_original'] and blocked['runtime_version']==2
    else:
        assert blocked['runtime_rejection'],'Original state0-blocked target accepted by actual runtime map factory'
        assert tuple(blocked['runtime_after'][1:])==SOURCE and blocked['runtime_version']==1


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--runtime-source',type=Path)
    parser.add_argument('--expect-gap',action='store_true')
    parser.add_argument('--report',type=Path,default=Path(__file__).parent/'evidence/world-runtime-collision-probe.json')
    args=parser.parse_args()
    report=asyncio.run(asyncio.wait_for(check(),10))
    report['mode']='expect_exact_gap' if args.expect_gap else 'assert_safe_collision'
    args.report.write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps(report,indent=2))
    assert_expected(report,expect_gap=args.expect_gap)


if __name__=='__main__':main()
