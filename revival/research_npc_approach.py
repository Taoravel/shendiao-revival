"""Offline NPC approach research; never opens a live process or database."""
import struct
import hashlib
import json
from pathlib import Path
from native_inspect import BASE, DATA, u32, disasm
import capstone
import contextlib
from research_npc_submenu import Machine

ROOT=Path(__file__).parent


def inspect_approach(dx,dy,collision=1,template=10157,*,npc_model_point=(100,100),actor_model_point=None):
    """Original target interaction with explicit model-API coordinates.

    Absolute points are model coordinates, not claimed logical-map positions.
    The original entity getters/conversion still execute. Callers must prove
    their logical-to-model mapping separately before asserting map behavior.
    """
    npc_point=npc_model_point
    actor_point=(npc_point[0]+dx,npc_point[1]+dy) if actor_model_point is None else actor_model_point
    if (any(type(point) is not tuple or len(point)!=2 for point in (npc_point,actor_point))
            or any(type(value) is not int or not 0<=value<2**31 for point in (npc_point,actor_point) for value in point)):
        raise ValueError('Explicit nonnegative signed32 model API coordinate tuples required')
    from unicorn.x86_const import UC_X86_REG_EDX
    m=Machine();npc=0x5003000
    m.w(m.stack,m.stop,npc);m.w(npc,0x22985e4)
    m.w(npc+0x10,1,1007);m.uc.mem_write(npc+0x148,b'\1');m.uc.mem_write(npc+0x18,b'\1')
    m.w(npc+0x150,template)
    m.w(m.ui,0x5005000)
    for i in range(0,0x400,4):m.w(0x5005000+i,0x5006000+i)
    # Execute both real entity coordinate getters; adapt only the model API.
    m.w(0x5005000+0xd0,0x11f6540);m.w(0x5005000+0xd4,0x11f6450)
    actor_model,npc_model,model_vt,model_getter=0x500c000,0x500d000,0x500e000,0x500b000
    m.w(m.ui+0x48,actor_model);m.w(npc+0x48,npc_model)
    m.w(actor_model,model_vt);m.w(npc_model,model_vt);m.w(model_vt+0x38,model_getter)
    m.uc.mem_write(0x5007000,b'\xd9\xfa\xc3') # host sqrt ABI adapter only
    events=[];last=[];comparisons=[];float_trace=[];geometry=[];model_phase=[False]
    net,vt,send=0x5008000,0x5009000,0x500a000
    m.w(net,vt);m.w(vt+0x3c,send)
    decoder=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
    def h(uc,a,s,u):
        sp=uc.reg_read(m.spreg)
        if a==0x29d6f58:events.append({'integer_distance_compare':uc.reg_read(m.axreg),'limit':13})
        if a==0x6bba90:
            events.append({'distance_float_points':[struct.unpack('<ff',uc.mem_read(m.r(sp+i),8)) for i in (4,8)]})
        if a==0x11fe700:events.append({'unadapted_action_dependency':hex(a)});uc.emu_stop()
        if BASE<=a<BASE+len(DATA):
            ins=next(decoder.disasm(bytes(uc.mem_read(a,s)),a),None)
            if model_phase[0] and ins:geometry.append((hex(a),bytes(uc.mem_read(a,s)).hex(),ins.mnemonic+' '+ins.op_str))
            if ins and ins.mnemonic.startswith(('fcomp','fcomi','comis','ucomis')):
                events.append({'fpu_compare':hex(a),'instruction':ins.mnemonic+' '+ins.op_str})
            if ins and (ins.mnemonic.startswith('f') or ins.mnemonic.endswith(('ss','ps'))):
                float_trace.append((hex(a),ins.mnemonic+' '+ins.op_str))
            if ins and ins.mnemonic=='cmp':
                comparisons.append((hex(a),ins.op_str))
                if len(comparisons)>25:comparisons.pop(0)
        if a==0x11d01f0:
            events.append({'unprepared_map_lookup_return':hex(m.r(sp))});uc.emu_stop()
        if a==0x11dc7d0:
            events.append({'scene_segment_query':hex(a),'adapter_result':0});m.ret(0,8);return
        if a==0x5006004:m.ret(1);return # host visible getter dependency
        if a in (0x11d1870,0x11d5260):
            events.append({'scene_lookup':hex(a)});m.ret(npc,4 if a==0x11d1870 else 8);return
        if a==0x19196a4:uc.reg_write(m.ipreg,0x5007000);return
        if a==0x11f6450:model_phase[0]=True
        if a==model_getter:
            is_npc=uc.reg_read(m.cxreg)==npc_model
            p=m.r(sp+4);point=npc_point if is_npc else actor_point
            events.append({'model_position_adapter':'npc' if is_npc else 'actor','point':point})
            m.w(p,*point);m.ret(p,4);return
        if a==0x11c5c00:
            events.append({'collision_query':[m.r(sp+i) for i in (4,8,12)],'adapter_result':collision})
            m.ret(collision,12);return
        if a==0x120eea0:
            events.append({'visit_ctor':hex(a),'key_words':[m.r(sp+4),m.r(sp+8)]})
        elif a==0x813860:m.ret(net);return
        elif a==send:
            obj=m.r(sp+4);assert m.r(obj+4)==0xc2329
            events.append({'visit_send':hex(m.r(obj+4)),'npc_key':m.r(obj+8)|(m.r(obj+12)<<32)})
            uc.emu_stop();return
        elif a==0x1215190:
            events.append({'dependency':hex(a),'args':[m.r(sp+i) for i in (4,8,12)]});uc.emu_stop()
        if 0x5006000<=a<0x5006400:
            events.append({'unadapted_virtual':hex(a-0x5006000)});uc.emu_stop()
        if not 0x29c0000<=a<0x29e0000:
            last.append(hex(a))
            if len(last)>25:last.pop(0)
        if a<BASE:events.append({'null_dependency':True});uc.emu_stop()
    error=None
    try:m.run(0x1215790,h)
    except Exception as e:error=str(e)
    return {'dx':dx,'dy':dy,'npc_model_point':npc_point,'actor_model_point':actor_point,
            'template':template,'collision_fixture':collision,'events':events,'error':error,
            'end':hex(m.uc.reg_read(m.ipreg)),'tail':last,'comparisons':comparisons,'float_trace':float_trace,
            'geometry_trace':geometry}


