"""Exclusive NPC direction codec/selection/actor-vector research, offline."""
import hashlib
import json
import struct
from pathlib import Path
from bxml import decode
from inspect_client import ROOT
from pfs import PfsArchive
from native_inspect import DATA
from native_gameplay_probe import probe
from world_entity_protocol import NpcBasic,npc_basic
from verify_world_intro_dispatch_native import IntroReplay
from unicorn.x86_const import (UC_X86_REG_EAX,UC_X86_REG_EBX,UC_X86_REG_ECX,UC_X86_REG_EDI,
    UC_X86_REG_ESI,UC_X86_REG_ESP,UC_X86_REG_EIP)


class Direction(IntroReplay):
    npc, actor, path, node = 0x5500000,0x5501000,0x5502000,0x5503000
    rows_address=0x5504000

    def __init__(self, rows):
        super().__init__(b'\xff\xfe',{'id':'2004','Name':'','Patn':''})
        self.rows=rows;self.attr_reads=[];self.selected=[];self.paths=[]
        self.w(self.npc,0x22985e4)
        self.w(self.npc+0x44,self.actor);self.w(self.npc+0x48,self.actor)
        self.w(self.actor,0x2462544);self.w(self.actor+0x1a8,self.path)
        self.uc.mem_write(self.npc+0x98,b'\1')
        self.set_ws(self.scene+0x168,'map_1002_dashengguan')
        self.halt=set()
        self.uc.mem_write(self.stop+0x800,b'\xd9\xfa\xc3') # CRT sqrt adapter

    def hook(self,e,a,size,user):
        sp=e.reg_read(UC_X86_REG_ESP)
        if a in self.halt:e.emu_stop()
        elif a==0x19196a4:e.reg_write(UC_X86_REG_EIP,self.stop+0x800)
        elif a==0x11c6030:
            self.paths.append(self.ws(sp+4))
            vec=self.r(sp+36)
            self.w(vec,0,self.rows_address,self.rows_address+8*len(self.rows),
                   self.rows_address+8*len(self.rows))
            self.ret(36,1)
        elif a==0x409ce0:
            row=(e.reg_read(UC_X86_REG_ECX)-self.rows_address)//8
            field=self.ws(self.r(sp+4))
            self.attr_reads.append({'row':row,'field':field})
            self.ret(8,int(self.rows[row].get(field,0)))
        elif a in (0x40ef60,0x40a380,0x40a7d0):
            self.ret() # XML document/vector ownership boundary
        elif a==0x11f5b00:
            self.selected.append(self.r(sp+4)) # preserve actual original setter
        else:super().hook(e,a,size,user)

    def run(self,direction,config_id=11206,key=1,position=(1286,3455)):
        bean=NpcBasic(key,config_id,'',*position,field_48=direction)
        wire,decoded=probe(0xfc71e0,0xfc6f70,0xfc73a0,fields={
            8:struct.pack('<q',key),0x10:struct.pack('<i',config_id),
            0x34:struct.pack('<hh',bean.x,bean.y),0x48:struct.pack('<i',direction)})
        assert wire==npc_basic(bean)
        assert wire[26:30]==struct.pack('>i',direction) # this fixture uses empty name
        assert struct.unpack_from('<i',decoded,0x48)[0]==direction
        # Original handler slice: list node embeds NpcBasic at +8.
        self.uc.mem_write(self.node+8,decoded[:0x64])
        self.w(0x550f004,0)
        self.uc.reg_write(UC_X86_REG_ESI,self.node)
        self.uc.reg_write(UC_X86_REG_EDI,0x550f000)
        self.uc.reg_write(UC_X86_REG_ESP,self.stack)
        self.uc.emu_start(0x11e71be,0x11e71cb,count=100)
        info=self.stack+0xbc
        assert self.r(info+0x20)==direction
        self.w(info+8,config_id)
        self.set_ws(info+0x24,'')
        self.execute(0x11fd140,ecx=self.npc+0x100,args=(info,))
        assert self.r(self.npc+0x120)==direction
        self.halt={0x120224c}
        self.uc.reg_write(UC_X86_REG_ESI,self.npc)
        self.uc.reg_write(UC_X86_REG_ESP,self.stack)
        self.uc.emu_start(0x12020e0,self.stop,count=200000)
        assert self.uc.reg_read(UC_X86_REG_EIP)==0x120224c
        vector=struct.unpack('<fff',self.uc.mem_read(self.path+0x10,12))
        assert len(self.selected)==1
        expected=((0.,-1.,0.),(1.,-1.,0.),(1.,0.,0.),(1.,1.,0.),
                  (0.,1.,0.),(-1.,1.,0.),(-1.,0.,0.),(-1.,-1.,0.))
        assert vector==expected[self.selected[0]]
        return {'key':key,'config_id':config_id,'position':position,'field_48':direction,'wire_hex':wire.hex(),
            'copied_120':self.r(self.npc+0x120),'native_selected':self.selected,
            'native_actor_vector':vector,'xml_paths':self.paths,'attribute_reads':self.attr_reads,
            'scope':'original codec, handler slice, NpcInfo copier, +98=1 direction selection, original actor vector setter'}


def check():
    cases=[]
    for direction in range(1,8):
        r=Direction([{'id':'11206','dir':'7'}]);out=r.run(direction)
        assert out['native_selected']==[direction] and not out['xml_paths']
        cases.append({'case':'nonzero_wire_bypasses_local_dir',**out})
    for fallback in range(8):
        r=Direction([{'id':'11206','dir':str(fallback)}]);out=r.run(0)
        assert out['native_selected']==[fallback if fallback in (1,3,5,7) else 4]
        cases.append({'case':'zero_wire_original_local_dir_selection',**out})
    archive=PfsArchive(ROOT/'artres/map.pfs')
    entry='map_1002_dashengguan/npc.xml';raw=archive.read(entry)
    rows=[dict(x.attrib) for x in decode(raw)]
    matched=[(i+1,row) for i,row in enumerate(rows) if row['id']=='11206']
    assert [(i,int(x['dir'])) for i,x in matched]==[(54,7),(55,1)]
    for placement,row in matched:
        for wire_dir in (0,int(row['dir'])):
            r=Direction(rows);out=r.run(wire_dir,key=(1002<<32)|placement,
                position=(int(row['posx']),int(row['posy'])))
            assert out['native_selected']==[wire_dir or 7]
            cases.append({'case':'fresh_same_config_distinct_placement',
                'placement':placement,'original_row':row,**out})
    return {'all_passed':True,'case_count':len(cases),'cases':cases,
        'image_sha256':hashlib.sha256(DATA).hexdigest(),
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'source':{'entry':entry,'sha256':hashlib.sha256(raw).hexdigest()},
        'source_hashes':{name:hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
            for name in ('world_entity_protocol.py','world_npcs.py','native_gameplay_probe.py',
                         'verify_world_intro_dispatch_native.py')},
        'adapters':['IntroReplay CRT/wstring adapters; x87 fsqrt replaces external CRT sqrt import',
            'XML load supplies original PFS rows; XML attribute ABI lookup is host, iterator/id-match/dir choice original',
            'XML document/vector destructor boundary'],
        'not_proven':['entire SAddUserScreen Process','full CNpc/model construction',
            'all shape/actor flag branches','visual GPU orientation','server direction policy']}


if __name__=='__main__':print(json.dumps(check(),ensure_ascii=False,indent=2))
