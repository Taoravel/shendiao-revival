"""Offline original config defaults, draw dispatch, and RT alpha conversion."""
import json
import struct
from pathlib import Path
from contextlib import redirect_stdout
from native_inspect import BASE, DATA, disasm
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_EBX, UC_X86_REG_ESP, UC_X86_REG_EIP

OUT=Path(__file__).parent/'evidence'


def machine():
    e=Uc(UC_ARCH_X86,UC_MODE_32)
    e.mem_map(BASE,(len(DATA)+4095)&~4095);e.mem_write(BASE,DATA)
    e.mem_map(0x5000000,0x100000)
    return e


def defaults():
    e=machine();obj,stack,stop=0x5001000,0x5080000,0x500f000
    e.mem_write(stack,struct.pack('<I',stop));e.reg_write(UC_X86_REG_EAX,obj)
    e.reg_write(UC_X86_REG_ESP,stack);e.emu_start(0x5ba8b0,stop,count=300)
    mode=struct.unpack('<I',e.mem_read(obj+0x48,4))[0]
    alpha,scale=struct.unpack('<f',e.mem_read(obj+0x18,4))[0],struct.unpack('<f',e.mem_read(obj+0x10,4))[0]
    assert mode==1 and abs(alpha-.6)<1e-6 and scale==1.5
    return {'original_defaults':True,'config_draw_mode_48':mode,'RT_alpha_18':alpha,'coordinate_scale_10':scale}


def dispatch(mode):
    e=machine();obj,stack=0x5001000,0x5080000
    e.mem_write(obj+0x48,struct.pack('<I',mode));e.mem_write(stack+0x60,struct.pack('<I',obj))
    e.reg_write(UC_X86_REG_EBX,0);e.reg_write(UC_X86_REG_ESP,stack)
    targets={0x6067db:'direct_mode0',0x6067c2:'direct_mode1',0x6066a4:'RT_mode2',0x6067e9:'no_draw_case'}
    outcome=[]
    def hook(uc,a,size,user):
        if a in targets:outcome.append(targets[a]);uc.emu_stop()
    e.hook_add(UC_HOOK_CODE,hook);e.emu_start(0x606683,0x6067f0,count=50)
    expected={0:'direct_mode0',1:'direct_mode1',2:'RT_mode2',3:'no_draw_case'}[mode]
    assert outcome==[expected]
    return {'config_draw_mode_48':mode,'native_dispatch':outcome[0]}


def rt_alpha(alpha):
    e=machine();obj,stack=0x5001000,0x5080000
    e.mem_write(obj+0x18,struct.pack('<f',alpha));e.reg_write(UC_X86_REG_ECX,obj)
    e.reg_write(UC_X86_REG_ESP,stack);e.emu_start(0x606745,0x606766,count=20)
    argb=struct.unpack('<I',e.mem_read(stack+0x64,4))[0]
    expected=0x00ffffff | (int(alpha*255)&255)<<24
    assert argb==expected,(alpha,hex(argb),hex(expected))
    return {'RT_alpha_18':alpha,'original_ARGB':hex(argb),'method':'original x86 conversion instructions'}


if __name__=='__main__':
    results=[defaults()]+[dispatch(m) for m in range(4)]+[rt_alpha(a) for a in (0.,.6,1.)]
    (OUT/'world-render-config-native.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    with (OUT/'world-render-config-native-disassembly.txt').open('w',encoding='utf-8') as f:
        with redirect_stdout(f):
            for label,a,n in (('config allocation/default initialization',0x5a760c,105),
                              ('default implementation',0x5ba8b0,210),
                              ('context config getter',0x5a6300,4),
                              ('draw dispatch and RT composite',0x606630,459)):
                print('\n',label);disasm(a,n)
    print(json.dumps(results,indent=2))
