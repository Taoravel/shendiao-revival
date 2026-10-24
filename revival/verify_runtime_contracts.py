"""Independent bounded-work and cancellation contracts for the runtime core."""
import asyncio
from pathlib import Path
import tempfile
from threading import Event
import unittest

from runtime_core import AsyncLog, Backpressure, BlockingIO, SerialOwner, StaleEpoch


class RuntimeContracts(unittest.IsolatedAsyncioTestCase):
    async def test_invalid_capacities_never_create_unbounded_mailboxes(self):
        async def handler(command):
            return None
        for capacity in (0, -1):
            owner = None
            try:
                try:
                    owner = SerialOwner('invalid', handler, capacity=capacity)
                except ValueError:
                    continue
                self.fail('SerialOwner accepted an unbounded mailbox capacity')
            finally:
                if owner is not None:
                    await owner.close()

    async def test_invalid_log_capacity_fails_before_accepting_events(self):
        with tempfile.TemporaryDirectory() as temp:
            for capacity in (0, -1):
                log = None
                try:
                    try:
                        log = AsyncLog(Path(temp) / 'log.jsonl', capacity=capacity)
                    except ValueError:
                        continue
                    self.fail('AsyncLog accepted an unbounded mailbox capacity')
                finally:
                    if log is not None:
                        await log.close()

    async def test_cancelled_caller_does_not_undo_accepted_command(self):
        entered, release = asyncio.Event(), asyncio.Event()
        applied = []
        async def handler(command):
            if command.operation == 'slow':
                entered.set()
                await release.wait()
            applied.append(command.operation)
            return command.operation
        owner = SerialOwner('role-a', handler, capacity=1)
        independent = SerialOwner('role-b', handler, capacity=1)
        first = asyncio.create_task(owner.call('slow'))
        try:
            await asyncio.wait_for(entered.wait(), 1)
            first.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await first
            second = asyncio.create_task(owner.call('after'))
            await asyncio.sleep(0)
            with self.assertRaises(Backpressure):
                await owner.call('overflow')
            self.assertEqual(await asyncio.wait_for(independent.call('independent'), 1), 'independent')
            self.assertEqual(applied, ['independent'])
            release.set()
            self.assertEqual(await asyncio.wait_for(second, 1), 'after')
            self.assertEqual(applied, ['independent', 'slow', 'after'])
        finally:
            release.set()
            await owner.close()
            await independent.close()
        with self.assertRaises(StaleEpoch):
            await owner.call('late')

    async def test_cancelled_io_retains_capacity_until_actual_completion(self):
        entered, release = Event(), Event()
        io = BlockingIO(partitions=1, workers_per_partition=1, capacity=1)
        def slow():
            entered.set()
            if not release.wait(3):
                raise TimeoutError('Probe release missing')
            return 'committed'
        call = asyncio.create_task(io.run('role-a', slow))
        try:
            self.assertTrue(await asyncio.to_thread(entered.wait, 1))
            call.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await call
            with self.assertRaises(Backpressure):
                await io.run('role-b', lambda: 'unexpected')
        finally:
            release.set()
            await io.close()


if __name__ == '__main__':
    unittest.main(verbosity=2)
