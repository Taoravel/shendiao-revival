"""Original family scene gate, service dispatch, selector consumer and confirm.

Offline mapped image only. Network acquisition/send, dialog factory/close and
host CRT are Adapters. No server, client process, real UI or battle is opened.
"""
import hashlib,json,struct
from native_inspect import BASE,DATA,u32
from verify_social_native import native_payload
from inspect_client import OUT,write_json
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_EDI,UC_X86_REG_ESI,UC_X86_REG_EBP,UC_X86_REG_ESP,UC_X86_REG_EIP


class Native:
    def __init__(self):
        self.uc=Uc(UC_ARCH_X86,UC_MODE_32);self.uc.mem_map(0,4096)
        self.uc.mem_map(BASE,(len(DATA)+4095)&~4095);self.uc.mem_write(BASE,DATA)
        self.uc.mem_map(0x5000000,0x800000);self.stack=0x5100000;self.stop=0x500f000
    def write(self,address,*values):self.uc.mem_write(address,struct.pack('<'+'I'*len(values),*values))
    def read(self,address):return struct.unpack('<I',self.uc.mem_read(address,4))[0]
    def ret(self,count=0,value=None):
        sp=self.uc.reg_read(UC_X86_REG_ESP)
        self.uc.reg_write(UC_X86_REG_EIP,self.read(sp));self.uc.reg_write(UC_X86_REG_ESP,sp+4+count)
        if value is not None:self.uc.reg_write(UC_X86_REG_EAX,value)
    def run(self,address,this,hook,*,args=()):
        self.write(self.stack,self.stop,*args)
        self.uc.reg_write(UC_X86_REG_ECX,this);self.uc.reg_write(UC_X86_REG_ESP,self.stack)
        def observe(machine,at,size,user):
            if at==self.stop:machine.emu_stop()
            else:hook(at)
        handle=self.uc.hook_add(UC_HOOK_CODE,observe)
        try:self.uc.emu_start(address,self.stop,count=500000)
        finally:self.uc.hook_del(handle)


def scene_gate(family,identity,current):
    n=Native();manager,world=0x5001000,0x5004000
    n.write(0x2944564,world)
    # Original FamilyData is passed by value after the return address.
    n.write(n.stack+4+4,family)
    n.uc.mem_write(n.stack+4+0x78,struct.pack('<Q',identity))
    def stop(at):
        if at==0x14a29d1:n.uc.emu_stop()
    n.run(0x14a2950,manager,stop)
    assert n.read(manager+0xd0)==family
    assert n.read(manager+0xd8)|(n.read(manager+0xdc)<<32)==identity
    n.uc.mem_write(world+0x30,struct.pack('<Q',current))
    n.run(0x148c1f0,manager,lambda at:None)
    return n.uc.reg_read(UC_X86_REG_EAX)


def service_dispatch(identity,current):
    n=Native();manager,world,menu=0x5001000,0x5004000,0x5006000
    n.write(0x2945570,manager);n.write(0x2944564,world)
    n.write(manager+0xd0,123)
    n.uc.mem_write(manager+0xd8,struct.pack('<Q',identity));n.uc.mem_write(world+0x30,struct.pack('<Q',current))
    n.write(n.stack+0x14,296)
    n.uc.reg_write(UC_X86_REG_EDI,296);n.uc.reg_write(UC_X86_REG_ESI,menu);n.uc.reg_write(UC_X86_REG_EBP,0)
    n.uc.mem_write(menu+0xd0,struct.pack('<Q',0x112233445566))
    observed=[]
    def hook(at):
        if at==0x1627be0:
            sp=n.uc.reg_read(UC_X86_REG_ESP);observed.append(('npc_service',n.read(sp+4)));n.uc.emu_stop()
        elif at==0x163845c:observed.append(('denied_before_send',));n.uc.emu_stop()
    n.run(0x1637fbf,menu,hook)
    assert len(observed)==1
    return observed[0]


def prompt_consumer(context,npc,mode,templates,opaque):
    n=Native();obj,dialog,items=0x5001000,0x5005000,0x5007000
    n.write(obj+8,context);n.uc.mem_write(obj+0x10,struct.pack('<Q',npc));n.write(obj+0x18,mode)
    n.write(obj+0x20,items,items+4*len(templates),items+4*len(templates));n.write(items,*templates)
    n.write(obj+0x2c,opaque);n.write(0x294575c,dialog);observed=[]
    def hook(at):
        if at==0x10831b0:n.ret(value=dialog)
        elif at==0x1685430:
            sp=n.uc.reg_read(UC_X86_REG_ESP)
            low,high,actual_context,actual_mode,vector,last=(n.read(sp+v) for v in (4,8,12,16,20,24))
            begin,end=n.read(vector+4),n.read(vector+8)
            observed.append((actual_context,low|(high<<32),actual_mode,tuple(n.read(p) for p in range(begin,end,4)),last))
            n.uc.emu_stop()
        elif at==0x168a1e0:raise AssertionError('Explicit silver-box list incorrectly used task/config fallback')
    n.run(0x168bed0,obj,hook,args=(0,0))
    assert observed==[(context,npc,mode,templates,opaque)]
    return observed[0]


