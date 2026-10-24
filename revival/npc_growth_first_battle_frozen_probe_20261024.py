"""Natural low-level progression to the first missing quest battle.

Run a frozen release in a new disposable database through its real encrypted
Peer/Owners. Never start its listener, touch a live save or enable a battle.
Default exits red unless the original NPC offers the current quest and its
dedicated native request really starts a bound battle. --expect-missing records
the present gap without calling that gap a passing gameplay result.
"""
import argparse
import asyncio
from contextlib import closing
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--expect-missing',action='store_true')
    args=parser.parse_args()
    source=args.source.resolve();report=args.report.resolve()
    if source in report.parents or not (source/'game_runtime.py').is_file():
        raise ValueError('Use a frozen source and a report outside that source')
    names=('game_runtime.py','runtime_storage.py','task_domain.py','task_conversation.py',
        'task_chains.py','task_prologue_touch.py','accounts.py')
    before={name:digest(source/name) for name in names}
    sys.path.insert(0,str(source))
    import inspect_client
    inspect_client.ROOT=Path(__file__).resolve().parents[1]
    inspect_client.OUT=source
    from accounts import AccountStore
    from game_runtime import GameRuntime
    import runtime_storage
    from verify_runtime import Peer
    from verify_prologue_touch_runtime import check as bloodmark_prefix
    from verify_master_commit_card_runtime import check as native_master_prefix
    import verify_master_commit_card_runtime
    import verify_newbie_cart_runtime
    from world_newbie import load_newbie_routes,check_birth_site
    from world_catalog import maps,maze_grids
    from world_entity_protocol import VISIT_NPC
    from world_movement import ROLE_MOVE,ROLE_STOP
    from task_dialog_protocol import S_VISIT_NPC,decode_visit_npc
    from task_persistence import load_task_state
    from wire import compact
    for name in names:
        module=sys.modules.get(Path(name).stem)
        if module is None or Path(module.__file__).resolve().parent!=source:
            raise AssertionError('Gameplay source overlay: '+name)
    # The historical cart harness waited for a synthetic DialogEnd. Only its
    # test prefix is replaced; every gameplay Module stays in the exact release.
    verify_newbie_cart_runtime.master_prefix=native_master_prefix
    helper=Path(verify_master_commit_card_runtime.__file__).resolve()
    helper_sha=digest(helper)
    route=load_newbie_routes()[(9,11)]
    audit=json.loads((source/'evidence/newbie-birth-sites-audit.json').read_text(encoding='utf-8'))
    witness=next(row for row in audit['routes'] if (row['character_id'],row['school_id'])==(9,11))

    async def run(store,prepared,role):
        prefix=await bloodmark_prefix(store,prepared,role,route,witness)
        runtime=GameRuntime(store,prepared,prologue_touch=True)
        try:
            peer=Peer(runtime);await peer.login(role)
            owner=runtime.roles[role['id']]
            address=owner.map_address
            task=store.task_resources.definitions[100107]
            target=task['target']
            assert (target['map_id'],target['npc_id'])==(1501,10908),target
            walk=check_birth_site(replace(route,home_map_id=1501,first_npc_id=10908,
                cinematic_endpoint=owner.position.value),maps(),maze_grids()[1501],
                store.npc_resources[0][1501],state_byte=0,
                interaction_allowed=store.npc_interaction_rules.allows,max_visited=100000)
            assert walk.status=='reachable',walk
            path=walk.path
            await peer.request(ROLE_MOVE,struct.pack('>hhhhQ',*path[0],*path[-1],0))
            await peer.request(ROLE_STOP,compact(len(path))+b''.join(struct.pack('>hh',*p) for p in path)
                +struct.pack('>hhQ',*path[-1],0))
            assert owner.map_address==address and owner.position.value==(1501,*path[-1])
            key=(1501<<32)|walk.placement_id
            with closing(store.leased(1111,role['id'],owner.epoch).connect()) as db:
                db.execute('BEGIN')
                actor,state=load_task_state(db,1111,role['id'],owner.epoch)
                assert 100107 in state.active and 100106 in state.completed and actor.level==2
                tables=tuple(row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'"))
            menu=await peer.request(VISIT_NPC,struct.pack('>q',key))
            decoded=[decode_visit_npc(body) for kind,body in menu if kind==S_VISIT_NPC]
            offered=any(100107 in row[2] for row in decoded)
            # Actual original CActiveScenarioQuestAIBattle, not CCommit and not
            # an inbound victory. It cannot itself complete any task.
            reply=await peer.request(0xc4a4c,struct.pack('>iQ',100107,key))
            started=owner.battle is not None
            with closing(store.leased(1111,role['id'],owner.epoch).connect()) as db:
                db.execute('BEGIN')
                _,after=load_task_state(db,1111,role['id'],owner.epoch)
                rows=list(db.execute('SELECT task_id,phase FROM task_battle_admissions WHERE role_id=?',
                    (role['id'],))) if 'task_battle_admissions' in tables else []
            return dict(natural_prefix=prefix,level=actor.level,task_id=100107,
                private_map_id=address.map_id,private_instance=address.instance_id,
                npc_id=10908,npc_placement_id=walk.placement_id,npc_key=key,
                approach_position=owner.position.value,approach_clear_report_witness=True,
                menu_reply_types=[hex(kind) for kind,_ in menu],decoded_task_menus=decoded,
                original_task_offered=offered,native_request_type='0xc4a4c',
                native_request_body=struct.pack('>iQ',100107,key).hex(),
                request_reply_types=[hex(kind) for kind,_ in reply],
                battle_admissions_table_prepared='task_battle_admissions' in tables,
                durable_admissions=rows,battle_started=started,
                task_still_active=100107 in after.active,
                task_completed=100107 in after.completed,
                first_battle_available=offered and started and bool(rows))
        finally:
            await runtime.close()

    with tempfile.TemporaryDirectory(prefix='growth-first-battle-') as directory:
        store=AccountStore(Path(directory)/'disposable.sqlite3')
        prepared=runtime_storage.prepare(store)
        role=store.create_role(1111,'成长第一战反馈',11,1010109)
        result=asyncio.run(asyncio.wait_for(run(store,prepared,role),90))
    assert before=={name:digest(source/name) for name in names}
    assert digest(helper)==helper_sha
    result.update(source=str(source),source_sha256=before,source_unchanged=True,
        harness_prefix_helper=dict(path=str(helper),sha256=helper_sha),
        methods=['diagnosing-bugs: real frozen natural creation-to-private-NPC red-capable feedback',
            'codebase-design: existing role/map/connection Interfaces; no production writer'],
        database='new disposable only',live_database_opened=False,listener_started=False,
        live_server_changed=False,client_operated=False,native_gui_verified=False,
        battle_capability_enabled_by_probe=False,
        limitations=['Movement reports are original-clear witnesses, not GUI pathfinding',
            'No real AI/roster, fabricated terminal event or task skip'])
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('level','task_id','original_task_offered',
        'battle_admissions_table_prepared','battle_started','task_still_active','first_battle_available')},
        ensure_ascii=False))
    if args.expect_missing:
        assert not result['first_battle_available'],'Gap no longer reproduces'
    else:
        assert result['first_battle_available'], 'Level2 dream storyteller does not start original task battle'


if __name__=='__main__':main()
