"""Original settings handlers/serializers; offline evidence, never GUI acceptance."""
import hashlib,json,struct
from native_inspect import DATA,BASE
from inspect_client import OUT,write_json
from verify_social_native import native_payload
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP,UC_X86_REG_EAX

def click(handler,level,active,selected=360001,current_research=300101):
    uc=Uc(UC_ARCH_X86,UC_MODE_32);uc.mem_map(0,4096);uc.mem_map(BASE,(len(DATA)+4095)&~4095);uc.mem_write(BASE,DATA);uc.mem_map(0x5000000,0x800000)
    control,manager,table,network=0x5001000,0x5002000,0x5003000,0x5004000
    head,item,stack,stop,send,close=0x5005000,0x5006000,0x5100000,0x500f000,0x500e010,0x500e020
    def w(a,*v):uc.mem_write(a,struct.pack('<'+'I'*len(v),*v))
    def r(a):return struct.unpack('<I',uc.mem_read(a,4))[0]
    w(control+4,table);w(table+4,close);w(control+0x20,123,256);w(item+0xc0,selected or 0)
    w(network,table+0x100);w(table+0x13c,send);w(0x2945570,manager)
    w(manager+0x280,level);w(manager+0x324,current_research);w(manager+0x32c,head)
    nodes=[0x5007000+i*0x40 for i in range(7)];w(head,nodes[0],nodes[-1])
    for i,node in enumerate(nodes):w(node,nodes[i+1] if i<6 else head,nodes[i-1] if i else head,360001+i,int(360001+i in active))
    sent=[];warnings=[]
    def ret(n=0,value=None):
        sp=uc.reg_read(UC_X86_REG_ESP);uc.reg_write(UC_X86_REG_EIP,r(sp));uc.reg_write(UC_X86_REG_ESP,sp+4+n)
        if value is not None:uc.reg_write(UC_X86_REG_EAX,value)
    def hook(u,at,size,data):
        sp=u.reg_read(UC_X86_REG_ESP)
        if at==stop:u.emu_stop()
        elif at==0x813860:ret(value=network)
        elif at==0x4af0b0:ret(value=item if selected else 0)
        elif at in (0x1919184,close):ret()
        elif at==0x837060:warnings.append(r(sp+8));u.emu_stop()
        elif at==send:
            obj=r(sp+4);kind=r(obj+4)
            values=tuple(r(obj+8+i*4) for i in range(3 if kind==0xc563b else 4))
            sent.append((kind,values));ret(4,value=1)
    uc.hook_add(UC_HOOK_CODE,hook);w(stack,stop,0x5009000);uc.reg_write(UC_X86_REG_ECX,control);uc.reg_write(UC_X86_REG_ESP,stack)
    uc.emu_start(handler,stop,count=100000)
    assert warnings or uc.reg_read(UC_X86_REG_EIP)==stop
    return sent,warnings


