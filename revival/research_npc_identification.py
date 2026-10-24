"""First-party offline NPC equipment identification: no runtime/DB/client use."""
import contextlib
import hashlib
import json
import struct
from pathlib import Path
from native_inspect import BASE, DATA, u32, vtables, disasm
from native_gameplay_probe import probe
from research_npc_submenu import Machine
from pfs import PfsArchive
from bxml import decode

ROOT=Path(__file__).parent
NPC_KEY=0x1234567800002a8a


def roundtrip(ctor,marshal,decode_,payload):
    from unicorn.x86_const import UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
    encoded=[]
    def observe(uc,obj):
        stream,buf,stack,stop=0x5002000,0x5003000,0x5100000,0x500f000
        uc.mem_write(buf-12,struct.pack('<III',0x7000,0,1));uc.mem_write(stream+8,bytes(4))
        uc.mem_write(stack,struct.pack('<II',stop,stream));uc.reg_write(UC_X86_REG_ECX,obj);uc.reg_write(UC_X86_REG_ESP,stack)
        uc.emu_start(marshal,stop,count=1000000)
        assert uc.reg_read(UC_X86_REG_EIP)==stop
        size=struct.unpack('<I',uc.mem_read(buf-8,4))[0];encoded.append(bytes(uc.mem_read(buf,size)))
    probe(ctor,marshal,decode_,payload=payload,observer=observe,host_imports={u32(0x22448a4):'copy_checked'})
    assert encoded==[payload]
    return {'hex':payload.hex(),'bytes':len(payload)}


def codec_rejects(ctor,marshal,decode_,payload):
    try:
        roundtrip(ctor,marshal,decode_,payload)
    except ValueError as error:
        assert str(error)=='Original codec rejected candidate'
        return {'hex':payload.hex(),'rejected':True,'exception':'original 0x1919292'}
    raise AssertionError('Expected original native decoder rejection')


def compact_count(count):
    # Candidate bytes only; acceptance/re-emission is checked by original code.
    assert 0<=count<0x4000
    return bytes([count]) if count<0x80 else struct.pack('>H',count|0x8000)


def request_body(keys,mode=1,npc_key=NPC_KEY):
    return compact_count(len(keys))+b''.join(struct.pack('>i',k) for k in keys)+struct.pack('>Qi',npc_key,mode)


def state_body(entries,mode=1,npc_key=NPC_KEY):
    return struct.pack('>Q',npc_key)+compact_count(len(entries))+b''.join(struct.pack('>ii',*e) for e in entries)+struct.pack('>i',mode)


def menu495(keys):
    from unicorn.x86_const import UC_X86_REG_ESI,UC_X86_REG_EBP
    m=Machine();m.w(m.ui+0xd0,NPC_KEY&0xffffffff,NPC_KEY>>32)
    net,vt,send=0x5003000,0x5004000,0x5005000
    m.w(net,vt);m.w(vt+0x3c,send);m.w(m.stack,m.stop)
    copy=u32(0x22448a4);m.uc.mem_map(copy&~4095,4096)
    heap=[0x5200000];events=[]
    def hook(uc,a,size,user):
        sp=uc.reg_read(m.spreg)
        if a==0x109e890:
            vec=m.r(sp+4);data=0x5008000
            if keys:m.w(data,*keys)
            m.w(vec,0,data if keys else 0,data+4*len(keys) if keys else 0,data+4*len(keys) if keys else 0)
            m.ret(cleanup=4)
        elif a==0x10831b0:
            args=[m.r(sp+i) for i in (4,8,12,16)]
            assert args==[NPC_KEY&0xffffffff,NPC_KEY>>32,0,10]
            events.append({'empty_open_args':args});uc.emu_stop()
        elif a==0x1919178:
            ptr=heap[0];heap[0]+=(m.r(sp+4)+15)&~15;m.ret(ptr)
        elif a==0x191910c:m.ret()
        elif a==copy:
            dst,capacity,src,count=(m.r(sp+i) for i in (4,8,12,16))
            assert count<=capacity
            if count:uc.mem_write(dst,bytes(uc.mem_read(src,count)))
            m.ret(0)
        elif a==0x813860:m.ret(net)
        elif a==send:
            obj=m.r(sp+4);assert m.r(obj+4)==0xc04cc
            begin,end=m.r(obj+0xc),m.r(obj+0x10)
            actual=[m.r(p) for p in range(begin,end,4)]
            assert actual==list(keys) and (m.r(obj+0x18)|(m.r(obj+0x1c)<<32))==NPC_KEY and m.r(obj+0x20)==1
            events.append({'sent':'0xc04cc','keys':actual,'npc_key':NPC_KEY,'mode':1});uc.emu_stop()
    m.uc.reg_write(UC_X86_REG_ESI,m.ui);m.uc.reg_write(UC_X86_REG_EBP,0)
    m.run(0x1638310,hook)
    assert len(events)==1
    return events[0]


