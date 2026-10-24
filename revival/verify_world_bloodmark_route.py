"""Exclusive offline bloodmark route diagnosis; temporary DB, no task edits."""
import asyncio
from collections import deque
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import struct
import tempfile

import verify_prologue_touch_runtime as integration
from accounts import AccountStore
from inspect_client import OUT
import runtime_storage
from world_newbie import load_newbie_routes
from world_catalog import maps,maze_grids
from world_grids import maze_grid
from world_collision import maze_clear,maze_segment_result
from world_pathfinding import find_pixel_path
from pfs import PfsArchive
from native_inspect import DATA
from verify_world_native_pathfinding import NativePath
from unicorn.x86_const import (UC_X86_REG_ESP,UC_X86_REG_EAX,UC_X86_REG_ECX,
    UC_X86_REG_EDX,UC_X86_REG_EIP)


class BloodmarkNative(NativePath):
    # Full Jiaxing maze is larger than old small-fixture cells/workspace gap.
    cells=0x5800000

    def __init__(self,*args,**kwargs):
        self.samples=[]
        super().__init__(*args,**kwargs)

    def hook(self,emu,addr,size,user):
        if addr==0x6284f0:
            self.samples.append((emu.reg_read(UC_X86_REG_EAX),self.r(emu.reg_read(UC_X86_REG_ESP)+8)))
        super().hook(emu,addr,size,user)

    def execute(self,at,eax=0,ecx=0,edx=0,args=()):
        self.w(self.stack,self.stop,*args)
        for reg,value in ((UC_X86_REG_ESP,self.stack),(UC_X86_REG_EAX,eax),
                          (UC_X86_REG_ECX,ecx),(UC_X86_REG_EDX,edx)):
            self.uc.reg_write(reg,value&0xffffffff)
        # Explicit offline instruction budget, not an original search policy.
        self.uc.emu_start(at,self.stop,count=20000000)
        assert self.uc.reg_read(UC_X86_REG_EIP)==self.stop,hex(self.uc.reg_read(UC_X86_REG_EIP))
        return self.uc.reg_read(UC_X86_REG_EAX)

    def dda(self,a,b):
        self.samples=[]
        result=self.execute(0x626b40,eax=b[0],edx=a[0],ecx=a[1],args=(b[1],self.query,self.query))
        return {'start':a,'end':b,'native_result':result,'samples':list(self.samples)}

    def point(self,p):
        self.w(self.start_vec,0,self.query)
        return bool(self.execute(0x6284f0,eax=p[0],args=(self.start_vec,p[1]))&255)


def reproduce():
    captured={}
    original=integration.check_birth_site
    def capture(route,*args,**kwargs):
        result=original(route,*args,**kwargs)
        captured.update(source=route.cinematic_endpoint,npc_id=route.first_npc_id,
            placements=[asdict(p) for p in args[2]],arguments=kwargs,
            sampled_result=asdict(result))
        print(json.dumps({'reproduced_route':captured}),flush=True)
        return result
    integration.check_birth_site=capture
    route=load_newbie_routes()[(9,11)]
    audit=json.loads((OUT/'evidence/newbie-birth-sites-audit.json').read_text(encoding='utf-8'))
    witness=next(r for r in audit['routes'] if (r['character_id'],r['school_id'])==(9,11))
    try:
        with tempfile.TemporaryDirectory(prefix='bloodmark-route-research-') as directory:
            store=AccountStore(Path(directory)/'state.sqlite3')
            prepared=runtime_storage.prepare(store)
            role=store.create_role(1111,'血印路线研究',11,1010109)
            try:
                asyncio.run(asyncio.wait_for(integration.check(store,prepared,role,route,witness),60))
            except AssertionError as error:
                assert captured and captured['sampled_result']['status']=='no_witness',str(error)
                captured['natural_integration_failed_at_route']=True
    finally:
        integration.check_birth_site=original
    assert captured['natural_integration_failed_at_route']
    return captured


