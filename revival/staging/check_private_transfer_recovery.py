"""Frozen candidate: actual failed transfer transaction/finalize -> new-lease recovery."""
import argparse
import asyncio
from contextlib import closing
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]


async def scenario(store,prepared,route,witness,*,failure):
    from game_runtime import GameRuntime
    from verify_runtime import Peer
    from verify_jiaxing_story_boundary_runtime import check as prefix
    from task_protocol import C_COMMIT_SCENARIO_QUEST
    from task_persistence import load_task_state
    from world_entity_protocol import VISIT_NPC
    import runtime_storage
    role=store.create_role(1111,'转场故障'+('甲' if failure=='sql' else '乙'),11,1010109)
    await prefix(store,prepared,role,route,witness)
    npc=next(p for p in store.npc_resources[0][1006] if (p.placement_id,p.npc_id)==(13,10498))
    epoch=store.acquire_lease(1111,role['id'])
    assert store.save_checkpoint(1111,role['id'],epoch,(1006,npc.x,npc.y),store.position_version(role['id'])+1)
    store.release_lease(role['id'],epoch)
    clock=[1000]
    runtime=GameRuntime(store,prepared,prologue_touch=True,story_clock=lambda:clock[0])
    try:
        peer=Peer(runtime);await peer.login(role)
        owner=runtime.roles[role['id']]
        public=owner.map_address
        key=(1006<<32)|13
        await peer.request(VISIT_NPC,struct.pack('>q',key))
        await asyncio.sleep(3.05)
        old_level,old_exp=owner.role['level'],owner.role['experience']
        if failure=='sql':
            def failed_encode(*args,**kwargs):
                raise ValueError('Controlled final native scene encoding failure inside transaction')
            guard=patch.object(runtime_storage,'scene_entry',failed_encode)
        else:
            source=runtime.registered_map(public)
            handler=source.mailbox.handler
            async def failed_finalize(command):
                if command.operation=='finalize':
                    raise ValueError('Controlled source finalization refusal after durable commit')
                return await handler(command)
            guard=patch.object(source.mailbox,'handler',failed_finalize)
        with guard:
            assert await peer.request(C_COMMIT_SCENARIO_QUEST,struct.pack('>iQi',100106,key,0))==[]
        assert owner.poisoned
        with closing(store.leased(1111,role['id'],owner.epoch).connect()) as db:
            db.execute('BEGIN')
            state=load_task_state(db,1111,role['id'],owner.epoch)[1]
            stages=tuple(db.execute('SELECT stage FROM world_handoffs WHERE role_id=? ORDER BY rowid',(role['id'],)))
        assert (100106 in state.completed)==(failure=='finalize')
        assert (100107 in state.active)==(failure=='finalize')
        assert stages[-1]==(('committed',) if failure=='finalize' else ('prepared',)),stages
        private=next(address for address in runtime.maps if address.instance_id>=2**62)
        await peer.connection.close()
        replacement=Peer(runtime);await replacement.login(role)
        current=runtime.roles[role['id']]
        assert current.epoch!=owner.epoch and not current.poisoned
        assert (current.role['level'],current.role['experience'])==(old_level,old_exp)
        expected=private if failure=='finalize' else public
        assert current.map_address==expected and current.transfer is None and current.battle is None
        with closing(store.leased(1111,role['id'],current.epoch).connect()) as db:
            db.execute('BEGIN')
            recovered=load_task_state(db,1111,role['id'],current.epoch)[1]
        assert (100106 in recovered.completed)==(failure=='finalize')
        assert (100106 in recovered.active)==(failure=='sql')
        for address in (public,private):
            target=runtime.registered_map(address)
            view=await target.mailbox.call('inspect_transfer',role['id'],
                next(iter((await _handoff_ids(store,role['id'])))))
            assert view.incoming is view.departure is None,view
        assert await replacement.request(100,b'recv')==[(100,b'recv')]
        return dict(failure=failure,new_lease=True,current_address_restored=True,
            expected_authority='committed_private_target' if failure=='finalize' else 'uncommitted_public_source',
            task_completion_once=True,old_membership_receipts_retired=True,no_battle=True)
    finally:
        await runtime.close()


async def _handoff_ids(store,role_id):
    with closing(store.connect()) as db:
        return tuple(row[0] for row in db.execute(
            'SELECT transfer_id FROM world_handoffs WHERE role_id=? ORDER BY rowid DESC',(role_id,)))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--candidate-record',type=Path,default=ROOT/'staging/private-story-candidate.json')
    args=parser.parse_args()
    record=json.loads(args.candidate_record.read_text(encoding='utf-8'))
    release=Path(record['release']);source=release/'source';harness=release/'harness'
    manifest=json.loads((release/'manifest.json').read_text(encoding='utf-8'))
    def verify():
        for name,value in manifest['sha256'].items():
            assert hashlib.sha256((source/name).read_bytes()).hexdigest()==value,name
        for name,value in record['workspace_sha256'].items():
            assert hashlib.sha256((harness/'workspace'/name).read_bytes()).hexdigest()==value,name
        for name,value in record['harness_sha256'].items():
            assert hashlib.sha256((harness/name).read_bytes()).hexdigest()==value,name
    verify();sys.path[:0]=[str(harness),str(source)]
    import inspect_client
    inspect_client.ROOT=ROOT.parent;inspect_client.OUT=harness/'workspace'
    from accounts import AccountStore
    import runtime_storage
    from world_newbie import load_newbie_routes
    route=load_newbie_routes()[(9,11)]
    audit=json.loads((inspect_client.OUT/'evidence/newbie-birth-sites-audit.json').read_text(encoding='utf-8'))
    witness=next(row for row in audit['routes'] if (row['character_id'],row['school_id'])==(9,11))
    async def run(folder):
        rows=[]
        for failure in ('sql','finalize'):
            store=AccountStore(Path(folder)/(failure+'.sqlite3'))
            rows.append(await scenario(store,runtime_storage.prepare(store),route,witness,failure=failure))
        return rows
    with tempfile.TemporaryDirectory(prefix='private-transfer-recovery-') as folder:
        rows=asyncio.run(asyncio.wait_for(run(folder),90))
    verify()
    result=dict(passed=rows,production_inputs=len(manifest['sha256']),
        scenario_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        exact_candidate=str(source),initial_npc_approach_fixture=True,
        live_server_changed=False,real_database_opened=False,native_gui_verified=False)
    (release/'checks/private-transfer-recovery-extra.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))


if __name__=='__main__':main()
