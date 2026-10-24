"""All resource-backed maps through actual encrypted runtime and native codecs.

Each map starts at an explicit offline legacy checkpoint. This verifies runtime
entry, complete configured NPC delivery, a same-cell step and reconnect; it is
not natural accessibility, scene rendering, quest visibility, or combat proof.
"""
import argparse
import asyncio
from contextlib import closing
import datetime
import hashlib
import importlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import uuid


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--maps', help='Diagnostic subset only; default is every available map')
    parser.add_argument('--fault-drop-npc-batch', action='store_true')
    parser.add_argument('--worker-source', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--client-root', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--runtime-source', type=Path, help='Exact existing immutable candidate source')
    parser.add_argument('--runtime-harness', type=Path, help='Candidate test helpers, without production modules')
    parser.add_argument('--report', type=Path)
    return parser.parse_args()


ARGS = arguments() if __name__ == '__main__' else None
if ARGS and (ARGS.worker_source or ARGS.runtime_source):
    import inspect_client
    selected_source = (ARGS.worker_source or ARGS.runtime_source).resolve(strict=True)
    if ARGS.client_root is not None:
        inspect_client.ROOT = ARGS.client_root
    inspect_client.OUT = selected_source
    sys.path.insert(0, str(selected_source))
    if ARGS.runtime_harness is not None:
        harness = ARGS.runtime_harness.resolve(strict=True)
        for path in harness.iterdir():
            importable = (path.is_file() and path.suffix in ('.py', '.pyc', '.pyd')
                          or path.is_dir() and any(path.glob('__init__.*')))
            if importable and not path.name.startswith(('verify_', 'research_', 'diagnose_')):
                raise ValueError('Only explicit test helpers allowed in harness: '+path.name)
        sys.path.insert(0, str(harness))
    # inspect_client was cached for its original asset root before selecting
    # candidate modules. Rebind its two parser imports before runtime loading,
    # so transitive production imports use one candidate class graph as well.
    for module in ('pfs', 'bxml'):
        sys.modules.pop(module, None)
    inspect_client.PfsArchive = importlib.import_module('pfs').PfsArchive
    inspect_client.decode = importlib.import_module('bxml').decode

from accounts import AccountStore
from game_runtime import GameRuntime
from inspect_client import OUT, ROOT, write_json
import runtime_storage
from runtime_core import StaleEpoch
from verify_runtime import Peer
from verify_world_entities_native import probe
from wire import read_compact, read_octets
from world_catalog import maps, maze_grids, valid_position
from world_collision import maze_clear, maze_segment_clear
from world_entity_protocol import ADD_USER_SCREEN
from world_owner import MapAddress
from world_protocol import ENTER_SCENE
from world_transfer_storage import load_map_instance_transaction


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def npc_records(body):
    roles, offset = read_compact(body)
    assert roles == 0, 'This audit expects NPC-only screen packets'
    count, offset = read_compact(body, offset)
    result = []
    for _ in range(count):
        key, config = struct.unpack_from('>qi', body, offset)
        name, offset = read_octets(body, offset+12)
        x, y = struct.unpack_from('>hh', body, offset)
        offset += struct.calcsize('>hhBhh4i')
        properties, offset = read_compact(body, offset)
        offset += properties*8
        result.append((key, config, name.decode('utf-16-le'), x, y))
    assert offset == len(body)
    return result


def native_npcs(body):
    actual = []

    def observe(machine, target):
        def u32(address):
            return struct.unpack('<I', machine.mem_read(address, 4))[0]
        head, count = u32(target+0x18), u32(target+0x1c)
        node = u32(head)
        while node != head:
            assert len(actual) < count
            bean = node+8
            key, config = struct.unpack('<qi', machine.mem_read(bean+8, 12))
            length, capacity = u32(bean+0x28), u32(bean+0x2c)
            text = bean+0x18 if capacity < 8 else u32(bean+0x18)
            name = bytes(machine.mem_read(text, length*2)).decode('utf-16-le')
            x, y = struct.unpack('<hh', machine.mem_read(bean+0x34, 4))
            actual.append((key, config, name, x, y))
            node = u32(node)
        assert len(actual) == count

    probe(0xfc5f40, 0xfc68f0, 0xfc69a0, payload=body, observer=observe)
    assert actual == npc_records(body), 'Original decoded NPCs differ from received records'
    return actual


