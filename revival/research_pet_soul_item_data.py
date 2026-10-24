"""Original orb object parser/converter, with explicit grade/config adapters.

This verifies field placement and display markers, not grade calculation,
whole item factory, gameplay authority, observers or GUI. The original
constructors, four-field decoder, assignment branches and returns execute.
"""
import struct
from native_inspect import DATA,BASE


def native_marker(mode,value):
    if mode not in ('bag','worn') or type(value) is not int or not -0x80000000<=value<=0x7fffffff:
        raise ValueError('Known native parser fixture required')
    from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
    from unicorn.x86_const import UC_X86_REG_ESP,UC_X86_REG_EAX,UC_X86_REG_EIP,UC_X86_REG_ECX
    uc=Uc(UC_ARCH_X86,UC_MODE_32)
    uc.mem_map(0,0x1000);uc.mem_map(BASE,(len(DATA)+4095)&~4095);uc.mem_write(BASE,DATA)
    uc.mem_map(0x5000000,0x400000)
    obj,bean,stream,buf=0x5001000,0x5002000,0x5003000,0x5004000
    cache,vtbl,row=0x5005000,0x5006000,0x5007000
    stack,stop,lookup=0x5100000,0x500f000,0x500f100
    def w(address,*values):uc.mem_write(address,struct.pack('<'+'I'*len(values),*[v&0xffffffff for v in values]))
    def rd(address):return struct.unpack('<I',uc.mem_read(address,4))[0]
    def ret(result,count=0):
        sp=uc.reg_read(UC_X86_REG_ESP);dest=rd(sp)
        uc.reg_write(UC_X86_REG_EAX,result);uc.reg_write(UC_X86_REG_ESP,sp+4+count);uc.reg_write(UC_X86_REG_EIP,dest)
    w(cache,vtbl);w(vtbl+8,lookup);w(row,31277,2)
    def hook(uc,address,size,user):
        if address==0x1078b30:ret(2)  # Independently certified XP, isolated here.
        elif address==0x89e380:ret(cache)
        elif address==lookup:ret(row,4)  # Exact original31277 soulType2.
    uc.hook_add(UC_HOOK_CODE,hook)
    if mode=='worn':
        w(bean,0x227b308,31277,120,10002,204,205,value);w(stack,stop,bean)
        uc.reg_write(UC_X86_REG_ECX,obj);uc.reg_write(UC_X86_REG_ESP,stack)
        uc.emu_start(0x1402f90,stop,count=100000)
        assert struct.unpack('<i',uc.mem_read(bean+24,4))[0]==value
    else:
        w(stack,stop);uc.reg_write(UC_X86_REG_ECX,obj);uc.reg_write(UC_X86_REG_ESP,stack)
        uc.emu_start(0x10743c0,stop,count=100000)
        w(obj+12,31277);w(obj+16,value)
        w(stream,0x224c100,buf,0);w(buf-12,0x7000,16,1)
        uc.mem_write(buf,struct.pack('>4i',120,10002,205,204));w(stack,stop,stream)
        uc.reg_write(UC_X86_REG_ECX,obj);uc.reg_write(UC_X86_REG_ESP,stack)
        uc.emu_start(0x107a020,stop,count=100000)
        assert rd(stream+8)==16
    assert uc.reg_read(UC_X86_REG_EIP)==stop and rd(obj+12)==31277 and rd(obj+0x58)==2
    assert uc.mem_read(obj+0x5c,1)[0]==1
    assert struct.unpack('<4i',uc.mem_read(obj+0x64,16))==(120,10002,205,204)
    return uc.mem_read(obj+0x5d,1)[0]
