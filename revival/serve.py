"""Loopback listener for partitioned owners and connection-owned encrypted sends."""
import argparse
import asyncio
import datetime
import hashlib
import json
import os
from pathlib import Path
from accounts import AccountStore
from game_runtime import GameRuntime
from runtime_core import AsyncLog
import runtime_storage
from inspect_client import OUT


def log(**event):
    """Compatibility diagnostic hook; live diagnostics use AsyncLog."""
    pass


async def main(training_battle=False):
    store = await asyncio.to_thread(AccountStore, OUT/'runtime/accounts.sqlite3')
    prepared = await asyncio.to_thread(runtime_storage.prepare, store)
    await asyncio.to_thread(record_deployment)
    logger = AsyncLog(OUT/'runtime/gateway.jsonl')
    runtime = GameRuntime(store,prepared,logger=logger,training=training_battle)
    server = await asyncio.start_server(runtime.handle_socket,'127.0.0.1',28993,limit=65536)
    logger.emit(event='listening',host='127.0.0.1',port=28993,capability='partitioned_owners_experimental')
    try:
        async with server:
            await server.serve_forever()
    finally:
        await runtime.close()
        await logger.close()


def record_deployment():
    root=Path(__file__).parent
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.glob('*.py'))}
    record={'pid':os.getpid(),'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'source_sha256_at_startup':hashes,'scope':'startup file snapshot; later edits require redeployment'}
    (OUT/'runtime/deployment.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--training-battle',action='store_true',help='Experimental training; native UI QA pending')
    asyncio.run(main(training_battle=parser.parse_args().training_battle))
