"""Exact bloodmark placement exception through public map NPC interactions."""
from dataclasses import replace,FrozenInstanceError
import json
from pathlib import Path
import struct
import tempfile
from types import SimpleNamespace
from world_catalog import maps
from world_owner import MapAddress,Location
from world_npcs import load_placements,load_npc_definitions,NpcScene
from inspect_client import OUT,write_json
from npc_interaction import load_npc_interaction_rules,prepare
from npc_lifecycle import NpcLifecycle,NpcLifecycleCommand,NpcSpawn


def refused(action):
    try:action()
    except ValueError:return
    raise AssertionError('Unsupported NPC policy or interaction was accepted')


def main():
    placements=load_placements();definitions=load_npc_definitions();catalog=maps()
    npc=next(p for p in placements[1006] if (p.placement_id,p.npc_id)==(13,10498))
    address=MapAddress(1006,1006,0);key=(1006<<32)|13
    legacy_path=OUT/'design/npc-interaction-v1.json'
    rules=load_npc_interaction_rules(placements,definitions,legacy_path)
    scene=NpcScene(address,placements[1006],catalog,interaction_radius=32,binding_capacity=1,
        interaction_rules=rules)
    scene.spawn(((key,13),),definitions,batch_size=64)
    edge=Location(1,'known-role-lease',address,1,npc.x+48,npc.y)
    assert scene.interact(struct.pack('>q',key),edge,edge,
        request_id='bloodmark-boundary48',deadline_ms=10,now_ms=1).npc_id==10498
    lifecycle=NpcLifecycle(address,placements[1006],catalog,generation='current-map-generation',
        interaction_radius=32,binding_capacity=64,receipt_capacity=64,interaction_rules=rules)
    lifecycle.spawn(((key,13),),definitions,batch_size=64)
    assert lifecycle.interact(struct.pack('>q',key),edge,edge,
        request_id='lifecycle-boundary48',deadline_ms=10,now_ms=1).npc_id==10498
    for owner in (scene,lifecycle):
        def interact(expected,current):
            return owner.interact(struct.pack('>q',key),expected,current,
                request_id='current-scope',deadline_ms=10,now_ms=1)
        assert interact(replace(edge,x=npc.x,y=npc.y+38),replace(edge,x=npc.x,y=npc.y+38))
        for far in (replace(edge,x=npc.x+49),replace(edge,x=npc.x+32,y=npc.y+36)):
            refused(lambda:interact(far,far))
        for wrong in (replace(edge,version=2),replace(edge,login_epoch='old-role-lease'),
                replace(edge,state='loading'),replace(edge,address=MapAddress(1006,999,0)),
                replace(edge,address=MapAddress(1006,1006,1))):
            refused(lambda:interact(edge,wrong))
        changed=replace(edge,x=npc.x+49,version=2)
        refused(lambda:interact(changed,changed))
    # Controlled alternative identities: never assign the exception by NPC ID alone.
    for alternate in (replace(npc,placement_id=999),replace(npc,npc_id=10497),replace(npc,map_id=1007)):
        alternate_address=MapAddress(alternate.map_id,alternate.map_id,0)
        for dynamic in (False,True):
            kwargs=dict(interaction_radius=32,binding_capacity=64,interaction_rules=rules)
            if dynamic:kwargs.update(generation='alternate-generation',receipt_capacity=64)
            other=(NpcLifecycle if dynamic else NpcScene)(alternate_address,(alternate,),catalog,**kwargs)
            other.spawn(((123,alternate.placement_id),),definitions,batch_size=64)
            point=Location(1,'known-role-lease',alternate_address,1,alternate.x+32,alternate.y)
            assert other.interact(struct.pack('>q',123),point,point,
                request_id='default32-edge',deadline_ms=10,now_ms=1)
            far=replace(point,x=alternate.x+33)
            refused(lambda:other.interact(struct.pack('>q',123),far,far,
                request_id='default32-outside',deadline_ms=10,now_ms=1))
    for constructor in (NpcScene,NpcLifecycle):
        extra={} if constructor is NpcScene else dict(generation='g',receipt_capacity=64)
        refused(lambda:constructor(address,(npc,),catalog,interaction_radius=48,binding_capacity=64,
            interaction_rules=rules,**extra))
    before=lifecycle.control_snapshot(now_ms=1)
    remove=NpcLifecycleCommand(address,'old-map-generation','old-remove',0,10,'remove',(key,),'test-control')
    refused(lambda:lifecycle.apply(remove,now_ms=1))
    assert lifecycle.control_snapshot(now_ms=1)==before
    lifecycle.apply(replace(remove,generation=lifecycle.generation,request_id='remove-original'),now_ms=1)
    refused(lambda:lifecycle.interact(struct.pack('>q',key),edge,edge,
        request_id='removed-key',deadline_ms=10,now_ms=1))
    new_key=lifecycle.next_entity_key
    lifecycle.apply(NpcLifecycleCommand(address,lifecycle.generation,'new-does-not-inherit',1,10,
        'spawn',(NpcSpawn(new_key,10498,npc.x,npc.y),),'test-control'),now_ms=1)
    refused(lambda:lifecycle.interact(struct.pack('>q',new_key),edge,edge,
        request_id='new-placement-default32',deadline_ms=10,now_ms=1))
    point=replace(edge,x=npc.x+32)
    assert lifecycle.interact(struct.pack('>q',new_key),point,point,
        request_id='new-placement-within32',deadline_ms=10,now_ms=1)
    raw=json.loads((OUT/'design/npc-interaction-v1.json').read_text(encoding='utf-8'))
    with tempfile.TemporaryDirectory() as temp:
        path=Path(temp)/'interaction.json'
        mutations=[dict(raw,revision='unknown'),dict(raw,default_radius=True),dict(raw,default_radius=48),
            dict(raw,overrides=raw['overrides']*2),dict(raw,overrides=[]),dict(raw,overrides=[True])]
        for field,value in (('map_id',1007),('placement_id',14),('npc_id',999999),('radius',64),
                ('radius',True),('radius',48.0),('original_x',1664),('original_y',960)):
            mutations.append(dict(raw,overrides=[dict(raw['overrides'][0],**{field:value})]))
        incomplete=dict(raw['overrides'][0]);del incomplete['npc_id']
        mutations.append(dict(raw,overrides=[incomplete]))
        for mutation in mutations:
            path.write_text(json.dumps(mutation),encoding='utf-8')
            refused(lambda:load_npc_interaction_rules(placements,definitions,path))
        path.write_text(json.dumps(raw),encoding='utf-8')
        missing=dict(placements);missing[1006]=tuple(p for p in placements[1006] if p.placement_id!=13)
        refused(lambda:load_npc_interaction_rules(missing,definitions,path))
        duplicate=dict(placements);duplicate[1006]=placements[1006]+(npc,)
        refused(lambda:load_npc_interaction_rules(duplicate,definitions,path))
        wrong=dict(placements);wrong[1006]=tuple(replace(p,x=1664) if p.placement_id==13 else p
            for p in placements[1006])
        refused(lambda:load_npc_interaction_rules(wrong,definitions,path))
        absent=dict(definitions);del absent[10498]
        refused(lambda:load_npc_interaction_rules(placements,absent,path))
        mismatched=dict(definitions);mismatched[10498]=dict(definitions[10498],id='10000')
        refused(lambda:load_npc_interaction_rules(placements,mismatched,path))
        frozen=load_npc_interaction_rules(placements,definitions,path)
        path.write_text('invalid after startup',encoding='utf-8')
        assert frozen.radius_for(1006,13,10498)==48
        assert scene.interact(struct.pack('>q',key),edge,edge,
            request_id='no-hot-policy-read',deadline_ms=10,now_ms=1)
    account_snapshot=SimpleNamespace(npc_resources=(placements,definitions));resources=account_snapshot.npc_resources
    assert prepare(account_snapshot,path=legacy_path)==rules and account_snapshot.npc_resources is resources
    try:rules.default_radius=48
    except FrozenInstanceError:pass
    else:raise AssertionError('Mutable startup interaction rules')
    report={'passed':['static and lifecycle original1006/p13/10498 accept inclusive48 and clear-point distance38',
        '49 and diagonal distance above48 reject; current position changes are re-proved',
        'same NPC at other placement/map and other NPC at same placement retain inclusive32',
        'address instance/partition, lease, position version and loading guards retained',
        'stale map-generation control rejected; removed key cannot be used; new instance does not inherit48',
        'unsupported/duplicate/noninteger/bool policy or changed original placement/definition rejects at startup',
        'rules frozen, no command-time policy read, explicit constructor default must match',
        'startup account snapshot retains original two-part NPC resource tuple'],
        'policy':'2026-10-23.npc-interaction.1','source_status':'designed distance, original placement client_verified',
        'alternate_identity_fixtures':True,'natural_task_flow_verified':False,
        'native_gui_verified':False,'live_database_modified':False}
    write_json(OUT/'evidence/npc-interaction-rules.json',report);print(report)


if __name__=='__main__':main()
