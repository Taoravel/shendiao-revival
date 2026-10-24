"""Execute original gameplay codecs offline; never calls the running client."""
import struct
from native_inspect import BASE, DATA, u32

def probe(constructor, serializer, decoder, fields=None, payload=None, *, observer=None, host_imports=None, factory=False):
    from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
    from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_EAX
    emu=Uc(UC_ARCH_X86,UC_MODE_32)
    emu.mem_map(0,0x1000)
    emu.mem_map(BASE,(len(DATA)+0xfff)&~0xfff)
    emu.mem_write(BASE,DATA)
    emu.mem_map(0x5000000,0x400000)
    obj,stream,buf,stack,stop=0x5001000,0x5002000,0x5003000,0x5100000,0x500f000
    read=lambda a:struct.unpack('<I',emu.mem_read(a,4))[0]
    def w(a,*v):emu.mem_write(a,struct.pack('<'+'I'*len(v),*v))
    w(stream,0x224c100,buf,0)
    w(buf-12,0x7000,0,1)
    w(stack,stop,stream)
    heap=[0x5200000]
    imports={u32(x):kind for x,kind in ((0x2244890,'alloc'),(0x2244894,'free'),(0x2244354,'decrement'),(0x2244334,'increment'),(0x2244450,'wstring_ctor'),(0x2244514,'string_begin'),(0x2244510,'string_end'))}
    imports[0x1919178]='alloc'
    imports[0x191910c]='free'
    imports[u32(0x224446c)]='wstring_copy'
    # Offline host CRT adapters only. Native protocol/collection instructions
    # remain unchanged; callers must identify the actual external ABI.
    for address,kind in (host_imports or {}).items():
        if (type(address) is not int or BASE<=address<BASE+len(DATA)
                or kind not in ('alloc_stdcall','copy_checked','free_stdcall')):
            raise ValueError('Unsupported native host adapter')
        imports[address]=kind
    for page in {addr&~0xfff for addr in imports if not BASE<=addr<BASE+len(DATA)}:
        emu.mem_map(page,0x1000)
    def ret(uc,count=0,value=None):
        sp=uc.reg_read(UC_X86_REG_ESP);dest=read(sp)
        if value is not None:uc.reg_write(UC_X86_REG_EAX,value)
        uc.reg_write(UC_X86_REG_ESP,sp+4+count)
        uc.reg_write(UC_X86_REG_EIP,dest)
    def hook(uc,addr,size,user):
        sp=uc.reg_read(UC_X86_REG_ESP)
        if addr==stop:uc.emu_stop();return
        kind=imports.get(addr)
        if kind=='alloc':
            count=read(sp+4);ptr=heap[0];heap[0]+=(count+15)&~15;ret(uc,value=ptr)
        elif kind=='alloc_stdcall':
            count=read(sp+4);ptr=heap[0];heap[0]+=max(16,(count+15)&~15);ret(uc,4,ptr)
        elif kind=='copy_checked':
            dst,capacity,src,count=(read(sp+offset) for offset in (4,8,12,16))
            if count>capacity:raise ValueError('Native checked-copy capacity')
            if count:uc.mem_write(dst,bytes(uc.mem_read(src,count)))
            ret(uc,value=0)
        elif kind=='free_stdcall':ret(uc,8)
        elif kind=='free':ret(uc)
        elif kind in ('decrement','increment'):
            ptr=read(sp+4);value=(read(ptr)+(-1 if kind=='decrement' else 1))&0xffffffff;w(ptr,value);ret(uc,4,value)
        elif kind=='wstring_ctor':
            ptr=uc.reg_read(UC_X86_REG_ECX)
            uc.mem_write(ptr,bytes(28));w(ptr+24,7);ret(uc,value=ptr)
        elif kind=='wstring_copy':
            ptr=uc.reg_read(UC_X86_REG_ECX);src=read(sp+4)
            count=read(src+20);source=src+4 if read(src+24)<8 else read(src+4)
            encoded=bytes(uc.mem_read(source,count*2))
            uc.mem_write(ptr,bytes(28));w(ptr+20,count);w(ptr+24,7)
            if count<=7:uc.mem_write(ptr+4,encoded+b'\0\0')
            else:
                dest=heap[0];heap[0]+=(len(encoded)+17)&~15
                uc.mem_write(dest,encoded+b'\0\0');w(ptr+4,dest);w(ptr+24,count)
            ret(uc,4,ptr)
        elif kind in ('string_begin','string_end'):
            ptr=uc.reg_read(UC_X86_REG_ECX);result=read(sp+4)
            data_ptr=ptr+4 if read(ptr+24)<8 else read(ptr+4)
            if kind=='string_end':data_ptr+=read(ptr+20)*2
            w(result,ptr,data_ptr);ret(uc,4,result)
        elif addr==0x74a6d0:
            # Host adapter for STL iterator-based UTF16 string assignment only.
            # Original OctetsStream has already consumed the actual wire string.
            ptr=uc.reg_read(UC_X86_REG_ECX);begin,end=read(sp+20),read(sp+24)
            encoded=bytes(uc.mem_read(begin,end-begin));count=len(encoded)//2
            if count<=7:uc.mem_write(ptr+4,encoded+b'\0\0')
            else:
                dest=heap[0];heap[0]+=(len(encoded)+17)&~15
                uc.mem_write(dest,encoded+b'\0\0');w(ptr+4,dest);w(ptr+24,count)
            w(ptr+20,count);ret(uc,28,ptr)
        elif addr==0x19191c2:
            dst,src,count=read(sp+4),read(sp+8),read(sp+12)
            if count:uc.mem_write(dst,bytes(uc.mem_read(src,count)))
            ret(uc,value=dst)
        elif addr==0x1919184:ret(uc)
        elif addr==0x1919292:
            raise ValueError('Original codec rejected candidate')
    emu.hook_add(UC_HOOK_CODE,hook)
    w(stack,stop)
    emu.reg_write(UC_X86_REG_ECX,obj);emu.reg_write(UC_X86_REG_ESP,stack)

    w(stack,stop)
    emu.reg_write(UC_X86_REG_ECX,obj);emu.reg_write(UC_X86_REG_ESP,stack)
    emu.emu_start(constructor,stop,count=500000)
    assert emu.reg_read(UC_X86_REG_EIP)==stop
    # Some original protocol types only expose allocating factories, rather
    # than an out-of-line this constructor. Retain the actual returned object.
    if factory:obj=emu.reg_read(UC_X86_REG_EAX)
    for offset,raw in (fields or {}).items():
        emu.mem_write(obj+offset,raw)
    if payload is None:
        w(stack,stop,stream)
        emu.reg_write(UC_X86_REG_ECX,obj);emu.reg_write(UC_X86_REG_ESP,stack)
        emu.emu_start(serializer,stop,count=1000000)
        assert emu.reg_read(UC_X86_REG_EIP)==stop
        payload=bytes(emu.mem_read(buf,read(buf-8)))
    # Decode into a fresh, originally constructed object.
    target=obj+0x800
    w(stack,stop)
    emu.reg_write(UC_X86_REG_ECX,target);emu.reg_write(UC_X86_REG_ESP,stack)
    emu.emu_start(constructor,stop,count=500000)
    if factory:target=emu.reg_read(UC_X86_REG_EAX)
    emu.mem_write(buf,payload);w(buf-12,0x7000,len(payload),1);w(stream+8,0)
    w(stack,stop,stream)
    emu.reg_write(UC_X86_REG_ECX,target);emu.reg_write(UC_X86_REG_ESP,stack)
    try:
        emu.emu_start(decoder,stop,count=1000000)
    except ValueError:
        raise
    except Exception as error:
        raise RuntimeError(f'Original decoder failed at {emu.reg_read(UC_X86_REG_EIP):x}') from error
    assert emu.reg_read(UC_X86_REG_EIP)==stop and read(stream+8)==len(payload)
    if observer is not None:
        observer(emu,target)
    return payload,bytes(emu.mem_read(target,0x600))
