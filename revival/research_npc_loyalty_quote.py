"""Execute original loyalty quote from original Pet codec and refresh stores.

Offline only: no production imports, live process, database, network or policy write.
"""
import contextlib
import functools
import hashlib
import json
import struct
from pathlib import Path

from bxml import decode
from native_gameplay_probe import probe
from native_inspect import BASE,DATA,disasm,u32
from pfs import PfsArchive
from research_npc_submenu import Machine

ROOT=Path(__file__).parent


def signed(value):return value if value<0x80000000 else value-0x100000000


@functools.lru_cache(None)
def native_pet(power,grade,loyalty):
    """Original Pet constructor -> marshal -> fresh original Pet decoder."""
    fields={4:struct.pack('<i',500001),8:struct.pack('<i',7),
            0x30:struct.pack('<i',power),0x34:struct.pack('<i',52611),
            0x38:struct.pack('<i',73),0x3c:struct.pack('<i',grade),
            0x90:struct.pack('<i',loyalty)}
    wire,bean=probe(0xf89ba0,0xf5df70,0xf5f1f0,fields)
    assert tuple(struct.unpack_from('<i',bean,o)[0] for o in (0x30,0x3c,0x90))==(power,grade,loyalty)
    return wire,bean


def quote(pets,role_level,rows):
    """Whole native1136290; only map-cell/config-row dependencies adapted."""
    from unicorn import UC_HOOK_CODE
    from unicorn.x86_const import (UC_X86_REG_EAX,UC_X86_REG_EBX,UC_X86_REG_ECX,
        UC_X86_REG_EDI,UC_X86_REG_EDX,UC_X86_REG_ESI,UC_X86_REG_EBP)
    m=Machine();uc=m.uc
    head=0x5003000;nodes=[0x5004000+i*0x1000 for i in range(len(pets))]
    message=0x5020000;cfgroot,vt,lookup,row=0x5300000,0x5310000,0x5311000,0x5312000
    m.w(m.ui+0x27c,head,len(pets));m.w(head,nodes[0] if nodes else head)
    for i,node in enumerate(nodes):m.w(node,nodes[i+1] if i+1<len(nodes) else head)
    m.w(0x2945aec,cfgroot);m.w(cfgroot+0xc1c,vt);m.w(vt+8,lookup)
    m.w(0x2945724,0)
    cells={};reads=[];lookups=[];steps=[];phase=['refresh']
    def cell(map_address,key):
        pair=(map_address,key)
        if pair not in cells:cells[pair]=0x5200000+4*len(cells)
        return cells[pair]
    m.w(cell(m.ui+0x164,490),role_level&0xffffffff)
    def hook(uc,a,size,user):
        sp=uc.reg_read(m.spreg)
        if a==0x4e8e00:
            map_address=uc.reg_read(UC_X86_REG_ECX);key=m.r(m.r(sp+4))
            ptr=cell(map_address,key)
            if phase[0]=='quote':reads.append({'map':hex(map_address),'key':key,'value':signed(m.r(ptr))})
            m.ret(ptr,4)
        elif a==lookup:
            grade=m.r(sp+4);cfg=rows.get(grade)
            m.w(row,(grade if cfg else 0xffffffff));m.w(row+0x24,int(cfg['maxloy']) if cfg else 0)
            lookups.append({'grade':grade,'record_id':grade if cfg else -1,
                            'maxloy':int(cfg['maxloy']) if cfg else None})
            m.ret(row,4)
        elif a==0x1136333:
            steps.append({'node':hex(uc.reg_read(UC_X86_REG_ESI)),
                          'deficit':signed(uc.reg_read(UC_X86_REG_EDI))})
        elif a==0x113634a:steps[-1]['native_remainder']=signed(uc.reg_read(UC_X86_REG_EDX))
        elif a==0x113634e:steps[-1]['unit_fee']=signed(uc.reg_read(UC_X86_REG_EDX))
        elif a==0x1136351:steps[-1]['contribution']=signed(uc.reg_read(UC_X86_REG_EDX))
        elif a==0x1136365:
            steps.append({'native_sum_before_free_gate':signed(uc.reg_read(UC_X86_REG_EBP))})
    uc.hook_add(UC_HOOK_CODE,hook)
    for i,((power,grade,loyalty),node) in enumerate(zip(pets,nodes)):
        wire,bean=native_pet(power,grade,loyalty)
        # Refresh's ESI is a message containing its Pet bean at +8. Only copied
        # decoded scalar fields are read by these original refresh slices.
        uc.mem_write(message+8,bean)
        pet=node+8
        for reg,value in ((m.spreg,m.stack),(UC_X86_REG_ESI,message),
                          (UC_X86_REG_EBX,pet),(UC_X86_REG_EDI,pet+0x34),
                          (UC_X86_REG_EDX,m.stack+0x18)):
            uc.reg_write(reg,value)
        uc.emu_start(0x113532c,0x1135373,count=1000)
        assert uc.reg_read(m.ipreg)==0x1135373
        assert m.r(cell(pet+0x34,1140))==power
        uc.reg_write(m.spreg,m.stack)
        uc.emu_start(0x113523c,0x113525f,count=1000)
        assert m.r(cell(pet+0x34,510))==(loyalty&0xffffffff)
        uc.emu_start(0x11354fb,0x113551c,count=1000)
        assert m.r(pet+0x2c)==grade
    phase[0]='quote';m.w(m.stack,m.stop)
    uc.reg_write(m.spreg,m.stack);uc.reg_write(m.cxreg,m.ui)
    uc.emu_start(0x1136290,m.stop,count=30000)
    assert uc.reg_read(m.ipreg)==m.stop
    value=signed(uc.reg_read(UC_X86_REG_EAX))
    subtotal=sum((int(rows[g]['maxloy'])-l)*(45+2*(p%10)) for p,g,l in pets if g in rows)
    # The missing-config probe is separately invalid data: native maxloy=0.
    subtotal+=sum(-l*(45+2*(p%10)) for p,g,l in pets if g not in rows)
    expected=-1 if not pets else -3 if subtotal>0 and role_level<=20 else subtotal
    assert value==expected,(pets,role_level,value,expected)
    assert [r['key'] for r in reads]==[k for _ in pets for k in (510,1140)]+([490] if subtotal>0 else [])
    return {'pets':[{'power':p,'grade':g,'loyalty':l,'pet_wire_sha256':hashlib.sha256(native_pet(p,g,l)[0]).hexdigest()}
                    for p,g,l in pets],
            'role_level':role_level,'native_return':value,'native_subtotal':subtotal,
            'lookups':lookups,'attribute_reads':reads,'arithmetic':steps}


