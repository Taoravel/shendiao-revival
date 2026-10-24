"""Offline original disappearance consumers, no runtime policy or live state."""
import json
import hashlib
import struct
import argparse
from pathlib import Path
from research_npc_submenu import Machine
from native_inspect import BASE,DATA,disasm,u32

ROOT=Path(__file__).parent


def consume(row,state,*,timer=-1,model=True):
    m=Machine();uc=m.uc
    manager,tablevt,lookup,bean,modelptr,modelvt=0x5020000,0x5021000,0x5022000,0x5023000,0x5024000,0x5025000
    m.w(0x2945aec,manager);m.w(manager+0x9f0,tablevt);m.w(tablevt+8,lookup)
    a=row['attributes'];ident=int(a['id']);p1=int(a.get('para1',0));p2=int(a.get('para2',0))
    m.w(bean,ident,p1,p2);m.string(bean+12,a.get('para3',''),0x5029000)
    if ident==99999:m.w(bean,0xffffffff)
    m.w(m.ui+0x150,ident);m.w(m.ui+0x258,state);m.w(m.ui+0x28c,timer&0xffffffff)
    npcvt,position,action,stopmove,show,speed=0x5026000,0x5026100,0x5026200,0x5026300,0x5026400,0x5026500
    m.w(m.ui,npcvt);m.w(npcvt+0xd0,position);m.w(npcvt+0x50,action);m.w(npcvt+0x130,stopmove);m.w(npcvt+0x110,show)
    m.w(m.ui+0x44,modelptr if model else 0);m.w(modelptr,modelvt);m.w(modelvt+0x154,speed)
    m.w(m.stack,m.stop)
    # CRT sqrt adapter uses equivalent x87 instruction; no model/branch replacement.
    sqrt_adapter=0x5026600;uc.mem_write(sqrt_adapter,b'\xd9\xfa\xc3')
    events=[]
    def hook(uc,addr,size,user):
        sp=uc.reg_read(m.spreg)
        if addr==m.stop:uc.emu_stop()
        elif addr==lookup:
            assert m.r(sp+4)==ident;events.append({'lookup':ident});m.ret(bean,4)
        elif addr==position:
            output=m.r(sp+4);m.w(output,(p1*16-300)&0xffffffff,(p2*16-400)&0xffffffff);m.ret(output,4)
        elif addr==action:
            events.append({'action':m.r(sp+4),'factor':struct.unpack('<f',uc.mem_read(sp+8,4))[0]});m.ret(cleanup=8)
        elif addr==stopmove:events.append({'npc_vt130':m.r(sp+4)});m.ret(cleanup=4)
        elif addr==speed:
            events.append({'model_speed_argument':struct.unpack('<f',uc.mem_read(sp+4,4))[0]});m.ret(cleanup=4)
        elif addr==0x1172b50:
            ptr=m.r(sp+4);events.append({'model_move':[m.r(ptr),m.r(ptr+4)],'flags':[m.r(sp+8),m.r(sp+12)]});m.ret(cleanup=12)
        elif addr==0x666b90:
            events.append({'native_float_to_int_input':list(struct.unpack('<ff',uc.mem_read(m.r(sp+4),8)))})
        elif addr==0x19196a4:uc.reg_write(m.ipreg,sqrt_adapter)
        elif addr==0x11fa3b0:
            events.append({'talk':m.read_string(m.r(sp+4)),'args':[m.r(sp+8),m.r(sp+12)]});m.ret(cleanup=12)
        elif addr==show:events.append({'npc_vt110':m.r(sp+4)});m.ret(cleanup=16)
        elif addr==0x8370a0:
            events.append({'text_resource_id':m.r(sp+8)});m.ret(m.r(sp+4))
        elif addr==0x11fce92:uc.reg_write(m.ipreg,0x11fce98) # string destructor host boundary
        elif addr==0x1919184:m.ret(uc.reg_read(m.axreg))
        elif addr==u32(0x2244554):
            # Adapt string equality only, preserving original branch on result.
            m.ret(1 if m.read_string(m.r(sp+4)) else 0)
    m.run(0x11fcc50,hook)
    assert uc.reg_read(m.ipreg)==m.stop
    return {'id':ident,'state_fixture':state,'timer_before':timer,'timer_after':struct.unpack('<i',uc.mem_read(m.ui+0x28c,4))[0],
            'fade_flag':uc.mem_read(m.ui+0x29d,1)[0],'events':events}


def fade(timer,delta,alpha,flag=0):
    from unicorn.x86_const import UC_X86_REG_ESI,UC_X86_REG_EBP
    m=Machine();uc=m.uc;vt,getter,setter=0x5020000,0x5021000,0x5022000
    m.w(m.ui,vt);m.w(vt+0x18,getter);m.w(vt+0x14,setter);m.w(m.ui+0x28c,timer);uc.mem_write(m.ui+0x29d,bytes([flag]))
    events=[]
    def hook(uc,a,size,user):
        sp=uc.reg_read(m.spreg)
        if a==0x11ff80c:uc.emu_stop()
        elif a==getter:m.ret(alpha)
        elif a==setter:events.append(m.r(sp+4)&255);m.ret(cleanup=4)
    uc.reg_write(UC_X86_REG_ESI,m.ui);uc.reg_write(UC_X86_REG_EBP,delta)
    m.run(0x11ff79a,hook)
    return {'timer_before':timer,'delta':delta,'alpha_before':alpha,'flag_before':flag,
            'timer_after':m.r(m.ui+0x28c),'fade_flag':uc.mem_read(m.ui+0x29d,1)[0],
            'ready_remove':uc.mem_read(m.ui+0x29c,1)[0],'alpha_calls':events}


