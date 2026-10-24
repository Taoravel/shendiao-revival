"""Actual owner task projections into the original tracker branch, disposable DB."""
import asyncio
from pathlib import Path
import struct
import tempfile
from accounts import AccountStore
from game_runtime import GameRuntime
from inspect_client import OUT, write_json
from task_protocol import S_ACCEPT_SCENARIO_QUEST, decode_accept_scenario_quest
from verify_runtime import Peer
from verify_task_tracker_native import trace_path
from world_newbie import END_PLAY_CG, load_newbie_routes
from verify_newbie_runtime import journal
import runtime_storage


def projected(frames):
    return [decode_accept_scenario_quest(body) for kind,body in frames if kind==S_ACCEPT_SCENARIO_QUEST]


def normal(infos, task_id):
    matches=[info for info in infos if info.quest_id==task_id]
    assert len(matches)==1, f'Active chapter task {task_id} is absent or duplicated on reconnect'
    branch=trace_path(matches[0].state)
    assert branch['branch']=='normal_config_trace', f'Active task {task_id} projects original failure text: {branch}'


async def check(store, prepared, role):
    route=load_newbie_routes()[(9,11)]
    runtime=GameRuntime(store,prepared)
    try:
        peer=Peer(runtime);await peer.login(role)
        normal(projected(peer.initial),route.intro_task_id)
        reply=await peer.request(END_PLAY_CG,struct.pack('>i',route.intro_movie_id))
        normal(projected(reply),route.successor_task_id)
        before=journal(store,role['id'])
        assert dict(before[0])=={route.intro_task_id:'completed',route.successor_task_id:'active'}
        assert await peer.request(END_PLAY_CG,struct.pack('>i',route.intro_movie_id))==[]
        await peer.connection.close()
        peer=Peer(runtime);await peer.login(role)
        normal(projected(peer.initial),route.successor_task_id)
        assert journal(store,role['id'])==before, 'Display recovery rewrote durable progress or rewards'
        await peer.connection.close()
    finally:await runtime.close()


def main():
    with tempfile.TemporaryDirectory(prefix='tracker-runtime-') as folder:
        store=AccountStore(Path(folder)/'state.sqlite3')
        prepared=runtime_storage.prepare(store)
        role=store.create_role(1111,'追踪验收',11,1010109)
        asyncio.run(check(store,prepared,role))
    result=dict(passed=['actual root and successor wire states select original normal tracker branch',
        'reconnect restores the exact active chapter successor once',
        'duplicate ESC/end and reconnect preserve durable tasks and rewards'],
        database='disposable',native_gui_verified=False,live_server_changed=False)
    write_json(OUT/'evidence/task-tracker-runtime-verification.json',result)
    print(result)


if __name__=='__main__':main()
