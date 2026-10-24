"""Offline original member-learning consumers, never GUI/server acceptance.

Configuration records, attribute/wallet fixtures, dialog factories and messages
are explicit Adapters. Original copies, maps, comparisons and packet builders
execute. SOURCE follows this actual source file; SOURCE_OUT is captured before
review redirects OUT to a temporary result directory.
"""
from pathlib import Path
import hashlib,json,struct
from inspect_client import OUT,write_json
from native_inspect import DATA,BASE,u32
from verify_family_donation_native import Native
from verify_social_native import native_payload
from research_battle import NativeBattleDecoder
from role_life_skills import LifeSkill
import life_skill_protocol as protocol
from unicorn.x86_const import (UC_X86_REG_EBP,
    UC_X86_REG_EDI,UC_X86_REG_ESI,UC_X86_REG_ESP,UC_X86_REG_EIP)


SOURCE=Path(__file__).resolve().parent
SOURCE_OUT=OUT
IMAGE_SHA='2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791'
COST_FIELDS=('id','outExpCost','outMoneyCost','outMoneyRP','outMoneyCostJQDS',
    'outExpCostJQDS','outMoneyJNYS','inExpCost','inMoneyCost','inBG',
    'inBangGongNeed','inBR','inSkillLevel')


def tree(n,container,head,rows,*,nil=0x15):
    """Independent synthetic MSVC tree layout; no production state/mapper."""
    rows=tuple(sorted(rows));nodes=[head+0x200*(i+1) for i in range(len(rows))]
    def build(lo,hi,parent):
        if lo>hi:return head
        mid=(lo+hi)//2;node=nodes[mid]
        left=build(lo,mid-1,node);right=build(mid+1,hi,node)
        n.write(node,left,parent,right,*rows[mid]);n.uc.mem_write(node+nil,b'\0')
        return node
    root=build(0,len(rows)-1,head)
    n.write(head,nodes[0] if nodes else head,root,nodes[-1] if nodes else head)
    n.uc.mem_write(head+nil,b'\1');n.write(container+4,head,len(rows))
    return {row[0]:node for row,node in zip(rows,nodes)}


def request_and_shared_update():
    npc=2**48+1395;wires=[]
    for mode in range(5):
        wire=native_payload(0xe56880,scalars=[(8,npc&0xffffffff),(12,npc>>32),(16,300101),(20,mode)])
        assert wire==struct.pack('>QiB',npc,300101,mode)
        assert protocol.request(wire)==(npc,300101,mode);wires.append(wire.hex())
    for skill in (300101,360001):
        wire=native_payload(0xdd0a80,scalars=[(8,0x227cfac),(12,skill),(16,11),(20,123)])
        assert wire==protocol.update(LifeSkill(skill,11,123))==struct.pack('>iii',skill,11,123)
        n=Native();manager,obj=0x5001000,0x5002000
        nodes=tree(n,manager+0x74,0x5010000,((skill,3,7),),nil=0x19)
        callback=0x5020000;n.write(manager+0x10,callback);n.write(callback,callback,callback)
        n.write(0x29448a4,manager)
        for address in (0x294f32c,0x294f330,0x294f338,0x294f340,0x294f33c,0x294576c):n.write(address,0)
        n.write(manager+0x40,0x11223344,0x55667788,0x88776655);n.write(obj+12,skill,11,123)
        n.run(0x12d7270,obj,lambda at:n.ret() if at==0x1919184 else None,args=(0,0))
        assert n.uc.reg_read(UC_X86_REG_EIP)==n.stop
        assert (n.read(nodes[skill]+16),n.read(nodes[skill]+20))==(11,123)
        assert (n.read(manager+0x40),n.read(manager+0x44),n.read(manager+0x48))==(0x11223344,0x55667788,0x88776655)
    assert u32(0xdd0a4d)==protocol.UPDATE_ASSIST_SKILL==0xc36b7
    return dict(raw_mode_wires=wires,skills_updated_in_original_shared_map=[300101,360001],
        other_skills_sentinel_unchanged=True,business_mode_bound_by_guild_button=0)


