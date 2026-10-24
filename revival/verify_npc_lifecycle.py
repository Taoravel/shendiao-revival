"""Public map-owned NPC lifecycle: native presence and interaction authority."""
from dataclasses import replace,FrozenInstanceError
import struct
from unittest.mock import patch
from world_catalog import maps
from world_owner import MapAddress,Location
from world_npcs import load_placements,load_npc_definitions
from world_entity_protocol import ADD_USER_SCREEN,REMOVE_USER_SCREEN,remove_npc_screen
from inspect_client import OUT,write_json
from npc_lifecycle import NpcLifecycle,NpcLifecycleCommand,NpcSpawn
from verify_world_entities_native import probe


def main():
    address=MapAddress(1007,77,0);placements=load_placements()[1007]
    npc=next(p for p in placements if p.npc_id==10000)
    scene=NpcLifecycle(address,placements,maps(),generation='map-generation-a',
        interaction_radius=32,binding_capacity=4,receipt_capacity=2)
    definitions=load_npc_definitions();key=(1007<<32)|npc.placement_id
    assert scene.spawn(((key,npc.placement_id),),definitions,batch_size=2)
    control=scene.control_snapshot(now_ms=1)
    assert (control.address,control.generation,control.revision,control.next_entity_key)==(
        address,'map-generation-a',0,key+1)
    assert tuple(e.entity_key for e in control.presence)==(key,)
    try:control.revision=99
    except FrozenInstanceError:pass
    else:raise AssertionError('Map NPC control snapshot is mutable')
    location=Location(1,'role-a',address,7,npc.x,npc.y)
    def command(identity,operation,entities,revision=None):
        return NpcLifecycleCommand(address,'map-generation-a',identity,scene.revision if revision is None else revision,
            100,operation,entities,'trusted-task-fixture')
    def visit(k=key,loc=location):
        return scene.interact(struct.pack('>q',k),loc,loc,request_id='visit',deadline_ms=100,now_ms=1)
    assert visit().npc_id==10000
    removal=command('remove-static','remove',(key,))
    hidden=scene.apply(removal,now_ms=1)
    assert hidden.messages==((REMOVE_USER_SCREEN,remove_npc_screen((key,))),)
    assert hidden.before[0].entity_key==key and hidden.after==()
    _,raw=probe(0xe6e9e0,0xe6ea90,0xe6eb20,payload=hidden.messages[0][1])
    assert struct.unpack_from('<I',raw,0x1c)[0]==1
    assert not scene.snapshot(batch_size=2)
    removed_control=scene.control_snapshot(now_ms=1)
    assert removed_control.revision==1 and removed_control.presence==()
    assert tuple(e.entity_key for e in control.presence)==(key,)
    assert scene.next_entity_key==key+1
    def refused(action):
        before=scene.view(),scene.revision,scene.next_entity_key
        try:action()
        except ValueError:pass
        else:raise AssertionError('Invalid/stale NPC lifecycle operation accepted')
        assert (scene.view(),scene.revision,scene.next_entity_key)==before
    refused(visit)
    next_key=key+1
    show=command('show-new','spawn',(NpcSpawn(next_key,10000,npc.x+20,npc.y),))
    created=scene.apply(show,now_ms=1)
    assert created.messages[0][0]==ADD_USER_SCREEN
    assert created.before==() and created.after[0].placement.x==npc.x+20
    _,raw=probe(0xfc5f40,0xfc68f0,0xfc69a0,payload=created.messages[0][1])
    assert struct.unpack_from('<I',raw,0x1c)[0]==1
    assert visit(next_key).entity_key==next_key
    refused(lambda:visit(next_key,replace(location,x=npc.x-13)))
    refused(lambda:scene.apply(replace(show,request_id='reuse-old',expected_revision=scene.revision,
        entities=(NpcSpawn(key,10000,npc.x,npc.y),)),now_ms=1))
    refused(lambda:scene.apply(replace(show,request_id='bad-template',expected_revision=scene.revision,
        entities=(NpcSpawn(next_key+1,99999999,npc.x,npc.y),)),now_ms=1))
    refused(lambda:scene.apply(replace(show,request_id='bad-map',expected_revision=scene.revision,
        address=MapAddress(1007,78,0)),now_ms=1))
    refused(lambda:scene.apply(replace(show,request_id='old-generation',expected_revision=scene.revision,
        generation='previous-map-generation'),now_ms=1))
    refused(lambda:scene.apply(replace(show,request_id='expired',expected_revision=scene.revision),now_ms=100))
    # Replaying an old spawn after later removal must not resurrect a ghost.
    with patch('builtins.open',side_effect=AssertionError('NPC lifecycle hot path file I/O')), \
         patch('io.open',side_effect=AssertionError('NPC lifecycle hot path file I/O')):
        assert visit(next_key).npc_id==10000
        assert scene.snapshot(batch_size=2)
        removed_again=scene.apply(command('remove-new','remove',(next_key,)),now_ms=1)
    replay=scene.apply(show,now_ms=1)
    assert replay.replayed and replay.messages==removed_again.messages and not scene.view()
    assert replay.before[0].entity_key==next_key and not replay.after
    # The bounded receipt cache can evict old commands; revision still fences
    # those old commands rather than executing their original effects again.
    refused(lambda:scene.apply(removal,now_ms=1))
    current=scene.revision
    refused(lambda:scene.apply(command('mixed-invalid','remove',(next_key,next_key+9)),now_ms=1))
    assert scene.revision==current
    bad_batch=command('mixed-spawn','spawn',(
        NpcSpawn(next_key+1,10000,npc.x,npc.y),NpcSpawn(next_key+2,99999999,npc.x+1,npc.y)))
    refused(lambda:scene.apply(bad_batch,now_ms=1))
    good_batch=replace(bad_batch,entities=(bad_batch.entities[0],replace(bad_batch.entities[1],npc_id=10000)))
    batch=scene.apply(good_batch,now_ms=1)
    assert len(scene.view())==2 and len(scene.snapshot(batch_size=1))==2
    _,raw=probe(0xfc5f40,0xfc68f0,0xfc69a0,payload=batch.messages[0][1])
    assert struct.unpack_from('<I',raw,0x1c)[0]==2
    refused(lambda:scene.apply(command('overflow','spawn',tuple(
        NpcSpawn(next_key+i,10000,npc.x,npc.y) for i in range(3,6))),now_ms=1))
    refused(lambda:scene.apply(replace(good_batch,expected_revision=scene.revision),now_ms=1))
    refused(lambda:visit(next_key+1,replace(location,address=MapAddress(1007,78,0))))
    second=NpcLifecycle(MapAddress(1007,78,0),placements,maps(),generation='map-generation-b',
        interaction_radius=32,binding_capacity=4,receipt_capacity=2)
    second.spawn(((key,npc.placement_id),),definitions,batch_size=2)
    assert len(second.view())==1 and len(scene.view())==2
    report={'passed':['native static removal immediately revokes NPC interaction',
        'new independently keyed original NPC definition spawns and can be visited at new position',
        'old keys cannot be reused after removal; map generation/instance/revision/deadline fence',
        'invalid mixed commands and missing templates leave state and revision unchanged',
        'replayed spawn after removal sends current removal; no client ghost resurrection',
        'bounded receipt eviction still rejects stale accepted commands via expected revision',
        'actual lifecycle spawn/remove payloads consumed by original native decoders',
        'failed mixed spawn consumes no keys/receipt; corrected same request succeeds with two same-template entities',
        'capacity and conflicting retry reject atomically; batched snapshots retain independent keys',
        'no hot-path file reads; independent map instance retains its own NPC state',
        'frozen control snapshot captures current authority once; prior snapshots survive removal unchanged'],
        'shared_map_owner_integrated':False,'native_gui_verified':False,'live_database_modified':False}
    write_json(OUT/'evidence/npc-lifecycle-verification.json',report);print(report)


if __name__=='__main__':main()