def main():
    passed=[]
    for name,handler,level,active,selected,packets,warnings in (
     ('level one has zero open slots',0x14e0700,1,(),360001,[],[2269]),
     ('level two first practice opens',0x14e0700,2,(),360001,[(0xc563d,(123,256,360001,1))],[]),
     ('level three second practice opens',0x14e0700,3,(360002,),360001,[(0xc563d,(123,256,360001,1))],[]),
     ('level three third practice exceeds level minus one slots',0x14e0700,3,(360002,360003),360001,[],[2269]),
     ('already open rejects',0x14e0700,3,(360001,),360001,[],[2267]),
     ('closing active practice emits zero flag',0x14e09d0,2,(360001,),360001,[(0xc563d,(123,256,360001,0))],[]),
     ('already closed rejects',0x14e09d0,2,(),360001,[],[2271]),
     ('open requires selected row',0x14e0700,3,(),None,[],[2270]),
     ('close requires selected row',0x14e09d0,3,(),None,[],[2272]),
     ('research selected furniture skill',0x14e1600,3,(),310103,[(0xc563b,(123,256,310103))],[]),
     ('research duplicate selection rejects',0x14e1600,3,(),300101,[],[2273])):
        actual=click(handler,level,active,selected=selected)
        assert actual==(packets,warnings),(name,actual)
        passed.append(dict(name=name,handler=hex(handler),packets=packets,first_warning_string_ids=warnings))
    for name,kind,address,tail in (
     ('CFactionSetPractice',0xc5655,0xe450b0,(360001,1)),
     ('CSetFactionPracticeOpen',0xc563d,0xe45700,(360001,1)),
     ('CSetFactionResearchSkill',0xc563b,0xe45740,(310103,))):
        expected=struct.pack('>Q'+'i'*len(tail),2**40+123,*tail)
        actual=native_payload(address,scalars=[(8,123),(0xc,256)]+[(0x10+i*4,v) for i,v in enumerate(tail)])
        assert actual==expected
        passed.append(dict(name=name,type=hex(kind),serializer=hex(address),wire=actual.hex()))
    for address,name,kind in ((0xe56770,'CPractiseSkill',0xc36cc),(0xe56880,'CUpdaetAssistSkillLevel',0xc36b6)):
        for mode in range(5):
            expected=struct.pack('>QiB',2**40+123,360001,mode)
            actual=native_payload(address,scalars=[(8,123),(0xc,256),(0x10,360001),(0x14,mode)])
            assert actual==expected
            passed.append(dict(name=name+' raw mode '+str(mode),type=hex(kind),serializer=hex(address),wire=actual.hex()))
    assert native_payload(0xe91320,scalars=[(4,360001),(8,1)])==struct.pack('>ii',360001,1)
    assert native_payload(0xe46060,scalars=[(8,360001),(0xc,1)])==struct.pack('>ii',360001,1)
    passed.append(dict(name='FactionPractice and SFactionSetPracticeOK id/status int pair',serializers=['0xe91320','0xe46060']))
    result=dict(passed=passed,image_sha256=hashlib.sha256(DATA).hexdigest(),native_gui_verified=False,runtime_integrated=False,
     scope='offline original settings handlers and native serializers; UI selection/network/dialog edges adapted; seven-node active list uses original lookup/count routines',
     conclusions=['legacy FactionData +40 is guild level cached at manager +280; legacy open count cannot exceed level minus one',
     'SRefreshFactionPracticeData c563c entries copy skill id and nonzero-as-boolean into active list',
     'settings, enable and individual practice are distinct requests',
     'request Q business context and individual raw modes remain unbound'])

    policy=json.loads((OUT/'design/recovery-baseline.json').read_text('utf-8'))['organizations']
    skills=json.loads((OUT/'catalogs/knight.gsp.skill.clifeskill.json').read_text('utf-8'))
    original_research={int(r['attributes']['id']) for r in skills if r['attributes'].get('bCanStudy')=='1'}
    assert set(policy['guild_research_skill_ids'])==original_research
    assert set(policy['guild_practice_skill_ids'])=={int(r['attributes']['id']) for r in skills if 360001<=int(r['attributes']['id'])<=360007}
    messages={int(r['attributes']['id']):r['attributes'].get('msg','') for r in json.loads((OUT/'catalogs/knight.gsp.message.cmessagetip.json').read_text('utf-8'))}
    assert '300万' in messages[140373] and '300万' in messages[144152] and '600万' in messages[144155]
    assert policy['guild_practice_open_fee']==3000000 and policy['guild_practice_open_min_funds']==6000000
    result['catalog_checks']=['research ids match original bCanStudy=1 rows','seven current practice ids are original life-skill rows',
        'opening fee 3000000 and current minimum funds 6000000 match original success/failure messages']
    result['current_seven_type_capacity_source']='inferred from verified legacy level-minus-one path'
    write_json(OUT/'evidence/guild-practice-native-verification.json',result)
    print(json.dumps(dict(count=len(passed),catalog_checks=result['catalog_checks'],runtime_integrated=False)))


if __name__=="__main__":main()

