"""Offline native write-set test for the proposed first-time material refresh."""
import json
from pathlib import Path
import struct
from native_inspect import DATA, BASE, u32
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_EIP, UC_X86_REG_ESP, UC_X86_REG_ECX


def run(enabled, random_value):
    emu=Uc(UC_ARCH_X86,UC_MODE_32)
    emu.mem_map(BASE,(len(DATA)+4095)&~4095);emu.mem_write(BASE,DATA)
    emu.mem_map(0x5000000,0x100000)
    obj,vector,entry,stack,stop=0x5001000,0x5001800,0x5002000,0x5080000,0x500f000
    def w(addr,value):emu.mem_write(addr,struct.pack('<I',value))
    w(obj+8,vector);w(obj+12,vector+4);w(obj+16,vector+4);w(vector,entry)
    before=bytearray(b'\x55'*0x100);before[0x30:0x34]=struct.pack('<I',1 if enabled else 0)
    emu.mem_write(entry,bytes(before));w(stack,stop)
    rand,invalid=u32(0x22448cc),u32(0x2244898)
    for page in {p&~4095 for p in (rand,invalid) if not BASE<=p<BASE+len(DATA)}:
        emu.mem_map(page,4096)
    def hook(uc,address,size,user):
        if address==stop:uc.emu_stop()
        elif address==invalid:raise AssertionError('native invalid iterator')
        elif address==rand:
            sp=uc.reg_read(UC_X86_REG_ESP);ret=struct.unpack('<I',uc.mem_read(sp,4))[0]
            uc.reg_write(UC_X86_REG_ESP,sp+4);uc.reg_write(UC_X86_REG_EAX,random_value)
            uc.reg_write(UC_X86_REG_EIP,ret)
    emu.hook_add(UC_HOOK_CODE,hook)
    emu.reg_write(UC_X86_REG_EAX,obj);emu.reg_write(UC_X86_REG_ESP,stack)
    emu.emu_start(0x692330,stop,count=10000)
    assert emu.reg_read(UC_X86_REG_EIP)==stop
    after=bytes(emu.mem_read(entry,0x100))
    changed=[i for i,(a,b) in enumerate(zip(before,after)) if a!=b]
    allowed=set(range(0x64,0x6c)) if enabled else set()
    assert set(changed)<=allowed
    times=struct.unpack_from('<ii',after,0x64)
    if enabled:assert times==(6745000+random_value%10000,745000+random_value%10000)
    else:assert after==before
    return {'effect_flag_bit1':enabled,'rand_fixture':random_value,
            'changed_entry_offsets':[hex(i) for i in changed],
            'time_64_68':list(times) if enabled else None,
            'color_alpha_and_other_entry_bytes_unchanged':True}


def game_time(scene_present):
    emu=Uc(UC_ARCH_X86,UC_MODE_32)
    emu.mem_map(BASE,(len(DATA)+4095)&~4095);emu.mem_write(BASE,DATA)
    emu.mem_map(0x5000000,0x100000)
    obj,timeptr,world,scene,stack,stop=0x5001000,0x5002000,0x5003000,0x5004000,0x5080000,0x500f000
    def w(addr,value):emu.mem_write(addr,struct.pack('<I',value))
    def r(addr):return struct.unpack('<I',emu.mem_read(addr,4))[0]
    for a in (0x2944720,0x2945584,0x2945620,0x29455ac):w(a,0)
    w(0x2944564,scene if scene_present else 0);w(0x29a4a70+0x40,world)
    sentinel=b'\x55'*0x700;emu.mem_write(world,sentinel);emu.mem_write(scene,sentinel)
    emu.mem_write(timeptr,struct.pack('<q',1792726800000));w(stack,stop);w(stack+4,timeptr)
    tmfunc=u32(0x22448d4)
    if not BASE<=tmfunc<BASE+len(DATA):emu.mem_map(tmfunc&~4095,4096)
    calls=[]
    def hook(uc,address,size,user):
        if address==stop:uc.emu_stop()
        elif address==tmfunc:
            sp=uc.reg_read(UC_X86_REG_ESP)
            # Host adapter for CRT calendar conversion only; noon avoids popup branches.
            uc.mem_write(r(sp+4),struct.pack('<9i',0,0,12,23,9,126,5,295,0))
            uc.reg_write(UC_X86_REG_ESP,sp+4);uc.reg_write(UC_X86_REG_EAX,0);uc.reg_write(UC_X86_REG_EIP,r(sp))
        elif address==0x816430:
            calls.append('create_activity_manager')
            sp=uc.reg_read(UC_X86_REG_ESP);uc.reg_write(UC_X86_REG_ESP,sp+4);uc.reg_write(UC_X86_REG_EIP,r(sp))
    emu.hook_add(UC_HOOK_CODE,hook)
    emu.reg_write(UC_X86_REG_ECX,obj);emu.reg_write(UC_X86_REG_ESP,stack)
    emu.emu_start(0x81b3e0,stop,count=10000)
    assert emu.reg_read(UC_X86_REG_EIP)==stop
    assert bytes(emu.mem_read(world,len(sentinel)))==sentinel
    assert bytes(emu.mem_read(scene,len(sentinel)))==sentinel
    assert struct.unpack('<q',emu.mem_read(obj+0x28,8))[0]==1792726800000
    return {'SGameTime_scene_present':scene_present,'world_and_scene_unchanged':True,
            'activity_callback':calls,'network_time_written':True,'scope':'noon, optional managers absent'}


