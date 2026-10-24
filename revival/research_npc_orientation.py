"""Original NPC direction range and remaining common model branches, offline."""
from collections import Counter,defaultdict
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import struct

from bxml import decode
from inspect_client import ROOT,catalog_rows
from pfs import PfsArchive
from native_inspect import BASE,DATA,disasm,u32
from native_gameplay_probe import probe
from world_entity_protocol import NpcBasic,npc_basic
from verify_world_npc_direction_native import check as old_direction_check
from verify_world_npc_shape_direction_native import ShapeDirection,check as old_shape_check
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_ESP,UC_X86_REG_EIP

HERE=Path(__file__).resolve().parent
HISTORY=('verify_world_npc_direction_native.py','verify_world_npc_shape_direction_native.py',
    'evidence/WORLD_NPC_DIRECTION_NATIVE.md','evidence/WORLD_NPC_SHAPE_DIRECTION_NATIVE.md')
BLOCKS=((0x11e71be,0x10),(0x11fd140,0x70),(0x12020e0,0x16c),(0x11f5b00,0x30),
    (0x6526e0,0xa),(0x652750,0x26),(0x651700,0xf0),(0x11db690,0x1c0),
    (0x11df645,0x154),(0x11fc5d3,0x23),(0x11fc91f,0xb))


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


class Orientation(ShapeDirection):
    def __init__(self,rows,config,shape,resdir,capability=0,random_value=0):
        super().__init__(rows,config,shape)
        self.set_ws(self.scene+0x168,resdir)
        self.capability=capability;self.random_value=random_value;self.cap_reads=[];self.random_calls=0
        self.rand_import=u32(0x22448cc)
        if not any(a<=self.rand_import<=b for a,b,_ in self.uc.mem_regions()):
            self.uc.mem_map(self.rand_import&~4095,4096)

    def hook(self,e,a,size,user):
        if a==self.rand_import:
            self.random_calls+=1;self.ret(value=self.random_value)
        elif a==0x6526e9:
            self.cap_reads.append(e.reg_read(UC_X86_REG_EAX)&255)
        else:super().hook(e,a,size,user)

    def pipeline(self,direction,key,position):
        derived=self.derive(255)
        self.uc.mem_write(self.path+0x47,bytes([self.capability]))
        self.uc.mem_write(self.path+0x10,struct.pack('<fff',9.,10.,11.))
        ident=int(self.config['id'])
        wire,decoded=probe(0xfc71e0,0xfc6f70,0xfc73a0,fields={
            8:struct.pack('<q',key),0x10:struct.pack('<i',ident),
            0x34:struct.pack('<hh',*position),0x48:struct.pack('<i',direction)})
        assert wire==npc_basic(NpcBasic(key,ident,'',*position,field_48=direction))
        self.uc.mem_write(self.node+8,decoded[:0x64]);self.w(0x550f004,0)
        self.uc.reg_write(UC_X86_REG_ESI,self.node);self.uc.reg_write(UC_X86_REG_EDI,0x550f000)
        self.uc.reg_write(UC_X86_REG_ESP,self.stack)
        self.uc.emu_start(0x11e71be,0x11e71cb,count=100)
        info=self.stack+0xbc
        assert self.r(info+0x20)==direction&0xffffffff
        self.w(info+8,ident);self.set_ws(info+0x24,'')
        self.execute(0x11fd140,ecx=self.npc+0x100,args=(info,))
        assert self.r(self.npc+0x120)==direction&0xffffffff
        self.w(self.stack+0x14,int(self.shape['id']))
        self.halt={0x120224c};self.uc.reg_write(UC_X86_REG_ESI,self.npc)
        self.uc.reg_write(UC_X86_REG_ESP,self.stack)
        self.uc.emu_start(0x12020e0,self.stop,count=200000)
        assert self.uc.reg_read(UC_X86_REG_EIP)==0x120224c
        return dict(config_id=ident,shape_id=int(self.shape['id']),original_shape_dir=int(self.shape['dir']),
            native_shape_flag=derived,wire_field_48=direction,key=key,position=position,
            wire_hex=wire.hex(),native_selected=list(self.selected),
            native_actor_vector=struct.unpack('<fff',self.uc.mem_read(self.path+0x10,12)),
            native_capability_getter_values=self.cap_reads,engine_capability_fixture=self.capability,
            external_rand_fixture=self.random_value,external_rand_calls=self.random_calls,
            original_xml_paths=self.paths,original_xml_attribute_reads=self.attr_reads,
            final_copied_120=self.r(self.npc+0x120))


