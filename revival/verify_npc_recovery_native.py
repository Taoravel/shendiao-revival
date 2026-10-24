"""Original four recovery requests, vigor fields and inn x87 vigor quote."""
import hashlib
import struct
from native_gameplay_probe import probe
from native_inspect import BASE,DATA
from verify_role_resource_protocol import native_assignment
from role_vigor import VigorState,refresh
from inspect_client import OUT,write_json


def main():
    from unicorn import Uc,UC_ARCH_X86,UC_MODE_32
    from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ESP,UC_X86_REG_EIP
    cases=[]
    for key in (1,0x123456789,0x123456789abcdef):
        for kind in range(1,5):
            expected=struct.pack('>qi',key,kind)
            native,raw=probe(0xdb1c70,0xe51c00,0xdb1d30,
                {8:struct.pack('<q',key),16:struct.pack('<i',kind)})
            assert native==expected and struct.unpack_from('<qi',raw,8)==(key,kind)
            cases.append([key,kind])
    try:probe(0xdb1c70,0xe51c00,0xdb1d30,payload=expected[:-1])
    except ValueError:pass
    else:raise AssertionError('Original recovery decoder accepted truncation')
    state=VigorState(7,1,85,100,'77',0,0)
    kind,payload=refresh(state);assert kind==0xc32c8
    obj=0x5001000;head=obj+0x100;nodes=[obj+0x140,obj+0x160]
    fields={8:struct.pack('<III',0,head,2),
        0x100:struct.pack('<IIIIIBB2x',nodes[0],nodes[0],nodes[-1],0,0,0,1)}
    for i,(key,value) in enumerate(((440,85),(620,100))):
        fields[0x140+i*32]=struct.pack('<IIIifBB2x',head,head if i==0 else nodes[i-1],
            head if i==1 else nodes[i+1],key,float(value),0,0)
    native,raw=probe(0xec3590,0xec36b0,0xec3730,fields)
    assert native==payload and struct.unpack_from('<I',raw,16)[0]==2
    for key,value in ((440,85),(440,0),(620,100)):assert native_assignment(key,value)==value
    factor=struct.unpack_from('<d',DATA,0x224e408-BASE)[0]
    assert factor.hex()=='0x1.3333340000000p-3'
    quotes=[]
    for maximum,expected in ((1,0),(6,0),(7,1),(20,3),(100,15),
                              (200,30),(300,45),(1000,150),(16777216,2516582)):
        uc=Uc(UC_ARCH_X86,UC_MODE_32)
        uc.mem_map(0,4096);uc.mem_map(BASE,(len(DATA)+4095)&~4095);uc.mem_write(BASE,DATA)
        uc.mem_map(0x5000000,0x200000)
        uc.reg_write(UC_X86_REG_ESP,0x5100000);uc.reg_write(UC_X86_REG_EAX,maximum)
        uc.emu_start(0x16338e6,0x16338f9,count=10000)
        assert uc.reg_read(UC_X86_REG_EIP)==0x16338f9
        actual=uc.reg_read(UC_X86_REG_EAX)
        assert actual==expected and actual==int(maximum*factor)
        quotes.append([maximum,actual])
    report={'passed':['12 original recovery key/type round trips; truncation rejection',
        'vigor440/620 original map codecs and generic assignments',
        '9 original x87 inn vigor calculations including float boundary'],
        'recovery':{'type':'0xc2333','constructor':'0xdb1c70','marshal':'0xe51c00',
            'unmarshal':'0xdb1d30','cases':cases},
        'vigor':{'factor_hex':factor.hex(),'original_executed':'0x16338e6..0x16338f9 including original ftol',
            'cases':quotes},'native_image_sha256':hashlib.sha256(DATA).hexdigest(),
        'native_gui_verified':False,'live_database_modified':False}
    write_json(OUT/'evidence/npc-recovery-native.json',report);print(report['passed'])


if __name__=='__main__':main()
