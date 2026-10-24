"""Original pixel-shader selection branches, replayed offline without D3D/UI."""
import json
from pathlib import Path
import struct
from native_inspect import DATA, BASE
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_EDI,UC_X86_REG_ESI,UC_X86_REG_ESP,UC_X86_REG_EIP


def emulator():
    e=Uc(UC_ARCH_X86,UC_MODE_32)
    e.mem_map(BASE,(len(DATA)+4095)&~4095);e.mem_write(BASE,DATA)
    e.mem_map(0x5000000,0x100000)
    return e


def capability(version):
    e=emulator();obj,stack,stop=0x5001000,0x5080000,0x500f000
    e.mem_write(stack,struct.pack('<II',stop,version))
    e.reg_write(UC_X86_REG_ECX,obj);e.reg_write(UC_X86_REG_ESP,stack)
    e.emu_start(0x711770,stop,count=100)
    actual=bytes(e.mem_read(obj+4,8));expected=bytes([version>=0xffff0300])*8
    assert actual==expected
    return {'shader_version_token':hex(version),'backend_available_bytes':list(actual),
            'meaning':'static minimum pixel-shader-3.0 capability, not asynchronous compilation completion'}


def program_defaults():
    e=emulator();obj,params,stack,stop=0x5001000,0x5002000,0x5080000,0x500f000
    e.mem_write(stack,struct.pack('<I',stop));e.reg_write(UC_X86_REG_EAX,obj)
    e.reg_write(UC_X86_REG_ESP,stack);e.emu_start(0x711c50,stop,count=300)
    initial=struct.unpack('<8f',e.mem_read(obj+0x4c,32))
    assert abs(initial[0]-.2)<1e-6 and initial[4:]==(1.,0.,500.,400.),initial
    supplied=(.25,.5,.75,1.,.125,.375,.625,.875)
    e.mem_write(params,struct.pack('<8f',*supplied));e.mem_write(stack,struct.pack('<II',stop,params))
    e.reg_write(UC_X86_REG_ECX,obj);e.reg_write(UC_X86_REG_ESP,stack)
    e.emu_start(0x7117b0,stop,count=300)
    actual=struct.unpack('<8f',e.mem_read(obj+0x4c,32));assert actual==supplied
    return {'program_constructor':hex(0x711c50),'initial_8float_parameters':initial,
            'parameter_setter':hex(0x7117b0),'all_8_parameters_copied':True}


def select(available=True, bind_result=0, selected=-1):
    e=emulator();selector,program,device,pvt,dvt,stack,stop=(
        0x5001000,0x5002000,0x5003000,0x5004000,0x5005000,0x5080000,0x500f000)
    def w(a,v):e.mem_write(a,struct.pack('<I',v&0xffffffff))
    def r(a):return struct.unpack('<I',e.mem_read(a,4))[0]
    w(selector+4,device);w(selector+8,program);w(selector+0x1c,selected);w(selector+0x20,-1)
    w(selector+0x34,0);w(0x29235d4,0)
    w(program,pvt);e.mem_write(program+4,bytes([available]));w(program+0xc,0x12345678)
    w(pvt+0xc,0x500f100);w(device,dvt);w(dvt+0x1ac,0x500f200);w(stack,stop)
    calls=[]
    def ret(uc,n,v=0):
        sp=uc.reg_read(UC_X86_REG_ESP);dest=r(sp)
        uc.reg_write(UC_X86_REG_ESP,sp+4+n);uc.reg_write(UC_X86_REG_EAX,v&0xffffffff);uc.reg_write(UC_X86_REG_EIP,dest)
    def hook(uc,a,size,user):
        if a==stop:uc.emu_stop()
        elif a==0x500f100:
            calls.append('upload_program_parameters');ret(uc,4)
        elif a==0x500f200:
            sp=uc.reg_read(UC_X86_REG_ESP)
            calls.append({'bind_shader_handle':hex(r(sp+8))});ret(uc,8,bind_result)
    e.hook_add(UC_HOOK_CODE,hook);e.reg_write(UC_X86_REG_ESI,selector)
    e.reg_write(UC_X86_REG_EDI,0);e.reg_write(UC_X86_REG_ESP,stack)
    e.emu_start(0x6e29c0,stop,count=300)
    assert e.reg_read(UC_X86_REG_EIP)==stop
    actual=bool(e.reg_read(UC_X86_REG_EAX)&255)
    expected=selected==0 or (available and bind_result>=0)
    assert actual==expected
    if not available or selected==0:assert calls==[]
    return {'available':available,'prior_selected':selected,'D3D_bind_result':hex(bind_result&0xffffffff),
            'native_return':actual,'native_selected_after':hex(r(selector+0x1c)),'calls':calls}


def shader_neutral_counterfactuals():
    # Exact neutral reduction of original built-in HLSL. At far-away centre,
    # p0..3=p5=0, p4=1 removes colour adjustment; remaining operation is the
    # backend snippet multiplying texel by vertex COLOR0. This is source-math
    # verification, not execution on the user's GPU.
    texture=(.4,.6,.8,1.)
    cases=[]
    for backend,vertex in ((0,(1.,1.,1.,1.)),(0,(0.,0.,0.,1.)),(1,(0.,0.,0.,1.))):
        colour=(1.,1.,1.,vertex[3]) if backend==1 else vertex
        result=tuple(a*b for a,b in zip(texture,colour))
        expected=(0.,0.,0.,1.) if backend==0 and vertex[0]==0 else texture
        assert result==expected
        cases.append({'backend':backend,'neutral_shader_parameters':[0,0,0,0,1,0,-10000,-10000],
                      'texture_fixture':texture,'vertex_COLOR0':vertex,'output':result,
                      'method':'exact neutral reduction of extracted original HLSL; not GPU execution'})
    return cases


if __name__=='__main__':
    results=[capability(v) for v in (0xffff0200,0xffff0300)]
    results.append(program_defaults())
    results += [select(False),select(True),select(True,-1),select(False,selected=0)]
    results += shader_neutral_counterfactuals()
    target=Path(__file__).parent/'evidence/world-pixel-shader-native.json'
    target.write_text(json.dumps(results,indent=2),encoding='utf-8')
    print(json.dumps(results,indent=2))
