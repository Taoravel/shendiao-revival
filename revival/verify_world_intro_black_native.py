"""Offline execution of the original enter-world intro blackout chain.

Only host allocation/string/resource/device boundaries are adapted. No client,
GUI, server, network, or online memory is accessed.
"""
import json
import struct
from contextlib import redirect_stdout
from pathlib import Path
from native_inspect import BASE, DATA, u32, disasm
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_ESI, UC_X86_REG_ESP, UC_X86_REG_EIP

OUT = Path(__file__).parent / 'evidence'


class Replay:
    def __init__(self):
        self.e = Uc(UC_ARCH_X86, UC_MODE_32)
        self.e.mem_map(0, 4096)
        self.e.mem_map(BASE, (len(DATA)+4095)&~4095)
        self.e.mem_write(BASE, DATA)
        self.e.mem_map(0x5000000, 0x400000)
        self.scene, self.packet, self.engine, self.renderer = 0x5001000, 0x5002000, 0x5003000, 0x5004000
        self.evt, self.rvt, self.stack, self.stop = 0x5005000, 0x5006000, 0x5100000, 0x500f000
        self.resource = 0x5007000
        self.heap = 0x5200000
        self.calls = []
        self.w(0x2944564, self.scene)
        self.w(self.engine, self.evt)
        self.w(self.renderer, self.rvt)
        self.w(0x2945060, self.evt)
        for offset, address in ((0x50, 0x500f010), (0x5c, 0x500f020)):
            self.w(self.evt+offset, address)
        for offset, address in ((0xf4, 0x500f030), (0x34, 0x500f040), (0xf8, 0x500f050), (0x44, 0x500f060)):
            self.w(self.rvt+offset, address)
        self.imports = {u32(0x22443f0): 'string', u32(0x22443ec): 'string_free'}
        for p in {a&~4095 for a in self.imports if not BASE <= a < BASE+len(DATA)}:
            self.e.mem_map(p,4096)
        self.e.hook_add(UC_HOOK_CODE, self.hook)

    def r(self, a):
        return struct.unpack('<I', self.e.mem_read(a,4))[0]

    def w(self, a, *values):
        self.e.mem_write(a, struct.pack('<'+'I'*len(values), *values))

    def ret(self, count=0, value=0):
        sp=self.e.reg_read(UC_X86_REG_ESP)
        self.e.reg_write(UC_X86_REG_EAX,value)
        self.e.reg_write(UC_X86_REG_ESP,sp+4+count)
        self.e.reg_write(UC_X86_REG_EIP,self.r(sp))

    def hook(self, e, a, size, user):
        sp=e.reg_read(UC_X86_REG_ESP)
        if a==self.stop:
            e.emu_stop()
        elif a==0x83384c:
            e.emu_stop()
        elif a==0x1919178:
            ptr=self.heap;self.heap+=(self.r(sp+4)+15)&~15;self.ret(value=ptr)
        elif a in (0x191910c, 0x1919184):
            self.ret()
        elif a==0x5a6660:
            self.ret(value=self.engine)
        elif a==0x500f010:
            self.ret()
        elif a==0x500f020:
            self.ret(4,self.renderer)
        elif a==0x500f030:
            self.calls.append({'load_resource': '/artres/image/movie/movieblack.tga'})
            self.ret(4,self.resource)
        elif a==0x500f040:
            ptr=self.r(sp+4);self.w(ptr,1024,768);self.ret(4,ptr)
        elif a==0x500f050:
            self.calls.append({'draw_resource':self.r(sp+4),'rect':struct.unpack('<4f',e.mem_read(self.r(sp+8),16)), 'ARGB':hex(self.r(sp+12))})
            self.ret(12)
        elif a==0x500f060:
            self.calls.append({'release_resource':self.r(sp+4)});self.ret(4)
        elif a==0x11dc9d0:
            # Record the actual original caller's vector insertion argument.
            ptr=self.r(self.r(sp+4))
            self.calls.append({'register_scene_effect':ptr,'vector_this':e.reg_read(UC_X86_REG_ECX)})
            self.w(self.scene+0x390,0x5008000,0x5008004,0x5008010)
            self.w(0x5008000,ptr);self.ret(4)
        elif self.imports.get(a)=='string':
            p=self.r(sp+4);chars=[]
            while self.r16(p):chars.append(chr(self.r16(p)));p+=2
            assert ''.join(chars)=='/artres/image/movie/movieblack.tga',chars
            self.calls.append({'original_string_argument':''.join(chars)})
            self.ret(4,e.reg_read(UC_X86_REG_ECX))
        elif self.imports.get(a)=='string_free':
            self.ret()

    def r16(self,a):
        return struct.unpack('<H',self.e.mem_read(a,2))[0]

    def run(self, address, obj, *args, end=None):
        self.w(self.stack,self.stop,*args)
        self.e.reg_write(UC_X86_REG_ESP,self.stack)
        self.e.reg_write(UC_X86_REG_ECX,obj)
        self.e.emu_start(address,end or self.stop,count=100000)
        assert self.e.reg_read(UC_X86_REG_EIP) in (self.stop,0x83384c,end)


