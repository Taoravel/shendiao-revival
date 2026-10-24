"""Original world attribute map codec and generic HP/MP assignment branch."""
import struct
from item_effects import VitalState
from item_effect_protocol import role_resource_refresh
from native_gameplay_probe import probe
from native_inspect import BASE,DATA
from inspect_client import OUT,write_json


def native_assignment(key,value):
    """Execute the original ordinary attr branch, stop before GUI observers.

    Host adapter only supplies an owned attribute-map slot. Original x87 float
    conversion and final overwrite execute unchanged; this is not full UI QA.
    """
    from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
    from unicorn.x86_const import UC_X86_REG_ESP,UC_X86_REG_EDI,UC_X86_REG_ESI,UC_X86_REG_EIP,UC_X86_REG_EAX,UC_X86_REG_ECX
    emu=Uc(UC_ARCH_X86,UC_MODE_32)
    emu.mem_map(0,0x1000);emu.mem_map(BASE,(len(DATA)+4095)&~4095);emu.mem_write(BASE,DATA)
    emu.mem_map(0x5000000,0x200000)
    role,tree,node,head,slot,stack=0x5001000,0x5002000,0x5003000,0x5004000,0x5005000,0x5100000
    def w(a,*v):emu.mem_write(a,struct.pack('<'+'I'*len(v),*v))
    def read(a):return struct.unpack('<I',emu.mem_read(a,4))[0]
    w(stack+0x18,tree);w(tree+4,head);w(node+12,key)
    emu.mem_write(node+16,struct.pack('<f',value));w(slot,12345)
    calls=[]
    def hook(uc,address,size,user):
        if address==0x113f630:uc.emu_stop()
        elif address==0x4e8e00:
            sp=uc.reg_read(UC_X86_REG_ESP)
            assert uc.reg_read(UC_X86_REG_ECX)==role+0x6c
            assert read(read(sp+4))==key
            calls.append(key)
            uc.reg_write(UC_X86_REG_EAX,slot)
            uc.reg_write(UC_X86_REG_ESP,sp+8)
            uc.reg_write(UC_X86_REG_EIP,read(sp))
    emu.hook_add(UC_HOOK_CODE,hook)
    emu.reg_write(UC_X86_REG_ESP,stack);emu.reg_write(UC_X86_REG_EDI,role);emu.reg_write(UC_X86_REG_ESI,node)
    emu.emu_start(0x113f5f0,0x113f630,count=10000)
    assert emu.reg_read(UC_X86_REG_EIP)==0x113f630 and calls==[key]
    return read(slot)


def main():
    kind,payload=role_resource_refresh(VitalState(1,3,201,500,601,1000))
    assert kind==0xc32c8
    # Build a concrete nonempty STL map inside the probe object. The original
    # marshal walks it; the original decoder constructs a new balanced map.
    obj=0x5001000;head=obj+0x100;nodes=[obj+0x140,obj+0x160]
    pairs=((60,201),(70,601))
    fields={8:struct.pack('<III',0,head,len(pairs)),
        0x100:struct.pack('<IIIIIBB2x',nodes[0],nodes[0],nodes[-1],0,0,0,1)}
    for i,(key,value) in enumerate(pairs):
        fields[0x140+i*32]=struct.pack('<IIIifBB2x',head,head if i==0 else nodes[i-1],
            head if i==len(pairs)-1 else nodes[i+1],key,float(value),0,0)
    original,raw=probe(0xec3590,0xec36b0,0xec3730,fields)
    assert original==payload and struct.unpack_from('<I',raw,16)[0]==2
    for key,value in ((60,201),(70,601),(60,0),(70,0),(60,16777216)):
        assert native_assignment(key,value)==value
    try:probe(0xec3590,0xec36b0,0xec3730,payload=payload[:-1])
    except ValueError:pass
    else:raise AssertionError('Original role map decoder accepted truncation')
    try:role_resource_refresh(VitalState(1,0,16777217,16777217,1,1))
    except ValueError:pass
    else:raise AssertionError('Float precision silently changed authoritative resources')
    report={'passed':['ordinary SRefreshRoleData type and two-entry map bytes match original marshal',
        'original map decoder consumes nonempty payload','original generic attr branch overwrites HP/MP',
        'zero resources and exact float boundary','native truncation rejection','inexact float refuses'],
        'constructor':'0xec3590','marshal':'0xec36b0','unmarshal':'0xec3730',
        'consumer_executed':'0x113f5f0..0x113f630',
        'consumer_adapter':'attribute map lookup supplies a slot; native float conversion and overwrite execute',
        'attribute_ids':{'60':'current HP','70':'current MP'},'native_ui_tested':False}
    write_json(OUT/'evidence/role-resource-protocol-verification.json',report)
    print('PASS:',', '.join(report['passed']))


if __name__=='__main__':main()
