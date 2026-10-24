"""Offline first-party role protocol evidence and native empty-list verification."""
from pathlib import Path
import argparse
import hashlib
import json
import struct
import sys
sys.path.insert(0, 'D:/Downloads/LCJDTClient/LCJDTClient/revival/.deps')
from native_inspect import DATA, BASE, u32, disasm

OUT = Path(__file__).parent / 'evidence'
FUNCTIONS = {
    'role_list_marshal': (0xfc0090, 0xc2),
    'role_list_unmarshal': (0xfc0160, 0x105),
    'role_list_process': (0x1007df0, 0x1c2),
    'role_list_screen_dispatch': (0x1006700, 0x60),
    'role_info_marshal': (0xebfc20, 0x258),
    'role_info_defaults': (0xebf940, 0x98),
    'role_info_constraints': (0xec05a0, 0x22),
    'create_role_marshal': (0xe3fc80, 0xa0),
    'create_role_ui_send': (0x100986f, 0x6e),
    'create_role_color_choice': (0x100b240, 0x74),
    'create_role_error_process': (0x10063a0, 0xb2),
    'enter_world_marshal': (0x83f590, 0xee),
    'enter_world_state_marshal': (0xfe0940, 0x1a10),
}


def empty_role_list(last_role_id, flag=0, tail=0):
    return struct.pack('>QB', last_role_id, flag) + b'\0' + struct.pack('>i', tail)


def verify_native_empty_list():
    """Execute original fc0160 decoder, including original compact/list decoder.

    Only Windows security-cookie validation is bypassed; no codec is replaced.
    The sentinel list and stream object layout are initialized as native objects.
    """
    from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
    from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_ESP, UC_X86_REG_EIP
    emu = Uc(UC_ARCH_X86, UC_MODE_32)
    emu.mem_map(0, 0x1000)
    emu.mem_map(BASE, (len(DATA)+0xfff)&~0xfff)
    emu.mem_write(BASE, DATA)
    emu.mem_map(0x5000000, 0x200000)
    obj, stream, buf, head, stack, stop = 0x5001000,0x5002000,0x5003000,0x5004000,0x5100000,0x5005000
    payload = empty_role_list(0x1122334455667788,0,1)
    def w(addr,*values): emu.mem_write(addr,struct.pack('<'+'I'*len(values),*values))
    w(obj,0x228662c,0xc0002)
    w(obj+0x18,head)
    w(head,head,head)
    w(obj+0x1c,0)
    w(stream,0x224c100,buf,0)
    w(buf-12,len(payload),len(payload),1)
    emu.mem_write(buf,payload)
    w(stack,stop,stream)
    visited = set()
    def hook(uc,addr,size,user):
        visited.add(addr)
        if addr==stop: uc.emu_stop()
        if addr==0x1919184: # native cookie checker uses process-specific CRT state
            sp=uc.reg_read(UC_X86_REG_ESP)
            ret=struct.unpack('<I',uc.mem_read(sp,4))[0]
            uc.reg_write(UC_X86_REG_ESP,sp+4)
            uc.reg_write(UC_X86_REG_EIP,ret)
    emu.hook_add(UC_HOOK_CODE,hook)
    emu.reg_write(UC_X86_REG_ECX,obj)
    emu.reg_write(UC_X86_REG_ESP,stack)
    emu.emu_start(0xfc0160,stop,count=200000)
    read=lambda addr:struct.unpack('<I',emu.mem_read(addr,4))[0]
    result={'selected_role_id':struct.unpack('<Q',emu.mem_read(obj+8,8))[0],
            'flag':emu.mem_read(obj+0x10,1)[0], 'list_size':read(obj+0x1c),
            'tail':read(obj+0x20),'consumed':read(stream+8),
            'payload_hex':payload.hex(),'native_list_decoder_visited':0xfbfdd0 in visited,
            'completed':emu.reg_read(UC_X86_REG_EIP)==stop}
    assert result['completed'] and result['selected_role_id']==0x1122334455667788
    assert result['consumed']==14 and result['tail']==1 and result['list_size']==0
    return result


