"""Isolated original CSubmit2Npc marshal evidence. No process/server access."""
import json
import struct

from native_inspect import BASE, DATA


def native_submit_body():
    from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
    from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_ESP, UC_X86_REG_EIP
    uc = Uc(UC_ARCH_X86, UC_MODE_32)
    uc.mem_map(0, 0x1000)
    uc.mem_map(BASE, (len(DATA)+4095)&~4095)
    uc.mem_write(BASE, DATA)
    uc.mem_map(0x5000000, 0x20000)
    obj, stream, buf, units, stack, stop = 0x5001000,0x5002000,0x5003000,0x5005000,0x5010000,0x500f000
    def w(addr, *values):uc.mem_write(addr, struct.pack('<'+'I'*len(values),*values))
    def read(addr):return struct.unpack('<I',uc.mem_read(addr,4))[0]
    w(obj,0x2284a94,0xc2340,101101)
    w(obj+0x10,0x55667788,0x11223344,1)
    w(obj+0x20,units,units+12,units+12)
    w(units,0x2284ab8,12345,3)
    w(stream,0x224c100,buf,0)
    w(buf-12,4096,0,1)
    w(stack,stop,stream)
    visited=set()
    def hook(emu,addr,size,user):
        visited.add(addr)
        if addr==stop:
            emu.emu_stop();return
        if addr not in (0x19191c2,0x1919184):return
        sp=emu.reg_read(UC_X86_REG_ESP)
        if addr==0x19191c2:
            dst,src,count=read(sp+4),read(sp+8),read(sp+12)
            if count:emu.mem_write(dst,bytes(emu.mem_read(src,count)))
            emu.reg_write(UC_X86_REG_EAX,dst)
        emu.reg_write(UC_X86_REG_EIP,read(sp));emu.reg_write(UC_X86_REG_ESP,sp+4)
    uc.hook_add(UC_HOOK_CODE,hook)
    uc.reg_write(UC_X86_REG_ECX,obj);uc.reg_write(UC_X86_REG_ESP,stack)
    uc.emu_start(0xf16270,stop,count=100000)
    body=bytes(uc.mem_read(buf,read(buf-8)))
    expected=struct.pack('>iQi',101101,0x1122334455667788,1)+b'\x01'+struct.pack('>ii',12345,3)
    assert uc.reg_read(UC_X86_REG_EIP)==stop and body==expected
    assert 0xf16160 in visited and 0xf16440 in visited
    return dict(protocol='CSubmit2Npc',type='0xc2340',marshal='0xf16270',
                unit_marshal='0xf16160',vector_marshal='0xf16440',
                body_hex=body.hex(),length=len(body),original_methods_visited=True,
                adapters=['CRT memcpy only','security-cookie return only'],
                scope='wire probe; no native UI, inventory rules, or game server executed')


if __name__=='__main__':print(json.dumps(native_submit_body(),indent=2))
