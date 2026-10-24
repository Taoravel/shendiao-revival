"""Offline native service93/160/855 gating, UI storage, single submit and cost."""
import contextlib
import hashlib
import json
import struct
from pathlib import Path
from native_inspect import BASE, DATA, u32, vtables, disasm
from research_npc_submenu import Machine
from verify_equipment_native_cost import NativeCost
from verify_social_native import native_payload
from pfs import PfsArchive
from bxml import decode

ROOT=Path(__file__).parent


def classification_branch(tag):
    """Artificial raw tag only; never claims a real config item has this tag."""
    m=Machine();wrapper=0x5003000
    m.w(wrapper+8,(tag<<4)|8);m.w(m.stack,m.stop,wrapper,2)
    reached=[]
    def hook(uc,a,size,user):
        if a in (0x1073090,0x89d550):reached.append(a);uc.emu_stop()
    m.run(0x10dbb20,hook)
    expected=0x1073090 if 6<=tag<=11 else 0x89d550
    assert reached==[expected]
    return {'artificial_tag':tag,'first_dependency':hex(expected),
            'branch':'special' if expected==0x1073090 else 'ordinary',
            'real_item_mapping_verified':False,'getter_replaced':False}


def real_config_classification(attr):
    """Original initializer/config-copy prefix, fed two actual original row fields.

    Stop before string copy: this does not claim a fully initialized item/UI.
    """
    m=Machine();wrapper=m.ui
    manager,vt,lookup,row=(0x5003000+i*0x1000 for i in range(4))
    template,kind=int(attr['id']),int(attr['itemtypeid'])
    m.w(manager,vt);m.w(vt+8,lookup);m.w(row,template,kind)
    m.w(m.stack,m.stop,template)
    stages=['copy'];events=[]
    def hook(uc,a,size,user):
        sp=uc.reg_read(m.spreg)
        if stages[0]=='copy':
            if a==0x89d730:m.ret(manager)
            elif a==lookup:
                assert m.r(sp+4)==template
                m.ret(row,4)
            elif a==0x10728a5:
                assert m.r(wrapper+4)==template and m.r(wrapper+8)==kind
                events.append({'copied_id':m.r(wrapper+4),'copied_itemtypeid':m.r(wrapper+8)})
                uc.emu_stop()
        elif a in (0x1073090,0x89d550):events.append({'fee_branch_dependency':hex(a)});uc.emu_stop()
    m.run(0x1080720,hook)
    stages[0]='branch';m.w(m.stack,m.stop,wrapper,2)
    m.run(0x10dbb20,lambda *args:None)
    tag=(kind>>4)&15
    assert events[-1]=={'fee_branch_dependency':hex(0x1073090 if 6<=tag<=11 else 0x89d550)}
    return {'id':template,'name':attr.get('name'),'itemtypeid':kind,'tag':tag,
            'events':events,'copy_scope':'id and type prefix only; before string copy',
            'getter_replaced':False}


