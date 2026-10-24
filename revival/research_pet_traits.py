"""Original Pet -> insight1160 and origin -> real return-dialog consumers."""
import struct
from native_gameplay_probe import probe
from inspect_client import OUT,write_json


def native_traits(payload):
    values=[]
    def observe(uc,message):
        from unicorn import UC_HOOK_CODE
        from unicorn.x86_const import (UC_X86_REG_EAX,UC_X86_REG_EBX,UC_X86_REG_ECX,
            UC_X86_REG_EDI,UC_X86_REG_EDX,UC_X86_REG_EBP,UC_X86_REG_ESI,UC_X86_REG_ESP,UC_X86_REG_EIP)
        pet,cell,ui,control,stack,stop=0x5300000,0x5302000,0x5304000,0x5306000,0x5108000,0x500f000
        def r(a):return struct.unpack('<I',uc.mem_read(a,4))[0]
        def w(a,*v):uc.mem_write(a,struct.pack('<'+'I'*len(v),*v))
        def ret(n,value=0):
            sp=uc.reg_read(UC_X86_REG_ESP);dest=r(sp)
            uc.reg_write(UC_X86_REG_EAX,value);uc.reg_write(UC_X86_REG_ESP,sp+n+4);uc.reg_write(UC_X86_REG_EIP,dest)
        seen={}
        def hook(uc,address,size,user):
            sp=uc.reg_read(UC_X86_REG_ESP)
            if address==0x4e8e00:
                assert r(r(sp+4))==1160
                ret(4,cell)
            elif address==0x837060:
                seen['origin_string']=r(sp+8);uc.emu_stop()
            elif address==0x454130:
                pointer,count=r(sp+4),r(sp+8)
                seen['binding_literal']=bytes(uc.mem_read(pointer,count)).decode()
                ret(8,uc.reg_read(UC_X86_REG_ECX))
            elif address==0x4552c0:ret(4,control)
        handle=uc.hook_add(UC_HOOK_CODE,hook)
        w(stack,stop)
        for reg,value in ((UC_X86_REG_EAX,cell),(UC_X86_REG_ECX,0),(UC_X86_REG_ESI,message),
            (UC_X86_REG_EBX,pet),(UC_X86_REG_EDI,pet+0x34),(UC_X86_REG_ESP,stack)):
            uc.reg_write(reg,value)
        uc.emu_start(0x1135358,0x1135373,count=100)
        insight=r(cell)
        uc.emu_start(0x11353c9,0x11353dd,count=100)
        origin=bytes(uc.mem_read(pet+0x29,1))[0]
        uc.reg_write(UC_X86_REG_EBP,pet);uc.reg_write(UC_X86_REG_EBX,0);uc.reg_write(UC_X86_REG_ESP,stack)
        uc.emu_start(0x143c940,stop,count=100)
        assert seen['origin_string']==(2138 if origin==2 else 2139)
        # Actual return UI fetches1160 as the integer being formatted for Wuxing.
        uc.reg_write(UC_X86_REG_EBP,pet);uc.reg_write(UC_X86_REG_ESP,stack)
        uc.emu_start(0x143d6ab,0x143d6c3,count=100)
        assert r(uc.reg_read(UC_X86_REG_ESP))==insight
        # Original ASCII control literal, window lookup terminal and member store.
        for reg,value in ((UC_X86_REG_EBP,0x20),(UC_X86_REG_EBX,0),(UC_X86_REG_EDI,ui+0x800),
                          (UC_X86_REG_ESI,ui),(UC_X86_REG_ESP,stack)):
            uc.reg_write(reg,value)
        uc.emu_start(0x143e4cb,0x143e516,count=100)
        assert seen['binding_literal']=='PetSuperReturn/Wuxing' and r(ui+0x68)==control
        # The display's final setter uses that same+68 control (string host
        # formatting is deliberately not substituted for original arithmetic).
        uc.hook_del(handle)
        values.append({'insight':insight,'origin':origin,'origin_string':seen['origin_string'],
                       'ui_control':seen['binding_literal']})
    probe(0xf9d7b0,0xf9d840,0xf9d880,payload=payload,observer=observe)
    return values[0]


def main():
    cases=[]
    for insight in (0,1,73,255,1000,0x7fffffff):
        for origin in (1,2):
            record,_=probe(0xf89ba0,0xf5df70,0xf5f1f0,
                {4:struct.pack('<i',500001),8:struct.pack('<i',7),
                 0x38:struct.pack('<i',insight),0xa8:struct.pack('<i',987654),0xb4:struct.pack('<i',origin)})
            value=native_traits(record)
            assert (value['insight'],value['origin'])==(insight,origin)
            cases.append(value)
    write_json(OUT/'evidence/pet-traits-native.json',{
        'source_status':'client_verified','passed':len(cases),'cases':cases,
        'insight':'Pet bean+38 -> raw SRefresh+40 -> original1135361..1135373 attr1160, NOT bean+a8/attr590',
        'origin':'Pet bean+b4 i32 -> raw SRefresh+bc low byte -> original11353c9..11353dd pet+29;2宝宝/1野生 via143c940 CString2138/2139',
        'binding':'original143e4cb ASCII PetSuperReturn/Wuxing -> actual member+68 store;143d6ab getter1160;143d72e final setter uses+68',
        'adapters':['original Pet and SRefreshPetData codecs execute unchanged',
                    'only attribute-map cell, CString resource lookup, CRT string construction and window lookup terminals',
                    'no full live dialog rendering or server RNG'],
        'correction':'prior rootbone label for1160 was unproved; actual return UI proves insight.590 remains the separate original legacy dodge aptitude and is not renamed insight',
        'limits':['representation bounds tested, not an original generated insight range/distribution',
                  'origin values other than1/2 not classified as supported complete identity',
                  'insight skill-learning probability and live UI still unverified']})
    print('PASS',len(cases),'original insight1160 and baby/wild identity stores and return-dialog consumers')


if __name__=='__main__':main()
