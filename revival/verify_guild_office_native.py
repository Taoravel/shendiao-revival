"""Original guild nomination/authority handlers executed offline, without GUI."""
import hashlib
import json
import struct
from native_inspect import DATA,BASE
from verify_social_native import native_payload
from inspect_client import OUT,write_json
import faction_protocol as p
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ECX,UC_X86_REG_ESI,UC_X86_REG_ESP,UC_X86_REG_EIP,UC_X86_REG_EAX


def execute(handler,rank=6,current=0,authority=0,mask=None):
    uc=Uc(UC_ARCH_X86,UC_MODE_32);uc.mem_map(0,4096)
    uc.mem_map(BASE,(len(DATA)+4095)&~4095);uc.mem_write(BASE,DATA)
    uc.mem_map(0x5000000,0x800000)
    control,manager,table,network=0x5001000,0x5002000,0x5003000,0x5004000
    own,target,item,event=0x5005000,0x5006000,0x5007000,0x5008000
    stack,stop,send,close=0x5100000,0x500f000,0x500e010,0x500e020
    def w(a,*v):uc.mem_write(a,struct.pack('<'+'I'*len(v),*v))
    def r(a):return struct.unpack('<I',uc.mem_read(a,4))[0]
    w(control+4,table);w(table+4,close);w(control+0x34,target)
    w(network,table+0x100);w(table+0x13c,send)
    w(0x2945570,manager);w(manager+0x3c0,own);w(own+0x54,rank)
    w(target,123,256);w(target+0x54,current);w(manager+0x3bc,authority)
    # This Q is the native dialog's NPC key; nomination instead reads target Q.
    w(control+0x20,123,256);w(item+0xc0,mask or 0);w(event+8,item)
    for stub in (send,close,stop):uc.mem_write(stub,b'\xc3')
    sent=[];guards=[]
    def ret(n=0,value=None):
        sp=uc.reg_read(UC_X86_REG_ESP)
        uc.reg_write(UC_X86_REG_EIP,r(sp));uc.reg_write(UC_X86_REG_ESP,sp+4+n)
        if value is not None:uc.reg_write(UC_X86_REG_EAX,value)
    def hook(machine,at,size,user):
        sp=machine.reg_read(UC_X86_REG_ESP)
        if at==stop:uc.emu_stop()
        elif at==0x813860:ret(value=network)
        elif at==0x4af0b0:ret(value=item)
        elif at in (0x1919184,close):ret()
        elif at==0x1625440:ret(4)
        elif at in (0x148ce02,0x148ce89):
            guards.append(hex(at));uc.reg_write(UC_X86_REG_EIP,0x148d004)
        elif at==0x15bb820:guards.append('protected_patrol');ret(12)
        elif at in (0x14e3b1d,0x14e3cfa):
            guards.append('authority_already_set' if at==0x14e3b1d else 'authority_not_set')
            uc.reg_write(UC_X86_REG_EIP,0x14e3c45 if at==0x14e3b1d else 0x14e3dd5)
        elif at==send:
            protocol=r(sp+4);kind=r(protocol+4)
            values=() if kind==p.RESIGN_FACTION_OFFICE else tuple(r(protocol+8+i*4)
                for i in range(4 if kind==p.SET_DEPUTY_AUTHORITY else 3))
            sent.append((kind,values));ret(4,value=1)
    uc.hook_add(UC_HOOK_CODE,hook)
    w(stack,stop,event);uc.reg_write(UC_X86_REG_ECX,control);uc.reg_write(UC_X86_REG_ESP,stack)
    uc.emu_start(handler,stop,count=100000)
    assert uc.reg_read(UC_X86_REG_EIP)==stop
    return sent,guards