def payment_display(role_level,item_level):
    """Original level getters, wallet loads and signed64 quote comparison.

    Quote itself is a declared fixture; text rendering is skipped. No currency
    getter or level getter is replaced, and no live assets are used.
    """
    from unicorn import UC_HOOK_MEM_READ
    from unicorn.x86_const import UC_X86_REG_EDX,UC_X86_REG_EBP,UC_X86_REG_EDI
    m=Machine();anchor=m.ui
    role,wallet,window,item,bean,head,node,net,vt,send=(0x5003000+i*0x1000 for i in range(10))
    npc=0x1234567800000093
    cash,bound,quote=0x0000000200000011,0x00000001000000ff,0x0000000180000000
    m.w(0x2944550,role);m.w(0x2944628,wallet)
    # Real attribute map carries native level key490; original1135590 and STL
    # lookup4e8e00 execute, including checking this key, without a fake getter.
    m.w(role+0x168,head,1);m.w(head,node,node,node)
    m.uc.mem_write(head+0x15,b'\1')
    m.w(node,head,head,head,490,role_level)
    m.w(wallet+0xb0,cash&0xffffffff,cash>>32)
    m.w(wallet+0xc8,bound&0xffffffff,bound>>32)
    m.w(anchor+0x34,window);m.w(window+0x278,item)
    m.w(item,bean);m.w(item+8,8);m.w(item+0x28,item_level)
    m.w(bean+0x14,91)
    m.w(anchor+0x1b8,npc&0xffffffff,npc>>32,1,4)
    m.w(net,vt);m.w(vt+0x3c,send)
    reads=[];events=[];stage=['display']
    def read_hook(uc,access,address,size,value,user):
        if stage[0]=='display' and wallet+0xb0<=address<wallet+0xd0:
            reads.append({'offset':hex(address-wallet),'size':size})
    m.uc.hook_add(UC_HOOK_MEM_READ,read_hook)
    def hook(uc,a,size,user):
        sp=uc.reg_read(m.spreg)
        if stage[0]=='display':
            if a==0x10dbb20:
                assert m.r(sp+4)==item and m.r(sp+8)==1
                m.ret(quote&0xffffffff,8);uc.reg_write(UC_X86_REG_EDX,quote>>32)
            elif a==0x10dc149:
                amount=m.r(sp+0x1c)|(uc.reg_read(UC_X86_REG_EBP)<<32)
                events.append({'loaded_balance':amount,'label_id':hex(uc.reg_read(UC_X86_REG_EDI))})
                # Skip only UI/config/string formatting. Both wallet selection
                # and following original64-bit affordability comparison run.
                uc.reg_write(m.ipreg,0x10dc20a)
            elif a==0x10dc22a:
                events.append({'quote_color':hex(uc.reg_read(UC_X86_REG_EDI))});uc.emu_stop()
        else:
            if a==0x813860:m.ret(net)
            elif a==send:
                obj=m.r(sp+4)
                assert m.r(obj+4)==0xc0413
                fields=(m.r(obj+8),m.r(obj+16)|(m.r(obj+20)<<32),m.r(obj+24),m.r(obj+28))
                assert fields==(1,npc,4,91)
                events.append({'sent':fields});m.ret(1,4)
            elif a==0x10ddae1:uc.emu_stop()
    m.w(m.stack,m.stop);m.run(0x10dc090,hook)
    low=role_level<60 and item_level<60
    expected=bound if low else cash
    assert events[0]=={'loaded_balance':expected,'label_id':hex(0xc4c6 if low else 0xc37e)}
    assert events[1]=={'quote_color':hex(0xffff0000 if low else 0xff00ff00)}
    assert reads==[{'offset':hex(x),'size':4} for x in ((0xc8,0xcc) if low else (0xb0,0xb4))],reads
    stage[0]='confirm';m.ui=anchor+0x20;m.w(m.stack,m.stop,0)
    m.run(0x10dda40,lambda *args:None)
    wire=native_payload(0xe4cf30,scalars=[(8,1),(0x18,4),(0x1c,91)],raw=[(0x10,struct.pack('<q',npc))])
    assert wire==struct.pack('>iqii',1,npc,4,91) and len(wire)==20
    return {'role_level':role_level,'item_level':item_level,'cash':cash,'bound_silver':bound,
            'quote_fixture':quote,'wallet_reads':reads,'events':events,'wire':wire.hex(),
            'quote_adapter':True,'text_render_skipped':True,'currency_in_wire':False}


