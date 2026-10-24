"""Real GC timer retries a failed retired Adapter, without releasing its slot."""
import asyncio

from game_runtime import MapOwner
from inspect_client import OUT, write_json
from runtime_story_maps import RuntimeStoryMaps
from world_owner import MapAddress
from world_story_instances import StoryInstanceRules, StoryInstance, StoryInstanceIntent


async def check(error_type):
    rules = StoryInstanceRules('2026-10-23.story-instance.1', 'newbie_bloodmark_dream',
        1501, 0, 2**62, 2**63, 8, 1, 128, 60000, 64, 64, None, {(9, 11): 100106})
    def record(role):
        return StoryInstance(rules.kind, role, 1,
            StoryInstanceIntent('chapter'+str(role), 'creation'+str(role), 'policy', 'route', 100106),
            rules.revision, MapAddress(1501, 2**62+role, 0))
    first, second = record(1), record(2)
    clock, registry = [1000], {}
    def create(entry):
        owner = MapOwner(entry.address, {1501: dict(available=True, width=4096, height=4096)}, story_rules=rules)
        registry[entry.address] = owner
        return owner
    def forget(address, owner):
        assert registry.pop(address) is owner
    manager = RuntimeStoryMaps(rules, create, forget, clock=lambda: clock[0])
    owner = await manager.get_map(first, request_id='load', deadline_ms=10000)
    original_close = owner.control_mailbox.close
    second_attempt, release = asyncio.Event(), asyncio.Event()
    attempts = []
    async def failing_then_held_close():
        attempts.append(len(attempts)+1)
        if len(attempts) == 1:
            raise error_type('Controlled Adapter failure before terminal cleanup')
        second_attempt.set()
        await release.wait()
        await original_close()
    owner.control_mailbox.close = failing_then_held_close
    try:
        clock[0] = 61000
        await asyncio.wait_for(second_attempt.wait(), 3.5)
        assert not manager.gc.done(), 'A local cleanup failure terminated the maintenance timer'
        assert first.address not in registry and manager.pool.loaded_count == 1
        try:
            await manager.get_map(first, request_id='too-early-reload', deadline_ms=71000)
        except ValueError:
            pass
        else:
            raise AssertionError('Retired Adapter resources were reused before cleanup terminated')
        other = await manager.get_map(second, request_id='independent-load', deadline_ms=71000)
        assert (await asyncio.wait_for(other.mailbox.call('inspect_lifecycle', clock[0]), 1)).address == second.address
        # Keep the other map occupied: only the first projection should retire.
        from game_runtime import Position
        await other.mailbox.call('join', Position(2, 1, (1501, 16, 16), 1, (1, 1)))
        completion = asyncio.create_task(manager.collect())
        await asyncio.sleep(0)
        assert manager.pool.loaded_count == 2
        release.set()
        assert await asyncio.wait_for(completion, 1) == (first.address,)
        assert attempts == [1, 2] and owner.control_mailbox.task.done()
        assert manager.pool.loaded_count == 1 and second.address in registry
        rebuilt = await manager.get_map(first, request_id='after-terminal-reload', deadline_ms=71000)
        assert rebuilt.story_handle.map_generation != owner.story_handle.map_generation
        return dict(error=error_type.__name__, timer_survived=True, cleanup_attempts=2,
            slot_retained_until_adapter_terminal=True, another_map_progressed=True,
            same_address_new_generation_after_cleanup=True)
    finally:
        release.set()
        await manager.stop()
        owner.control_mailbox.close = original_close
        if not owner.control_mailbox.task.done():
            await original_close()
        for active in tuple(registry.values()):
            if not active.mailbox.task.done():
                await active.mailbox.close()
        await manager.close()


def main():
    async def run():
        return await asyncio.gather(check(ConnectionError), check(TimeoutError))
    results = asyncio.run(asyncio.wait_for(run(), 12))
    report = dict(passed=results, directory_authorization_fixture=True,
        actual_timer_and_map_mailboxes=True, live_server_changed=False,
        native_gui_verified=False, battle_executed=False)
    write_json(OUT/'evidence/story-cleanup-retry-verification.json', report)
    print(report)


if __name__ == '__main__':
    main()
