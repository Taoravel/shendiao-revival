"""An early encrypted world ACK must not bypass the exact scene drain gate.

Uses actual ConnectionOwner, role/map owners, codec and temporary storage.
Only Writer.drain is delayed. The ACK is sent before that drain completes,
so the old joined guard cannot substitute for movement declaration checks.
"""
import argparse
import asyncio
import hashlib
import importlib
from pathlib import Path
import struct
import sys
import tempfile

import inspect_client
if __name__ == '__main__':
    bootstrap = argparse.ArgumentParser(add_help=False)
    bootstrap.add_argument('--runtime-source', type=Path)
    bootstrap.add_argument('--runtime-harness', type=Path)
    selected, _ = bootstrap.parse_known_args()
    if selected.runtime_source is not None:
        source = selected.runtime_source.resolve(strict=True)
        sys.path.insert(0, str(source))
        inspect_client.OUT = source
        if selected.runtime_harness is not None:
            harness = selected.runtime_harness.resolve(strict=True)
            for path in harness.iterdir():
                importable = (path.is_file() and path.suffix in ('.py', '.pyc', '.pyd')
                              or path.is_dir() and any(path.glob('__init__.*')))
                if importable and not path.name.startswith(('verify_', 'research_', 'diagnose_')):
                    raise ValueError('Only explicit test helpers allowed in harness: '+path.name)
            sys.path.insert(0, str(harness))
        # Keep original asset routing, but load parsers from this candidate
        # before constructing any runtime classes or reading original assets.
        for module in ('pfs', 'bxml'):
            sys.modules.pop(module, None)
        inspect_client.PfsArchive = importlib.import_module('pfs').PfsArchive
        inspect_client.decode = importlib.import_module('bxml').decode

from accounts import AccountStore
from game_runtime import GameRuntime
from inspect_client import OUT, write_json
import runtime_storage
from verify_runtime import Writer
from verify_world_resource_runtime import MapPeer, Events, checkpoint_fixture
from wire import frame
from world_protocol import ENTER_WORLD, ENTER_SCENE, AFTER_ENTER_WORLD


class GatedWriter(Writer):
    """External I/O Adapter, usable with both historical and current runtimes."""
    def __init__(self):
        super().__init__()
        self.remaining = None
        self.entered, self.release = asyncio.Event(), asyncio.Event()

    async def drain(self):
        if self.remaining is not None:
            self.remaining -= 1
            if self.remaining == 0:
                self.remaining = None
                self.entered.set()
                await self.release.wait()
        await super().drain()


class EarlyAckPeer(MapPeer):
    async def request(self, kind, body):
        if kind == 0xc0005:
            self.writer.remaining = 3
        replies = await super().request(kind, body)
        if kind == 0xc0005:
            # The original Peer.login expects its three entry frames alone.
            # Demultiplex later initialization frames from the SAME decoded
            # encrypted stream; no packet or server callback is fabricated.
            entry_types = (ENTER_WORLD, 0xc0007, ENTER_SCENE)
            self.early_initial = [message for message in replies if message[0] not in entry_types]
            return [message for message in replies if message[0] in entry_types]
        return replies


def sources():
    names = ('game_runtime', 'runtime_storage', 'world_owner',
        'world_movement', 'world_catalog', 'world_collision', 'verify_runtime',
        'verify_world_resource_runtime', 'verify_world_movement_delivery_boundaries')
    if 'runtime_movement' in sys.modules:
        names += ('runtime_movement',)
    result = {}
    for name in names:
        path = (Path(__file__).resolve() if name == 'verify_world_movement_delivery_boundaries'
                else Path(importlib.import_module(name).__file__).resolve())
        result[name] = dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    for name in ('design/world-movement-state-v1.json', 'evidence/native-image.bin'):
        path = OUT/name
        if path.exists():
            result[name] = dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    return result


def production_imports(source):
    if source is None:
        return {}
    result = {}
    for path in source.resolve().glob('*.py'):
        if path.stem == 'inspect_client' or path.stem.startswith(('verify_', 'research_', 'diagnose_')):
            continue
        module = sys.modules.get(path.stem)
        if module is not None:
            actual = Path(module.__file__).resolve()
            assert actual == path.resolve(), 'Production import outside candidate: '+path.stem
            result[path.stem] = dict(path=str(actual), sha256=hashlib.sha256(actual.read_bytes()).hexdigest())
    return result


async def map_rejection(runtime, owner, position, kind, body):
    try:
        await runtime.map(owner.map_address).mailbox.call('move_for_encounter',
            owner.id, owner.epoch, position.version, kind, body)
    except ValueError as error:
        return str(error)
    raise AssertionError('Map accepted an operation expected to be refused')


