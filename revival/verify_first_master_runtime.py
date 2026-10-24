"""Natural first-master card, selected weapon and actual equip via owners.

Disposable DB and continuous native connection codecs. Movement reports use a
previously audited clear path; this does not execute client input/pathfinding.
No task offer, manual position, direct item grant, client, live port or battle.
"""
import argparse
import asyncio
from contextlib import closing
import json
from pathlib import Path
import struct
import tempfile

from accounts import AccountStore
from game_runtime import GameRuntime
from inspect_client import OUT,write_json
from inventory import EQUIP_ITEM,UNEQUIP_ITEM,BAG_INFO
from native_gameplay_probe import probe
from task_protocol import (C_COMMIT_SCENARIO_QUEST,S_REFRESH_SCENARIO_QUEST_STATE,
                           S_ACCEPT_SCENARIO_QUEST,decode_accept_scenario_quest)
from verify_growth_runtime import GrowthPeer,role_values
from verify_newbie_runtime import require_opening,movie_frames
from world_card_protocol import S_PLAY_CARD_EFFECT,C_GET_CARD_ITEM
from world_entity_protocol import VISIT_NPC
from world_movement import ROLE_MOVE,ROLE_STOP
from world_newbie import load_newbie_routes,END_PLAY_CG
from wire import compact
from research_first_master_dialogue_end import native_start_completion
from research_task_existing_quest import assert_ready_before_visit
import runtime_storage


class MissingMaster(AssertionError):
    pass


def state(store,role_id):
    with closing(store.connect()) as db:
        tasks=tuple(db.execute('SELECT task_id,state FROM task_journal WHERE role_id=? ORDER BY task_id',(role_id,)))
        items=tuple(db.execute('SELECT id,template_id,quantity,binding,equipment_slot FROM inventory_items '
                              'WHERE role_id=? ORDER BY id',(role_id,)))
        experience=db.execute('SELECT experience FROM role_progress WHERE role_id=?',(role_id,)).fetchone()
    return tasks,items,experience


