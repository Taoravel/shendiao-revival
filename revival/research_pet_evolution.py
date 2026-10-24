"""Original evolution byte, sparse stage ceiling, shape consumer and request.

No server effects are inferred from a client's presentation or request name.
"""
import hashlib
import json
import struct
import zlib
from native_inspect import BASE,DATA
from native_gameplay_probe import probe
from inspect_client import ROOT,OUT,write_json,catalog_rows
from pfs import PfsArchive
from bxml import decode
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_EBX,UC_X86_REG_ECX,UC_X86_REG_EDI,UC_X86_REG_EDX,UC_X86_REG_EBP,UC_X86_REG_ESI,UC_X86_REG_ESP,UC_X86_REG_EIP


class NativeEvolution:
    def __init__(self):
        self.uc=uc=Uc(UC_ARCH_X86,UC_MODE_32)
        uc.mem_map(0,0x1000)
        uc.mem_map(BASE,(len(DATA)+0xfff)&~0xfff);uc.mem_write(BASE,DATA)
        uc.mem_map(0x5000000,0x400000)
        self.pet,self.root,self.row,self.attr,self.stack,self.stop=(0x5300000,0x5302000,0x5306000,0x5308000,0x5108000,0x500f000)
        self.rows={int(r['attributes']['id']):r for r in json.loads((OUT/'catalogs/knight.gsp.pet.cpetevolution.json').read_text(encoding='utf-8'))}
        self.pets={int(r['attributes']['id']):r['attributes'] for r in json.loads((OUT/'catalogs/knight.gsp.pet.cpetattr.json').read_text(encoding='utf-8'))}
        self.w(0x2945aec,self.root)
        for off,vt,terminal in ((0xb94,0x5303000,0x500d000),(0xb60,0x5303100,0x500d010)):
            self.w(self.root+off,vt);self.w(vt+8,terminal)
        uc.hook_add(UC_HOOK_CODE,self.hook)

    def r(self,a):return struct.unpack('<I',self.uc.mem_read(a,4))[0]
    def w(self,a,*v):self.uc.mem_write(a,struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v)))
    def ret(self,n,value):
        uc=self.uc;sp=uc.reg_read(UC_X86_REG_ESP);target=self.r(sp)
        uc.reg_write(UC_X86_REG_EAX,value);uc.reg_write(UC_X86_REG_ESP,sp+4+n);uc.reg_write(UC_X86_REG_EIP,target)
    def hook(self,uc,address,size,user):
        sp=uc.reg_read(UC_X86_REG_ESP)
        if address==0x500d000:
            assert self.r(sp+4)==self.template
            self.ret(4,self.row)
        elif address==0x500d010:
            assert self.r(sp+4)==self.template
            self.w(self.row+0x200,self.template);self.w(self.row+0x244,int(self.pets[self.template]['kind']))
            self.ret(4,self.row+0x200)
        elif address==0x4e8e00:
            key=self.r(self.r(sp+4));assert key in (1440,490)
            self.ret(4,self.attr+(4 if key==490 else 0))
        elif address==0x5f08c0:
            assert uc.reg_read(UC_X86_REG_ECX)==self.pet+0x34 and self.r(self.r(sp+8))==1440
            out=self.r(sp+4);head=0x530b000;self.w(self.pet+0x38,head);self.w(out,self.pet+0x34,head+0x40)
            self.ret(8,out)
        elif address==0x837060:
            self.label_key=self.r(sp+8);self.ret(0,self.r(sp+4))
        elif address in (0x1130ce0,0x1919292):
            raise AssertionError('Unrestored special shape or original assertion reached')

    def setup(self,template,stage=0):
        self.template=template;row=self.rows[template];self.w(self.row,template,int(row['attributes']['totalShape']))
        for number,name in enumerate(('needlevel','needitemnum','shape')):
            values=tuple(map(int,row['lists'][name]));begin=self.row+0x400+number*0x100
            self.w(begin,*values);self.w(self.row+8+number*0x10,0,begin,begin+4*len(values),begin+4*len(values))
        self.w(self.pet+4,template);self.w(self.attr,stage)
        self.w(self.stack,self.stop,self.pet)
        self.uc.reg_write(UC_X86_REG_ESP,self.stack)
        self.uc.reg_write(UC_X86_REG_ECX,self.pet)

    def maximum(self,template):
        self.setup(template)
        self.uc.emu_start(0x1130640,self.stop,count=10000)
        assert self.uc.reg_read(UC_X86_REG_EIP)==self.stop
        return self.uc.reg_read(UC_X86_REG_EAX)

    def maximum_ui(self,template,stage):
        self.setup(template,stage)
        self.uc.emu_start(0x1130b20,self.stop,count=10000)
        assert self.uc.reg_read(UC_X86_REG_EIP)==self.stop
        return self.uc.reg_read(UC_X86_REG_EAX)

    def shape(self,template,stage):
        assert int(self.pets[template]['kind'])!=2
        self.setup(template,stage)
        self.uc.emu_start(0x1138370,self.stop,count=20000)
        assert self.uc.reg_read(UC_X86_REG_EIP)==self.stop
        return self.r(self.pet+0xb0)

    def next_ordinary(self,template,stage):
        """Actual UI next-index, level comparison, pill type and table count."""
        self.setup(template,stage);self.w(self.attr+4,150);self.w(self.stack+0x18,self.row)
        self.uc.reg_write(UC_X86_REG_ESI,self.pet);self.uc.reg_write(UC_X86_REG_EBP,stage)
        self.uc.emu_start(0x14063bc,0x1406591,count=10000)
        assert self.uc.reg_read(UC_X86_REG_EIP)==0x1406591
        return self.uc.reg_read(UC_X86_REG_EBP),self.r(self.stack+0x14),self.r(self.stack+0x18)

    def label(self,template,stage):
        maximum=self.maximum(template)
        self.setup(template,stage);self.w(self.stack+0xd8,stage)
        self.uc.reg_write(UC_X86_REG_EAX,maximum)
        self.uc.emu_start(0x113a6bc,0x113a6e3,count=1000)
        return self.label_key


