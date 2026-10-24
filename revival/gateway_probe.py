"""Loopback-only diagnostic listener; does not claim authentication success."""
import asyncio
import datetime
import hashlib
import json
from inspect_client import OUT

TRACE = OUT / 'evidence/gateway-probe'


def record(event, **fields):
    TRACE.mkdir(parents=True, exist_ok=True)
    item = {'time': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'event': event, **fields}
    with (TRACE / 'events.jsonl').open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(item) + '\n')


async def handle(reader, writer):
    identifier = datetime.datetime.now(datetime.timezone.utc).strftime('%H%M%S%f')
    record('connected', connection=identifier)
    total = 0
    try:
        while total < 65536:
            data = await asyncio.wait_for(reader.read(min(4096, 65536-total)), 120)
            if not data:
                break
            total += len(data)
            with (TRACE / (identifier + '.bin')).open('ab') as stream:
                stream.write(data)
            record('received', connection=identifier, size=len(data), sha256=hashlib.sha256(data).hexdigest())
    except (TimeoutError, ConnectionError) as error:
        record('connection_end', connection=identifier, reason=type(error).__name__)
    finally:
        writer.close()
        await writer.wait_closed()
        record('closed', connection=identifier, received=total)


async def main():
    server = await asyncio.start_server(handle, '127.0.0.1', 28993)
    record('listening', address='127.0.0.1', port=28993, mode='capture only; no login implementation')
    async with server:
        await asyncio.sleep(1800)


if __name__ == '__main__':
    asyncio.run(main())
