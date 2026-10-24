"""One held retirement must not stop timer scans for a later idle map.

Explicit directory/catalog/clock and close-delay Adapters; actual map owners
and maintenance timer. No database, sockets, live roles, GUI or battles.
"""
import argparse
import asyncio
import hashlib
import json

from game_runtime import MapOwner
from inspect_client import OUT, write_json
from runtime_story_maps import RuntimeStoryMaps
from world_owner import MapAddress
from world_story_instances import StoryInstanceRules, StoryInstance, StoryInstanceIntent


async def check():
    rules = StoryInstanceRules('2026-10-23.story-instance.1', 'newbie_bloodmark_dream',
        1501, 0, 2**62, 2**63, 8, 1, 128, 60000, 64, 64, None, {(9, 11):100106})

    def record(role):
        return StoryInstance(rules.kind, role, 1,
            StoryInstanceIntent('chapter'+str(role), 'creation'+str(role), 'policy', 'route', 100106),
            rules.revision, MapAddress(1501, 2**62+role, 0))

    first, second = record(1), record(2)
    clock, registry = [1000], {}
    first_entered, first_release, other_retired = asyncio.Event(), asyncio.Event(), asyncio.Event()

    def create(entry):
        owner = MapOwner(entry.address, {1501:dict(available=True, width=4096, height=4096)}, story_rules=rules)
        registry[entry.address] = owner
        return owner

    def forget(address, owner):
        assert registry.pop(address) is owner
        if address == second.address:
            other_retired.set()

    manager = RuntimeStoryMaps(rules, create, forget, clock=lambda:clock[0])
    first_owner = await manager.get_map(first, request_id='load-first', deadline_ms=10000)
    original_close = first_owner.control_mailbox.close

    async def held_close():
        first_entered.set()
        await first_release.wait()
        await original_close()

    first_owner.control_mailbox.close = held_close
    try:
        clock[0] = 61000
        await asyncio.wait_for(first_entered.wait(), 2)
        assert manager.pool.loaded_count == 1 and first.address not in registry
        other = await manager.get_map(second, request_id='load-later-map', deadline_ms=71000)
        assert (await other.mailbox.call('inspect_lifecycle', clock[0])).address == second.address
        clock[0] += rules.idle_unload_after_ms
        try:
            await asyncio.wait_for(other_retired.wait(), 2.2)
            independent_collection = True
        except TimeoutError:
            independent_collection = False
        assert not first_release.is_set() and not first_owner.control_mailbox.task.done()
        first_release.set()
        # Positive control: the very same second map is collectable once the
        # held cleanup ends, so a negative result is not bad idle eligibility.
        await asyncio.wait_for(other_retired.wait(), 2)
        return dict(other_collected_before_first_cleanup=independent_collection,
            same_other_map_collected_after_release=True, actual_periodic_timer=True,
            directory_catalog_and_clock_fixtures=True, held_close_adapter=True,
            explicit_collect_called=False, live_service_changed=False,
            live_database_accessed=False, native_gui_verified=False, battle_executed=False)
    finally:
        first_release.set()
        await manager.stop()
        for owner in tuple(registry.values()):
            if not owner.mailbox.task.done():
                await owner.mailbox.close()
        await manager.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--expect-blocked', action='store_true')
    args = parser.parse_args()
    names = ('game_runtime.py', 'runtime_story_maps.py', 'world_owner.py', 'runtime_core.py',
             'world_story_projection_pool.py', 'verify_story_gc_isolation.py')
    before = {name:hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in names}
    result = asyncio.run(asyncio.wait_for(check(), 10))
    assert before == {name:hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in names}
    result['source_hashes_unchanged'] = before
    suffix = 'baseline' if args.expect_blocked else 'verification'
    write_json(OUT/f'evidence/story-gc-isolation-root-{suffix}.json', result)
    print(json.dumps(result))
    if args.expect_blocked:
        assert not result['other_collected_before_first_cleanup'], 'The observed maintenance bottleneck no longer reproduces'
    else:
        assert result['other_collected_before_first_cleanup'], 'One held Adapter cleanup blocked later independent map reclamation scans'


if __name__ == '__main__':
    main()
