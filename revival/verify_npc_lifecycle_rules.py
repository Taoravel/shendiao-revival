"""Frozen lifecycle startup policy through its public loader; no live storage."""
from dataclasses import FrozenInstanceError,replace
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
from inspect_client import OUT,write_json
from npc_interaction import load_npc_interaction_rules
from world_npcs import load_placements,load_npc_definitions
from world_catalog import maps
from world_owner import MapAddress,Location
import struct
import npc_lifecycle


def main():
    placements,definitions=load_placements(),load_npc_definitions()
    interaction=load_npc_interaction_rules(placements,definitions)
    assert hasattr(npc_lifecycle,'load_npc_lifecycle_rules'), 'NPC lifecycle has no frozen startup policy loader'
    rules=npc_lifecycle.load_npc_lifecycle_rules(interaction)
    assert (rules.revision,rules.binding_capacity,rules.receipt_capacity,rules.snapshot_batch_size)==(
        '2026-10-23.npc-lifecycle.1',512,4096,64)
    assert rules.interaction_rules is interaction
    assert rules.interaction_policy=='2026-10-23.npc-interaction.2'
    assert rules.initial_control_source=='root-lifecycle-control:2026-10-23.npc-lifecycle.1'
    assert rules.movement_enabled is False
    try:rules.binding_capacity=1024
    except FrozenInstanceError:pass
    else:raise AssertionError('NPC lifecycle startup policy is mutable')
    resources=(placements,definitions)
    accounts=SimpleNamespace(npc_resources=resources,npc_interaction_rules=interaction)
    assert hasattr(npc_lifecycle,'prepare'), 'NPC lifecycle has no startup preparation Interface'
    assert npc_lifecycle.prepare(accounts)==rules
    assert accounts.npc_lifecycle_rules.interaction_rules is interaction
    assert accounts.npc_resources is resources

    def refused(action):
        try:action()
        except ValueError:return
        raise AssertionError('Unsupported NPC lifecycle startup policy accepted')

    policy=json.loads((OUT/'design/npc-lifecycle-v1.json').read_text(encoding='utf-8'))
    invalid=[]
    for field in ('revision','binding_capacity','receipt_capacity','snapshot_batch_size',
                  'interaction_policy','initial_control_source','movement_enabled'):
        missing=dict(policy);del missing[field];invalid.append(missing)
    for field in ('binding_capacity','receipt_capacity','snapshot_batch_size'):
        for value in (None,True,float(policy[field]),0,-1,policy[field]+1):
            invalid.append(dict(policy,**{field:value}))
    for field,value in (('revision','unknown'),('interaction_policy','2026-10-23.npc-interaction.1'),
                        ('initial_control_source','task:anything'),('movement_enabled',True),
                        ('movement_enabled',0),('interaction_radius',32),('interaction_radius',208)):
        invalid.append(dict(policy,**{field:value}))
    invalid.extend(([],None))
    with tempfile.TemporaryDirectory(prefix='npc-lifecycle-rules-') as directory:
        path=Path(directory)/'policy.json'
        for candidate in invalid:
            path.write_text(json.dumps(candidate),encoding='utf-8')
            refused(lambda:npc_lifecycle.load_npc_lifecycle_rules(interaction,path=path))
        path.write_text(json.dumps(policy),encoding='utf-8')
        frozen=npc_lifecycle.load_npc_lifecycle_rules(interaction,path=path)
        path.write_text('{}',encoding='utf-8')
    assert frozen==rules
    legacy=load_npc_interaction_rules(placements,definitions,OUT/'design/npc-interaction-v1.json')
    for bad in (None,legacy,SimpleNamespace(revision=interaction.revision)):
        refused(lambda:npc_lifecycle.load_npc_lifecycle_rules(bad))
        refused(lambda:replace(rules,interaction_rules=bad))
    unprepared=SimpleNamespace(npc_lifecycle_rules=rules)
    refused(lambda:npc_lifecycle.prepare(unprepared))
    assert unprepared.npc_lifecycle_rules is rules

    address=MapAddress(1007,77,0);catalog=maps()
    scene=npc_lifecycle.NpcLifecycle(address,placements[1007],catalog,generation='owning-map-fixture',
        binding_capacity=rules.binding_capacity,receipt_capacity=rules.receipt_capacity,
        interaction_rules=rules.interaction_rules)
    static=tuple(((1007<<32)|p.placement_id,p.placement_id) for p in placements[1007])
    assert len(static)==196
    with patch('builtins.open',side_effect=AssertionError('Lifecycle hot path file read')), \
         patch('io.open',side_effect=AssertionError('Lifecycle hot path file read')):
        packets=scene.spawn(static,definitions,batch_size=rules.snapshot_batch_size)
        assert len(packets)==4 and scene.control_snapshot(now_ms=1).revision==0
        npc=placements[1007][0];location=Location(1,'role-fixture',address,1,npc.x,npc.y)
        body=struct.pack('>q',(1007<<32)|npc.placement_id)
        assert scene.interact(body,location,location,request_id='visit',deadline_ms=100,now_ms=1)
        assert scene.radius is None
        key=scene.next_entity_key
        command=npc_lifecycle.NpcLifecycleCommand(address,scene.generation,'fill-explicit-budget',0,100,
            'spawn',tuple(npc_lifecycle.NpcSpawn(key+i,npc.npc_id,npc.x,npc.y) for i in range(316)),
            rules.initial_control_source)
        filled=scene.apply(command,now_ms=1)
        assert len(filled.messages)==5 and len(scene.view())==512
        before=scene.control_snapshot(now_ms=1)
        refused(lambda:scene.apply(replace(command,request_id='over-budget',expected_revision=1,
            entities=(npc_lifecycle.NpcSpawn(scene.next_entity_key,npc.npc_id,npc.x,npc.y),)),now_ms=1))
        move=npc_lifecycle.NpcMove(static[0][0],(npc.x+1,npc.y),100,1)
        refused(lambda:scene.apply(replace(command,request_id='motion-still-off',expected_revision=1,
            operation='move',entities=(move,)),now_ms=1))
        assert scene.control_snapshot(now_ms=1)==before
        assert len(scene.snapshot(batch_size=rules.snapshot_batch_size))==8
    report={'passed':['approved startup budgets and exact shared interaction object are frozen',
        'startup preparation keeps the original resource tuple and shared interaction object',
        'strict approved fields reject missing, changed, bool/float and legacy circle policies',
        'legacy or missing interaction rules reject without overwriting startup state',
        'original largest map bootstraps with frozen v2 and no hot file reads',
        '512 includes static and dynamic entities; 513th and unactivated motion reject atomically'],
        'invalid_policy_cases':len(invalid),'capacity_entities_are_controlled_fixtures':True,
        'trusted_runtime_source_authorization_verified':False,
        'shared_runtime_verified':False,'live_database_modified':False,'native_gui_verified':False}
    write_json(OUT/'evidence/npc-lifecycle-rules-verification.json',report)
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':main()
