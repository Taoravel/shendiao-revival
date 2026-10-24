"""Original cake-count codec, refresh store1540 and shared twenty-cake guard."""
import struct
from native_gameplay_probe import probe
from inspect_client import OUT,write_json


def native_count(payload):
    result=[]
    def observe(uc,message):
        from unicorn import UC_HOOK_CODE
        from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_EDI,UC_X86_REG_ESI,UC_X86_REG_ESP,UC_X86_REG_EIP
        pet,cell,stack,stop=0x5300000,0x5302000,0x5108000,0x500f000
        def r(a):return struct.unpack('<I',uc.mem_read(a,4))[0]
        def w(a,*v):uc.mem_write(a,struct.pack('<'+'I'*len(v),*v))
        seen={}
        def hook(uc,address,size,user):
            sp=uc.reg_read(UC_X86_REG_ESP)
            if address==0x4e8e00:
                assert r(r(sp+4))==1540
                seen['attribute']=1540
                uc.reg_write(UC_X86_REG_EAX,cell);uc.reg_write(UC_X86_REG_ESP,sp+8);uc.reg_write(UC_X86_REG_EIP,r(sp))
            elif address in (0x11378f5,0x1137904):
                seen['twenty_rejected']=address==0x11378f5;uc.emu_stop()
        h=uc.hook_add(UC_HOOK_CODE,hook)
        for reg,val in ((UC_X86_REG_ESI,message),(UC_X86_REG_EDI,pet+0x34),(UC_X86_REG_ESP,stack)):
            uc.reg_write(reg,val)
        uc.emu_start(0x1135390,0x11353b4,count=100)
        seen['count']=r(cell)
        uc.reg_write(UC_X86_REG_ESI,pet);uc.reg_write(UC_X86_REG_ESP,stack)
        uc.emu_start(0x11378d9,stop,count=100)
        assert seen['twenty_rejected']==(seen['count']==20)
        uc.hook_del(h);result.append(seen)
    probe(0xf9d7b0,0xf9d840,0xf9d880,payload=payload,observer=observe)
    return result[0]


def main():
    identity={4:struct.pack('<i',500001),8:struct.pack('<i',7)}
    original,_=probe(0xf89ba0,0xf5df70,0xf5f1f0,identity)
    cases=[]
    for count in (0,1,19,20):
        payload,raw=probe(0xf89ba0,0xf5df70,0xf5f1f0,identity|{0x111:bytes([count])})
        assert raw[0x111]==count
        assert [(i,a,b) for i,(a,b) in enumerate(zip(original,payload)) if a!=b]==([] if count==0 else [(164,0,count)])
        value=native_count(payload);assert value['count']==count;cases.append(value)
    write_json(OUT/'evidence/pet-cake-native.json',{'source_status':'client_verified','passed':len(cases),'cases':cases,
        'codec':'original Pet bean+111 -> empty-name wire164/base tail155; signed-byte refresh+119 -> attr1540',
        'guard':'actual11378d9..11378f3 branches at attr1540==20 to original145133 rejection, not20 per aptitude',
        'adapters':'only attr-map cell lookup; original codecs/store/compare/branch execute unchanged',
        'limits':['not cake probability/gain formula','not live UI','additions history is designed persistent audit']})
    print('PASS',len(cases),'original cake count codec/1540 refresh store/twenty cap branch')


if __name__=='__main__':main()
