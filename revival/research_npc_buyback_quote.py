"""Original buyback quote against one actual captured published server frame.

Offline only. Writes this batch's JSON/disassembly; no old probe main runs.
"""
from contextlib import redirect_stdout
from fractions import Fraction
import hashlib
import io
import json
from pathlib import Path
import struct

from bxml import decode
from native_gameplay_probe import probe
from native_inspect import BASE, DATA, disasm, u32
from pfs import PfsArchive
from research_npc_submenu import Machine

ROOT=Path(__file__).resolve().parent
CAPTURE='evidence/npc-buyback-current-price-frame.json'
PRODUCER='staging/capture_npc_buyback_price_frame.py'
PREVIOUS=('research_npc_shop_catalog.py','evidence/NPC_SHOP_CATALOG_NATIVE_RESEARCH.md',
          'evidence/npc-shop-catalog-native.json','evidence/npc-shop-catalog-disassembly.txt')
SEALED={
 PREVIOUS[0]:'fd3f5dc3feac5c532a35251c59cb38daa98e7b68ab757c734d1ebbe3390033ea',
 PREVIOUS[1]:'0b7622cba029fcad6e0bd34bfde696ca6dc115b99dd30d131ceb5d4da0677c0c',
 PREVIOUS[2]:'ddeddb4a860377559cb3a5f60ddc2c2ae73922757d9b878ad93d793257a07c5b',
 PREVIOUS[3]:'65f618d1113e4f75bc6ec0c3b4778d8f05a26da7c8044960632e6cc08329b5e2',
 PRODUCER:'0be40588f04796ef72aee299520455251c98478dfd47c5015b05f06044fbf34c',
 CAPTURE:'ea45ec31e266eafc39699ee77797f53c59c28d7a2932a8bffbefbcc1b7f13955',
 'evidence/npc-equipment-identification-ready.json':'9b05ab14fd786558a2e320a70ae5a9579b578b3c4170ecb241fac8e2bab98794',
 'evidence/npc-placement-direction-ready.json':'761c97193b18d92e860aa8cbfeac045a34d9c10057c792d586b0484c7df62d82',
 'evidence/npc-repair-column-candidate-ready.json':'9e297b2f66678c2a198492a3240ec72cf3d7bf4659531427e5d759582b5e1543',
 'staging/npc-repair-column-candidate-v1/npc_repairs.py':'e648d4f977a58d774d670e606a0f72e722c657e17f66f50413ff9170d227dd9b'}
BLOCKS=((0x89e210,0xb),(0xc983be,0x10),(0x884250,0x60),(0x8842d0,0xa),
        (0x8840a0,0x187),(0x10a4b44,0x51),(0x81a760,0x90),(0x10817bc,0x10),
        (0x1103504,0x40),(0x19191e0,0xc2),(0x110224a,0x25),
        (0x1102b6a,0x16),(0x110416c,0x22),(0x11090c0,0xb7),(0x1109d6c,0x73))


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze():
    previous=json.loads((ROOT/PREVIOUS[2]).read_text(encoding='utf8'))
    names=set(previous['input_sha256_after'])|set(SEALED)|{
      Path(__file__).name,'catalogs/knight.gsp.npc.citemsell.json'}
    return {name:sha(ROOT/name) for name in sorted(names)}