async def check(store, prepared, role, result):
    start, clear, wall = (360, 2264), (361, 2264), (1664, 960)
    checkpoint_fixture(store, role, (1006, *start))
    events = Events()
    runtime = GameRuntime(store, prepared, logger=events)
    peer = EarlyAckPeer(runtime)
    peer.writer = peer.connection.writer = GatedWriter()
    writer = peer.writer
    login = asyncio.create_task(peer.login(role))
    result.update(scope='actual encrypted early ACK, joined member, then movement before exact writer drain',
        explicit_initial_checkpoint_fixture=True, native_gui_verified=False,
        live_server_changed=False, battle_executed=False)
    try:
        await asyncio.wait_for(writer.entered.wait(), 4)
        owner = runtime.roles[role['id']]
        assert not owner.joined
        # The scene frame has been written, while its drain is still paused.
        # A client can send this empty original ACK before server drain ends.
        await peer.connection.receive(peer.output.transform(frame(AFTER_ENTER_WORLD, b'')))
        assert owner.joined, 'Early world ACK did not reach actual role initialization'
        assert not owner.newbie_pending and not owner.transfer and not owner.battle and not owner.require_move_start
        before = owner.position
        stop = b'\0'+struct.pack('>hhQ', *clear, 1006)
        events.rows.clear()
        await peer.connection.receive(peer.output.transform(frame(0xc0faa, stop)))
        result.update(joined_before_drain=owner.joined, old_joined_guard_excluded=True,
            before_position=before.value, before_version=before.version,
            pre_drain_resulting_position=owner.position.value, pre_drain_resulting_version=owner.position.version,
            pre_drain_durable_position=store.position(1111, role['id']),
            drain_still_paused=not writer.release.is_set())
        assert owner.joined and owner.position == before and not writer.release.is_set()
        assert store.position(1111, role['id']) == before.value
        assert store.position_version(role['id']) == before.version
        assert events.rows and all(row.get('reason') == 'ValueError' for row in events.rows)
        # Production logs intentionally retain only the error class. Cross the
        # actual public map mailbox as a second observation of the exact gate,
        # without installing a context or modifying any production dependency.
        reason = await map_rejection(runtime, owner, before, 0xc0faa, stop)
        assert reason == 'Movement waits for exact normal-state delivery', reason
        result.update(pre_drain_map_rejection=reason, pre_drain_checkpoint_unchanged=True)
        writer.release.set()
        await login
        assert peer.early_initial, 'Actual early initialization frames were not decoded'
        events.rows.clear()
        await peer.request(0xc0fa1, struct.pack('>hhhhQ', *start, *clear, 1006))
        await peer.request(0xc0faa, stop)
        assert owner.position.value == (1006, *clear) and not events.rows
        before = owner.position
        for kind, body in ((0xc0fa3, struct.pack('>hh', *wall)+b'\0'+struct.pack('>Q', 1006)),
                           (0xc0faa, b'\0'+struct.pack('>hhQ', *wall, 1006))):
            events.rows.clear()
            await peer.request(kind, body)
            assert owner.position == before
            assert store.position(1111, role['id']) == before.value
            assert store.position_version(role['id']) == before.version
            assert events.rows and all(row.get('reason') == 'ValueError' for row in events.rows)
            assert await map_rejection(runtime, owner, before, kind, body) == 'Movement enters blocked maze cell'
        assert owner.battle is None and not runtime.battles
        await peer.connection.close()
        resumed = MapPeer(runtime)
        await resumed.login(role)
        current = runtime.roles[role['id']]
        assert current.epoch != owner.epoch and current.position.value == before.value
        assert current.position.version == before.version
        assert await resumed.request(100, b'gate') == [(100, b'gate')]
        result.update(clear_after_exact_drain=True, blocked_CHECK_and_STOP_rejected=True,
            rejected_position_version_and_storage_unchanged=True,
            reconnect_preserved=True, continuous_encrypted_heartbeat=True)
        return result
    finally:
        writer.release.set()
        await asyncio.gather(login, return_exceptions=True)
        await runtime.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runtime-source', type=Path)
    parser.add_argument('--runtime-harness', type=Path)
    parser.add_argument('--report', type=Path,
        default=Path(__file__).parent/'evidence/world-movement-delivery-boundaries-verification.json')
    args = parser.parse_args()
    before = sources()
    production_imports(args.runtime_source)
    result = dict(all_passed=False)
    try:
        with tempfile.TemporaryDirectory(prefix='world-movement-delivery-') as directory:
            store = AccountStore(Path(directory)/'state.sqlite3')
            role = store.create_role(1111, '提前确认移动门槛', 11, 1010109)
            asyncio.run(asyncio.wait_for(check(store, runtime_storage.prepare(store), role, result), 45))
        result['all_passed'] = True
    except Exception as error:
        result['error'] = repr(error)
        raise
    finally:
        result.update(source=before, inputs_stable=before == sources(),
            production_imports=production_imports(args.runtime_source))
        write_json(args.report, result)
    assert result['inputs_stable']
    print(dict(all_passed=True, old_joined_guard_excluded=result['old_joined_guard_excluded'],
        wall_rejected=result['blocked_CHECK_and_STOP_rejected'], inputs_stable=True))


if __name__ == '__main__':
    main()
