"""Original practice buttons and assist-skill codecs executed offline."""
import struct,json,hashlib
from native_inspect import DATA,BASE,u32
from verify_social_native import native_payload
from inspect_client import OUT,write_json
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP,UC_X86_REG_ECX,UC_X86_REG_EAX,UC_X86_REG_EIP
from unicorn.x86_const import UC_X86_REG_ESI
from unicorn.x86_const import UC_X86_REG_EBP,UC_X86_REG_EDX
import practice_protocol as p
from role_practice import PracticeState


def click(handler):
    uc=Uc(UC_ARCH_X86,UC_MODE_32);uc.mem_map(0,4096)
    uc.mem_map(BASE,(len(DATA)+4095)&~4095);uc.mem_write(BASE,DATA);uc.mem_map(0x5000000,0x20000)
    control,event,button,rows,network,table,stack,stop,send=range(0x5001000,0x500a000,0x1000)
    def w(at,*values):uc.mem_write(at,struct.pack('<'+'I'*len(values),*values))
    def r(at):return struct.unpack('<I',uc.mem_read(at,4))[0]
    w(control+0x24,rows,rows+0x20,rows+0x20);w(control+0x168,123,256)
    w(event+8,button);w(button+0x26c,0);w(rows,button);w(network,table);w(table+0x3c,send)
    w(stack,stop,event);uc.reg_write(UC_X86_REG_ESP,stack);uc.reg_write(UC_X86_REG_ECX,control)
    sent=[]
    def ret(count=0,value=None):
        sp=uc.reg_read(UC_X86_REG_ESP);uc.reg_write(UC_X86_REG_EIP,r(sp));uc.reg_write(UC_X86_REG_ESP,sp+4+count)
        if value is not None:uc.reg_write(UC_X86_REG_EAX,value)
    def hook(machine,at,size,data):
        sp=machine.reg_read(UC_X86_REG_ESP)
        if at==0x4d3aa0:ret(value=360001)
        elif at==0x813860:ret(value=network)
        elif at==0x1919184:ret()
        elif at==send:
            obj=r(sp+4);assert r(obj+4)==p.PRACTISE_SKILL
            sent.append((r(obj+8)|(r(obj+12)<<32),r(obj+16),bytes(machine.mem_read(obj+20,1))[0]));ret(4,value=1)
    uc.hook_add(UC_HOOK_CODE,hook);uc.emu_start(handler,stop,count=10000)
    assert uc.reg_read(UC_X86_REG_EIP)==stop and len(sent)==1
    return sent[0]


def npc_context():
    index=DATA[0x163f5f0-BASE+1023-0x31d]
    assert u32(0x163f578+index*4)==0x1639b1f
    uc=Uc(UC_ARCH_X86,UC_MODE_32);uc.mem_map(0,4096)
    uc.mem_map(BASE,(len(DATA)+4095)&~4095);uc.mem_write(BASE,DATA);uc.mem_map(0x5000000,0x20000)
    ui,control,stack=0x5001000,0x5002000,0x5010000
    uc.mem_write(ui+0xd0,struct.pack('<II',123,256));uc.mem_write(stack,struct.pack('<I',0x500f000))
    uc.reg_write(UC_X86_REG_ESI,ui);uc.reg_write(UC_X86_REG_ESP,stack)
    registrations=[]
    def ret(count=0,value=None):
        sp=uc.reg_read(UC_X86_REG_ESP);destination=struct.unpack('<I',uc.mem_read(sp,4))[0]
        uc.reg_write(UC_X86_REG_EIP,destination);uc.reg_write(UC_X86_REG_ESP,sp+4+count)
        if value is not None:uc.reg_write(UC_X86_REG_EAX,value)
    def hook(machine,at,size,data):
        sp=machine.reg_read(UC_X86_REG_ESP)
        if at==0x1629cb0:ret()
        elif at==0x1629c30:ret(value=control)
        elif at==0x8015e0:ret(value=0x5003000)
        elif at==0x8013b0:
            registrations.append(struct.unpack('<IIIII',machine.mem_read(sp+4,20)));ret(20)
    uc.hook_add(UC_HOOK_CODE,hook);uc.emu_start(0x1639b1f,0x14d86fd,count=10000)
    assert uc.reg_read(UC_X86_REG_EIP)==0x14d86fd
    assert struct.unpack('<Q',uc.mem_read(control+0x168,8))[0]==2**40+123
    assert registrations==[(123,256,1,control+4,13)]
    return dict(service=1023,dispatch='0x1639b1f',initializer='0x14d86d0',context_offset='+0x168',registration_type=13)


def native_open_map(opened):
    obj,head=0x5001000,0x5001400
    nodes=[0x5001600+i*0x30 for i in range(7)]
    def tree(lo,hi,parent):
        if lo>hi:return head,[]
        mid=(lo+hi)//2;node=nodes[mid]
        left,lrows=tree(lo,mid-1,node);right,rrows=tree(mid+1,hi,node)
        raw=struct.pack('<IIIII BB2x',left,parent,right,360001+mid,int(360001+mid in opened),1,0)
        return node,lrows+[(node-obj,raw)]+rrows
    root,rows=tree(0,6,head)
    rows.append((head-obj,struct.pack('<IIIII BB2x',nodes[0],root,nodes[-1],0,0,0,1)))
    return native_payload(0xed21a0,scalars=[(12,head),(16,7)],raw=rows)


