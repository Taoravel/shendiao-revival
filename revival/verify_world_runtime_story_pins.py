"""Real GameRuntime map mailbox cancellation/expiry and unload-cleanup gates.

Temporary DB and explicit initial private checkpoint fixtures. Manual trusted
clock/collection isolates these races; no original client/GUI or battle runs.
"""
import asyncio
import argparse
import hashlib
from pathlib import Path
import tempfile
import time

from accounts import AccountStore
from game_runtime import GameRuntime
from inspect_client import OUT, write_json
import runtime_storage
from verify_runtime import Peer
from verify_runtime_private_role import fixtures


async def cancelled(task):
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        return
    raise AssertionError('The observer did not actually cancel')


def unload_refused(manager, handle, request_id):
    try:
        manager.pool.begin_unload(handle, request_id=request_id, now_ms=manager.now())
    except ValueError:
        return
    raise AssertionError('Actual queued/executing command lost its projection pin')


async def check(store, prepared, *, fault_early_expiry_release=False):
    entries, _ = await fixtures(store, prepared)
    clock = [1000]
    runtime = GameRuntime(store, prepared, story_clock=lambda: clock[0])
    held, release, closing, cleaned = (asyncio.Event() for _ in range(4))
    expired = None
    try:
        # Manual collect is the public scheduling seam for these deterministic
        # races. This check does not claim the periodic timer was exercised.
        runtime.story_maps.gc.cancel()
        await asyncio.gather(runtime.story_maps.gc, return_exceptions=True)
        peers = []
        for role, record in entries:
            peer = Peer(runtime)
            await peer.login(role)
            peers.append(peer)
        role, record = entries[0]
        other_role, other_record = entries[1]
        owner = runtime.registered_map(record.address)
        old_generation = owner.story_handle.map_generation
        other_map = runtime.registered_map(other_record.address)
        other_epoch = runtime.roles[other_role['id']].epoch
        await peers[0].connection.close()
        empty = await owner.mailbox.call('inspect_lifecycle', clock[0])
        assert empty.idle and empty.members == 0
        raw = owner.control_mailbox
        delegate = raw.handler
        seen = []

        async def gate(command):
            if command.request_id == 'held-map-command':
                held.set()
                await release.wait()
            if command.request_id == 'expired-map-command':
                seen.append(command.operation)
            return await delegate(command)

        raw.handler = gate
        clock[0] = 61000
        observer = asyncio.create_task(owner.mailbox.call('inspect_lifecycle', clock[0],
                                                         request_id='held-map-command'))
        await asyncio.wait_for(held.wait(), 2)
        await cancelled(observer)
        unload_refused(runtime.story_maps, owner.story_handle, 'cancelled-observer-still-busy')
        second_location = await asyncio.wait_for(other_map.mailbox.call('location',
                                               other_role['id'], other_epoch), 2)
        assert second_location.address == other_record.address
        assert await asyncio.wait_for(peers[1].request(100, b'pin1'), 2) == [(100, b'pin1')]
        captured = []
        original_acquire = runtime.story_maps.pool.acquire

        def capture(record, **kwargs):
            pin = original_acquire(record, **kwargs)
            captured.append(pin)
            return pin

        if fault_early_expiry_release:
            runtime.story_maps.pool.acquire = capture
        expired = asyncio.create_task(owner.mailbox.call('inspect_lifecycle', clock[0],
            request_id='expired-map-command', deadline=time.monotonic()-1))
        # Let the real raw SerialOwner enqueue behind the held handler.
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        if fault_early_expiry_release:
            runtime.story_maps.pool.acquire = original_acquire
            assert len(captured) == 1
            # Explicit test-only fault: remove this actual queued command's pin
            # before its mailbox deadline rejection. No production edits.
            runtime.story_maps.pool.release(captured[0], now_ms=clock[0])
        fillers = [runtime.story_maps.pool.acquire(record, request_id='capacity-filler-'+str(i),
            deadline_ms=clock[0]+1000, now_ms=clock[0], actor_state='static_original')
            for i in range(runtime.story_maps.rules.pins_per_projection-2)]
        try:
            runtime.story_maps.pool.acquire(record, request_id='queued-expiry-capacity-probe',
                deadline_ms=clock[0]+1000, now_ms=clock[0], actor_state='static_original')
        except ValueError:
            pass
        else:
            raise AssertionError('Queued expired command was not counted in its own occupied pin slot')
        unload_refused(runtime.story_maps, owner.story_handle, 'expired-queued-still-busy')
        release.set()
        try:
            await asyncio.wait_for(expired, 2)
        except TimeoutError:
            pass
        else:
            raise AssertionError('Queued expired command was executed')
        assert seen == [], 'Expired command reached MapOwner.handle instead of the mailbox terminal path'
        terminal_capacity = [runtime.story_maps.pool.acquire(record,
            request_id='released-terminal-capacity-'+str(i), deadline_ms=clock[0]+1000,
            now_ms=clock[0], actor_state='static_original') for i in range(2)]
        for pin in fillers+terminal_capacity:
            assert runtime.story_maps.pool.release(pin, now_ms=clock[0])
        final = await owner.mailbox.call('inspect_lifecycle', clock[0])
        assert final.idle
        raw.handler = delegate
        clock[0] = 120999
        assert await runtime.story_maps.collect() == (), 'Pin release did not restart the full idle interval'
        old_close = owner.mailbox.close

        async def slow_close():
            closing.set()
            await cleaned.wait()
            await old_close()

        owner.mailbox.close = slow_close
        clock[0] = 121000
        collector = asyncio.create_task(runtime.story_maps.collect())
        await asyncio.wait_for(closing.wait(), 2)
        assert runtime.registered_map(record.address) is None
        assert runtime.story_maps.pool.loaded_count == 2, 'Retirement released the slot before actual cleanup'
        await cancelled(collector)
        assert runtime.story_maps.pool.loaded_count == 2, 'Observer cancellation released a cleanup slot'
        try:
            runtime.story_maps.pool.acquire(record, request_id='reload-before-cleanup',
                deadline_ms=clock[0]+1000, now_ms=clock[0], actor_state='static_original')
        except ValueError:
            pass
        else:
            raise AssertionError('Same private address was reloadable before its old Adapter terminated')
        assert (await asyncio.wait_for(other_map.mailbox.call('location', other_role['id'], other_epoch), 2)).address == other_record.address
        assert await asyncio.wait_for(peers[1].request(100, b'pin2'), 2) == [(100, b'pin2')]
        completion = asyncio.create_task(runtime.story_maps.collect())
        await asyncio.sleep(0)
        cleaned.set()
        assert await asyncio.wait_for(completion, 2) == (record.address,)
        assert runtime.story_maps.pool.loaded_count == 1
        try:
            await owner.mailbox.call('inspect_lifecycle', clock[0])
        except ValueError:
            pass
        else:
            raise AssertionError('Old retired Adapter remained usable')
        replacement = Peer(runtime)
        await replacement.login(role)
        rebuilt = runtime.registered_map(record.address)
        assert rebuilt.story_handle.map_generation != old_generation
        assert runtime.roles[role['id']].map_address == record.address
        return dict(passed=[
            'cancelled observer retains the actual executing map command pin',
            'another private map and encrypted heartbeat proceed while one map handler is held',
            'deadline rejection before MapOwner.handle releases its pin only at actual terminal',
            'final pin release restarts the complete60000ms idle interval',
            'retirement and cancelled collect observer retain the slot until Adapter cleanup terminates',
            'another map proceeds during cleanup; same-address reload waits then uses a new generation'],
            natural_role_origins=2, initial_private_checkpoint_fixture=True,
            fault_injection='actual SerialOwner handler and Adapter close gates; original delegates retained',
            trusted_clock_adapter=True, periodic_collection_verified=False,
            queued_expiry_pin_capacity_verified=True, additional_controlled_capacity_pins=len(fillers),
            native_gui_verified=False, battle_executed=False, live_server_changed=False)
    finally:
        release.set()
        cleaned.set()
        if expired is not None:
            await asyncio.gather(expired, return_exceptions=True)
        await runtime.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--fault-early-expiry-release', action='store_true',
                        help='Intentional test-only premature release; this run must fail')
    args = parser.parse_args()
    names = ('game_runtime.py', 'runtime_core.py', 'runtime_story_maps.py', 'runtime_storage.py',
             'world_owner.py', 'world_story_projection_pool.py', 'world_story_instances.py',
             'verify_world_runtime_story_pins.py', 'verify_runtime_private_role.py')
    before = {name: hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in names}
    with tempfile.TemporaryDirectory(prefix='world-runtime-story-pins-') as directory:
        store = AccountStore(Path(directory)/'state.sqlite3')
        result = asyncio.run(asyncio.wait_for(check(store, runtime_storage.prepare(store),
            fault_early_expiry_release=args.fault_early_expiry_release), 30))
    after = {name: hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in names}
    assert before == after, 'Shared input changed while the check ran; this is not a fixed-source result'
    result.update(source_sha256=before, inputs_stable=True)
    write_json(OUT/'evidence/world-runtime-story-pins-verification.json', result)
    print({key: result[key] for key in ('passed', 'inputs_stable', 'initial_private_checkpoint_fixture')})


if __name__ == '__main__':
    main()
