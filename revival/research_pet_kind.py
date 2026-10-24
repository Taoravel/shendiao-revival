"""Offline original kind parser, complete kind2 predicate and immortality UI branch."""
import hashlib
import json
import struct
from native_inspect import BASE, DATA, u32
from inspect_client import OUT, write_json
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX, UC_X86_REG_EBP,
    UC_X86_REG_EDI, UC_X86_REG_EDX, UC_X86_REG_ESI, UC_X86_REG_ESP, UC_X86_REG_EIP)


def main():
    uc=Uc(UC_ARCH_X86,UC_MODE_32)
    uc.mem_map(0,0x1000)
    uc.mem_map(BASE,(len(DATA)+0xfff)&~0xfff)
    uc.mem_write(BASE,DATA)
    uc.mem_map(0x5000000,0x200000)
    pet,root,cache,vt,row,stack=0x5001000,0x5003000,0x5005000,0x5005100,0x5006000,0x5100000
    ctor,dtor,lookup,assign,stop=0x500d000,0x500d010,0x500d020,0x500d030,0x500ff00
    def r(a):return struct.unpack('<I',uc.mem_read(a,4))[0]
    def w(a,*values):uc.mem_write(a,struct.pack('<'+'I'*len(values),*(v&0xffffffff for v in values)))
    def ret(n,value=0):
        sp=uc.reg_read(UC_X86_REG_ESP);dest=r(sp)
        uc.reg_write(UC_X86_REG_EAX,value)
        uc.reg_write(UC_X86_REG_ESP,sp+4+n);uc.reg_write(UC_X86_REG_EIP,dest)
    assert u32(0x225c5e4+8)==0x884e60
    assert DATA[0x22660e8-BASE:0x22660e8-BASE+10]=='kind\0'.encode('utf-16le')
    w(0x2945aec,root);w(root+0xb60,0x225c5e4,cache);w(cache,vt);w(vt+8,lookup)
    w(0x22443f0,ctor);w(0x22443ec,dtor);w(0x2244464,assign)
    current={};observed={}
    def hook(uc,address,size,user):
        sp=uc.reg_read(UC_X86_REG_ESP)
        if address==ctor:
            # Host CRT string terminal; actual native push selects literal kind.
            assert r(sp+4) in (0x22660e8,0x24416a4)
            if r(sp+4)==0x22660e8:observed['kind_literal']=True
            ret(4,uc.reg_read(UC_X86_REG_ECX))
        elif address==dtor:ret(0)
        elif address==assign:ret(4,uc.reg_read(UC_X86_REG_ECX))
        elif address==0x409ce0:
            assert observed['kind_literal'] and r(sp+8)==0
            ret(8,current['kind'])
        elif address==lookup:
            assert uc.reg_read(UC_X86_REG_ECX)==cache
            observed.setdefault('lookups',[]).append(r(sp+4))
            assert r(sp+4)==current['id']
            ret(4,row)
        elif address==0x837060:
            # Do not emulate text formatting. Observe actual original text key.
            observed['ui_string']=r(sp+8);uc.emu_stop()
        elif address in (0x1404aaf,0x143db55,0x143dc79):
            observed['branch']=hex(address);uc.emu_stop()
        elif address==0x89dde0:
            # Original denial branch has not yet looked up its notice.
            # Let the native pushes execute, stopping just before vtable access.
            ret(0,cache)
        elif address==0x143dc5f:
            observed['notice']=r(sp);uc.emu_stop()
    uc.hook_add(UC_HOOK_CODE,hook)
    rows=json.loads((OUT/'catalogs/knight.gsp.pet.cpetattr.json').read_text(encoding='utf-8'))
    strings=json.loads((OUT/'catalogs/knight.gsp.message.cstringres.json').read_text(encoding='utf-8'))
    messages=json.loads((OUT/'catalogs/knight.gsp.message.cmessagetip.json').read_text(encoding='utf-8'))
    assert next(r['attributes']['msg'] for r in strings if r['attributes']['id']=='2676')=='永生'
    assert next(r['attributes']['msg'] for r in messages if r['attributes']['id']=='146589')=='神兽类宠物或野生宠物不能进行超级还童操作。'
    cases=[]
    for item in rows:
        attr=item['attributes'];current={'id':int(attr['id']),'kind':int(attr['kind'])};observed={}
        uc.mem_write(row,bytes(0x100));w(row,current['id']);w(row+0x58,int(attr['life']))
        for reg,value in ((UC_X86_REG_ESP,stack),(UC_X86_REG_EDI,row),(UC_X86_REG_ESI,cache),(UC_X86_REG_EBX,0)):
            uc.reg_write(reg,value)
        uc.emu_start(0xa72fbe,0xa72ffa,count=100)
        assert uc.reg_read(UC_X86_REG_EIP)==0xa72ffa and r(row+0x44)==current['kind']
        w(pet+4,current['id']);w(stack,stop,pet);uc.reg_write(UC_X86_REG_ESP,stack)
        uc.emu_start(0x1129900,stop,count=100)
        special=uc.reg_read(UC_X86_REG_EAX)&0xff
        assert uc.reg_read(UC_X86_REG_EIP)==stop and special==int(current['kind']==2)
        uc.reg_write(UC_X86_REG_EDI,row)
        # This display slice only reads pet+2c, no care value or sentinel.
        uc.reg_write(UC_X86_REG_EBP,pet);uc.reg_write(UC_X86_REG_ESP,stack)
        uc.emu_start(0x1404931,stop,count=100)
        assert observed.get('ui_string')==(2676 if special else None)
        if not special:assert observed['branch']=='0x1404aaf'
        for wild in (0,1):
            observed.pop('branch',None);observed.pop('notice',None)
            uc.mem_write(pet+0x29,bytes([wild]));uc.reg_write(UC_X86_REG_ESI,pet)
            uc.reg_write(UC_X86_REG_ESP,stack)
            uc.emu_start(0x143db26,stop,count=100)
            denied=observed.get('notice')==146589
            assert denied==(bool(wild) or bool(special))
            if not denied:assert observed['branch']=='0x143db55'
        cases.append({'id':current['id'],'name':attr['name'],'kind':current['kind'],
                      'native_kind2':bool(special),'ui_string':observed.get('ui_string')})
    # Whole original predicate handles missing rows without calling them kind2.
    current={'id':0x7fffffff,'kind':2};w(pet+4,current['id']);w(row,-1);w(row+0x44,2)
    w(stack,stop,pet);uc.reg_write(UC_X86_REG_ESP,stack)
    uc.emu_start(0x1129900,stop,count=100)
    assert uc.reg_read(UC_X86_REG_EAX)&0xff==0
    write_json(OUT/'evidence/pet-kind-native.json',{
        'source_status':'client_verified','image_sha256':hashlib.sha256(DATA).hexdigest(),
        'cases':cases,'passed_rows':len(cases),'missing_row_predicate':False,
        'parser':'a72fbe..a72ffa original literal kind -> XML integer terminal -> record+44',
        'predicate':'whole1129900, actual89e280 root+b60 and884e60 original dispatcher; exact kind==2',
        'immortality_display':'1404931..1404987 exact kind2 -> original string ID2676=永生; other kinds ->1404aaf',
        'super_rebirth_guard':'143db26..143dc5f actual template lookup; wild flag+29==1 or kind2 -> notice146589; kind3 does not take this guard',
        'adapters':['Host XML integer and CRT string terminals only',
                    'Actual original CPetAttr table implementation/vtable retained; cache row lookup terminal supplies original rows',
                    'UI text lookup/notice observed, full dialog not executed'],
        'limits':['No original server code or live client/server/battle',
                  'Kind3 does not receive this immortality text; absence alone does not prove all server care rules',
                  'No lifetime sentinel inferred; original display selects by kind, not life6000',
                  'Super rebirth guard only; not complete ordinary or super rebirth eligibility']})
    print('PASS',len(cases),'original kind parser, whole predicate, immortality display and super-rebirth guard')


if __name__=='__main__':main()
