"""Observe an original task/map versus actual placed NPC contract mismatch.

This is a diagnosis, not permission to remap tasks, create NPCs or complete one.
Only original102002/10157, a disposable role and real encrypted Peer are used.
"""
import asyncio
import hashlib
import json
from pathlib import Path
import struct
import tempfile

from accounts import AccountStore
from game_runtime import GameRuntime
from inspect_client import OUT,write_json
from task_dialog_protocol import decode_visit_npc
from task_protocol import C_COMMIT_SCENARIO_QUEST
from verify_runtime import Peer
from world_entity_protocol import VISIT_NPC,VISIT_NPC_REPLY
import runtime_storage


INPUTS=('diagnose_npc_task_room_target.py','game_runtime.py','runtime_storage.py',
    'accounts.py','tasks.py','task_domain.py','task_conversation.py','world_npcs.py',
    'catalogs/tasks.json','catalogs/world.json','catalogs/knight.gsp.npc.cnpcconfig.json',
    'design/npc-interaction-v2.json')


def sha(name):return hashlib.sha256((OUT/name).read_bytes()).hexdigest()


async def observe(store,prepared,role,npc):
    runtime=GameRuntime(store,prepared)
    try:
        peer=Peer(runtime);await peer.login(role);owner=runtime.roles[role['id']]
        task=store.task_resources.definitions[102002]
        assert task['target']['npc_id']==npc.npc_id==10157
        assert task['target']['map_id']==1007 and npc.map_id==1376
        await owner.mailbox.call('offer_task',102002)
        before=await owner.io(runtime_storage.task_state,store,1111,role['id'],owner.epoch)
        assert 102002 in before[1].offered
        key=(npc.map_id<<32)|npc.placement_id
        messages=await peer.request(VISIT_NPC,struct.pack('>q',key))
        visits=[decode_visit_npc(body) for kind,body in messages if kind==VISIT_NPC_REPLY]
        assert visits and visits[-1][0]==key
        assert 102002 not in visits[-1][2]
        command=struct.pack('>iQi',102002,key,0)
        assert await peer.request(C_COMMIT_SCENARIO_QUEST,command)==[]
        try:
            await owner.mailbox.call('receive',C_COMMIT_SCENARIO_QUEST,command,
                request_id='original-room-map-contract-diagnosis')
        except ValueError as error:
            refusal=str(error)
        else:raise AssertionError('Original task map mismatch no longer reproduces; inspect current behavior')
        assert refusal=='Task acceptance NPC mismatch',refusal
        after=await owner.io(runtime_storage.task_state,store,1111,role['id'],owner.epoch)
        assert after==before
        return dict(task_id=102002,npc_id=10157,task_target_map=1007,
            original_static_map=1376,original_static_placement=npc.placement_id,
            original_static_position=[npc.x,npc.y],actual_encrypted_npc_visit_accepted=True,
            trusted_offered_task_omitted_from_menu=True,original_commit_rejected=refusal,
            offered_task_state_unchanged=True,
            seam='actual Peer visit/commit and actual RoleOwner receive exception',
            interpretation='task target map and original placed room map disagree; authoritative mapping policy unresolved',
            task_completed=False,map_or_npc_remapped=False,live_database_modified=False,
            service_started=False,native_gui_verified=False,scope='workspace diagnosis; not deployment verification')
    finally:await runtime.close()


def main():
    inputs={name:sha(name) for name in INPUTS}
    with tempfile.TemporaryDirectory(prefix='npc-task-room-target-') as directory:
        store=AccountStore(Path(directory)/'state.sqlite3')
        role=store.create_role(1111,'任务房间引用',11,1010109)
        prepared=runtime_storage.prepare(store)
        npc=next(p for p in store.npc_resources[0][1376] if p.npc_id==10157)
        epoch=store.acquire_lease(1111,role['id'])
        assert store.save_checkpoint(1111,role['id'],epoch,(npc.map_id,npc.x,npc.y),1)
        report=asyncio.run(asyncio.wait_for(observe(store,prepared,role,npc),60))
    for name,digest in inputs.items():
        if sha(name)!=digest:raise RuntimeError('Source changed during diagnosis: '+name)
    report['source_sha256']=inputs
    write_json(OUT/'evidence/npc-task-room-target-diagnosis.json',report)
    print(json.dumps({key:value for key,value in report.items() if key!='source_sha256'},ensure_ascii=False))


if __name__=='__main__':main()
