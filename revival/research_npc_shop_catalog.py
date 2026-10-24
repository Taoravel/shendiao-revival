"""Bounded original shop purchase/buyback research. No live process or database.

Only this probe's JSON and disassembly outputs are written. Historical probes
are imported only for the generic Machine, never run or counted.
"""
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import struct

from bxml import decode
from native_gameplay_probe import probe
from native_inspect import BASE, DATA, disasm, u32, vtables
from pfs import PfsArchive
from research_npc_submenu import Machine
from verify_social_native import native_payload

ROOT = Path(__file__).resolve().parent
OLD = (
 'research_npc_repair_columns.py', 'evidence/NPC_REPAIR_COLUMN_RESEARCH.md',
 'evidence/npc-repair-column-native.json', 'evidence/npc-repair-column-disassembly.txt',
 'research_npc_special_repair_menu.py', 'evidence/NPC_SPECIAL_REPAIR_MENU_RESEARCH.md',
 'evidence/npc-special-repair-menu-native.json', 'evidence/npc-special-repair-menu-disassembly.txt',
 'research_npc_special_repairs.py', 'evidence/NPC_SPECIAL_REPAIRS_NATIVE_RESEARCH.md',
 'evidence/npc-special-repairs-native.json', 'evidence/npc-special-repairs-native-disassembly.txt',
 'research_npc_special_repair_cost.py', 'evidence/NPC_SPECIAL_REPAIR_COST_RESEARCH.md',
 'evidence/npc-special-repair-cost-native.json', 'evidence/npc-special-repair-cost-native-disassembly.txt')
WATCHED = OLD + ('npc_gameplay.py', 'npc_shop_sales.py', 'npc_shop_payments.py',
 'npc_repairs.py', 'inventory.py', 'native_gameplay_probe.py', 'native_inspect.py',
 'research_npc_submenu.py', 'verify_social_native.py', 'pfs.py', 'bxml.py',
 'inspect_client.py', 'evidence/native-image.bin',
 'catalogs/knight.gsp.item.npcsellitem.json', 'catalogs/knight.gsp.item.citemattr.json',
 'catalogs/knight.gsp.npc.cnpcconfig.json', '../artres/config.pfs', '../artres/ui.pfs',
 'ARCHITECTURE.md', 'DESIGN_AUTHORITY.md',
 'evidence/npc-equipment-identification-ready.json', 'evidence/npc-placement-direction-ready.json',
 Path(__file__).name)
BLOCKS = ((0x1103060, 0x38), (0x110887e, 0x1a0), (0x1103cc7, 0x1a0),
 (0x1636d38, 0x31), (0x110a690, 0x78), (0x110a9b5, 0x70), (0x110b9bf, 0x32),
 (0x110bd17, 0x65), (0x89dc80, 0xb), (0x878090, 0xe0), (0x89d730, 0xb), (0x86ee90, 0xa),
 (0xc9894e, 0x15), (0x11039bf, 0x1b1), (0x11020c0, 0x7c),
 (0x464dd0, 0x39), (0x1106580, 0x3f5), (0x1109168, 0x20),
 (0x1109d6c, 0xd2), (0x10a90c0, 0x29), (0x10a49f0, 0x2a0),
 (0x1103440, 0x18b), (0x110a55a, 0x31), (0x110a64f, 0x3f),
 (0xef64e0, 0x55), (0xef65b0, 0x12b), (0x10a9054, 0x18),
 (0x10a4840, 0x19f), (0x1081790, 0x66))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze():
    return {name: sha(ROOT/name) for name in WATCHED}