def table_source():
    archive=PfsArchive(ROOT.parent/'artres/config.pfs')
    entry='autoconfig/knight.gsp.npc.citemsell.xml';raw=archive.read(entry);xml=decode(raw)
    assert all(not list(row) for row in xml)
    projection=[{'attributes':dict(row.attrib),'lists':{}} for row in xml]
    cached=json.loads((ROOT/'catalogs/knight.gsp.npc.citemsell.json').read_text(encoding='utf8'))
    assert projection==[{'attributes':r['attributes'],'lists':r['lists']} for r in cached]
    rows={int(r['attributes']['id']):r['attributes'] for r in projection}
    assert rows[32000]==dict(id='32000',buyprice='150',sellprice='75',moneytype='2',sellnpc='10011',ifshow='0')
    assert 40200 not in rows and 40204 not in rows
    col=u32(0x225c2bc-4);ti=u32(col+12)
    rtti=DATA[ti+8-BASE:ti+180-BASE].split(b'\0')[0].decode('ascii')
    assert rtti=='.?AVknight_gsp_npc_Citemsell_table_implement@XMLCONFIG@@'
    return rows,{'entry':entry,'archive':'artres/config.pfs','bytes':len(raw),
       'crc32':hex(archive.entries[entry].crc),'sha256':hashlib.sha256(raw).hexdigest(),
       'rows':len(projection),'full_attributes_and_lists_equal':True,
       'buyprice_distribution':{'positive':sum(int(row['buyprice'])>0 for row in rows.values()),
          'zero':sum(int(row['buyprice'])==0 for row in rows.values()),
          'negative':sum(int(row['buyprice'])<0 for row in rows.values())},
       'wrapper_vtable':'0x225c2bc','wrapper_rtti':rtti,'member':'ConfigManager+0xb28',
       'selected_rows':{str(i):rows.get(i) for i in (40200,40204,32000)}}


def parse_original_row(row):
    """Entire generated native field reader, with XML/string host adapters."""
    m=Machine();record,node=0x5010000,0x5011000
    ctor,dtor=(u32(p) for p in (0x22443f0,0x22443ec))
    for page in {a&~4095 for a in (ctor,dtor)}:
        if BASE<=page<BASE+len(DATA):continue
        try:m.uc.mem_map(page,4096)
        except Exception:pass
    calls=[]
    def hook(uc,a,size,user):
        sp=uc.reg_read(m.spreg)
        if a==ctor:
            ptr=m.r(sp+4);raw=bytearray()
            while bytes(uc.mem_read(ptr+len(raw),2))!=b'\0\0':raw+=uc.mem_read(ptr+len(raw),2)
            m.string(uc.reg_read(m.cxreg),raw.decode('utf-16le'),0x5020000);m.ret(uc.reg_read(m.cxreg),4)
        elif a==dtor:m.ret()
        elif a==0x409ce0:
            assert uc.reg_read(m.cxreg)==node
            name=m.read_string(m.r(sp+4));default=m.r(sp+8)
            value=int(row.get(name,default));calls.append((name,value));m.ret(value,8)
        elif a==0x1919184:m.ret()
    m.w(m.stack,m.stop,record,node);m.run(0x8840a0,hook)
    values=struct.unpack('<6i',bytes(m.uc.mem_read(record,24)))
    expected=tuple(int(row[k]) for k in ('id','buyprice','sellprice','moneytype','sellnpc','ifshow'))
    assert values==expected and tuple(k for k,v in calls)==('id','buyprice','sellprice','moneytype','sellnpc','ifshow')
    return bytes(m.uc.mem_read(record,24)),{'source_id':int(row['id']),'native_fields':dict(zip(('id@0','buyprice@4','sellprice@8','moneytype@c','sellnpc@10','ifshow@14'),values)),'xml_reads':calls}


def conversion_case(price,quantity,fpcw,cpu_flag):
    from unicorn.x86_const import UC_X86_REG_ESI,UC_X86_REG_FPCW,UC_X86_REG_EAX
    m=Machine();wrapper,obj,entry=0x5010000,0x5011000,0x5012000
    m.w(wrapper,obj);m.w(wrapper+0x7c,price);m.w(obj+0x28,quantity);m.w(entry,wrapper)
    m.w(0x29b8ef8,cpu_flag);m.w(m.stack,m.stop)
    m.uc.reg_write(UC_X86_REG_FPCW,fpcw);m.uc.reg_write(UC_X86_REG_ESI,entry)
    paths=[]
    def hook(uc,a,size,user):
        if a in (0x19191e9,0x1919216):paths.append(hex(a))
        elif a==0x110351c:uc.emu_stop()
    m.run(0x1103504,hook)
    result=m.uc.reg_read(UC_X86_REG_EAX)
    assert result==int(Fraction(price*quantity*11,10))
    assert paths==[hex(0x19191e9 if cpu_flag else 0x1919216)]
    return dict(price=price,quantity=quantity,fpcw=hex(fpcw),cpu_flag=cpu_flag,native_result=result,conversion_entry=paths[0])


