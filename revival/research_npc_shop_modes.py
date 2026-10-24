"""Offline original NPC purchase mode/button and CRC-checked shelf audit."""
import contextlib
import hashlib
import json
import struct
from pathlib import Path
from pfs import PfsArchive
from bxml import decode
from native_inspect import BASE, DATA, u32, vtables, disasm
from verify_social_native import native_payload
from research_npc_submenu import Machine

ROOT = Path(__file__).parent


def buy_button(first, second, ui_mode=0):
    """Run entire original purchase dispatch; UI selection/network are dependencies."""
    m=Machine()
    selected, bean, radio1, radio2, net, vt, send=(0x5003000+i*0x1000 for i in range(7))
    npc=0x1234567800000157
    m.w(m.stack,m.stop)
    m.w(m.ui+0xc8,selected);m.w(selected,bean);m.w(bean+0x26c,32000)
    m.w(m.ui+0x78,ui_mode);m.w(m.ui+0xd8,2)
    m.w(m.ui+0xe8,npc & 0xffffffff,npc>>32)
    m.w(m.ui+0x60,radio1,radio2)
    m.uc.mem_write(radio1+0x530,bytes([first]));m.uc.mem_write(radio2+0x530,bytes([second]))
    m.w(net,vt);m.w(vt+0x3c,send)
    sent=[]
    def hook(uc,address,size,user):
        sp=uc.reg_read(m.spreg)
        if address==0x813860:m.ret(net)
        elif address==send:
            obj=m.r(sp+4)
            assert m.r(obj)==0x2279760 and m.r(obj+4)==0xc232c
            key=m.r(obj+8)|(m.r(obj+12)<<32)
            result=(key,m.r(obj+16),m.r(obj+20),m.r(obj+24))
            assert result[:3]==(npc,32000,2)
            sent.append(result);m.ret(1,4)
        elif address==0x1106975:uc.emu_stop()
    m.run(0x1106580,hook)
    assert len(sent)==1
    return {'radio1':first,'radio2':second,'ui_mode':ui_mode,'sent':sent[0]}


def main():
    assert vtables('.?AVCBuyItemFromNpc@npc@gsp@knight@@')==[0x2279760]
    assert vtables('.?AVCNpcSellItemDlg@@')==[0x2290118]
    assert u32(0x163f09c+DATA[0x163f1c0-BASE]*4)==0x1636d38
    codec=[]
    for mode in range(12):
        key=0x1234567800000157
        actual=native_payload(0xe516d0,scalars=[(0x10,32000),(0x14,2),(0x18,mode)],raw=[(8,struct.pack('<q',key))])
        assert actual==struct.pack('>qiii',key,32000,2,mode)
        codec.append({'mode':mode,'hex':actual.hex()})
    for mode in (-1,12):
        try:native_payload(0xe516d0,scalars=[(0x10,32000),(0x14,2),(0x18,mode & 0xffffffff)],raw=[(8,struct.pack('<q',key))])
        except RuntimeError:pass
        else:raise AssertionError('Original range guard missing')
    buttons=[buy_button(a,b) for a,b in ((1,0),(0,1),(1,1),(0,0))]
    assert [r['sent'][3] for r in buttons]==[0,1,0,0]
    buttons += [buy_button(1,0,t) for t in (5,7)]
    assert [r['sent'][3] for r in buttons[-2:]]==[4,9]
    archives={'config':PfsArchive(ROOT.parent/'artres/config.pfs'),'ui':PfsArchive(ROOT.parent/'artres/ui.pfs')}
    sources={}
    def read(archive,name):
        p=archives[archive];raw=p.read(name);entry=p.entries[name]
        sources[name]={'archive':archive,'crc32':hex(entry.crc),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
        return decode(raw)
    shelf=read('config','autoconfig/knight.gsp.item.npcsellitem.xml')
    attrs={int(r.get('id')):dict(r.attrib) for r in read('config','autoconfig/knight.gsp.item.citemattr.xml')}
    npcs={int(r.get('id')):dict(r.attrib) for r in read('config','autoconfig/knight.gsp.npc.cnpcconfig.xml')}
    layout=read('ui','layouts/npcsellitemdlg.layout')
    radios={w.get('Name'):next((x.get('Value') for x in w if x.get('Name')=='Text'),None)
            for w in layout.iter('Window') if w.get('Name','') in ('NpcSellItem/sellDialog/1','NpcSellItem/sellDialog/2')}
    assert list(radios.values())==['银两购买','绑银购买']
    problem=[];all_shelves=[]
    for r in shelf:
        npc=int(r.get('id'));node=r.find('items');items=[int(x.text) for x in (() if node is None else node)]
        unavailable=[{'item':item,'price':attrs.get(item,{}).get('price'),'attributes':attrs.get(item)}
                     for item in items if not attrs.get(item,{}).get('price','').isdigit() or int(attrs[item]['price'])<=0]
        all_shelves.append({'npc_id':npc,'items':items,'npc_definition':npcs.get(npc)})
        if unavailable:problem.append({'npc_id':npc,'items':unavailable})
    evidence=ROOT/'evidence'
    regions=[(0xe516d0,0x76),(0xdaf540,0x21),(0x1636d38,0x31),(0x10ecaf0,0x80),
             (0x1108280,0x100),(0x11087c2,0xbe),(0x1106580,0x3f5),(0x110a690,0x80),
             (0x110bd17,0x21),(0x10fc9d0,0x88),(0x110a355,0x5a),
             (0x10e520a,0x77),(0x13dfa25,0x4a),(0x18757ab,0x49)]
    with (evidence/'npc-shop-modes-native-disassembly.txt').open('w',encoding='utf8') as f:
        with contextlib.redirect_stdout(f):
            for address,length in regions:
                print('\nREGION',hex(address));disasm(address,length)
    known={r['npc_id'] for r in all_shelves if r['npc_definition'] is not None and r['items']}
    report={'image_sha256':hashlib.sha256(DATA).hexdigest(),'sources':sources,'codec':codec,
            'rejected_modes':[-1,12],'buttons':buttons,'radios':radios,'shelf_count':len(all_shelves),
            'problem_shelf_count':len(problem),'known_npc_shelves':len(known),
            'known_npc_problem_shelves':sum(r['npc_id'] in known for r in problem),
            'problem_shelves':problem,'all_shelves':all_shelves,
            'examples':{str(k):attrs.get(k) for k in (32000,63140,63634,63633)},
            'native_gui_verified':False,'runtime_changed':False,'zero_price_interpretation':'unknown'}
    (evidence/'npc-shop-modes-native.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({k:report[k] for k in ('image_sha256','shelf_count','problem_shelf_count','radios','buttons')},ensure_ascii=True))


if __name__=='__main__':main()
