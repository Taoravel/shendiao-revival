"""Natural creation through cart, Jiaxing title task and first earned growth.

No trusted task offer, manual spawn or grant; movement is native-clear report
fixtures, not real client walking. Disposable DB, no listener, GUI or battle.
"""
import argparse
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
from native_gameplay_probe import probe
from task_protocol import (C_COMMIT_SCENARIO_QUEST,C_QUEST_DIALOG_END,S_ACCEPT_SCENARIO_QUEST,
    S_REFRESH_SCENARIO_QUEST_STATE,decode_accept_scenario_quest)
from verify_first_master_runtime import state
from verify_growth_runtime import GrowthPeer,role_values
from verify_newbie_cart_runtime import check as cart_prefix
from wire import compact
from world_catalog import maps,maze_grids
from world_entity_protocol import VISIT_NPC
from world_movement import ROLE_MOVE,ROLE_STOP
from world_newbie import load_newbie_routes,check_birth_site
from world_npcs import load_placements
import runtime_storage


class MissingJiaxing(AssertionError):
    pass


async def check(store,prepared,role,route,witness):
    await cart_prefix(store,prepared,role,route,witness)
    before=state(store,role['id'])
    title=next(q for q,status in before[0] if status=='active')
    task=store.task_resources.definitions[title]
    assert int(task['attributes']['ScenarioInfoAnimationID'])==60001
    assert task['display_rewards']['ExpReward']==120 and before[2]==(0,)
    source=store.position(1111,role['id'])
    candidate=replace(route,home_map_id=source[0],first_npc_id=task['target']['npc_id'],cinematic_endpoint=source)
    walk=check_birth_site(candidate,maps(),maze_grids()[source[0]],load_placements()[source[0]],
        state_byte=0,interaction_radius=32,max_visited=100000)
    assert walk.status=='reachable', ('No clear Jiaxing NPC witness',walk)
    runtime=GameRuntime(store,prepared)
    try:
        peer=GrowthPeer(runtime);await peer.login(role)
        path=walk.path
        await peer.request(ROLE_MOVE,struct.pack('>hhhhQ',*path[0],*path[-1],0))
        await peer.request(ROLE_STOP,compact(len(path))+b''.join(struct.pack('>hh',*p) for p in path)
            +struct.pack('>hhQ',*path[-1],0))
        owner=runtime.roles[role['id']]
        assert owner.position.value==(source[0],*path[-1])
        key=(source[0]<<32)|walk.placement_id
        menu=await peer.request(VISIT_NPC,struct.pack('>q',key))
        ready=(S_REFRESH_SCENARIO_QUEST_STATE,struct.pack('>ii',title,3))
        if ready not in menu and not any(kind==S_ACCEPT_SCENARIO_QUEST and
                (decode_accept_scenario_quest(body).quest_id,decode_accept_scenario_quest(body).state)==(title,3)
                for kind,body in menu):
            raise MissingJiaxing(str(dict(task=title,expected_ready=3,reply_types=[hex(k) for k,_ in menu])))
        assert await peer.request(C_QUEST_DIALOG_END,struct.pack('>i',title))==[]
        assert state(store,role['id'])==before
        command=struct.pack('>iQi',title,key,0)
        completed=await peer.request(C_COMMIT_SCENARIO_QUEST,command)
        expected=dict(before[0]);expected[title]='completed'
        for successor in task['next_ids']:expected[successor]='active'
        current=state(store,role['id'])
        assert dict(current[0])==expected and current[1]==before[1] and current[2]==(31,)
        marker=(S_REFRESH_SCENARIO_QUEST_STATE,struct.pack('>ii',title,1))
        assert completed.count(marker)==1, 'Native title display must be delegated by one original state1'
        assert not any(kind in (0xc0017,0xc001c) for kind,_ in completed), 'Local title became CG or weapon card'
        values=role_values(completed)
        assert tuple(values[k] for k in (490,500,80,810,1230,140,150))==(2,5,49,38,8,110,106)
        duplicate=await peer.request(C_COMMIT_SCENARIO_QUEST,command)
        assert marker not in duplicate and state(store,role['id'])==current
        with closing(store.connect()) as db:
            effect=json.loads(db.execute('SELECT payload FROM task_effects WHERE role_id=? AND task_id=?',
                (role['id'],title)).fetchone()[0])
        assert effect['native_completion_effect']['id']==60001
        assert effect['native_completion_effect']['gui_confirmed'] is False
        await peer.connection.close()
        peer=GrowthPeer(runtime);await peer.login(role)
        assert state(store,role['id'])==current and marker not in peer.initial
        restored=role_values(peer.initial)
        assert tuple(restored[k] for k in (490,500,80,810,1230))==(2,5,49,38,8)
        _,native=probe(0xfe4160,0xfe45f0,0xfe4630,payload=peer.world_body)
        assert struct.unpack_from('<i',native,0x34)[0]==2
        assert tuple(struct.unpack_from('<i',native,o)[0] for o in (0x70,0x80,0x88))==(49,38,8)
        return dict(passed=['natural intro/master/card/equip/cart prefix and clear native reports to actual Jiaxing NPC',
            'original60001 local-title task completes only on valid NPC commit and emits one state1',
            'original120XP naturally earnslevel2/XP31/free5 while worn totals become49/38/8',
            'received weapon remains unique; duplicate/reconnect grant no XP/points or title replay',
            'native entry and current full map retain earned level and equipped growth'],
            database='disposable',native_gui_verified=False,live_server_changed=False,battle_executed=False)
    finally:
        await runtime.close()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--expect-missing',action='store_true')
    args=parser.parse_args();route=load_newbie_routes()[(9,11)]
    audit=json.loads((OUT/'evidence/newbie-birth-sites-audit.json').read_text(encoding='utf-8'))
    witness=next(r for r in audit['routes'] if (r['character_id'],r['school_id'])==(9,11))
    with tempfile.TemporaryDirectory(prefix='newbie-jiaxing-') as directory:
        store=AccountStore(Path(directory)/'state.sqlite3');prepared=runtime_storage.prepare(store)
        role=store.create_role(1111,'自然嘉兴成长',11,1010109)
        try:report=asyncio.run(check(store,prepared,role,route,witness))
        except MissingJiaxing as error:
            if not args.expect_missing:raise
            report=dict(missing_jiaxing_reproduced=True,observation=str(error),database='disposable',
                native_gui_verified=False,live_server_changed=False,battle_executed=False)
        else:assert not args.expect_missing, 'Jiaxing missing feedback does not reproduce'
    suffix='baseline' if args.expect_missing else 'verification'
    write_json(OUT/f'evidence/newbie-jiaxing-runtime-{suffix}.json',report);print(report)


if __name__=='__main__':main()
