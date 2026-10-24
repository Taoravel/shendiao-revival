"""A real mailbox rejects one expired retirement; later maintenance must recover."""
import asyncio
from pathlib import Path
import tempfile
import time

from accounts import AccountStore
from game_runtime import GameRuntime
from inspect_client import OUT, write_json
from verify_runtime_private_role import fixtures
import runtime_storage


class ExpireOneRetirement:
    """Actual SerialOwner deadline rejection, rather than a fabricated reply."""
    def __init__(self, raw):
        self.raw = raw
        self.expired = False

    def __getattr__(self, name):
        return getattr(self.raw, name)

    async def call(self, operation, *args, **kwargs):
        if operation == 'retire_idle' and not self.expired:
            self.expired = True
            kwargs['deadline'] = time.monotonic()-1
        return await self.raw.call(operation, *args, **kwargs)


async def check(store, prepared):
    entries, _ = await fixtures(store, prepared)
    record = entries[0][1]
    clock = [1000]
    runtime = GameRuntime(store, prepared, story_clock=lambda: clock[0])
    try:
        runtime.story_maps.gc.cancel()
        await asyncio.gather(runtime.story_maps.gc, return_exceptions=True)
        owner = await runtime.story_maps.get_map(record, request_id='maintenance-load', deadline_ms=10000)
        initial = await owner.mailbox.call('inspect_lifecycle', clock[0])
        assert initial.idle
        assert await runtime.story_maps.collect() == ()
        owner.control_mailbox = ExpireOneRetirement(owner.control_mailbox)
        clock[0] += store.story_instance_rules.idle_unload_after_ms
        try:
            assert await runtime.story_maps.collect() == ()
        except TimeoutError:
            pass
        assert owner.control_mailbox.metrics['deadline_rejected'] == 1
        assert runtime.story_maps.pool.loaded_count == 1
        assert runtime.registered_map(record.address) is owner
        assert await runtime.story_maps.collect() == (record.address,), (
            'A terminal mailbox deadline lost the unload identity and permanently fenced an empty private map')
        assert runtime.story_maps.pool.loaded_count == 0
        assert runtime.registered_map(record.address) is None
        return dict(passed=['real mailbox expiry preserves the occupied slot while its retirement is unconfirmed',
            'confirmed live refusal releases the unload fence; next pass drains the original map Adapter'],
            initial_directory_fixture=True, deadline_adapter='one real SerialOwner queued-deadline rejection',
            live_server_changed=False, native_gui_verified=False, battle_executed=False)
    finally:
        await runtime.close()


def main():
    with tempfile.TemporaryDirectory(prefix='story-maintenance-') as directory:
        store = AccountStore(Path(directory)/'state.sqlite3')
        result = asyncio.run(asyncio.wait_for(check(store, runtime_storage.prepare(store)), 45))
    write_json(OUT/'evidence/story-maintenance-recovery-verification.json', result)
    print(result)


if __name__ == '__main__':
    main()
