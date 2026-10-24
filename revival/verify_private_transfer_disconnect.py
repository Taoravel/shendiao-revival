"""Actual bloodmark handoff interrupted before its send barrier; no live store."""
import asyncio
from contextlib import closing
import json
from pathlib import Path
import struct
import tempfile

from accounts import AccountStore
from game_runtime import GameRuntime
from inspect_client import OUT, write_json
from task_protocol import C_COMMIT_SCENARIO_QUEST
from verify_jiaxing_story_boundary_runtime import check as natural_boundary
from verify_runtime import Peer, Writer
from world_entity_protocol import VISIT_NPC
from world_newbie import load_newbie_routes
from world_transfer_storage import load_map_instance_transaction
import runtime_storage


class HeldWriter(Writer):
    """Only the drain timing varies; the original connection owns all bytes."""
    def __init__(self):
        super().__init__()
        self.armed = False
        self.entered = asyncio.Event()
        self.release = asyncio.Event()

    async def drain(self):
        if self.armed:
            self.entered.set()
            await self.release.wait()
        await super().drain()


async def check(store, prepared, role, route, witness):
    await natural_boundary(store, prepared, role, route, witness)
    # Isolate connection termination, rather than repeat navigation QA here.
    npc = next(p for p in store.npc_resources[0][1006]
               if p.placement_id == 13 and p.npc_id == 10498)
    epoch = store.acquire_lease(1111, role['id'])
    assert store.save_checkpoint(1111, role['id'], epoch, (1006, npc.x, npc.y),
                                 store.position_version(role['id'])+1)
    store.release_lease(role['id'], epoch)
    clock = [1000]
    runtime = GameRuntime(store, prepared, prologue_touch=True, story_clock=lambda: clock[0])
    pending = None
    try:
        peer = Peer(runtime)
        writer = HeldWriter()
        peer.writer = writer
        peer.connection.writer = writer
        await peer.login(role)
        owner = runtime.roles[role['id']]
        key = (1006 << 32) | 13
        await peer.request(VISIT_NPC, struct.pack('>q', key))
        await asyncio.sleep(3.05)
        writer.armed = True
        pending = asyncio.create_task(peer.request(C_COMMIT_SCENARIO_QUEST,
            struct.pack('>iQi', 100106, key, 0)))
        await asyncio.wait_for(writer.entered.wait(), 3)
        assert owner.transfer is not None, 'Controlled drain missed the committed loading handoff'
        receipt = owner.transfer
        target = runtime.registered_map(receipt.location.address)
        before = await target.mailbox.call('inspect_lifecycle', clock[0])
        assert before.members == before.incoming == 1
        pending.cancel()
        await asyncio.gather(pending, return_exceptions=True)
        await peer.connection.close()
        ended = await target.mailbox.call('inspect_lifecycle', clock[0])
        assert ended.members == 0 and ended.pending_scene_deliveries == 0, ended
        assert ended.incoming == ended.departures == ended.offers == 0, (
            'Disconnect left a completed transfer receipt fencing private-map reclamation', ended)
        assert ended.idle, ended
        assert await runtime.story_maps.collect() == ()
        clock[0] += store.story_instance_rules.idle_unload_after_ms
        assert await runtime.story_maps.collect() == (receipt.location.address,)
        assert runtime.registered_map(receipt.location.address) is None
        again = Peer(runtime)
        await again.login(role)
        current = runtime.roles[role['id']]
        with closing(store.leased(1111, role['id'], current.epoch).connect()) as db:
            db.execute('BEGIN')
            checkpoint = load_map_instance_transaction(db, 1111, role['id'], current.epoch)
        assert current.map_address == receipt.location.address == checkpoint.address
        assert current.position.value == receipt.location.position == checkpoint.position
        assert current.battle is None
        assert await again.request(100, bytes(4)) == [(100, bytes(4))]
        return dict(passed=[
            'natural public prefix and actual timed bloodmark commit reach a loading private target',
            'disconnect before send barrier clears members, transfer receipts and every scene ticket',
            'published idle interval permits actual map retirement and exact-address cold login'],
            npc_approach_fixture=True, held_writer_adapter=True,
            live_server_changed=False, native_gui_verified=False, battle_executed=False)
    finally:
        if pending is not None and not pending.done():
            pending.cancel()
            await asyncio.gather(pending, return_exceptions=True)
        await runtime.close()


def main():
    route = load_newbie_routes()[(9, 11)]
    audit = json.loads((OUT/'evidence/newbie-birth-sites-audit.json').read_text(encoding='utf-8'))
    witness = next(r for r in audit['routes'] if (r['character_id'], r['school_id']) == (9, 11))
    with tempfile.TemporaryDirectory(prefix='private-transfer-close-') as directory:
        store = AccountStore(Path(directory)/'state.sqlite3')
        prepared = runtime_storage.prepare(store)
        role = store.create_role(1111, '入梦断线验', 11, 1010109)
        result = asyncio.run(asyncio.wait_for(check(store, prepared, role, route, witness), 60))
    write_json(OUT/'evidence/private-transfer-disconnect-verification.json', result)
    print(result)


if __name__ == '__main__':
    main()