def vertical(sid,enabled=1,mismatch=0,column=4):
    from unicorn.x86_const import UC_X86_REG_ESI,UC_X86_REG_EBP
    m=Machine();anchor=m.ui
    manager,scene,dialog,window,item,bean,net,vt,send=(0x5003000+i*0x1000 for i in range(9))
    npc=0x1234567800000093
    m.w(0x2945570,manager);m.w(0x2944564,scene)
    m.w(manager+0xd0,enabled);m.w(manager+0xd8,13,27)
    m.w(scene+0x30,13^(1 if mismatch==1 else 0),27^(1 if mismatch==2 else 0))
    m.w(anchor+0xd0,npc&0xffffffff,npc>>32)
    m.w(m.stack,m.stop)
    m.w(net,vt);m.w(vt+0x3c,send)
    events=[];stage=['open']
    def hook(uc,a,size,user):
        sp=uc.reg_read(m.spreg)
        if stage[0]=='open':
            if a==0x16299a0:
                events.append({'open_args':[m.r(sp+4),m.r(sp+8),m.r(sp+12)]})
                m.ret(dialog)
            elif a in (0x10dc470,0x10dd800):m.ret()
            elif a==0x10de20f:
                events.append({'stored_method':m.r(dialog+0x1c0),
                               'stored_npc':m.r(dialog+0x1b8)|(m.r(dialog+0x1bc)<<32)})
                uc.emu_stop()
            elif a==0x163761e:events.append({'gate_rejected':True});uc.emu_stop()
        else:
            if a==0x813860:m.ret(net)
            elif a==send:
                obj=m.r(sp+4)
                assert m.r(obj)==0x2276c04 and m.r(obj+4)==0xc0413
                fields=(m.r(obj+8),m.r(obj+0x10)|(m.r(obj+0x14)<<32),m.r(obj+0x18),m.r(obj+0x1c))
                events.append({'sent':fields});m.ret(1,4)
            elif a==0x10ddae1:uc.emu_stop()
    m.uc.reg_write(UC_X86_REG_ESI,anchor);m.uc.reg_write(UC_X86_REG_EBP,0)
    m.run({93:0x16375e9,160:0x1636f1a,855:0x1639cec}[sid],hook)
    if events[-1].get('gate_rejected'):
        assert len(events)==1
        return {'service':sid,'enabled':enabled,'mismatch':mismatch,'events':events}
    expected={93:1,160:0,855:2}[sid]
    assert events[-1]=={'stored_method':expected,'stored_npc':npc}
    assert events[0]['open_args']==[expected,npc&0xffffffff,npc>>32]
    stage[0]='button';m.ui=dialog+0x20
    m.w(m.ui+0x14,window);m.w(window+0x278,item);m.w(item,bean);m.w(bean+0x14,91)
    m.w(m.ui+0x1a4,column);m.w(m.stack,m.stop,0)
    # Existing hook persists; second run installs only a no-op additional hook.
    m.run(0x10dda40,lambda *args:None)
    assert events[-1]['sent']==(expected,npc,column,91)
    wire=native_payload(0xe4cf30,scalars=[(8,expected),(0x18,column),(0x1c,91)],raw=[(0x10,struct.pack('<q',npc))])
    assert wire==struct.pack('>iqii',expected,npc,column,91)
    return {'service':sid,'column':column,'events':events,'wire':wire.hex()}


