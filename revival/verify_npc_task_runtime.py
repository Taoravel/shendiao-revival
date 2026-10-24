"""Disposable native-wire NPC visit/accept/complete/reconnect runtime slice."""
import asyncio
from contextlib import closing
import json
from pathlib import Path
import struct
import tempfile
from accounts import AccountStore
from game_runtime import GameRuntime
import runtime_storage
from verify_runtime import Peer
from task_protocol import C_COMMIT_SCENARIO_QUEST,decode_scenario_state
from task_dialog_protocol import decode_visit_npc,S_REFRESH_USER_EXP,decode_user_experience
from world_entity_protocol import VISIT_NPC,ADD_USER_SCREEN,NPC_SERVICE
from inventory import QUERY_BAG,BAG_INFO
from inspect_client import OUT,write_json


async def check(store,prepared,role,npc):
    rt=GameRuntime(store,prepared)
    key=(npc.map_id<<32)|npc.placement_id
    try:
        p=Peer(rt);await p.login(role)
        assert any(k==ADD_USER_SCREEN for k,b in p.initial)
        command=struct.pack('>iQi',100192,key,0)
        assert await p.request(C_COMMIT_SCENARIO_QUEST,command)==[]
        owner=rt.roles[role['id']]
        await owner.io(runtime_storage.initialize_role_wallet,store,1111,role['id'],owner.epoch,
                       (4321,0,0,0),'explicit_migration')
        await owner.mailbox.call('offer_task',100192)
        menu=await p.request(VISIT_NPC,struct.pack('>q',key))
        assert decode_visit_npc(menu[-1][1])==(key,[],[100192])
        accepted=await p.request(C_COMMIT_SCENARIO_QUEST,command)
        assert [k for k,b in accepted]==[0xc4a45,0xc4a47,0xc232a]
        assert decode_scenario_state(accepted[1][1])==(100192,3)
        await p.connection.close()
        p=Peer(rt);await p.login(role)
        assert any(k==0xc4a45 for k,b in p.initial)
        await p.request(VISIT_NPC,struct.pack('>q',key))
        assert await p.request(NPC_SERVICE,struct.pack('>qi',key,100192))==[]
        completed=await p.request(C_COMMIT_SCENARIO_QUEST,command)
        assert decode_scenario_state(completed[0][1])==(100192,1)
        assert decode_user_experience(completed[1][1])==150
        bag=await p.request(QUERY_BAG,struct.pack('>iQ',1,0))
        assert bag[0][0]==BAG_INFO and struct.unpack_from('>Q',bag[0][1],4)[0]==4321
        assert await p.request(C_COMMIT_SCENARIO_QUEST,command)==[]
        with closing(store.connect()) as db:
            assert db.execute('SELECT experience FROM role_progress WHERE role_id=?',(role['id'],)).fetchone()==(150,)
            assert db.execute('SELECT template_id,quantity,binding FROM inventory_items WHERE role_id=?',(role['id'],)).fetchall()==[(43000,1,1)]
        await p.connection.close()
        p=Peer(rt);await p.login(role)
        assert [decode_user_experience(b) for k,b in p.initial if k==S_REFRESH_USER_EXP]==[150]
        return {'passed':['map-owned NPC spawn in encrypted stream','unoffered quest refused',
            'NPC distance/scoped menu then native CCommit acceptance','active quest resumes after reconnect',
            'generic service ID cannot complete a task','completion + bound item + 150 EXP atomic',
            'duplicate commit does not reaward','native nonempty bag response','reconnect restores experience'],
            'task':100192,'map':1006,'npc':10899,'live_role_modified':False,'native_gui_verified':False}
    finally:
        await rt.close()


def main():
    with tempfile.TemporaryDirectory() as temp:
        store=AccountStore(Path(temp)/'npc-task.sqlite3')
        role=store.create_role(1111,'对话测试',11,1010109)
        prepared=runtime_storage.prepare(store)
        npc=next(p for p in store.npc_resources[0][1006] if p.npc_id==10899)
        store.save_position(1111,role['id'],(npc.map_id,npc.x,npc.y))
        result=asyncio.run(check(store,prepared,role,npc))
    write_json(OUT/'evidence/npc-task-runtime.json',result)
    print(json.dumps(result))


if __name__=='__main__':main()