def main():
    natural=reproduce()
    assert tuple(natural['source'])==(1006,360,2264)
    start=tuple(natural['source'][1:])
    target=tuple(natural['placements'][0][k] for k in ('x','y'))
    assert target==(1668,970) and natural['sampled_result']['visited']==44928
    root=Path(__file__).resolve().parent
    mn,rn='map_1006_jiaxing/maze.dat','map_1006_jiaxing/map.rmp'
    archive=PfsArchive(root/'runtime/client/artres/map.pfs')
    raw,rmp=archive.read(mn),archive.read(rn)
    grid=maze_grid(raw)
    assert grid==maze_grids()[1006]
    width,height=struct.unpack_from('<II',rmp,8)
    assert (width*2//3,height)==(maps()[1006]['width'],maps()[1006]['height'])==(6144,4736)
    assert (grid.width,grid.height)==(384,296)
    component={(start[0]//16,start[1]//16)}
    queue=deque(component)
    while queue:
        x,y=queue.popleft()
        for dx,dy in ((0,-1),(-1,0),(1,0),(0,1)):
            p=(x+dx,y+dy)
            if (0<=p[0]<grid.width and 0<=p[1]<grid.height and p not in component
                    and not grid.cell(*p)&1):
                component.add(p);queue.append(p)
    clear=[]
    for y in range(grid.height):
        for x in range(grid.width):
            if grid.cell(x,y)&1:continue
            p=(min(max(target[0],x*16),x*16+15),min(max(target[1],y*16),y*16+15))
            d=(p[0]-target[0])**2+(p[1]-target[1])**2
            clear.append((d,p,(x,y),(x,y) in component))
    nearest=sorted(clear)
    assert len(component)==44928 and len(clear)==51277
    assert nearest[0]==(1444,(1668,1008),(104,63),True)
    circle=[]
    reps={}
    for y in range(target[1]-32,target[1]+33):
        for x in range(target[0]-32,target[0]+33):
            if (x-target[0])**2+(y-target[1])**2<=32**2:
                circle.append((x,y));reps.setdefault((x//16,y//16),(x,y))
    assert all(not maze_clear(grid,*p,mask=1) for p in circle)
    nearest_pixel=nearest[0][1]
    planned=find_pixel_path(grid,start,nearest_pixel,mask=1,max_expansions=113664,
        max_nodes=113664,max_samples=10000000)
    assert planned.status=='found'
    native=BloodmarkNative(grid.width,grid.height,grid.cells,1)
    wrapped=native.wrapper(tuple(map(float,start)),nearest_pixel)
    wrapped_points=tuple(tuple(map(int,p)) for p in wrapped['float_path'])
    assert wrapped['return_EAX']==0 and wrapped_points==planned.points
    assert wrapped['expanded_nodes']==planned.expanded_nodes==773
    assert wrapped_points==((1032,1560),(1672,1016))
    witness=(start,*wrapped_points,nearest_pixel)
    segments=[native.dda(a,b) for a,b in zip(witness,witness[1:])]
    for segment in segments:
        assert segment['native_result']==0
        assert maze_segment_result(grid,segment['start'],segment['end'],mask=1)==0
        assert all(maze_clear(grid,*p,mask=1) for p in segment['samples'])
    direct=native.dda(start,nearest_pixel)
    assert direct['native_result']==1
    circle_native=[]
    for cell,p in sorted(reps.items()):
        flag=grid.cell(*cell)
        clear_original=native.point(p)
        assert not clear_original and flag&1
        circle_native.append({'cell':cell,'representative_in_circle':p,'maze_flag':flag,
            'original_6284f0_clear':clear_original})
    assert native.point(nearest_pixel)
    assert (nearest_pixel[0]-target[0])**2+(nearest_pixel[1]-target[1])**2>32**2
    center=min(((x*16+8-target[0])**2+(y*16+8-target[1])**2,(x*16+8,y*16+8),(x,y)) for x,y in component)
    result={'all_passed':True,'native_image_sha256':hashlib.sha256(DATA).hexdigest(),
        'natural_source_reproduction':natural,'map_id':1006,'source':start,
        'target_placement':natural['placements'][0],'mask':1,'radius_under_test':32,
        'radius32_witness_exists':False,'reason':'all integer pixels in target disk blocked under native mask1',
        'target_maze_flag':grid.cell(target[0]//16,target[1]//16),
        'raw_RMP_render_size':[width,height],'logical_map_size':[6144,4736],
        'circle_integer_pixels':len(circle),'circle_clear_pixels':0,
        'circle_native_cell_representatives':circle_native,
        'all_clear_cells':len(clear),'source_four_connected_cells':len(component),
        'component_cells_sha256':hashlib.sha256(b''.join(struct.pack('<HH',*p) for p in sorted(component))).hexdigest(),
        'nearest_global_clear_pixel':{'point':nearest_pixel,'distance_squared':1444,'distance':38,
            'cell':(104,63),'in_source_component':True},
        'nearest_component_center':{'distance_squared':center[0],'point':center[1],'cell':center[2]},
        'nearest_clear_rectangles':[{'distance_squared':d,'nearest_pixel':p,'cell':c,'in_source_component':r}
            for d,p,c,r in nearest[:12]],
        'native_wrapper_to_nearby_clear_area':wrapped,'python_pixel_wrapper':asdict(planned),
        'diagnostic_nearby_witness':{'points':witness,'within_requested_radius':False,
            'last_segment':'extra diagnostic DDA-clear leg to exact nearest pixel; not emitted by wrapper',
            'original_DDA_segments':segments},
        'direct_source_to_nearest_DDA':direct,
        'sources':[{'entry':n,'sha256':hashlib.sha256(b).hexdigest(),'CRC_checked':True} for n,b in ((mn,raw),(rn,rmp))],
        'prefix_script_sha256':hashlib.sha256(Path(integration.__file__).read_bytes()).hexdigest(),
        'scope':'temporary-DB natural prefix through bloodmark route failure; geometry/native planning only after failure',
        'unchanged':['mask','radius','NPC position','task progression','production/shared/policies/old verifiers'],
        'unverified':['original NPC approach semantics','native GUI travel','different movement states or noninteger actor coordinates']}
    path=Path(__file__).parent/'evidence/world-bloodmark-route-verification.json'
    path.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'all_passed':True,'source':start,'radius32_clear_pixels':0,
        'nearest_clear_distance':38,'native_wrapper_points':wrapped_points,'result':str(path)}))


if __name__=='__main__':main()
