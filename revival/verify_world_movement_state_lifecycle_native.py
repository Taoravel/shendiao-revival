"""Offline lifecycle seams; stdout only, no production or process writes."""
import hashlib
import json
from pathlib import Path

from bxml import decode
from inspect_client import ROOT
from pfs import PfsArchive
from research_scene_ready import first_reason_gate
from verify_world_scene_movement_state_native import SceneStateProbe
from verify_world_intro_return_native import ReturnReplay
from unicorn import UC_HOOK_MEM_WRITE
from unicorn.x86_const import UC_X86_REG_EIP, UC_X86_REG_ESI, UC_X86_REG_ESP


class StateReturn(ReturnReplay):
    def __init__(self, maps, sound, prior):
        super().__init__(maps, sound, 1100, (1800,1200))
        self.uc.mem_write(self.player+0x218, bytes([prior]))
        self.movement_writes=[]
        self.uc.hook_add(UC_HOOK_MEM_WRITE, self.observe_state)

    def observe_state(self, emu, access, address, size, value, user):
        if address <= self.player+0x218 < address+size:
            self.movement_writes.append({'pc':hex(emu.reg_read(UC_X86_REG_EIP)),
                'address':hex(address),'size':size,'value':value})

    def movement_state(self):
        return self.uc.mem_read(self.player+0x218,1)[0]


def check():
    cases=[]
    for map_id,a,expected in ((1100,0,0),(1100,1,1),(1404,0,2)):
        r=SceneStateProbe()
        state=r.scene_success_slice(a,2,success=1,reason=516015,map_id=map_id)
        assert state['state_218']==expected
        ack=first_reason_gate(516015)
        assert ack['sent_types']==[0xc003d]
        cases.append({'case':'separate_scene_success_and_first_ACK_slices',
            'map_id':map_id,'normalized_a':a,'scene_result':state,'ACK_slice':ack,
            'scope':'two separately executed original slices, not full Scene flow'})
    ack=first_reason_gate(0)
    assert ack['sent_types']==[]
    cases.append({'case':'ordinary_reason_no_first_ACK','ACK_slice':ack})
    for prior in (0,1,2):
        for name,map_id,reason in (('ordinary',1100,0),('map1404',1404,0),
                                    ('reason516023',1100,516023)):
            r=SceneStateProbe()
            scene=r.scene_success_slice(0,prior,success=1,reason=reason,map_id=map_id)
            assert scene['state_218']==(0 if name=='ordinary' else prior)
            r.uc.mem_write(r.packet+0x18,b'\0')
            r.halt_at=set()
            result=r.process(0x11d7a20)
            assert result['movement_state_218']==0 and result['current']==(100,100)
            r.uc.reg_write(UC_X86_REG_ESI,r.role)
            r.uc.reg_write(UC_X86_REG_ESP,r.stack)
            r.uc.emu_start(0x12028f7,0x120291b,count=1000)
            assert r.read(r.path+0x48)==1
            cases.append({'case':'Scene_then_original_SSetRoleLocation0','prior':prior,
                'scene_case':name,'scene_result':scene,'location_result':result,'mask_after':1})
        for gate,offset in (('virtual158',0x2c0),('virtual15c',0x2cc)):
            r=SceneStateProbe()
            r.uc.mem_write(r.role+0x218,bytes([prior]))
            r.w(r.role+offset,1)
            r.uc.mem_write(r.packet+0x18,b'\0')
            result=r.process(0x11d7a20)
            assert result['movement_state_218']==0
            assert result['current']==(8,8) and result['target_328']==(100,100)
            r.uc.reg_write(UC_X86_REG_ESI,r.role)
            r.uc.reg_write(UC_X86_REG_ESP,r.stack)
            r.uc.emu_start(0x12028f7,0x120291b,count=1000)
            assert r.read(r.path+0x48)==1
            cases.append({'case':'location0_position_gate','prior':prior,'gate':gate,
                          'result':result,'mask_after':1,'position_and_target_disagree':True})
        for missing in ('lookup_role','Scene'):
            r=SceneStateProbe()
            r.uc.mem_write(r.role+0x218,bytes([prior]))
            if missing=='lookup_role':r.found_role=0
            else:r.w(0x2944564,0)
            r.uc.mem_write(r.packet+0x18,b'\0')
            result=r.process(0x11d7a20)
            assert result['movement_state_218']==prior and result['current']==(8,8)
            cases.append({'case':'location0_missing_target_preserves','prior':prior,
                          'missing':missing,'result':result})
    archive=PfsArchive(ROOT/'artres/config.pfs')
    raw=archive.read('autoconfig/knight.gsp.map.cmapconfig.xml')
    maps={int(e.attrib['id']):dict(e.attrib) for e in decode(raw)
          if e.attrib['id'] in ('1100','1009','1007')}
    sound=next(dict(e.attrib) for e in decode(archive.read(
        'autoconfig/knight.gsp.effectpath.ceffectpath.xml')) if e.attrib['id']=='2004')
    for prior in (0,1,2):
        r=StateReturn(maps,sound,prior)
        r.execute(0x12bc780,ecx=r.manager,args=(1009,240,2192))
        assert r.movement_state()==prior and not r.movement_writes
        r.execute(0x12c0bf0,ecx=r.manager)
        assert r.movement_state()==prior and not r.movement_writes
        loads=[x['engine_world_load'] for x in r.return_trace if 'engine_world_load' in x]
        assert loads[-1]['directory']==maps[1100]['resdir']
        r.w(r.manager+0x38,11001)
        r.uc.mem_write(r.manager+0x3c,b'\1')
        r.execute(0x12c0970,ecx=r.manager)
        assert r.r(r.manager+0x3c)&255==0
        assert r.r(0x5410904)==0xc0018 and r.r(0x5410908)==11001
        assert r.movement_state()==prior and not r.movement_writes
        cases.append({'case':'original_Setmap_Return_End_cleanup_preserves_state',
            'prior':prior,'after':r.movement_state(),'state_writes':r.movement_writes,
            'CEnd_type':hex(r.r(0x5410904)),'movie_id':r.r(0x5410908),
            'manager_active_after':r.r(r.manager+0x3c)&255,'world_load_requests':loads,
            'scope':'direct public wrappers/cleanup; not full original movie playback'})
    files=['verify_world_movement_state_lifecycle_native.py',
           'verify_world_scene_movement_state_native.py','research_scene_ready.py',
           'verify_world_intro_return_native.py','verify_world_intro_dispatch_native.py']
    base=Path(__file__).parent
    return {'all_passed':True,'case_count':len(cases),'cases':cases,
        'image_sha256':hashlib.sha256(__import__('native_inspect').DATA).hexdigest(),
        'source_hashes':{n:hashlib.sha256((base/n).read_bytes()).hexdigest() for n in files},
        'adapters':['existing Scene success post-load slice and ACK-send boundary',
                    'existing ReturnReplay engine/config/presentation seams'],
        'not_proven':['actual client ACK correlation or resource rendering',
                      'entire CG timeline or all +218 writers',
                      'unknown auxiliary Scene services do not write +218',
                      'server declaration/activation policy']}


if __name__=='__main__':
    print(json.dumps(check(),ensure_ascii=False,indent=2))
