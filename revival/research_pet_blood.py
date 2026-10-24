"""Original blood power/cap stores, colour-limited level lookup and potential UI."""
import json
import struct

from native_gameplay_probe import probe
from native_inspect import u32
from inspect_client import OUT,write_json


def native_blood_record(payload):
    result=[]
    def observe(uc,message):
        from unicorn import UC_HOOK_CODE
        from unicorn.x86_const import (UC_X86_REG_EAX,UC_X86_REG_EBX,UC_X86_REG_ECX,
            UC_X86_REG_EDI,UC_X86_REG_EDX,UC_X86_REG_ESI,UC_X86_REG_ESP,UC_X86_REG_EIP)
        def r(a):return struct.unpack('<I',uc.mem_read(a,4))[0]
        def w(a,*v):uc.mem_write(a,struct.pack('<'+'I'*len(v),*v))
        stack,stop,pet,root,vt,record=0x5108000,0x500f000,0x5300000,0x5308000,0x530a000,0x530b000
        attrs={};cells={};queries=[]
        rows={int(row['attributes']['id']):row['attributes'] for row in json.loads(
            (OUT/'catalogs/knight.gsp.pet.cpetbloodconfig.json').read_text(encoding='utf-8'))}
        def ret(n,value=0):
            sp=uc.reg_read(UC_X86_REG_ESP);dest=r(sp)
            uc.reg_write(UC_X86_REG_EAX,value);uc.reg_write(UC_X86_REG_ESP,sp+4+n);uc.reg_write(UC_X86_REG_EIP,dest)
        def terminal(uc,address,size,user):
            sp=uc.reg_read(UC_X86_REG_ESP)
            if address==0x4e8e00:
                key=r(r(sp+4));cell=0x530c000+len(cells)*4;cells[key]=cell;ret(4,cell)
            elif address==0x500d000:
                key=r(sp+4);row=rows[key];queries.append(key)
                w(record,key,int(row['lowpower']),int(row['uppower']),0)
                uc.mem_write(record+0x10,struct.pack('<d',float(row['ratio'])));ret(4,record)
        hook=uc.hook_add(UC_HOOK_CODE,terminal)
        w(stack,stop);w(0x2945724,0)
        for reg,value in ((UC_X86_REG_ESP,stack),(UC_X86_REG_ESI,message),
                          (UC_X86_REG_EBX,pet),(UC_X86_REG_EDI,pet+0x34),(UC_X86_REG_EDX,stack+0x18)):
            uc.reg_write(reg,value)
        uc.emu_start(0x113532c,0x1135373,count=1000)
        assert uc.reg_read(UC_X86_REG_EIP)==0x1135373
        attrs={key:r(cell) for key,cell in cells.items()}
        uc.emu_start(0x11354fb,0x113551c,count=1000)
        grade=r(pet+0x2c)
        w(0x2945aec,root);w(root+0xb68,vt);w(vt+8,0x500d000)
        w(stack,stop,attrs[1140],grade);uc.reg_write(UC_X86_REG_ESP,stack)
        uc.emu_start(0x11297d0,stop,count=10000)
        assert uc.reg_read(UC_X86_REG_EIP)==stop
        row=uc.reg_read(UC_X86_REG_EAX);level=r(row)
        # Exact original ordinary potential display arithmetic, not its strings.
        w(stack+0x38,level);uc.reg_write(UC_X86_REG_ESP,stack)
        uc.emu_start(0x1435a01,0x1435a0b,count=10)
        potential=r(uc.reg_read(UC_X86_REG_ESP))
        uc.hook_del(hook)
        result.append({'power':attrs[1140],'maximum_power':attrs[1150],'insight':attrs[1160],
            'grade':grade,'level':level,'displayed_blood_potential':potential,'queries':queries})
    probe(0xf9d7b0,0xf9d840,0xf9d880,payload=payload,observer=observe)
    return result[0]


def main():
    caps=(3,5,7,9,12,15)
    assert tuple(u32(0x28d0b1c+4*i) for i in range(1,7))==caps
    request,_=probe(0xdbe0f0,0xe53940,0xdbe1b0,
        {8:struct.pack('<i',7),0xc:struct.pack('<i',1),0x10:struct.pack('<i',2),0x18:struct.pack('<Q',500001)})
    assert request==struct.pack('>iiiQ',7,1,2,500001)
    rows=json.loads((OUT/'catalogs/knight.gsp.pet.cpetbloodconfig.json').read_text(encoding='utf-8'))
    cases=[]
    for grade,cap in enumerate(caps,1):
        for row in rows[:cap+1]:
            attr=row['attributes'];level=int(attr['id'])
            for power in dict.fromkeys((int(attr['lowpower']),int(attr['uppower']))):
                data,_=probe(0xf89ba0,0xf5df70,0xf5f1f0,{4:struct.pack('<i',500001),8:struct.pack('<i',7),
                    0x30:struct.pack('<i',power),0x34:struct.pack('<i',int(rows[cap]['attributes']['lowpower'])),
                    0x38:struct.pack('<i',73),0x3c:struct.pack('<i',grade)})
                value=native_blood_record(data)
                assert value['level']==level and value['displayed_blood_potential']==level*10
                assert (value['power'],value['maximum_power'],value['insight'],value['grade'])==(
                    power,int(rows[cap]['attributes']['lowpower']),73,grade)
                cases.append(value)
    write_json(OUT/'evidence/pet-blood-native.json',{'source_status':'client_verified','passed':len(cases),'cases':cases,
        'separate_request_codec':{'type':'0xc07e7','bytes':request.hex(),'format':'three BE32 plus BE64; business identities unproved'},
        'stores':'Original Pet codec ->113532c..1135373 bean+30/+34/+38 ->attr1140/1150/1160; colour bean+3c ->pet+2c',
        'level':'Whole original11297d0 executes range scan and colour cap; actual89e290 getter/root+b68 uses CPetBloodConfig installed d43510',
        'potential':'Original1435a01..1435a0b computes level*10 for ordinary blood display',
        'insight_correction':'1160 is raw insight, independently proved by original return UI Wuxing control in pet-traits-native.json; prior rootbone label was incorrect',
        'adapters':'Only extracted original table row lookup and terminal attribute-map cells; no replacement level algorithm',
        'limits':['Normal blood branch only; metamorphosis is separate','Cap field probe value is supplied, not proof of original server clamping','No live client/server/battle']})
    print('PASS',len(cases),'original power/cap/independent insight stores, native colour-limited blood level and ordinary potential arithmetic')


if __name__=='__main__':main()
