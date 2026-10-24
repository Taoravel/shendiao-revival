"""Private scene delivery terminal paths through real runtime Interfaces.

Temporary roles use an explicit initial private-checkpoint fixture. Controlled
Writer/map-handler Adapters hold or fail actual work; no GUI/live service runs.
"""
import argparse
import asyncio
from contextlib import asynccontextmanager
from dataclasses import replace
import hashlib
from pathlib import Path
import tempfile

from accounts import AccountStore
from game_runtime import GameRuntime
from inspect_client import OUT, write_json
import runtime_storage
from verify_runtime import Peer
from verify_runtime_private_role import fixtures


def available_pins(manager, record):
    """Measure remaining public pool capacity without inspecting its dicts."""
    held = []
    try:
        for number in range(manager.rules.pins_per_projection + 1):
            try:
                pin = manager.pool.acquire(record, request_id=f'terminal-probe:{number}',
                    deadline_ms=manager.now()+10000, now_ms=manager.now(),
                    actor_state='static_original')
            except ValueError as error:
                assert str(error) == 'Story pending operation capacity'
                return len(held)
            held.append(pin)
        raise AssertionError('Published operation capacity was not enforced')
    finally:
        for pin in held:
            manager.pool.release(pin, now_ms=manager.now())


@asynccontextmanager
async def session(store, prepared, entries):
    runtime = GameRuntime(store, prepared, story_clock=lambda: 1000)
    runtime.story_maps.gc.cancel()
    await asyncio.gather(runtime.story_maps.gc, return_exceptions=True)
    try:
        peers = []
        for role, _ in entries:
            peer = Peer(runtime)
            await peer.login(role)
            peers.append(peer)
        role, record = entries[0]
        owner = runtime.roles[role['id']]
        target = runtime.registered_map(record.address)
        assert available_pins(runtime.story_maps, record) == 64
        yield runtime, peers, owner, target, record
    finally:
        await runtime.close()


async def deliveries(runtime, owner, count=1):
    # A four-byte heartbeat is an original harmless logical response. Creating
    # it here isolates scene lifetime from the NPC/task decision producing it.
    return await runtime.scene_messages(owner, [(100, b'scen')] * count)


async def pending(runtime, target):
    return (await target.mailbox.call('inspect_lifecycle', runtime.story_maps.now())).pending_scene_deliveries


