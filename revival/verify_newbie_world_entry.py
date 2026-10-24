"""Actual owner entry -> intro gate -> walking to the original first NPC.

    All43 new roles use disposable storage and encrypted in-memory peers.
    No live listener, client, battle, manual spawn or trusted quest shortcut.
"""
import asyncio
from contextlib import closing
from pathlib import Path
import struct
import tempfile
from accounts import AccountStore
from game_runtime import GameRuntime
from inspect_client import OUT, write_json
from verify_growth_runtime import GrowthPeer
from world_newbie import load_newbie_routes, END_PLAY_CG, START_PLAY_CG
from world_entity_protocol import VISIT_NPC, VISIT_NPC_REPLY
from world_movement import ROLE_STOP
import runtime_storage


def stop(point):
    return b'\0'+struct.pack('>hhQ',*point,0)


async def check(store,prepared,roles,routes):
    runtime = GameRuntime(store,prepared)
    results = []
    try:
        for key, role in roles:
            route, witness = routes[key], store.newbie_birth_sites[key]
            peer = GrowthPeer(runtime)
            await peer.login(role)
            owner = runtime.roles[role['id']]
            assert owner.newbie_pending and owner.position.value == route.cinematic_endpoint
            assert len(witness.path) > 1
            original = owner.position
            # Valid geometry does not bypass a pending opening authorization.
            await peer.request(ROLE_STOP,stop(witness.path[1]))
            assert owner.position == original
            await peer.request(END_PLAY_CG,struct.pack('>i',route.intro_movie_id))
            assert not owner.newbie_pending
            for point in witness.path[1:]:
                await peer.request(ROLE_STOP,stop(point))
                assert owner.position.value == (route.home_map_id,*point)
            expected = owner.position.value
            placement = next(p for p in store.npc_resources[0][route.home_map_id]
                             if p.placement_id == witness.placement_id)
            npc_key = (route.home_map_id<<32)|placement.placement_id
            replies = await peer.request(VISIT_NPC,struct.pack('>q',npc_key))
            assert any(kind==VISIT_NPC_REPLY and body[:8]==struct.pack('>q',npc_key)
                       for kind,body in replies), 'First NPC was not reachable through its real wire key'
            with closing(store.connect()) as db:
                assert db.execute('SELECT map_id,x,y FROM role_positions WHERE role_id=?',
                                  (role['id'],)).fetchone() == expected
            await peer.connection.close()
            again = GrowthPeer(runtime)
            await again.login(role)
            assert runtime.roles[role['id']].position.value == expected
            assert not runtime.roles[role['id']].newbie_pending
            assert not any(kind==START_PLAY_CG for kind,_ in again.initial)
            await again.connection.close()
            results.append(dict(character_id=key[0],school_id=key[1],
                home_map_id=route.home_map_id,first_npc_id=placement.npc_id,
                movement_reports=len(witness.path)-1,committed_position=expected,
                pending_move_rejected=True,completed_move_accepted=True,
                native_npc_key_reply=True,reconnect_preserved_position=True))
    finally:
        await runtime.close()
    return results


def main():
    routes = load_newbie_routes()
    with tempfile.TemporaryDirectory(prefix='newbie-world-entry-') as directory:
        results = []
        choices = tuple(routes.items())
        # Honor the actual three-character cap. Each disposable account/database
        # starts with the real creation path; no direct role INSERT bypass.
        for offset in range(0,len(choices),3):
            store = AccountStore(Path(directory)/f'state-{offset}.sqlite3')
            prepared = runtime_storage.prepare(store)
            shapes = store.task_resources.shape_to_role_config
            roles = tuple((key,store.create_role(1111,f'出生验证{i}',route.school_id,
                next(shape for shape,character in shapes.items() if character==key[0])))
                for i,(key,route) in enumerate(choices[offset:offset+3],start=offset))
            results.extend(asyncio.run(asyncio.wait_for(check(store,prepared,roles,routes),timeout=120)))
            print(f'checked {len(results)}/43 original routes',flush=True)
    assert len(results) == 43
    report = dict(routes=results,route_count=len(results),
        total_movement_reports=sum(r['movement_reports'] for r in results),
        tested='actual role/map owners, durable creation/chapter, RC4/MPPC peer and NPC wire reply',
        coordinates='native logical pixels; paths already checked against original maze/DDA',
        gui_verified=False,client_input_unlocked_verified=False,
        server_movement_gate_verified=True,shared_runtime_tested=True,
        collision_runtime_enabled=False,database='disposable',
        live_server_changed=False,live_role_changed=False,client_launched=False,battle_executed=False)
    write_json(OUT/'evidence/newbie-world-entry-verification.json',report)
    print({k:report[k] for k in ('route_count','total_movement_reports','server_movement_gate_verified',
                               'shared_runtime_tested','gui_verified','live_server_changed')})


if __name__ == '__main__':
    main()
