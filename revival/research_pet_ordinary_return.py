"""Original ordinary-return template-uselevel95 selection and real CUseItem construction."""
import struct
import json
from native_inspect import BASE,DATA
from native_gameplay_probe import probe
from inspect_client import OUT,write_json
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import (UC_X86_REG_EAX,UC_X86_REG_EBP,UC_X86_REG_ESI,UC_X86_REG_EDI,
    UC_X86_REG_ECX,UC_X86_REG_EIP,UC_X86_REG_ESP)


def main():
    uc=Uc(UC_ARCH_X86,UC_MODE_32)
    uc.mem_map(BASE,(len(DATA)+0xfff)&~0xfff);uc.mem_write(BASE,DATA)
    uc.mem_map(0x5000000,0x400000)
    row,dialog,stack=0x5300000,0x5302000,0x5108000
    def r(a):return struct.unpack('<I',uc.mem_read(a,4))[0]
    def w(a,*v):uc.mem_write(a,struct.pack('<'+'I'*len(v),*v))
    def hook(uc,address,size,user):
        if address==0x1429800:
            # UI label/count rebuild terminal; qualification arithmetic is original.
            sp=uc.reg_read(UC_X86_REG_ESP)
            uc.reg_write(UC_X86_REG_ESP,sp+4);uc.reg_write(UC_X86_REG_EIP,r(sp))
    uc.hook_add(UC_HOOK_CODE,hook)
    cases=[]
    pets=json.loads((OUT/'catalogs/knight.gsp.pet.cpetattr.json').read_text(encoding='utf-8'))
    for source in pets:
        attr=source['attributes'];level=int(attr['uselevel'])
        for old in (0,1):
            w(row+0x48,level);uc.mem_write(dialog+0xfc,bytes([old]))
            for reg,val in ((UC_X86_REG_EBP,row),(UC_X86_REG_ESI,dialog),(UC_X86_REG_ESP,stack)):
                uc.reg_write(reg,val)
            uc.emu_start(0x142ac8f,0x142acab,count=100)
            chosen=bytes(uc.mem_read(dialog+0xfc,1))[0]
            assert chosen==int(level>=95)
            # Real bag lookup computes the requested template31002 + (flag?85:0).
            uc.mem_write(stack+0x3c,bytes([chosen]));uc.reg_write(UC_X86_REG_ESP,stack);uc.reg_write(UC_X86_REG_ECX,dialog)
            uc.emu_start(0x1094897,0x10948b9,count=100)
            template=uc.reg_read(UC_X86_REG_EAX)
            assert template==(31087 if level>=95 else 31002)
            cases.append({'pet_template':int(attr['id']),'template_uselevel':level,'old_ui_flag':old,'item_template':template})
    sends=[]
    for pet,key in ((1,11),(7,12),(0x7fffffff,0x7fffffff)):
        w(dialog+0xd0,pet)
        for reg,val in ((UC_X86_REG_ESI,dialog),(UC_X86_REG_EDI,key),(UC_X86_REG_ESP,stack)):
            uc.reg_write(reg,val)
        uc.emu_start(0x14293c6,0x14293db,count=100)
        assert tuple(r(stack+0xc+4*i) for i in range(6))==(0x2277200,0xc03ff,key,1,pet,0)
        payload,raw=probe(0xd98770,0xe4d740,0xd987a0,
            {8:struct.pack('<i',key),12:struct.pack('<i',1),16:struct.pack('<Q',pet)},factory=True)
        assert payload==struct.pack('>iiQ',key,1,pet)
        sends.append({'pet':pet,'key':key,'body':payload.hex()})
    write_json(OUT/'evidence/pet-ordinary-return-native.json',{
        'source_status':'client_verified','template_cases':len(cases),'cases':cases,'actual_send_cases':sends,
        'threshold':'original142ac71 fetches CPetAttr for selected pet template,142ac8f compares row+48(uselevel) against95, not current level490',
        'item_selection':'original1094897..10948b9 computes31002/31087 from real dialog flag, no inferred current-level switch',
        'send':'actual14293c6..14293db calls unchanged10729f0 CUseItem constructor(key,1,u64pet), original factory/codec roundtrip',
        'guards':'static original1429338..14293c6 rejects absent selected pet, active190/194 and other-status1130850; original142a6f4 tests pet+a0/+a4 then149193; these guard meanings/authorities are not all executed by this probe',
        'limits':['no live UI/client','random distribution and reset transaction separate','special-kind ordinary qualification not inferred from super-return kind2 guard']})
    print('PASS',len(cases),'original template-uselevel95/item-selection cases and',len(sends),'actual ordinary-return send/codec cases')


if __name__=='__main__':main()
