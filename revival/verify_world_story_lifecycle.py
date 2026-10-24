"""Actual map-owner quiescence and bounded private projection lifecycle."""
from world_owner import MapOwner,MapAddress,Location,MoveCommand
from world_catalog import maps
from dataclasses import replace
from pathlib import Path
import tempfile
import struct
import asyncio
import hashlib
import json
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from accounts import AccountStore
import runtime_storage
from world_story_instances import (load_story_instance_rules,StoryInstance,StoryInstanceIntent,
    prepare_story_instance_storage,allocate_story_instance_transaction,load_story_instance_transaction)
from task_newbie_chapter import read_newbie_chapter
from game_runtime import GameRuntime
from verify_growth_runtime import GrowthPeer
from world_story_projection_pool import StoryProjectionPool
from inspect_client import OUT,write_json


def refused(action):
    try:action()
    except ValueError:return
    raise AssertionError('Busy, stale or premature lifecycle operation accepted')


async def durable_cycle(store,prepared,rules):
    with closing(store.connect()) as db,db:prepare_story_instance_storage(db)
    runtime=GameRuntime(store,prepared)
    try:
        role=store.create_role(1111,'生命周期目录',11,1010109)
        peer=GrowthPeer(runtime);await peer.login(role)
        owner=runtime.roles[role['id']]
        await peer.request(0xc0018,struct.pack('>i',11001))
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            origin=read_newbie_chapter(db,1111,owner.id,owner.epoch,store.newbie_rules).origin
            intent=StoryInstanceIntent(origin.chapter_id,origin.creation_id,origin.policy,origin.route_fingerprint,100106)
            record=allocate_story_instance_transaction(db,1111,owner.id,owner.epoch,intent,rules)
        pool=StoryProjectionPool(rules,pins_per_projection=2)
        load=pool.acquire(record,request_id='durable-cycle',deadline_ms=1000,now_ms=0,actor_state='static_original')
        projection=MapOwner(record.address,prepared[3],capacity=1,transfer_capacity=2,mailbox_capacity=2)
        projection.configure_lifecycle(scene_delivery_capacity=2,actor_state='static_original')
        use=pool.finish_load(load,projection.inspect_lifecycle(0),now_ms=1);pool.release(use,now_ms=1)
        unload=pool.begin_unload(use.handle,request_id='durable-unload',now_ms=60001)
        receipt=projection.retire_idle(projection.inspect_lifecycle(60001),60001,
            minimum_idle_ms=rules.idle_unload_after_ms)
        assert pool.finish_unload(unload,receipt)==record and pool.loaded_count==0
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            restored=load_story_instance_transaction(db,1111,owner.id,owner.epoch,intent,rules,
                expected_address=record.address)
            assert restored==record
        next_load=pool.acquire(restored,request_id='durable-cold',deadline_ms=62000,now_ms=61000,
            actor_state='static_original')
        cold=MapOwner(restored.address,prepared[3],capacity=1,transfer_capacity=2,mailbox_capacity=2)
        cold.configure_lifecycle(scene_delivery_capacity=2,actor_state='static_original')
        new_use=pool.finish_load(next_load,cold.inspect_lifecycle(61000),now_ms=61001)
        assert new_use.handle.record.address==use.handle.record.address
        assert new_use.handle.map_generation!=use.handle.map_generation
        refused(lambda:pool.release(use,now_ms=61001))
        await peer.connection.close()
        return dict(natural_roles=1,durable_identity_preserved=True,fresh_owner_generation=True,
            scope='empty projection cycle of a naturally authorized directory; no bloodmark entry or actor render')
    finally:await runtime.close()