def scene_cleanup(flag):
    from unicorn.x86_const import UC_X86_REG_ESI,UC_X86_REG_EDI
    m=Machine();uc=m.uc;head,node,vt,dtor=0x5020000,0x5021000,0x5022000,0x5023000
    m.w(head+4,0x5024000);m.w(node+0x18,m.ui);m.w(m.ui,vt);m.w(vt,dtor)
    uc.mem_write(m.ui+0x29c,bytes([flag]));events=[]
    def hook(uc,a,size,user):
        sp=uc.reg_read(m.spreg)
        if a==dtor:
            events.append({'virtual_destructor_receiver':hex(uc.reg_read(m.cxreg)),'delete_flag':m.r(sp+4)});m.ret(cleanup=4)
        elif a==0x11cf1f0:
            events.append({'erase_boundary':hex(a)});uc.emu_stop()
        elif a==0x11d235f:events.append({'kept':True});uc.emu_stop()
    uc.reg_write(UC_X86_REG_ESI,node);uc.reg_write(UC_X86_REG_EDI,head)
    m.run(0x11d2322,hook)
    assert events==([{'virtual_destructor_receiver':hex(m.ui),'delete_flag':1},{'erase_boundary':'0x11cf1f0'}] if flag else [{'kept':True}])
    return {'ready_remove':flag,'events':events}


def main():
    p=argparse.ArgumentParser();p.add_argument('--disasm',choices=('consumer','fade','scene_delete','loader','getter'));args=p.parse_args()
    if args.disasm:
        disasm(*{'consumer':(0x11fcc50,0x275),'fade':(0x11ff79a,0x72),'scene_delete':(0x11d2322,0x3d),'loader':(0x87ed46,0xa9),'getter':(0x89dfa0,11)}[args.disasm]);return
    from pfs import PfsArchive
    from bxml import decode
    from inspect_client import catalog_rows
    archive=PfsArchive(ROOT.parent/'artres/config.pfs');sources=[];tables={}
    for stem in ('cnpcdisappearconfig','cnpcconfig','cscenenpcconfig','cscenenpcbase'):
        name='autoconfig/knight.gsp.npc.'+stem+'.xml';raw=archive.read(name);rows=catalog_rows(decode(raw));tables[stem]=rows
        saved=json.loads((ROOT/'catalogs'/('knight.gsp.npc.'+stem+'.json')).read_text(encoding='utf-8'))
        project=lambda rs:[(r['attributes'],r['lists']) for r in rs]
        assert project(rows)==project(saved)
        sources.append({'path':name,'rows':len(rows),'crc32':archive.entries[name].crc,'sha256':hashlib.sha256(raw).hexdigest(),'all_attributes_lists_match':True})
    rows=tables['cnpcdisappearconfig'];catalog={int(r['attributes']['id']):r for r in tables['cnpcconfig']}
    cases=[consume(r,int(catalog[int(r['attributes']['id'])]['attributes']['hide'])) for r in rows]
    first=rows[0]
    cases.extend((consume(first,2),consume(first,3),consume(first,6),consume(first,5,timer=0),consume(first,5,timer=10),consume({'attributes':{'id':'99999'}},5)))
    fades=[fade(100,99,255),fade(100,100,255),fade(100,101,255),fade(0,60,255),fade(0,60,255,1),fade(0,60,10,1),fade(0,60,0,1),fade(0,5,255,1)]
    for row,case in zip(rows,cases):
        a=row['attributes'];state=case['state_fixture']
        assert state in (4,5) and case['timer_after']==(3200 if state==4 else 1500) and case['fade_flag']==0
        moves=[e for e in case['events'] if 'model_move' in e]
        assert len(moves)==1 and moves[0]['model_move']==[int(a['para1'])*24,int(a['para2'])*16]
        talks=[e for e in case['events'] if 'talk' in e]
        if state==4:assert len(talks)==1 and talks[0]['talk']==a['para3']
    assert cases[11]['events']==[] and cases[11]['timer_after']==-1
    assert cases[12]['timer_after']==1000 and cases[12]['events'][1]=={'text_resource_id':195}
    assert cases[13]['fade_flag']==1 and cases[16]['fade_flag']==1
    assert cases[14]['events']==[] and cases[15]['events']==[]
    assert fades[0]['timer_after']==1 and fades[0]['fade_flag']==0
    assert fades[1]['timer_after']==0 and fades[1]['alpha_calls']==[239]
    assert fades[2]['alpha_calls']==[239] and fades[3]['alpha_calls']==[]
    assert fades[4]['alpha_calls']==[245] and fades[5]['ready_remove']==1 and fades[5]['alpha_calls']==[0]
    assert fades[6]['ready_remove']==0 and fades[6]['alpha_calls']==[] and fades[7]['alpha_calls']==[255]
    result={'image_sha256':hashlib.sha256(DATA).hexdigest(),'sources':sources,'rows':rows,
        'npc_definition_attributes':{str(int(r['attributes']['id'])):catalog[int(r['attributes']['id'])]['attributes'] for r in rows},
        'consumer_cases':cases,'fade_cases':fades,'scene_cleanup_cases':[scene_cleanup(0),scene_cleanup(1)],
        'state_source_note':'state_fixture uses catalog hide values; init field assignment not proven',
        'production_modified':False,'gui_verified':False,'server_lifecycle_verified':False}
    (ROOT/'evidence/npc-disappear-native.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'consumer_cases':len(cases),'fade_cases':len(fades),'scene_cleanup_cases':2,'original_rows':len(rows),'passed':27,'gui_verified':False},indent=2))


if __name__=='__main__':main()
