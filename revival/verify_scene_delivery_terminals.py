"""Actual encrypted send-pump terminals and private-map collection.

Private initial checkpoints and stale fence variants are explicit fixtures.
No live service, account, database, game process or battle is accessed.
"""
import asyncio
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import time

from accounts import AccountStore
from game_runtime import GameRuntime
from inspect_client import OUT, write_json
from social_owner import Delivery
from verify_runtime import Peer
from verify_runtime_private_role import fixtures
from wire import frame
from world_movement import ROLE_STOP
import runtime_storage
import social_protocol as sp


async def pause_drain(peer):
    entered, release = asyncio.Event(), asyncio.Event()

    async def held():
        entered.set()
        await release.wait()

    peer.writer.drain = held
    await peer.connection.receive(peer.output.transform(frame(100, b'hold')))
    await asyncio.wait_for(entered.wait(), 1)
    return release


async def idle_snapshot(runtime, target):
    return await target.control_mailbox.call('inspect_lifecycle', runtime.story_maps.now())


async def retired_after_close(runtime, peer, entry, now):
    await peer.connection.close()
    target = runtime.registered_map(entry.address)
    snapshot = await idle_snapshot(runtime, target)
    assert snapshot.pending_scene_deliveries == 0 and snapshot.members == 0
    now[0] += runtime.story_maps.rules.idle_unload_after_ms
    collected = await runtime.story_maps.collect()
    assert entry.address in collected and runtime.registered_map(entry.address) is None


async def check_fences(store, prepared, entries, npc):
    now = [int(time.monotonic()*1000)]
    runtime = GameRuntime(store, prepared, story_clock=lambda: now[0])
    release = None
    try:
        peers = []
        for role, entry in entries:
            peer = Peer(runtime)
            await peer.login(role)
            peers.append(peer)
        peer, other = peers
        role, entry = entries[0]
        owner = runtime.roles[role['id']]
        target = runtime.registered_map(entry.address)
        release = await pause_drain(peer)
        body = sp.chat_message(role, sp.CURRENT_CHANNEL, '正常场景消息')
        messages = await runtime.scene_messages(owner, [(sp.CHAT_RECEIVE, body)]*3)
        token = owner.scene_token
        stale_token = replace(messages[1], fence=replace(messages[1].fence, scene_token='stale-scene-token-fixture'))
        stale_map = replace(messages[2], fence=replace(messages[2].fence, map_generation='stale-map-generation-fixture'))
        for message in (stale_token, stale_map, messages[0]):
            assert await peer.connection.offer_message(message, owner.epoch)
        assert (await idle_snapshot(runtime, target)).pending_scene_deliveries == 3
        # A real ordinary accepted STOP changes position version, not scene identity.
        await peer.connection.receive(peer.output.transform(frame(ROLE_STOP,
            b'\0'+struct.pack('>hhQ', npc.x+1, npc.y, 1501))))
        assert owner.position.value == (1501, npc.x+1, npc.y) and owner.scene_token == token
        assert await asyncio.wait_for(other.request(100, b'free'), .5) == [(100, b'free')]
        release.set()
        delivered = await peer.take()
        assert delivered == [(100, b'hold'), (sp.CHAT_RECEIVE, body)], delivered
        assert peer.connection.metrics['stale_scene_delivery'] == 2
        assert (await idle_snapshot(runtime, target)).pending_scene_deliveries == 0
        assert await peer.request(100, b'next') == [(100, b'next')]
        await retired_after_close(runtime, peer, entry, now)
        assert runtime.registered_map(entries[1][1].address) is not None
        assert await other.request(100, b'live') == [(100, b'live')]
    finally:
        if release is not None:
            release.set()
        await runtime.close()


async def check_queue_full(store, prepared, entries):
    now = [int(time.monotonic()*1000)]
    runtime = GameRuntime(store, prepared, story_clock=lambda: now[0])
    release = None
    try:
        role, entry = entries[0]
        peer = Peer(runtime)
        await peer.login(role)
        owner = runtime.roles[role['id']]
        target = runtime.registered_map(entry.address)
        release = await pause_drain(peer)
        body = sp.chat_message(role, sp.CURRENT_CHANNEL, '队列满应明确拒绝')
        queued = await runtime.scene_messages(owner, [(sp.CHAT_RECEIVE, body)])
        assert await peer.connection.offer_message(queued[0], owner.epoch)
        while not peer.connection.queue.full():
            assert peer.connection.offer(100, b'fill')
        assert (await idle_snapshot(runtime, target)).pending_scene_deliveries == 1
        snapshot = owner.snapshot()
        delivery = Delivery(owner.id, owner.epoch, sp.CHAT_RECEIVE, body, scene_key=snapshot.scene_key)
        assert not await runtime.offer_scene_channel(snapshot, delivery)
        # The newly rejected ticket has terminated; the older queued ticket remains.
        assert (await idle_snapshot(runtime, target)).pending_scene_deliveries == 1
        assert peer.connection.closed and peer.writer.closed
        assert peer.connection.metrics['send_rejected'] == 1
        await retired_after_close(runtime, peer, entry, now)
        assert peer.connection.queue.empty() and peer.connection.pending_bytes == 0
        await asyncio.wait_for(peer.connection.queue.join(), 1)
    finally:
        if release is not None:
            release.set()
        await runtime.close()


async def check(store, prepared):
    entries, npc = await fixtures(store, prepared)
    await check_fences(store, prepared, entries, npc)
    await check_queue_full(store, prepared, entries)


def main():
    inputs = ('game_runtime.py', 'runtime_story_maps.py', 'runtime_storage.py', 'world_owner.py',
              'world_story_projection_pool.py', 'social_owner.py', 'social_runtime.py',
              'verify_scene_delivery_terminals.py', 'verify_runtime.py', 'verify_runtime_private_role.py')
    before = {name:hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in inputs}
    with tempfile.TemporaryDirectory(prefix='scene-terminals-root-') as folder:
        store = AccountStore(Path(folder)/'state.sqlite3')
        asyncio.run(asyncio.wait_for(check(store, runtime_storage.prepare(store)), 40))
    assert before == {name:hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in inputs}
    report = dict(passed=[
        'actual private tickets remain registered behind a held encrypted send drain',
        'stale scene-token/map-generation fixtures drop before encoding, while real STOP retains a fresh frame',
        'subsequent original RC4/MPPC decoder heartbeat remains continuous after both dropped frames',
        'another private role heartbeat proceeds while the first connection drain is held',
        'full actual send queue rejects a new current-channel ticket without consuming its scene capacity',
        'close terminates queued tickets and bytes; full idle interval collects the exact projection'],
        source_hashes_unchanged=before, initial_private_checkpoint_fixture=True,
        stale_fences_are_controlled_fixtures=True, actual_scene_transition_verified=False,
        live_service_changed=False, live_database_accessed=False, native_gui_verified=False,
        battle_executed=False, commercial_capacity_verified=False)
    write_json(OUT/'evidence/scene-delivery-terminals-root-verification.json', report)
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
