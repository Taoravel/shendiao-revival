"""A real queued finish expires once; GC must finish its exact retained ticket."""
import asyncio
from pathlib import Path
import tempfile
import time

from accounts import AccountStore
from game_runtime import GameRuntime
from inspect_client import OUT, write_json
from verify_runtime import Peer
from verify_runtime_private_role import fixtures
import runtime_storage


class ExpireOneFinish:
    def __init__(self, raw):
        self.raw, self.expired = raw, False

    def __getattr__(self, name):
        return getattr(self.raw, name)

    async def call(self, operation, *args, **kwargs):
        if operation == 'finish_scene_delivery' and not self.expired:
            self.expired = True
            kwargs['deadline'] = time.monotonic()-1
        return await self.raw.call(operation, *args, **kwargs)


async def check(store, prepared):
    entries, _ = await fixtures(store, prepared)
    role, record = entries[0]
    clock = [1000]
    runtime = GameRuntime(store, prepared, story_clock=lambda: clock[0])
    try:
        runtime.story_maps.gc.cancel()
        await asyncio.gather(runtime.story_maps.gc, return_exceptions=True)
        peer = Peer(runtime)
        await peer.login(role)
        owner = runtime.roles[role['id']]
        target = runtime.registered_map(record.address)
        location = await target.mailbox.call('location', owner.id, owner.epoch)
        delivery = await runtime.story_maps.begin_delivery(target, location, peer.connection.generation)
        target.control_mailbox = ExpireOneFinish(target.control_mailbox)
        await peer.connection.cleanup_delivery(delivery)
        pending = await target.mailbox.call('inspect_lifecycle', clock[0])
        assert pending.pending_scene_deliveries == 1
        assert target.control_mailbox.metrics['deadline_rejected'] == 1
        await peer.connection.close()
        assert await runtime.story_maps.collect() == ()
        cleaned = await target.mailbox.call('inspect_lifecycle', clock[0])
        assert cleaned.pending_scene_deliveries == 0, 'Expired scene cleanup lost its only retry owner'
        assert cleaned.idle
        clock[0] += store.story_instance_rules.idle_unload_after_ms
        assert await runtime.story_maps.collect() == (record.address,)
        assert runtime.registered_map(record.address) is None
        return dict(passed=[
            'actual expired finish retains the pending world ticket and occupied pin',
            'after disconnect a later map maintenance pass retries that exact ticket',
            'confirmed finish clears scene accounting and only then permits full-idle retirement'],
            initial_private_checkpoint_fixture=True, actual_mailbox_deadline=True,
            live_server_changed=False, native_gui_verified=False, battle_executed=False)
    finally:
        await runtime.close()


def main():
    with tempfile.TemporaryDirectory(prefix='scene-cleanup-recovery-') as directory:
        store = AccountStore(Path(directory)/'state.sqlite3')
        result = asyncio.run(asyncio.wait_for(check(store, runtime_storage.prepare(store)), 45))
    write_json(OUT/'evidence/scene-cleanup-recovery-verification.json', result)
    print(result)


if __name__ == '__main__':
    main()