def frame_quotes(capture,table_rows,parsed):
    from unicorn import UC_HOOK_CODE
    from unicorn.x86_const import (UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP,
      UC_X86_REG_ESI,UC_X86_REG_EBP,UC_X86_REG_EBX,UC_X86_REG_EDI,UC_X86_REG_EAX,UC_X86_REG_FPCW)
    wire=bytes.fromhex(capture['body_hex']);assert hashlib.sha256(wire).hexdigest()==capture['body_sha256']
    results=[]
    def observer(uc,message):
        def r(a):return struct.unpack('<I',uc.mem_read(a,4))[0]
        def w(a,*v):uc.mem_write(a,struct.pack('<'+'I'*len(v),*v))
        def execute(start,end,ecx=0,sp=0x5100000):
            w(sp,0x500f000);uc.reg_write(UC_X86_REG_ESP,sp);uc.reg_write(UC_X86_REG_ECX,ecx)
            uc.emu_start(start,end,count=100000)
            assert uc.reg_read(UC_X86_REG_EIP)==end
        begin,end=r(message+0x20),r(message+0x24);assert end-begin==3*64
        w(0x5003000-8,0);w(0x5100000,0x500f000,0x5002000)
        uc.reg_write(UC_X86_REG_ESP,0x5100000);uc.reg_write(UC_X86_REG_ECX,message)
        uc.emu_start(0xef65b0,0x500f000,count=1000000)
        assert bytes(uc.mem_read(0x5003000,r(0x5003000-8)))==wire
        for index,source in enumerate(capture['raw_item_records']):
            bean=begin+64*index;template=r(bean+4);key=r(bean+12);quantity=r(bean+32)
            assert (template,key,quantity)==(source['template'],source['key'],source['quantity'])
            wrapper,obj,entry,row,ui,cell,manager,backend,backendvt,lookup,cfg,missing,frame,items,tab1,tab2=(0x5310000+i*0x1000 for i in range(16))
            w(wrapper,obj,template);w(entry,wrapper)
            # Preserve the actual decoded bean with original copy/property instructions.
            w(0x5100000,0x500f000,bean)
            uc.reg_write(UC_X86_REG_ESP,0x5100000);uc.reg_write(UC_X86_REG_ECX,obj+8)
            uc.emu_start(0x81a760,0x500f000,count=10000)
            uc.reg_write(UC_X86_REG_ESI,wrapper);uc.reg_write(UC_X86_REG_EBX,bean);uc.reg_write(UC_X86_REG_EDI,4)
            execute(0x10817bc,0x10817cc)
            assert tuple(r(obj+n) for n in (0xc,0x14,0x28,0x48,0x4c))==(template,key,quantity,source['position'],4)
            w(0x5100000+0x48,message+0x30)
            uc.reg_write(UC_X86_REG_ESI,bean+12);uc.reg_write(UC_X86_REG_EBP,wrapper)
            execute(0x10a4b44,0x10a4b95)
            raw_price=r(wrapper+0x7c);assert raw_price==capture['raw_price_map'][str(key)]
            w(0x2945aec,manager);w(manager+0xb28,0x225c2bc,backend);w(backend,backendvt);w(backendvt+8,lookup)
            uc.mem_write(cfg,parsed);w(missing,0xffffffff)
            observed={'lookup_keys':[],'conversion_entries':[]}
            def lookup_hook(emu,a,size,user):
                if a==lookup:
                    sp=emu.reg_read(UC_X86_REG_ESP);asked=r(sp+4);observed['lookup_keys'].append(asked)
                    assert asked==template
                    result=cfg if asked in table_rows else missing
                    assert (asked in table_rows)==(template==32000)
                    emu.reg_write(UC_X86_REG_EAX,result);emu.reg_write(UC_X86_REG_ESP,sp+8);emu.reg_write(UC_X86_REG_EIP,r(sp))
                elif a==0x110351c:observed['default_native_quote']=emu.reg_read(UC_X86_REG_EAX)
                elif a in (0x19191e9,0x1919216):observed['conversion_entries'].append(hex(a))
            token=uc.hook_add(UC_HOOK_CODE,lookup_hook)
            w(0x29b8ef8,u32(0x29b8ef8));uc.reg_write(UC_X86_REG_FPCW,0x027f)
            uc.reg_write(UC_X86_REG_ESI,entry)
            execute(0x1103504,0x1103544)
            uc.hook_del(token)
            final=r(0x5100000+0x14)
            assert observed['lookup_keys']==[template]
            assert observed['default_native_quote']=={40200:275,40204:7700,32000:330}[template]
            assert final=={40200:275,40204:7700,32000:300}[template]
            # Original mode0 branch consumes the computed pointer, and stores row price.
            w(frame+0xc,0);w(frame+0x10,0x5100000+0x14)
            uc.reg_write(UC_X86_REG_EBP,frame);uc.reg_write(UC_X86_REG_ESI,row);uc.reg_write(UC_X86_REG_EDI,0xffffffff)
            execute(0x110224a,0x1102b80)
            assert r(row+0x18)==final
            w(row,cell);w(cell+0x278,wrapper)
            # Original select tail sets this row and UI quantity=1. Highlight is GUI only.
            uc.reg_write(UC_X86_REG_ESI,ui);uc.reg_write(UC_X86_REG_EDI,row);uc.reg_write(UC_X86_REG_EBX,0)
            def highlight(emu,a,size,user):
                if a==0x1102e10:
                    sp=emu.reg_read(UC_X86_REG_ESP)
                    emu.reg_write(UC_X86_REG_ESP,sp+8);emu.reg_write(UC_X86_REG_EIP,r(sp))
            token=uc.hook_add(UC_HOOK_CODE,highlight)
            execute(0x110416c,0x110418e);uc.hook_del(token)
            assert r(ui+0xc8)==row and r(ui+0xd8)==1
            w(ui+0x34,tab1,tab2);uc.mem_write(tab1+0x530,b'\0');uc.mem_write(tab2+0x530,b'\1')
            w(0x2944628,items)
            debit=next(d['actual_cash_debit'] for d in capture['actual_repurchase_debits'] if d['key']==key)
            guard_cases=[]
            for cash in (debit,final-1,final,capture['actual_wallet_after']['cash']):
                w(items+0xb0,cash,0);seen=[]
                def guard(emu,a,size,user):
                    if a in (0x1109d96,0x1109dab):
                        seen.append((a,emu.reg_read(UC_X86_REG_EDI)));emu.emu_stop()
                token=uc.hook_add(UC_HOOK_CODE,guard)
                w(0x5100000,0x500f000,0)
                uc.reg_write(UC_X86_REG_ESP,0x5100000);uc.reg_write(UC_X86_REG_ECX,ui)
                uc.emu_start(0x11090c0,0x500f000,count=10000);uc.hook_del(token)
                assert seen==[(0x1109d96 if cash<final else 0x1109dab,final)]
                guard_cases.append(dict(cash=cash,quote_in_EDI=seen[0][1],passed_to_capacity_check=cash>=final,
                  boundary=('actual published debit' if cash==debit else 'computed quote -1/equal') if cash!=capture['actual_wallet_after']['cash'] else 'actual captured wallet'))
            results.append(dict(template=template,key=key,quantity=quantity,raw_price_map_value=raw_price,
               override_found=template in table_rows,override_buyprice=table_rows.get(template,{}).get('buyprice'),
               final_native_quote=final,actual_published_cash_debit=debit,difference=final-debit,
               row_price_after_original_store=r(row+0x18),selected_UI_quantity=r(ui+0xd8),cash_guards=guard_cases,**observed))
    probe(0xef64e0,0xef65b0,0xef6640,payload=wire,observer=observer)
    return results