async def check(store, prepared, rows, *, fault_early_release=False):
    entries, _ = await fixtures(store, prepared)
    async with session(store, prepared, entries) as (rt, peers, owner, target, record):
        message, = await deliveries(rt, owner)
        assert await pending(rt, target) == 1
        assert available_pins(rt.story_maps, record) == 63
        assert await peers[0].connection.offer_message(message, owner.epoch)
        assert await peers[0].take() == [(100, b'scen')]
        assert await pending(rt, target) == 0
        assert available_pins(rt.story_maps, record) == 64
        rows.append('successful encrypted send/drain finishes exact ticket and pin')

        message, = await deliveries(rt, owner)
        assert not await peers[0].connection.offer_message(message, owner.epoch-1)
        assert await peers[0].take() == []
        assert await pending(rt, target) == 0
        assert available_pins(rt.story_maps, record) == 64
        rows.append('stale-epoch offer rejects and cleans an unqueued ticket')

        message, = await deliveries(rt, owner)
        message = replace(message, fence=replace(message.fence, scene_token='stale-scene-token'))
        assert await peers[0].connection.offer_message(message, owner.epoch)
        assert await peers[0].take() == []
        assert peers[0].connection.metrics['stale_scene_delivery'] == 1
        assert await pending(rt, target) == 0
        assert available_pins(rt.story_maps, record) == 64
        assert await peers[0].request(100, b'next') == [(100, b'next')]
        rows.append('queued stale-scene fence drops before encoding; cipher stream continues')

        try:
            await deliveries(rt, owner, 65)
        except ValueError as error:
            assert str(error) == 'Story pending operation capacity'
        else:
            raise AssertionError('Oversized private response bypassed per-projection capacity')
        assert await pending(rt, target) == 0
        assert available_pins(rt.story_maps, record) == 64
        rows.append('partial 65-message construction failure cleans all 64 accepted registrations')

    async with session(store, prepared, entries) as (rt, peers, owner, target, record):
        message, = await deliveries(rt, owner)
        peers[0].connection.byte_capacity = 0  # Explicit smaller transport budget.
        assert not await peers[0].connection.offer_message(message, owner.epoch)
        assert peers[0].connection.closed
        assert await pending(rt, target) == 0
        assert available_pins(rt.story_maps, record) == 64
        await peers[0].connection.close()
        rows.append('send byte-budget refusal cleans unqueued ticket and disconnects target')

    for failure in ('connection_error', 'timeout'):
        async with session(store, prepared, entries) as (rt, peers, owner, target, record):
            entered, release = asyncio.Event(), asyncio.Event()

            async def failed_drain():
                entered.set()
                if failure == 'connection_error':
                    raise ConnectionError('Controlled Writer Adapter failure')
                await release.wait()

            peers[0].writer.drain = failed_drain
            message, = await deliveries(rt, owner)
            try:
                assert await peers[0].connection.offer_message(message, owner.epoch)
                await asyncio.wait_for(entered.wait(), 2)
                if failure == 'timeout':
                    assert available_pins(rt.story_maps, record) == 63
                    assert await peers[1].request(100, b'live') == [(100, b'live')]
                # Exercise the real three-second ConnectionOwner drain timeout.
                await asyncio.wait_for(asyncio.shield(peers[0].connection.pump), 4)
                assert peers[0].connection.closed
                assert await pending(rt, target) == 0
                assert available_pins(rt.story_maps, record) == 64
                rows.append(f'{failure}: actual send pump terminates and releases delivery')
            finally:
                release.set()

    async with session(store, prepared, entries) as (rt, peers, owner, target, record):
        entered, release = asyncio.Event(), asyncio.Event()

        async def held_drain():
            entered.set()
            await release.wait()

        peers[0].writer.drain = held_drain
        try:
            for message in await deliveries(rt, owner, 3):
                assert await peers[0].connection.offer_message(message, owner.epoch)
            await asyncio.wait_for(entered.wait(), 2)
            assert peers[0].connection.queue.qsize() == 2
            assert await pending(rt, target) == 3
            assert available_pins(rt.story_maps, record) == 61
            await peers[0].connection.close()
            assert await pending(rt, target) == 0
            assert available_pins(rt.story_maps, record) == 64
            assert await peers[1].request(100, b'live') == [(100, b'live')]
            rows.append('pump cancellation cleans one active and two queued deliveries')
        finally:
            release.set()

    async with session(store, prepared, entries) as (rt, peers, owner, target, record):
        entered, release = asyncio.Event(), asyncio.Event()
        raw = target.control_mailbox
        delegate = raw.handler

        async def held_finish(command):
            if command.operation == 'finish_scene_delivery':
                entered.set()
                await release.wait()
            return await delegate(command)

        raw.handler = held_finish
        message, = await deliveries(rt, owner)
        observer = asyncio.create_task(peers[0].connection.cleanup_delivery(message.delivery))
        try:
            await asyncio.wait_for(entered.wait(), 2)
            if fault_early_release:
                rt.story_maps.pool.release(message.delivery.pin, now_ms=rt.story_maps.now())
            assert available_pins(rt.story_maps, record) == 63, \
                'In-flight finish lost its own delivery pin before map terminal'
            observer.cancel()
            try:
                await observer
            except asyncio.CancelledError:
                pass
            else:
                raise AssertionError('Cleanup observer was not cancelled')
            assert available_pins(rt.story_maps, record) == 63, \
                'Cancelled cleanup observer released still-executing delivery pin'
            assert await peers[1].request(100, b'live') == [(100, b'live')]
            release.set()
            await raw.queue.join()
            while rt.story_maps.work:
                await asyncio.gather(*tuple(rt.story_maps.work))
            assert await pending(rt, target) == 0
            assert available_pins(rt.story_maps, record) == 64
            rows.append('cancelled cleanup observer keeps its own pin until actual map finish; peer continues')
        finally:
            release.set()
            await asyncio.gather(observer, return_exceptions=True)
            await raw.queue.join()

    async with session(store, prepared, entries) as (rt, peers, owner, target, record):
        raw, delegate = target.control_mailbox, target.control_mailbox.handler
        failures = []

        async def refused_finish(command):
            if command.operation == 'finish_scene_delivery' and not failures:
                failures.append(command.operation)
                raise ValueError('Controlled map cleanup refusal')
            return await delegate(command)

        raw.handler = refused_finish
        message, = await deliveries(rt, owner)
        await peers[0].connection.cleanup_delivery(message.delivery)
        assert peers[0].connection.metrics['scene_cleanup_failed'] == 1
        assert await pending(rt, target) == 1
        assert available_pins(rt.story_maps, record) == 63
        await peers[0].connection.cleanup_delivery(message.delivery)
        assert await pending(rt, target) == 0
        assert available_pins(rt.story_maps, record) == 64
        rows.append('unconfirmed cleanup retains ticket/pin; exact retry releases after confirmation')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--fault-early-release', action='store_true')
    args = parser.parse_args()
    names = ('game_runtime.py', 'runtime_story_maps.py', 'runtime_core.py',
        'world_owner.py', 'world_story_projection_pool.py', 'runtime_storage.py',
        'verify_runtime.py', 'verify_runtime_private_role.py',
        'verify_world_scene_delivery_terminal.py')
    before = {name: hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in names}
    result = dict(passed=[], all_passed=False, source_sha256=before,
        fault_early_release=args.fault_early_release, initial_private_checkpoint_fixture=True,
        timer_collect_verified=False, native_gui_verified=False, live_server_changed=False,
        battle_executed=False)
    path = OUT/('evidence/world-scene-delivery-terminal-fault.json' if args.fault_early_release
                else 'evidence/world-scene-delivery-terminal-verification.json')
    try:
        with tempfile.TemporaryDirectory(prefix='world-scene-terminal-') as directory:
            store = AccountStore(Path(directory)/'state.sqlite3')
            asyncio.run(asyncio.wait_for(check(store, runtime_storage.prepare(store),
                result['passed'], fault_early_release=args.fault_early_release), 60))
        after = {name: hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in names}
        assert before == after, 'Execution inputs changed during verification'
        result.update(all_passed=True, inputs_stable=True)
    except Exception as error:
        result.update(error=repr(error))
        raise
    finally:
        write_json(path, result)
    print(dict(all_passed=True, groups=len(result['passed']), live_server_changed=False))


if __name__ == '__main__':
    main()
