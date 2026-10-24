"""Offline battle protocol research against this installation's native image.

Original constructors and unmarshallers execute in Unicorn. Host adapters cover
allocation, CRT memory copy and STL UTF16 assignment, never wire decoding.
"""
import hashlib
import json
import struct
from pathlib import Path
from native_inspect import BASE, DATA, u32, vtables, refs

OUT = Path(__file__).parent / 'evidence'
CLASSES = {
    'SSendBattleStart': (0xd5baa0, 0xd5bb50),
    'SSendAddFighters': (0xfc02e0, 0xfc0840),
    'SSendRoundStart': (0xec6350, 0xec6400),
    'CSendAction': (0xd598c0, 0xd59ab0),
    'CSendRoundPlayEnd': (0xe69bc0, 0xe69cd0),
    'SSendRoundScript': (0xfef0f0, 0xff1240),
    'SSendRoundPlayEnd': (0xd5c870, 0xd5c900),
    'SSendBattleEnd': (0xec57f0, 0xec5900),
    'SSendRoleInitAttrs': (0xec5fd0, 0xec60e0),
    'SSendPetInitAttrs': (0xec5ce0, 0xec5df0),
    'SSendOtherSkills': (0xf30da0,0xf30e50),
}


class NativeBattleDecoder:
    def __init__(self):
        from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
        from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_EAX
        self.cx, self.sp, self.ip, self.ax = UC_X86_REG_ECX, UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_EAX
        self.u = u = Uc(UC_ARCH_X86, UC_MODE_32)
        u.mem_map(0, 0x1000)
        u.mem_map(BASE, (len(DATA)+4095)&~4095)
        u.mem_write(BASE, DATA)
        u.mem_map(0x5000000, 0x1000000)
        self.heap = 0x5400000
        self.obj, self.stream, self.buf = 0x5001000, 0x5002000, 0x5010000
        self.stack, self.stop = 0x5100000, 0x500f000
        imports = {u32(a): k for a, k in (
            (0x2244890,'alloc'), (0x2244894,'free'),
            (0x2244354,'dec'), (0x2244334,'inc'),
            (0x2244450,'wstring'), (0x224446c,'string_copy'),
            (0x2244514,'begin'), (0x2244510,'end'))}
        imports.update({0x1919178:'alloc', 0x191910c:'free', 0x1919184:'cookie', 0x19191c2:'copy', 0x74a6d0:'assign'})
        for page in {a&~4095 for a in imports if not BASE <= a < BASE+len(DATA)}:
            u.mem_map(page, 4096)

        def hook(uc, addr, size, user):
            if addr == self.stop:
                uc.emu_stop()
                return
            kind = imports.get(addr)
            if not kind:
                return
            sp = uc.reg_read(self.sp)
            def ret(n=0, value=None):
                if value is not None: uc.reg_write(self.ax, value)
                uc.reg_write(self.ip, self.read(sp))
                uc.reg_write(self.sp, sp+4+n)
            if kind == 'alloc':
                count = self.read(sp+4)
                ptr = self.allocate(count)
                ret(value=ptr)
            elif kind in ('free','cookie'): ret()
            elif kind in ('dec','inc'):
                ptr = self.read(sp+4)
                value = (self.read(ptr) + (1 if kind=='inc' else -1)) & 0xffffffff
                self.write(ptr,value)
                ret(4,value)
            elif kind == 'copy':
                dst,src,count = (self.read(sp+i) for i in (4,8,12))
                if count: uc.mem_write(dst,bytes(uc.mem_read(src,count)))
                ret(value=dst)
            elif kind == 'wstring':
                ptr=uc.reg_read(self.cx)
                uc.mem_write(ptr,bytes(28));self.write(ptr+24,7);ret(value=ptr)
            elif kind == 'string_copy':
                ptr=uc.reg_read(self.cx);src=self.read(sp+4)
                count=self.read(src+20)
                source=src+4 if self.read(src+24)<8 else self.read(src+4)
                dest=ptr+4 if count<=7 else self.allocate(count*2+2)
                uc.mem_write(ptr,bytes(28));self.write(ptr+24,max(7,count))
                uc.mem_write(dest,bytes(uc.mem_read(source,count*2))+bytes(2))
                if count>7:self.write(ptr+4,dest)
                self.write(ptr+20,count);ret(4,ptr)
            elif kind in ('begin','end'):
                ptr=uc.reg_read(self.cx);result=self.read(sp+4)
                data=ptr+4 if self.read(ptr+24)<8 else self.read(ptr+4)
                if kind=='end': data+=self.read(ptr+20)*2
                self.write(result,ptr,data);ret(4,result)
            elif kind == 'assign':
                ptr=uc.reg_read(self.cx);start,end=self.read(sp+20),self.read(sp+24)
                value=bytes(uc.mem_read(start,end-start));count=len(value)//2
                dest=ptr+4 if count<=7 else self.allocate(len(value)+2)
                uc.mem_write(dest,value+b'\0\0')
                if count>7:self.write(ptr+4,dest);self.write(ptr+24,count)
                self.write(ptr+20,count);ret(28,ptr)
        u.hook_add(UC_HOOK_CODE,hook)

    def allocate(self, size):
        ptr=self.heap;self.heap+=(size+15)&~15
        if self.heap >= 0x6000000: raise RuntimeError('Probe heap exhausted')
        return ptr

    def read(self, addr):
        return struct.unpack('<I',self.u.mem_read(addr,4))[0]

    def write(self, addr, *values):
        self.u.mem_write(addr,struct.pack('<'+'I'*len(values),*values))

    def call(self, addr, *args):
        self.write(self.stack,self.stop,*args)
        self.u.reg_write(self.sp,self.stack);self.u.reg_write(self.cx,self.obj)
        try: self.u.emu_start(addr,self.stop,count=2000000)
        except Exception as exc: raise RuntimeError(f'Native probe stopped at {self.u.reg_read(self.ip):x}') from exc
        assert self.u.reg_read(self.ip)==self.stop

    def decode(self, name, payload):
        constructor,decoder=CLASSES[name]
        self.call(constructor)
        self.write(self.stream,0x224c100,self.buf,0)
        self.write(self.buf-12,len(payload),len(payload),1)
        self.u.mem_write(self.buf,payload)
        self.call(decoder,self.stream)
        assert self.read(self.stream+8)==len(payload), (name,'trailing bytes')
        return self

    def list_items(self, container):
        head=self.read(container+4);node=self.read(head);result=[]
        while node!=head:
            assert len(result)<100
            result.append(node+8);node=self.read(node)
        assert len(result)==self.read(container+8)
        return result


def main():
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    md=Cs(CS_ARCH_X86,CS_MODE_32)
    result={'image_sha256':hashlib.sha256(DATA).hexdigest(),'classes':{}}
    lines=[]
    for name,(ctor,decoder) in CLASSES.items():
        namespace='skill' if name=='SSendOtherSkills' else 'battle'
        table=vtables('.?AV'+name+'@'+namespace+'@gsp@knight@@')[0]
        result['classes'][name]={'constructor':hex(ctor),'vtable':hex(table),
            'marshal':hex(u32(table)), 'unmarshal':hex(decoder),'process':hex(u32(table+24))}
        for addr,size in ((ctor,128),(u32(table),1600),(decoder,2000),(u32(table+24),1200)):
            lines.append(f'\n{name} {addr:x}')
            for i in md.disasm(DATA[addr-BASE:addr-BASE+size],addr):
                if i.mnemonic!='int3':lines.append(f'{i.address:08x} {i.mnemonic} {i.op_str}')
    (OUT/'battle-disassembly.txt').write_text('\n'.join(lines),encoding='utf-8')
    (OUT/'battle-protocol-index.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