def enter(intro_value):
    r=Replay()
    r.e.mem_write(r.packet+0x48,struct.pack('<q',intro_value))
    r.e.reg_write(UC_X86_REG_ESI,r.packet)
    r.run(0x83380a,r.packet)
    created=r.r(r.scene+0x39c)
    assert bool(created)==(intro_value<=0)
    assert bytes(r.e.mem_read(0x2945438,1))==bytes([int(intro_value<=0)])
    result={'packet_intro_q64_at_48':intro_value,'intro_flag':int(intro_value<=0),'effect_created':bool(created),'calls':r.calls.copy()}
    if created:
        assert r.r(created)==0x229ef5c and r.r(created+8)==300000
        assert struct.unpack('<f',r.e.mem_read(created+0xc,4))[0]==1
        result.update(duration_ms=r.r(created+8),initial_alpha=1)
        r.calls.clear();r.run(0x11d3770,r.scene)
        assert r.calls==[{'draw_resource':r.resource,'rect':(0.,0.,1024.,768.),'ARGB':'0xffffffff'}]
        result['original_draw']=r.calls.copy()
        r.calls.clear();r.run(0x11d2a30,r.scene,0,299999)
        assert r.r(created+4)==299999 and r.r(created+0x10)==r.resource
        assert r.e.mem_read(created+0x15,1)==b'\0' and not r.calls
        r.run(0x11d2a30,r.scene,0,1)
        assert r.r(created+0x10)==0 and r.e.mem_read(created+0x15,1)==b'\1'
        assert r.r(r.scene+0x394)==r.r(r.scene+0x390)
        assert r.e.mem_read(0x2945438,1)==b'\1'
        result['expiry_at_300000']=r.calls.copy()
        result['intro_flag_after_timeout']=1
        r.calls.clear();r.run(0x11d3770,r.scene)
        assert not r.calls
        result['draw_after_expiry']=[]
    return result


def clear_explicitly():
    r=Replay();r.e.reg_write(UC_X86_REG_ESI,r.packet);r.run(0x83380a,r.packet)
    assert r.r(r.scene+0x39c)
    r.calls.clear();r.run(0x11d3a10,r.scene)
    assert r.r(r.scene+0x39c)==0
    assert r.r(r.scene+0x390)==r.r(r.scene+0x394)
    assert r.calls==[{'release_resource':r.resource}]
    return {'original_clear_11d3a10': True, 'cleared_scene_39c':True,'vector_empty':True,'calls':r.calls}


def cg_cleanup():
    r=Replay();r.e.reg_write(UC_X86_REG_ESI,r.packet);r.run(0x83380a,r.packet)
    assert r.r(r.scene+0x39c) and r.e.mem_read(0x2945438,1)==b'\1'
    r.calls.clear();r.run(0x12bc870,0)
    assert r.r(r.scene+0x39c)==0 and r.e.mem_read(0x2945438,1)==b'\0'
    assert r.r(r.scene+0x390)==r.r(r.scene+0x394)
    return {'original_CG_cleanup_function':'0x12bc870',
            'cleared_intro_lock_2945438':True,'cleared_scene_39c':True,'vector_empty':True,'calls':r.calls}


def experience_route():
    r=Replay();value=0x1234567887654321
    r.e.mem_write(r.packet+0xf8,struct.pack('<Q',value))
    r.e.reg_write(UC_X86_REG_ESI,r.packet)
    r.run(0x833ef3,0,end=0x833f0d)
    roleinfo=r.stack+0x24
    assert struct.unpack('<Q',r.e.mem_read(roleinfo+0x80,8))[0]==value
    manager=0x5009000
    r.e.reg_write(UC_X86_REG_ESI,manager)
    r.e.reg_write(UC_X86_REG_EAX,roleinfo)
    r.run(0x113b430,0,end=0x113b437)
    target=r.e.reg_read(UC_X86_REG_ECX)
    assert target==manager+0xf8
    from unicorn.x86_const import UC_X86_REG_EDI
    r.e.reg_write(UC_X86_REG_EDI,roleinfo)
    r.e.reg_write(UC_X86_REG_ESI,target)
    r.run(0x113ac4d,0,end=0x113ac6b)
    assert struct.unpack('<Q',r.e.mem_read(manager+0x178,8))[0]==value
    assert r.e.mem_read(r.packet+0x48,8)==b'\0'*8
    return {'native_spans':['0x833ef3..0x833f0d','0x113b430..0x113b437','0x113ac4d..0x113ac6b'],
            'packet_experience_offset':'0xf8','RoleInfo_offset':'0x80','RoleDataManager_offset':'0x178',
            'value':value,'packet_intro_offset_48_independent':True,
            'scope':'three original copy spans; not complete SEnterWorld processing'}


def asset():
    from inspect_client import ROOT
    from pfs import PfsArchive
    from PIL import Image
    import io,hashlib
    archive=PfsArchive(ROOT/'artres/image.pfs')
    raw=archive.read('movie/movieblack.tga')
    image=Image.open(io.BytesIO(raw));image.load()
    assert image.size==(1024,768) and image.mode=='RGBA'
    assert image.getextrema()==((0,0),(0,0),(0,0),(255,255))
    return {'original_asset':'artres/image.pfs:movie/movieblack.tga','crc_checked':True,
            'sha256':hashlib.sha256(raw).hexdigest(),'size':image.size,'mode':image.mode,
            'all_pixels_RGBA':[0,0,0,255]}


if __name__=='__main__':
    results=[asset()]+[enter(x) for x in (0,1,-1,2**32)]+[clear_explicitly(),cg_cleanup(),experience_route()]
    (OUT/'world-intro-black-native.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    with (OUT/'world-intro-black-native-disassembly.txt').open('w',encoding='utf-8') as stream:
        with redirect_stdout(stream):
            for a,n in ((0x83380a,66),(0x11df870,280),(0x12ba630,120),(0x12ba8f0,180),(0x12babd0,50),(0x11d3a10,31),(0x11d2a30,200),(0x11d3770,90),(0x12bc870,42),(0x12c304a,41),(0x833ef3,26),(0x113b430,12),(0x113ac4d,30),(0x11355b0,35)):
                print('\n',hex(a));disasm(a,n)
    print(json.dumps(results,indent=2))
