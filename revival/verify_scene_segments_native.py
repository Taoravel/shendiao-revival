"""Offline differential of original segment predicate, with original point calls."""
import hashlib
import json
from pathlib import Path
import random
import struct
from native_inspect import BASE, DATA, capstone
from world_collision import maze_segment_result, _segment_samples
from world_grids import SceneGrid


def main():
    from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
    from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_EDX, UC_X86_REG_ECX, UC_X86_REG_ESP, UC_X86_REG_EIP
    uc=Uc(UC_ARCH_X86,UC_MODE_32)
    uc.mem_map(BASE,(len(DATA)+4095)&~4095);uc.mem_write(BASE,DATA)
    uc.mem_map(0x5000000,0x10000)
    stack,stop,layout,cells=0x5001000,0x500f000,0x5002000,0x5003000
    def put(address,*values):uc.mem_write(address,struct.pack('<'+'I'*len(values),*(v&0xffffffff for v in values)))
    trace=[]
    def signed(v):return v if v<0x80000000 else v-0x100000000
    def hook(emu,address,size,user):
        if address==0x6284f0:
            sp=emu.reg_read(UC_X86_REG_ESP)
            y=struct.unpack('<I',emu.mem_read(sp+8,4))[0]
            trace.append((signed(emu.reg_read(UC_X86_REG_EAX)),signed(y)))
    uc.hook_add(UC_HOOK_CODE,hook)
    def run(grid,start,end,mask):
        trace.clear();uc.mem_write(cells,grid.cells)
        put(layout,grid.width,grid.height,cells,mask,0,0,grid.width,grid.height)
        # Native routine sees a two-pointer wrapper by value after end_y.
        put(stack,stop,end[1],layout,layout)
        uc.reg_write(UC_X86_REG_ESP,stack)
        uc.reg_write(UC_X86_REG_EAX,end[0]&0xffffffff)
        uc.reg_write(UC_X86_REG_EDX,start[0]&0xffffffff)
        uc.reg_write(UC_X86_REG_ECX,start[1]&0xffffffff)
        uc.emu_start(0x626b40,stop,count=6000000)
        assert uc.reg_read(UC_X86_REG_EIP)==stop
        result=uc.reg_read(UC_X86_REG_EAX)
        expected=maze_segment_result(grid,start,end,mask=mask)
        assert result==expected,(start,end,mask,result,expected)
        expected_trace=list(_segment_samples(start,end))
        if result==1:expected_trace=expected_trace[:len(trace)]
        assert trace==expected_trace,(start,end,trace,expected_trace)
        return {'start':start,'end':end,'mask':mask,'native_result':result,'samples':list(trace)}
    clear=SceneGrid(4,4,bytes(16),12)
    rng=random.Random(601)
    segments=[((8,8),(56,8)),((56,8),(8,8)),((8,8),(8,56)),((8,56),(8,8)),
              ((8,8),(56,56)),((56,56),(8,8)),((8,8),(56,24)),((56,24),(8,8)),
              ((8,8),(24,56)),((24,56),(8,8)),((8,56),(24,8)),((24,8),(8,56)),
              ((16,16),(16,16)),((-15,-1),(17,18)),((-16,0),(17,18))]
    segments += [((rng.randrange(64),rng.randrange(64)),(rng.randrange(64),rng.randrange(64))) for _ in range(128)]
    total=0
    for start,end in segments:
        for mask in (1,8):
            run(clear,start,end,mask);total+=1
            for index in range(16):
                flags=bytearray(16);flags[index]=mask
                run(SceneGrid(4,4,bytes(flags),12),start,end,mask);total+=1
    flags=bytearray(16);flags[1]=1
    across=run(SceneGrid(4,4,bytes(flags),12),(8,8),(56,8),1)
    same_flags=bytes([1])+bytes(15)
    same=run(SceneGrid(4,4,same_flags,12),(8,8),(8,8),1)
    # Side cells around a diagonal contact are blocked; native centerline still
    # passes. Do not add a server supercover/corner prohibition and call it native.
    corners=bytearray(16);corners[1]=corners[4]=1
    corner=run(SceneGrid(4,4,bytes(corners),12),(8,8),(24,24),1)
    assert across['native_result']==1 and same['native_result']==3 and corner['native_result']==0
    report={'image_sha256':hashlib.sha256(DATA).hexdigest(),'routine':'0x626b40',
            'native_differential_cases':total,'counterfactuals':{'wall_between_clear_endpoints':across,'same_point_blocked_cell':same,'diagonal_side_cells_blocked':corner},
            'mode':'unmodified segment and point instructions; code hook observes samples only',
            'wire_path_nodes_semantics':'check/stop copy role+0x34c; append/pop timing not fully established'}
    out=Path(__file__).resolve().parent/'evidence'
    (out/'scene-segment-native.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    cs=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
    (out/'scene-segment-native-disassembly.txt').write_text('\n'.join(f'{i.address:08x} {i.mnemonic:8} {i.op_str}' for i in cs.disasm(DATA[0x626b40-BASE:0x626cb9-BASE],0x626b40)),encoding='utf-8')
    # Preserve the actual caller/builder fragments used for the static claims.
    ranges=((0x6138f7,0x4e),(0x6bc3d9,0x2b),(0x12160b0,0x8b),
            (0x121720e,0xaa),(0x1217f73,0x63),(0x1214b60,0x39),
            (0x121793e,0x40),(0x1214110,0x30))
    builder_text='native-image.bin SHA256 '+report['image_sha256']+'\n'
    for start,size in ranges:
        builder_text += '\n'+'\n'.join(f'{i.address:08x} {i.mnemonic:8} {i.op_str}' for i in cs.disasm(DATA[start-BASE:start-BASE+size],start))+'\n'
    (out/'movement-report-builders-disassembly.txt').write_text(builder_text,encoding='utf-8')
    print(json.dumps({'cases':total,'counterfactual_results':{k:v['native_result'] for k,v in report['counterfactuals'].items()}}))

if __name__=='__main__':main()
