"""Original Scene NPC ordered-index registration/query/removal, offline only."""
import hashlib
import json
import struct
from pathlib import Path

from native_inspect import BASE, DATA
from verify_world_native_pathfinding import NativePath
from research_world_npc_approach_motion import Motion
from pfs import PfsArchive
from inspect_client import ROOT
from world_grids import maze_grid
from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_EDX, UC_X86_REG_EBX,
    UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_ESP, UC_X86_REG_EIP)


def call(m, address, args=(), *, ecx=0):
    if isinstance(m, NativePath):
        m.execute(address, args=args, ecx=ecx)
    else:
        m.call(address, args, ecx=ecx)
    return m.uc.reg_read(UC_X86_REG_EAX)


class Index:
    """Pure original container seam; entities are explicit fixture inputs."""
    def __init__(self, machine, scene):
        self.m, self.scene = machine, scene
        self.index = scene + 0x68
        call(machine, 0x11d8b40, ecx=self.index)

    def read(self, p):
        return struct.unpack('<I',self.m.uc.mem_read(p,4))[0]

    def write(self, p, *values):
        self.m.w(p,*values)

    def entity(self, key, template, *, visible=1, active=1):
        entity = self.m.alloc(1024)
        self.write(entity,0x22985e4)
        call(self.m,0x1174ee0,(key&0xffffffff,key>>32),ecx=entity)
        self.write(entity+0x150,template)
        self.m.uc.mem_write(entity+0x18,bytes([visible]))
        self.m.uc.mem_write(entity+0x148,bytes([active]))
        return entity

    def register(self, key, entity):
        info = self.m.alloc(16)
        self.write(info,key&0xffffffff,key>>32)
        self.write(self.m.stack,self.m.stop)
        for reg,value in ((UC_X86_REG_ESP,self.m.stack),(UC_X86_REG_ESI,info),
                (UC_X86_REG_EDI,entity),(UC_X86_REG_EBX,self.scene)):
            self.m.uc.reg_write(reg,value)
        # Actual successful-initialization registration slice, including the
        # original map operator[] and native pointer store. No host tree nodes.
        self.m.uc.emu_start(0x11d9f25,0x11d9f30,count=100000)
        assert self.m.uc.reg_read(UC_X86_REG_EIP)==0x11d9f30

    def by_template(self, template):
        return call(self.m,0x11d1870,(template,),ecx=self.scene)

    def by_key(self, key):
        return call(self.m,0x11d5260,(key&0xffffffff,key>>32),ecx=self.scene)

    def key(self, entity):
        call(self.m,0x1174ed0,ecx=entity)
        return self.m.uc.reg_read(UC_X86_REG_EAX)|(self.m.uc.reg_read(UC_X86_REG_EDX)<<32)

    def ordered(self):
        head=self.read(self.index+4)
        node=self.read(head)
        iterator=self.m.alloc(8)
        result=[]
        while node!=head:
            assert len(result)<32
            result.append({'key':self.read(node+0x10)|(self.read(node+0x14)<<32),
                'entity':hex(self.read(node+0x18)),
                'template':self.read(self.read(node+0x18)+0x150)})
            self.write(iterator,self.index,node)
            call(self.m,0x11c79d0,ecx=iterator)
            node=self.read(iterator+4)
        assert len(result)==self.read(self.index+8)
        return result

    def remove(self,key):
        argument,output=self.m.alloc(8),self.m.alloc(8)
        self.write(argument,key&0xffffffff,key>>32)
        call(self.m,0x11d42d0,(output,argument),ecx=self.index)
        node=self.read(output+4)
        if node==self.read(self.index+4):
            return False
        call(self.m,0x11cf1f0,(output,self.index,node),ecx=self.index)
        return True


