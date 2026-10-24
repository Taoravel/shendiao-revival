"""Real portal failures recover the durable source or committed target.

Disposable DB, actual owners/codecs, no running listener, GUI or battle. The
fault is either late SQL abort or source-finalize failure after real commit.
"""
import argparse
import asyncio
from contextlib import closing
from pathlib import Path
import sqlite3
import struct
import tempfile
from unittest.mock import patch

from accounts import AccountStore
from game_runtime import GameRuntime
from inspect_client import OUT,write_json
from verify_runtime import Peer
import runtime_storage


def inject(store,enabled):
    with closing(store.connect()) as db,db:
        if enabled:
            db.execute("CREATE TRIGGER transfer_abort_commit BEFORE UPDATE OF stage ON world_handoffs "
                "WHEN NEW.stage='committed' BEGIN SELECT RAISE(ABORT,'controlled transfer commit abort'); END")
        else:
            db.execute('DROP TRIGGER transfer_abort_commit')


async def check(store,prepared,role,expect_stuck,after_commit=False):
    runtime=GameRuntime(store,prepared)
    try:
        peer=Peer(runtime);await peer.login(role)
        current=runtime.roles[role['id']]
        assert await current.io(store.save_checkpoint,1111,role['id'],current.epoch,
            current.position.value,current.position.version)
        with closing(store.connect()) as db:
            source=db.execute('SELECT map_id,x,y FROM role_positions WHERE role_id=?',(role['id'],)).fetchone()
        assert source==current.position.value
        command=b'\0'+struct.pack('>hhQ',8592,7104,0)
        if after_commit:
            # The real durable commit has already succeeded when source
            # finalization executes. Replace only that public fault seam.
            with patch.object(runtime.map(1007).domain,'finalize',
                    side_effect=ValueError('controlled postcommit source finalization')) as finalizer:
                assert await peer.request(0xc0faa,command)==[]
                assert finalizer.call_count==1
            authority=(1014,896,3776);stage='committed'
        else:
            inject(store,True)
            try:
                await peer.request(0xc0faa,command)
            except sqlite3.IntegrityError as error:
                assert 'controlled transfer commit abort' in str(error)
            else:
                raise AssertionError('Controlled late transfer commit failure did not execute')
            inject(store,False)
            authority=source;stage='prepared'
        with closing(store.connect()) as db:
            assert db.execute('SELECT map_id,x,y FROM role_positions WHERE role_id=?',(role['id'],)).fetchone()==authority
            assert db.execute('SELECT stage FROM world_handoffs WHERE role_id=?',(role['id'],)).fetchone()==(stage,)
        owner=runtime.roles[role['id']]
        assert owner.poisoned, 'An uncertain map handoff must fence its old role owner'
        await peer.connection.close()
        peer=Peer(runtime)
        try:
            await peer.login(role)
        except ValueError as error:
            if not expect_stuck:raise
            assert str(error)=='Role already in map', 'A different login failure is not the map-residue baseline'
            locations={str(map_id):{'state':loc.state,'version':loc.version,'epoch':str(loc.login_epoch)}
                for (map_id,_),m in runtime.maps.items()
                if (loc:=m.domain.location(role['id'])) is not None}
            return dict(stuck_reproduced=True,error=str(error),durable_position=authority,
                failure_phase='after_commit' if after_commit else 'before_commit',
                remaining_map_memberships=locations,database='disposable',native_gui_verified=False,
                live_server_changed=False,battle_executed=False)
        assert not expect_stuck, 'Durable-source reconnect is no longer stuck'
        assert runtime.roles[role['id']].position.value==authority
        if after_commit:
            assert runtime.map(1007).domain.location(role['id']) is None
            await peer.request(0xc0fa1,struct.pack('>hhhhQ',896,3776,912,3792,0))
            await peer.request(0xc0faa,b'\0'+struct.pack('>hhQ',912,3792,0))
            assert runtime.roles[role['id']].position.value==(1014,912,3792)
            await peer.connection.close()
            peer=Peer(runtime);await peer.login(role)
            assert runtime.roles[role['id']].position.value==(1014,912,3792)
            await peer.connection.close()
            return dict(passed=['real durable target commit survives source-finalize failure',
                'same-runtime new lease retires both old map memberships and joins target',
                'legal target move and second reconnect preserve a checkpoint newer than the original receipt'],
                database='disposable',native_gui_verified=False,live_server_changed=False,battle_executed=False)
        assert runtime.map(1014).domain.location(role['id']) is None
        # Recovery must permit a new valid transfer, not merely let login pass.
        replies=await peer.request(0xc0faa,b'\0'+struct.pack('>hhQ',8592,7104,0))
        assert any(kind==0xc0fa9 for kind,_ in replies)
        assert runtime.roles[role['id']].position.value==(1014,896,3776)
        await peer.connection.close()
        return dict(passed=['late SQL failure leaves durable source and prepared decision unchanged',
            'old role fenced; reconnect in the same runtime recovers source and retires old target loading',
            'fresh portal handoff succeeds after recovery without restarting the server'],
            database='disposable',native_gui_verified=False,live_server_changed=False,battle_executed=False)
    finally:
        await runtime.close()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--expect-stuck',action='store_true')
    parser.add_argument('--after-commit',action='store_true')
    args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='transfer-failure-recovery-') as directory:
        store=AccountStore(Path(directory)/'state.sqlite3')
        role=store.create_role(1111,'过图故障恢复',12,1010101)
        prepared=runtime_storage.prepare(store)
        report=asyncio.run(check(store,prepared,role,args.expect_stuck,args.after_commit))
    suffix='baseline' if args.expect_stuck else 'verification'
    name='transfer-postcommit-recovery' if args.after_commit else 'transfer-failure-recovery'
    write_json(OUT/f'evidence/{name}-{suffix}.json',report);print(report)


if __name__=='__main__':
    main()