def main():
    names=('world_owner.py','world_story_projection_pool.py','world_story_instances.py',
        'verify_world_story_lifecycle.py','design/story-instance-v1.json')
    source_hashes={name:hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in names}
    with tempfile.TemporaryDirectory(prefix='story-lifecycle-') as folder:
        store=AccountStore(Path(folder)/'roles.sqlite3')
        prepared=runtime_storage.prepare(store)
        rules=load_story_instance_rules(prepared[0],store.newbie_rules)
        assert rules.pins_per_projection==64 and rules.scene_delivery_capacity==64
        policy=json.loads((OUT/'design/story-instance-v1.json').read_text(encoding='utf-8'))
        invalid_path=Path(folder)/'invalid-policy.json'
        for name in ('pins_per_projection','scene_delivery_capacity'):
            for value in (True,64.0,65,None):
                invalid=dict(policy,**{name:value})
                invalid_path.write_text(json.dumps(invalid),encoding='utf-8')
                refused(lambda:load_story_instance_rules(prepared[0],store.newbie_rules,path=invalid_path))
        durable=asyncio.run(asyncio.wait_for(durable_cycle(store,prepared,rules),45))
    catalog=maps();address=MapAddress(1501,4611686018427387905,0)
    owner=MapOwner(address,catalog,capacity=1,transfer_capacity=2,mailbox_capacity=2)
    owner.configure_lifecycle(scene_delivery_capacity=2,actor_state='static_original')
    idle=owner.inspect_lifecycle(0)
    refused(lambda:owner.retire_idle(idle,59999,minimum_idle_ms=60000))
    retired=owner.retire_idle(idle,60000,minimum_idle_ms=60000)
    assert retired.address==address and retired.idle_since_ms==0 and retired.retired_at_ms==60000
    refused(lambda:owner.join(Location(1,1,address,1,1008,1264)))
    stale_command=MoveCommand(Location(1,1,address,1,1008,1264),'old-owner-command',100000,0xc0faa,
        b'\0'+struct.pack('>hhQ',1008,1264,1501))
    assert owner.submit(stale_command,60000)=='owner_retired'
    assert owner.move(stale_command,60000).rejection=='owner_retired'
    legacy=MapOwner(address,catalog,capacity=1,transfer_capacity=2,mailbox_capacity=2)
    legacy_snapshot=legacy.inspect_lifecycle(0)
    assert not legacy_snapshot.enabled and not legacy_snapshot.idle
    refused(lambda:legacy.retire_idle(legacy_snapshot,60000,minimum_idle_ms=60000))
    aba=MapOwner(address,catalog,capacity=1,transfer_capacity=2,mailbox_capacity=2)
    aba.configure_lifecycle(scene_delivery_capacity=2,actor_state='static_original')
    old_empty=aba.inspect_lifecycle(0)
    aba_location=aba.join(Location(1,1,address,1,1008,1264));aba.leave(aba_location)
    refused(lambda:aba.retire_idle(old_empty,60000,minimum_idle_ms=60000))
    fresh_empty=aba.inspect_lifecycle(60000)
    assert fresh_empty.idle_since_ms==60000 and fresh_empty.revision!=old_empty.revision
    aba.retire_idle(fresh_empty,120000,minimum_idle_ms=60000)
    queued=MapOwner(address,catalog,capacity=1,transfer_capacity=2,mailbox_capacity=2)
    queued.configure_lifecycle(scene_delivery_capacity=2,actor_state='static_original')
    queued.inspect_lifecycle(0)
    assert queued.submit(stale_command,1)=='accepted'
    queued_snapshot=queued.inspect_lifecycle(1)
    assert queued_snapshot.queued_movements==1 and not queued_snapshot.idle
    refused(lambda:queued.retire_idle(queued_snapshot,60000,minimum_idle_ms=60000))
    assert queued.process_one(60000).rejection=='not_in_map'
    queued.retire_idle(queued.inspect_lifecycle(60000),120000,minimum_idle_ms=60000)
    pending=MapOwner(address,catalog,capacity=1,transfer_capacity=2,mailbox_capacity=2)
    pending.configure_lifecycle(scene_delivery_capacity=2,actor_state='static_original')
    current=pending.join(Location(1,1,address,1,1008,1264))
    refused(lambda:pending.begin_scene_delivery(replace(current,login_epoch=True),
        connection_generation=1,request_id='malformed-epoch'))
    delivery=pending.begin_scene_delivery(current,connection_generation=1,request_id='scene-send')
    assert pending.begin_scene_delivery(current,connection_generation=1,request_id='scene-send')==delivery
    refused(lambda:pending.begin_scene_delivery(current,connection_generation=2,request_id='scene-send'))
    refused(lambda:pending.finish_scene_delivery(replace(delivery,connection_generation=2)))
    refused(lambda:pending.finish_scene_delivery(replace(delivery,location=replace(current,login_epoch=True))))
    other_generation=MapOwner(address,catalog,capacity=1,transfer_capacity=2,mailbox_capacity=2)
    other_generation.configure_lifecycle(scene_delivery_capacity=2,actor_state='static_original')
    refused(lambda:other_generation.finish_scene_delivery(delivery))
    assert pending.finish_scene_delivery(delivery)
    replacement_delivery=pending.begin_scene_delivery(current,connection_generation=1,request_id='scene-send')
    assert replacement_delivery!=delivery
    refused(lambda:pending.finish_scene_delivery(delivery))
    delivery=replacement_delivery
    pending.leave(current)
    blocked=pending.inspect_lifecycle(0)
    assert blocked.pending_scene_deliveries==1 and not blocked.idle
    refused(lambda:pending.retire_idle(blocked,60000,minimum_idle_ms=60000))
    assert pending.finish_scene_delivery(delivery)
    assert not pending.finish_scene_delivery(delivery)
    now_idle=pending.inspect_lifecycle(60000)
    pending.retire_idle(now_idle,120000,minimum_idle_ms=60000)
    dirty=MapOwner(address,catalog,capacity=1,transfer_capacity=2,mailbox_capacity=2)
    dirty.configure_lifecycle(scene_delivery_capacity=2,actor_state='static_original')
    dirty.mark_actor_mutation()
    dirty_snapshot=dirty.inspect_lifecycle(0)
    assert not dirty_snapshot.actors_pristine and not dirty_snapshot.idle
    refused(lambda:dirty.retire_idle(dirty_snapshot,60000,minimum_idle_ms=60000))
    source_address=MapAddress(1006,1006,0)
    source=MapOwner(source_address,catalog,capacity=1,transfer_capacity=2,mailbox_capacity=2)
    source.configure_lifecycle(scene_delivery_capacity=2,actor_state='static_original')
    source_location=source.join(Location(1,1,source_address,1,576,3536))
    target=MapOwner(address,catalog,capacity=1,transfer_capacity=2,mailbox_capacity=2)
    target.configure_lifecycle(scene_delivery_capacity=2,actor_state='static_original')
    target.inspect_lifecycle(0)
    offer=source.prepare_transfer(source_location,(1501,1008,1264),request_id='lifecycle-handoff',
        deadline_ms=100000,now_ms=0)
    reserved=target.reserve(offer,1)
    reserved_snapshot=target.inspect_lifecycle(1)
    assert reserved_snapshot.incoming==1 and reserved_snapshot.members==0 and not reserved_snapshot.idle
    refused(lambda:target.retire_idle(reserved_snapshot,60000,minimum_idle_ms=60000))
    frozen=source.freeze(reserved,1)
    source_snapshot=source.inspect_lifecycle(1)
    assert source_snapshot.members==source_snapshot.departures==1
    refused(lambda:source.retire_idle(source_snapshot,60000,minimum_idle_ms=60000))
    receipt=target.activate(frozen,1);source.finalize(receipt)
    active=target.ready(receipt.location);target.leave(active)
    assert not target.inspect_lifecycle(60000).idle
    target.retire_receipt(receipt);source.retire_receipt(receipt)
    target.retire_idle(target.inspect_lifecycle(60000),120000,minimum_idle_ms=60000)
    source.retire_idle(source.inspect_lifecycle(60000),120000,minimum_idle_ms=60000)
    refused(lambda:StoryProjectionPool(rules,pins_per_projection=65))
    pool=StoryProjectionPool(rules,pins_per_projection=2)
    loads=[]
    for number in range(128):
        record=StoryInstance(rules.kind,1111,number+1,
            StoryInstanceIntent(f'chapter-{number}',f'create-{number}','2026-10-23.newbie.1','a'*64,100106),
            rules.revision,MapAddress(1501,4611686018427388004+number,0))
        loads.append(pool.acquire(record,request_id=f'load-{number}',deadline_ms=1000,now_ms=0,
            actor_state='static_original'))
    assert pool.loaded_count==128
    refused(lambda:pool.acquire(replace(record,address=replace(record.address,instance_id=4611686018427388999),
        role_id=999,intent=replace(record.intent,chapter_id='overflow')),
        request_id='overflow',deadline_ms=1000,now_ms=0,actor_state='static_original'))
    cancellation=pool.cancel_load(loads[-1])
    assert pool.loaded_count==128, 'Observation timeout released a still-running load slot'
    assert pool.cancel_load(loads[-1])==cancellation
    refused(lambda:pool.acquire(replace(record,address=replace(record.address,instance_id=4611686018427388999),
        role_id=999,intent=replace(record.intent,chapter_id='overflow')),
        request_id='still-overflow',deadline_ms=1000,now_ms=1,actor_state='static_original'))
    cancelled_owner=MapOwner(loads[-1].record.address,catalog,capacity=1,transfer_capacity=2,mailbox_capacity=2)
    cancelled_owner.configure_lifecycle(scene_delivery_capacity=2,actor_state='static_original')
    refused(lambda:pool.finish_load(loads[-1],cancelled_owner.inspect_lifecycle(0),now_ms=1))
    assert pool.loaded_count==128
    cancelled_owner.retire_idle(cancelled_owner.inspect_lifecycle(60000),60000,minimum_idle_ms=60000)
    assert pool.finish_load_cancel(cancellation)==loads[-1].record and pool.loaded_count==127
    refused(lambda:pool.finish_load_cancel(cancellation))
    load=loads[0]
    projection=MapOwner(load.record.address,catalog,capacity=1,transfer_capacity=2,mailbox_capacity=2)
    projection.configure_lifecycle(scene_delivery_capacity=2,actor_state='static_original')
    use=pool.finish_load(load,projection.inspect_lifecycle(0),now_ms=1)
    refused(lambda:pool.begin_unload(use.handle,request_id='held-use',now_ms=1))
    assert pool.release(use,now_ms=1)
    refused(lambda:pool.begin_unload(use.handle,request_id='operation-just-finished',now_ms=1))
    refused(lambda:pool.begin_unload(use.handle,request_id='external-work-idle-boundary',now_ms=60000))
    attempt1=pool.begin_unload(use.handle,request_id='retry-unload',now_ms=60001)
    pool.cancel_unload(attempt1,projection.inspect_lifecycle(60001))
    attempt2=pool.begin_unload(use.handle,request_id='retry-unload',now_ms=60001)
    refused(lambda:pool.cancel_unload(attempt1,projection.inspect_lifecycle(60001)))
    pool.cancel_unload(attempt2,projection.inspect_lifecycle(60001))
    unload=pool.begin_unload(use.handle,request_id='idle-unload',now_ms=60001)
    refused(lambda:pool.acquire(load.record,request_id='while-unloading',deadline_ms=63000,now_ms=60002,
        actor_state='static_original'))
    receipt=projection.retire_idle(projection.inspect_lifecycle(60001),60001,
        minimum_idle_ms=rules.idle_unload_after_ms)
    refused(lambda:pool.cancel_unload(unload,projection.inspect_lifecycle(60001)))
    assert pool.finish_unload(unload,receipt)==load.record and pool.loaded_count==126
    refused(lambda:pool.finish_unload(unload,receipt))
    again=pool.acquire(load.record,request_id='cold-reload',deadline_ms=62000,now_ms=61000,
        actor_state='static_original')
    assert again.record.address==load.record.address and again.generation!=load.generation
    loaded_again=MapOwner(again.record.address,catalog,capacity=1,transfer_capacity=2,mailbox_capacity=2)
    loaded_again.configure_lifecycle(scene_delivery_capacity=2,actor_state='static_original')
    use_again=pool.finish_load(again,loaded_again.inspect_lifecycle(61000),now_ms=61001)
    loaded_again.mark_actor_mutation()
    hot=pool.acquire(again.record,request_id='hot-dynamic',deadline_ms=63000,now_ms=61002,
        actor_state='dynamic_uncheckpointed')
    assert hot.handle==use_again.handle
    refused(lambda:pool.release(use,now_ms=61002))
    assert pool.release(hot,now_ms=61003)
    replacement=pool.acquire(again.record,request_id='hot-dynamic',deadline_ms=63000,now_ms=61003,
        actor_state='dynamic_uncheckpointed')
    assert replacement.use_id!=hot.use_id
    refused(lambda:pool.release(hot,now_ms=61003))
    refused(lambda:pool.acquire(replace(again.record,address=replace(again.record.address,instance_id=4611686018427389999),
        role_id=999,intent=replace(again.record.intent,chapter_id='dynamic-cold')),
        request_id='dynamic-cold',deadline_ms=63000,now_ms=61002,actor_state='dynamic_uncheckpointed'))
    outcomes=set()
    with ThreadPoolExecutor(max_workers=2) as threads:
        for _ in range(32):
            raced=MapOwner(address,catalog,capacity=1,transfer_capacity=2,mailbox_capacity=2)
            raced.configure_lifecycle(scene_delivery_capacity=2,actor_state='static_original')
            expected=raced.inspect_lifecycle(0);barrier=Barrier(2)
            def enqueue():
                barrier.wait(timeout=2)
                return raced.submit(stale_command,60000)
            def retire():
                barrier.wait(timeout=2)
                try:raced.retire_idle(expected,60000,minimum_idle_ms=60000)
                except ValueError:return False
                return True
            if _ % 2:
                sealed=threads.submit(retire);submitted=threads.submit(enqueue)
            else:
                submitted=threads.submit(enqueue);sealed=threads.submit(retire)
            accepted=submitted.result(timeout=3);retired_ok=sealed.result(timeout=3)
            assert (retired_ok and accepted=='owner_retired') or (not retired_ok and accepted=='accepted')
            outcomes.add((retired_ok,accepted))
    result=dict(passed=['actual empty owner retires only after60seconds and fences old joins/commands',
        'legacy map owners remain non-retirable until explicit lifecycle opt-in',
        'join-leave ABA invalidates old idle evidence and restarts a conservative timer',
        'queued movement blocks retirement until drained',
        'pending scene delivery survives leave and blocks retirement until exact completion',
        'scene delivery replay is idempotent; foreign connection and owner generation refuse',
        'dynamic actor mutation blocks unload without an in-memory pristine reset',
        'reserved targets and frozen sources cannot retire',
        'handoff receipts must be explicitly retired before idle countdown starts',
        '128 process slots include in-flight loads and reject a129th allocation',
        'load cancellation retains its slot until exact loader cleanup confirmation and rejects late completion',
        'pending operation pins block unload and stale replacement releases refuse',
        'unload retry has a fresh attempt identity; old cancellation refuses',
        'retiring projection refuses new acquisition until exact owner retirement',
        'cold rebuild retains full address and changes runtime generation',
        'live dynamic projections remain usable while uncheckpointed cold loads refuse',
        'natural durable directory survives projection unload and cold owner rebuild with a fresh generation',
        '32 actual producer-vs-owner retirement races never accept a command on a retired owner'],
        process_slot_limit=128,minimum_idle_ms=60000,
        enqueue_retire_races=32,race_outcomes=sorted(outcomes),
        durable_cycle=durable,source_sha256=source_hashes,
        scope='published policy and actual MapOwner lifecycle; pool directory records are frozen controlled inputs',
        shared_runtime_integrated=False,gui_verified=False,live_server_changed=False)
    assert source_hashes=={name:hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in names}
    write_json(OUT/'evidence/world-story-lifecycle-verification.json',result)
    print(result)


if __name__=='__main__':main()
