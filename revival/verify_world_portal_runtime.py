"""Ordinary original portals through exact encrypted runtime and cold reload.

Each case uses its own temporary DB and an explicit source checkpoint fixture.
No production protocol/position dependency is replaced; no real client/service.
"""
import argparse
import asyncio
from contextlib import closing
import hashlib
import importlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import time
import traceback

import inspect_client


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runtime-source', type=Path, required=True)
    parser.add_argument('--runtime-harness', type=Path)
    parser.add_argument('--pairs', help='Diagnostic subset, e.g. 1002:1004,1007:1014')
    parser.add_argument('--legacy-source', action='store_true',
        help='Keep legacy unknown-instance source; diagnostic gameplay only, no durable address claim')
    parser.add_argument('--report', type=Path, required=True)
    return parser.parse_args()


ARGS = arguments() if __name__ == '__main__' else None
if ARGS:
    source = ARGS.runtime_source.resolve(strict=True)
    inspect_client.OUT = source
    sys.path.insert(0, str(source))
    if ARGS.runtime_harness:
        harness = ARGS.runtime_harness.resolve(strict=True)
        for path in harness.iterdir():
            importable = (path.is_file() and path.suffix in ('.py', '.pyc', '.pyd')
                          or path.is_dir() and any(path.glob('__init__.*')))
            if importable and not path.name.startswith(('verify_', 'research_', 'diagnose_')):
                raise ValueError('Only explicit test helpers allowed in harness: '+path.name)
        sys.path.insert(0, str(harness))
    for module in ('pfs', 'bxml'):
        sys.modules.pop(module, None)
    inspect_client.PfsArchive = importlib.import_module('pfs').PfsArchive
    inspect_client.decode = importlib.import_module('bxml').decode

from accounts import AccountStore
from bxml import decode
from game_runtime import GameRuntime
from inspect_client import ROOT, OUT
from pfs import PfsArchive
import runtime_storage
from verify_world_resource_handoffs import approach, nearby
from verify_world_resource_runtime import MapPeer, Events, checkpoint_fixture, native_npcs, scene_position
from world_catalog import maps, maze_grids, valid_position
from world_collision import maze_clear
from world_entity_protocol import ADD_USER_SCREEN
from world_owner import MapAddress
from world_protocol import ENTER_SCENE
from world_transfer_storage import load_map_instance_transaction, bind_map_instance_transaction


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def sources():
    names = ('accounts', 'game_runtime', 'runtime_storage', 'runtime_core', 'runtime_movement',
        'world_owner', 'world_movement', 'world_catalog', 'world_transfer_storage',
        'world_protocol', 'world_npcs', 'world_entity_protocol', 'verify_runtime',
        'verify_world_resource_handoffs', 'verify_world_resource_runtime', 'pfs', 'bxml')
    paths = {name: Path(importlib.import_module(name).__file__).resolve() for name in names}
    paths['portal_verifier'] = Path(__file__).resolve()
    return {name: dict(path=str(path), sha256=digest(path)) for name, path in paths.items()}


def production_imports(source):
    result = {}
    for path in source.glob('*.py'):
        if path.stem == 'inspect_client' or path.stem.startswith(('verify_', 'research_', 'diagnose_')):
            continue
        module = sys.modules.get(path.stem)
        if module is not None:
            actual = Path(module.__file__).resolve()
            assert actual == path.resolve(), 'Production import outside candidate: '+path.stem
            result[path.stem] = dict(path=str(actual), sha256=digest(actual))
    return result


def witnesses(catalog, grids):
    configured, eligible = set(), {}
    portal_cells = 0
    for mid, row in catalog.items():
        for cell, target in row['portals'].items():
            portal_cells += 1
            pair = mid, target[0]
            configured.add(pair)
            if (pair in eligible or mid == target[0]
                    or not valid_position((mid, cell[0]*16, cell[1]*16), catalog)
                    or not valid_position(target, catalog)):
                continue
            if (not maze_clear(grids[mid], cell[0]*16, cell[1]*16, mask=1)
                    or not maze_clear(grids[target[0]], *target[1:], mask=1)):
                continue
            leg = approach(mid, cell, catalog, grids[mid])
            step = nearby(target[0], target[1:], catalog, grids[target[0]])
            if leg is not None and step is not None:
                eligible[pair] = dict(source_map=mid, source_cell=cell,
                    approach=leg[0], portal=leg[1], target=target, target_step=step)
    assert portal_cells == 6275 and len(configured) == 227 and len(eligible) == 212
    return configured, eligible