def draw_parameter_defaults(world_time, keyframes=False):
    """Execute the real per-draw parameter calculator with no map keyframes."""
    emu=Uc(UC_ARCH_X86,UC_MODE_32)
    emu.mem_map(BASE,(len(DATA)+4095)&~4095);emu.mem_write(BASE,DATA)
    emu.mem_map(0x5000000,0x100000)
    world,engine,contextvt,enginevt,renderer,rendervt,config,mapobj,stack,stop=(
        0x5001000,0x5002000,0x5003000,0x5004000,0x5005000,0x5006000,0x5007000,0x5008000,0x5080000,0x500f000)
    def w(addr,value):emu.mem_write(addr,struct.pack('<I',value))
    def r(addr):return struct.unpack('<I',emu.mem_read(addr,4))[0]
    w(world+8,engine);w(world+0x298,mapobj);w(world+0x27c,world_time)
    w(engine,enginevt);w(engine+4,contextvt);w(enginevt+0x5c,0x500f100)
    w(contextvt+0x34,0x500f200);w(renderer,rendervt)
    w(rendervt+0x118,0x500f300);w(rendervt+0x11c,0x500f400)
    emu.mem_write(config+0x14,b'\1\0');w(stack,stop);w(stack+4,0)
    if keyframes:
        head,a,b=0x5009000,0x5009100,0x5009200
        w(mapobj+0xd0,head);w(mapobj+0xd4,2)
        for addr,links in ((head,(a,a,b)),(a,(head,head,b)),(b,(head,a,head))):
            emu.mem_write(addr,struct.pack('<III',*links))
        emu.mem_write(head+0x31,b'\1')
        w(a+0xc,0);w(b+0xc,3600000)
        emu.mem_write(a+0x10,struct.pack('<8f',0,.1,.2,.3,1,.5,0,0))
        emu.mem_write(b+0x10,struct.pack('<8f',.5,.6,.7,.8,1,.9,0,0))
    captured=[]
    def ret(uc,count,value=0):
        sp=uc.reg_read(UC_X86_REG_ESP);dest=r(sp)
        uc.reg_write(UC_X86_REG_ESP,sp+4+count);uc.reg_write(UC_X86_REG_EAX,value);uc.reg_write(UC_X86_REG_EIP,dest)
    def hook(uc,address,size,user):
        if address==stop:uc.emu_stop()
        elif address==0x500f100:ret(uc,4,renderer)
        elif address==0x500f200:ret(uc,0,config)
        elif address==0x500f300:ret(uc,4)
        elif address==0x500f400:
            sp=uc.reg_read(UC_X86_REG_ESP);ptr=r(sp+8)
            captured.append(struct.unpack('<8f',uc.mem_read(ptr,32)));ret(uc,8)
    emu.hook_add(UC_HOOK_CODE,hook)
    emu.reg_write(UC_X86_REG_EAX,world);emu.reg_write(UC_X86_REG_ESP,stack)
    emu.emu_start(0x604b80,stop,count=10000)
    assert emu.reg_read(UC_X86_REG_EIP)==stop
    if keyframes:
        ratio=world_time/3600000 if world_time<=3600000 else (7200000-world_time)/3600000
        expected=(.5*ratio,.1+.5*ratio,.2+.5*ratio,.3+.5*ratio,1,.5+.4*ratio,-10000,-10000)
        assert len(captured)==1 and all(abs(a-b)<1e-5 for a,b in zip(captured[0],expected)),captured
    else:assert captured==[(0.,0.,0.,0.,1.,0.,-10000.,-10000.)],captured
    return {'per_draw_parameter_time':world_time,'no_keyframes':not keyframes,
            'renderer_11c_parameters':captured[0], 'computed_on_this_draw':True}


if __name__=='__main__':
    results=[run(True,0),run(True,9999),run(False,1234),game_time(False),game_time(True)]
    results += [draw_parameter_defaults(t) for t in (0,755001,6745001)]
    results += [draw_parameter_defaults(t, True) for t in (0,1800000,5400000)]
    target=Path(__file__).parent/'evidence/world-time-material-native.json'
    target.write_text(json.dumps(results,indent=2),encoding='utf-8')
    print(json.dumps(results,indent=2))
