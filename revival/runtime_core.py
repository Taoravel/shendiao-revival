"""Bounded entity mailboxes and partitioned blocking I/O, with no world lock.

All queue accounting lives on the asyncio loop. Worker threads receive only
storage Adapter calls, never Sessions, writers, or mutable gameplay state.
"""
import asyncio
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import datetime
import hashlib
import json
import time
import uuid


class Backpressure(RuntimeError):
    pass


class StaleEpoch(ValueError):
    pass


@dataclass(frozen=True)
class Command:
    operation: str
    args: tuple
    request_id: str
    deadline: float


class SerialOwner:
    """One key, one sequential handler, bounded pending commands, no global lock.

    Cancellation abandons the reply, not an already submitted command/commit.
    Handlers must fence durable writes and avoid cycles between owner calls.
    """
    def __init__(self, key, handler, capacity=64, metrics=None):
        if type(capacity) is not int or capacity < 1:
            raise ValueError('Positive integer mailbox capacity required')
        self.key, self.handler = key, handler
        self.queue = asyncio.Queue(maxsize=capacity)
        self.metrics = metrics if metrics is not None else Counter()
        self.accepting = True
        self.task = asyncio.create_task(self._run(), name=f'owner:{key}')

    async def call(self, operation, *args, request_id=None, deadline=None):
        if not self.accepting:
            raise StaleEpoch('Owner closed')
        command = Command(operation, args, request_id or uuid.uuid4().hex,
                          deadline if deadline is not None else time.monotonic()+10)
        reply = asyncio.get_running_loop().create_future()
        try:
            self.queue.put_nowait((command, reply, time.monotonic()))
        except asyncio.QueueFull:
            self.metrics['mailbox_rejected'] += 1
            raise Backpressure(f'Owner mailbox full: {self.key}') from None
        self.metrics['mailbox_high_water'] = max(self.metrics['mailbox_high_water'], self.queue.qsize())
        # Observe eventual errors even if a caller times out or disconnects.
        reply.add_done_callback(lambda f: f.exception() if not f.cancelled() else None)
        return await asyncio.shield(reply)

    async def _run(self):
        while True:
            item = await self.queue.get()
            if item is None:
                self.queue.task_done()
                return
            command, reply, queued = item
            start = time.monotonic()
            self.metrics['wait_microseconds'] += int((start-queued)*1e6)
            try:
                if start > command.deadline:
                    self.metrics['deadline_rejected'] += 1
                    raise TimeoutError('Command deadline expired before execution')
                result = await self.handler(command)
                reply.set_result(result)
            except Exception as error:
                reply.set_exception(error)
            finally:
                self.metrics['commands'] += 1
                self.metrics['execute_microseconds'] += int((time.monotonic()-start)*1e6)
                self.queue.task_done()

    async def close(self):
        self.accepting = False
        # Finish accepted work. No task cancellation of a possible commit.
        await self.queue.join()
        self.queue.put_nowait(None)
        await self.task


class BlockingIO:
    """Independent bounded I/O partitions; there is no all-server executor.

    Capacity includes running work. A timed-out thread retains its slot until
    it actually ends, preventing unbounded executor queues after cancellations.
    """
    def __init__(self, partitions=8, workers_per_partition=2, capacity=32):
        if any(type(v) is not int or v < 1 for v in (partitions, workers_per_partition, capacity)):
            raise ValueError('Positive I/O limits required')
        self.executors = [ThreadPoolExecutor(max_workers=workers_per_partition,
                          thread_name_prefix=f'persist-{i}') for i in range(partitions)]
        self.pending = [0]*partitions
        self.capacity = capacity
        self.metrics = Counter()
        self.closed = False

    def partition(self, key):
        # Stable across interpreter processes; deployment can replace this router.
        value = hashlib.blake2b(str(key).encode(), digest_size=8).digest()
        return int.from_bytes(value, 'big') % len(self.executors)

    async def run(self, key, operation, *args, timeout=10):
        if self.closed:
            raise RuntimeError('Persistence closed')
        part = self.partition(key)
        if self.pending[part] >= self.capacity:
            self.metrics['rejected'] += 1
            raise Backpressure(f'Persistence partition full: {part}')
        self.pending[part] += 1
        self.metrics['high_water'] = max(self.metrics['high_water'], self.pending[part])
        start = time.monotonic()
        future = asyncio.get_running_loop().run_in_executor(self.executors[part], operation, *args)
        def completed(f):
            self.pending[part] -= 1
            self.metrics['completed'] += 1
            self.metrics['total_microseconds'] += int((time.monotonic()-start)*1e6)
            if not f.cancelled():
                f.exception()
        future.add_done_callback(completed)
        try:
            return await asyncio.wait_for(asyncio.shield(future), timeout)
        except TimeoutError:
            self.metrics['timeouts'] += 1
            raise

    async def close(self):
        self.closed = True
        # Startup/teardown only; do not wait synchronously on the network loop.
        await asyncio.gather(*(asyncio.to_thread(e.shutdown, wait=True) for e in self.executors))


class AsyncLog:
    """Bounded diagnostic logging, independent of persistence work resources.

    Diagnostics drop with a counter on saturation; durable receipts belong in
    the asset transaction, never in this best-effort queue.
    """
    def __init__(self, path, capacity=2048, sink=None):
        if type(capacity) is not int or capacity < 1:
            raise ValueError('Positive integer log capacity required')
        self.path, self.sink = path, sink or self._append
        self.queue = asyncio.Queue(maxsize=capacity)
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='diagnostic-log')
        self.metrics = Counter()
        self.task = asyncio.create_task(self._run(), name='diagnostic-log')

    def emit(self, **event):
        event['time'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        try:
            self.queue.put_nowait(event)
        except asyncio.QueueFull:
            self.metrics['dropped'] += 1

    def _append(self, events):
        with self.path.open('a', encoding='utf-8') as stream:
            for event in events:
                stream.write(json.dumps(event, ensure_ascii=False)+'\n')

    async def _run(self):
        while True:
            event = await self.queue.get()
            if event is None:
                self.queue.task_done()
                return
            batch = [event]
            while len(batch) < 64 and not self.queue.empty():
                # Sentinel is added only after queue.join in close().
                batch.append(self.queue.get_nowait())
            try:
                await asyncio.get_running_loop().run_in_executor(self.executor, self.sink, batch)
            except Exception:
                self.metrics['write_failures'] += len(batch)
            finally:
                for _ in batch:
                    self.queue.task_done()

    async def close(self):
        await self.queue.join()
        self.queue.put_nowait(None)
        await self.task
        await asyncio.to_thread(self.executor.shutdown, wait=True)