def response_handler(mode,entries=((91,0),),owned=True):
    m=Machine();obj=m.ui
    data,wrapper,bean=0x5003000,0x5004000,0x5005000
    m.w(0x2944628,0x5007000);m.w(obj+8,NPC_KEY&0xffffffff,NPC_KEY>>32)
    m.w(obj+0x10,0,data,data+12*len(entries),data+12*len(entries));m.w(obj+0x20,mode)
    for i,(key,state) in enumerate(entries):m.w(data+i*12,0x2284614,key,state&0xffffffff)
    m.w(wrapper,bean);m.w(bean+0x58,77)
    m.w(m.stack,m.stop,0,0);events=[]
    def hook(uc,a,size,user):
        sp=uc.reg_read(m.spreg)
        if a==0x1091670:
            key,column=m.r(sp+4),m.r(sp+8)
            assert key==91 and column==1
            events.append({'lookup_key':key,'column':column,'owned':owned});m.ret(wrapper if owned else 0,8)
        elif a==0x10831b0:
            args=[m.r(sp+i) for i in (4,8,12,16)]
            assert args==[NPC_KEY&0xffffffff,NPC_KEY>>32,0,43 if mode==2 else 10]
            assert m.r(bean+0x58)==((entries[-1][1]&0xffffffff) if owned and entries else 77)
            events.append({'opened':args,'identified_after':m.r(bean+0x58)});uc.emu_stop()
    m.run(0x10934a0,hook)
    assert len(events)==len(entries)+1
    return {'response_mode':mode,'entries':entries,'owned':owned,'events':events}


def selection_fee(level,fee_row,identified=0,count=1,kind=8,confirm_chain=False):
    m=Machine();entries=0x5003000;wrapper=0x500a000;bean=0x500b000
    manager,vt,lookup,row=0x500c000,0x500d000,0x500e000,0x500f100
    m.w(m.ui+0xec,entries,entries+5*0x138,entries+5*0x138)
    for i in range(5):
        window=0x5011000+i*0x1000;m.w(entries+i*0x138+8,window);m.w(window+0x278,wrapper if i<count else 0)
    m.w(wrapper,bean);m.w(wrapper+8,kind);m.w(wrapper+0x28,level)
    m.w(bean+0x14,91);m.w(bean+0x58,identified)
    m.w(manager,vt);m.w(vt+8,lookup)
    m.w(row,*((0xffffffff,0) if fee_row is None else (level,fee_row)))
    m.w(m.stack,m.stop);m.w(m.ui+0x58,NPC_KEY&0xffffffff,NPC_KEY>>32)
    dialog,net,netvt,send=0x5020000,0x5021000,0x5022000,0x5023000
    m.w(net,netvt);m.w(netvt+0x3c,send)
    events=[];stage=['fee']
    def hook(uc,a,size,user):
        sp=uc.reg_read(m.spreg)
        if stage[0]=='popup':
            if a==0x1129af0:m.ret(dialog)
            elif a==0x463580:m.ret(cleanup=4)
            elif a==0x1644f80:m.ret()
            elif a==0x1648b18:
                saved=(m.r(dialog+0x38)|(m.r(dialog+0x3c)<<32),m.r(dialog+0x48),m.r(dialog+0x64))
                assert saved==(NPC_KEY,91,0)
                events.append({'confirmation_stored':saved});uc.emu_stop()
            return
        if stage[0]=='send':
            if a==0x813860:m.ret(net)
            elif a==send:
                obj=m.r(sp+4);fields=tuple(m.r(obj+i) for i in (8,12,16))
                assert m.r(obj+4)==0xc4276 and fields==(91,0,1)
                events.append({'confirmation_sent':fields});uc.emu_stop()
            return
        if a==0x89d820:m.ret(manager)
        elif a==lookup:
            assert m.r(sp+4)==level
            events.append({'fee_lookup_level':level});m.ret(row,4)
        elif a==0x16882ec:
            # The original getter/qualification/lookup branch has completed.
            # Avoid text renderer ABI; resume at real fee load after renderer.
            uc.reg_write(m.ipreg,0x168830f)
        elif a==0x1688313:
            fee=m.r(sp);assert fee==fee_row
            events.append({'fee_read':fee});uc.emu_stop()
        elif a in (0x168825d,0x1688283,0x16882a4,0x168844c):
            events.append({'rejected_at':hex(a)});uc.emu_stop()
    m.run(0x1688170,hook)
    if confirm_chain:
        assert events[-1]=={'fee_read':fee_row}
        # Formatting is outside this proof: resume at native selected-instance
        # extraction/factory call, then native confirmation-context stores.
        stage[0]='popup';m.run(0x1688364,lambda *args:None)
        assert 'confirmation_stored' in events[-1]
        stage[0]='send';m.ui=dialog;m.w(m.stack,m.stop,496)
        m.run(0x1648d00,lambda *args:None)
        assert 'confirmation_sent' in events[-1]
    return {'level':level,'identified':identified,'selected_count':count,'kind':kind,'events':events}