def expected_npcs(mid, catalog, archive, definitions):
    names = {name.casefold(): name for name in archive.entries}
    assert len(names) == len(archive.entries), 'Ambiguous original map resource names'
    entry = names.get((catalog[mid]['resdir']+'/npc.xml').casefold())
    # Original maps without npc.xml have no configured placements. Require
    # the actual decoded target packets to be empty, rather than skip them.
    if entry is None:
        return [], None, None
    raw = archive.read(entry)
    rows = [dict(row.attrib) for row in decode(raw)]
    return ([(mid<<32 | index+1, int(row['id']), definitions[int(row['id'])].get('name', ''),
             int(row['posx']), int(row['posy'])) for index, row in enumerate(rows)],
            entry, hashlib.sha256(raw).hexdigest())


async def run_case(witness, result, catalog, archive, definitions, decoded_npcs):
    started = time.monotonic()
    mid, target = witness['source_map'], tuple(witness['target'])
    start, portal, step = map(tuple, (witness['approach'], witness['portal'], witness['target_step']))
    result['phase'] = 'prepare_offline_source'
    with tempfile.TemporaryDirectory(prefix='world-original-portal-') as folder:
        store = AccountStore(Path(folder)/'state.sqlite3')
        role = store.create_role(1111, '原门户核验', 11, 1010109)
        prepared = runtime_storage.prepare(store)
        checkpoint_fixture(store, role, (mid, *start))
        events = Events()
        runtime = GameRuntime(store, prepared, logger=events)
        try:
            peer = MapPeer(runtime)
            await peer.login(role)
            owner = runtime.roles[role['id']]
            result['phase'] = 'source_login'
            assert not owner.newbie_pending and not owner.transfer
            assert owner.position.value == (mid, *start)
            assert owner.map_address == MapAddress(mid, mid, 0)
            assert [scene_position(body) for body in peer.scenes] == [(mid, *start)]
            if not ARGS.legacy_source:
                # Explicit offline adoption from the ACTUAL joined owner,
                # never infer an instance solely from the resource template.
                current = await runtime.map(owner.map_address).mailbox.call('location', owner.id, owner.epoch)
                with closing(store.leased(1111, role['id'], owner.epoch).connect()) as db, db:
                    db.execute('BEGIN')
                    adopted = bind_map_instance_transaction(db, 1111, role['id'], owner.epoch, current)
                assert adopted.address == owner.map_address
            events.rows.clear()
            await peer.request(0xc0fa1, struct.pack('>hhhhQ', *start, *portal, mid))
            assert owner.position.value == (mid, *start)
            result['phase'] = 'portal_stop_and_exact_scene_drain'
            replies = await peer.request(0xc0faa, b'\0'+struct.pack('>hhQ', *portal, mid))
            assert not events.rows, events.rows
            assert owner.position.value == target and owner.transfer is None
            assert owner.map_address == MapAddress(target[0], target[0], 0)
            assert [scene_position(body) for kind, body in replies if kind == ENTER_SCENE] == [target]
            records = []
            for kind, body in replies:
                if kind != ADD_USER_SCREEN:
                    continue
                body_hash = hashlib.sha256(body).hexdigest()
                if body_hash not in decoded_npcs:
                    decoded_npcs[body_hash] = native_npcs(body)
                records.extend(decoded_npcs[body_hash])
            expected, npc_entry, npc_entry_hash = expected_npcs(target[0], catalog, archive, definitions)
            result['target_npc_resource_entry'] = npc_entry
            result['target_npc_resource_sha256'] = npc_entry_hash
            assert records == expected, 'Target scene omitted/reordered/or mixed original NPC placements'
            assert store.position(1111, role['id']) == target
            result['target_npcs'] = len(records)
            result['target_npcs_sha256'] = hashlib.sha256(json.dumps(records, ensure_ascii=False).encode('utf8')).hexdigest()
            result['phase'] = 'target_move_and_durable_full_address'
            await peer.request(0xc0fa1, struct.pack('>hhhhQ', *target[1:], *step, target[0]))
            await peer.request(0xc0faa, b'\0'+struct.pack('>hhQ', *step, target[0]))
            assert not events.rows and owner.position.value == (target[0], *step)
            assert store.position(1111, role['id']) == owner.position.value
            version = owner.position.version
            assert store.position_version(role['id']) == version
            with closing(store.leased(1111, role['id'], owner.epoch).connect()) as db, db:
                db.execute('BEGIN')
                checkpoint = load_map_instance_transaction(db, 1111, role['id'], owner.epoch)
            if ARGS.legacy_source:
                assert checkpoint is None, 'Legacy audit must not silently create instance provenance'
            else:
                assert checkpoint.address == owner.map_address and checkpoint.position == owner.position.value
                assert checkpoint.version == version
            expected_address, expected_position = owner.map_address, owner.position.value
            result['durable_instance_bound'] = checkpoint is not None
            assert owner.battle is None and not runtime.battles
            epoch = owner.epoch
            await peer.connection.close()
            result['phase'] = 'same_runtime_reconnect'
            resumed = MapPeer(runtime)
            await resumed.login(role)
            current = runtime.roles[role['id']]
            result['warm_observed'] = dict(previous_epoch=epoch, epoch=current.epoch,
                address=repr(current.map_address), expected_address=repr(expected_address),
                position=current.position.value, expected_position=expected_position,
                version=current.position.version, expected_version=version,
                scenes=[scene_position(body) for body in resumed.scenes])
            assert current.epoch != epoch, 'Reconnect must acquire a new login epoch'
            assert current.map_address == expected_address, result['warm_observed']
            assert current.position.value == expected_position and current.position.version == version, result['warm_observed']
            assert result['warm_observed']['scenes'] == [expected_position], result['warm_observed']
            # The original heartbeat protocol requires exactly four bytes.
            assert await resumed.request(100, b'port') == [(100, b'port')]
            await resumed.connection.close()
        finally:
            await runtime.close()
        result['phase'] = 'cold_runtime_reconnect'
        runtime = GameRuntime(store, prepared, logger=events)
        try:
            cold = MapPeer(runtime)
            await cold.login(role)
            current = runtime.roles[role['id']]
            assert current.map_address == expected_address
            assert current.position.value == expected_position and current.position.version == version
            assert [scene_position(body) for body in cold.scenes] == [expected_position]
            assert await cold.request(100, b'cold') == [(100, b'cold')]
            assert current.battle is None and not runtime.battles
            await cold.connection.close()
        finally:
            await runtime.close()
    result.update(status='passed', phase='complete', same_runtime_reconnect=True,
        cold_runtime_reconnect=True, saved_version=version, seconds=round(time.monotonic()-started, 3))


