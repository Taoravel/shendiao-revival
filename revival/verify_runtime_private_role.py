"""Real lease/login/map/NPC/move/reconnect from an explicit private checkpoint.

Natural creation/intro and the public story allocator establish identity. The
initial private checkpoint is a controlled persistence fixture, not bloodmark
completion or a scene handoff; those require their own shared-runtime checks.
"""
import asyncio
from contextlib import closing
from pathlib import Path
import struct
import tempfile
from accounts import AccountStore
from game_runtime import GameRuntime
from inspect_client import OUT,write_json
from task_newbie_chapter import read_newbie_chapter
from verify_runtime import Peer
from world_entity_protocol import VISIT_NPC,ADD_USER_SCREEN
from world_owner import Location
from world_movement import ROLE_STOP
from world_story_instances import (StoryInstanceIntent,load_story_instance_rules,
    prepare_story_instance_storage,allocate_story_instance_transaction)
from world_transfer_storage import bind_map_instance_transaction,load_map_instance_transaction
import runtime_storage
import social_protocol as sp


async def fixtures(store,prepared):
    initial=GameRuntime(store,prepared);roles=[]
    try:
        for name in ('私境重登甲','私境重登乙'):
            role=store.create_role(1111,name,11,1010109)
            peer=Peer(initial);await peer.login(role)
            await peer.request(0xc0018,struct.pack('>i',11001))
            await peer.connection.close();roles.append(role)
    finally:await initial.close()
    rules=load_story_instance_rules(prepared[0],store.newbie_rules)
    with closing(store.connect()) as db,db:prepare_story_instance_storage(db)
    npc=next(p for p in store.npc_resources[0][1501] if p.npc_id==10908)
    entries=[]
    for role in roles:
        epoch=store.acquire_lease(1111,role['id'])
        with closing(store.leased(1111,role['id'],epoch).connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            chapter=read_newbie_chapter(db,1111,role['id'],epoch,store.newbie_rules)
            assert chapter.phase=='completed'
            origin=chapter.origin
            entry=allocate_story_instance_transaction(db,1111,role['id'],epoch,
                StoryInstanceIntent(origin.chapter_id,origin.creation_id,origin.policy,
                    origin.route_fingerprint,rules.source_tasks[(origin.route.character_id,origin.route.school_id)]),rules)
        version=store.position_version(role['id'])+1
        assert store.save_checkpoint(1111,role['id'],epoch,(1501,npc.x,npc.y),version)
        with closing(store.leased(1111,role['id'],epoch).connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            bind_map_instance_transaction(db,1111,role['id'],epoch,
                Location(role['id'],epoch,entry.address,version,npc.x,npc.y))
        entries.append((role,entry))
        store.release_lease(role['id'],epoch)
    return entries,npc


async def check(store,prepared):
    entries,npc=await fixtures(store,prepared)
    runtime=GameRuntime(store,prepared);peers=[]
    try:
        for role,entry in entries:
            peer=Peer(runtime);await peer.login(role);peers.append(peer)
            target=runtime.registered_map(entry.address)
            assert target is not None, 'Real role login flattened its durable private address into public1501'
            owner=runtime.roles[role['id']]
            current=await target.mailbox.call('location',role['id'],owner.epoch)
            assert current.address==entry.address and current.position==(1501,npc.x,npc.y)
            assert any(kind==ADD_USER_SCREEN for kind,body in peer.initial)
            assert await peer.request(VISIT_NPC,struct.pack('>q',(1501<<32)|npc.placement_id))
        own=await peers[0].request(sp.CHAT_SEND,struct.pack('>i',sp.CURRENT_CHANNEL)+sp.text('私境当前')+sp.text('')+b'\0')
        assert any(kind==sp.CHAT_RECEIVE for kind,body in own)
        assert not any(kind==sp.CHAT_RECEIVE for kind,body in await peers[1].take()), 'Private current channel crossed instance identity'
        for channel in (sp.SCHOOL_CHANNEL,sp.WORLD_CHANNEL):
            sent=await peers[0].request(sp.CHAT_SEND,struct.pack('>i',channel)+sp.text('原跨图范围')+sp.text('')+b'\0')
            assert any(kind==sp.CHAT_RECEIVE for kind,body in sent)
            assert any(kind==sp.CHAT_RECEIVE for kind,body in await peers[1].take())
        first=entries[0][0];other=entries[1][0]
        other_owner=runtime.roles[other['id']]
        other_map=runtime.registered_map(entries[1][1].address)
        unchanged=await other_map.mailbox.call('location',other['id'],other_owner.epoch)
        await peers[0].request(ROLE_STOP,b'\0'+struct.pack('>hhQ',npc.x+1,npc.y,1501))
        owner=runtime.roles[first['id']]
        assert owner.position.value==(1501,npc.x+1,npc.y)
        assert owner.battle is None, 'This map routing check must not enter battle'
        assert await other_map.mailbox.call('location',other['id'],other_owner.epoch)==unchanged
        with closing(store.leased(1111,first['id'],owner.epoch).connect()) as db,db:
            db.execute('BEGIN')
            checkpoint=load_map_instance_transaction(db,1111,first['id'],owner.epoch)
            assert checkpoint.address==entries[0][1].address and checkpoint.position==(1501,npc.x+1,npc.y)
        await peers[0].connection.close()
        peers[0]=Peer(runtime);await peers[0].login(first)
        owner=runtime.roles[first['id']]
        same=runtime.registered_map(entries[0][1].address)
        assert (await same.mailbox.call('location',first['id'],owner.epoch)).position==checkpoint.position
        await peers[0].request(sp.CHAT_SEND,struct.pack('>i',sp.CURRENT_CHANNEL)+sp.text('重登私境')+sp.text('')+b'\0')
        assert not any(kind==sp.CHAT_RECEIVE for kind,body in await peers[1].take())
    finally:await runtime.close()
    cold=GameRuntime(store,prepared)
    try:
        peer=Peer(cold);await peer.login(first)
        owner=cold.roles[first['id']]
        current=await cold.registered_map(entries[0][1].address).mailbox.call('location',first['id'],owner.epoch)
        assert current.address==checkpoint.address and current.position==checkpoint.position
        assert await peer.request(VISIT_NPC,struct.pack('>q',(1501<<32)|npc.placement_id))
    finally:await cold.close()
    return dict(passed=['real encrypted login restores two distinct durable private addresses with original NPC resources',
        'actual NPC visit and movement route to their exact owner; other instance remains unchanged',
        'ordinary STOP checkpoint preserves address; disconnect/reconnect and cold runtime restore position and NPC',
        'actual private current chat and reconnect do not cross instances; school/world still reach both'],
        natural_origins=2,initial_private_checkpoint_fixture=True,
        bloodmark_handoff_verified=False,private_capacity_or_unload_verified=False,
        native_gui_verified=False,live_server_changed=False,battle_executed=False)


def main():
    with tempfile.TemporaryDirectory(prefix='private-role-runtime-') as folder:
        store=AccountStore(Path(folder)/'state.sqlite3')
        result=asyncio.run(asyncio.wait_for(check(store,runtime_storage.prepare(store)),60))
    write_json(OUT/'evidence/runtime-private-role-verification.json',result);print(result)


if __name__=='__main__':main()
