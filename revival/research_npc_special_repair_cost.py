"""Independent offline oracle for original tag6..11 repair quotation.

Original EquipObject parser, CItemAttr copy, all scalar getters, x87 power,
special fee arithmetic and signed64 truncation execute unchanged.
"""
import contextlib
from decimal import Decimal,localcontext
import hashlib
import json
from pathlib import Path
import struct

from bxml import decode
from native_inspect import BASE,DATA,disasm,u32
from pfs import PfsArchive
from research_equipment_detail_full import NativeEquipmentDetail,basic_payload

ROOT=Path(__file__).parent
HISTORICAL={
    'research_npc_special_repairs.py':'88bb5258c17a9db8d1dd28324f2528d98b79b16097edb14d5b54b43368452023',
    'evidence/npc-special-repairs-native.json':'8ecc806aab098d8d0e2edac192f57517c1e05f66746e3919ac809f927e8d83dc',
    'evidence/NPC_SPECIAL_REPAIRS_NATIVE_RESEARCH.md':'10a418afe9175882a7dc9712ad126287dd951a77eef88087428e8162cd7044a3',
    'evidence/npc-special-repairs-native-disassembly.txt':'d8c1b02d345911c1e2e5cd74155a827270e3e197e8271780b6051d89402053ed'}


def preserve_history():
    assert all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha for name,sha in HISTORICAL.items())


class SpecialCost:
    def __init__(self,attr):
        from unicorn import UC_HOOK_CODE
        from unicorn.x86_const import UC_X86_REG_EDX
        self.DX=UC_X86_REG_EDX;self.attr=attr
        self.n=NativeEquipmentDetail(int(attr['id']),prefix=5)
        n=self.n;self.wrapper=0x5700000;self.phase='copy';self.events=[]
        n.w(self.wrapper,n.obj);n.w(n.rows[1]+0x24,int(attr['level']))
        self.copy_import=u32(0x22444b4)
        page=self.copy_import&~4095
        if not any(start<=page<=end for start,end,permissions in n.emu.mem_regions()):n.emu.mem_map(page,4096)
        n.emu.hook_add(UC_HOOK_CODE,self.hook)
        sp,cx,ax,ip=n.regs
        n.w(n.stack,n.stop,int(attr['id']));n.emu.reg_write(sp,n.stack);n.emu.reg_write(cx,self.wrapper)
        n.emu.emu_start(0x1080720,n.stop,count=30000)
        assert n.emu.reg_read(ip)==0x10728bb
        assert (n.r(self.wrapper+4),n.r(self.wrapper+8),n.r(self.wrapper+0x28))==(
            int(attr['id']),int(attr['itemtypeid']),int(attr['level']))
        self.copy_events=list(self.events);self.phase='parse'

    def hook(self,uc,a,size,user):
        n=self.n;sp,cx,ax,ip=n.regs;p=uc.reg_read(sp)
        if self.phase=='copy':
            if a==self.copy_import:
                # Host std::wstring copy is irrelevant to the scalar copy chain.
                self.events.append({'adapter':'wstring copy','target':hex(uc.reg_read(cx))});n.ret(4)
            elif a==0x10728bb:
                self.events.append({'id':n.r(self.wrapper+4),'type':n.r(self.wrapper+8),'level':n.r(self.wrapper+0x28)})
                uc.emu_stop()
        elif self.phase=='quote':
            if a==0x89d550:raise AssertionError('Special item entered ordinary fee table')
            elif a in (0x107309e,0x1072de8,0x1072e28,0x1074d3e):
                self.events.append({'native_getter_return':hex(a),'value':uc.reg_read(ax)})
            elif a==0x10dbbb3:
                self.power=struct.unpack('<d',uc.mem_read(p+0x20,8))[0]
                self.factor=struct.unpack('<f',uc.mem_read(p+0x2c,4))[0]
            elif a==0x10dbc0c:self.divisor=n.r(p+0x2c)

    def parse(self,q,current,maximum,score=9999,prefix=5):
        n=self.n;self.phase='parse'
        body=basic_payload(prefix=prefix,score=score,properties=(),current=current,maximum=maximum)
        body=body[:37]+struct.pack('>i',q)+body[41:]
        parsed=n.parse(body)
        assert (parsed['color'],parsed['current'],parsed['maximum'])==(q,current,maximum)
        self.parsed=parsed;self.wire_sha=hashlib.sha256(body).hexdigest()

    def cost(self,method):
        n=self.n;sp,cx,ax,ip=n.regs
        self.phase='quote';self.events=[];self.power=self.factor=None;self.divisor=None
        n.w(n.stack,n.stop,self.wrapper,method);n.emu.reg_write(sp,n.stack)
        n.emu.emu_start(0x10dbb20,n.stop,count=30000)
        assert n.emu.reg_read(ip)==n.stop
        bits=n.emu.reg_read(ax)|(n.emu.reg_read(self.DX)<<32)
        value=bits if bits<1<<63 else bits-(1<<64)
        p=self.parsed;level=int(self.attr['level']);missing=p['maximum']-p['current']
        assert [e['value'] for e in self.events]==[p['color']]*3+[p['maximum'],p['current'],level]
        assert self.factor==(struct.unpack_from('<f',DATA,0x2474050-BASE)[0] if p['color']<=4 else 1.0)
        assert self.divisor==2-int(min(p['color'],4)/4)
        with localcontext() as ctx:
            ctx.prec=80
            expected=int(Decimal(level)*2*Decimal.from_float(self.factor)*missing*Decimal.from_float(self.power)/self.divisor)
        assert value==expected,(value,expected,p,level)
        return {'method':method,'native_signed64_cost':value,'native_power_stored_double':self.power.hex(),
                'factor_float32_as_hex':self.factor.hex(),'divisor':self.divisor,'native_getters':self.events}


