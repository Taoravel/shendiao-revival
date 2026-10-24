"""Original family appointment clicks/guards, offline x86 execution only."""
import hashlib
import json
import struct
from native_inspect import DATA,BASE
from inspect_client import OUT,write_json
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP,UC_X86_REG_EAX


def click(handler,target,*,deputy=True,review_flag=None):
    uc=Uc(UC_ARCH_X86,UC_MODE_32);uc.mem_map(0,4096)
    uc.mem_map(BASE,(len(DATA)+4095)&~4095);uc.mem_write(BASE,DATA)
    uc.mem_map(0x5000000,0x800000)
    control,manager,table,network=0x5001000,0x5002000,0x5003000,0x5004000
    head,records,role,stack,stop=0x5005000,0x5006000,0x5007000,0x5100000,0x500f000
    send,close=0x500e010,0x500e020
    def w(a,*v):uc.mem_write(a,struct.pack('<'+'I'*len(v),*v))
    def r(a):return struct.unpack('<I',uc.mem_read(a,4))[0]
    w(control+4,table);w(table+4,close);w(control+0x30,target,0)
    w(network,table+0x100);w(table+0x13c,send)
    w(0x2945570,manager);w(0x2944550,role);w(role+0xf8,1,0)
    w(manager+0xb4,head);w(manager+0xcc,records);w(manager+0x228,103)
    nodes=[head+0x100+i*0x40 for i in range(3)]
    w(head,nodes[0])
    for i,position in enumerate((2,1 if deputy else 0,0)):
        data=records+i*0x100
        w(nodes[i],nodes[i+1] if i<2 else head,0,data)
        w(data,i+1,0);w(data+0x34,position)
    for stub in (send,close,stop):uc.mem_write(stub,b'\xc3')
    sent=[];tips=[]
    def ret(n=0,value=None):
        sp=uc.reg_read(UC_X86_REG_ESP)
        uc.reg_write(UC_X86_REG_EIP,r(sp));uc.reg_write(UC_X86_REG_ESP,sp+4+n)
        if value is not None:uc.reg_write(UC_X86_REG_EAX,value)
    def hook(machine,at,size,user):
        sp=machine.reg_read(UC_X86_REG_ESP)
        if at==stop:uc.emu_stop()
        elif at==0x813860:ret(value=network)
        elif at==0x1919184 or at==close:ret()
        elif at==0x15bb820:tips.append(r(r(sp+4)));ret(12)
        elif at==send:
            protocol=r(sp+4)
            sent.append((r(protocol+4),r(protocol+8),r(protocol+0xc),r(protocol+0x10)))
            ret(4,value=1)
    uc.hook_add(UC_HOOK_CODE,hook)
    if review_flag is None:w(stack,stop,0x5008000)
    else:w(stack,stop,target,0,review_flag);w(manager+0x168,20)
    uc.reg_write(UC_X86_REG_ECX,control if review_flag is None else manager);uc.reg_write(UC_X86_REG_ESP,stack)
    uc.emu_start(handler,stop,count=100000)
    assert uc.reg_read(UC_X86_REG_EIP)==stop
    return sent,tips


def main():
    cases=[('leader button transfers to existing deputy',0x14c3000,2,True,[(0xc5604,2,0,2)],[]),
           ('self deputy means abdication',0x14c3030,1,True,[(0xc5604,1,0,1)],[]),
           ('self member means abdication',0x14c3060,1,True,[(0xc5604,1,0,0)],[]),
           ('self abdication requires successor',0x14c3060,1,False,[],[140172]),
           ('ordinary member cannot skip deputy',0x14c3000,3,True,[],[140176]),
           ('second deputy slot rejected',0x14c3030,3,True,[],[140177]),
           ('patrol button is guild appointment 1',0x14c2fd0,3,True,[(0xc5621,3,0,1)],[])]
    passed=[]
    for name,handler,target,deputy,packets,tips in cases:
        actual=click(handler,target,deputy=deputy)
        assert actual==(packets,tips),(name,actual)
        passed.append(dict(name=name,handler=hex(handler),packets=packets,tips=tips))
    for flag in (0,1):
        sent,tips=click(0x14970f0,4,review_flag=flag)
        assert sent==[(0xc55fe,4,0,flag)] and not tips
        passed.append(dict(name='original family review manager '+str(flag),handler='0x14970f0',packets=sent,tips=tips))
    report=dict(passed=passed,image_sha256=hashlib.sha256(DATA).hexdigest(),
                scope='original handler/manager/roster lookup execution, adapted network/tip/dialog edges',native_gui_verified=False)
    write_json(OUT/'evidence/faction-ui-verification.json',report)
    print(json.dumps(report))


if __name__=='__main__':main()
