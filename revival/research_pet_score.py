"""Execute whole original1133e80 with original blood scan and empty extra gear."""
import json
import struct
import hashlib
import zlib
from native_inspect import BASE,DATA
from inspect_client import ROOT,OUT,write_json,catalog_rows
from pfs import PfsArchive
from bxml import decode
from pet_score import ScoreRules
from pet_protocol import growth_wire_float
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP


def main():
    archive=PfsArchive(ROOT/'artres/config.pfs');sources=[]
    for name in ('pet.cpetgradecfg','pet.cpetattr','pet.cpetbloodconfig'):
        filename='knight.gsp.'+name
        raw=archive.read('autoconfig/'+filename+'.xml')
        direct=catalog_rows(decode(raw))
        cached=json.loads((OUT/f'catalogs/{filename}.json').read_text(encoding='utf-8'))
        assert [(r['attributes'],r['lists']) for r in direct]==[(r['attributes'],r['lists']) for r in cached]
        sources.append({'table':filename,'rows':len(direct),'bytes':len(raw),
            'crc32':f'{zlib.crc32(raw)&0xffffffff:08x}','sha256':hashlib.sha256(raw).hexdigest()})
    rules=ScoreRules.load();uc=Uc(UC_ARCH_X86,UC_MODE_32)
    uc.mem_map(0,0x1000);uc.mem_map(BASE,(len(DATA)+0xfff)&~0xfff);uc.mem_write(BASE,DATA)
    uc.mem_map(0x5000000,0x400000)
    pet,root,vt,grade_row,pet_row,blood_row,head,extra_head,stack,stop=(
        0x5300000,0x5302000,0x5304000,0x5306000,0x5306800,0x5307000,0x531f000,0x531f100,0x5108000,0x500f000)
    grade_term,pet_term,blood_term=0x500d000,0x500d010,0x500d020
    def r(a):return struct.unpack('<I',uc.mem_read(a,4))[0]
    def w(a,*v):uc.mem_write(a,struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v)))
    def ret(n,value=0):
        sp=uc.reg_read(UC_X86_REG_ESP);dest=r(sp)
        uc.reg_write(UC_X86_REG_EAX,value);uc.reg_write(UC_X86_REG_ESP,sp+n+4);uc.reg_write(UC_X86_REG_EIP,dest)
    w(0x2945aec,root)
    for off,vtable,terminal in ((0xba4,vt,grade_term),(0xb60,vt+0x100,pet_term),(0xb68,vt+0x200,blood_term)):
        w(root+off,vtable);w(vtable+8,terminal)
    w(pet+0x38,head);w(head,head,head,head)
    w(pet+0xc0,extra_head);w(extra_head,extra_head,extra_head,extra_head)
    bloods={int(r['attributes']['id']):r['attributes'] for r in json.loads((OUT/'catalogs/knight.gsp.pet.cpetbloodconfig.json').read_text(encoding='utf-8'))}
    nodes={};current={};seen=[]
    def hook(uc,address,size,user):
        sp=uc.reg_read(UC_X86_REG_ESP)
        if address==grade_term:
            key=r(sp+4)
            if key>len(rules.rows):ret(4,0);return
            attr,coefficient=rules.rows[key-1];w(grade_row,key,attr);uc.mem_write(grade_row+8,struct.pack('<d',coefficient))
            ret(4,grade_row)
        elif address==pet_term:
            assert r(sp+4)==current['template']
            kind,uselevel=rules.templates[current['template']]
            w(pet_row,current['template']);w(pet_row+0x44,kind,uselevel);ret(4,pet_row)
        elif address==blood_term:
            key=r(sp+4);row=bloods[key]
            w(blood_row,key,int(row['lowpower']),int(row['uppower']),0)
            uc.mem_write(blood_row+0x10,struct.pack('<d',float(row['ratio'])));ret(4,blood_row)
        elif address==0x5f08c0:
            assert uc.reg_read(UC_X86_REG_ECX)==pet+0x34
            out,key=r(sp+4),r(r(sp+8));w(out,pet+0x34,nodes.get(key,head));ret(8,out)
        elif address==0x1919184:ret(0)
    uc.hook_add(UC_HOOK_CODE,hook)
    pets=json.loads((OUT/'catalogs/knight.gsp.pet.cpetattr.json').read_text(encoding='utf-8'))
    for row in pets:
        a=row['attributes'];template=int(a['id']);kind,uselevel=rules.templates[template]
        aptitude=tuple(int(a[n+'aptmin']) for n in ('attack','defend','phyforce','magic','speed'))
        growth=int(row['lists']['growrate'][0])
        for level,insight,learned,stage in ((0,0,(200091,200061),0),(3,73,(200011,200012,200013,200534),2),(3,73,(200011,200012,200013,200534),56)):
            current={'template':template};power=int(bloods[level]['lowpower'])
            attrs=dict(zip((540,550,560,570,580),aptitude))
            attrs.update({590:0,1160:insight,1140:power,1440:stage,1660:0,1670:0,1760:0})
            attrs.update({1170+10*i:sum(v%10==i+1 for v in learned) for i in range(3)})
            nodes={}
            for idx,(key,value) in enumerate(attrs.items()):
                node=0x5310000+idx*0x40;nodes[key]=node;w(node,head,head,head,key,value)
            w(pet+4,template);w(pet+0x2c,1);uc.mem_write(pet+0x30,struct.pack('<f',growth_wire_float(growth)))
            w(stack,stop,pet);uc.reg_write(UC_X86_REG_ECX,root);uc.reg_write(UC_X86_REG_ESP,stack)
            uc.emu_start(0x1133e80,stop,count=200000)
            assert uc.reg_read(UC_X86_REG_EIP)==stop
            actual=uc.reg_read(UC_X86_REG_EAX)
            expected=rules.project(template,aptitude,growth,insight,learned,level,evolution_stage=stage)
            assert actual==expected,(template,actual,expected)
            seen.append({'template':template,'kind':kind,'blood_level':level,'insight':insight,'evolution_stage':stage,'score':actual})
    write_json(OUT/'evidence/pet-score-native.json',{'source_status':'client_verified','original_pfs_sources':sources,'passed':len(seen),'cases':seen,
        'oracle':'whole original1133e80 including real original config getters, original iterator checks, full ordinary blood scan11297d0, kind bonuses and original empty-gear helper functions; final original ftol',
        'adapters':'only original extracted config row terminal and attr-map lookup terminal; no replacement score/blood/rounding algorithm',
        'projection':'pure float32-per-product/accumulation matches raw evolution0/2/56 and original zeros for590/1660/1670/1760 and extra gear; score projection does not authorize these stages for every template',
        'limits':['not complete advanced/equipped/metamorphosed pet score','insight sample73 is input, not original RNG range','no live client/server']})
    print('PASS',len(seen),'whole original score and pure supported wire projection cases')


if __name__=='__main__':main()
