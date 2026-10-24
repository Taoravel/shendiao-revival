"""Reproduce the old network loop stalling behind a controlled storage wait."""
import asyncio
import threading
import time
from gateway import Session
from wire import frame, octets
from inspect_client import OUT, write_json


async def probe():
    released = threading.Event()
    progressed = asyncio.Event()
    class SlowStore:
        def account(self, _):
            if not released.wait(1):
                raise AssertionError('Fixture release missing')
            return None
    async def peer():
        await asyncio.sleep(.01)
        progressed.set()
    other = asyncio.create_task(peer())
    timer = threading.Timer(.15, released.set)
    timer.start()
    start = time.monotonic()
    try:
        try:
            Session(SlowStore()).feed(frame(103, octets(b'fixture')+octets(bytes(16))+
                                           bytes(4)+octets(b'')+bytes(4)+octets(b'')))
        except ValueError:
            pass
        verdict = progressed.is_set()
        result = {'other_connection_progressed_before_storage_release': verdict,
                  'loop_blocked_seconds': round(time.monotonic()-start, 3),
                  'expected_architecture_criterion_passed': verdict}
        write_json(OUT/'evidence/runtime-legacy-blocking.json', result)
        print(result)
        await other
    finally:
        released.set()
        timer.join()
    assert verdict, 'Legacy Session.feed blocked the network loop behind storage'


if __name__ == '__main__':
    asyncio.run(probe())
