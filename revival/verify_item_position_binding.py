"""Original item copy, bag-position consumer and binding/give branch.

Checks semantics which an original serializer roundtrip alone cannot prove.
"""
import struct
from inventory import item_record
from native_gameplay_probe import probe
from native_inspect import BASE,DATA
from inspect_client import OUT,write_json


def native_item_view(decoded):
    from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
    from unicorn.x86_const import UC_X86_REG_ESP,UC_X86_REG_ECX,UC_X86_REG_EBX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EAX,UC_X86_REG_EIP
    emu=Uc(UC_ARCH_X86,UC_MODE_32)
    emu.mem_map(0,0x1000);emu.mem_map(BASE,(len(DATA)+4095)&~4095);emu.mem_write(BASE,DATA)
    emu.mem_map(0x5000000,0x200000)
    obj,bean,wrapper,stack,stop=0x5001000,0x5002000,0x5003000,0x5100000,0x500f000
    def w(a,*v):emu.mem_write(a,struct.pack('<'+'I'*len(v),*v))
    def read(a):return struct.unpack('<I',emu.mem_read(a,4))[0]
    emu.mem_write(bean,decoded);w(wrapper,obj)
    def hook(uc,address,size,user):
        if address in (stop,0x10817cc,0x1683766,0x1683728):uc.emu_stop()
    emu.hook_add(UC_HOOK_CODE,hook)
    w(stack,stop,bean)
    emu.reg_write(UC_X86_REG_ESP,stack);emu.reg_write(UC_X86_REG_ECX,obj+8)
    emu.emu_start(0x81a760,stop,count=10000)
    assert emu.reg_read(UC_X86_REG_EIP)==stop
    # SGetBagInfo consumer 10817bc..cc copies bean+10 to display position+48.
    emu.reg_write(UC_X86_REG_ESI,wrapper);emu.reg_write(UC_X86_REG_EBX,bean);emu.reg_write(UC_X86_REG_EDI,1)
    emu.emu_start(0x10817bc,0x10817cc,count=10000)
    assert emu.reg_read(UC_X86_REG_EIP)==0x10817cc
    position=read(obj+0x48)
    w(stack,stop);emu.reg_write(UC_X86_REG_ESP,stack);emu.reg_write(UC_X86_REG_ECX,wrapper)
    emu.emu_start(0x1072e70,stop,count=10000)
    binding=emu.reg_read(UC_X86_REG_EAX)
    # The real give branch uses the same getter. Stop before looking up the
    # message140857 ('bound items cannot be given') or entering unrelated UI.
    emu.reg_write(UC_X86_REG_ESP,stack);emu.reg_write(UC_X86_REG_EBX,wrapper)
    emu.emu_start(0x168375b,0x1683766,count=10000)
    give_rejected=emu.reg_read(UC_X86_REG_EIP)==0x1683766
    assert give_rejected==bool(binding)
    return position,binding,give_rejected


def main():
    for slot,binding in ((0,0),(5,0),(0,1),(5,1),(39,0),(39,1)):
        payload=item_record({'template_id':31000,'slot':slot,'id':7,'quantity':3,'binding':binding})
        _,raw=probe(0x8184f0,0x822040,0x81a590,payload=payload)
        actual=native_item_view(raw)
        assert actual==(slot,binding,bool(binding)),(slot,binding,actual)
        original,_=probe(0x8184f0,0x822040,0x81a590,
            {4:struct.pack('<i',31000),8:struct.pack('<i',binding),12:struct.pack('<i',7),
             16:struct.pack('<i',slot),32:struct.pack('<i',3)})
        assert payload==original
    report={'passed':['native copy and bag-position consumer preserve nonzero slots',
        'native binding getter independent of odd/even slot',
        'native give branch refuses bound items only','production bytes match independently populated native record'],
        'correct_wire_order':['template_id','flags','instance_key','position'],
        'binding_mask':1,'native_ui_tested':False,
        'consumer_functions':['0x81a760','0x10817bc..0x10817cc','0x1072e70','0x168375b..0x1683766']}
    write_json(OUT/'evidence/item-position-binding-verification.json',report)
    print('PASS:',', '.join(report['passed']))


if __name__=='__main__':main()