class NaturalLookup(Motion):
    def __init__(self,*args,npc_key=0x5060708010203040,duplicate_key=None,**kwargs):
        if (type(npc_key) is not int or not 0<=npc_key<1<<63 or
                (duplicate_key is not None and (type(duplicate_key) is not int or
                    not 0<=duplicate_key<1<<63 or duplicate_key==npc_key))):
            raise ValueError('Distinct nonnegative signed64 NPC keys required')
        self.real_lookup_entries=[]
        super().__init__(*args,**kwargs)
        self.npc_key=npc_key
        # Original entity key setter runs BEFORE original index registration.
        call(self,0x1174ee0,(npc_key&0xffffffff,npc_key>>32),ecx=self.npc)
        self.original_index=Index(self,self.scene)
        self.original_index.register(npc_key,self.npc)
        self.expected_key=npc_key if duplicate_key is None else min(npc_key,duplicate_key)
        if duplicate_key is not None:
            other=self.alloc(1024)
            self.uc.mem_write(other,bytes(self.uc.mem_read(self.npc,1024)))
            call(self,0x1174ee0,(duplicate_key&0xffffffff,duplicate_key>>32),ecx=other)
            self.original_index.register(duplicate_key,other)

    def hook(self,emu,address,size,user):
        if address in (0x11d1870,0x11d5260):
            sp=emu.reg_read(UC_X86_REG_ESP)
            self.real_lookup_entries.append({'entry':hex(address),'return':hex(self.read(sp)),
                'arguments':[self.read(sp+4),self.read(sp+8)]})
            return  # Execute original body, bypass inherited lookup adapters.
        super().hook(emu,address,size,user)


