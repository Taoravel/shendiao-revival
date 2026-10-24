"""First-party opening evidence only; no runtime, GUI, or character mutations."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
sys.path.insert(0,'D:/Downloads/LCJDTClient/LCJDTClient/revival/.deps')
from native_inspect import BASE,DATA,disasm

ROOT=Path(__file__).parent
FUNCTIONS={'start_process':(0x12c43b0,0x18),'start_decode':(0xd57540,0x6b),
           'end_decode':(0xd4f110,0x6b),'end_send':(0x12c0970,0x111),
           'natural_end':(0x12c0b10,0x49),'movie_loader':(0x12c3be0,0xd0),
           'zero_exp_branch':(0x83380a,0x42),'zero_exp_overlay':(0x11df870,0x118),
           'animation_parser':(0xbb6751,0x3f)}


def native_decode(address,movie_id):
    from unicorn import Uc,UC_ARCH_X86,UC_MODE_32
    from unicorn.x86_const import UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
    emu=Uc(UC_ARCH_X86,UC_MODE_32)
    emu.mem_map(BASE,(len(DATA)+4095)&~4095);emu.mem_write(BASE,DATA)
    emu.mem_map(0x5000000,0x10000)
    obj,stream,buf,stack,stop=0x5001000,0x5002000,0x5003000,0x500f000,0x5000100
    def w(a,*v):emu.mem_write(a,struct.pack('<'+'I'*len(v),*v))
    payload=struct.pack('>i',movie_id)
    w(stream,0,buf,0);w(buf-12,4,4,1);emu.mem_write(buf,payload);w(stack,stop,stream)
    emu.reg_write(UC_X86_REG_ESP,stack);emu.reg_write(UC_X86_REG_ECX,obj)
    emu.emu_start(address,stop,count=1000)
    decoded=struct.unpack('<i',emu.mem_read(obj+8,4))[0]
    consumed=struct.unpack('<I',emu.mem_read(stream+8,4))[0]
    assert emu.reg_read(UC_X86_REG_EIP)==stop and decoded==movie_id and consumed==4
    return {'decoder':hex(address),'body_hex':payload.hex(),'decoded_movie_id':decoded,'consumed':consumed}


def main():
    p=argparse.ArgumentParser();p.add_argument('--disasm',choices=FUNCTIONS)
    args=p.parse_args()
    if args.disasm:disasm(*FUNCTIONS[args.disasm]);return
    rows=json.loads((ROOT/'catalogs/knight.gsp.task.cmainmissioninfo.json').read_text(encoding='utf-8'))
    table={int(r['attributes']['id']):r for r in rows}
    incoming=lambda q:[int(r['attributes']['id']) for r in rows if str(q) in r['lists'].get('PostMissionList',[])]
    movie=(ROOT/'extracted/config/movie/11001.txt').read_bytes()
    # Preserve the original BOM-marked UTF16 source file.
    text=movie.decode('utf-16')
    result={'image_sha256':hashlib.sha256(DATA).hexdigest(),
            'root':table[100101], 'root_incoming':incoming(100101),'task100192_incoming':incoming(100192),
            'movie11001_sha256':hashlib.sha256(movie).hexdigest(),
            'movie_map_commands':[s for s in text.splitlines() if s.lower().startswith('setmap ')],
            'movie_final_commands':[s for s in text.splitlines() if s.startswith(('Return ','End'))],
            'native_decoders':[native_decode(0xd57540,11001),native_decode(0xd4f110,11001)]}
    assert result['root_incoming']==[] and result['task100192_incoming']==[100112]
    assert table[100101]['attributes']['MissionType']=='50'
    assert table[100101]['attributes']['ScenarioInfoAnimationID']=='11001'
    (ROOT/'evidence/story-opening-native-evidence.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='root'},ensure_ascii=True,indent=2))


if __name__=='__main__':main()
