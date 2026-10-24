"""Durable story identity -> bounded exact runtime map and original NPC resources.

Controlled public map-mailbox joins check routing only. They do not claim the
unfinished bloodmark/handoff/load pipeline admitted these roles to the dream.
"""
import asyncio
from contextlib import closing
import hashlib
from pathlib import Path
import struct
import tempfile

from accounts import AccountStore
from game_runtime import GameRuntime,Position
from inspect_client import OUT,write_json
from task_newbie_chapter import read_newbie_chapter
from verify_growth_runtime import GrowthPeer
from world_entity_protocol import ADD_USER_SCREEN
from world_movement import ROLE_STOP
from world_story_instances import (StoryInstanceIntent,load_story_instance_rules,
    prepare_story_instance_storage,allocate_story_instance_transaction)
import runtime_storage


async def check(store,prepared):
    rules=load_story_instance_rules(prepared[0],store.newbie_rules)
    with closing(store.connect()) as db,db:
        prepare_story_instance_storage(db)
    runtime=GameRuntime(store,prepared)
    try:
        entries=[]
        for name in ('实例路由甲','实例路由乙'):
            role=store.create_role(1111,name,11,1010109)
            peer=GrowthPeer(runtime);await peer.login(role)
            await peer.request(0xc0018,struct.pack('>i',11001))
            owner=runtime.roles[role['id']]
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                chapter=read_newbie_chapter(db,1111,owner.id,owner.epoch,store.newbie_rules)
                assert chapter.phase=='completed'
                origin=chapter.origin
                intent=StoryInstanceIntent(origin.chapter_id,origin.creation_id,origin.policy,
                    origin.route_fingerprint,100106)
                entry=allocate_story_instance_transaction(db,1111,owner.id,owner.epoch,intent,rules)
            entries.append((owner,entry))
        assert entries[0][1].address!=entries[1][1].address
        maps=[];locations=[]
        npc=next(p for p in store.npc_resources[0][1501] if p.npc_id==10908)
        for owner,entry in entries:
            assert runtime.registered_map(entry.address) is None
            try:
                runtime.map(entry.address)
            except ValueError:
                pass
            else:
                raise AssertionError('Private address alone bypassed directory admission and projection loading budget')
            target=await runtime.story_maps.get_map(entry,request_id='factory-'+str(owner.id),
                deadline_ms=runtime.story_maps.now()+10000)
            assert runtime.registered_map(entry.address) is target, 'Private map registered under a flattened or wrong address'
            assert runtime.map(entry.address) is target
            # Explicit controlled domain join, not a real role scene handoff.
            joined=await target.mailbox.call('join',Position(owner.id,owner.epoch,
                (1501,npc.x,npc.y),1,(npc.x//16,npc.y//16)))
            current=await target.mailbox.call('location',owner.id,owner.epoch)
            assert current.address==entry.address
            packets=await target.mailbox.call('spawn',owner.id,owner.epoch)
            assert any(kind==ADD_USER_SCREEN for kind,body in packets), 'Private map lost original template NPC resources'
            key=(1501<<32)|npc.placement_id
            proof,seen=await target.mailbox.call('npc',owner.id,owner.epoch,joined.version,struct.pack('>q',key))
            assert proof.npc_id==10908 and proof.address==entry.address and seen==current
            maps.append(target);locations.append(current)
        assert maps[0] is not maps[1]
        owner=entries[0][0];initial=locations[0]
        # This test explicitly controls map admission rather than a role handoff.
        # Exercise the same public map declaration Interface with an explicit
        # fixture send receipt; the encrypted lifecycle test proves real drain.
        from world_protocol import scene_entry,ENTER_SCENE
        declaration=await maps[0].mailbox.call('declare_movement',owner.id,owner.epoch,
            initial,1,'controlled-map-fixture',ENTER_SCENE,scene_entry(initial.position,reason=0),'normal_scene')
        await maps[0].mailbox.call('movement_sent',owner.id,owner.epoch,declaration,False)
        moved,_=await maps[0].mailbox.call('move',owner.id,owner.epoch,initial.version,
            ROLE_STOP,b'\0'+struct.pack('>hhQ',npc.x+1,npc.y,1501))
        assert moved.value==(1501,npc.x+1,npc.y)
        other=entries[1][0]
        assert await maps[1].mailbox.call('location',other.id,other.epoch)==locations[1]
        public=runtime.map(1501)
        assert public not in maps and runtime.map(1501) is public
        return dict(passed=['unloaded private address alone refuses; two durable records load through the bounded projection Interface',
            'two durable story identities route to distinct exactly registered runtime owners',
            'same private address reuses its owner; original1501 NPC10908 remains interactable in both',
            'controlled mailbox movement in one instance preserves the other; public1501 remains distinct'],
            natural_origins=2,controlled_map_joins=True,shared_bloodmark_or_role_handoff_verified=False,
            cold_recovery_verified=False,native_gui_verified=False,live_server_changed=False,battle_executed=False)
    finally:await runtime.close()


def main():
    try:
        with tempfile.TemporaryDirectory(prefix='runtime-private-map-') as folder:
            store=AccountStore(Path(folder)/'roles.sqlite3');prepared=runtime_storage.prepare(store)
            result=asyncio.run(asyncio.wait_for(check(store,prepared),60))
    except AssertionError as error:
        write_json(OUT/'evidence/runtime-private-map-factory-budget-baseline.json',dict(failure=str(error),
            game_runtime_sha256=hashlib.sha256((OUT/'game_runtime.py').read_bytes()).hexdigest(),
            live_server_changed=False,native_gui_verified=False,battle_executed=False))
        raise
    write_json(OUT/'evidence/runtime-private-map-factory-verification.json',result);print(result)


if __name__=='__main__':main()
