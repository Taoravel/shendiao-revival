"""A timed-out role storage operation must not be overtaken by another write."""
import asyncio
from pathlib import Path
import tempfile
from threading import Event
from unittest.mock import patch

from accounts import AccountStore
from game_runtime import GameRuntime, RoleOwner
from inventory import AssetChange
from runtime_core import BlockingIO, StaleEpoch, Backpressure
import runtime_storage
from inspect_client import OUT, write_json


class ShortIO(BlockingIO):
    async def run(self, key, operation, *args, timeout=10):
        return await super().run(key, operation, *args, timeout=0.05)


async def check(accounts, prepared, role, epoch):
    entered, release, first_finished = Event(), Event(), Event()
    io = ShortIO(partitions=1, workers_per_partition=2, capacity=4)
    runtime = GameRuntime(accounts, prepared, io=io)
    owner = RoleOwner(runtime, role, 1111, epoch)
    runtime.roles[role['id']] = owner
    original = runtime_storage.settle
    result = {'same_role_storage_overtook_timed_out_write': False,
              'database': 'disposable', 'live_server_changed': False}

    def gated(*args):
        change = args[-1]
        if change.settlement_id == 'order:first':
            entered.set()
            if not release.wait(3):
                raise TimeoutError('Probe release missing')
            try:
                return original(*args)
            finally:
                first_finished.set()
        if not first_finished.is_set():
            result['same_role_storage_overtook_timed_out_write'] = True
        return original(*args)

    with patch.object(runtime_storage, 'settle', gated):
        first = asyncio.create_task(owner.mailbox.call('settle', AssetChange('order:first', grants=((31000, 1),))))
        second = None
        try:
            assert await asyncio.to_thread(entered.wait, 1)
            # A caller deadline may expire; this must not release write ownership.
            done, _ = await asyncio.wait({first}, timeout=0.15)
            if first in done:
                try:
                    await first
                except TimeoutError:
                    result['first_wait_timed_out'] = True
                else:
                    raise AssertionError('Paused write returned before release')
                second = asyncio.create_task(owner.mailbox.call('settle', AssetChange('order:second', grants=((31000, 1),))))
                done, _ = await asyncio.wait({second}, timeout=0.2)
                if second in done:
                    try:
                        await second
                    except StaleEpoch:
                        result['role_fenced_until_outcome_recovery'] = True
                else:
                    result['ownership_retained_until_io_completion'] = True
            else:
                result['ownership_retained_until_io_completion'] = True
        finally:
            release.set()
            await asyncio.gather(*(t for t in (first, second) if t is not None), return_exceptions=True)
            await owner.mailbox.close()
            await runtime.close()
    return result


def main():
    with tempfile.TemporaryDirectory(prefix='runtime-io-order-') as temp:
        accounts = AccountStore(Path(temp) / 'state.sqlite3')
        role = accounts.create_role(1111, '顺序检查', 12, 1010101)
        prepared = runtime_storage.prepare(accounts)
        epoch = accounts.acquire_lease(1111, role['id'])
        result = asyncio.run(check(accounts, prepared, role, epoch))
    write_json(OUT / 'evidence/runtime-io-order-verification.json', result)
    print(result)
    if result['same_role_storage_overtook_timed_out_write']:
        raise SystemExit(1)
    if not (result.get('role_fenced_until_outcome_recovery') or result.get('ownership_retained_until_io_completion')):
        raise AssertionError('No ordering guard observed')


if __name__ == '__main__':
    main()