def confirm496(service_id=496,item_key=91):
    m=Machine();net,vt,send=0x5003000,0x5004000,0x5005000
    m.w(m.ui+0x38,NPC_KEY&0xffffffff,NPC_KEY>>32)
    m.w(m.ui+0x48,item_key);m.w(m.ui+0x64,0)
    m.w(net,vt);m.w(vt+0x3c,send);m.w(m.stack,m.stop,service_id);sent=[]
    def hook(uc,a,size,user):
        sp=uc.reg_read(m.spreg)
        if a==0x813860:m.ret(net)
        elif a==send:
            obj=m.r(sp+4);assert (m.r(obj),m.r(obj+4))==(0x227bfdc,0xc4276)
            fields=tuple(m.r(obj+i) for i in (8,12,16));assert fields==(item_key,0,1)
            sent.append(fields);uc.emu_stop()
        elif a==0x164903f:uc.emu_stop()
    m.run(0x1648d00,hook)
    assert bool(sent)==(service_id==496)
    return {'service':service_id,'sent':sent}


def main():
    sources={};archives={k:PfsArchive(ROOT.parent/f'artres/{k}.pfs') for k in ('config','map')}
    def read(archive,name):
        p=archives[archive];raw=p.read(name);e=p.entries[name]
        sources[name]={'archive':archive,'bytes':len(raw),'crc32':hex(e.crc),'sha256':hashlib.sha256(raw).hexdigest()}
        return decode(raw)
    services={r.get('id'):{'attributes':dict(r.attrib),'lists':{c.tag:[v.text for v in c] for c in r}}
              for r in read('config','autoconfig/knight.gsp.npc.cnpcserverconfig.xml') if r.get('id') in ('495','496','540')}
    fees=[dict(r.attrib) for r in read('config','autoconfig/knight.gsp.item.cnpcidentifyneedmoneyconfig.xml')]
    npcs={r.get('id'):dict(r.attrib) for r in read('config','autoconfig/knight.gsp.npc.cnpcconfig.xml') if r.get('id')=='10890'}
    placements=[]
    for name in archives['map'].entries:
        if '1007' in name and name.endswith('/npc.xml'):
            root=read('map',name)
            for i,r in enumerate(root.iter()):
                if r.get('id')=='10890':placements.append({'entry':name,'index_in_iter':i,'attributes':dict(r.attrib)})
    codec=[]
    request_cases=[((),1,NPC_KEY),((91,),1,NPC_KEY),((91,92),1,NPC_KEY),
                   ((92,91,92),1,NPC_KEY),((-2147483648,0,2147483647),-2147483648,0xfedcba9800002a8a),
                   ((91,),2147483647,0), (tuple(range(1,128)),1,NPC_KEY),
                   (tuple(range(1,129)),1,NPC_KEY)]
    for keys,mode,npc_key in request_cases:
        body=request_body(keys,mode,npc_key)
        codec.append({'name':'CRequestEquipsIsIdentify','keys':keys,'mode':mode,'npc_key':npc_key,
                      'body':roundtrip(0xe6c980,0xe6cae0,0xe6ca20,body)})
    state_cases=[(((91,0),(92,1)),1,NPC_KEY),((),-2147483648,0),
                 (((92,1),(91,0),(92,-2147483648)),2147483647,0xfedcba9800002a8a),
                 (((2147483647,2147483647),),2,NPC_KEY),
                 (tuple((i,0) for i in range(1,129)),1,NPC_KEY)]
    for entries,mode,npc_key in state_cases:
        codec.append({'name':'SSendEquipsIdentifyState','entries':entries,'mode':mode,'npc_key':npc_key,
                      'body':roundtrip(0xf04490,0xf04e70,0xf04f10,state_body(entries,mode,npc_key))})
    for fields in ((91,0,1),(91,92,2),(-1,-2,-3),(-2147483648,0,2147483647)):
        codec.append({'name':'CIdentifyEquip','fields':fields,'body':roundtrip(0xdc78e0,0xe55760,0xdc7980,struct.pack('>iii',*fields))})
    codec_negative=[]
    for key in (0,-1,-2147483648):
        codec_negative.append({'name':'SSendEquipsIdentifyState','key':key,
                               'body':codec_rejects(0xf04490,0xf04e70,0xf04f10,state_body(((key,0),)))})
    for name,ctor,marshal,dec,body in (
            ('CRequestEquipsIsIdentify',0xe6c980,0xe6cae0,0xe6ca20,request_body((91,))),
            ('SSendEquipsIdentifyState',0xf04490,0xf04e70,0xf04f10,state_body(((91,0),))),
            ('CIdentifyEquip',0xdc78e0,0xe55760,0xdc7980,struct.pack('>iii',91,0,1))):
        codec_negative.append({'name':name,'reason':'truncated final int32',
                               'body':codec_rejects(ctor,marshal,dec,body[:-1])})
    menu=[menu495(keys) for keys in ((),(91,92))]
    states=[response_handler(i) for i in (1,2)]
    states.extend([response_handler(1,((91,1),(91,0))),response_handler(1,((91,-1),)),
                   response_handler(1,((91,1),),owned=False),response_handler(1,())])
    price=[selection_fee(int(r['id']),int(r['needmoney'])) for r in fees]
    for c,r in zip(price,fees):assert c['events'][-1]=={'fee_read':int(r['needmoney'])}
    chain=selection_fee(50,15000,confirm_chain=True)
    negative=[selection_fee(50,15000,identified=1),selection_fee(50,15000,count=0),
              selection_fee(50,15000,count=2),selection_fee(151,None),selection_fee(51,None)]
    negative.append(selection_fee(50,15000,kind=18))
    for r in negative:assert 'rejected_at' in r['events'][-1]
    confirm=[confirm496(496),confirm496(497)]
    regions=[(0x1638310,0xf6),(0x109e994,0x30),(0x1688990,0x20),(0x1688170,0x170),
             (0x168830f,0x106),(0x1073110,0x16),(0x1648fb0,0x4b),(0x10934a0,0xa4),
             (0xe6c980,0x54),(0xe6ca20,0x13b),(0xdc78e0,0x1b),(0xe55760,0x2e),
             (0x1648a80,0x98),(0x8703b6,0x2c),(0xf04e10,0x51),(0xf04f10,0xd5),
             (0xf04d80,0x90),(0xf047a0,0x8b),(0xdc7900,0x4),(0xdc7980,0xc9),
             (0x10f25b0,0x100),(0xe6cae0,0x7d),(0xf04e70,0x9b),(0xf04ff0,0x120),
             (0x1074d10,0x2f),(0x1688170,0x306)]
    out=ROOT/'evidence'
    with (out/'npc-identification-native-disassembly.txt').open('w',encoding='utf8') as f:
        with contextlib.redirect_stdout(f):
            for a,n in regions:print('\nREGION',hex(a));disasm(a,n)
    report={'image_sha256':hashlib.sha256(DATA).hexdigest(),'sources':sources,'services':services,'fees':fees,
            'npc_candidates':npcs,'placements':placements,'service495_binding_proven':False,
            'codec':codec,'codec_negative':codec_negative,'menu495':menu,'state_handler':states,'selection_fees':price,'negative_selection':negative,
            'confirmation':confirm,'quote_confirmation_chain':chain,
            'proof_limits':{
                'fee_level_getter':'native 0x1074d10 called by 0x1688170',
                'fee_level_input':'explicit wrapper+0x28 layout fixture; CItemAttr-to-wrapper copy not traced',
                'fee_level_template_field_proven':False,
                'fee_lookup':'Adapter precise PFS rows, not original XML cache initialization',
                'kind8_input':'layout fixture; does not prove all ordinary six-slot template eligibility',
                'kind18_negative':'decimal18 = hex0x12; native low nibble2 != equipment category8',
                'native_special_level_rule':'full kind 0x1c8/0x2c8/0x3c8: bean+0xd0 when 0<value<=1000, otherwise wrapper+0x28; static only',
                'final_result_generation':'unknown; query state write is not settlement',
                'currency_and_transaction':'unknown; no permission inferred from codec'},
            'server_formula_restored':False,'native_gui_verified':False,'runtime_changed':False}
    (out/'npc-identification-native.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print('PASS',len(codec)+len(codec_negative)+len(menu)+len(states)+len(price)+len(negative)+len(confirm)+1,'offline identification cases')


if __name__=='__main__':main()
