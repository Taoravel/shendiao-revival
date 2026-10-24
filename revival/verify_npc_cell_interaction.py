"""Captured native visit at a real clear point crosses actual NPC admission."""
from dataclasses import replace,FrozenInstanceError
import json
from pathlib import Path
import struct
import tempfile
from types import SimpleNamespace
from world_catalog import maps,maze_grids
from world_collision import maze_clear
from world_npcs import load_placements,load_npc_definitions,NpcScene
from world_owner import MapAddress,Location
from npc_interaction import load_npc_interaction_rules
from npc_lifecycle import NpcLifecycle,NpcLifecycleCommand,NpcSpawn
from inspect_client import OUT,write_json


def refused(action):
    try:action()
    except ValueError:return
    raise AssertionError('Unsupported cell policy or stale NPC admission was accepted')


def main():
    placements=load_placements();definitions=load_npc_definitions();catalog=maps()
    npc=next(p for p in placements[1006] if (p.placement_id,p.npc_id)==(13,10498))
    original=json.loads((OUT/'evidence/npc-client-visit-root-red.json').read_text(encoding='utf-8'))
    body=bytes.fromhex(original['captured_body_hex']);key,=struct.unpack('>q',body)
    assert original['original_visit_sent'] and original['mask1_clear']
    assert original['role_logical']==[1668,1032]
    assert maze_clear(maze_grids()[1006],1668,1032,mask=1)
    rules=load_npc_interaction_rules(placements,definitions)
    address=MapAddress(1006,1006,0)
    scene=NpcScene(address,placements[1006],catalog,interaction_radius=32,binding_capacity=64,
        interaction_rules=rules)
    scene.spawn(((key,npc.placement_id),),definitions,batch_size=64)
    point=Location(1,'current-role-lease',address,1,1668,1032)
    assert scene.interact(body,point,point,request_id='actual-native-62',deadline_ms=10,now_ms=1)
    lifecycle=NpcLifecycle(address,placements[1006],catalog,generation='actual-current-map',
        binding_capacity=64,receipt_capacity=64,interaction_rules=rules)
    lifecycle.spawn(((key,npc.placement_id),),definitions,batch_size=64)
    assert lifecycle.interact(body,point,point,request_id='native62-lifecycle',deadline_ms=10,now_ms=1)
    captured=json.loads((OUT/'evidence/npc-interaction-compatibility-audit.json').read_text(encoding='utf-8'))
    for case in captured['ordinary_cases']:
        placement=next(p for p in placements[case['map_id']]
            if (p.placement_id,p.npc_id)==(case['placement_id'],case['npc_id']))
        assert [placement.x,placement.y]==case['npc_logical']
        x,y=case['actor_logical'];assert maze_clear(maze_grids()[placement.map_id],x,y,mask=1)
        target=MapAddress(placement.map_id,placement.map_id,0)
        location=Location(1,'ordinary-current',target,1,x,y)
        for constructor in (NpcScene,NpcLifecycle):
            kwargs={} if constructor is NpcScene else dict(generation='ordinary-map',receipt_capacity=64)
            owner=constructor(target,(placement,),catalog,binding_capacity=64,interaction_rules=rules,**kwargs)
            owner.spawn(((case['key'],placement.placement_id),),definitions,batch_size=64)
            assert owner.interact(struct.pack('>q',case['key']),location,location,
                request_id='ordinary-native64',deadline_ms=10,now_ms=1).npc_id==placement.npc_id
    # Literal independent boundary examples: the accepted region is not a208 circle.
    controlled=replace(npc,x=1615,y=1600)
    assert rules.allows(controlled,(1006,1807,1600))
    assert not rules.allows(controlled,(1006,1808,1600))  # 13 cells, only193 logical pixels.
    controlled=replace(npc,x=1600,y=1600)
    assert rules.allows(controlled,(1006,1807,1679))  # cell12,4; pixel207,79 is outside208 circle.
    assert rules.allows(controlled,(1006,1760,1728))  # cell10,8, squared164.
    assert not rules.allows(controlled,(1006,1792,1680))  # cell12,5, squared169.
    for malformed in ((1668,1032),[1006,1668,1032],(1006,True,1032),(1006,1668.0,1032),
            (1006,-1,1032),(1007,1668,1032)):
        assert not rules.allows(npc,malformed)
    assert not rules.allows(replace(npc,map_id=0),(0,npc.x,npc.y))
    refused(lambda:rules.radius_for(1006,13,10498))
    for owner in (scene,lifecycle):
        for changed in (replace(point,version=2),replace(point,login_epoch='another-lease'),
                replace(point,address=MapAddress(1006,999,0)),replace(point,state='loading'),
                replace(point,address=MapAddress(1006,1006,1))):
            refused(lambda:owner.interact(body,point,changed,
                request_id='stale-proof',deadline_ms=10,now_ms=1))
        far=replace(point,x=1668+13*16,y=npc.y,version=2)
        refused(lambda:owner.interact(body,far,far,request_id='fresh-but-distant',deadline_ms=10,now_ms=1))
        refused(lambda:owner.interact(body,point,point,request_id='expired',deadline_ms=1,now_ms=1))
    before=lifecycle.control_snapshot(now_ms=1)
    command=NpcLifecycleCommand(address,'old-map-generation','remove-old',0,10,'remove',(key,),'test-control')
    refused(lambda:lifecycle.apply(command,now_ms=1))
    assert lifecycle.control_snapshot(now_ms=1)==before
    lifecycle.apply(replace(command,generation=lifecycle.generation,request_id='remove-current'),now_ms=1)
    refused(lambda:lifecycle.interact(body,point,point,request_id='gone',deadline_ms=10,now_ms=1))
    fresh=lifecycle.next_entity_key
    lifecycle.apply(NpcLifecycleCommand(address,lifecycle.generation,'new-common-distance',1,10,'spawn',
        (NpcSpawn(fresh,10498,npc.x,npc.y),),'test-control'),now_ms=1)
    assert lifecycle.interact(struct.pack('>q',fresh),point,point,
        request_id='new-entity-same-predicate',deadline_ms=10,now_ms=1).placement_id!=13
    raw=json.loads((OUT/'design/npc-interaction-v2.json').read_text(encoding='utf-8'))
    with tempfile.TemporaryDirectory() as temp:
        path=Path(temp)/'cells.json'
        variants=[dict(raw,revision='unknown'),dict(raw,distance_mode='circle'),dict(raw,overrides=[]),
            dict(raw,default_radius=208)]
        for field in ('logical_pixels_per_cell','cell_distance_limit_exclusive','cell_squared_distance_limit_exclusive'):
            for value in (True,float(raw[field]),raw[field]+1,None):variants.append(dict(raw,**{field:value}))
        for variant in variants:
            path.write_text(json.dumps(variant),encoding='utf-8')
            refused(lambda:load_npc_interaction_rules(placements,definitions,path))
        path.write_text(json.dumps(raw),encoding='utf-8')
        for bad in (replace(npc,npc_id=999999),replace(npc,map_id=1007),replace(npc,x=-1),
                replace(npc,placement_id=True),replace(npc,npc_id=[])):
            snapshot=dict(placements);snapshot[1006]=(bad,)
            refused(lambda:load_npc_interaction_rules(snapshot,definitions,path))
        snapshot=dict(placements);snapshot[1006]=(npc,npc)
        refused(lambda:load_npc_interaction_rules(snapshot,definitions,path))
        frozen=load_npc_interaction_rules(placements,definitions,path)
        path.write_text('changed after startup',encoding='utf-8')
        assert frozen.allows(npc,point.position)
    try:rules.logical_pixels_per_cell=32
    except FrozenInstanceError:pass
    else:raise AssertionError('Mutable cell policy')
    account=SimpleNamespace(npc_resources=(placements,definitions));resources=account.npc_resources
    from npc_interaction import prepare
    assert prepare(account)==rules and account.npc_resources is resources
    assert scene.radius is None and lifecycle.radius is None
    report={'passed':['same captured bloodmark q64 at original-clear62 point passes Scene and Lifecycle',
        'two ordinary original64-point captures pass both map-owned consumers',
        'cell boundary/within-cell offsets and non208-circle examples match literal decisions',
        'single three-part position shape, frozen strict policy and no scalar radius_for',
        'full address/role lease/version/active/deadline and current position recheck remain',
        'stale map generation and removed entity reject; fresh dynamic binding uses same predicate',
        'unsupported/bool/noninteger recipe and invalid original snapshots reject at startup',
        'policy remains frozen after file changes; startup resource tuple preserved'],
        'policy':rules.revision,'native_gui_verified':False,'live_database_modified':False,
        'source':'captured native requests and original placements; server admission adoption designed',
        'ordinary_native_collision_queries':'controlled fixtures in original research, not real path proof'}
    write_json(OUT/'evidence/npc-cell-interaction.json',report);print(report)


if __name__=='__main__':main()