def native_default_world_payload(name='', role_id=1, school=12, shape=1010101, stats=None, scene=False):
    """Original constructor/serializer with selected positive scalar probes.

    This is a layout probe, not a promise that a world can load with zero stats.
    """
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
        elif kind=='free':ret(uc)
        elif kind in ('decrement','increment'):
            ptr=read(sp+4);value=(read(ptr)+(-1 if kind=='decrement' else 1))&0xffffffff;w(ptr,value);ret(uc,4,value)
        elif kind=='wstring_ctor':
            ptr=uc.reg_read(UC_X86_REG_ECX)
            uc.mem_write(ptr,bytes(28));w(ptr+24,7);ret(uc,value=ptr)
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
    emu.hook_add(UC_HOOK_CODE,hook)
    w(stack,stop)
    emu.reg_write(UC_X86_REG_ECX,obj);emu.reg_write(UC_X86_REG_ESP,stack)
    constructor=0xdac580 if scene else 0xfdfe90
    serializer=0xe50b00 if scene else 0xfe0940
    decoder=0xf74260 if scene else 0xfe2350
    emu.emu_start(constructor,stop,count=100000)
    assert emu.reg_read(UC_X86_REG_EIP)==stop
    if scene:
        emu.mem_write(obj+0x28,struct.pack('<hh',8480,6976))
        w(obj+0x30,516015);w(obj+0x38,1007,0)
    else:
        w(obj+8,role_id&0xffffffff,role_id>>32)
        w(obj+0x2c,1,school,shape)
        for offset,value in (stats or {}).items():w(obj+offset,value)
    string_offset=8 if scene else 0x10
    name_obj=obj+string_offset
    encoded_name=name.encode('utf-16le')
    name_chars=len(encoded_name)//2
    if name_chars<=7:
        emu.mem_write(name_obj+4,encoded_name+b'\0\0')
    else:
        name_ptr=heap[0];heap[0]+=(len(encoded_name)+17)&~15
        emu.mem_write(name_ptr,encoded_name+b'\0\0')
        w(name_obj+4,name_ptr);w(name_obj+24,name_chars)
    w(name_obj+20,name_chars)
    w(stack,stop,stream)
    emu.reg_write(UC_X86_REG_ECX,obj);emu.reg_write(UC_X86_REG_ESP,stack)
    try: emu.emu_start(serializer,stop,count=500000)
    except Exception as exc:
        raise RuntimeError(f'native serializer at {emu.reg_read(UC_X86_REG_EIP):x}; imports {imports}') from exc
    assert emu.reg_read(UC_X86_REG_EIP)==stop
    payload=bytes(emu.mem_read(buf,read(buf-8)))
    valid=None
    if not scene:
        w(stack,stop)
        emu.reg_write(UC_X86_REG_ECX,obj);emu.reg_write(UC_X86_REG_ESP,stack)
        emu.emu_start(0xfe43b0,stop,count=100000)
        valid=bool(emu.reg_read(UC_X86_REG_EAX)&0xff)
    decoded_obj=obj+0x600
    w(stack,stop)
    emu.reg_write(UC_X86_REG_ECX,decoded_obj);emu.reg_write(UC_X86_REG_ESP,stack)
    emu.emu_start(constructor,stop,count=100000)
    w(stream+8,0);w(stack,stop,stream)
    emu.reg_write(UC_X86_REG_ECX,decoded_obj);emu.reg_write(UC_X86_REG_ESP,stack)
    try:emu.emu_start(decoder,stop,count=500000)
    except Exception as exc:raise RuntimeError(f'decoder at {emu.reg_read(UC_X86_REG_EIP):x}; imports {imports}') from exc
    assert emu.reg_read(UC_X86_REG_EIP)==stop and read(stream+8)==len(payload)
    decoded_name_obj=decoded_obj+string_offset
    np=decoded_name_obj+4 if read(decoded_name_obj+24)<8 else read(decoded_name_obj+4)
    decoded_name=bytes(emu.mem_read(np,read(decoded_name_obj+20)*2)).decode('utf-16le')
    assert decoded_name==name
    if scene:
        decoded_fields={'x':struct.unpack('<h',emu.mem_read(decoded_obj+0x28,2))[0],
                        'y':struct.unpack('<h',emu.mem_read(decoded_obj+0x2a,2))[0],
                        'reason':read(decoded_obj+0x30),
                        'scene_id':struct.unpack('<Q',emu.mem_read(decoded_obj+0x38,8))[0]}
        assert decoded_fields=={'x':8480,'y':6976,'reason':516015,'scene_id':1007}
    else:
        decoded_fields={'role_id':struct.unpack('<Q',emu.mem_read(decoded_obj+8,8))[0],
                        'level':read(decoded_obj+0x2c),'school':read(decoded_obj+0x30),'shape':read(decoded_obj+0x34)}
        assert decoded_fields=={'role_id':role_id,'level':1,'school':school,'shape':shape}
        for offset,value in (stats or {}).items():assert read(decoded_obj+offset)==value
    prefix='scene' if scene else 'world'
    (OUT/f'{prefix}-named-probe.bin').write_bytes(payload)
    result={'bytes':len(payload),'hex':payload.hex(),'native_constraints_passed':valid,
            'role_id':role_id,'name':name,'level':1,'school':school,'shape':shape,
            'native_constructor_executed':True,
            'native_decoder_consumed':read(stream+8),'decoded_name':decoded_name,
            'decoded_fields':decoded_fields,
            'stats':stats or {},
            'scope':'original constructor/serializer/decoder; host STL string assignment adapter; not world load validation'}
    (OUT/f'{prefix}-named-probe.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--native-empty-list',action='store_true')
    p.add_argument('--world-layout-probe',action='store_true')
    p.add_argument('--scene-layout-probe',action='store_true')
    p.add_argument('--experimental-vitals',type=int)
    p.add_argument('--name',default='')
    p.add_argument('--role-id',type=int,default=1)
    p.add_argument('--school',type=int,default=12)
    p.add_argument('--shape',type=int,default=1010101)
    p.add_argument('--disasm',choices=FUNCTIONS)
    args=p.parse_args()
    if args.disasm:
        disasm(*FUNCTIONS[args.disasm])
    if args.native_empty_list:
        result=verify_native_empty_list()
        result['image_sha256']=hashlib.sha256(DATA).hexdigest()
        (OUT/'role-native-verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        print(json.dumps(result,indent=2))
    if args.world_layout_probe or args.scene_layout_probe:
        stats={off:args.experimental_vitals for off in (0x48,0x4c,0x50,0x54,0x58)} if args.experimental_vitals is not None else {}
        print(json.dumps(native_default_world_payload(args.name,args.role_id,args.school,args.shape,stats,args.scene_layout_probe),indent=2))


if __name__=='__main__': main()