def main():
    root=Path(__file__).resolve().parent
    m=NativePath(1,1,b'\0')
    first,second=Index(m,0x5500000),Index(m,0x5501000)
    rows=[]
    assert first.by_key(1)==first.by_template(10498)==0
    rows.append({'case':'empty','ordered':first.ordered()})
    high,low=0x200000001,1
    a=first.entity(high,10498)
    b=first.entity(low,10498,visible=0,active=0)
    first.register(high,a);first.register(low,b)
    assert first.by_template(10498)==b
    assert first.by_key(high)==a and first.by_key(low)==b
    rows.append({'case':'duplicate_template_high_inserted_first_invisible_low_is_selected',
        'ordered':first.ordered(),'selected_key':first.key(first.by_template(10498))})
    assert second.by_template(10498)==second.by_key(low)==0
    c=second.entity(low,10014)
    second.register(low,c)
    assert second.by_key(low)==c and first.by_key(low)==b
    rows.append({'case':'scene_isolation_same_key_different_entity',
        'first':hex(first.by_key(low)),'second':hex(second.by_key(low))})
    replacement=first.entity(low,10498)
    first.register(low,replacement)
    assert first.by_key(low)==replacement and len(first.ordered())==2
    rows.append({'case':'same_key_registration_replaces_pointer','ordered':first.ordered()})
    assert first.remove(low) and not first.remove(low)
    assert first.by_key(low)==0 and first.by_template(10498)==a
    assert second.by_key(low)==c
    rows.append({'case':'remove_first_duplicate_then_other_selected','ordered':first.ordered()})
    mixed=Index(m,0x5502000)
    keys=[0x100000000,0xffffffffffffffff,0x8000000000000000,0xffffffff,0,0x7fffffffffffffff,1]
    pointers={}
    for key in keys:
        entity=mixed.entity(key,10498)
        mixed.register(key,entity);pointers[key]=entity
    expected=sorted(keys,key=lambda n:n-(1<<64) if n>>63 else n)
    assert [v['key'] for v in mixed.ordered()]==expected
    assert all(mixed.by_key(key)==entity for key,entity in pointers.items())
    assert mixed.by_key(0x100000001)==0
    assert mixed.key(mixed.by_template(10498))==0x8000000000000000
    rows.append({'case':'signed64_order_and_exact_full_key_queries','ordered':mixed.ordered(),
        'expected_signed_order':expected,'wire_scope':'negative keys are container-only; not CVisit wire'})
    for key in expected:
        assert mixed.remove(key) and mixed.by_key(key)==0
    assert mixed.by_template(10498)==0 and mixed.ordered()==[]
    rows.append({'case':'remove_all_then_empty','ordered':mixed.ordered()})
    archive=PfsArchive(ROOT/'artres/map.pfs')
    names=('map_1006_jiaxing/maze.dat','map_1006_jiaxing/map.rmp')
    raw=[archive.read(name) for name in names]
    motion=NaturalLookup(maze_grid(raw[0]),struct.unpack_from('<II',raw[1],8),1,0,
        duplicate_key=0x0102030410203040)
    initial=motion.navigate()
    assert initial['messages']==1
    motion.call(0x6529b0,(0x3f800000,),ecx=motion.actor)
    ticks=[]
    for now,delta in ((2000,1000),(3000,1000)):
        motion.now=now
        ticks.append(motion.actor_tick(now,delta))
    visits=[msg for msg in motion.messages if msg['kind']==0xc2329]
    assert len(visits)==1 and visits[0]['npc_key']==motion.expected_key
    assert not any(e.get('adapter')=='scene_NPC_template_lookup' for e in motion.navigation_events)
    assert ticks[-1]['future_engine']==ticks[-1]['future_character']==[]
    assert motion.read(motion.role+0x314)==0
    # Separate consumer seam: explicit nonzero metadata, no arrival claim.
    # It selects the HIGH key exactly rather than the template's first LOW key.
    motion.w(motion.role+0x314,10498,0x10203040,0x50607080)
    motion.call(0x12172f0,ecx=motion.role)
    exact_visits=[msg for msg in motion.messages if msg['kind']==0xc2329]
    assert [msg['npc_key'] for msg in exact_visits]==[motion.expected_key,0x5060708010203040]
    assert motion.read(motion.role+0x314)==motion.read(motion.role+0x318)==motion.read(motion.role+0x31c)==0
    assert bytes(motion.uc.mem_read(motion.maze_cells,len(raw[0])-12))==raw[0][12:]
    requested_key=(1006<<32)|13
    keyed=NaturalLookup(maze_grid(raw[0]),struct.unpack_from('<II',raw[1],8),1,0,npc_key=requested_key)
    assert keyed.original_index.by_key(requested_key)==keyed.npc
    assert keyed.original_index.by_template(10498)==keyed.npc
    assert keyed.original_index.key(keyed.npc)==requested_key
    rows.append({'case':'public_constructor_key_precedes_registration','npc_key':requested_key,
        'ordered':keyed.original_index.ordered(),'scope':'constructor/real lookup only, not second motion'})
    result={'all_passed':True,'image_sha256':hashlib.sha256(DATA).hexdigest(),
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'container_cases':rows,
        'dependency_scripts':[{'path':name,'sha256':hashlib.sha256((root/name).read_bytes()).hexdigest()}
            for name in ('research_world_npc_approach_motion.py','verify_world_native_pathfinding.py')],
        'natural_motion':{'initial':initial,'ticks':ticks,'original_lookup_entries':motion.real_lookup_entries,
            'messages':motion.messages,'scope':'natural public navigation through arrival for first Visit; second Visit is separate explicit nonzero-metadata consumer seam, not another arrival',
            'registered_keys':[motion.expected_key,0x5060708010203040],
            'maze_unchanged':bytes(motion.uc.mem_read(motion.maze_cells,len(raw[0])-12))==raw[0][12:]},
        'sources':[{'path':name,'sha256':hashlib.sha256(b).hexdigest(),'CRC_checked':True} for name,b in zip(names,raw)],
        'instructions':[{'address':hex(a),'bytes_hex':DATA[a-BASE:a-BASE+n].hex()}
            for a,n in ((0x11d1870,0x78),(0x11d5260,0x5e),(0x11d8b40,0xac),
                (0x11d42d0,0x67),(0x11cc0a0,0x3b),(0x11d9f14,0x21),
                (0x11cf1f0,0xb0),(0x12173a1,0x9d))]}
    out=root/'evidence/world-scene-npc-lookup.json'
    out.write_text(json.dumps(result,indent=2),encoding='utf8')
    print(json.dumps({'all_passed':True,'container_cases':len(rows),'result':str(out)}))


if __name__=='__main__':
    main()