def main():
    source = ARGS.runtime_source.resolve()
    manifest_path = source.parent/'manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf8'))['sha256']
    manifest_hash = digest(manifest_path)
    assert all(digest(source/name) == value for name, value in manifest.items())
    before = sources()
    imports_before = production_imports(source)
    archives = (ROOT/'artres/map.pfs', ROOT/'artres/config.pfs')
    assets = {str(path): digest(path) for path in archives}
    catalog, grids = maps(), maze_grids()
    configured, eligible = witnesses(catalog, grids)
    selected = sorted(eligible)
    if ARGS.pairs:
        selected = sorted({tuple(map(int, pair.split(':'))) for pair in ARGS.pairs.split(',')})
        assert set(selected) <= set(eligible)
    result = dict(all_passed=False, source=before, manifest=str(manifest_path),
        manifest_sha256=manifest_hash, production_files=len(manifest), asset_sha256=assets,
        configured_pairs=len(configured), eligible_pairs=len(eligible), selected_pairs=selected,
        complete_ordinary_pair_scope=selected == sorted(eligible),
        unsupported_pairs=sorted(configured-set(eligible)), cases=[],
        source_checkpoint_fixture=True, client_scene_loading_ack_proven=False,
        explicit_source_instance_adoption_fixture=not ARGS.legacy_source,
        original_client_pathfinder_or_full_trajectory_verified=False,
        battle_executed=False, live_server_changed=False, native_gui_verified=False,
        fixture='fresh temporary account DB per pair; real encrypted MOVE/STOP/scene, original-NPC rows, same/cold runtime reconnect')
    archive = PfsArchive(ROOT/'artres/map.pfs')
    definitions = {int(row['attributes']['id']): row['attributes'] for row in
        json.loads((OUT/'catalogs/knight.gsp.npc.cnpcconfig.json').read_text(encoding='utf8'))}

    decoded_npcs = {}

    async def check():
        for index, pair in enumerate(selected):
            row = dict(eligible[pair], status='failed')
            result['cases'].append(row)
            try:
                await asyncio.wait_for(run_case(eligible[pair], row, catalog, archive, definitions, decoded_npcs), 45)
            except Exception as error:
                row['error'] = repr(error)
                row['traceback'] = traceback.format_exc()
            if (index+1) % 10 == 0:
                print(json.dumps(dict(checked=index+1, selected=len(selected),
                    passed=sum(item['status']=='passed' for item in result['cases']))), flush=True)

    try:
        asyncio.run(check())
        result['all_passed'] = all(row['status']=='passed' for row in result['cases'])
    finally:
        result['inputs_stable'] = before == sources() and assets == {str(path): digest(path) for path in archives}
        result['production_stable'] = digest(manifest_path) == manifest_hash and all(
            digest(source/name) == value for name, value in manifest.items())
        result['production_imports'] = production_imports(source)
        result['native_decoded_npc_batches'] = len(decoded_npcs)
        result['initial_production_imports'] = imports_before
        ARGS.report.parent.mkdir(parents=True, exist_ok=True)
        ARGS.report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf8')
    assert result['inputs_stable'] and result['production_stable']
    assert result['all_passed'], 'Ordinary runtime portal failures; inspect per-pair phase/error'
    print(json.dumps(dict(all_passed=True, ordinary_pairs=len(selected),
        full_scope=result['complete_ordinary_pair_scope'])), flush=True)


if __name__ == '__main__':
    main()
