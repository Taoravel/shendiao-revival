"""Natural opening-to-bloodmark via actual owners; explicit source activation.

Original-clear movement reports are witnesses, not a native navigation/GUI run.
The original type40 successor remains active and no battle is executed.
"""
import asyncio
import argparse
from contextlib import closing
from dataclasses import replace
import json
from pathlib import Path
import struct
import tempfile
from accounts import AccountStore
from game_runtime import GameRuntime
from inspect_client import OUT,write_json
from task_protocol import C_COMMIT_SCENARIO_QUEST,S_REFRESH_SCENARIO_QUEST_STATE
from task_persistence import load_task_state
from verify_runtime import Peer
from verify_jiaxing_story_boundary_runtime import check as natural_boundary
from world_catalog import maps,maze_grids
from world_entity_protocol import VISIT_NPC
from world_movement import ROLE_MOVE,ROLE_STOP
from world_newbie import load_newbie_routes,check_birth_site
from world_npcs import load_placements
from world_transfer_storage import load_map_instance_transaction
from wire import compact
import runtime_storage


async def check(store,prepared,role,route,witness,*,approach_fixture=False):
    await natural_boundary(store,prepared,role,route,witness)
    if approach_fixture:
        npc=next(p for p in load_placements()[1006] if p.placement_id==13 and p.npc_id==10498)
        epoch=store.acquire_lease(1111,role['id'])
        assert store.save_checkpoint(1111,role['id'],epoch,(1006,npc.x,npc.y),store.position_version(role['id'])+1)
        store.release_lease(role['id'],epoch)
    runtime=GameRuntime(store,prepared,prologue_touch=True)
    try:
        peer=Peer(runtime);await peer.login(role)
        owner=runtime.roles[role['id']]
        _,state=await owner.io(runtime_storage.task_state,store,1111,role['id'],owner.epoch)
        assert 100106 in state.active, 'Explicit shared prologue consumer did not recover the real pending bloodmark edge'
        source=owner.position.value
        task=store.task_resources.definitions[100106]
        if not approach_fixture:
            walk=check_birth_site(replace(route,home_map_id=1006,first_npc_id=10498,cinematic_endpoint=source),
                maps(),maze_grids()[1006],tuple(p for p in load_placements()[1006] if p.placement_id==13),
                state_byte=0,interaction_allowed=store.npc_interaction_rules.allows,max_visited=100000)
            assert walk.status=='reachable' and walk.placement_id==13,walk
            path=walk.path
            await peer.request(ROLE_MOVE,struct.pack('>hhhhQ',*path[0],*path[-1],0))
            await peer.request(ROLE_STOP,compact(len(path))+b''.join(struct.pack('>hh',*p) for p in path)
                +struct.pack('>hhQ',*path[-1],0))
        approached=owner.position.value
        original_npc=next(p for p in store.npc_resources[0][1006] if p.placement_id==13 and p.npc_id==10498)
        approach_distance_squared=(approached[1]-original_npc.x)**2+(approached[2]-original_npc.y)**2
        key=(1006<<32)|13
        menu=await peer.request(VISIT_NPC,struct.pack('>q',key))
        assert (S_REFRESH_SCENARIO_QUEST_STATE,struct.pack('>ii',100106,3)) in menu, 'Shared visit did not open the original bloodmark progress menu'
        command=struct.pack('>iQi',100106,key,0)
        assert await peer.request(C_COMMIT_SCENARIO_QUEST,command)==[], 'Premature original commit bypassed the designed clock'
        await asyncio.sleep(3.05)
        replies=await peer.request(C_COMMIT_SCENARIO_QUEST,command)
        assert any(kind==0xc0fa9 for kind,body in replies), 'Mature bloodmark did not produce the exact private scene handoff'
        assert owner.position.value==(1501,1008,1264) and owner.battle is None
        with closing(store.leased(1111,role['id'],owner.epoch).connect()) as db,db:
            db.execute('BEGIN')
            checkpoint=load_map_instance_transaction(db,1111,role['id'],owner.epoch)
            _,state=load_task_state(db,1111,role['id'],owner.epoch)
            assert 100106 in state.completed and 100107 in state.active
            assert checkpoint.address.map_id==1501 and 2**62<=checkpoint.address.instance_id<2**63
        assert owner.map_address==checkpoint.address and owner.transfer is None
        await peer.connection.close();peer=Peer(runtime);await peer.login(role)
        owner=runtime.roles[role['id']]
        assert owner.map_address==checkpoint.address and owner.position.value==checkpoint.position
        assert owner.battle is None
        return dict(passed=['natural intro/master/weapon/equip/cart/Jiaxing/storyteller prefix',
            'explicit pending-edge recovery and actual original progress menu, premature reject then mature commit',
            'target address, handoff, zero reward task and original paused battle successor commit atomically',
            'exact scene send barrier and reconnect preserve private target; no battle executed'],
            movement='original-clear report witnesses; native travel/GUI unverified',
            natural_origins=1,initial_npc_approach_fixture=approach_fixture,
            natural_bloodmark_approach_verified=not approach_fixture,
            interaction_policy=store.npc_interaction_rules.revision,
            bloodmark_approach_position=approached,bloodmark_approach_distance_squared=approach_distance_squared,
            battle_executed=False,native_gui_verified=False,live_server_changed=False)
    finally:await runtime.close()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--approach-fixture',action='store_true')
    args=parser.parse_args()
    route=load_newbie_routes()[(9,11)]
    audit=json.loads((OUT/'evidence/newbie-birth-sites-audit.json').read_text(encoding='utf-8'))
    witness=next(r for r in audit['routes'] if (r['character_id'],r['school_id'])==(9,11))
    with tempfile.TemporaryDirectory(prefix='prologue-touch-runtime-') as directory:
        store=AccountStore(Path(directory)/'state.sqlite3');prepared=runtime_storage.prepare(store)
        role=store.create_role(1111,'血印自然链',11,1010109)
        result=asyncio.run(asyncio.wait_for(check(store,prepared,role,route,witness,approach_fixture=args.approach_fixture),60))
    name='prologue-touch-runtime-approach-fixture.json' if args.approach_fixture else 'prologue-touch-runtime-verification.json'
    write_json(OUT/'evidence'/name,result);print(result)


if __name__=='__main__':main()