def main():
    preserve_history();archive=PfsArchive(ROOT.parent/'artres/config.pfs');sources={};configs={}
    for short in ('citemattr','cequipeffect','cequipprefixconfig','cgodweapon'):
        name=f'autoconfig/knight.gsp.item.{short}.xml';raw=archive.read(name)
        configs[short]={int(r.get('id')):r for r in decode(raw)}
        sources[name]={'bytes':len(raw),'crc32':hex(archive.entries[name].crc),'sha256':hashlib.sha256(raw).hexdigest()}
    # The reused parser's configuration Adapter reads catalogs. Check all of its
    # relevant rows/fields against this batch's freshly verified PFS extraction.
    catalogs={short:{int(r['attributes']['id']):r for r in json.loads((ROOT/f'catalogs/knight.gsp.item.{short}.json').read_text(encoding='utf8'))}
              for short in configs}
    assert set(catalogs['cgodweapon'])==set(configs['cgodweapon'])
    assert catalogs['cequipprefixconfig'][5]['attributes']==dict(configs['cequipprefixconfig'][5].attrib)
    selected=[];counts={}
    for tag in range(6,12):
        group=[r for r in configs['citemattr'].values() if int(r.get('itemtypeid'))&15==8 and (int(r.get('itemtypeid'))>>4)&15==tag]
        counts[tag]=len(group);selected.extend(group[:2])
    results=[];diagnostics=[]
    for row in selected:
        attr=dict(row.attrib);template=int(attr['id']);tag=(int(attr['itemtypeid'])>>4)&15
        assert catalogs['citemattr'][template]['attributes']==attr
        original_effect=configs['cequipeffect'][template]
        assert catalogs['cequipeffect'][template]['attributes']==dict(original_effect.attrib)
        assert catalogs['cequipeffect'][template]['lists']['scorecolor']==[v.text for v in original_effect.find('scorecolor')]
        native=SpecialCost(attr)
        item={'id':template,'name':attr.get('name'),'itemtypeid':int(attr['itemtypeid']),'tag':tag,
              'original_level':int(attr['level']),'original_needLevel':int(attr['needLevel']),
              'original_endurecoef':original_effect.get('endurecoef'),
              'native_config_copy':native.copy_events,'cases':[]}
        for q in range(1,7):
            for current,maximum in ((0,100),(80,100),(100,100)):
                native.parse(q,current,maximum)
                methods=[native.cost(method) for method in (0,1,2)]
                assert len({r['native_signed64_cost'] for r in methods})==1
                item['cases'].append({'wire_color_q':q,'prefix_quality':5,'score':9999,
                                      'current':current,'maximum':maximum,'wire_sha256':native.wire_sha,
                                      'native_parsed_fields':{k:native.parsed[k] for k in ('color','prefix_quality','score','current','maximum')},
                                      'methods':methods})
        results.append(item)
    native=SpecialCost(dict(selected[0].attrib))
    for q,current,maximum,method in ((1,0,0,2),(4,20,20,2),(1,101,100,2),
                                     (0,80,100,2),(7,80,100,2),(6,0,2147483647,2),
                                     (4,80,100,99),(4,80,100,-1)):
        native.parse(q,current,maximum)
        diagnostics.append({'q':q,'current':current,'maximum':maximum,**native.cost(method)})
    assert diagnostics[5]['native_signed64_cost']>0x7fffffff
    sources_field=DATA[0x2251a44-BASE:0x2251a44-BASE+12].decode('utf-16le').rstrip('\0')
    assert sources_field=='level'
    report={'source_status':'client_verified','native_image_sha256':hashlib.sha256(DATA).hexdigest(),
            'historical_96_files_sha256':HISTORICAL,'sources':sources,'original_type_counts':counts,
            'sample_items':results,'diagnostic_cases':diagnostics,
            'passed':sum(len(c['methods']) for i in results for c in i['cases'])+len(diagnostics),
            'formula':'trunc_signed64(level * 2 * factor_f32 * (maximum-current) * native_pow_1_3(q-1)_stored_f64 / (2-trunc(min(q,4)/4)))',
            'q_source':'original EquipObject107d960 wire color scalar -> bean+5c; tag>5 retains it; native1073090',
            'level_source':'original CItemAttr level reader86e95a/86e983 -> record+24 -> native10728af/10728b2 -> wrapper+28 ->1074d10',
            'condition_source':'original EquipObject parser wire current/max -> bean+c8/cc -> native1072dd0/1072e10',
            'adapters':['reused original-parser host CRT/STL string/config lookup Adapters; relevant rows freshly compared to original PFS',
                        'original initializer/copy stops at10728bb after id/type/level; wstring copy host Adapter',
                        'scalar wire q/current/max/prefix/score fixtures, not actual server item generation'],
            'unknown':['special-item condition generation/maxima/time-limit semantics','repair success/failure and max changes',
                       'server eligibility/payment/materials and real NPC binding','currency is not selected by quote function',
                       'full wrapper initialization/GUI and gameplay integration not executed'],
            'production_changed':False,'policy_changed':False}
    out=ROOT/'evidence'
    (out/'npc-special-repair-cost-native.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    regions=((0x10dbb20,0xfa),(0x1073090,0x12),(0x1072dd0,0x19),(0x1072e10,0x19),
             (0x1074d10,0x2f),(0x1073d70,0x30),(0x1919216,0x75),(0x86e95a,0x2c),
             (0x1080720,0x54),(0x1072890,0x2b),(0x107d960,0x1a0),(0x107dc18,0x23d))
    with (out/'npc-special-repair-cost-native-disassembly.txt').open('w',encoding='utf8') as f:
        with contextlib.redirect_stdout(f):
            for a,size in regions:print('\nREGION',hex(a),'BYTES',DATA[a-BASE:a-BASE+size].hex());disasm(a,size)
    preserve_history();print('PASS',report['passed'],'special repair costs; original96 evidence hashes preserved')


if __name__=='__main__':main()
