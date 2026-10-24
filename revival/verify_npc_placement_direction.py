"""Original placement direction through public NPC spawning and native decoder.

No service, live role or GUI is used. NpcBasic.field48 zero retains its native
fallback meaning; this check does not remap it to actor direction enum zero.
"""
import hashlib
import json
import struct
from dataclasses import replace
from collections import Counter

from inspect_client import OUT,write_json
from npc_interaction import load_npc_interaction_rules
from npc_lifecycle import NpcLifecycle,NpcLifecycleCommand,NpcSpawn
from world_catalog import maps
from world_entity_protocol import ADD_USER_SCREEN
from world_npcs import NpcScene,load_placements,load_npc_definitions
from world_owner import MapAddress
from verify_world_entities_native import probe


def original_directions(messages):
    result={}
    for kind,body in messages:
        assert kind==ADD_USER_SCREEN
        def observe(emu,obj):
            def u32(address):return struct.unpack('<I',emu.mem_read(address,4))[0]
            head=u32(obj+0x18);count=u32(obj+0x1c);node=u32(head)
            for _ in range(count):
                assert node!=head
                key=struct.unpack('<q',emu.mem_read(node+0x10,8))[0]
                direction=struct.unpack('<i',emu.mem_read(node+0x50,4))[0]
                assert key not in result
                result[key]=direction;node=u32(node)
            assert node==head
        probe(0xfc5f40,0xfc68f0,0xfc69a0,payload=body,observer=observe)
    return result


def main():
    places=load_placements();definitions=load_npc_definitions();catalog=maps()
    selected=tuple(p for p in places[1002] if p.npc_id==11206)
    assert [(p.placement_id,p.direction) for p in selected]==[(54,7),(55,1)]
    rules=load_npc_interaction_rules(places,definitions)
    scene=NpcScene(MapAddress(1002,1002,0),selected,catalog,
        binding_capacity=64,interaction_rules=rules)
    bindings=tuple(((1002<<32)|p.placement_id,p.placement_id) for p in selected)
    expected={key:p.direction for (key,_),p in zip(bindings,selected)}
    actual=original_directions(scene.spawn(bindings,definitions,batch_size=64))
    hashes={name:hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in (
        'world_npcs.py','npc_lifecycle.py','world_entity_protocol.py','catalogs/world.json',
        'verify_world_entities_native.py','native_gameplay_probe.py','evidence/native-image.bin')}
    if actual!=expected:
        write_json(OUT/'evidence/npc-placement-direction-baseline.json',dict(
            expected=expected,actual=actual,source_sha256=hashes,
            failure='Original per-placement dir is lost before native NpcBasic.field48',
            seam='public NpcScene.spawn -> actual original SAddUserScreen decoder',
            live_server_changed=False,native_gui_verified=False))
        raise AssertionError(f'Original placement directions must reach native NpcBasic: {actual} != {expected}')
    lifecycle=NpcLifecycle(MapAddress(1002,1002,0),selected,catalog,generation='direction-domain-check',
        binding_capacity=64,receipt_capacity=32,interaction_rules=rules)
    lifecycle.spawn(bindings,definitions,batch_size=64)
    life_actual=original_directions(lifecycle.snapshot(batch_size=64))
    if life_actual!=expected:
        write_json(OUT/'evidence/npc-placement-direction-lifecycle-baseline.json',dict(
            expected=expected,actual=life_actual,source_sha256=hashes,
            failure='Current lifecycle snapshot loses original per-placement directions',
            live_server_changed=False,native_gui_verified=False))
        raise AssertionError(f'Lifecycle snapshot must preserve original directions: {life_actual} != {expected}')
    for value in (-1,8,True,False,None,1.0,'1'):
        try:replace(selected[0],direction=value)
        except ValueError:pass
        else:
            write_json(OUT/'evidence/npc-placement-direction-range-baseline.json',dict(
                failure='NpcPlacement accepts a non-original direction value',
                accepted_value=repr(value),accepted_type=type(value).__name__,source_sha256=hashes))
            raise AssertionError('Invalid original direction accepted: '+repr(value))
    # Cover the complete original corpus through both public encoding paths.
    count=0;distribution=Counter()
    for map_id,entries in places.items():
        address=MapAddress(map_id,map_id,0)
        bindings_all=tuple(((map_id<<32)|p.placement_id,p.placement_id) for p in entries)
        expected_all={(map_id<<32)|p.placement_id:p.direction for p in entries}
        static=NpcScene(address,entries,catalog,binding_capacity=512,interaction_rules=rules)
        assert original_directions(static.spawn(bindings_all,definitions,batch_size=64))==expected_all,map_id
        current=NpcLifecycle(address,entries,catalog,generation='direction-corpus-'+str(map_id),
            binding_capacity=512,receipt_capacity=32,interaction_rules=rules)
        current.spawn(bindings_all,definitions,batch_size=64)
        assert original_directions(current.snapshot(batch_size=64))==expected_all,map_id
        count+=len(entries);distribution.update(p.direction for p in entries)
    assert count==3443 and distribution=={0:13,1:314,2:40,3:1273,4:761,5:757,6:50,7:235}
    # Dynamic spawn keeps the existing zero fallback; a replay encodes current
    # retained directions without republishing a stale bootstrap snapshot.
    source='controlled-direction-domain-check'
    remove=NpcLifecycleCommand(lifecycle.address,lifecycle.generation,'direction-remove',
        lifecycle.revision,100,'remove',(bindings[0][0],),source)
    lifecycle.apply(remove,now_ms=1)
    control=lifecycle.control_snapshot(now_ms=2)
    spawn=NpcLifecycleCommand(lifecycle.address,lifecycle.generation,'direction-spawn',
        control.revision,100,'spawn',(NpcSpawn(control.next_entity_key,11206,1286,3455),),source)
    change=lifecycle.apply(spawn,now_ms=2)
    assert original_directions(change.messages)=={control.next_entity_key:0}
    replay=lifecycle.apply(spawn,now_ms=3)
    assert replay.replayed and original_directions(replay.messages)=={control.next_entity_key:0}
    assert original_directions(lifecycle.snapshot(batch_size=64))=={bindings[1][0]:1,control.next_entity_key:0}
    for name,digest in hashes.items():
        assert hashlib.sha256((OUT/name).read_bytes()).hexdigest()==digest,name
    report=dict(passed=['same original config keeps distinct placement directions7/1',
        'current lifecycle snapshot preserves original placement directions',
        'placement value rejects out-of-range and non-integer directions',
        'all304 original maps and3443 placements preserve raw direction through native decoder',
        'all13 original zero values retain native fallback sentinel',
        'dynamic zero/replay/current snapshot retain their own direction values'],
        source_sha256=hashes,native_decoder_consumed_exact_public_payload=True,
        map_records_checked=len(places),original_placements_checked=count,
        original_direction_distribution=dict(sorted(distribution.items())),
        zero_mapping_changed=False,actual_shared_runtime_verified=False,
        live_server_changed=False,native_gui_verified=False)
    write_json(OUT/'evidence/npc-placement-direction-verification.json',report)
    print(json.dumps(report['passed']))


if __name__=='__main__':main()
