"""Natural first-master prefix then original cart branch through real owners.

Disposable database, original encrypted codecs and audited movement reports.
No trusted task offer, manual spawn, direct item grant, live port, GUI or battle.
"""
import argparse
import asyncio
from contextlib import asynccontextmanager
from dataclasses import replace
import json
from pathlib import Path
import struct
import tempfile

from accounts import AccountStore
from game_runtime import GameRuntime
from inspect_client import OUT,write_json
from native_gameplay_probe import probe
from task_protocol import (C_COMMIT_SCENARIO_QUEST,S_ACCEPT_SCENARIO_QUEST,
    S_REFRESH_SCENARIO_QUEST_STATE,decode_accept_scenario_quest)
from verify_first_master_runtime import check as master_prefix,state
from verify_growth_runtime import GrowthPeer,role_values
from wire import compact
from world_catalog import maps,maze_grids
from world_collision import maze_clear,maze_segment_clear
from world_entity_protocol import VISIT_NPC
from world_movement import ROLE_MOVE,ROLE_STOP
from world_newbie import load_newbie_routes,check_birth_site
from world_npcs import load_placements
import runtime_storage


class MissingCart(AssertionError):
    pass


@asynccontextmanager
async def cart_visit(store,prepared,role,route,witness):
    """Natural prefix and current cart authorization for happy/fault feedback."""
    await master_prefix(store,prepared,role,route,witness)
    before=state(store,role['id'])
    driver=next(task for task,status in before[0] if status=='active')
    definition=store.task_resources.definitions[driver]
    # Reuse the bounded native-clear witness search for this actual NPC leg.
    candidate=replace(route,first_npc_id=definition['target']['npc_id'],
        cinematic_endpoint=(route.home_map_id,*witness['path'][-1]))
    walk=check_birth_site(candidate,maps(),maze_grids()[route.home_map_id],load_placements()[route.home_map_id],
        state_byte=0,interaction_radius=32,max_visited=100000)
    assert walk.status=='reachable', ('No clear cart movement witness',walk)
    path=walk.path
    runtime=GameRuntime(store,prepared)
    try:
        peer=GrowthPeer(runtime);await peer.login(role)
        assert runtime.roles[role['id']].position.value==candidate.cinematic_endpoint
        await peer.request(ROLE_MOVE,struct.pack('>hhhhQ',*path[0],*path[-1],0))
        body=compact(len(path))+b''.join(struct.pack('>hh',*point) for point in path)+struct.pack('>hhQ',*path[-1],0)
        await peer.request(ROLE_STOP,body)
        owner=runtime.roles[role['id']]
        assert owner.position.value==(route.home_map_id,*path[-1])
        key=(route.home_map_id<<32)|walk.placement_id
        menu=await peer.request(VISIT_NPC,struct.pack('>q',key))
        ready=(S_REFRESH_SCENARIO_QUEST_STATE,struct.pack('>ii',driver,3))
        ready_bean=any(kind==S_ACCEPT_SCENARIO_QUEST and
            (decode_accept_scenario_quest(payload).quest_id,decode_accept_scenario_quest(payload).state)==(driver,3)
            for kind,payload in menu)
        if ready not in menu and not ready_bean:
            raise MissingCart(str(dict(cart_task=driver,expected_ready=3,
                actual_reply_types=[hex(kind) for kind,_ in menu],current_tasks=state(store,role['id'])[0])))
        yield runtime,peer,owner,driver,key,definition,before
    finally:
        await runtime.close()


