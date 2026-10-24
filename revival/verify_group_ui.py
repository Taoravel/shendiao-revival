"""Execute original native Agree/Refuse click handlers; no live GUI interaction.

Only network acquisition/send, dialog close and CRT cookie checks are adapted.
The original handler constructs the protocol and fills its fields itself.
"""
import hashlib
import json
import struct
from native_inspect import DATA,BASE
from inspect_client import OUT,write_json
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP,UC_X86_REG_EAX


def click(address,invitation):
    uc=Uc(UC_ARCH_X86,UC_MODE_32)
    uc.mem_map(0,4096)
    uc.mem_map(BASE,(len(DATA)+4095)&~4095);uc.mem_write(BASE,DATA)
    uc.mem_map(0x5000000,0x800000)
    control,network,table,stack,stop=0x5001000,0x5002000,0x5003000,0x5100000,0x500f000
    send,close=0x500e010,0x500e020
    def w(a,*v):uc.mem_write(a,struct.pack('<'+'I'*len(v),*v))
    def r(a):return struct.unpack('<I',uc.mem_read(a,4))[0]
    w(control+4,table);w(table+4,close)
    w(network,table+0x100);w(table+0x13c,send)
    w(control+0x30,567 if invitation else 123,0,567,0)
    for stub in (send,close,stop):uc.mem_write(stub,b'\xc3')
    sent=[]
    def ret(n=0,value=None):
        sp=uc.reg_read(UC_X86_REG_ESP)
        uc.reg_write(UC_X86_REG_EIP,r(sp));uc.reg_write(UC_X86_REG_ESP,sp+4+n)
        if value is not None:uc.reg_write(UC_X86_REG_EAX,value)
    def hook(machine,at,size,user):
        if at==stop:uc.emu_stop()
        elif at==0x813860:ret(value=network)
        elif at==0x1919184 or at==close:ret()
        elif at==send:
            protocol=r(uc.reg_read(UC_X86_REG_ESP)+4)
            values=[r(protocol+offset) for offset in ((8,0x10,0x14) if invitation else (8,0x10,0x14,0x18,0x1c))]
            sent.append(dict(kind=r(protocol+4),values=values));ret(4,value=1)
    uc.hook_add(UC_HOOK_CODE,hook)
    w(stack,stop,0x5004000)
    uc.reg_write(UC_X86_REG_ECX,control);uc.reg_write(UC_X86_REG_ESP,stack)
    uc.emu_start(address,stop,count=100000)
    assert uc.reg_read(UC_X86_REG_EIP)==stop and len(sent)==1
    return sent[0]


def main():
    # Native UI creation binds these literal control names to these handlers.
    cases=[('ReplyInviteGroupDlg/Agree',0x22cc434,0x16ef820,True,1),
           ('ReplyInviteGroupDlg/Refuse',0x22cc3fc,0x16ef8b0,True,0),
           ('OwnerReplyJointDlg/Agree',0x22cc500,0x16f0280,False,0),
           ('OwnerReplyJointDlg/Refuse',0x22cc4c8,0x16f0310,False,1)]
    passed=[]
    for name,literal,handler,invitation,flag in cases:
        assert DATA[literal-BASE:literal-BASE+len(name)+1]==name.encode()+b'\0'
        actual=click(handler,invitation)
        assert actual['kind']==(0xc4e53 if invitation else 0xc4e4b)
        assert actual['values']==([flag,567,0] if invitation else [flag,123,0,567,0]),(name,actual)
        passed.append(dict(button=name,handler=hex(handler),kind=hex(actual['kind']),decision=flag))
    assert DATA[0x22ca500-BASE:0x22ca500-BASE+12].decode('utf-16-le')=='  (%s)'
    result=dict(passed=passed,history_time_format_native_address='0x22ca500',
        image_sha256=hashlib.sha256(DATA).hexdigest(),scope='original x86 handler execution, adapted UI/network edges',native_gui_verified=False)
    write_json(OUT/'evidence/group-ui-verification.json',result)
    print(json.dumps(result))


if __name__=='__main__':main()