def full_snapshot_replacement():
    """A life-only complete list must not be mistaken for a safe segment delta."""
    from unicorn import UC_HOOK_CODE
    p=NativeBattleDecoder();manager=p.allocate(0x200);callback=p.allocate(0x40);events=p.allocate(0x40)
    packet=p.obj;p.obj=manager+0x74;p.call(0x12d2990);p.obj=packet
    p.write(0x29448a4,manager);p.write(manager+0x18,callback);p.write(callback+12,0x500e010)
    p.write(manager+0x10,events);p.write(events,events,events)
    for address in (0x294576c,0x294f32c,0x294f330,0x294f338,0x294f340,0x294f33c):p.write(address,0)
    def observe(uc,at,size,user):
        if at==0x500e010:
            sp=uc.reg_read(p.sp);uc.reg_write(p.ip,p.read(sp));uc.reg_write(p.sp,sp+4)
    p.u.hook_add(UC_HOOK_CODE,observe)
    def entries():
        head=p.read(manager+0x78);values={}
        def visit(node):
            if node==head:return
            visit(p.read(node));values[p.read(node+12)]=(p.read(node+16),p.read(node+20));visit(p.read(node+8))
        visit(p.read(head+4));return values
    p.write(packet+12,360001,3,27);p.call(0x12d7270,0,0);before=entries();assert before=={360001:(3,27)}
    wire=b'\1'+struct.pack('>iii',300101,11,123)
    p.call(0xea3bd0);p.write(p.stream,0x224c100,p.buf,0);p.write(p.buf-12,len(wire),len(wire),1)
    p.u.mem_write(p.buf,wire);p.call(0xea41d0,p.stream);assert p.read(p.stream+8)==len(wire)
    p.call(0x12d5b80,0,0);after=entries();assert after=={300101:(11,123)}
    return dict(before=before,after=after,original_full_snapshot_removed_prior_practice=True)


def panel(ids):
    rows=tuple((skill,20+i) for i,skill in enumerate(ids));npc=2**48+1394
    fixture=Native();obj,head=0x5001000,0x5010000
    tree(fixture,obj+0x10,head,rows)
    raw=[(head-obj,bytes(fixture.uc.mem_read(head,0x20)))]
    for i in range(14):
        node=head+0x200*(i+1);raw.append((node-obj,bytes(fixture.uc.mem_read(node,0x20))))
    wire=native_payload(0xf30a70,scalars=[(8,npc&0xffffffff),(12,npc>>32),(20,head),(24,14)],raw=raw)
    assert wire==protocol.study_panel(npc,rows)==struct.pack('>Q',npc)+b'\x0e'+b''.join(struct.pack('>ii',*row) for row in rows)
    decoder=NativeBattleDecoder();decoder.call(0xf30940)
    decoder.write(decoder.stream,0x224c100,decoder.buf,0);decoder.write(decoder.buf-12,len(wire),len(wire),1)
    decoder.u.mem_write(decoder.buf,wire);decoder.call(0xf309f0,decoder.stream)
    assert decoder.read(decoder.stream+8)==len(wire) and decoder.read(decoder.obj+4)==0xc36b8
    assert decoder.read(decoder.obj+8)|(decoder.read(decoder.obj+12)<<32)==npc
    decoded=[];sentinel=decoder.read(decoder.obj+20)
    def visit(node):
        if node==sentinel:return
        visit(decoder.read(node));decoded.append(struct.unpack('<ii',bytes(decoder.u.mem_read(node+12,8))));visit(decoder.read(node+8))
    visit(decoder.read(sentinel+4));assert tuple(decoded)==rows and decoder.read(decoder.obj+24)==14
    # Execute Process through actual catalog lookup/cap-map mutation, then stop
    # before its GUI refresh; factory and NPC registration are external edges.
    n=Native();dialog=0x5002000;n.write(obj+8,npc&0xffffffff,npc>>32);tree(n,obj+0x10,0x5010000,rows)
    tree(n,dialog+0x7c,0x5020000,tuple((skill,0) for skill in ids),nil=0xf9)
    nodes=tree(n,dialog+0x88,0x5030000,tuple((skill,7) for skill in ids));n.write(0x294f330,dialog);registered=[]
    def observe(at):
        sp=n.uc.reg_read(UC_X86_REG_ESP)
        if at==0x13531c0:n.ret(value=dialog)
        elif at==0x8015e0:registered.append(tuple(n.read(sp+i) for i in (4,8,12,16,20)));n.ret(value=0x5040000)
        elif at==0x8013b0:n.ret()
        elif at==0x1351f99:n.uc.emu_stop()
    n.run(0x1353240,obj,observe,args=(0,0));assert n.uc.reg_read(UC_X86_REG_EIP)==0x1351f99
    assert registered==[(npc&0xffffffff,npc>>32,1,dialog+4,13)]
    assert (n.read(dialog+0x68),n.read(dialog+0x6c))==(npc&0xffffffff,npc>>32)
    assert tuple((skill,n.read(nodes[skill]+16)) for skill in ids)==rows
    return dict(bytes=len(wire),wire_hex=wire.hex(),maximums=rows,
        original_decoder_consumed=len(wire),original_process_stop='0x1351f99',npc_registration=registered)