async def check(store,prepared,role,route,witness):
    async with cart_visit(store,prepared,role,route,witness) as visit:
        runtime,peer,owner,driver,key,definition,before=visit
        replies=await peer.request(C_COMMIT_SCENARIO_QUEST,struct.pack('>iQi',driver,key,0))
        a=definition['attributes']
        target=(int(a['RewardMapID']),int(a['RewardMapXPos'])*16,int(a['RewardMapYPos'])*16)
        if owner.position.value!=target:
            raise MissingCart(str(dict(cart_task=driver,expected_target=target,actual_target=owner.position.value)))
        scenes=[payload for kind,payload in replies if kind==0xc0fa9]
        assert len(scenes)==1, 'Cart must emit one target scene entry'
        _,native=probe(0xdac580,0xe50b00,0xf74260,payload=scenes[0])
        assert struct.unpack_from('<hh',native,0x28)==target[1:]
        assert struct.unpack_from('<Q',native,0x38)[0]==target[0]
        assert struct.unpack_from('<i',native,0x30)[0]==0
        assert owner.transfer is None, 'Actual connection send barrier did not finish scene loading'
        assert runtime.map(route.home_map_id).domain.location(role['id']) is None
        assert runtime.map(target[0]).domain.location(role['id']).state=='active'
        expected=dict(before[0]);expected[driver]='completed';expected[definition['next_ids'][0]]='active'
        assert dict(state(store,role['id'])[0])==expected
        assert state(store,role['id'])[1]==before[1], 'Cart duplicated or changed the received weapon'
        committed=state(store,role['id'])
        await peer.request(C_COMMIT_SCENARIO_QUEST,struct.pack('>iQi',driver,key,0))
        assert state(store,role['id'])==committed, 'Duplicate cart choice changed rewards or tasks'
        grid=maze_grids()[target[0]]
        nearby=next((target[1]+dx,target[2]+dy) for dx,dy in ((16,0),(0,16),(-16,0),(0,-16))
            if maze_clear(grid,target[1]+dx,target[2]+dy,mask=1)
            and maze_segment_clear(grid,target[1:],(target[1]+dx,target[2]+dy),mask=1))
        await peer.request(ROLE_MOVE,struct.pack('>hhhhQ',*target[1:],*nearby,0))
        await peer.request(ROLE_STOP,compact(1)+struct.pack('>hh',*nearby)+struct.pack('>hhQ',*nearby,0))
        arrived=(target[0],*nearby)
        assert owner.position.value==arrived, 'Valid native movement after the cart scene barrier was rejected'
        await peer.connection.close()
        peer=GrowthPeer(runtime);await peer.login(role)
        assert runtime.roles[role['id']].position.value==arrived
        assert state(store,role['id'])==committed
        values=role_values(peer.initial)
        assert tuple(values[k] for k in (80,810,1230))==(45,35,8)
        return dict(passed=['natural intro/card/received weapon/equip prefix',
            'clear native movement reports reach original cart and authorize original option0',
            'cart completion and unique successor follow designed Jiaxing target',
            'original scene decoder confirms target; exact connection send barrier clears source and activates target',
            'legal target movement continues and reconnect preserves its later checkpoint',
            'duplicate choice and reconnect preserve tasks, weapon and current attributes'],
            database='disposable',native_gui_verified=False,live_server_changed=False,battle_executed=False,
            movement_scope='native-clear witness reports; client travel and full speed enforcement unverified')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--expect-missing',action='store_true')
    args=parser.parse_args();route=load_newbie_routes()[(9,11)]
    audit=json.loads((OUT/'evidence/newbie-birth-sites-audit.json').read_text(encoding='utf-8'))
    witness=next(row for row in audit['routes'] if (row['character_id'],row['school_id'])==(9,11))
    with tempfile.TemporaryDirectory(prefix='newbie-cart-runtime-') as directory:
        store=AccountStore(Path(directory)/'state.sqlite3');prepared=runtime_storage.prepare(store)
        role=store.create_role(1111,'自然车夫接线',11,1010109)
        try:
            result=asyncio.run(check(store,prepared,role,route,witness))
        except MissingCart as error:
            if not args.expect_missing:raise
            result=dict(missing_cart_reproduced=True,observation=str(error),database='disposable',
                native_gui_verified=False,live_server_changed=False,battle_executed=False)
        else:
            assert not args.expect_missing, 'Missing cart feedback no longer reproduces'
    suffix='baseline' if args.expect_missing else 'verification'
    write_json(OUT/f'evidence/newbie-cart-runtime-{suffix}.json',result);print(result)


if __name__=='__main__':
    main()
