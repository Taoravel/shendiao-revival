"""Offline native-image inspection only. No process access or mutation."""
from pathlib import Path
import argparse
import struct
import sys
sys.path.insert(0, 'D:/Downloads/LCJDTClient/LCJDTClient/revival/.deps')
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

BASE = 0x400000
IMAGE = Path(__file__).parent / 'evidence/native-image.bin'
data = IMAGE.read_bytes()
md = Cs(CS_ARCH_X86, CS_MODE_32)

def hits(needle):
    at = 0
    while True:
        at = data.find(needle, at)
        if at < 0:
            return
        yield BASE + at
        at += 1

def refs(address):
    return list(hits(struct.pack('<I', address)))

def disasm(address, length):
    for ins in md.disasm(data[address-BASE:address-BASE+length], address):
        print(f'{ins.address:08x}: {ins.mnemonic:8} {ins.op_str}')

def strings(term):
    for addr in hits(term.encode()):
        start = addr-BASE
        end = data.find(b'\0', start)
        print(hex(addr), repr(data[start:end]), 'refs', [hex(x) for x in refs(addr)])

def rtti(name):
    if '@' not in name: name+='@gnet'
    for addr in hits(('.?AV'+name+'@@').encode()):
        td=addr-8
        print('type',hex(td))
        for ref in refs(td):
            col=ref-12
            sig,off,cd,_,hier=struct.unpack_from('<IIIII',data,col-BASE)
            if sig==0 and off<0x1000 and cd==0:
                for r in refs(col):
                    print('COL',hex(col),'vtable',hex(r+4))
                    for n in range(12):
                        fn=struct.unpack_from('<I',data,r+4+n*4-BASE)[0]
                        print(n,hex(fn))

def native_compress(raw):
    """Execute only the isolated pure compressor on an emulated CPU."""
    from unicorn import Uc, UC_ARCH_X86, UC_MODE_32
    from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EAX
    u=Uc(UC_ARCH_X86,UC_MODE_32)
    u.mem_map(BASE,(len(data)+4095)&~4095)
    u.mem_write(BASE,data)
    area=0x5000000
    u.mem_map(area,0x40000)
    src, table, cursor, dest, stack, stop=(area,area+0x10000,area+0x11000,area+0x20000,area+0x3f000,area+0x3fff0)
    u.mem_write(src,raw+b'\0'*8)
    u.mem_write(table,struct.pack('<I',src)*256)
    u.mem_write(cursor,struct.pack('<I',src))
    u.mem_write(stack,struct.pack('<IIIII',stop,dest,len(raw),cursor,table))
    u.reg_write(UC_X86_REG_ESP,stack)
    u.emu_start(0x1918cb0,stop,count=1000000)
    end=u.reg_read(UC_X86_REG_EAX)
    return bytes(u.mem_read(dest,end-dest))

def literal_compress(raw):
    bits=''.join((f'{b:08b}' if b<128 else '10'+f'{b&127:07b}') for b in raw)+'1111000000'
    bits+='0'*((-len(bits))%8)
    return int(bits,2).to_bytes(len(bits)//8,'big')

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--find')
    p.add_argument('--refs', type=lambda x:int(x,0))
    p.add_argument('--disasm', type=lambda x:int(x,0))
    p.add_argument('--length', type=lambda x:int(x,0), default=256)
    p.add_argument('--words', type=lambda x:int(x,0))
    p.add_argument('--rtti')
    p.add_argument('--findhex')
    p.add_argument('--offset', type=lambda x:int(x,0))
    p.add_argument('--calls', type=lambda x:int(x,0))
    p.add_argument('--compress')
    p.add_argument('--self-check', action='store_true')
    p.add_argument('--evidence', action='store_true')
    a=p.parse_args()
    if a.find: strings(a.find)
    if a.rtti: rtti(a.rtti)
    if a.findhex: print([hex(x) for x in hits(bytes.fromhex(a.findhex))])
    if a.offset is not None:
        for ins in md.disasm(data[0x774000-BASE:0x778000-BASE],0x774000):
            if hex(a.offset) in ins.op_str:
                print(f'{ins.address:08x}: {ins.mnemonic:8} {ins.op_str}')
    if a.calls is not None:
        result=[]
        for addr in hits(b'\xe8'):
            if addr-BASE+5 <= len(data):
                target=addr+5+struct.unpack_from('<i',data,addr-BASE+1)[0]
                if target == a.calls: result.append(hex(addr))
        print(result)
    if a.compress is not None:
        raw=bytes.fromhex(a.compress)
        print('native',native_compress(raw).hex(),'literal',literal_compress(raw).hex())
    if a.self_check:
        cases=[bytes.fromhex('010203807f80ff'),bytes(range(128)),bytes(range(128,256)),bytes(range(256))]
        for raw in cases:
            assert native_compress(raw)==literal_compress(raw),(len(raw),'mismatch')
        print('4 literal-stream comparisons matched the emulated original compressor')
    if a.evidence:
        import contextlib
        import hashlib
        out=Path(__file__).parent/'evidence/auth-disassembly.txt'
        with out.open('w',encoding='utf-8') as f, contextlib.redirect_stdout(f):
            print('image sha256',hashlib.sha256(data).hexdigest())
            print('\nNETWORK VERSION CALLER EVIDENCE')
            for addr,length in [(0x82acf0,0x80),(0x82af3b,0x1a),(0x82c43b,0x2a),(0x82c698,0x38)]:
                disasm(addr,length)
            for addr,length in [(0x7897b0,0x140),(0x7716e0,0x160),(0x7787d0,0x130),(0x7720b0,0xd5),(0x772400,0x210),(0x7706b0,0xf0),(0x774a00,0x310),(0x774e00,0x320),(0x7746a0,0xf0),(0x774930,0xd0),(0x7738a0,0x190),(0x776ce0,0x350),(0x781b30,0x100),(0x78cd00,0x50),(0x78d600,0x60),(0x8158e0,0x40),(0x82af3b,0x1a),(0x1918cb0,0x4c0),(0x78c460,0x150),(0x776690,0x20),(0x770fc0,0x50),(0x77c370,0xc0),(0x781fa0,0x140),(0x7770d0,0x210)]:
                print('\nFUNCTION / RANGE',hex(addr))
                disasm(addr,length)
        print(out)
    if a.refs is not None: print('refs', [hex(x) for x in refs(a.refs)])
    if a.disasm is not None: disasm(a.disasm,a.length)
    if a.words is not None:
        for addr in range(a.words,a.words+a.length,4):
            print(hex(addr),hex(struct.unpack_from('<I',data,addr-BASE)[0]))

if __name__=='__main__': main()
