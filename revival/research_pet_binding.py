"""Original decoded Pet flag conversion and binding query, offline only."""
import struct

from native_gameplay_probe import probe


def observe_binding(uc,pet_bean):
    from unicorn.x86_const import (UC_X86_REG_EAX,UC_X86_REG_EDI,
        UC_X86_REG_ESP,UC_X86_REG_EIP)
    def w(address,*values):uc.mem_write(address,struct.pack('<'+'I'*len(values),*values))
    stack,manager,head,node,stop=0x5108000,0x5300000,0x5301000,0x5302000,0x500f000
    pet=node+8
    key=struct.unpack('<I',uc.mem_read(pet_bean+8,4))[0]
    w(0x2944550,manager);w(manager+0x27c,head)
    w(head,node,node);w(node,head,head);w(pet,key)
    uc.mem_write(stack+0x3c,bytes(uc.mem_read(pet_bean,0x140)))
    uc.reg_write(UC_X86_REG_ESP,stack);uc.reg_write(UC_X86_REG_EDI,pet)
    uc.emu_start(0x10c2bb5,0x10c2bf1,count=1000)
    assert uc.reg_read(UC_X86_REG_EIP)==0x10c2bf1
    raw=uc.mem_read(pet+0x6a,1)[0]
    w(stack,stop,key);uc.reg_write(UC_X86_REG_ESP,stack)
    uc.emu_start(0x11308c0,stop,count=1000)
    assert uc.reg_read(UC_X86_REG_EIP)==stop
    return raw,bool(uc.reg_read(UC_X86_REG_EAX)&255)


def native_record_binding(payload):
    result=[]
    probe(0xf89ba0,0xf5df70,0xf5f1f0,payload=payload,
          observer=lambda uc,target:result.append(observe_binding(uc,target)))
    return result[0]


def native_column_bindings(payload):
    result=[]
    def observe(uc,target):
        def r(a):return struct.unpack('<I',uc.mem_read(a,4))[0]
        assert r(target+8)==1
        begin,end=r(target+0x10),r(target+0x14)
        assert (end-begin)%0x140==0
        pets=tuple((r(p+8),p) for p in range(begin,end,0x140))
        result.extend((key,*observe_binding(uc,p)) for key,p in pets)
    probe(0xf20220,0xf20aa0,0xf20b60,payload=payload,observer=observe)
    return tuple(result)