async def check(store,prepared,role,route,witness):
    runtime=GameRuntime(store,prepared)
    try:
        peer=GrowthPeer(runtime);await peer.login(role)
        require_opening(store,runtime,peer,role,route)
        await peer.request(END_PLAY_CG,struct.pack('>i',route.intro_movie_id))
        expected={route.intro_task_id:'completed',route.successor_task_id:'active'}
        assert dict(state(store,role['id'])[0])==expected
        before=state(store,role['id'])
        choice=struct.pack('>ii',route.successor_card_effect_id,49009)
        await peer.request(C_GET_CARD_ITEM,choice)
        await peer.request(END_PLAY_CG,struct.pack('>i',route.successor_card_effect_id))
        assert state(store,role['id'])==before, 'Unsolicited card or false CG end granted a weapon'
        path=tuple(tuple(point) for point in witness['path'])
        assert path[0]==route.cinematic_endpoint[1:]
        await peer.request(ROLE_MOVE,struct.pack('>hhhhQ',*path[0],*path[-1],0))
        stop=compact(len(path))+b''.join(struct.pack('>hh',*point) for point in path)+struct.pack('>hhQ',*path[-1],0)
        await peer.request(ROLE_STOP,stop)
        assert runtime.roles[role['id']].position.value==(route.home_map_id,*path[-1])
        key=(route.home_map_id<<32)|witness['placement_id']
        menu=await peer.request(VISIT_NPC,struct.pack('>q',key))
        ready=(S_REFRESH_SCENARIO_QUEST_STATE,struct.pack('>ii',route.successor_task_id,3))
        if ready not in menu:
            raise MissingMaster(str(dict(master_task=route.successor_task_id,expected_ready=3,
                actual_reply_types=[hex(kind) for kind,_ in menu],current_tasks=state(store,role['id'])[0])))
        assert_ready_before_visit(menu,route.successor_task_id)
        # Consume the actual phase2 Start output; phase3 DialogEnd is not an
        # event that the real client emits after this three-sentence dialogue.
        native_messages,_,phase=native_start_completion(route.successor_task_id,key)
        assert phase==2 and len(native_messages)==1 and native_messages[0][0]==C_COMMIT_SCENARIO_QUEST
        committed=await peer.request(*native_messages[0])
        assert (S_PLAY_CARD_EFFECT,struct.pack('>i',route.successor_card_effect_id)) in committed
        assert state(store,role['id'])==before, 'Dialogue commit completed the card task early'
        assert state(store,role['id'])==before, 'Showing the card granted a default weapon'
        for body in (choice[:7],choice+b'\0',struct.pack('>ii',route.successor_card_effect_id+1,49009),
                     struct.pack('>ii',route.successor_card_effect_id,40101)):
            await peer.request(C_GET_CARD_ITEM,body)
            assert state(store,role['id'])==before
        _,raw=probe(0xd919d0,0xe4c480,0xd91a70,payload=choice)
        assert struct.unpack_from('<ii',raw,8)==(route.successor_card_effect_id,49009)
        claimed=await peer.request(C_GET_CARD_ITEM,choice)
        after=state(store,role['id'])
        equipment_task=store.task_resources.definitions[route.successor_task_id]['next_ids'][0]
        expected[route.successor_task_id]='completed';expected[equipment_task]='active'
        assert dict(after[0])==expected and len(after[1])==1
        item_key,template,quantity,binding,slot=after[1][0]
        assert (template,quantity,binding,slot)==(49009,1,1,None)
        assert after[2]==(0,) and any(kind==BAG_INFO for kind,_ in claimed)
        for body in (choice,struct.pack('>ii',route.successor_card_effect_id,49006)):
            await peer.request(C_GET_CARD_ITEM,body)
            assert state(store,role['id'])==after, 'Card replay or second button granted another weapon'
        await peer.connection.close()
        peer=GrowthPeer(runtime);await peer.login(role)
        assert not movie_frames(peer.initial) and not any(kind==S_PLAY_CARD_EFFECT for kind,_ in peer.initial)
        assert state(store,role['id'])==after, 'Reconnect auto-equipped or reissued a selected weapon'
        equipped=await peer.request(EQUIP_ITEM,struct.pack('>ii',item_key,0))
        current=state(store,role['id'])
        driver=store.task_resources.definitions[equipment_task]['next_ids'][0]
        expected[equipment_task]='completed';expected[driver]='active'
        assert dict(current[0])==expected and current[1]==((item_key,49009,1,1,0),)
        values=role_values(equipped)
        assert {key:values[key] for key in (80,810,1230)}=={80:45,810:35,1230:8}
        await peer.request(EQUIP_ITEM,struct.pack('>ii',item_key,0))
        assert state(store,role['id'])==current
        removed=await peer.request(UNEQUIP_ITEM,struct.pack('>ii',item_key,0))
        bare=role_values(removed)
        assert {key:bare[key] for key in (80,810,1230)}=={80:20,810:20,1230:0}
        carried=state(store,role['id'])
        assert carried[0]==current[0] and carried[1]==((item_key,49009,1,1,None),)
        assert carried[2]==current[2], 'Unequip changed completed task rewards'
        await peer.request(UNEQUIP_ITEM,struct.pack('>ii',item_key,0))
        assert state(store,role['id'])==carried, 'A fresh invalid unequip changed assets or task state'
        reworn=role_values(await peer.request(EQUIP_ITEM,struct.pack('>ii',item_key,0)))
        assert {key:reworn[key] for key in (80,810,1230)}=={80:45,810:35,1230:8}
        assert state(store,role['id'])==current, 'Re-equip duplicated the completed objective or item'
        await peer.connection.close()
    finally:
        await runtime.close()
    runtime=GameRuntime(store,prepared)
    try:
        peer=GrowthPeer(runtime);await peer.login(role)
        values=role_values(peer.initial)
        assert {key:values[key] for key in (80,810,1230)}=={80:45,810:35,1230:8}
        _,raw=probe(0xfe4160,0xfe45f0,0xfe4630,payload=peer.world_body)
        assert tuple(struct.unpack_from('<i',raw,offset)[0] for offset in (0x70,0x80,0x88))==(45,35,8)
        assert state(store,role['id'])==current
        assert runtime.roles[role['id']].position.value==(route.home_map_id,*path[-1])
    finally:
        await runtime.close()
    return dict(passed=[
        'natural intro then clear-path wire reports reach the original first master',
        'original native Start CCommit authorizes the card with current NPC proof; no synthetic DialogEnd or automatic weapon',
        'one legal native card choice atomically grants one bound original weapon and activates type59',
        'malformed/foreign choice, second-button replay and reconnect cannot duplicate or auto-equip',
        'actual original equip request completes only the received-instance objective and activates its driver',
        'unequip restores current naked20/20/0; invalid repeated removal and re-equip preserve task rewards and one instance',
        'absolute45/35/8 equipment stats and same native entry fields survive runtime reconstruction'],
        database='disposable',native_gui_verified=False,live_server_changed=False,battle_executed=False,
        movement_scope='audited clear native reports, not actual client travel or complete speed enforcement')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--expect-missing',action='store_true')
    args=parser.parse_args()
    routes=load_newbie_routes();route=routes[(9,11)]
    audit=json.loads((OUT/'evidence/newbie-birth-sites-audit.json').read_text(encoding='utf-8'))
    witness=next(row for row in audit['routes'] if (row['character_id'],row['school_id'])==(9,11))
    with tempfile.TemporaryDirectory(prefix='first-master-runtime-') as directory:
        store=AccountStore(Path(directory)/'state.sqlite3');prepared=runtime_storage.prepare(store)
        role=store.create_role(1111,'拜师选武器',11,1010109)
        try:
            result=asyncio.run(check(store,prepared,role,route,witness))
        except MissingMaster as error:
            if not args.expect_missing:
                raise
            result=dict(missing_master_reproduced=True,observation=str(error),database='disposable',
                native_gui_verified=False,live_server_changed=False,battle_executed=False)
        else:
            assert not args.expect_missing, 'Missing first-master feedback no longer reproduces'
    suffix='baseline' if args.expect_missing else 'verification'
    write_json(OUT/f'evidence/first-master-runtime-{suffix}.json',result)
    print(result)


if __name__=='__main__':
    main()