def main():
    evidence=ROOT/'evidence';p=PfsArchive(ROOT.parent/'artres/config.pfs');sources={}
    def config(name):
        raw=p.read(name);e=p.entries[name]
        sources[name]={'crc32':hex(e.crc),'length':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
        return decode(raw)
    labels={r.get('id'):dict(r.attrib) for r in config('autoconfig/knight.gsp.npc.cnpcserverconfig.xml') if r.get('id') in ('93','160','855','513')}
    fees=[dict(r.attrib) for r in config('autoconfig/knight.gsp.item.cequiprepairconfig.xml')]
    attrs={int(r.get('id')):dict(r.attrib) for r in config('autoconfig/knight.gsp.item.citemattr.xml')}
    equipment={int(r.get('id')):dict(r.attrib) for r in config('autoconfig/knight.gsp.item.cequipeffect.xml')}
    original_groups={tag:[a for a in attrs.values() if (int(a['itemtypeid'])&15)==8
                          and ((int(a['itemtypeid'])>>4)&15)==tag] for tag in range(6,12)}
    real_types=[real_config_classification(a) for group in original_groups.values() for a in group[:2]]
    real_types.append(real_config_classification(attrs[49009]))
    from types import SimpleNamespace
    from inventory import Inventory
    current=SimpleNamespace(items=attrs,equipment=equipment)
    for case in real_types:
        accepted=Inventory._ordinary_equipment(current,case['id'])
        case['current_ordinary_guard']=accepted
        assert accepted==(case['tag']<=5)
    assert vtables('.?AVCFactionManager@@')==[0x22b2900]
    assert vtables('.?AVCEquipRepairDlg@@')==[0x228e5f8]
    expected_targets={93:0x16375e9,160:0x1636f1a,855:0x1639cec}
    for sid,target in expected_targets.items():
        idx=DATA[0x163f1c0-BASE+sid-2] if sid<234 else DATA[0x163f5f0-BASE+sid-0x31d]
        table=0x163f09c if sid<234 else 0x163f578
        assert u32(table+4*idx)==target
    cases=[vertical(s, column=c) for s in (93,160,855) for c in (1,4)]
    cases += [vertical(93,enabled=0),vertical(93,mismatch=1),vertical(93,mismatch=2)]
    native=NativeCost();costs=[]
    for row in fees:
        level=int(row['id'])
        for method,field in ((0,'skillrepair'),(1,'familyrepair'),(2,'npcrepair')):
            native.w(native.wrapper+0x28,level);native.w(native.obj+0x5c,1)
            native.w(native.obj+0xc8,80,100)
            native.w(native.row,level,int(row['npcrepair']),int(row['familyrepair']),int(row['skillrepair']))
            native.w(native.stack,native.stop,native.wrapper,method)
            native.emu.reg_write(native.SP,native.stack)
            native.emu.emu_start(0x10dbb20,native.stop,count=10000)
            value=native.emu.reg_read(native.AX)
            assert native.emu.reg_read(native.IP)==native.stop and value==int(row[field])*20
            costs.append({'level':level,'method':method,'member':field,'missing':20,'color':1,'cost':value})
    payment=[payment_display(r,i) for r,i in ((59,59),(59,60),(60,59),(60,60))]
    branches=[classification_branch(tag) for tag in range(16)]
    regions=[(0x16375e9,0x65),(0x1636f1a,0x31),(0x1639cec,0x15),
             (0x148c1f0,0x2d),(0x815c90,0x6a),(0x14a1160,0x40),
             (0x10de1e0,0x47),(0x10dda40,0xa9),(0x10dbb20,0x19e),
             (0x86b4c6,0xa2),(0x10dc090,0x215),(0x1135590,0x1c),
             (0x1074d10,0x2f),(0x10dd610,0x7b),(0x86e8e7,0x30),
             (0x1080720,0x5a),(0x1072890,0x1f),(0x10e1dcb,0x12)]
    with (evidence/'npc-special-repairs-native-disassembly.txt').open('w',encoding='utf8') as f:
        with contextlib.redirect_stdout(f):
            for a,n in regions:print('\nREGION',hex(a));disasm(a,n)
    report={'image_sha256':hashlib.sha256(DATA).hexdigest(),'sources':sources,'labels':labels,
            'verticals':cases,'native_cost_cases':costs,'payment_display_controlled':payment,
            'raw_tag_branch_controlled':branches,
            'kind6_11_original_type_mapping':'original row fields through native initializer/copy prefix',
            'real_config_type_prefix':real_types,'original_type_counts':{str(t):len(g) for t,g in original_groups.items()},
            'native_gui_verified':False,
            'server_eligibility_proven':False,'runtime_changed':False}
    (evidence/'npc-special-repairs-native.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'verticals':len(cases),'native_cost_cases':len(costs),'payment_display_controlled':payment},ensure_ascii=True))


if __name__=='__main__':main()