def selected_confirm(context,npc,mode,units):
    n=Native();dialog,rows,network,table,send,close=0x5001000,0x5003000,0x5006000,0x5007000,0x500e010,0x500e020
    n.uc.mem_write(dialog+0x58,struct.pack('<Q',npc));n.write(dialog+0x60,context,mode)
    n.write(dialog+0xec,rows,rows+5*0x138,rows+5*0x138)
    n.write(dialog+4,table);n.write(table+4,close);n.write(network,table);n.write(table+0x3c,send)
    for index,(key,count) in enumerate(units):n.write(rows+index*0x138,key,count)
    heap=[0x5200000];sent=[]
    imports={u32(0x2244890):'alloc',u32(0x2244894):'free',0x1919178:'alloc',0x191910c:'free'}
    for page in {p&~4095 for p in imports if not BASE<=p<BASE+len(DATA)}:n.uc.mem_map(page,4096)
    def hook(at):
        sp=n.uc.reg_read(UC_X86_REG_ESP);kind=imports.get(at)
        if kind=='alloc':
            address=heap[0];heap[0]+=max(16,(n.read(sp+4)+15)&~15);n.ret(value=address)
        elif kind=='free':n.ret()
        elif at==0x19191c2:
            dst,src,count=(n.read(sp+v) for v in (4,8,12))
            if count:n.uc.mem_write(dst,bytes(n.uc.mem_read(src,count)))
            n.ret(value=dst)
        elif at==0x1919184:n.ret()
        elif at==0x813860:n.ret(value=network)
        elif at==close:n.ret(value=1)
        elif at==send:
            obj=n.read(sp+4);begin,end=n.read(obj+0x20),n.read(obj+0x24)
            actual=tuple((n.read(p+4),n.read(p+8)) for p in range(begin,end,12))
            sent.append((n.read(obj+4),n.read(obj+8),n.read(obj+0x10)|(n.read(obj+0x14)<<32),n.read(obj+0x18),actual));n.ret(4,1)
    n.run(0x1684710,dialog,hook)
    assert n.uc.reg_read(UC_X86_REG_EIP)==n.stop
    assert sent==[(0xc2340,context,npc,mode,units)],sent
    return sent[0]


def main():
    from family_donation_protocol import DonationWindow,prompt,decode_submission
    from task_item_protocol import NpcItemSubmission,encode_npc_item_submission
    identity=2**40+1401
    assert scene_gate(123,identity,identity)==1
    assert scene_gate(123,identity,1401)==0
    assert scene_gate(0,identity,identity)==0
    assert service_dispatch(identity,identity)==('npc_service',296)
    assert service_dispatch(identity,identity+1)==('denied_before_send',)
    context,npc,mode,opaque=731,0x112233445566,0,0  # explicit isolated window; not recovered server choice
    window=DonationWindow(context,npc,mode,opaque)
    actual=native_payload(0xe6fe10,scalars=[(8,context),(0x10,npc&0xffffffff),(0x14,npc>>32),
        (0x18,mode),(0x2c,opaque)],raw=[(0x20,struct.pack('<III',0x5005000,0x5005008,0x5005008)),
        (0x4000,struct.pack('<ii',36076,36201))])
    assert actual==prompt(window)[1]
    assert prompt_consumer(context,npc,mode,(36076,36201),opaque)==(context,npc,mode,(36076,36201),opaque)
    units=((12345,3),(67890,2))
    selected_confirm(context,npc,mode,units)
    wire=encode_npc_item_submission(NpcItemSubmission(context,npc,mode,units))
    raw_units=b''.join(struct.pack('<III',0x2284ab8,key,count) for key,count in units)
    actual_request=native_payload(0xf16270,scalars=[(8,context),(0x10,npc&0xffffffff),(0x14,npc>>32),(0x18,mode)],
        raw=[(0x20,struct.pack('<III',0x5005000,0x5005000+len(raw_units),0x5005000+len(raw_units))),(0x4000,raw_units)])
    assert actual_request==wire
    assert decode_submission(wire,window,maximum_count=100).units==units
    selected_confirm(context,npc,mode,tuple((i,1) for i in range(1,6)))
    result=dict(passed=['FamilyData tail Q reaches exact family scene gate including high32 bits',
        'service296 dispatch runs original family scene gate then NPC service helper, mismatched scene denied',
        'SSubmit2Npc original marshal matches explicit silver-box prompt',
        'original SSubmit2Npc consumer retains explicit context/NPC/mode/templates/opaque',
        'original selector confirm walks selected keys and quantities in five rows and constructs CSubmit2Npc'],
        image_sha256=hashlib.sha256(DATA).hexdigest(),native_gui_verified=False,live_server_changed=False,
        historical_donation_server_context_mode_opaque_verified=False,
        mode0_is_explicit_isolated_fixture=True,
        adapters=['network acquisition/send','dialog factory/close','host CRT allocation/free/memcpy/cookie'],
        scope='original instructions, explicit temporary selector fixtures; consumer stops at dialog initialization')
    write_json(OUT/'evidence/family-donation-native-verification.json',result);print(json.dumps(result))


if __name__=='__main__':main()