def local_shelf(config_id, items):
    """Original getter, wrapper forwarding, vector assignment and page count.

    Backend lookup + record layout are dependency fixtures, not an executed
    table loader or proof that the service2 first parameter is an NPC ID.
    """
    from unicorn.x86_const import UC_X86_REG_ESI, UC_X86_REG_EBP, UC_X86_REG_EBX
    m = Machine()
    manager, backend, vt, lookup, row, src, dst = (0x5010000+i*0x1000 for i in range(7))
    m.w(0x2945aec, manager)
    m.w(manager+0x860, 0x2259044, backend)
    m.w(backend, vt); m.w(vt+8, lookup)
    m.w(src, *items); m.w(dst, *([0]*len(items)))
    m.w(row, config_id, 0, src, src+4*len(items), src+4*len(items))
    m.w(m.ui+0x88, 0, dst, dst+4*len(items), dst+4*len(items))
    m.w(m.stack+0x114, config_id)
    m.uc.reg_write(UC_X86_REG_ESI, m.ui)
    m.uc.reg_write(UC_X86_REG_EBP, m.ui+0x88)
    m.uc.reg_write(UC_X86_REG_EBX, 0)
    imported = u32(0x22448a4)
    if not (BASE <= imported < BASE+len(DATA)):
        try: m.uc.mem_map(imported & ~4095, 4096)
        except Exception: pass
    calls = []
    def hook(uc, address, size, user):
        sp = uc.reg_read(m.spreg)
        if address == lookup:
            assert m.r(sp+4) == config_id
            assert uc.reg_read(m.cxreg) == backend
            calls.append(config_id); m.ret(row, 4)
        elif address == imported:
            dest, capacity, source, count = (m.r(sp+n) for n in (4,8,12,16))
            assert count <= capacity
            uc.mem_write(dest, bytes(uc.mem_read(source, count))); m.ret(0)
        elif address == 0x1107c90: uc.emu_stop()
    m.run(0x110bd17, hook)
    actual = [m.r(p) for p in range(m.r(m.ui+0x8c), m.r(m.ui+0x90), 4)]
    assert actual == items and calls == [config_id]
    assert m.r(m.ui+0xe0) == max(1,(len(items)+9)//10)
    return {'config_lookup_key':config_id, 'copied_templates':actual,
            'pages':m.r(m.ui+0xe0), 'source_mode':'entered mode0 branch; mode provenance unverified'}


def tab_branch(selected):
    from unicorn.x86_const import UC_X86_REG_ESI, UC_X86_REG_EBX
    m = Machine(); tab = 0x5010000
    m.w(m.ui+0x38, tab); m.uc.mem_write(tab+0x530, bytes([selected]))
    m.uc.reg_write(UC_X86_REG_ESI, m.ui); m.uc.reg_write(UC_X86_REG_EBX, 0)
    end = []
    def hook(uc,address,size,user):
        if address in (0x1103cd6,0x1103e55): end.append(address); uc.emu_stop()
    m.run(0x1103cc7,hook)
    assert end == [0x1103cd6 if selected else 0x1103e55]
    return {'buyback_tab_selected':bool(selected),'next':hex(end[0])}


def purchase(config_id, items, index, quantity, attr):
    """Original local page selection -> setter -> complete request builder.

    Config records/backend and GUI name/icon drawing are dependency adapters.
    The original CItemAttr lookup and cell setter execute, not a full CEGUI.
    """
    from unicorn.x86_const import UC_X86_REG_ESI, UC_X86_REG_EAX, UC_X86_REG_EDI, UC_X86_REG_EBP
    m = Machine(); cell, selected, values, cells, page = (0x5010000+i*0x1000 for i in range(5))
    chosen = items[index]
    # Enter the original loop body with an explicit slot index and full shelf.
    m.w(values, *items); m.w(m.ui+0x88, 0, values, values+len(items)*4, values+len(items)*4)
    m.w(cells+32*index,cell); m.w(m.ui+0xbc,cells,cells+320,cells+320)
    m.w(page,1);m.w(m.stack+0x5c,page);m.w(m.ui+0x78,0)
    m.w(m.stack+0x1c,index,index*32)
    m.uc.reg_write(UC_X86_REG_ESI,m.ui);m.uc.reg_write(UC_X86_REG_EAX,0)
    m.uc.reg_write(UC_X86_REG_EDI,index);m.uc.reg_write(UC_X86_REG_EBP,index*32)
    stage = ['render']; captured=[]; sent=[]; lookup_keys=[]
    net,vt,send,radio1,radio2=(0x5020000+i*0x1000 for i in range(5))
    manager,backend,backendvt,lookup,record=(0x5030000+i*0x1000 for i in range(5))
    m.w(0x2945aec,manager)
    m.w(manager+0x5b8,vtables('.?AVknight_gsp_item_CItemAttr_table_implement@XMLCONFIG@@')[0],backend)
    m.w(backend,backendvt);m.w(backendvt+8,lookup)
    m.w(record,int(attr['id']));m.w(record+0x70,int(attr['icon']))
    npc=0x1234567800002714
    def hook(uc,address,size,user):
        sp=uc.reg_read(m.spreg)
        if stage[0]=='render':
            if address==0x11020c0:
                captured.append((m.r(m.r(sp+4)),m.r(sp+4)));assert m.r(sp+8)==0;uc.emu_stop()
        elif stage[0]=='attribute':
            if address==lookup:
                lookup_keys.append(m.r(sp+4));assert uc.reg_read(m.cxreg)==backend;m.ret(record,4)
            elif address in (0x1586330,0x48d270):m.ret(0,4) # name/icon presentation only
            elif address==0x464e05:uc.emu_stop()
        elif stage[0]=='send':
            if address==0x813860:m.ret(net)
            elif address==send:
                obj=m.r(sp+4)
                assert (m.r(obj),m.r(obj+4))==(0x2279760,0xc232c)
                sent.append((m.r(obj+8)|(m.r(obj+12)<<32),m.r(obj+16),m.r(obj+20),m.r(obj+24)))
                m.ret(1,4)
            elif address==0x1106975:uc.emu_stop()
    m.run(0x11039ff,hook);assert len(captured)==1 and captured[0][0]==chosen
    stage[0]='attribute';m.w(m.stack,m.stop,captured[0][1],0,0x5039000,0x5039004);m.ui=cells+32*index
    m.run(0x11020c0,lambda *args:None)
    assert m.r(cell+0x26c)==chosen and lookup_keys==[chosen]
    assert m.r(cells+32*index+0x14)==int(attr['icon'])
    stage[0]='send';m.ui=0x5001000
    m.w(m.ui+0xc8,selected);m.w(selected,cell);m.w(m.ui+0xd8,quantity)
    m.w(m.ui+0xe8,npc&0xffffffff,npc>>32);m.w(m.ui+0x60,radio1,radio2)
    m.uc.mem_write(radio1+0x530,b'\1');m.w(net,vt);m.w(vt+0x3c,send)
    m.run(0x1106580,lambda *args:None)
    assert sent==[(npc,chosen,quantity,0)]
    wire=native_payload(0xe516d0,scalars=[(0x10,chosen),(0x14,quantity),(0x18,0)],raw=[(8,struct.pack('<Q',npc))])
    assert wire==struct.pack('>Qiii',npc,chosen,quantity,0)
    return {'config_id_fixture':config_id,'page':1,'slot_index':index,'template':chosen,'quantity':quantity,
            'cell_template':m.r(cell+0x26c),'attribute_lookup_key':lookup_keys[0],'icon':int(attr['icon']),
            'protocol':'0xc232c','wire':wire.hex(),
            'bridge':'same full shelf -> original slot template lookup/CItemAttr lookup/cell setter -> selected cell; no stock instance supplied'}


def repurchase(key, template, quantity, position, binding, unit_price):
    """Original full decode/re-encode, response entry, price map and sender.

    Clear/install are observed at their call boundaries; price map search and
    wrapper+7c write execute original code using the decoded STL tree.
    """
    from unicorn import UC_HOOK_CODE
    from unicorn.x86_const import UC_X86_REG_ECX,UC_X86_REG_EIP,UC_X86_REG_ESP,UC_X86_REG_ESI,UC_X86_REG_EBP,UC_X86_REG_EBX
    item=struct.pack('>iiiiQiQiQ',template,binding,key,position,0,quantity,0,0,0)
    wire=struct.pack('>Qi',123456,20)+b'\1'+item+b'\1'+struct.pack('>ii',key,unit_price)
    observed={}
    def observer(uc,obj):
        def r(a):return struct.unpack('<I',uc.mem_read(a,4))[0]
        def w(a,*v):uc.mem_write(a,struct.pack('<'+'I'*len(v),*v))
        stack,stop=0x5100000,0x500f000
        begin,end=r(obj+0x20),r(obj+0x24)
        assert end-begin==64
        assert tuple(r(begin+n) for n in (4,8,12,16,32))==(template,binding,key,position,quantity)
        observed['decoded_item_hex']=bytes(uc.mem_read(begin,64)).hex()
        # Independent marshal after decode; probe(payload=...) itself only decodes.
        w(0x5003000-8,0);w(stack,stop,0x5002000)
        uc.reg_write(UC_X86_REG_ECX,obj);uc.reg_write(UC_X86_REG_ESP,stack)
        uc.emu_start(0xef65b0,stop,count=1000000)
        assert bytes(uc.mem_read(0x5003000,r(0x5003000-8)))==wire
        w(0x2944628,0x5300000);w(stack,stop,0,0)
        uc.reg_write(UC_X86_REG_ECX,obj);uc.reg_write(UC_X86_REG_ESP,stack)
        calls=[]
        def response(emu,a,size,user):
            sp=emu.reg_read(UC_X86_REG_ESP)
            if a==0x108f9f0:
                calls.append(('clear',r(sp+4)))
                emu.reg_write(UC_X86_REG_ESP,sp+8);emu.reg_write(UC_X86_REG_EIP,r(sp))
            elif a==0x10a49f0:
                calls.append(('install',r(sp+4),r(sp+8)));emu.emu_stop()
        token=uc.hook_add(UC_HOOK_CODE,response)
        uc.emu_start(0x10a90c0,stop,count=1000);uc.hook_del(token)
        assert calls==[('clear',4),('install',obj+8,obj+0x30)]
        observed['response_calls']=[['clear',4],['install','ItemBag@+8','prices@+0x30']]
        wrapper=0x5310000
        w(stack+0x48,obj+0x30);w(wrapper+0x7c,0xfeedface)
        uc.reg_write(UC_X86_REG_ESP,stack);uc.reg_write(UC_X86_REG_ESI,begin+12)
        uc.reg_write(UC_X86_REG_EBP,wrapper)
        uc.emu_start(0x10a4b44,0x10a4b95,count=10000)
        assert r(wrapper+0x7c)==unit_price
        observed['mapped_price']=r(wrapper+0x7c)
        # Original baseline display math; stops before optional config override.
        itemobject,entry=0x5311000,0x5312000
        w(wrapper,itemobject);w(itemobject+0xc,template);w(itemobject+0x14,key)
        w(itemobject+0x28,quantity);w(itemobject+0x48,position);w(entry,wrapper)
        uc.reg_write(UC_X86_REG_ESI,entry);uc.reg_write(UC_X86_REG_ESP,stack)
        uc.emu_start(0x1103504,0x110351c,count=10000)
        from unicorn.x86_const import UC_X86_REG_EAX
        baseline=uc.reg_read(UC_X86_REG_EAX)
        assert baseline==int(unit_price*1.1*quantity)
        observed['baseline_display_before_config_override']=baseline
        # Selection bridge supplies the decoded identity and quantity to an
        # ItemRef; the original request builder itself chooses instance key.
        cell,ui,net,vt,send=0x5313000,0x5314000,0x5315000,0x5316000,0x5317000
        npc=0x1234567800002714
        w(cell+0x278,wrapper);w(ui+0xe8,npc&0xffffffff,npc>>32)
        w(net,vt);w(vt+0x3c,send);w(stack,stop)
        uc.reg_write(UC_X86_REG_ESP,stack);uc.reg_write(UC_X86_REG_ECX,cell)
        uc.reg_write(UC_X86_REG_ESI,ui);uc.reg_write(UC_X86_REG_EBX,0)
        sent=[]
        def sender(emu,a,size,user):
            sp=emu.reg_read(UC_X86_REG_ESP)
            if a==0x813860:
                emu.reg_write(UC_X86_REG_ESP,sp+4);emu.reg_write(UC_X86_REG_EIP,r(sp));emu.reg_write(UC_X86_REG_EAX,net)
            elif a==send:
                packet=r(sp+4);assert r(packet+4)==0xc232e
                sent.append((r(packet+8)|(r(packet+12)<<32),r(packet+16)))
                emu.emu_stop()
        token=uc.hook_add(UC_HOOK_CODE,sender)
        uc.emu_start(0x1109ddf,0x1109e3e,count=1000);uc.hook_del(token)
        assert sent==[(npc,key)]
        observed['repurchase_request']={'protocol':'0xc232e','npc_key':npc,'item_key':key}
    probe(0xef64e0,0xef65b0,0xef6640,payload=wire,observer=observer)
    request=native_payload(0xe51c60,scalars=[(0x10,key)],raw=[(8,struct.pack('<Q',0x1234567800002714))])
    assert request==struct.pack('>Qi',0x1234567800002714,key)
    return dict(template=template,key=key,quantity=quantity,position=position,binding=binding,
                input_price_map_value=unit_price,wire=wire.hex(),request_wire=request.hex(),**observed)


def response_comparison(repurchase_empty):
    """Both native response envelopes at their actual process boundaries.

    This cannot identify which message the unavailable original server sent.
    """
    from unicorn import UC_HOOK_CODE
    from unicorn.x86_const import UC_X86_REG_ECX,UC_X86_REG_EIP,UC_X86_REG_ESP,UC_X86_REG_ESI
    bag=struct.pack('>Qi',123456,20)+b'\0'
    wire=bag+b'\0' if repurchase_empty else struct.pack('>i',4)+bag+b'\0'
    observed={}
    def observer(uc,obj):
        def r(a):return struct.unpack('<I',uc.mem_read(a,4))[0]
        def w(a,*v):uc.mem_write(a,struct.pack('<'+'I'*len(v),*v))
        stack,stop=0x5100000,0x500f000
        w(0x5003000-8,0);w(stack,stop,0x5002000)
        uc.reg_write(UC_X86_REG_ECX,obj);uc.reg_write(UC_X86_REG_ESP,stack)
        uc.emu_start(0xef65b0 if repurchase_empty else 0xef62d0,stop,count=1000000)
        assert bytes(uc.mem_read(0x5003000,r(0x5003000-8)))==wire
        w(0x2944628,0x5300000);w(stack,stop,0,0)
        uc.reg_write(UC_X86_REG_ECX,obj);uc.reg_write(UC_X86_REG_ESI,obj);uc.reg_write(UC_X86_REG_ESP,stack)
        calls=[]
        def hook(emu,a,size,user):
            sp=emu.reg_read(UC_X86_REG_ESP)
            if a==0x108f9f0:
                calls.append(['clear',r(sp+4)])
                emu.reg_write(UC_X86_REG_ESP,sp+8);emu.reg_write(UC_X86_REG_EIP,r(sp))
            elif a==0x10a49f0:
                assert (r(sp+4),r(sp+8))==(obj+8,obj+0x30)
                calls.append(['install',4,'ItemBag','price_map']);emu.emu_stop()
            elif a==0x10a4840:
                assert (r(sp+4),r(sp+8))==(4,obj+0x10)
                calls.append(['install',4,'ItemBag','no price_map']);emu.emu_stop()
        token=uc.hook_add(UC_HOOK_CODE,hook)
        uc.emu_start(0x10a90c0 if repurchase_empty else 0x10a9054,stop,count=1000)
        uc.hook_del(token)
        assert calls==([['clear',4],['install',4,'ItemBag','price_map']] if repurchase_empty else [['install',4,'ItemBag','no price_map']])
        observed['process_calls']=calls
    probe(*( (0xef64e0,0xef65b0,0xef6640) if repurchase_empty else (0xef6220,0xef62d0,0xef6350)),payload=wire,observer=observer)
    return {'protocol':'0xc0434' if repurchase_empty else '0xc03f3','empty':True,'wire':wire.hex(),**observed}


def main():
    before=freeze()
    assert hashlib.sha256(DATA).hexdigest()=='2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791'
    assert before['evidence/native-image.bin']==hashlib.sha256(DATA).hexdigest()
    assert before['evidence/npc-equipment-identification-ready.json']=='9b05ab14fd786558a2e320a70ae5a9579b578b3c4170ecb241fac8e2bab98794'
    assert before['evidence/npc-placement-direction-ready.json']=='761c97193b18d92e860aa8cbfeac045a34d9c10057c792d586b0484c7df62d82'
    col=u32(0x2259044-4);type_info=u32(col+12)
    table_rtti=DATA[type_info+8-BASE:type_info+200-BASE].split(b'\0')[0].decode('ascii')
    assert table_rtti=='.?AVknight_gsp_item_NpcSellItem_table_implement@XMLCONFIG@@'
    sources={}; tables={}
    for name in ('knight.gsp.item.npcsellitem','knight.gsp.item.citemattr','knight.gsp.npc.cnpcconfig'):
        archive=PfsArchive(ROOT.parent/'artres/config.pfs');entry='autoconfig/'+name+'.xml'
        raw=archive.read(entry);xml=decode(raw)
        # The cache's children also retain extraction-time indentation tails;
        # BXML has no such text. Compare every row's actual attributes/lists.
        assert all(not child.attrib and all(not list(x) and not x.attrib for x in child) for row in xml for child in row)
        projected=[{'attributes':dict(row.attrib),'lists':{child.tag:[x.text for x in child] for child in row}} for row in xml]
        cache=ROOT/'catalogs'/f'{name}.json'
        cached=json.loads(cache.read_text(encoding='utf8'))
        assert projected==[{'attributes':row['attributes'],'lists':row['lists']} for row in cached]
        tables[name]={int(row['attributes']['id']):row for row in projected}
        sources[entry]={'archive':'artres/config.pfs','crc32':hex(archive.entries[entry].crc),'bytes':len(raw),
                        'sha256':hashlib.sha256(raw).hexdigest(),'rows':len(projected),'full_cache_projection_equal':True,
                        'projection_fields':'all rows: all attributes and all flat child lists; no nested/attributed child elements; formatting tails excluded', 'cache_sha256':sha(cache)}
    archive=PfsArchive(ROOT.parent/'artres/ui.pfs');entry='layouts/npcsellitemdlg.layout';raw=archive.read(entry);layout=decode(raw)
    tabs={w.get('Name'):next((x.get('Value') for x in w if x.get('Name')=='Text'),None)
          for w in layout.iter('Window') if w.get('Name') in ('NpcSellItem/tab1','NpcSellItem/tab11')}
    assert tabs=={'NpcSellItem/tab1':'购买','NpcSellItem/tab11':'回购'}
    assert DATA[0x2290078-BASE:0x2290078-BASE+22].split(b'\0')[0]==b'NpcSellItemDlg.layout'
    sources[entry]={'archive':'artres/ui.pfs','crc32':hex(archive.entries[entry].crc),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    shelves=tables['knight.gsp.item.npcsellitem'];attrs=tables['knight.gsp.item.citemattr']
    selected=[10004]+[key for key,row in shelves.items() if len(row['lists'].get('items',[]))>10][:2]
    assert len(selected)==3
    shelf_cases=[local_shelf(key,list(map(int,shelves[key]['lists']['items']))) for key in selected]
    items=list(map(int,shelves[10004]['lists']['items']))
    purchase_cases=[purchase(10004,items,index,qty,attrs[items[index]]['attributes']) for index in (0,4,9) for qty in (1,7)]
    tab_cases=[tab_branch(value) for value in (0,1)]
    repurchase_cases=[repurchase(701+i,items[i],qty,pos,binding,100+i*10)
                      for i,(qty,pos,binding) in enumerate(((1,0,0),(3,4,1),(7,9,1)))]
    response_cases=[response_comparison(value) for value in (False,True)]
    after=freeze();assert after==before,'Inputs changed during probe; discard outputs and coordinate'
    output=io.StringIO()
    with redirect_stdout(output):
        for address,size in BLOCKS:
            print('\nREGION',hex(address),hex(size));disasm(address,size)
    (ROOT/'evidence/npc-shop-catalog-disassembly.txt').write_text(output.getvalue(),encoding='utf8')
    report={'image_sha256':hashlib.sha256(DATA).hexdigest(),'method':'research skill: original PFS + bounded native execution; separate observations/Adapters/unknowns',
      'actual_case_count':len(shelf_cases)+len(purchase_cases)+len(tab_cases)+len(repurchase_cases)+len(response_cases),
      'case_count_unit':'one independent fixture chain; codec and inner calls are not separately counted',
      'sources':sources,'tabs':tabs,'native_bindings':{'tab1':'UI+0x34 at 0x11088cd','tab11':'UI+0x38 at 0x1108928','layout_name_method':'0x1103060',
       'shelf_table_rtti':table_rtti,'shelf_wrapper_vtable':'0x2259044','shelf_member':'ConfigManager+0x860',
       'mode_source':'open stack+0x120 -> EBP at 0x110a9b5 -> UI+0x78 at 0x110aa0b; separate from first param stack+0x114'},
      'local_shelf_cases':shelf_cases,'purchase_chains':purchase_cases,'tab_branch_cases':tab_cases,'repurchase_chains':repurchase_cases,'response_comparison_cases':response_cases,
      'source_examples':{'npc10004':tables['knight.gsp.npc.cnpcconfig'][10004],
       'shelf10004':shelves[10004], 'item_attributes':{str(i):attrs[i] for i in items}},
      'dependency_adapters':['Machine native image/scratch memory/stop boundaries; no original GUI process',
       'local shelf backend lookup supplies original PFS row using id+vector memory layout; original ConfigManager getter and wrapper forwarding execute',
       'host checked-copy CRT copies bytes; native vector assignment/page arithmetic execute',
       'normal renderer loop-body slot/index/page are supplied; original full source vector is retained; CItemAttr backend supplies original PFS id/icon scalars; original getter/wrapper/lookup call/cell setter execute; name/icon drawing skipped and selected-cell pointer supplied',
       'network manager/send captures bytes only, never connects; original purchase and repurchase request construction executes',
       'native_gameplay_probe offline allocation/free/refcount/UTF16/CRT adapters as declared in hashed helper; original codec and STL tree execute',
       'response clear-column is observed/no-op; install call is observed/stopped, not a completed ItemManager mutation',
       'buyback ItemRef memory bridge takes decoded item fields; original price-map lookup/write and display baseline math execute; optional price override and full button guards excluded'],
      'unknowns':['service2 menu+d8 actual first-parameter origin and actual mode for NPC10004 remain unproved; npctype1 is not asserted equal UI mode',
       'underlying original server behavior, stock limits, infinite stock, expiry policy, permission lists and price/currency eligibility remain unknown',
       'ordinary local shelf contains template IDs only; no stock instance keys, 99 counts, binding or expiry can be derived from it',
       'SGetRepurchaseItems has no NPC identity/request correlation; stale replies must be fenced by owning server/session context, which this client research does not implement',
       'SGetBagInfo column4 common handler also accepts an ItemBag; which response original server chose after query4 is unknown without original server/capture',
       'buyback default display is map value*quantity*1.1 then conversion; config override at ConfigManager+0xb28 can replace it; final original pricing not reconstructed',
       'native GUI session, merchant permission reachability and full original ItemManager install/render path are not verified'],
      'input_sha256_before':before,'input_sha256_after':after,
      'native_gui_verified':False,'production_changed':False,'server_implemented':False}
    (ROOT/'evidence/npc-shop-catalog-native.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'passed':report['actual_case_count'],'shelves':selected,'watched_files_unchanged':len(before)},ensure_ascii=False))


if __name__=='__main__':main()