def native_stage(payload):
    result=[]
    def observe(uc,message):
        pet,cell,stack=0x5300000,0x5302000,0x5108000
        def r(a):return struct.unpack('<I',uc.mem_read(a,4))[0]
        def hook(uc,address,size,user):
            if address==0x4e8e00:
                sp=uc.reg_read(UC_X86_REG_ESP)
                assert r(r(sp+4))==1440
                uc.reg_write(UC_X86_REG_EAX,cell);uc.reg_write(UC_X86_REG_EIP,r(sp));uc.reg_write(UC_X86_REG_ESP,sp+8)
        handle=uc.hook_add(UC_HOOK_CODE,hook)
        for reg,value in ((UC_X86_REG_ESI,message),(UC_X86_REG_EBX,pet),(UC_X86_REG_EDI,pet+0x34),(UC_X86_REG_ESP,stack)):
            uc.reg_write(reg,value)
        uc.emu_start(0x1135373,0x1135390,count=100)
        result.append(struct.unpack('<i',uc.mem_read(cell,4))[0]);uc.hook_del(handle)
    probe(0xf9d7b0,0xf9d840,0xf9d880,payload=payload,observer=observe)
    return result[0]


def main():
    archive=PfsArchive(ROOT/'artres/config.pfs');sources=[]
    for table in ('pet.cpetevolution','pet.cpetattr','pet.cpetfinal','message.cstringres'):
        raw=archive.read('autoconfig/knight.gsp.'+table+'.xml')
        direct=catalog_rows(decode(raw));cached=json.loads((OUT/f'catalogs/knight.gsp.{table}.json').read_text(encoding='utf-8'))
        assert [(r['attributes'],r['lists']) for r in direct]==[(r['attributes'],r['lists']) for r in cached]
        sources.append({'table':table,'rows':len(direct),'crc32':f'{zlib.crc32(raw)&0xffffffff:08x}','sha256':hashlib.sha256(raw).hexdigest()})
    native=NativeEvolution();cases=[];shapes=[];plans=[]
    from pet_evolution import EvolutionRules,PetEvolution
    pure=EvolutionRules.load()
    for template,row in native.rows.items():
        levels=tuple(map(int,row['lists']['needlevel']))
        expected=levels.index(-1)-1 if levels[-1]==-1 else len(levels)-1
        maximum=native.maximum(template);assert maximum==expected
        assert all(native.maximum_ui(template,stage)==maximum for stage in (0,maximum,maximum+1))
        cases.append({'template':template,'maximum_raw_stage':maximum,'totalShape':int(row['attributes']['totalShape']),'needlevel':levels})
        if int(native.pets[template]['kind'])==2:continue
        for stage in range(maximum):
            if stage and (levels[stage]<=0 or int(row['lists']['shape'][stage])<=0):continue
            target,item,count=native.next_ordinary(template,stage)
            plan=pure.plan(template,PetEvolution(0,stage),150)
            assert (plan.stage,*plan.costs[0])==(target,item,count)
            plans.append({'template':template,'stage':stage,'next':target,'item':item,'quantity':count})
        for stage in range(7):
            shape=native.shape(template,stage)
            assert shape==int(row['lists']['shape'][min(stage,maximum)])
            label=native.label(template,stage);assert label==2485+min(stage,maximum)
            shapes.append({'template':template,'raw_stage':stage,'shape':shape,'label_cstring':label})
    assert next(r for r in cases if r['template']==500050)['maximum_raw_stage']==6
    assert native.shape(500050,3)==0 and native.shape(500050,6)==46076
    stores=[]
    for stage in (0,1,2,6,127,255):
        record,_=probe(0xf89ba0,0xf5df70,0xf5f1f0,{4:struct.pack('<i',500001),8:struct.pack('<i',7),0x110:bytes([stage])})
        actual=native_stage(record);assert actual==(stage if stage<128 else stage-256)
        stores.append({'input_byte':stage,'original_attr1440':actual})
    sends=[]
    for pet in (1,7,0x7fffffff):
        native.w(native.stack,0);native.uc.reg_write(UC_X86_REG_ESP,native.stack);native.uc.reg_write(UC_X86_REG_EAX,pet)
        native.uc.emu_start(0x1402070,0x1402084,count=100)
        assert tuple(native.r(native.stack+8+4*i) for i in range(3))==(0x227aeec,0xc07fc,pet)
        body,_=probe(0xdbcda0,0xe536d0,0xdbcdd0,{8:struct.pack('<i',pet)},factory=True)
        assert body==struct.pack('>i',pet)
        sends.append({'pet':pet,'body':body.hex()})
    write_json(OUT/'evidence/pet-evolution-native.json',{'source_status':'client_verified','original_pfs_sources':sources,
        'ceiling_cases':cases,'shape_cases':shapes,'ordinary_next_cases':plans,'signed_byte_stores':stores,'actual_send_cases':sends,
        'oracle':'whole1130640 shape ceiling and whole1130b20 UI ceiling (3 raw stages per template), whole1138370 ordinary shape, actual14063bc..1406591 next-index/level/pill/count and113a6bc..113a6e3 CString2485+min(raw,cap) selection; actual89e2d0/b94 and89e280/b60 getters; extracted table, attr-map and CString lookup terminals only',
        'storage':'original Pet bean+110 signedbyte -> raw SRefresh+118 -> original1135373..113538e attr1440; distinct adjacent cake+111/1540',
        'request':'actual1402070..1402084 current pet key and original CReqPetEvolve factory/marshal/unmarshal; business phase/eligibility and material debit not inferred',
        'sparse':'maximum may6 despite missing intermediate needlevels/shapes; ordinary shape helper can select0 for a gap, so caller must not authorize every raw stage',
        'limits':['not server eligibility/cost/growth/success algorithm','kind2 shape1130ce0 not replaced with ordinary rule','no live server/client/GUI']})
    print('PASS',len(cases),'original evolution ceilings,',len(shapes),'ordinary shapes,',len(plans),'actual next/pill/count plans,6 signed stores and3 confirm requests')


if __name__=='__main__':main()
