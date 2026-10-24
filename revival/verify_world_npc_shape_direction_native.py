"""Original shape3d -> CNpc+98 -> direction selection; independent of frozen 19."""
import hashlib
import json
from pathlib import Path
from bxml import decode
from pfs import PfsArchive
from inspect_client import ROOT
from native_inspect import DATA,u32
from verify_world_npc_direction_native import Direction
from unicorn import UC_HOOK_MEM_WRITE
from unicorn.x86_const import (UC_X86_REG_EAX,UC_X86_REG_EBX,UC_X86_REG_ECX,
    UC_X86_REG_ESI,UC_X86_REG_ESP,UC_X86_REG_EIP)


class ShapeDirection(Direction):
    shape_bean,config_bean,info=0x5510000,0x5511000,0x5512000

    def __init__(self,rows,config,shape):
        super().__init__(rows)
        self.config,self.shape=config,shape
        self.shape_lookups=[];self.writes98=[]
        self.compare=u32(0x2244554)
        page=self.compare&~4095
        if not any(a<=page<=b for a,b,_ in self.uc.mem_regions()):self.uc.mem_map(page,4096)
        self.w(0x540a000+0xa28,0x5513000)
        self.w(0x5513008,self.stop+0x900)
        self.w(self.shape_bean,int(shape['id']))
        self.set_ws(self.shape_bean+0xb4,shape.get('shape3d',''))
        self.w(self.shape_bean+0x100,int(shape.get('dir','0')))
        self.uc.hook_add(UC_HOOK_MEM_WRITE,self.observe)

    def observe(self,e,access,address,size,value,user):
        if address<=self.npc+0x98<address+size:
            self.writes98.append({'pc':hex(e.reg_read(UC_X86_REG_EIP)),
                                  'address':hex(address),'size':size,'value':value})

    def hook(self,e,a,size,user):
        sp=e.reg_read(UC_X86_REG_ESP)
        if a==self.stop+0x900:
            self.shape_lookups.append(self.r(sp+4))
            assert self.r(sp+4)==int(self.shape['id'])
            self.ret(4,self.shape_bean)
        elif a==self.compare:
            self.ret(value=int(self.ws(self.r(sp+4))!=self.wz(self.r(sp+8))))
        else:super().hook(e,a,size,user)

    def derive(self,poison):
        self.uc.mem_write(self.npc+0x98,bytes([poison]))
        self.writes98.clear()
        self.w(self.config_bean,int(self.config['id']),int(self.config.get('bodytype','0')),
               int(self.config['npctype']),int(self.config['modelID']))
        # Original first dword copy section establishes CNpc+15c=modelID.
        self.halt={0x11f3025}
        self.w(self.stack,self.stop,self.config_bean)
        self.uc.reg_write(UC_X86_REG_ESP,self.stack)
        self.uc.reg_write(UC_X86_REG_ECX,self.npc+0x150)
        self.uc.emu_start(0x11f3000,self.stop,count=1000)
        assert self.uc.reg_read(UC_X86_REG_EIP)==0x11f3025
        assert self.r(self.npc+0x15c)==int(self.config['modelID'])
        self.w(self.info+0x40,0) # no NpcInfo shape override
        self.w(self.npc+0x44,0) # fresh creation path, before engine actor exists
        self.halt={0x11fb39f,0x11fb5ed}
        self.uc.reg_write(UC_X86_REG_EAX,0)
        self.uc.reg_write(UC_X86_REG_EBX,self.info)
        self.uc.reg_write(UC_X86_REG_ESI,self.npc)
        self.uc.reg_write(UC_X86_REG_ESP,self.stack)
        self.uc.emu_start(0x1201e01,self.stop,count=200000)
        expected=int(bool(self.shape.get('shape3d','')))
        assert self.uc.mem_read(self.npc+0x98,1)[0]==expected
        assert self.writes98[-1]['pc']==('0x11fb398' if expected else '0x11fb5e6')
        assert self.shape_lookups==[int(self.config['modelID'])]
        # Explicit engine actor construction seam, after original flag write.
        self.w(self.npc+0x44,self.actor)
        return {'initial_poison':poison,'shape_id':self.r(self.npc+0x15c),
            'shape3d':self.shape.get('shape3d',''),'native_98':expected,
            'writes98':list(self.writes98),'shape_lookups':list(self.shape_lookups)}


def check():
    archive=PfsArchive(ROOT/'artres/config.pfs')
    sources={}
    records={}
    for table in ('cnpcconfig','cnpcshape'):
        entry=f'autoconfig/knight.gsp.npc.{table}.xml';raw=archive.read(entry)
        sources[entry]=hashlib.sha256(raw).hexdigest()
        records[table]={x.attrib['id']:dict(x.attrib) for x in decode(raw)}
    config=records['cnpcconfig']['11206'];shape=records['cnpcshape'][config['modelID']]
    assert shape['id']=='6027' and shape['shape3d']=='3ds_BN014_gaibangnandizi'
    raw=PfsArchive(ROOT/'artres/map.pfs').read('map_1002_dashengguan/npc.xml')
    sources['map_1002_dashengguan/npc.xml']=hashlib.sha256(raw).hexdigest()
    rows=[dict(x.attrib) for x in decode(raw)]
    cases=[]
    for placement in (54,55):
        row=rows[placement-1];assert row['id']=='11206'
        for field in (0,int(row['dir'])):
            r=ShapeDirection(rows,config,shape)
            derivation=r.derive(255)
            out=r.run(field,key=(1002<<32)|placement,
                      position=(int(row['posx']),int(row['posy'])))
            assert out['native_selected']==[field or 7]
            assert r.uc.mem_read(r.npc+0x98,1)==b'\1' and len(r.writes98)==1
            cases.append({'case':'actual_11206_shape_derived_direction','placement':placement,
                          'derivation':derivation,'direction':out})
    for poison in (0,1,255):
        for nonempty in (False,True):
            control=dict(shape,shape3d=shape['shape3d'] if nonempty else '')
            r=ShapeDirection(rows,config,control);out=r.derive(poison)
            cases.append({'case':'single_shape3d_branch_counterfactual',
                          'original_resource':nonempty,'derivation':out})
    base=Path(__file__).parent
    return {'all_passed':True,'case_count':len(cases),'cases':cases,
        'config_11206':config,'shape_6027':shape,'sources':sources,
        'image_sha256':hashlib.sha256(DATA).hexdigest(),
        'source_hashes':{n:hashlib.sha256((base/n).read_bytes()).hexdigest() for n in
            ('verify_world_npc_shape_direction_native.py','verify_world_npc_direction_native.py',
             'world_npcs.py','world_entity_protocol.py')},
        'adapters':['typed config/shape bean fields from fresh original PFS',
                    'original shape table getter retained; provider lookup returns typed bean',
                    'wstring inequality library ABI',
                    'engine actor provided after original +98 write; full model allocation not executed',
                    'frozen Direction XML/CRT boundaries'],
        'not_proven':['full CNpc/resource/render construction',
                      'all +98 writers or later shape replacement',
                      'live direction display','all shape branches for all NPCs']}


if __name__=='__main__':print(json.dumps(check(),ensure_ascii=False,indent=2))
