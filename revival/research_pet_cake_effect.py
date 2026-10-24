"""Offline whole original cake prediction with actual blood/config/float arithmetic."""
import json
import struct
import hashlib
import zlib
from native_inspect import BASE,DATA
from inspect_client import ROOT,OUT,write_json,catalog_rows
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP


class NativeCake:
    def __init__(self):
        uc=self.uc=Uc(UC_ARCH_X86,UC_MODE_32)
        uc.mem_map(0,0x1000);uc.mem_map(BASE,(len(DATA)+0xfff)&~0xfff);uc.mem_write(BASE,DATA)
        uc.mem_map(0x5000000,0x400000)
        self.root,self.vt,self.manager,self.head,self.node=0x5300000,0x5304000,0x5306000,0x5308000,0x5309000
        self.pet=self.node+8;self.stack=0x5108000;self.stop=0x500f000
        self.grade_row,self.pet_row,self.blood_row,self.cake_row=0x530b000,0x530c000,0x530d000,0x530e000
        self.gain_out,self.name_out=0x530f000,0x530f010
        self.w(0x2945aec,self.root);self.w(0x2944550,self.manager)
        self.terminals={}
        for i,(off,name) in enumerate(((0xb60,'pet'),(0xb68,'blood'),(0xb78,'cake'),(0xc1c,'grade'))):
            vt=self.vt+i*0x100;term=0x500d000+i*0x10
            self.w(self.root+off,vt);self.w(vt+8,term);self.terminals[term]=name
        self.w(self.manager+0x27c,self.head);self.w(self.head,self.node);self.w(self.node,self.head)
        def rows(name):return {int(r['attributes']['id']):r['attributes'] for r in json.loads(
            (OUT/f'catalogs/knight.gsp.{name}.json').read_text(encoding='utf-8'))}
        self.pets=rows('pet.cpetattr');self.bloods=rows('pet.cpetbloodconfig')
        self.cakes=rows('pet.cpetcake');self.grades=rows('pet.cpetxuemaiconfig')
        uc.hook_add(UC_HOOK_CODE,self.hook)

    def r(self,a):return struct.unpack('<I',self.uc.mem_read(a,4))[0]
    def w(self,a,*v):self.uc.mem_write(a,struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v)))
    def ret(self,n,value=0):
        sp=self.uc.reg_read(UC_X86_REG_ESP);dest=self.r(sp)
        self.uc.reg_write(UC_X86_REG_EAX,value);self.uc.reg_write(UC_X86_REG_ESP,sp+n+4);self.uc.reg_write(UC_X86_REG_EIP,dest)

    def hook(self,uc,address,size,user):
        sp=uc.reg_read(UC_X86_REG_ESP)
        if address in (0x1137a75,0x1137b37,0x1137b99,0x1137ba1,0x1137bae):
            self.trace[hex(address)]=uc.reg_read(UC_X86_REG_EAX)
        if address==0x4e8e00:
            assert uc.reg_read(UC_X86_REG_ECX)==self.pet+0x34
            key=self.r(self.r(sp+4));cell=0x5310000+key*4
            self.w(cell,self.attrs.get(key,0));self.ret(4,cell)
        elif address in self.terminals:
            name=self.terminals[address];key=self.r(sp+4)
            if name=='pet':
                assert key==self.current_template
                row=self.pets[key];self.w(self.pet_row,key);self.w(self.pet_row+0x44,int(row['kind']),int(row['uselevel']))
                for i,n in enumerate(('attack','defend','phyforce','magic','speed')):
                    self.w(self.pet_row+0x5c+i*8,int(row[n+'aptmin']),int(row[n+'aptmax']))
                self.ret(4,self.pet_row)
            elif name=='blood':
                row=self.bloods.get(key)
                if row is None:self.w(self.blood_row,-1);self.ret(4,self.blood_row);return
                self.w(self.blood_row,key,int(row['lowpower']),int(row['uppower']),0)
                uc.mem_write(self.blood_row+0x10,struct.pack('<d',float(row['ratio'])));self.ret(4,self.blood_row)
            elif name=='grade':
                self.w(self.grade_row,key);self.w(self.grade_row+0x80,int(self.grades[key]['maxstarnum']));self.ret(4,self.grade_row)
            elif name=='cake':
                self.cake_queries.append(key);row=self.cakes.get(key)
                if row is None:self.w(self.cake_row,-1,0,0)
                else:self.w(self.cake_row,key,int(row['ratio']),int(row['percentage']))
                self.ret(4,self.cake_row)

    def predict(self,template,item,aptitudes,*,power=0,grade=1,count=0,stone=(0,)*5):
        self.current_template=template;self.cake_queries=[];self.trace={}
        self.attrs={1540:count,1140:power,1760:0}
        self.attrs.update(dict(zip((540,550,560,570,580),aptitudes)))
        self.attrs.update(dict(zip((1940,1950,1960,1970,1980),stone)))
        self.w(self.pet,7,template);self.w(self.pet+0x2c,grade)
        self.w(self.gain_out,0);self.w(self.name_out,0)
        self.w(self.stack,self.stop,7,item,self.gain_out,self.name_out)
        self.uc.reg_write(UC_X86_REG_ECX,self.manager);self.uc.reg_write(UC_X86_REG_ESP,self.stack)
        self.uc.emu_start(0x1137870,self.stop,count=300000)
        assert self.uc.reg_read(UC_X86_REG_EIP)==self.stop
        signed=lambda a:struct.unpack('<i',self.uc.mem_read(a,4))[0]
        return {'error':self.uc.reg_read(UC_X86_REG_EAX),'gain':signed(self.gain_out),
                'attribute_name_string':signed(self.name_out),'cake_rows':tuple(self.cake_queries),'trace':dict(self.trace)}


