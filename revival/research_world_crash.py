"""Read-only minidump extraction and exact failing-instruction CPU replay."""
from pathlib import Path
import argparse
import json
import struct
import contextlib
from research_auth import data,BASE,md
from native_inspect import disasm

OUT=Path(__file__).parent/'evidence'
DEFAULT=Path(__file__).parent/'runtime/client/bin/2026-10-23 9-56-57.dmp'

def parse(path):
    d=path.read_bytes()
    def u32(off):return struct.unpack_from('<I',d,off)[0]
    assert d[:4]==b'MDMP'
    n,rva=u32(8),u32(12)
    streams={}
    for i in range(n):
        typ,size,loc=struct.unpack_from('<III',d,rva+i*12)
        streams[typ]=(loc,size)
    loc,size=streams[6]
    csize,crva=struct.unpack_from('<II',d,loc+160)
    ctx=d[crva:crva+csize]
    regs={k:struct.unpack_from('<I',ctx,v)[0] for k,v in {'edi':156,'esi':160,'ebx':164,'edx':168,'ecx':172,'eax':176,'ebp':180,'eip':184,'esp':196}.items()}
    memory=[]
    if 5 in streams:
        mloc,_=streams[5]
        for i in range(u32(mloc)):
            va,length,mrva=struct.unpack_from('<QII',d,mloc+4+i*16)
            memory.append((va,d[mrva:mrva+length]))
    if 9 in streams:
        mloc,_=streams[9]
        count,mrva=struct.unpack_from('<QQ',d,mloc)
        for i in range(count):
            va,length=struct.unpack_from('<QQ',d,mloc+16+i*16)
            memory.append((va,d[mrva:mrva+length]));mrva+=length
    def read(va,length):
        for start,buf in memory:
            if start<=va and va+length<=start+len(buf):return buf[va-start:va-start+length]
        return None
    stack=read(regs['esp'],128)
    result={'dump':str(path),'exception_code':hex(u32(loc+8)),
            'exception_address':hex(struct.unpack_from('<Q',d,loc+24)[0]),
            'exception_parameters':[hex(struct.unpack_from('<Q',d,loc+40+i*8)[0]) for i in range(min(u32(loc+32),15))],
            'registers':{k:hex(v) for k,v in regs.items()},'memory_ranges':len(memory),
            'stack_words':([hex(x) for x in struct.unpack('<32I',stack)] if stack else [])}
    return result,regs,read

def replay(regs):
    from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_MEM_INVALID,UcError
    from unicorn import x86_const as rc
    u=Uc(UC_ARCH_X86,UC_MODE_32)
    page=regs['eip']&~4095
    u.mem_map(page,4096)
    u.mem_write(page,data[page-BASE:page-BASE+4096])
    for name,value in regs.items():u.reg_write(getattr(rc,'UC_X86_REG_'+name.upper()),value)
    errors=[]
    def invalid(uc,kind,address,size,value,user):errors.append({'address':hex(address),'size':size,'kind':kind});return False
    u.hook_add(UC_HOOK_MEM_INVALID,invalid)
    try:u.emu_start(regs['eip'],regs['eip']+4,count=1)
    except UcError:pass
    observed=errors[0] if errors else None
    assert observed and int(observed['address'],16)==((regs['esi']+0x35)&0xffffffff),observed
    return {'verdict':'RED: original fault instruction reproduced its invalid read',
            'instruction':[f'{x.mnemonic} {x.op_str}' for x in md.disasm(data[regs['eip']-BASE:regs['eip']-BASE+4],regs['eip'])],
            'invalid_access':observed,'scope':'one original instruction with real dump registers; no application changes'}

def verify_time_decoder():
    from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
    from unicorn import x86_const as rc
    u=Uc(UC_ARCH_X86,UC_MODE_32)
    u.mem_map(BASE,(len(data)+4095)&~4095);u.mem_write(BASE,data)
    u.mem_map(0x5000000,0x20000)
    obj,stream,buf,stack,stop=0x5001000,0x5002000,0x5003000,0x5010000,0x501f000
    value=0x0000019a00001234
    payload=struct.pack('>Q',value)
    def w(a,*v):u.mem_write(a,struct.pack('<'+'I'*len(v),*v))
    w(obj,0x227034c,0xc0007,0,0)
    w(stream,0x224c100,buf,0);w(buf-12,8,8,1);u.mem_write(buf,payload)
    w(stack,stop,stream);u.reg_write(rc.UC_X86_REG_ECX,obj);u.reg_write(rc.UC_X86_REG_ESP,stack)
    u.emu_start(0xd53d00,stop,count=10000)
    actual=struct.unpack('<Q',u.mem_read(obj+8,8))[0]
    consumed=struct.unpack('<I',u.mem_read(stream+8,4))[0]
    assert actual==value and consumed==8
    # Narrow branch proof: with original missing global, ordinary time-handler
    # path reaches the unmodified creator call. Stop BEFORE any allocation.
    w(0x29455ac,0)
    visited=[]
    def stop_creator(uc,addr,size,user):
        visited.append(addr)
        if addr==0x816430:uc.emu_stop()
    u.hook_add(UC_HOOK_CODE,stop_creator)
    u.emu_start(0x81b54f,0x81b55d,count=20)
    assert 0x816430 in visited
    return {'protocol_name':'knight::gsp::SGameTime','type':0xc0007,'sample_be_u64':payload.hex(),
            'decoded_value':actual,'consumed':consumed,'native_decoder_completed':True,
            'time_normal_branch_reaches_activity_creator':True,
            'scope':'original decoder and missing-global branch to creator entry only; does not execute complete timer handler or resource-dependent creator'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--dump',type=Path,default=DEFAULT);p.add_argument('--replay',action='store_true');p.add_argument('--read',type=lambda x:int(x,0));p.add_argument('--length',type=lambda x:int(x,0),default=64);p.add_argument('--verify-time',action='store_true');p.add_argument('--evidence',action='store_true')
    a=p.parse_args();result,regs,read=parse(a.dump)
    if a.replay:result['replay']=replay(regs)
    if a.verify_time:result['time_verification']=verify_time_decoder()
    result['captured_activity_manager']=read(0x29455ac,4).hex()
    if a.evidence:
        with (OUT/'world-crash-disassembly.txt').open('w',encoding='utf-8') as f,contextlib.redirect_stdout(f):
            for addr,size in [(0x12a18f0,0x3e),(0x11e27fa,0x40),(0x816430,0x77),(0x81b3e0,0x1d9),(0x81f570,0x11),(0xd53c70,0x18),(0xd53d00,0x1a),(0xe40a40,0x18),(0x12a4c40,0xa9)]:
                print('\nRANGE',hex(addr));disasm(addr,size)
            for addr in (0x2886fe4,0x28d68e4):
                end=data.find(b'\0',addr-BASE);print(hex(addr),data[addr-BASE:end].decode('ascii'))
    if a.read is not None:
        raw=read(a.read,a.length);print(raw.hex() if raw else 'not captured');return
    (OUT/'world-crash-replay.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))

if __name__=='__main__':main()
