"""Original nonempty pet skill list, refresh copy and learned-icon loop."""
import struct

from native_gameplay_probe import probe
from native_inspect import u32
from inspect_client import OUT, write_json
from wire import compact


def observe_skills(uc, message, *, inner_offset=8):
    """Continue the original decoded message at actual consumer slices.

    The final icon observer replaces GUI work only. Original list assignment,
    checked iterators, expiry lookup and UI list traversal execute.
    """
    from unicorn import UC_HOOK_CODE
    from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX,
        UC_X86_REG_EDI, UC_X86_REG_ESI, UC_X86_REG_EBP, UC_X86_REG_ESP, UC_X86_REG_EIP)
    def read(addr):
        return struct.unpack('<I', uc.mem_read(addr,4))[0]
    def w(addr, *values):
        uc.mem_write(addr,struct.pack('<'+'I'*len(values),*values))
    pet, head, panel, tree, stack = 0x5301000, 0x5302000, 0x5303000, 0x5304000, 0x5108000
    w(pet+0x44,head,0)
    w(head,head,head)
    w(pet+0x50,tree,0)
    w(tree,tree,tree,tree)
    uc.mem_write(tree+0x21,b'\1')
    uc.mem_write(stack,bytes(0x200))
    uc.reg_write(UC_X86_REG_ESP,stack)
    uc.reg_write(UC_X86_REG_ESI,message+inner_offset-8)
    uc.reg_write(UC_X86_REG_EBX,pet)
    uc.emu_start(0x11353c9,0x1135429,count=50000)
    assert uc.reg_read(UC_X86_REG_EIP)==0x1135429
    copied=[]
    node=read(head)
    while node!=head:
        assert len(copied)<32
        copied.append(read(node+8))
        node=read(node)
    assert len(copied)==read(pet+0x48)
    # Read the original client clock used by the icon loop. Timed probes first
    # synchronize it through the actual SGameTime decoder/process.
    w(stack,0x500f000)
    uc.reg_write(UC_X86_REG_ESP,stack)
    uc.emu_start(0x813850,0x500f000,count=100)
    from unicorn.x86_const import UC_X86_REG_EDX
    clock_low,clock_high=uc.reg_read(UC_X86_REG_EAX),uc.reg_read(UC_X86_REG_EDX)
    captured=[]
    def ret(count=0,value=0):
        sp=uc.reg_read(UC_X86_REG_ESP)
        dest=read(sp)
        uc.reg_write(UC_X86_REG_EAX,value)
        uc.reg_write(UC_X86_REG_ESP,sp+4+count)
        uc.reg_write(UC_X86_REG_EIP,dest)
    def gui_hook(uc, address, size, user):
        if address==0x11b0c80:
            ret(value=0x5306000)
        elif address==0x12d8120:
            sp=uc.reg_read(UC_X86_REG_ESP)
            captured.append(tuple(read(sp+i) for i in (4,8,12,16)))
            ret(16)
    handle=uc.hook_add(UC_HOOK_CODE,gui_hook)
    w(panel+0x158,pet)
    w(panel+0xc8,*range(0x60000001,0x6000000d))
    uc.mem_write(stack,bytes(0x200))
    for offset,value in ((0x14,panel+0xc8),(0x1c,0),(0x20,pet+0x40),(0x24,12),
                         (0x28,clock_low),(0x2c,clock_high),
                         (0x34,read(head)),(0x44,head)):
        w(stack+offset,value)
    uc.reg_write(UC_X86_REG_ESP,stack)
    uc.reg_write(UC_X86_REG_EDI,panel)
    uc.reg_write(UC_X86_REG_EBX,pet+0x40)
    uc.reg_write(UC_X86_REG_ESI,read(head))
    uc.reg_write(UC_X86_REG_EBP,0)
    uc.emu_start(0x140dfb2,0x140e0ed,count=50000)
    assert uc.reg_read(UC_X86_REG_EIP)==0x140e0ed
    uc.hook_del(handle)
    return tuple(copied),tuple(captured)


def native_record_skills(payload):
    result=[]
    probe(0xf9d7b0,0xf9d840,0xf9d880,payload=payload,
          observer=lambda uc,message:result.append(observe_skills(uc,message)))
    return result[0]


def main():
    obj=0x5001000
    head,first,second=obj+0x300,obj+0x320,obj+0x340
    fields={4:struct.pack('<i',500001),8:struct.pack('<i',7),
        0xbc:struct.pack('<II',head,2),0x300:struct.pack('<II',first,second),
        0x320:struct.pack('<III',second,head,200091),
        0x340:struct.pack('<III',head,first,200061)}
    output,_=probe(0xf89ba0,0xf5df70,0xf5f1f0,fields)
    default,_=probe(0xf89ba0,0xf5df70,0xf5f1f0,
                    {4:struct.pack('<i',500001),8:struct.pack('<i',7)})
    expected=default[:138]+compact(2)+struct.pack('>ii',200091,200061)+default[139:]
    assert output==expected
    copied,icons=native_record_skills(output)
    assert copied==(200091,200061)
    assert icons==((0x60000001,200091,0,0),(0x60000002,200061,0,0))
    result={'wire':'Pet bean+b8 list<i32>: compact count and ordered BE32 IDs; default empty count at wire138 for empty name',
        'source':'original ctorf89ba0, marshal f5df70, decoderf5f1f0; message ctorf9d7b0/decoderf9d880',
        'consumer':'original refresh11353c9..1135429 learned-list/expiry assignment; original learned-icon loop140dfb2..140e0ed',
        'skills':copied,'native_icon_arguments':icons,
        'adapter':'original standard runtime import adapters; original expiry tree copy and clock getter; terminal GUI icon observer only',
        'skill_levels':'no separate learned level in this list; each exact original skill ID selects its own skill definition',
        'learn_request_layout':'CPetLearnSkillByBook c07ff: six BE32 fields, first2 positive and last4 >=-1; canonical original drag branch142d820 fills last4=-1',
        'native_gui_tested':False,'battle_effects_tested':False}
    write_json(OUT/'evidence/pet-skills-native.json',result)
    print('PASS original learned skill list and icon arguments:',copied)


if __name__=='__main__':main()
