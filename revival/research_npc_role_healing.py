"""Primary offline NPC role-healing dispatch evidence; never access live state."""
import json
import struct
import hashlib
import argparse
from pathlib import Path
from native_inspect import BASE,DATA,u32,disasm
from research_npc_submenu import Machine

ROOT=Path(__file__).parent
IDS=(92,294,459,1957,2037)


def dispatch(sid,*,family_current=True,family_low_matches=True,family_high_matches=True):
    from unicorn.x86_const import UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP
    m=Machine();uc=m.uc
    net,vt,send,close,family,role=0x5020000,0x5021000,0x5022000,0x5023000,0x5024000,0x5025000
    m.w(net,vt);m.w(vt+0x3c,send);m.w(m.ui+4,vt);m.w(vt+4,close)
    m.w(m.ui+0xd0,0x86,0x12345678,10086);m.w(m.stack+0x14,sid)
    m.w(0x2945570,family);m.w(0x2944564,role)
    m.w(family+0xd0,1 if family_current else 0);m.w(family+0xd8,123,0);m.w(role+0x30,123,0)
    if not family_low_matches:m.w(family+0xd8,124)
    if not family_high_matches:m.w(family+0xdc,1)
    events=[];branches=[]
    def hook(uc,a,size,user):
        sp=uc.reg_read(m.spreg)
        if a in (0x163f057,0x163f062,0x163f06e):events.append({'end':hex(a)});uc.emu_stop()
        elif a==0x813860:m.ret(net)
        elif a==send:
            obj=m.r(sp+4);vtable=m.r(obj)
            from verify_social_native import native_payload
            from native_gameplay_probe import probe
            captured=bytes(uc.mem_read(obj,32))
            payload=native_payload(u32(vtable),raw=[(0,captured)])
            assert payload==struct.pack('>Qi',0x1234567800000086,sid)
            _,decoded=probe(0x837400,0x83b5a0,0x8392d0,payload=payload)
            assert struct.unpack_from('<Qi',decoded,8)==(0x1234567800000086,sid)
            events.append({'send':hex(a),'vtable':hex(vtable),'type':hex(m.r(obj+4)),
                           'object_hex':captured.hex(),'native_marshaled_body':payload.hex(),
                           'native_marshal':hex(u32(vtable)),'native_decode':'0x8392d0',
                           'vtable_functions':[hex(u32(vtable+i*4)) for i in range(9)]})
            m.ret(1,4)
        elif a==close:events.append({'window_virtual_call':hex(a)});m.ret()
        elif a==0x1919184:m.ret(uc.reg_read(m.axreg))
        elif a==0x15bb820:
            events.append({'local_feedback':hex(a),'args':[hex(m.r(sp+i)) for i in (4,8,12)],
                           'argument_values':[hex(m.r(m.r(sp+i))) for i in (4,8,12)]});uc.emu_stop()
        elif a in (0x1637801,0x163aed1,0x1627be0,0x1633870,0x148c1f0,0x29d2b17,0x29ccf19,0x8281d9):branches.append(hex(a))
    uc.reg_write(UC_X86_REG_ESI,m.ui);uc.reg_write(UC_X86_REG_EDI,sid);uc.reg_write(UC_X86_REG_EBP,0)
    m.run(0x1636d06,hook)
    return {'service':sid,'family_current_fixture':family_current,'family_low_matches':family_low_matches,
            'family_high_matches':family_high_matches,'branches':branches,'events':events}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--disasm',choices=('guild_dispatch','guild_predicate','generic_dispatch','generic_body','marshal'))
    args=parser.parse_args()
    if args.disasm:
        disasm(*{'guild_dispatch':(0x1637801,0x4b),'guild_predicate':(0x148c1f0,0x2d),
                 'generic_dispatch':(0x163aed1,9),'generic_body':(0x1627be0,0xbc),'marshal':(0x83b5a0,0x62)}[args.disasm]);return
    from pfs import PfsArchive
    from bxml import decode
    from inspect_client import catalog_rows
    archive=PfsArchive(ROOT.parent/'artres/config.pfs');name='autoconfig/knight.gsp.npc.cnpcserverconfig.xml'
    raw=archive.read(name);rows=catalog_rows(decode(raw));catalog={int(r['attributes']['id']):r for r in rows}
    result={'image_sha256':hashlib.sha256(DATA).hexdigest(),'config':{'path':name,'sha256':hashlib.sha256(raw).hexdigest(),'crc32':archive.entries[name].crc},
            'original_rows':{str(i):catalog[i] for i in IDS},
            'original_menu_parents':{str(i):[p for p,r in catalog.items() if str(i) in r.get('lists',{}).get('childservice',())] for i in IDS},
            'dispatch':[dispatch(i) for i in IDS]+[dispatch(92,family_current=False),dispatch(92,family_low_matches=False),dispatch(92,family_high_matches=False)],
            'source_status':'client_verified','execution_scope':'original menu switch, predicate, generic construction and send boundary; original marshal/decode',
            'gui_verified':False,'server_healing_effect_verified':False,'production_modified':False,'live_database_accessed':False}
    msg_name='autoconfig/knight.gsp.message.cmessagetip.xml';msg_raw=archive.read(msg_name)
    msg_rows=catalog_rows(decode(msg_raw))
    result['local_feedback_source']={'path':msg_name,'sha256':hashlib.sha256(msg_raw).hexdigest(),'crc32':archive.entries[msg_name].crc,
        'row':next(r for r in msg_rows if int(r['attributes']['id'])==0x22367)}
    for case in result['dispatch'][:5]:
        assert '0x1633870' not in case['branches'] and '0x1627be0' in case['branches']
        assert len([e for e in case['events'] if 'send' in e])==1
        assert case['events'][0]['type']=='0xc232b'
        assert case['events'][-1]=={'end':'0x163f057'}
    for case in result['dispatch'][5:]:
        assert '0x1627be0' not in case['branches']
        assert len(case['events'])==1 and case['events'][0]['argument_values'][0]=='0x22367'
        assert 'local_feedback' in case['events'][0]
    (ROOT/'evidence/npc-role-healing-native.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'cases':len(result['dispatch']),'native_send_and_codec_cases':5,'native_family_rejection_cases':3,
        'menu_parents':result['original_menu_parents'],'server_healing_effect_verified':False},indent=2))


if __name__=='__main__':main()
