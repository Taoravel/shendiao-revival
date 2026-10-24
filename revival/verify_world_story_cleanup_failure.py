"""Observe actual maintenance error fencing without inventing recovery policy.

Real RuntimeStoryMaps timer/MapOwner/pool; explicit catalog/directory and close
failure Adapters. No database, socket, live role, game, or shared edit.
"""
import asyncio
import hashlib
from pathlib import Path

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
    clock, registry = [1000], {}

    def create(entry):
        owner = MapOwner(entry.address,
            {1501: dict(available=True, width=4096, height=4096)}, story_rules=rules)
        registry[entry.address] = owner
        return owner

    def forget(address, owner):
        assert registry.pop(address) is owner

    manager = RuntimeStoryMaps(rules, create, forget, clock=lambda: clock[0])
    owner = await manager.get_map(first, request_id='initial-load', deadline_ms=10000)
    raw, original_close = owner.control_mailbox, owner.control_mailbox.close
    entered = asyncio.Event()
    close_calls = []

    async def failed_close():
        close_calls.append(error_type.__name__)
        entered.set()
        # A controlled Adapter reports failure BEFORE resource termination.
        raise error_type('Controlled cleanup outcome remains unconfirmed')

    raw.close = failed_close
    try:
        clock[0] = 61000
        await asyncio.wait_for(entered.wait(), 3)  # Real one-second GC timer.
        active = tuple(manager.maintenance.values())
        await asyncio.gather(*active, return_exceptions=True)
        for _ in range(100):
            if not manager.maintenance:
                break
            await asyncio.sleep(0)
        else:
            raise AssertionError('Actual failed maintenance task did not reach terminal callback')
        if error_type is ConnectionError:
            try:
                await asyncio.wait_for(asyncio.shield(manager.gc), 2)
            except ConnectionError:
                pass
            else:
                raise AssertionError('Unexpected maintenance error did not surface from GC task')
        else:
            # Await a fresh actual maintenance command, not arbitrary wall time.
            await manager.collect()
            assert not manager.gc.done()
        snapshot = await raw.call('inspect_lifecycle', clock[0])
        assert snapshot.retired and not snapshot.idle
        assert first.address not in registry
        assert manager.pool.loaded_count == 1
        try:
            await manager.get_map(first, request_id='reload-after-close-failure', deadline_ms=71000)
        except ValueError as error:
            admission_error = str(error)
        else:
            raise AssertionError('Unknown cleanup permitted a second owner for a retired address')
        assert admission_error == 'Story projection is retiring'
        # A later full idle interval still has no public cleanup-retry branch.
        clock[0] = 121000
        assert await manager.collect() == ()
        assert len(close_calls) == 1 and manager.pool.loaded_count == 1
        other = await manager.get_map(second, request_id='independent-map', deadline_ms=131000)
        live = await asyncio.wait_for(other.mailbox.call('inspect_lifecycle', clock[0]), 1)
        assert not live.retired and live.address == second.address
        return dict(error_type=error_type.__name__, timer_exercised=True,
            gc_task_terminal=manager.gc.done(), retired=True, cleanup_attempts=len(close_calls),
            address_fenced=admission_error, slot_retained_after_another_idle_interval=True,
            subsequent_collect_retries_cleanup=False, independent_map_accepted=True,
            assessment='safe fence retained; automatic cleanup recovery unavailable in exercised path')
    finally:
        # Explicit test teardown confirms termination; this is not an existing
        # production recovery Interface and does not finish the pool unload.
        await manager.stop()
        raw.close = original_close
        await owner.mailbox.close()
        for remaining in tuple(registry.values()):
            await remaining.mailbox.close()
        await manager.close()


def main():
    names = ('runtime_story_maps.py', 'runtime_core.py', 'world_owner.py',
             'world_story_projection_pool.py', 'game_runtime.py',
             'verify_world_story_cleanup_failure.py')
    before = {name: hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in names}

    async def run():
        return [await observe(ConnectionError), await observe(TimeoutError)]

    rows = asyncio.run(asyncio.wait_for(run(), 15))
    after = {name: hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in names}
    assert before == after, 'Observed runtime changed during cleanup evidence collection'
    result = dict(observations=rows, source_sha256=before, inputs_stable=True,
        lifecycle_safety_verified=True, automatic_cleanup_recovery_verified=False,
        directory_authorization_fixture=True, live_server_changed=False,
        native_gui_verified=False, battle_executed=False)
    write_json(OUT/'evidence/world-story-cleanup-failure-observation.json', result)
    print(dict(observation_groups=len(rows), safe_fences_retained=True,
               automatic_cleanup_recovery_verified=False))


if __name__ == '__main__':
    main()