def cost_readers(costs):
    observations=[]
    for target in (1,40,155):
        n=Native();row=0x5001000;n.write(row,*[int(costs[target][key]) for key in COST_FIELDS])
        n.run(0xcfbbe0,n.stack+0xbc,lambda at:None,args=(row,));assert n.uc.reg_read(UC_X86_REG_EIP)==n.stop
        actual=[]
        for address,key in ((0x1350fcc,'inMoneyCost'),(0x1351075,'inExpCost'),(0x1351116,'inBG')):
            def observe(at):
                if at==0x1016030:
                    sp=n.uc.reg_read(UC_X86_REG_ESP);actual.append((key,n.read(n.read(sp+8))));n.uc.emu_stop()
            n.run(address,0,observe);assert n.uc.reg_read(UC_X86_REG_EIP)==0x1016030
        assert actual==[(key,int(costs[target][key])) for key in ('inMoneyCost','inExpCost','inBG')]
        observations.append(dict(target=target,formatter_arguments=dict(actual)))
    return observations


def service_gate():
    observations=[]
    index=DATA[0x163f1c0-BASE+121-2];assert u32(0x163f09c+index*4)==0x1637b0f
    for level,correct,expected in ((29,True,'low_level'),(30,False,'wrong_scene'),(30,True,'service121')):
        n=Native();menu,role,manager,world=0x5001000,0x5002000,0x5003000,0x5004000
        n.write(0x2944550,role);n.write(0x2945570,manager);n.write(0x2944564,world)
        tree(n,role+0x164,0x5010000,((0x1ea,level),));n.write(manager+0x228,123)
        n.write(manager+0x240,1394,256);n.write(world+0x110,1394);n.write(world+0x30,1394+int(not correct),256)
        n.write(menu+0xd0,10076,512);n.write(n.stack+0x14,121)
        n.uc.reg_write(UC_X86_REG_EDI,121);n.uc.reg_write(UC_X86_REG_ESI,menu);n.uc.reg_write(UC_X86_REG_EBP,0);seen=[]
        def observe(at):
            if at in (0x89dde0,0x1637b99,0x1627be0):
                seen.append('low_level' if at==0x89dde0 else 'wrong_scene' if at==0x1637b99 else 'service121');n.uc.emu_stop()
        n.run(0x1636d1c,0,observe);assert seen==[expected]
        if expected=='service121':assert n.read(n.uc.reg_read(UC_X86_REG_ESP)+4)==121
        observations.append(dict(level=level,correct_guild_scene=correct,outcome=expected))
    return observations


