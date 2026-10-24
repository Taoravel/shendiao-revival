"""Offline original x86 submenu and recovery dispatch; no live process or DB."""
import hashlib
import json
import struct
import argparse
from pathlib import Path
from native_inspect import BASE, DATA, u32, disasm

ROOT = Path(__file__).parent
ROWS = json.loads((ROOT/'catalogs/knight.gsp.npc.cnpcserverconfig.json').read_text(encoding='utf-8'))
CAT = {int(r['attributes']['id']): r for r in ROWS}


class Machine:
    def __init__(self):
        from unicorn import Uc, UC_ARCH_X86, UC_MODE_32
        from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_EAX, UC_X86_REG_ECX
        self.spreg,self.ipreg,self.axreg,self.cxreg=UC_X86_REG_ESP,UC_X86_REG_EIP,UC_X86_REG_EAX,UC_X86_REG_ECX
        self.uc=Uc(UC_ARCH_X86,UC_MODE_32)
        self.uc.mem_map(0,4096)
        self.uc.mem_map(BASE,(len(DATA)+4095)&~4095);self.uc.mem_write(BASE,DATA)
        self.uc.mem_map(0x5000000,0x400000)
        self.uc.mem_map(u32(0x2244554)&~4095,8192)
        self.uc.mem_write(u32(0x2244554),b'\xc3')
        self.ui,self.stack,self.stop=0x5001000,0x5100000,0x500f000
    def w(self,a,*v):self.uc.mem_write(a,struct.pack('<'+'I'*len(v),*v))
    def r(self,a):return struct.unpack('<I',self.uc.mem_read(a,4))[0]
    def string(self,a,text,heap):
        raw=text.encode('utf-16le');count=len(raw)//2
        self.uc.mem_write(a,bytes(28));self.w(a+20,count,max(7,count))
        if count<=7:self.uc.mem_write(a+4,raw+b'\0\0')
        else:self.w(a+4,heap);self.uc.mem_write(heap,raw+b'\0\0')
    def read_string(self,a):
        count=self.r(a+20);ptr=a+4 if self.r(a+24)<8 else self.r(a+4)
        return bytes(self.uc.mem_read(ptr,count*2)).decode('utf-16le') if count else ''
    def ret(self,value=0,cleanup=0):
        sp=self.uc.reg_read(self.spreg);target=self.r(sp)
        self.uc.reg_write(self.axreg,value);self.uc.reg_write(self.spreg,sp+4+cleanup);self.uc.reg_write(self.ipreg,target)
    def run(self,start,hook):
        from unicorn import UC_HOOK_CODE
        trace=[]
        self.uc.hook_add(UC_HOOK_CODE,lambda uc,a,s,u: (trace.append(hex(a)), trace.pop(0) if len(trace)>12 else None))
        self.uc.hook_add(UC_HOOK_CODE,hook)
        self.uc.reg_write(self.spreg,self.stack);self.uc.reg_write(self.cxreg,self.ui)
        try:self.uc.emu_start(start,self.stop,count=30000)
        except Exception as error:
            raise RuntimeError(f'Native probe stopped at {self.uc.reg_read(self.ipreg):x}, sp={self.uc.reg_read(self.spreg):x}; trace={trace}') from error


