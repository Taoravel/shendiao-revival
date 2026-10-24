"""A rejected/idempotent map join cannot revoke an already playable member.

Real encrypted legacy Peer and map mailbox; only the initial temporary
checkpoint is a fixture. No manufactured movement declaration or binding.
"""
import argparse
import asyncio
from dataclasses import replace
from pathlib import Path
import struct
import tempfile
from accounts import AccountStore
from game_runtime import GameRuntime
from inspect_client import OUT,write_json
import runtime_storage
from verify_world_resource_runtime import MapPeer,checkpoint_fixture


async def check(store,prepared,role,case):
    checkpoint_fixture(store,role,(1006,360,2264))
    runtime=GameRuntime(store,prepared)
    try:
        peer=MapPeer(runtime);await peer.login(role)
        owner=runtime.roles[role['id']];before=owner.position
        target=runtime.map(owner.map_address)
        if case=='duplicate':
            joined=await target.mailbox.call('join',before)
            if joined!=before:raise AssertionError('Idempotent join changed current position')
        else:
            try:await target.mailbox.call('join',replace(before,version=before.version+1))
            except ValueError:pass
            else:raise AssertionError('Conflicting join replaced current map membership')
        # This must cross the real dispatch/map/context path. Reading a cached
        # Position alone would miss prior movement.leave() side effects.
        await peer.request(0xc0faa,b'\0'+struct.pack('>hhQ',361,2264,1006))
        if owner.position.value!=(1006,361,2264) or owner.position.version<=before.version:
            raise AssertionError(case+' join revoked the current playable member')
        if await peer.request(100,b'join')!=[(100,b'join')]:raise AssertionError('Healthy member lost connection')
        return dict(case=case,original_member_still_playable=True,real_encrypted_peer=True)
    finally:await runtime.close()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--case',choices=('all','duplicate','conflict'),default='all')
    args=parser.parse_args();results=[]
    for case in ('duplicate','conflict') if args.case=='all' else (args.case,):
        with tempfile.TemporaryDirectory(prefix='member-join-admission-') as directory:
            store=AccountStore(Path(directory)/'state.sqlite3')
            role=store.create_role(1111,'地图入场保留',11,1010109)
            results.append(asyncio.run(asyncio.wait_for(check(store,runtime_storage.prepare(store),role,case),30)))
    report=dict(cases=results,live_database_accessed=False,live_service_changed=False,
        native_gui_verified=False,battle_executed=False)
    write_json(OUT/'evidence/runtime-member-join-admission-verification.json',report);print(report)


if __name__=='__main__':main()
