"""Natural next dialogue and the explicit unsupported progress/transfer gate.

No manual spawn/task offer/grant, GUI, live listener or actual battle. Movement
uses original-clear report witnesses, not client pathfinding or visual timing.
"""
import asyncio
from contextlib import closing
from dataclasses import replace
import json
from pathlib import Path
import struct
import tempfile

from accounts import AccountStore
from game_runtime import GameRuntime
from inspect_client import OUT,write_json
from task_protocol import (C_COMMIT_SCENARIO_QUEST,S_ACCEPT_SCENARIO_QUEST,
    S_REFRESH_SCENARIO_QUEST_STATE,decode_accept_scenario_quest)
from verify_first_master_runtime import state
from verify_growth_runtime import GrowthPeer,role_values
from verify_newbie_jiaxing_runtime import check as jiaxing_prefix
from wire import compact
from world_catalog import maps,maze_grids
from world_entity_protocol import VISIT_NPC
from world_movement import ROLE_MOVE,ROLE_STOP
from world_newbie import load_newbie_routes,check_birth_site
from world_npcs import load_placements
import runtime_storage


async def check(store,prepared,role,route,witness):
    await jiaxing_prefix(store,prepared,role,route,witness)
    before=state(store,role['id'])
    assert dict(before[0])[100160]=='active' and before[2]==(31,)
    definition=store.task_resources.definitions[100160]
    assert definition['next_ids']==[100106] or tuple(definition['next_ids'])==(100106,)
    source=store.position(1111,role['id'])
    candidate=replace(route,home_map_id=source[0],first_npc_id=definition['target']['npc_id'],cinematic_endpoint=source)
    walk=check_birth_site(candidate,maps(),maze_grids()[source[0]],load_placements()[source[0]],
        state_byte=0,interaction_radius=32,max_visited=100000)
    assert walk.status=='reachable',walk
    runtime=GameRuntime(store,prepared)
    try:
        peer=GrowthPeer(runtime);await peer.login(role)
        path=walk.path
        await peer.request(ROLE_MOVE,struct.pack('>hhhhQ',*path[0],*path[-1],0))
        await peer.request(ROLE_STOP,compact(len(path))+b''.join(struct.pack('>hh',*p) for p in path)
            +struct.pack('>hhQ',*path[-1],0))
        assert runtime.roles[role['id']].position.value==(1006,*path[-1])
        key=(1006<<32)|walk.placement_id
        menu=await peer.request(VISIT_NPC,struct.pack('>q',key))
        assert (S_REFRESH_SCENARIO_QUEST_STATE,struct.pack('>ii',100160,3)) in menu or any(
            kind==S_ACCEPT_SCENARIO_QUEST and
            (decode_accept_scenario_quest(body).quest_id,decode_accept_scenario_quest(body).state)==(100160,3)
            for kind,body in menu)
        await peer.request(C_COMMIT_SCENARIO_QUEST,struct.pack('>iQi',100160,key,1))
        assert state(store,role['id'])==before
        command=struct.pack('>iQi',100160,key,0)
        completed=await peer.request(C_COMMIT_SCENARIO_QUEST,command)
        marker=(S_REFRESH_SCENARIO_QUEST_STATE,struct.pack('>ii',100160,1))
        assert completed.count(marker)==1
        current=state(store,role['id'])
        expected=dict(before[0]);expected[100160]='completed'
        assert dict(current[0])==expected and current[1:]==before[1:]
        values=role_values(completed)
        assert tuple(values[k] for k in (490,500,80,810,1230))==(2,5,49,38,8)
        with closing(store.connect()) as db:
            effect=json.loads(db.execute('SELECT payload FROM task_effects WHERE role_id=? AND task_id=100160',
                (role['id'],)).fetchone()[0])
        assert (effect['chain_status'],effect['chain_reason'],effect['chain_target'],effect['chain_resolved'])==(
            'pending','successor_gameplay_unimplemented',100106,False)
        assert marker not in await peer.request(C_COMMIT_SCENARIO_QUEST,command)
        await peer.request(C_COMMIT_SCENARIO_QUEST,struct.pack('>iQi',100106,key,0))
        assert state(store,role['id'])==current
        await peer.connection.close()
        peer=GrowthPeer(runtime);await peer.login(role)
        assert state(store,role['id'])==current and marker not in peer.initial
        assert runtime.roles[role['id']].position.value[0]==1006
        return dict(passed=['natural intro/master/equip/cart/Jiaxing120XP prefix then original-clear report to actual storyteller',
            'original100160 dialogue commits once with option0, zero reward and currentL2/31/free5/49/38/8 preserved',
            'wrong option, repeated dialogue and unauthorized100106 commit mutate no tasks/assets/XP',
            '100106 remains explicitly pending successor_gameplay_unimplemented after reconnect; no dream transfer or battle fabricated'],
            next_missing_task=100106,first_paused_battle_task=100107,database='disposable',
            native_gui_verified=False,live_server_changed=False,battle_executed=False)
    finally:await runtime.close()


def main():
    route=load_newbie_routes()[(9,11)]
    audit=json.loads((OUT/'evidence/newbie-birth-sites-audit.json').read_text(encoding='utf-8'))
    witness=next(r for r in audit['routes'] if (r['character_id'],r['school_id'])==(9,11))
    with tempfile.TemporaryDirectory(prefix='jiaxing-story-boundary-') as directory:
        store=AccountStore(Path(directory)/'state.sqlite3');prepared=runtime_storage.prepare(store)
        role=store.create_role(1111,'说书自然链',11,1010109)
        report=asyncio.run(check(store,prepared,role,route,witness))
    write_json(OUT/'evidence/jiaxing-story-boundary-runtime-verification.json',report);print(report)


if __name__=='__main__':main()