def click(sid,level=0):
    """Execute menu's real early local dispatch, nonempty branch and jump table.

    Configuration lookup/copy and UI renderer are dependency adapters, not
    claims of a fully running UI. Original 1633030 /741740/branch code executes.
    """
    from unicorn.x86_const import UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBX
    m=Machine();uc=m.uc
    item,manager,vt,lookup,cfg,child,other=0x5003000,0x5004000,0x5004100,0x5004200,0x5005000,0x5006000,0x5007000
    m.w(item+0x30,sid,0);m.w(m.ui+0x20,level)
    m.w(manager,vt);m.w(vt+8,lookup);m.w(cfg,sid,int(CAT[sid]['attributes'].get('icon',0)))
    ids=list(map(int,CAT[sid].get('lists',{}).get('childservice',())))
    m.w(child,*ids);m.w(cfg+0x24,0,child,child+len(ids)*4,child+len(ids)*4);m.w(other,0xffffffff)
    m.string(cfg+8,CAT[sid]['attributes'].get('servicedescribe',''),0x5010000)
    cached=((0x24,0x34,0x5009000,(295,170),'ROOT'),
            (0x50,0x60,0x5009100,(13,10001),'TIER1'),
            (0x7c,0x8c,0x5009200,(10,11,12,10002),'TIER2'))
    for vo,to,buffer,values,text in cached:
        m.w(buffer,*values);m.w(m.ui+vo,0,buffer,buffer+len(values)*4,buffer+len(values)*4)
        m.string(m.ui+to,text,0x5011000)
    close_vtable,close=0x500a000,0x500a100
    m.w(m.ui+4,close_vtable);m.w(close_vtable+4,close)
    events=[]
    def hook(uc,a,size,user):
        sp=uc.reg_read(m.spreg)
        if a in (0x163f062,0x163f06e):events.append({'end':hex(a)});uc.emu_stop()
        elif a==0x89e000:m.ret(manager)
        elif a==lookup:
            assert m.r(sp+4)==sid;m.ret(cfg,4)
        elif a==0xce5230:
            assert m.r(sp+4)==cfg
            uc.mem_write(uc.reg_read(m.cxreg),bytes(uc.mem_read(cfg,0x6c)));m.ret(uc.reg_read(m.cxreg),4)
        elif a==0x1631980:
            vec,text=m.r(sp+4),m.r(sp+8)
            begin,end=m.r(vec+4),m.r(vec+8)
            values=[m.r(p) for p in range(begin,end,4)] if begin else []
            events.append({'builder':hex(a),'level':m.r(m.ui+0x20),'vector_address':hex(vec),'children':values,'text_address':hex(text),'text':m.read_string(text)})
            m.ret(cleanup=8)
        elif a==close:
            events.append({'window_virtual_call':hex(a),'receiver':hex(uc.reg_read(m.cxreg)),'vtable_slot':4});m.ret()
        elif a==0x1636d06 and sid in (170,295,10001,10002,10003,10004):
            raise AssertionError('Local-only action reached server service dispatch')
        elif a==0x1919184:m.ret(uc.reg_read(m.axreg))
        elif a==u32(0x2244554):m.ret(0) # empty webaddress vs original nonempty sentinel
        elif a==0x89ee50:m.ret(manager)
        elif a==0x1636c96:uc.reg_write(m.axreg,other) # other config lookup is absent
        elif a==0x162f080:m.ret(0,4) # unrelated shop filter
        elif a==0x1633870:events.append({'recovery_dispatch':m.r(sp+4)});uc.emu_stop()
        elif a==0x813860:raise AssertionError('Unexpected network manager on local menu branch')
    uc.reg_write(UC_X86_REG_ESI,m.ui);uc.reg_write(UC_X86_REG_EDI,item);uc.reg_write(UC_X86_REG_EBX,0)
    m.run(0x1636b8b,hook)
    return {'service':sid,'initial_level':level,'final_level':m.r(m.ui+0x20),'events':events}


def recovery(sid,cost=7,cash=100):
    """Run original checks, constructor and submission; adapt cost getters/UI/network."""
    m=Machine();uc=m.uc;role,wallet,net,vt,send,close=0x5003000,0x5004000,0x5005000,0x5006000,0x5007000,0x5008000
    key=0x1234567800000086
    m.w(m.stack,m.stop,sid);m.w(m.ui+0xd0,key&0xffffffff,key>>32)
    m.w(0x2944550,role);m.w(0x2944628,wallet);m.w(wallet+0xb0,cash,0)
    m.w(net,vt);m.w(vt+0x3c,send);m.w(m.ui+4,vt);m.w(vt+4,close)
    sent=[];checks=[]
    def hook(uc,a,size,user):
        sp=uc.reg_read(m.spreg)
        if a in (0x11360e0,0x1136290):checks.append(hex(a));m.ret(cost)
        elif a==0x813860:m.ret(net)
        elif a==send:
            obj=m.r(sp+4);kind=m.r(obj+4)
            assert kind==0xc2333
            low,high,k=m.r(obj+8),m.r(obj+12),m.r(obj+16)
            sent.append({'type':hex(kind),'npc_key':(high<<32)|low,'kind':k,'constructor_vtable':hex(m.r(obj))})
            m.ret(1,4)
        elif a==close:m.ret()
        elif a==0x1919184:m.ret(uc.reg_read(m.axreg))
        elif a==0x1633bd5:uc.emu_stop() # actual no-send feedback path
    m.run(0x1633870,hook)
    return {'service':sid,'cost_adapter':cost,'cash':cash,'native_cost_calls':checks,'sent':sent}


