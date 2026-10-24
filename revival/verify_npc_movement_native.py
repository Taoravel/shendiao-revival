"""Original NPC movement codec and original handler-to-object assignment."""
import hashlib
import struct
from native_gameplay_probe import probe
from native_inspect import BASE,DATA
from npc_lifecycle import npc_move_to,NPC_MOVE_TO
from inspect_client import OUT,write_json


def original_consumer(payload):
    from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
    from unicorn.x86_const import UC_X86_REG_ESP,UC_X86_REG_ECX,UC_X86_REG_EIP,UC_X86_REG_EAX
    _,raw=probe(0xdaba20,0xe509c0,0xdabaf0,payload=payload)
    uc=Uc(UC_ARCH_X86,UC_MODE_32)
    uc.mem_map(0,4096);uc.mem_map(BASE,(len(DATA)+4095)&~4095);uc.mem_write(BASE,DATA)
    uc.mem_map(0x5000000,0x200000)
    msg,npc,manager,vtable,stack,stop=0x5001000,0x5002000,0x5003000,0x5004000,0x5100000,0x500f000
    def write(a,*values):uc.mem_write(a,struct.pack('<'+'I'*len(values),*values))
    def read(a):return struct.unpack('<I',uc.mem_read(a,4))[0]
    uc.mem_write(msg,raw);write(npc,vtable);write(vtable+0xc8,stop)
    write(0x2944564,manager);write(0x294acd4,0);write(stack,stop,0,0)
    seen=[];reached=[]
    def ret(count=0,value=None):
        sp=uc.reg_read(UC_X86_REG_ESP);dest=read(sp)
        uc.reg_write(UC_X86_REG_ESP,sp+4+count);uc.reg_write(UC_X86_REG_EIP,dest)
        if value is not None:uc.reg_write(UC_X86_REG_EAX,value)
    def hook(emu,address,size,user):
        if address==stop:emu.emu_stop()
        elif address==0x806de0:ret()  # diagnostic logging only, cdecl
        elif address==0x11d5260:
            sp=emu.reg_read(UC_X86_REG_ESP)
            seen.append(read(sp+4)|(read(sp+8)<<32));ret(8,npc)
        elif address==0x1201366:
            reached.append(True);emu.emu_stop()  # native fields written, before rendering virtual
    uc.hook_add(UC_HOOK_CODE,hook)
    uc.reg_write(UC_X86_REG_ESP,stack);uc.reg_write(UC_X86_REG_ECX,msg)
    uc.emu_start(0x11d8170,stop,count=20000)
    result=struct.unpack('<5i',uc.mem_read(npc+0x10c,20)) if reached else None
    assert uc.reg_read(UC_X86_REG_EIP) in (stop,0x1201366)
    return seen,result


def main():
    passed=[]
    for key,duration,origin,target in ((1,1,(1,2),(3,4)),
            (0x123456789,1000,(1680,5311),(1700,5343)),
            (0x123456789abcdef,2147483647,(32766,32765),(32767,32767))):
        kind,expected=npc_move_to(key,duration,origin,target);assert kind==NPC_MOVE_TO
        actual,raw=probe(0xdaba20,0xe509c0,0xdabaf0,{8:struct.pack('<q',key),
            0x10:struct.pack('<i',duration),0x18:struct.pack('<2h',*origin),0x20:struct.pack('<2h',*target)})
        assert actual==expected and struct.unpack_from('<I',raw,4)[0]==NPC_MOVE_TO
        seen,result=original_consumer(expected)
        assert seen==[key] and result==(*target,*origin,duration)
        passed.append([key,duration,origin,target])
    for duration,origin in ((0,(1,2)),(-1,(1,2)),(1000,(0,0))):
        seen,result=original_consumer(struct.pack('>qi4h',1,duration,*origin,3,4))
        assert seen==[1] and result is None
        try:npc_move_to(1,duration,origin,(3,4))
        except ValueError:pass
        else:raise AssertionError('Server emitted a native-ignored NPC move')
    divisor=struct.unpack_from('<d',DATA,0x2473fa8-BASE)[0];assert divisor==1000
    report={'passed':['3 original SNPCMoveTo high-key/duration/coordinate codec round trips',
        'original handler resolves actual64bit NPC key and assigns destination/source/duration in correct order',
        'original zero/negative duration and origin0,0 are ignored; server refuses them'],
        'protocol':'0xc0fd2','constructor':'0xdaba20','marshal':'0xe509c0','unmarshal':'0xdabaf0',
        'consumer_executed':'0x11d8170->0x1201320..0x1201366',
        'consumer_adapters':'logging no-op and owned-NPC key lookup only; original field assignment executes',
        'animation_duration_divisor':divisor,'cases':passed,'native_image_sha256':hashlib.sha256(DATA).hexdigest(),
        'authoritative_movement_scheduler_implemented':False,'native_gui_verified':False}
    write_json(OUT/'evidence/npc-movement-native.json',report);print(report['passed'])


if __name__=='__main__':main()