def main():
    archive=PfsArchive(ROOT.parent/'artres/config.pfs');name='autoconfig/knight.gsp.pet.cpetxuemaiconfig.xml'
    raw=archive.read(name);rows={int(r.get('id')):dict(r.attrib) for r in decode(raw)}
    assert {k:int(v['maxloy']) for k,v in rows.items()}=={1:100,2:100,3:125,4:200,5:300,6:400}
    cases=[]
    def add(layer,pets,level=21):
        cases.append({'layer':layer,**quote(tuple(pets),level,rows)})
    for remainder in range(10):
        for deficit in (0,1,20,100):add('ones_digit_x_deficit',((remainder,1,100-deficit),))
    for grade,row in rows.items():add('independent_colour_cap',((9,grade,int(row['maxloy'])-1),))
    for power in (63,64,229,230,1139,1140,2019,2020,52610,52611):
        add('power_not_blood_level',((power,6,399),))
    for level in (0,19,20,21,60,155):
        add('free_gate_positive',((9,1,80),),level)
        add('free_gate_zero',((9,1,100),),level)
    for pets in (((0,1,80),(9,1,80)),((9,1,80),(0,1,80)),
                 ((9,1,80),(52611,6,399)),((9,1,100),(52611,6,399)),
                 ((0,1,80),(1,1,99),(9,4,180)),tuple((i,1,99) for i in range(10))):
        add('multi_pet_sum',pets)
    add('multi_pet_free',((9,1,80),(52611,6,399)),20)
    for level in (0,20,21):add('no_pets',(),level)
    # These are intentionally invalid snapshots, not domain eligibility rules.
    add('invalid_overfull_loyalty',((9,1,101),))
    add('invalid_missing_colour_config',((9,7,1),))
    report={'source_status':'client_verified','passed':len(cases),
            'native_image_sha256':hashlib.sha256(DATA).hexdigest(),
            'source':{'archive':'config.pfs','entry':name,'bytes':len(raw),
                      'crc32':hex(archive.entries[name].crc),'sha256':hashlib.sha256(raw).hexdigest()},
            'rows':rows,'cases':cases,
            'formula':'sum((maxloy(colour)-attr510)*(45+2*(attr1140 signed_remainder 10)))',
            'free_gate':'positive subtotal and role attr490 <=20 returns native sentinel -3; no pets returns -1; zero sum returns0',
            'field_source':{'power':'Pet bean+0x30 -> original113532c..1135373 -> attr1140',
                            'colour':'Pet bean+0x3c -> original11354fb..113551c -> pet+0x2c -> list node+0x34',
                            'loyalty':'Pet bean+0x90 -> original113523c..113525f -> attr510',
                            'level':'role attr490 supplied scalar; threshold branch executes unchanged'},
            'adapters':['map operator[] cell storage only','precise original PFS row lookup only',
                        'original decoded scalar Pet copied into original refresh message layout',
                        'role level/map/list fixtures, not actual world ownership or asset import'],
            'limits':['Original native quote, not original server debit rules','No original GUI, runtime, live DB or deployment',
                      'No blood-level lookup used in quote','Valid matrix only nonnegative power0..52611; negative power C++ remainder outside restored domain',
                      'Missing/overfull cases document native lack of validation, not permission'],
            'production_changed':False,'policy_changed':False}
    evidence=ROOT/'evidence'
    (evidence/'npc-loyalty-quote-native.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    regions=((0x1136290,0x109),(0x113532c,0x47),(0x113523c,0x23),(0x11354fb,0x21),
             (0x89e3b0,0xb),(0xd436fc,0x10),(0x886cea,0x2f),
             (0x1633b13,0x59),(0x1633b7c,0x89))
    with (evidence/'npc-loyalty-quote-native-disassembly.txt').open('w',encoding='utf8') as f:
        with contextlib.redirect_stdout(f):
            for address,size in regions:
                print('\nREGION',hex(address),'BYTES',DATA[address-BASE:address-BASE+size].hex())
                disasm(address,size)
    print('PASS',len(cases),'original loyalty quote cases')


if __name__=='__main__':main()