def authority_context():
    uc=Uc(UC_ARCH_X86,UC_MODE_32);uc.mem_map(0,4096)
    uc.mem_map(BASE,(len(DATA)+4095)&~4095);uc.mem_write(BASE,DATA);uc.mem_map(0x5000000,0x800000)
    ui,manager,own,control,stack=0x5001000,0x5002000,0x5003000,0x5004000,0x5100000
    def w(a,*v):uc.mem_write(a,struct.pack('<'+'I'*len(v),*v))
    def r(a):return struct.unpack('<I',uc.mem_read(a,4))[0]
    w(ui+0xd0,123,256);w(0x2945570,manager);w(manager+0x3c0,own)
    w(own+0x54,6);w(0x2952490,control);w(stack,0x500f000)
    uc.reg_write(UC_X86_REG_ESI,ui);uc.reg_write(UC_X86_REG_ESP,stack)
    registrations=[]
    def ret(n=0,value=None):
        sp=uc.reg_read(UC_X86_REG_ESP)
        uc.reg_write(UC_X86_REG_EIP,r(sp));uc.reg_write(UC_X86_REG_ESP,sp+4+n)
        if value is not None:uc.reg_write(UC_X86_REG_EAX,value)
    def hook(machine,at,size,data):
        sp=machine.reg_read(UC_X86_REG_ESP)
        if at==0x1919184:ret()
        elif at==0x8015e0:ret(value=0x500a000)
        elif at==0x8013b0:
            registrations.append(tuple(r(sp+4+i*4) for i in range(5)));ret(20)
    uc.hook_add(UC_HOOK_CODE,hook);uc.emu_start(0x1637ad3,0x1637253,count=10000)
    assert uc.reg_read(UC_X86_REG_EIP)==0x1637253
    assert r(control+0x20)+(r(control+0x24)<<32)==2**40+123
    assert registrations==[(123,256,1,control+4,13)]
    report=dict(passed=['original NPC UI d0/d4 key traverses 1637ad3 ->148d6b0 ->14e4600 ->authority dialog +20/+24'],
        image_sha256=hashlib.sha256(DATA).hexdigest(),npc_key=2**40+123,dialog_registration=registrations,
        npc_key_origin='SVisitNpc ->1635f10 stores key d0/d4; original instructions re-read',native_gui_verified=False,
        scope='offline original NPC dispatch-to-dialog chain; timer/dialog registry and security-check edges adapted')
    write_json(OUT/'evidence/guild-authority-context-verification.json',report)


def main():
    passed=[]
    for name,handler in (('deputy',0x14a8cd0),('left_elder',0x14a8d00),('right_elder',0x14a8d30),
                         ('patrol',0x14a8d60),('member',0x14a8d90)):
        flag=p.GUILD_POSITIONS[name]
        assert execute(handler,current=1 if flag==0 else 0)==([(p.FACTION_POSITION,(123,256,flag))],[])
        passed.append('original nomination button '+name+' emits '+str(flag))
    for rank,authority,expected in ((5,0,False),(5,64,True),(4,511,False)):
        sent,guards=execute(0x14a8d00,rank=rank,authority=authority)
        assert bool(sent)==expected and bool(guards)!=expected
        passed.append('original appointment guard rank '+str(rank)+' authority '+str(authority))
    assert execute(0x14a8d60,current=3)==([],['protected_patrol'])
    passed.append('original higher officer cannot overwrite directly with patrol')
    for bit in range(9):
        mask=1<<bit
        for handler,current,enabled in ((0x14e3ad0,0,1),(0x14e3c60,mask,0)):
            assert execute(handler,authority=current,mask=mask)==([(p.SET_DEPUTY_AUTHORITY,(123,256,mask,enabled))],[])
        raw=struct.pack('>Qii',2**40+123,mask,1)
        assert native_payload(0xe45830,scalars=[(8,123),(0xc,256),(0x10,mask),(0x14,1)])==raw
        assert p.decode(p.SET_DEPUTY_AUTHORITY,raw)==(2**40+123,mask,1)
        passed.append('original grant/revoke button and serializer one-hot '+str(mask))
    for handler,authority,reason in ((0x14e3ad0,64,'authority_already_set'),(0x14e3c60,0,'authority_not_set')):
        assert execute(handler,authority=authority,mask=64)==([],[reason])
        passed.append('original duplicate authority guard '+reason)
    assert execute(0x148d020)==([(p.RESIGN_FACTION_OFFICE,())],[])
    assert native_payload(0xd6e100)==b'' and p.decode(p.RESIGN_FACTION_OFFICE,b'')==()
    passed.append('original outgoing confirmation emits empty office resignation c5622')
    for mask in (0,64,256,511):assert native_payload(0xe467b0,scalars=[(8,mask)])==p.deputy_authority(mask)
    passed.append('native authority response c5638 supports all nine bits')
    authority_context()
    result=dict(passed=passed,image_sha256=hashlib.sha256(DATA).hexdigest(),native_gui_verified=False,
        scope='original nomination/authority handlers and manager executed offline; network/dialog/string warning edges adapted',
        native_guild_management_routes_integrated=False)
    write_json(OUT/'evidence/guild-ui-verification.json',result);print(json.dumps(dict(passed=len(passed))))


if __name__=='__main__':main()
