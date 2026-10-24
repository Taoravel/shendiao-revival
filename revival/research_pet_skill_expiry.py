"""Original server-time synchronization and timed learned-skill consumers."""
from pathlib import Path
import json
import struct

from native_gameplay_probe import probe
from native_inspect import u32
from research_pet_skills import observe_skills
from inspect_client import OUT,write_json


def synchronize_clock(uc,now_ms):
    from unicorn import UC_HOOK_CODE
    from unicorn.x86_const import UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
    def w(a,*v):uc.mem_write(a,struct.pack('<'+'I'*len(v),*v))
    stack,stop,message,stream,buf=0x5108000,0x500f000,0x5307000,0x5002000,0x5003000
    w(stack,stop);uc.reg_write(UC_X86_REG_ECX,message);uc.reg_write(UC_X86_REG_ESP,stack)
    uc.emu_start(0xd53c70,stop,count=1000)
    uc.mem_write(buf,struct.pack('>q',now_ms));w(buf-8,8);w(stream+8,0)
    w(stack,stop,stream);uc.reg_write(UC_X86_REG_ECX,message);uc.reg_write(UC_X86_REG_ESP,stack)
    uc.emu_start(0xd53d00,stop,count=1000)
    assert struct.unpack('<q',uc.mem_read(message+8,8))[0]==now_ms
    target=u32(0x22448d4)
    uc.mem_map(target&~4095,4096)
    captured=[]
    def calendar(uc,address,size,user):
        if address!=target:return
        sp=uc.reg_read(UC_X86_REG_ESP)
        ptr=struct.unpack('<I',uc.mem_read(sp+8,4))[0]
        captured.append(struct.unpack('<q',uc.mem_read(ptr,8))[0]);uc.emu_stop()
    hook=uc.hook_add(UC_HOOK_CODE,calendar)
    w(stack,stop,0,0);uc.reg_write(UC_X86_REG_ECX,message);uc.reg_write(UC_X86_REG_ESP,stack)
    uc.emu_start(0x81f570,stop,count=10000);uc.hook_del(hook)
    assert uc.reg_read(UC_X86_REG_EIP)==target
    assert struct.unpack('<q',uc.mem_read(0x2945088,8))[0]==now_ms
    assert captured==[now_ms//1000]
    return {'server_ms':now_ms,'calendar_seconds':captured[0]}


def native_timed_record(payload,now_ms):
    result=[]
    def observe(uc,message):
        clock=synchronize_clock(uc,now_ms)
        skills,icons=observe_skills(uc,message)
        result.append((skills,icons,clock))
    probe(0xf9d7b0,0xf9d840,0xf9d880,payload=payload,observer=observe)
    return result[0]


def main():
    import pefile
    # Resolve the exact archived IAT target using the matching side-by-side CRT.
    matches=[]
    for p in Path('C:/Windows/WinSxS').glob('x86_microsoft.vc80.crt*/msvcr80.dll'):
        pe=pefile.PE(str(p));exports={s.name:s.address for s in pe.DIRECTORY_ENTRY_EXPORT.symbols if s.name}
        base=u32(0x2244890)-exports[b'malloc']
        if (base+exports[b'free']==u32(0x2244894)
                and base+exports[b'_localtime64_s']==u32(0x22448d4)):
            matches.append({'module':p.parent.name,'base':hex(base),'function':'_localtime64_s',
                            'iat':'0x22448d4','target':hex(u32(0x22448d4))})
    assert matches,'Matching original calendar import evidence unavailable'
    obj=0x5001000;lh=obj+0x300;n1=obj+0x320;n2=obj+0x340;th=obj+0x380;tn=obj+0x3c0
    rows=[]
    for expiry in (1000,1700000000123,32535215999000):
        fields={4:struct.pack('<i',500001),8:struct.pack('<i',7),
            0xbc:struct.pack('<II',lh,2),0x300:struct.pack('<II',n1,n2),
            0x320:struct.pack('<III',n2,lh,200484),0x340:struct.pack('<III',lh,n1,200061),
            0xc8:struct.pack('<II',th,1),0x380:struct.pack('<III',tn,tn,tn)+bytes(0x14)+b'\0\1',
            0x3c0:struct.pack('<III',th,th,th)+bytes(4)+struct.pack('<i',200484)+bytes(4)
                +struct.pack('<q',expiry)+b'\1\0'}
        payload,_=probe(0xf89ba0,0xf5df70,0xf5f1f0,fields)
        for now in (expiry-1,expiry,expiry+1):
            skills,icons,clock=native_timed_record(payload,now)
            assert skills==(200484,200061)
            expected=(0x60000001,200484,expiry&0xffffffff,expiry>>32) if now<=expiry else (0x60000001,200534,0,0)
            assert icons==(expected,(0x60000002,200061,0,0))
            rows.append(dict(clock,expiry_ms=expiry,icon_arguments=icons))
    write_json(OUT/'evidence/pet-skill-clock-expiry-native.json',{
        'source_status':'client_verified','passed':len(rows),'cases':rows,'import':matches,
        'clock_path':'SGameTime c0007 ctord53c70/decoderd53d00 ->81f570->81b3e0 stores singleton+28 then original signed64 divide1000 before _localtime64_s',
        'skill_path':'Pet+c4 original codec ->11353c9..1135429 learned/expiry copy ->140dfb2..140e0ed original icon loop reads same clock',
        'units':'Unix epoch milliseconds; calendar import accepts seconds since1970',
        'reference':'https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/localtime-s-localtime32-s-localtime64-s',
        'limits':['OS calendar call observed before its other UI side effects','No live client/server interaction','Client clock advancement between SGameTime packets not established here']})
    print('PASS',len(rows),'original SGameTime codec/store/divide1000 and timed icon boundary cases; matching CRT import verified')


if __name__=='__main__':main()