def graph():
    children={i:tuple(map(int,r.get('lists',{}).get('childservice',()))) for i,r in CAT.items()}
    missing=[{'parent':p,'missing_child':c} for p,cs in children.items() for c in cs if c not in CAT]
    cycles=set()
    def visit(i,path):
        if i in path:
            cycle=path[path.index(i):];variants=[tuple(cycle[j:]+cycle[:j]) for j in range(len(cycle))]
            cycles.add(min(variants));return
        for c in children.get(i,()):visit(c,path+[i])
    for i in CAT:visit(i,[])
    return {'service_count':len(CAT),'parents_with_children':sum(bool(c) for c in children.values()),'edges':sum(map(len,children.values())),
            'missing':missing,'cycles':[list(c) for c in sorted(cycles)],'rows':{str(i):CAT[i] for i in (10,11,12,170,295,1277,10001,10002,10003,10004)}}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--disasm',choices=('submenu','back','recovery','constructor','config_description'))
    args=parser.parse_args()
    if args.disasm:
        disasm(*{'submenu':(0x1636b8b,0xb4),'back':(0x1633364,0x85),'recovery':(0x1633a93,0x1a0),'constructor':(0x1627990,0x27),'config_description':(0xa711b7,0x8e)}[args.disasm]);return
    from pfs import PfsArchive
    from bxml import decode
    from inspect_client import catalog_rows
    archive=PfsArchive(ROOT.parent/'artres/config.pfs')
    name='autoconfig/knight.gsp.npc.cnpcserverconfig.xml'
    raw=archive.read(name)
    original=catalog_rows(decode(raw))
    semantic=lambda rows:[(r['attributes'],r['lists']) for r in rows]
    assert semantic(original)==semantic(ROWS),'Original PFS and saved catalog semantic fields differ'
    result={'image_sha256':hashlib.sha256(DATA).hexdigest(),'base':hex(BASE),'click_cases':[click(295,i) for i in (0,1,2)],
            'back_cases':[click(10001,i) for i in (1,2,3)],'leaf_cases':[click(i) for i in (10,11,12)],
            'navigation_cases':[click(sid,i) for sid in (10002,10003,10004) for i in (0,1,2,3)],
            'information_cases':[click(170,i) for i in (0,1,2)],
            'recovery_cases':[recovery(i) for i in (10,11,12)]+[recovery(10,-1),recovery(11,0),recovery(12,7,1)],'graph':graph(),
            'production_modified':False,'gui_verified':False,'network_or_db_used':False}
    result['original_config']={'path':name,'crc32':archive.entries[name].crc,'sha256':hashlib.sha256(raw).hexdigest(),'all_attributes_and_lists_match':True,'catalog_pretty_print_whitespace_ignored':True}
    result['native_jump_targets']={str(sid):hex(u32(0x163f09c+DATA[0x163f1c0-BASE+sid-2]*4)) for sid in (10,11,12)}
    for c in result['click_cases']:assert c['events'][0]['children']==[10,11,12,10001] and c['final_level']==c['initial_level']+1
    for c in result['back_cases']:
        assert c['events'][0]['vector_address']==hex(0x5001000+0x24) and c['final_level']==0
        assert c['events'][0]['children']==[295,170] and c['events'][0]['text']=='ROOT'
        assert c['events'][-1]=={'end':'0x163f06e'}
    for c in result['navigation_cases']:
        if c['service']==10004:
            assert c['events']==[{'window_virtual_call':'0x500a100','receiver':'0x5001004','vtable_slot':4},{'end':'0x163f06e'}]
            assert c['final_level']==c['initial_level']
        else:
            target=1 if c['service']==10002 else 2
            expected=(0x50,0x60,[13,10001],'TIER1') if target==1 else (0x7c,0x8c,[10,11,12,10002],'TIER2')
            event=c['events'][0]
            assert c['final_level']==target and event['vector_address']==hex(0x5001000+expected[0])
            assert event['text_address']==hex(0x5001000+expected[1]) and event['children']==expected[2] and event['text']==expected[3]
            assert c['events'][-1]=={'end':'0x163f06e'}
    for c in result['information_cases']:
        assert c['events'][0]['children']==[10001] and c['final_level']==c['initial_level']+1
        assert c['events'][0]['text']==CAT[170]['attributes']['servicedescribe']
        assert c['events'][-1]=={'end':'0x163f062'}
    for c in result['leaf_cases']:assert c['events']==[{'recovery_dispatch':c['service']}]
    for c,k in zip(result['recovery_cases'][:3],(2,3,4)):
        assert len(c['sent'])==1 and c['sent'][0]['kind']==k
        assert c['sent'][0]['npc_key']==0x1234567800000086 and c['sent'][0]['type']=='0xc2333'
    for c in result['recovery_cases'][3:]:assert not c['sent']
    (ROOT/'evidence/npc-submenu-native.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'image_sha256':result['image_sha256'],'original_config':result['original_config'],
        'native_cases':sum(len(result[k]) for k in ('click_cases','back_cases','leaf_cases','recovery_cases','navigation_cases','information_cases')),
        'graph':{k:v for k,v in result['graph'].items() if k!='rows'}},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