def scene_position(body):
    _, offset = read_octets(body)
    x, y, state, reason, map_id, weather = struct.unpack_from('>hhBiQB', body, offset)
    _, end = read_octets(body, offset+18)
    assert end == len(body)
    _, native = probe(0xdac580, 0xe50b00, 0xf74260, payload=body)
    assert struct.unpack_from('<hh', native, 0x28) == (x, y)
    assert struct.unpack_from('<Q', native, 0x38)[0] == map_id
    assert native[0x2c] == state and native[0x40] == weather
    return map_id, x, y


def points(map_id, catalog, grid):
    for cy in range(min(grid.height, (min(catalog[map_id]['height'], 32768)+15)//16)):
        for cx in range(min(grid.width, (min(catalog[map_id]['width'], 32768)+15)//16)):
            if (cx, cy) in catalog[map_id]['portals']:
                continue
            start, step = (cx*16+8, cy*16+8), (cx*16+9, cy*16+8)
            if (valid_position((map_id, *step), catalog)
                    and maze_clear(grid, *start, mask=1)
                    and maze_clear(grid, *step, mask=1)
                    and maze_segment_clear(grid, start, step, mask=1)):
                return start, step
    raise AssertionError(('No nonportal same-cell clear witness', map_id))


class MapPeer(Peer):
    def __init__(self, runtime):
        super().__init__(runtime)
        self.scenes = []

    async def request(self, kind, body):
        replies = await super().request(kind, body)
        self.scenes.extend(payload for message, payload in replies if message == ENTER_SCENE)
        return replies


class Events:
    def __init__(self):
        self.rows = []

    def emit(self, **row):
        if row.get('event') == 'gameplay_rejected':
            self.rows.append(row)


def checkpoint_fixture(store, role, position):
    epoch = store.acquire_lease(1111, role['id'])
    try:
        with closing(store.leased(1111, role['id'], epoch).connect()) as db, db:
            db.execute('BEGIN')
            assert load_map_instance_transaction(db, 1111, role['id'], epoch) is None, \
                'Fixture may not overwrite a durably adopted instance'
        assert store.save_checkpoint(1111, role['id'], epoch, position,
                                     store.position_version(role['id'])+1)
    finally:
        store.release_lease(role['id'], epoch)


async def check(store, prepared, role, selected, result, *, fault_drop=False):
    events = Events()
    runtime = GameRuntime(store, prepared, logger=events)
    catalog, grids = prepared[3], maze_grids()
    raw_catalog = json.loads((OUT/'catalogs/world.json').read_text(encoding='utf8'))
    placement_rows = {int(row['attributes']['id']): row['npc_placements'] for row in raw_catalog}
    definitions = {int(row['attributes']['id']): row['attributes'] for row in
        json.loads((OUT/'catalogs/knight.gsp.npc.cnpcconfig.json').read_text(encoding='utf8'))}
    decoded = {}
    fault_applied = False
    try:
        for index, map_id in enumerate(selected):
            start, step = points(map_id, catalog, grids[map_id])
            checkpoint_fixture(store, role, (map_id, *start))
            target = runtime.map(map_id)
            if fault_drop and not fault_applied and target.spawn_packets:
                original = target.spawn_packets
                target.spawn_packets = original[1:]
                result['fault'] = dict(map_id=map_id, original_batches=len(original),
                    sent_batches=len(target.spawn_packets), original_first_sha256=
                    hashlib.sha256(original[0][1]).hexdigest())
                fault_applied = True
            peer = MapPeer(runtime)
            await peer.login(role)
            owner = runtime.roles[role['id']]
            assert owner.map_address == MapAddress(map_id, map_id, 0)
            assert owner.position.value == (map_id, *start) and not owner.newbie_pending
            assert [scene_position(body) for body in peer.scenes] == [(map_id, *start)]
            packets = [body for kind, body in peer.initial if kind == ADD_USER_SCREEN]
            expected = [((map_id<<32)|(ordinal+1), int(row['id']),
                definitions[int(row['id'])].get('name', ''), int(row['posx']), int(row['posy']))
                for ordinal, row in enumerate(placement_rows[map_id])]
            actual = []
            for body in packets:
                key = hashlib.sha256(body).hexdigest()
                if key not in decoded:
                    decoded[key] = native_npcs(body)
                actual.extend(decoded[key])
            assert actual == expected, ('Runtime omitted/reordered configured NPC placements',
                                       map_id, len(expected), len(actual))
            await peer.request(0xc0fa1, struct.pack('>hhhhQ', *start, *step, map_id))
            assert owner.position.value == (map_id, *start)
            await peer.request(0xc0faa, b'\0'+struct.pack('>hhQ', *step, map_id))
            assert owner.position.value == (map_id, *step)
            assert owner.battle is None and not runtime.battles and not events.rows
            version = owner.position.version
            await peer.connection.close()
            try:
                await target.mailbox.call('location', role['id'], owner.epoch)
            except StaleEpoch:
                pass
            else:
                raise AssertionError('Disconnected membership remained readable under the old lease')
            peer = MapPeer(runtime)
            await peer.login(role)
            resumed = runtime.roles[role['id']]
            assert resumed.position.value == (map_id, *step) and resumed.position.version == version
            assert resumed.map_address == MapAddress(map_id, map_id, 0)
            assert [scene_position(body) for body in peer.scenes] == [(map_id, *step)]
            assert [body for kind, body in peer.initial if kind == ADD_USER_SCREEN] == packets
            assert await peer.request(100, b'maps') == [(100, b'maps')]
            await peer.connection.close()
            result['maps'].append(dict(map_id=map_id, start=start, step=step,
                configured_npcs=len(expected), native_decoded_npcs=len(actual),
                npc_batches=len(packets), npc_records_sha256=hashlib.sha256(
                    json.dumps(actual, ensure_ascii=False).encode('utf8')).hexdigest(),
                stop_version=version, encrypted_reconnect_preserved=True))
            if (index+1) % 25 == 0:
                print(json.dumps(dict(verified_maps=index+1, total=len(selected))), flush=True)
        assert not fault_drop or fault_applied
        result.update(all_passed=True, native_npc_batches=len(decoded))
    finally:
        await runtime.close()


def worker(args):
    candidate_manifest = None
    if args.runtime_source is not None:
        candidate_manifest = args.runtime_source.resolve().parent/'manifest.json'
        manifest = json.loads(candidate_manifest.read_text(encoding='utf8'))['sha256']
        assert all(digest(args.runtime_source/name) == expected for name, expected in manifest.items()), \
            'Exact candidate production manifest mismatch before verification'

    def production_imports():
        if args.runtime_source is None:
            return {}
        source = args.runtime_source.resolve()
        imported = {}
        for path in source.glob('*.py'):
            # inspect_client is deliberately cached before bootstrap to retain
            # the caller's original asset root. All other production imports
            # must come from the selected candidate, including transitive ones.
            if path.stem == 'inspect_client' or path.stem.startswith(('verify_', 'research_', 'diagnose_')):
                continue
            module = sys.modules.get(path.stem)
            if module is not None:
                actual = Path(module.__file__).resolve()
                assert actual == path.resolve(), 'Production import outside candidate: '+path.stem
                imported[path.stem] = dict(path=str(actual), sha256=digest(actual))
        return imported

    production_imports()
    catalog = maps()
    available = sorted(mid for mid, row in catalog.items() if row['available'])
    selected = sorted(set(map(int, args.maps.split(',')))) if args.maps else available
    assert set(selected) <= set(available)
    names = ('game_runtime', 'runtime_storage', 'runtime_story_maps', 'accounts', 'world_owner',
        'world_catalog', 'world_npcs', 'world_entity_protocol', 'world_movement', 'wild_encounters',
        'verify_runtime', 'verify_world_entities_native', 'native_gameplay_probe',
        'verify_world_resource_runtime')

    def sources():
        paths = {name: Path(__file__).resolve() if name == 'verify_world_resource_runtime'
                 else Path(importlib.import_module(name).__file__).resolve() for name in names}
        return {name: dict(path=str(path), sha256=digest(path)) for name, path in paths.items()}

    result = dict(all_passed=False, maps=[], source=sources(), configured_maps=len(catalog),
        available_maps=len(available), selected_maps=selected,
        unavailable_maps=sorted(set(catalog)-set(available)),
        complete_available_map_scope=selected == available, initial_checkpoint_fixture=True,
        movement_scope='one clear nonportal same-cell pixel; actual MOVE/STOP and wild_move unchanged',
        original_npc_visibility_and_direction_verified=False, native_gui_verified=False,
        live_server_changed=False, battle_executed=False)
    if candidate_manifest is not None:
        result.update(candidate_manifest=str(candidate_manifest), candidate_production_files=len(manifest),
            candidate_manifest_sha256=digest(candidate_manifest), execution_scope='exact existing candidate, no source copy or mutation')
        for module in ('game_runtime', 'runtime_storage', 'world_owner', 'world_movement'):
            assert Path(result['source'][module]['path']).parent == args.runtime_source.resolve(), module
    assets = (ROOT/'artres/map.pfs', ROOT/'artres/config.pfs')
    result['asset_sha256'] = {str(path.relative_to(ROOT)): digest(path) for path in assets}
    try:
        with tempfile.TemporaryDirectory(prefix='world-all-resource-runtime-') as directory:
            store = AccountStore(Path(directory)/'state.sqlite3')
            role = store.create_role(1111, '全图离线核查', 11, 1010109)
            prepared = runtime_storage.prepare(store)
            asyncio.run(asyncio.wait_for(check(store, prepared, role, selected, result,
                fault_drop=args.fault_drop_npc_batch), 900))
        assert result['source'] == sources(), 'Execution source changed during verification'
        assert result['asset_sha256'] == {str(path.relative_to(ROOT)): digest(path) for path in assets}
        if candidate_manifest is not None:
            assert digest(candidate_manifest) == result['candidate_manifest_sha256']
            assert all(digest(args.runtime_source/name) == expected for name, expected in manifest.items())
            result['candidate_production_stable'] = True
            result['production_imports'] = production_imports()
        result['inputs_stable'] = True
    except Exception as error:
        result.update(all_passed=False, error=repr(error))
        raise
    finally:
        write_json(args.report, result)
    print(json.dumps(dict(all_passed=True, maps=len(result['maps']),
        npc_placements=sum(row['configured_npcs'] for row in result['maps']),
        native_npc_batches=result['native_npc_batches'])), flush=True)


def main():
    if ARGS.runtime_harness is not None and ARGS.runtime_source is None:
        raise ValueError('Runtime harness requires explicit candidate source')
    if ARGS.worker_source or ARGS.runtime_source:
        if ARGS.report is None:
            raise ValueError('Explicit report path required for an external worker/candidate')
        worker(ARGS)
        return
    label = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:6]
    source = OUT/f'evidence/snapshots/world-resource-runtime-{label}/source'
    source.mkdir(parents=True)
    files = list(OUT.glob('*.py'))
    for folder in ('catalogs', 'design', 'evidence'):
        files.extend((OUT/folder).glob('*.json'))
    files.append(OUT/'evidence/native-image.bin')
    snapshot = {}
    for path in files:
        name = str(path.relative_to(OUT))
        raw = path.read_bytes()
        destination = source/name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)
        snapshot[name] = hashlib.sha256(raw).hexdigest()
    write_json(source.parent/'manifest.json', dict(source_sha256=snapshot))
    report = ARGS.report or OUT/('evidence/world-resource-runtime-fault.json'
        if ARGS.fault_drop_npc_batch else 'evidence/world-resource-runtime-verification.json')
    command = [sys.executable, '-B', str(source/Path(__file__).name),
        '--worker-source', str(source), '--client-root', str(ROOT), '--report', str(report.resolve())]
    if ARGS.maps:
        command += ['--maps', ARGS.maps]
    if ARGS.fault_drop_npc_batch:
        command.append('--fault-drop-npc-batch')
    run = subprocess.run(command, timeout=1000)
    if report.exists():
        result = json.loads(report.read_text(encoding='utf8'))
        stable = all(digest(source/name) == expected for name, expected in snapshot.items())
        result.update(snapshot_manifest=str(source.parent/'manifest.json'),
            snapshot_files_stable=stable, parent_returncode=run.returncode)
        write_json(report, result)
        assert stable
    assert run.returncode == 0, f'Frozen runtime worker failed; see {report}'


if __name__ == '__main__':
    main()
