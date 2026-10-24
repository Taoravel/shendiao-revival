"""Read-only evidence probe for the original client's black world symptom."""
import argparse
import ctypes as C
from ctypes import wintypes as W
import json
from pathlib import Path
import struct
import time

OUT=Path(__file__).parent/'evidence'


class ProcessReader:
    def __init__(self,pid):
        self.kernel=C.WinDLL('kernel32',use_last_error=True)
        self.kernel.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD]
        self.kernel.OpenProcess.restype=W.HANDLE
        self.kernel.ReadProcessMemory.argtypes=[W.HANDLE,C.c_void_p,C.c_void_p,C.c_size_t,C.POINTER(C.c_size_t)]
        self.kernel.CloseHandle.argtypes=[W.HANDLE]
        self.handle=self.kernel.OpenProcess(0x410,False,pid)
        if not self.handle:raise C.WinError(C.get_last_error())
    def read(self,addr,size):
        buf=C.create_string_buffer(size);got=C.c_size_t()
        if not self.kernel.ReadProcessMemory(self.handle,C.c_void_p(addr),buf,size,C.byref(got)) or got.value!=size:
            raise OSError(f'unreadable address {addr:#x} size {size}')
        return buf.raw
    def u32(self,addr):return struct.unpack('<I',self.read(addr,4))[0]
    def string(self,addr):
        count=self.u32(addr+20);capacity=self.u32(addr+24)
        if count>1024:return {'invalid_count':count,'capacity':capacity}
        ptr=addr+4 if capacity<8 else self.u32(addr+4)
        return self.read(ptr,count*2).decode('utf-16le',errors='replace') if count else ''
    def type_name(self,obj):
        table=self.u32(obj);locator=self.u32(table-4);desc=self.u32(locator+12)
        return self.read(desc+8,180).split(b'\0')[0].decode('ascii',errors='replace')
    def close(self):self.kernel.CloseHandle(self.handle)


def snapshot(pid):
    r=ProcessReader(pid)
    try:
        globals_={name:r.u32(addr) for name,addr in {'scene_manager':0x2944564,'main_role':0x294454c,
                'role_manager':0x2944550,'network_manager':0x2945060,'frame_context':0x2944554}.items()}
        result={'pid':pid,'captured_unix':time.time(),'access':'PROCESS_QUERY_INFORMATION|PROCESS_VM_READ',
                'globals':{key:hex(value) for key,value in globals_.items()},
                'enter_world_skip_byte':r.read(0x2945080,1)[0]}
        for name in ('scene_manager','main_role','role_manager'):
            ptr=globals_[name]
            if not ptr:continue
            info={'type':r.type_name(ptr),'vtable':hex(r.u32(ptr))}
            if name=='scene_manager':
                offsets=(0x30,0x34,0x38,0x58,0x110,0x1ac,0x288,0x28c,0x308,0x32c,0x335,0x338,0x33c,0x378)
                info['words']={hex(off):r.u32(ptr+off) for off in offsets}
                info['scene_label']=r.string(ptr+0x3c)
                info['map_resdir']=r.string(ptr+0x168)
            elif name=='main_role':
                info['words']={hex(off):r.u32(ptr+off) for off in (0x30,0x34,0x38,0x2c0,0x2c4,0x2c8,0x2cc,0x330,0x334,0x358,0x35c,0x398,0x39c)}
                info['methods']={hex(off):hex(r.u32(r.u32(ptr)+off)) for off in (0x30,0xd0,0xd4,0x184)}
            result[name]=info
        return result
    finally:r.close()


def main():
    p=argparse.ArgumentParser();p.add_argument('--pid',type=int,required=True)
    args=p.parse_args();result=snapshot(args.pid)
    target=OUT/f'black-scene-state-{args.pid}.json'
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=True,indent=2))


if __name__=='__main__':main()