def main():
    from pfs import PfsArchive
    from bxml import decode
    archive=PfsArchive(ROOT/'artres/config.pfs');sources=[]
    for name in ('pet.cpetattr','pet.cpetcake','pet.cpetbloodconfig','pet.cpetxuemaiconfig'):
        raw=archive.read('autoconfig/knight.gsp.'+name+'.xml')
        direct=catalog_rows(decode(raw))
        cached=json.loads((OUT/f'catalogs/knight.gsp.{name}.json').read_text(encoding='utf-8'))
        assert [(r['attributes'],r['lists']) for r in direct]==[(r['attributes'],r['lists']) for r in cached]
        sources.append({'table':name,'rows':len(direct),'crc32':f'{zlib.crc32(raw)&0xffffffff:08x}',
            'sha256':hashlib.sha256(raw).hexdigest()})
    oracle=NativeCake();cases=[];mismatches=[];passed=0;rounding_differences=0;digest=hashlib.sha256()
    from pet_cake_effects import EffectRules
    from pet_blood import BloodRules,PetBlood
    from pet_growth import Profile
    from dataclasses import replace
    pure=EffectRules.load()
    blood_rules=BloodRules.load()
    for template,row in oracle.pets.items():
        for level in range(16):
            power=int(oracle.bloods[level]['lowpower']);blood=blood_rules.progress(PetBlood(0,power),6)
            for style in ('min','mid','max'):
                aptitudes=tuple(int(row[n+'aptmin']) if style=='min' else int(row[n+'aptmax']) if style=='max'
                    else (int(row[n+'aptmin'])+int(row[n+'aptmax']))//2 for n in ('attack','defend','phyforce','magic','speed'))
                profile=Profile(template,1000,aptitudes)
                effective=blood_rules.effective_profile(profile,blood).aptitudes
                for i in range(5):
                    result=oracle.predict(template,31268+i,effective,power=power,grade=6)
                    ratio=int(float(oracle.bloods[blood.level]['ratio'])*1000.0)
                    predicted=pure.predict(template,31268+i,effective,ratio,0)
                    assert predicted.error==result['error'],(template,style,level,i,predicted,result)
                    if not predicted.error:
                        assert predicted.client_gain==result['gain'],(template,style,level,i,predicted,result)
                        assert predicted.base_gain==result['trace'].get('0x1137b99',0)
                    record={'template':template,'style':style,'level':level,'item':31268+i,'aptitudes':aptitudes,
                        'effective':effective,**result}
                    digest.update(json.dumps(record,sort_keys=True).encode());passed+=1
                    if len(cases)<40 or template in (500069,500118) and level in (0,15) and style=='mid':cases.append(record)
                    if not predicted.error and predicted.client_gain>0:
                        after=list(aptitudes);after[i]+=predicted.base_gain
                        actual=blood_rules.effective_profile(replace(profile,aptitudes=tuple(after)),blood).aptitudes[i]-effective[i]
                        if actual!=predicted.client_gain:
                            rounding_differences+=1
                            if len(mismatches)<24:mismatches.append(dict(record,base_gain=predicted.base_gain,actual_gain=actual))
    assert passed==158*16*3*5
    for count in (19,20):
        result=oracle.predict(500001,31268,(1130,1235,960,657,1122),count=count)
        assert result['error']==(145133 if count==20 else 0)
    write_json(OUT/'evidence/pet-cake-effect-native.json',{
        'source_status':'client_verified','scope':'original client prediction only; server application is separately designed','passed':passed,'original_pfs_sources':sources,
        'oracle':'whole original1137870 incl actual pet-list scan, original CPetAttr getters, full112c090/11297d0 ordinary blood projection and full cake arithmetic/ftol; only attr cell and original extracted table lookup terminals',
        'matrix':'158templates*16 ordinary blood levels*min/mid/max*5named cakes; rejection errors and all nonerror gain/base steps match pure projection',
        'case_digest_sha256':digest.hexdigest(),'samples':cases,'current_rational_blood_rounding_difference_count':rounding_differences,
        'rounding_examples':mismatches,'limits':['native UI prediction is not an observed server formula',
            'nonzero spirit-stone/1760/evolution advanced projections still separate',
            'max rejection produces garbage negative gain internally; no such gain is an eligible effect',
            'rational current blood authority may yield1 different point, explicitly retained and audited rather than hidden policy migration',
            'no live client/server']})
    print('PASS',passed,'whole original cake predictions; current rational blood boundary differences',rounding_differences)


if __name__=='__main__':main()
