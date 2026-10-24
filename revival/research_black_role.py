"""Read-only, narrowly scoped live player/appearance state probes."""
import argparse
import ctypes as C
from ctypes import wintypes as W
import json
from pathlib import Path
import struct
from native_inspect import DATA,BASE,disasm,u32

OUT=Path(__file__).parent/'evidence'

class Reader:
    def __init__(self,pid):
        self.k=C.WinDLL('kernel32',use_last_error=True)
        self.k.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];self.k.OpenProcess.restype=W.HANDLE
        self.k.ReadProcessMemory.argtypes=[W.HANDLE,C.c_void_p,C.c_void_p,C.c_size_t,C.POINTER(C.c_size_t)]
        self.k.CloseHandle.argtypes=[W.HANDLE]
        self.h=self.k.OpenProcess(0x410,False,pid)
        if not self.h:raise C.WinError(C.get_last_error())
    def read(self,address,length):
        buf=C.create_string_buffer(length);n=C.c_size_t()
        if not self.k.ReadProcessMemory(self.h,C.c_void_p(address),buf,length,C.byref(n)):return None
        return buf.raw[:n.value]
    def word(self,a):
        b=self.read(a,4)
        return struct.unpack('<I',b)[0] if b and len(b)==4 else None
    def close(self):self.k.CloseHandle(self.h)

def typename(vtable):
    try:
        col=u32(vtable-4);td=u32(col+12);at=td+8-BASE
        return DATA[at:DATA.index(b'\0',at)].decode('ascii')
    except Exception:return None

def probe(pid):
    r=Reader(pid)
    try:
        objects={}
        for name,address in [('main_actor',0x294454c),('player_data',0x2944550),('role_manager',0x2944564),('scene_manager',0x2944798),('activity',0x29455ac)]:
            ptr=r.word(address);vtable=r.word(ptr) if ptr else None
            row={'global':hex(address),'pointer':hex(ptr) if ptr is not None else None,'vtable':hex(vtable) if vtable is not None else None,'native_type':typename(vtable) if vtable else None}
            if name=='main_actor' and ptr:
                row['render_object_at_44']=hex(r.word(ptr+0x44) or 0)
            if name=='role_manager' and ptr:
                row['scene_state_at_364']=r.word(ptr+0x364)
            objects[name]=row
        result={'pid':pid,'method':'ReadProcessMemory only, fixed known player globals; no process writes or arbitrary strings',
                'objects':objects,
                'flags':{hex(a):(r.read(a,1).hex() if r.read(a,1) else None) for a in [0x2945080,0x2945438,0x294524d]},
                'scope':'native actor/data object presence only; visual black-screen diagnosis requires renderer/scene probes'}
        (OUT/'black-role-state.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        print(json.dumps(result,indent=2))
    finally:r.close()

def main():
    p=argparse.ArgumentParser();p.add_argument('--pid',type=int);a=p.parse_args()
    if a.pid:probe(a.pid)

if __name__=='__main__':main()