def main():
    historical={name:sha(HERE/name) for name in HISTORY}
    production={name:sha(HERE/name) for name in ('world_npcs.py','npc_lifecycle.py','world_entity_protocol.py')}
    assert historical[HISTORY[0]]=='1580ec34fe3c363b41077af71f45334b8d0d75c547ee7ff2ea5ae1aa178582bc'
    assert historical[HISTORY[1]]=='893aecd8ce515b46a06fbfc335691283aba1337dcf72f395ba812a9b9a542384'
    config=PfsArchive(ROOT/'artres/config.pfs');maps=PfsArchive(ROOT/'artres/map.pfs')
    sources=[];tables={}
    for short in ('cnpcconfig','cnpcshape','cmapconfig'):
        prefix='npc' if short!='cmapconfig' else 'map'
        member=f'autoconfig/knight.gsp.{prefix}.{short}.xml';raw=config.read(member)
        rows=catalog_rows(decode(raw));saved=json.loads((HERE/f'catalogs/knight.gsp.{prefix}.{short}.json').read_text(encoding='utf8'))
        assert [(r['attributes'],r['lists']) for r in rows]==[(r['attributes'],r['lists']) for r in saved]
        tables[short]={int(r['attributes']['id']):r['attributes'] for r in rows}
        sources.append(dict(archive='config.pfs',member=member,length=len(raw),crc32=config.entries[member].crc,sha256=hashlib.sha256(raw).hexdigest()))
    world=json.loads((HERE/'catalogs/world.json').read_text(encoding='utf8'))
    paths={name.casefold():name for name in maps.entries};original={};distribution=Counter();zeros=[];duplicate_groups=[]
    for item in world:
        mid=int(item['attributes']['id']);resdir=tables['cmapconfig'][mid]['resdir']
        member=paths.get((resdir+'/npc.xml').casefold())
        if member is None:rows=[]
        else:
            raw=maps.read(member);rows=[dict(n.attrib) for n in decode(raw)]
            sources.append(dict(archive='map.pfs',map_id=mid,member=member,length=len(raw),crc32=maps.entries[member].crc,sha256=hashlib.sha256(raw).hexdigest()))
        assert rows==[{k:v for k,v in row.items() if k!='definition_name'} for row in item['npc_placements']]
        original[mid]=(resdir,rows);groups=defaultdict(list)
        for index,row in enumerate(rows,1):
            direction=int(row.get('dir',0));distribution[direction]+=1;groups[int(row['id'])].append((index,row))
            if direction==0:zeros.append(dict(map_id=mid,placement_id=index,row=row))
        for ident,group in groups.items():
            if len({r.get('dir','0') for _,r in group})>1:
                duplicate_groups.append(dict(map_id=mid,config_id=ident,placements=[dict(placement_id=i,row=r) for i,r in group]))
    assert sum(distribution.values())==3443 and len(zeros)==13
    assert all(z['row'].get('dir')=='0' for z in zeros)
    assert dict(distribution)=={0:13,1:314,2:40,3:1273,4:761,5:757,6:50,7:235}
    inherited_direction=old_direction_check();inherited_shape=old_shape_check()
    cases=[];vectors=((0.,-1.,0.),(1.,-1.,0.),(1.,0.,0.),(1.,1.,0.),(0.,1.,0.),(-1.,1.,0.),(-1.,0.,0.),(-1.,-1.,0.))
    def run_case(mid,index,row,direction,cap=0,rng=0,label='real_resource'):
        attrs=tables['cnpcconfig'][int(row['id'])];shape=tables['cnpcshape'][int(attrs['modelID'])]
        resdir,rows=original[mid]
        probe=Orientation(rows,attrs,shape,resdir,cap,rng)
        value=probe.pipeline(direction,(mid<<32)|index,(int(row['posx']),int(row['posy'])))
        value.update(case=label,map_id=mid,placement_id=index,original_row=row)
        if value['native_selected'] and 0<=value['native_selected'][-1]<=7:
            assert tuple(value['native_actor_vector'])==vectors[value['native_selected'][-1]]
        cases.append(value);return value
    # All original zero rows, preserving the wire sentinel rather than inventing enum0.
    for zero in zeros:
        out=run_case(zero['map_id'],zero['placement_id'],zero['row'],0,label='all_original_zero_rows')
        assert out['native_selected']==[4],out
    # Three real empty-shape3d records; capability itself is an explicit engine fixture.
    for ident in (10903,11220,11361):
        index,row=next((i,r) for i,r in enumerate(original[1002][1],1) if int(r['id'])==ident)
        for cap in (0,1):
            for direction in range(8):
                out=run_case(1002,index,row,direction,cap,label='real_non3d_shape_capability_matrix')
                assert out['native_shape_flag']['native_98']==0
                if int(tables['cnpcshape'][int(tables['cnpcconfig'][ident]['modelID'])]['dir'])==1:expected=[4]
                elif not cap:expected=[direction or 4]
                elif direction==4:expected=[4,3]
                elif direction:expected=[direction]
                else:expected=[5] if int(row['dir'])==5 else [3]
                assert out['native_selected']==expected,(out,expected)
    index,row=next((i,r) for i,r in enumerate(original[1002][1],1) if r['id']=='10903')
    assert run_case(1002,index,row,0,1,1,'external_rand_other_branch')['native_selected']==[5]
    # Real repeated non-3D config14504 enters a subclass which calls common CNpc init.
    for index,row in enumerate(original[1100][1],1):
        if row['id']=='14504' and index in (32,35):
            for cap in (0,1):
                for direction in (0,int(row['dir'])):
                    out=run_case(1100,index,row,direction,cap,label='real_special_subclass_common_init_only')
                    expected=([direction or 4] if not cap else ([1] if not direction else [4,3] if direction==4 else [direction]))
                    assert out['native_selected']==expected
    for ident in (11206,):
        index,row=next((i,r) for i,r in enumerate(original[1002][1],1) if int(r['id'])==ident)
        for direction in (-1,8,2147483647):
            out=run_case(1002,index,row,direction,label='illegal_wire_diagnostic_not_permission')
            assert out['native_selected']==[direction&0xffffffff]
    for name,digest in historical.items():assert sha(HERE/name)==digest,name
    for name,digest in production.items():assert sha(HERE/name)==digest,name
    result=dict(source_status='client_verified',image_sha256=hashlib.sha256(DATA).hexdigest(),script_sha256=sha(Path(__file__)),
        historical_files_sha256=historical,unchanged_workspace_source_sha256=production,
        input_context='workspace source hashes, not a claim that strict-startup Lifecycle is deployed',
        original_sources=sources,map_records_checked=len(world),static_placements=3443,
        original_direction_distribution=dict(sorted(distribution.items())),original_zero_placements=zeros,
        repeated_config_different_direction_groups=duplicate_groups,
        inherited_19=inherited_direction,inherited_10=inherited_shape,new_cases=cases,
        passed=len(cases)+inherited_direction['case_count']+inherited_shape['case_count'],
        original_zero_is_not_actor_enum_zero=True,field48_zero_is_fallback_sentinel=True,
        direction0_alternate_wire_encoding_proven=False,
        caveats=['All-source range audit is not complete model construction for3443 placements.',
            'Engine capability path+47 and external rand are controlled fixtures, not recovered creation rules.',
            'Special145xx cases cover their common CNpc init only, not subclass postprocessing.',
            'No server original wire mapping/GUI or authoritative service policy is proven.'],
        production_changed=False,policy_changed=False,server_started=False,live_database_accessed=False,native_gui_verified=False)
    output=io.StringIO()
    with redirect_stdout(output):
        for address,length in BLOCKS:print('BLOCK',hex(address));disasm(address,length)
    (HERE/'evidence/npc-orientation-native.txt').write_text(output.getvalue(),encoding='utf8')
    (HERE/'evidence/npc-orientation-native.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(passed=result['passed'],new_cases=len(cases),maps=len(world),direction_distribution=result['original_direction_distribution'],old19_and10_preserved=True),ensure_ascii=False))


if __name__=='__main__':main()