def click(costs,target,cash,bound,depot,*,xp=1000000000,maximum=155,popularity=1000,prompted=False):
    n=Native();dialog,manager,role,wallet,row,table,vtable,message=tuple(0x5000000+i*0x1000 for i in range(1,9))
    n.write(0x29448a4,manager);n.write(0x2944550,role);n.write(0x2944628,wallet)
    tree(n,manager+0x74,0x5010000,((300101,target-1,0),),nil=0x19)
    tree(n,dialog+0x88,0x5020000,((300101,maximum),));tree(n,role+0x164,0x5030000,((0x262,popularity),))
    n.write(dialog+0x60,300101);n.write(dialog+0x68,1394,256);n.uc.mem_write(dialog+0x74,bytes((int(prompted),)))
    n.write(role+0x178,xp,0);n.write(wallet+0xb0,cash,0);n.write(wallet+0xb8,depot,0);n.write(wallet+0xc8,bound,0)
    n.write(row,*[int(costs[target][key]) for key in COST_FIELDS]);n.write(table,vtable);n.write(vtable+8,0x500e100)
    n.write(message,message+0x100);n.write(message+0x108,0x500e110);heap=[0x5200000];lookups=[];seen=[]
    def observe(at):
        sp=n.uc.reg_read(UC_X86_REG_ESP)
        if at in (0x1919178,u32(0x2244890)):
            count=n.read(sp+4);pointer=heap[0];heap[0]+=max(16,(count+15)&~15);n.ret(value=pointer)
        elif at in (0x191910c,u32(0x2244894),0x1919184):n.ret()
        elif at==0x89e8f0:n.ret(value=table)
        elif at==0x500e100:lookups.append(n.read(sp+4));n.ret(4,value=row)
        elif at==0x89dde0:n.ret(value=message)
        elif at==0x500e110:seen.append(('warning',n.read(sp+4)));n.uc.emu_stop()
        elif at==0x135069f:seen.append(('minimum_wallet',142514));n.uc.emu_stop()
        elif at==0x813860:
            packet=sp+4+0x3c;seen.append(('send',n.read(packet+4),n.read(packet+8),n.read(packet+12),
                n.read(packet+16),bytes(n.uc.mem_read(packet+20,1))[0]));n.uc.emu_stop()
    n.run(0x13503c0,dialog,observe,args=(0,))
    assert n.uc.reg_read(UC_X86_REG_EIP) in (0x500e110,0x135069f,0x813860) and len(seen)==1
    assert lookups==([target] if maximum>=target else [])
    return seen[0]


def purchase_boundaries(costs):
    sent=('send',0xc36b6,1394,256,300101,0);results=[]
    cases=[(1,0,0,10000,{},('minimum_wallet',142514)),(1,1,0,10000,{},('minimum_wallet',142514)),
        (1,2,0,10000,{},('minimum_wallet',142514)),(1,3,0,0,{},('minimum_wallet',142514)),
        (1,0,3,0,{},('minimum_wallet',142514)),(1,9999,0,0,{},('minimum_wallet',142514)),
        (1,10000,0,0,{},sent),(1,0,10000,0,{},sent),(1,0,0,2,{},('warning',140419)),
        (155,9999,0,10000000,{},('minimum_wallet',142514)),(155,10000,0,10000000,{},('warning',141620)),
        (155,10000,0,10000000,dict(prompted=True),sent),(155,695471,0,0,{},('warning',140419)),
        (155,695472,0,0,{},sent),(155,10000000,0,0,dict(maximum=154),('warning',140421)),
        (155,10000000,0,0,dict(xp=22060445),('warning',140424)),
        (1,10000,0,0,dict(popularity=11),('warning',140418)),(1,10000,0,0,dict(popularity=12),sent)]
    for target,cash,bound,depot,options,expected in cases:
        actual=click(costs,target,cash,bound,depot,**options);assert actual==expected
        results.append(dict(target=target,cost=int(costs[target]['inMoneyCost']),cash=cash,bound_silver=bound,
            deposit=depot,options=options,outcome=actual))
    return results