def native_open_choice(status):
    uc=Uc(UC_ARCH_X86,UC_MODE_32);uc.mem_map(0,4096)
    uc.mem_map(BASE,(len(DATA)+4095)&~4095);uc.mem_write(BASE,DATA);uc.mem_map(0x5000000,0x20000)
    control,rows,head,node,window,stack=0x5001000,0x5002000,0x5003000,0x5004000,0x5005000,0x5010000
    uc.mem_write(control+0x24,struct.pack('<III',rows,rows+32,rows+32));uc.mem_write(rows,struct.pack('<I',window))
    uc.mem_write(window+0x590,struct.pack('<I',360001));uc.mem_write(window+0x52a,b'\x7f')
    uc.mem_write(head,struct.pack('<IIIII BB2x',node,node,node,0,0,0,1))
    uc.mem_write(node,struct.pack('<IIIII BB2x',head,head,head,360001,status,1,0))
    uc.mem_write(stack,struct.pack('<IIII',0x500f000,0,head,1))
    uc.reg_write(UC_X86_REG_ESP,stack);uc.reg_write(UC_X86_REG_ECX,control)
    def hook(machine,at,size,data):
        if at in (0x14d68a6,0x14d6a62):machine.emu_stop()
    uc.hook_add(UC_HOOK_CODE,hook);uc.emu_start(0x14d6770,0x500f000,count=10000)
    assert uc.reg_read(UC_X86_REG_EIP) in (0x14d68a6,0x14d6a62)
    return bytes(uc.mem_read(window+0x52a,1))[0]


def progress_row(level):
    uc=Uc(UC_ARCH_X86,UC_MODE_32);uc.mem_map(0,4096)
    uc.mem_map(BASE,(len(DATA)+4095)&~4095);uc.mem_write(BASE,DATA);uc.mem_map(0x5000000,0x20000)
    uc.mem_write(0x5002008,struct.pack('<I',0x5003000))
    uc.reg_write(UC_X86_REG_ESP,0x5010000);uc.reg_write(UC_X86_REG_EAX,0x5001000)
    uc.reg_write(UC_X86_REG_EDX,0x5002000);uc.reg_write(UC_X86_REG_EBP,level)
    uc.emu_start(0x14d544b,0x5003000,count=100)
    assert uc.reg_read(UC_X86_REG_EIP)==0x5003000
    return struct.unpack('<I',uc.mem_read(uc.reg_read(UC_X86_REG_ESP)+4,4))[0]


def main():
    passed=[]
    assert click(0x14d4020)==(2**40+123,360001,0)
    assert click(0x14d4150)==(2**40+123,360001,1)
    passed.append('original seven-skill cash and pill buttons emit modes zero and one with full NPC context')
    state=PracticeState(360001,3,27,9)
    assert native_payload(0xe56a90,scalars=[(4,state.skill),(8,state.level),(12,state.experience)])==p.update(state)
    assert native_payload(0xdd0a80,scalars=[(8,0x227cfac),(12,state.skill),(16,state.level),(20,state.experience)])==p.update(state)
    assert u32(0xdd0a4d)==p.UPDATE_ASSIST_SKILL
    passed.append('original AssistSkill and SUpdateAssistSkill serialize skill/level/experience as three signed32 values')
    for mode in range(5):
        body=native_payload(0xe56770,scalars=[(8,123),(12,256),(16,360001),(20,mode)])
        assert p.request(body)==(2**40+123,360001,mode)
    for invalid in (body[:-1],body+b'\0',struct.pack('>QiB',1,360001,5)):
        try:p.request(invalid)
        except ValueError:pass
        else:raise AssertionError('malformed practice body accepted')
    passed.append('original personal request preserves NPC Q and five raw modes; cash/pill remain distinct from other modes')
    context=npc_context()
    passed.append('original service1023 passes NPC UI key through dialog initializer to both cash/pill request context')
    assert native_open_map((360001,360004))==p.open_types((360001,360004))
    assert native_open_map(())==p.open_types(())
    assert u32(0xed2153)==p.FACTION_PRACTICE
    passed.append('original SFactionPractice nonempty tree serializes all seven current open/closed settings')
    assert native_open_choice(0)==1 and native_open_choice(1)==0 and native_open_choice(9)==0
    passed.append('original current-dialog map consumer treats zero as closed and nonzero as open')
    items={int(r['attributes']['id']):r['attributes'] for r in json.loads((OUT/'catalogs/knight.gsp.item.citemattr.json').read_text('utf-8'))}
    assert items[36747]['name']=='修炼丹' and items[61335]['name']=='铭文经卷' and items[36747]['itemtypeid']=='150'
    layout=(OUT/'decoded/ui/layouts/gangskillrole.layout').read_text('utf-8')
    assert '勇武、谋略、意念每次试炼增加20点修炼经验' in layout
    assert '招架、抗命、冥思和仁心每次试炼增加30点修炼经验' in layout
    assert '试炼不消耗帮派资材' in layout
    passed.append('original pill36747 differs from inscription61335; current layout explicitly defines twenty/thirty XP and no pill material cost')
    assert [progress_row(level) for level in (0,1,40)]==[1,2,41]
    passed.append('original current combat-practice progress bar queries current level plus one; server carry/consumption remains designed')
    result=dict(passed=passed,image_sha256=hashlib.sha256(DATA).hexdigest(),native_gui_verified=False,
        npc_context=context,scope='original handlers/serializers only; button ID/window/network edges adapted; no server NPC authorization or live purchase')
    write_json(OUT/'evidence/role-practice-native-verification.json',result);print(json.dumps(result))


if __name__=='__main__':main()
