"""Actual early first-world ACK may revoke a scene while its drain is pending.

A genuine current intro supersedes the old declaration; its late successful
drain must not install state or kill the replacement cinematic connection.
"""
import asyncio
from pathlib import Path
import struct
import tempfile
from accounts import AccountStore
from game_runtime import GameRuntime
from inspect_client import OUT,write_json
import runtime_storage
from verify_runtime_movement_lifecycle import GatedPeer,GatedWriter
from world_newbie import END_PLAY_CG,START_PLAY_CG,load_newbie_routes
from wire import frame


async def check(store,prepared,role):
    runtime=GameRuntime(store,prepared)
    peer=GatedPeer(runtime);writer=GatedWriter();peer.writer=peer.connection.writer=writer
    pending=asyncio.create_task(peer.login(role))
    try:
        await asyncio.wait_for(writer.entered.wait(),2)
        owner=runtime.roles[role['id']]
        await peer.connection.receive(peer.output.transform(frame(0xc003d,b'')))
        assert owner.joined and owner.newbie_pending and owner.intro_ticket is not None
        before=owner.position
        stop=b'\0'+struct.pack('>hhQ',*before.value[1:],before.value[0])
        await peer.connection.receive(peer.output.transform(frame(0xc0faa,stop)))
        assert owner.position==before
        writer.release.set()
        await pending
        assert not peer.connection.closed,'Late revoked scene receipt killed current intro connection'
        route=load_newbie_routes()[(9,role['school'])]
        assert (START_PLAY_CG,struct.pack('>i',route.intro_movie_id)) in peer.early_initial
        await peer.request(END_PLAY_CG,struct.pack('>i',route.intro_movie_id))
        assert not owner.newbie_pending and not peer.connection.closed
        before=owner.position
        await peer.request(0xc0faa,stop)
        assert owner.position.version>before.version
        return dict(real_early_ack_intro=True,revoked_scene_never_regrants=True,
            replacement_intro_connection_preserved=True,authorized_end_restores_movement=True,
            live_service_changed=False,native_gui_verified=False,battle_executed=False)
    finally:
        writer.release.set();await asyncio.gather(pending,return_exceptions=True)
        await runtime.close()


def main():
    with tempfile.TemporaryDirectory(prefix='movement-intro-race-') as directory:
        store=AccountStore(Path(directory)/'state.sqlite3');prepared=runtime_storage.prepare(store)
        role=store.create_role(1111,'剧情晚回执行走',11,1010109)
        result=asyncio.run(asyncio.wait_for(check(store,prepared,role),30))
    write_json(OUT/'evidence/runtime-movement-intro-race-verification.json',result);print(result)


if __name__=='__main__':main()