def main():
    before=freeze()
    assert all(before[n]==digest for n,digest in SEALED.items())
    assert before['evidence/native-image.bin']==hashlib.sha256(DATA).hexdigest()
    capture=json.loads((ROOT/CAPTURE).read_text(encoding='utf8'))
    assert capture['producer_sha256']==before[PRODUCER] and capture['exact_original_items_restored']
    assert capture['stock_or_price_packets_fabricated'] is False and capture['quote_policy_changed'] is False
    rows,source=table_source();parsed,schema_case=parse_original_row(rows[32000])
    conversions=[conversion_case(p,q,cw,flag) for p,q in ((1,1),(9,1),(10,1),(3,5))
                 for cw in (0x027f,0x037f) for flag in (0,1)]
    quotes=frame_quotes(capture,rows,parsed)
    after=freeze();assert before==after,'Inputs changed; discard outputs and coordinate'
    constant=struct.unpack('<d',DATA[0x2290090-BASE:0x2290098-BASE])[0]
    report={'method':'research: first-party original PFS/native image + exact captured published frame; explicit dependency adapters',
      'actual_case_count':1+len(conversions)+len(quotes),'case_count_unit':'1 full generated schema reader +16 scalar precision/path fixtures +3 real-frame item quote chains; 12 cash subchecks are internal',
      'capture_input_sha256':before[CAPTURE],'producer_sha256':before[PRODUCER],
      'captured_body_sha256':capture['body_sha256'],'captured_body_hex':capture['body_hex'],
      'source':source,'schema_case':schema_case,'quote_chains':quotes,'conversion_cases':conversions,
      'constant':{'address':'0x2290090','bytes_le':DATA[0x2290090-BASE:0x2290098-BASE].hex(),
                  'binary64_hex':constant.hex(),'exact_fraction':str(Fraction(constant)),
                  'difference_from_11_over_10':str(Fraction(constant)-Fraction(11,10))},
      'image_original_conversion_flag':u32(0x29b8ef8),'image_sha256':hashlib.sha256(DATA).hexdigest(),
      'host_dependency_adapters':[
       'PFS/BXML authoritative row attributes: native XML reader executes; XML integer getter and temporary UTF16 host strings are adapters',
       'full exact captured three-item c0434 frame: original decoder and marshal execute; native decoded STL price tree is searched without replacing its getter',
       'partial ItemRef memory bridge points to an Object; original 81a760 bean copy and 10817bc property writes execute; wrapper template duplicates decoded template',
       'original ConfigManager getter89e210 and Citemsell wrapper8842d0 execute; backend lookup is adapted from full CRC-checked PFS membership and native-parsed row, with genuine absence sentinel for 40200/40204; full config cache loader is not executed',
       'price calculation, config branch, row-price assignment, selection quantity=1, entire cash callback entry/guard execute; only selection highlight is a GUI no-op',
       'FPCW027f/037f and feature-flag0/1 are explicit offline environment fixtures; actual running client FPU state is not measured',
       'hashed native_gameplay_probe offline CRT allocation/free/copy/refcount adapters; Machine scratch mappings; no network/process/DB access'],
      'findings':['Citemsell override uses buyprice@+4, not sellprice@+8; key is wrapper template ID',
       'original final native quote differs from actual published debit in all three captured cases; a confirmed presentation/cash-guard mismatch for these fixtures',
       'default native UI formula and override are client observations, not unavailable original-server truth'],
      'unknowns':['full original GUI/cache lifecycle and original server pricing policy','original running client x87 precision/control and CPU feature flag; tested alternatives agree for bounded fixtures',
       'other templates, extreme signed32 overflow and negative-price handling; no broad price-policy claim',
       'whether any original server fee, currency rule or special NPC policy matches these client quotes; requires independent authority decision'],
      'input_sha256_before':before,'input_sha256_after':after,'production_changed':False,
      'live_database_accessed':False,'producer_rerun':False,'network_or_services_used':False,'native_gui_verified':False}
    out=io.StringIO()
    with redirect_stdout(out):
        for address,size in BLOCKS:print('\nREGION',hex(address));disasm(address,size)
    (ROOT/'evidence/npc-buyback-quote-disassembly.txt').write_text(out.getvalue(),encoding='utf8')
    (ROOT/'evidence/npc-buyback-quote-native.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'passed':report['actual_case_count'],'cash_subchecks':sum(len(q['cash_guards']) for q in quotes),
                      'native_quotes':[q['final_native_quote'] for q in quotes],'preserved':len(before)},ensure_ascii=False))


if __name__=='__main__':main()
