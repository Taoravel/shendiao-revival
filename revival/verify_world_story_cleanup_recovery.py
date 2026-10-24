"""Independent current shared cleanup retry/terminal verification.

Directory/catalog/close-failure fixtures, actual timer/map/pool. No live state.
"""
import asyncio
import hashlib

from game_runtime import MapOwner
from inspect_client import OUT, write_json
from runtime_story_maps import RuntimeStoryMaps
from world_owner import MapAddress
from world_story_instances import StoryInstanceRules, StoryInstance, StoryInstanceIntent


async def observe(error_type):
    rules = StoryInstanceRules('2026-10-23.story-instance.1', 'newbie_bloodmark_dream',
        1501, 0, 2**62, 2**63, 8, 1, 128, 60000, 64, 64, None, {(9, 11): 100106})

    def record(role):
        return StoryInstance(rules.kind, role, 1,
            StoryInstanceIntent(f'chapter{role}', f'creation{role}', 'policy', 'route', 100106),
            rules.revision, MapAddress(1501, 2**62+role, 0))

    first, second = record(1), record(2)
    clock, registry, forgotten = [1000], {}, []

    def create(entry):
        assert entry.address not in registry
        owner = MapOwner(entry.address,
            {1501: dict(available=True, width=4096, height=4096)}, story_rules=rules)
        registry[entry.address] = owner
        return owner

    def forget(address, owner):
        assert registry.pop(address) is owner
        forgotten.append((address, owner.story_handle.map_generation))

    manager = RuntimeStoryMaps(rules, create, forget, clock=lambda: clock[0])
    old = await manager.get_map(first, request_id='first-load', deadline_ms=10000)
    old_generation = old.story_handle.map_generation
    raw, original_close = old.control_mailbox, old.control_mailbox.close
    failed, retrying, release = asyncio.Event(), asyncio.Event(), asyncio.Event()
    attempts = []
    collector = None

    async def retryable_close():
        attempts.append(error_type.__name__)
        if len(attempts) == 1:
            failed.set()
            raise error_type('Controlled pre-terminal cleanup failure')
        retrying.set()
        await release.wait()
        await original_close()

    raw.close = retryable_close
    try:
        clock[0] = 61000
        await asyncio.wait_for(failed.wait(), 3)  # Actual production GC timer.
        await asyncio.gather(*tuple(manager.maintenance.values()), return_exceptions=True)
        for _ in range(100):
            if not manager.maintenance:
                break
            await asyncio.sleep(0)
        else:
            raise AssertionError('Failed maintenance observer did not terminate')
        assert not manager.gc.done(), 'Cleanup error terminated current maintenance loop'
        assert manager.pool.loaded_count == 1 and first.address not in registry
        other = await manager.get_map(second, request_id='other-load', deadline_ms=71000)
        assert not (await other.mailbox.call('inspect_lifecycle', clock[0])).retired
        collector = asyncio.create_task(manager.collect())
        await asyncio.wait_for(retrying.wait(), 2)
        collector.cancel()
        try:
            await collector
        except asyncio.CancelledError:
            pass
        else:
            raise AssertionError('Outer collect observer was not cancelled')
        assert manager.pool.loaded_count == 2 and not raw.task.done()
        try:
            await manager.get_map(first, request_id='forbidden-reload', deadline_ms=71000)
        except ValueError as error:
            assert str(error) == 'Story projection is retiring'
        else:
            raise AssertionError('Retry observer cancellation released unknown cleanup slot')
        assert (await other.mailbox.call('inspect_lifecycle', clock[0])).address == second.address
        release.set()
        await asyncio.gather(*tuple(manager.maintenance.values()))
        assert raw.task.done() and not raw.task.cancelled() and raw.task.exception() is None
        assert manager.pool.loaded_count == 1
        assert forgotten == [(first.address, old_generation)]
        fresh = await manager.get_map(first, request_id='after-real-close', deadline_ms=71000)
        assert fresh is not old and fresh.story_handle.map_generation != old_generation
        assert fresh.story_handle.record == first
        return dict(error_type=error_type.__name__, timer_exercised=True,
            cleanup_attempts=len(attempts), gc_survives=True,
            cancelled_observer_retains_fence=True, actual_adapter_terminal=True,
            registry_forgot_exactly_once=True, independent_map_progress=True,
            same_address_new_generation_after_cleanup=True)
    finally:
        release.set()
        if collector is not None:
            await asyncio.gather(collector, return_exceptions=True)
        await manager.stop()
        raw.close = original_close
        if not raw.task.done():
            await old.mailbox.close()
        for owner in tuple(registry.values()):
            if not owner.mailbox.task.done():
                await owner.mailbox.close()
        await manager.close()


def main():
    names = ('game_runtime.py', 'runtime_story_maps.py', 'runtime_core.py',
        'world_owner.py', 'world_story_projection_pool.py', 'verify_world_story_cleanup_recovery.py')
    before = {name: hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in names}

    async def run():
        return [await observe(ConnectionError), await observe(TimeoutError)]

    results = asyncio.run(asyncio.wait_for(run(), 15))
    after = {name: hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in names}
    assert before == after, 'Runtime changed during cleanup retry verification'
    write_json(OUT/'evidence/world-story-cleanup-recovery-verification.json',
        dict(all_passed=True, groups=results, source_sha256=before, inputs_stable=True,
            directory_authorization_fixture=True, real_io_fault_verified=False,
            native_gui_verified=False, live_server_changed=False, battle_executed=False))
    print(dict(all_passed=True, groups=len(results), live_server_changed=False))


if __name__ == '__main__':
    main()
