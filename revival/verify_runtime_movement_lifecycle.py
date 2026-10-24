"""Actual encrypted connection: a queued scene is not a movement declaration.

The only gate is the real target Writer.drain. Temporary legacy role/checkpoint;
no live DB, socket, GUI or battle is used.
"""
import asyncio
from pathlib import Path
import struct
import tempfile

from accounts import AccountStore
from game_runtime import GameRuntime
from inspect_client import OUT, write_json
import runtime_storage
from verify_runtime import Writer
from verify_world_resource_runtime import MapPeer, Events, checkpoint_fixture
from wire import frame


class GatedWriter(Writer):
    def __init__(self):
        super().__init__()
        self.remaining = None
        self.entered, self.release = asyncio.Event(), asyncio.Event()

    async def drain(self):
        if self.remaining is not None:
            self.remaining -= 1
            if self.remaining == 0:
                self.remaining = None
                self.entered.set()
                await self.release.wait()
        await super().drain()


class GatedPeer(MapPeer):
    def __init__(self,runtime):
        super().__init__(runtime)
        self.early_initial=[]

    async def request(self, kind, body):
        if kind == 0xc0005:
            # Exact third frame of load: ENTER_WORLD, clock, ENTER_SCENE.
            self.writer.remaining = 3
        replies=await super().request(kind, body)
        if kind==0xc0005:
            # The adversarial early ACK below legitimately queues first-world
            # output while Scene.drain is held. Preserve those received frames;
            # the shared Peer login validator consumes the entry triplet only.
            self.early_initial=replies[3:]
            return replies[:3]
        return replies


async def check(store, prepared, role):
    start, clear, wall = (360, 2264), (361, 2264), (1664, 960)
    checkpoint_fixture(store, role, (1006, *start))
    events = Events()
    runtime = GameRuntime(store, prepared, logger=events)
    peer = GatedPeer(runtime)
    # Preserve the actual ConnectionOwner; replace only its external I/O Adapter.
    writer = GatedWriter()
    peer.writer = peer.connection.writer = writer
    login = asyncio.create_task(peer.login(role))
    try:
        await asyncio.wait_for(writer.entered.wait(), 3)
        owner = runtime.roles[role['id']]
        # Exercise the *new* context gate after the old joined requirement has
        # been satisfied through actual encrypted ingress. An early client ACK
        # must never act as the server's exact Scene delivery declaration.
        await peer.connection.receive(peer.output.transform(frame(0xc003d,b'')))
        assert owner.joined and not owner.transfer and not owner.newbie_pending and owner.battle is None
        before = owner.position
        stop = b'\0' + struct.pack('>hhQ', *clear, 1006)
        await peer.connection.receive(peer.output.transform(frame(0xc0faa, stop)))
        assert owner.position == before, 'Movement accepted before exact scene drain'
        assert events.rows, 'Missing pre-declaration rejection'
        writer.release.set()
        await login
        events.rows.clear()
        await peer.request(0xc0fa1, struct.pack('>hhhhQ', *start, *clear, 1006))
        await peer.request(0xc0faa, stop)
        assert owner.position.value == (1006, *clear) and not events.rows
        before = owner.position
        await peer.request(0xc0faa, b'\0' + struct.pack('>hhQ', *wall, 1006))
        assert owner.position == before and events.rows
        assert owner.battle is None and not runtime.battles
        return dict(scene_drain_before_movement=True, ordinary_clear_after_drain=True,
            original_wall_rejected=True, real_encrypted_connection=True,
            native_gui_verified=False, live_service_changed=False)
    finally:
        writer.release.set()
        await asyncio.gather(login, return_exceptions=True)
        await runtime.close()


def main():
    with tempfile.TemporaryDirectory(prefix='runtime-movement-lifecycle-') as directory:
        store = AccountStore(Path(directory) / 'state.sqlite3')
        role = store.create_role(1111, '行走生命周期', 11, 1010109)
        result = asyncio.run(asyncio.wait_for(check(store, runtime_storage.prepare(store), role), 30))
    write_json(OUT / 'evidence/runtime-movement-lifecycle-verification.json', result)
    print(result)


if __name__ == '__main__':
    main()