if __name__=='__main__':
    from pfs import PfsArchive
    from bxml import decode
    p=PfsArchive(ROOT.parent/'artres/config.pfs');name='autoconfig/knight.gsp.npc.cnpcconfig.xml';raw=p.read(name)
    configs={r.get('id'):dict(r.attrib) for r in decode(raw) if r.get('id') in ('10157','10498','10908')}
    result=[inspect_approach(x,y,c,t) for t in (10157,10498,10908) for c in (0,1)
            for x,y in ((0,0),(32,0),(300,0),(312,0),(0,200),(0,208),(100,100),(216,144))]
    for r in result:
        assert r['error'] is None and r['end'] in ('0x500a000','0x11fe700'),r
        has_visit=any('visit_send' in e for e in r['events'])
        distance=next(e['integer_distance_compare'] for e in r['events'] if 'integer_distance_compare' in e)
        assert has_visit==(distance<13)
        if r['template']==10498:assert not any('collision_query' in e or 'scene_segment_query' in e for e in r['events'])
    trace=result[2]['geometry_trace']
    with (ROOT/'evidence/npc-approach-native-execution.txt').open('w',encoding='utf8') as f:
        for a,b,ins in trace:f.write(f'{a} {b} {ins}\n')
    for r in result:r.pop('geometry_trace')
    report={'image_sha256':hashlib.sha256(DATA).hexdigest(),'probes':result,'native_gui_verified':False,
            'source':{'entry':name,'bytes':len(raw),'crc32':hex(p.entries[name].crc),'sha256':hashlib.sha256(raw).hexdigest()},'npc_configs':configs,
            'server_radius_proven':False,'live_client_accessed':False}
    (ROOT/'evidence/npc-approach-native.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    with (ROOT/'evidence/npc-approach-native-disassembly.txt').open('w',encoding='utf8') as f:
        with contextlib.redirect_stdout(f):
            for a,n in ((0x12163e0,0xa5),(0x1215790,0x39),(0x29cb006,0x1e),(0x29d6f58,0x10),
                        (0x11c5ba0,0x2e),
                        (0x6bba90,0x3d),(0x5a5370,0x1d),(0x11f6450,0x31),(0x11f6540,0x91),
                        (0x120eea0,0x1e)):
                print('\nREGION',hex(a));disasm(a,n)
    print('PASS',len(result),'controlled original approach cases; radius/real path remain unverified')
