"""Probe the actual server entry with controlled account I/O and two TCP peers.

Disposable storage and an ephemeral loopback port only. The independent peer
thread releases slow account I/O after heartbeat receipt or a bounded timeout.
No native client, live account storage or shared listener is touched.
"""
import argparse
import asyncio
from contextlib import closing
import hashlib
import hmac
import json
from pathlib import Path
import socket
import struct
import tempfile
from threading import Event, Thread
from unittest.mock import patch

from accounts import AccountStore
from inspect_client import OUT, write_json
import serve
from wire import FrameReader, frame, octets, read_octets


def receive(sock, reader, wanted):
    while True:
        data = sock.recv(65536)
        if not data:
            raise ConnectionError('Peer closed during isolation probe')
        for kind, body in reader.feed(data):
            if kind == wanted:
                return body


async def probe(entry='serve'):
    entered, release, listening = Event(), Event(), Event()
    result = {'entry': 'serve.main' if entry == 'serve' else 'GameRuntime.handle_socket',
              'transport': 'two real TCP connections',
              'database': 'disposable', 'heartbeat_while_account_io_pending': False,
              'live_server_modified': False}
    port = []

    class SlowAccounts(AccountStore):
        def account(self, identity):
            entered.set()
            if not release.wait(5):
                raise TimeoutError('Isolation probe did not release account I/O')
            return super().account(identity)

    original_start = asyncio.start_server

    async def ephemeral_start(callback, *args, **kwargs):
        # Keep the production handler, change only the test listener address.
        kwargs.pop('host', None)
        kwargs.pop('port', None)
        server = await original_start(callback, '127.0.0.1', 0, **kwargs)
        port.append(server.sockets[0].getsockname()[1])
        listening.set()
        return server

    def peers():
        try:
            if not listening.wait(10):
                raise TimeoutError('Server did not reach listen')
            with closing(socket.create_connection(('127.0.0.1', port[0]), timeout=3)) as slow:
                slow_reader = FrameReader()
                challenge, _ = read_octets(receive(slow, slow_reader, 101))
                with closing(socket.create_connection(('127.0.0.1', port[0]), timeout=3)) as healthy:
                    healthy_reader = FrameReader()
                    receive(healthy, healthy_reader, 101)
                    secret = hashlib.md5(b'11111111').digest()
                    proof = hmac.new(secret, challenge, hashlib.md5).digest()
                    slow.sendall(frame(103, octets(b'1111') + octets(proof)
                                       + bytes(4) + octets(b'') + bytes(4) + octets(b'')))
                    if not entered.wait(3):
                        raise TimeoutError('Account request did not enter injected I/O')
                    healthy.settimeout(1)
                    body = struct.pack('>I', 12345)
                    healthy.sendall(frame(100, body))
                    try:
                        reply = receive(healthy, healthy_reader, 100)
                    except socket.timeout:
                        result['observation'] = 'heartbeat blocked until account I/O release'
                    else:
                        result['heartbeat_while_account_io_pending'] = (
                            reply == body and not release.is_set())
                        result['observation'] = 'heartbeat returned before account I/O release'
        except Exception as exc:
            result['probe_error'] = type(exc).__name__ + ': ' + str(exc)
        finally:
            release.set()

    with tempfile.TemporaryDirectory(prefix='gateway-isolation-') as temp:
        fixture_root = Path(temp)
        (fixture_root / 'runtime').mkdir()
        store = SlowAccounts(fixture_root / 'accounts.sqlite3')
        async def selected_main():
            if entry == 'serve':
                return await serve.main()
            from game_runtime import GameRuntime
            import runtime_storage
            prepared = await asyncio.to_thread(runtime_storage.prepare, store)
            runtime = GameRuntime(store, prepared)
            try:
                server = await asyncio.start_server(runtime.handle_socket, '127.0.0.1', 0)
                async with server:
                    await server.serve_forever()
            finally:
                await runtime.close()
        # Startup fixtures are created before entering the server event loop.
        with patch.object(serve, 'AccountStore', lambda *a, **kw: store), \
                patch.object(serve, 'OUT', fixture_root), \
                patch.object(serve, 'log', lambda **event: None), \
                patch.object(asyncio, 'start_server', ephemeral_start):
            worker = Thread(target=peers, name='gateway-isolation-peer', daemon=True)
            worker.start()
            server_task = asyncio.create_task(selected_main())
            try:
                await asyncio.to_thread(worker.join, 15)
                if worker.is_alive():
                    result['probe_error'] = 'Peer thread did not stop'
            finally:
                release.set()
                server_task.cancel()
                try:
                    await server_task
                except asyncio.CancelledError:
                    pass
                await asyncio.sleep(0.05)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--entry', choices=('serve', 'runtime'), default='serve')
    parser.add_argument('--expect-blocked', action='store_true',
                        help='Capture a reproducible failing baseline')
    args = parser.parse_args()
    result = asyncio.run(probe(args.entry))
    result['baseline_mode'] = args.expect_blocked
    filename = 'runtime-isolation-verification.json' if args.entry == 'runtime' else 'gateway-isolation-verification.json'
    write_json(OUT / 'evidence' / filename, result)
    if args.expect_blocked:
        write_json(OUT / 'evidence/gateway-isolation-baseline.json', result)
    print(json.dumps(result))
    if result.get('probe_error'):
        raise SystemExit(2)
    passed = result['heartbeat_while_account_io_pending']
    if passed == args.expect_blocked:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