def main():
    assert hashlib.sha256(DATA).hexdigest()==IMAGE_SHA
    catalog=json.loads((SOURCE_OUT/'catalogs/knight.gsp.skill.clifeskill.json').read_text(encoding='utf8'))
    ids=tuple(sorted(int(row['attributes']['id']) for row in catalog if row['attributes']['bCanStudy']=='1'));assert len(ids)==14
    costs={int(row['attributes']['id']):row['attributes'] for row in json.loads(
        (SOURCE_OUT/'catalogs/knight.gsp.skill.clifeskillcost.json').read_text(encoding='utf8'))}
    request=request_and_shared_update();replacement=full_snapshot_replacement();maximums=panel(ids);numbers=cost_readers(costs)
    gates=service_gate();boundaries=purchase_boundaries(costs)
    source_names=('verify_guild_member_learning_native.py','life_skill_protocol.py','role_life_skills.py',
        'verify_family_donation_native.py','verify_social_native.py','research_battle.py')
    resource_names=('catalogs/knight.gsp.skill.clifeskill.json','catalogs/knight.gsp.skill.clifeskillcost.json',
        'decoded/ui/layouts/assistskillstudyinfaction.layout')
    result=dict(passed=['original c36b6 raw0..4 marshals match current codec and c36b7 updates life/practice in shared+74 while preserving OtherSkills+40',
        'original c36b5 full constructor/decoder/Process replaces shared+74 and removes omitted practice, proving a life-only list is unsafe',
        'original c36b8 fourteen-map marshal matches current codec; full ctor/unmarshal consumes121 bytes and Process copies NPC Q/caps before GUI',
        'original cost copy and three numeric readers bind silver, role experience and reputation display at target1/40/155',
        'original service121 switch executes role-level29/30 and current guild64 scene checks',
        'original full guild learning button checks research cap, role XP, individual popularity, total money, wallet10000 and local deposit prompt'],
        request=request,full_snapshot_replacement=replacement,panel=maximums,cost_readers=numbers,service_gate=gates,purchase_boundaries=boundaries,
        native_image_sha256=IMAGE_SHA,source_root=str(SOURCE),resource_root=str(SOURCE_OUT),
        source_sha256={name:hashlib.sha256((SOURCE/name).read_bytes()).hexdigest() for name in source_names},
        resource_sha256={name:hashlib.sha256((SOURCE_OUT/name).read_bytes()).hexdigest() for name in resource_names},
        method='research executes primary native consumers; codebase-design confines controlled external Adapters to this verification Module',
        adapters=['existing Native allocation/CRT/cookie helpers; synthetic original-layout attribute, wallet and map fixtures',
            'configuration getter and row lookup return actual catalog target rows; original cfbbe0 copy and comparisons execute',
            'message lookup stops at original message ID; transport stops after original complete request construction',
            'c36b5 manager reset notification uses an empty callback; original list/tree decoding and replacement execute',
            'c36b8 window factory and NPC registration adapted, stopping at1351f99 before GUI refresh',
            'cost formatter intercepted at1016030 before string/UI work; service stopped at1627be0 request-helper entry'],
        unknown=['original server debits/priority/refunds, inBG actual debit, inBangGongNeed/inBR business rules',
            'proficiency upgrade consumption, full maxlevel derivation, real NPC/MapAddress authorization and GUI'],
        original_full_guild_button_to_observation_executed=True,full_panel_process_executed=False,
        complete_production_details_mapper_implemented=False,native_gui_verified=False,live_server_changed=False)
    write_json(OUT/'evidence/guild-member-learning-native-verification.json',result)
    print(json.dumps(dict(passed=len(result['passed']),purchase_boundaries=len(boundaries),panel_bytes=maximums['bytes'],
        native_gui_verified=False,live_server_changed=False)))


if __name__=='__main__':main()
