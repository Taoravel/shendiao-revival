"""Replay original producer bodies after two real blocked-target handoffs.

Temporary accounts only. Does not select a replacement landing or relax maze.
"""
import argparse
import asyncio
import importlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import traceback

import inspect_client


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runtime-source', type=Path, required=True)
    parser.add_argument('--runtime-harness', type=Path, required=True)
    parser.add_argument('--native-report', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    return parser.parse_args()


ARGS = arguments() if __name__ == '__main__' else None
if ARGS:
    SOURCE = ARGS.runtime_source.resolve(strict=True)
    inspect_client.OUT = SOURCE
    sys.path.insert(0, str(SOURCE))
    harness = ARGS.runtime_harness.resolve(strict=True)
    for path in harness.iterdir():
        importable = (path.is_file() and path.suffix in ('.py', '.pyc', '.pyd')
                      or path.is_dir() and any(path.glob('__init__.*')))
        if importable and not path.name.startswith(('verify_', 'research_', 'diagnose_')):
            raise ValueError('Only explicit test helpers allowed in harness: '+path.name)
    sys.path.insert(0, str(harness))
    for name in ('pfs', 'bxml'):
        sys.modules.pop(name, None)
    inspect_client.PfsArchive = importlib.import_module('pfs').PfsArchive
    inspect_client.decode = importlib.import_module('bxml').decode

from accounts import AccountStore
from game_runtime import GameRuntime
import runtime_storage
from inspect_client import ROOT
from verify_world_portal_runtime import digest, sources, production_imports
from verify_world_resource_runtime import MapPeer, Events, checkpoint_fixture, scene_position
from verify_world_resource_handoffs import approach
from world_catalog import maps, maze_grids, valid_position
from world_collision import maze_clear
from world_protocol import ENTER_SCENE


def verify_observations(row):
    packets = row['packets']
    assert [packet['kind'] for packet in packets] == [0xc0fa1, 0xc0fa3, 0xc0faa]
    first, check, stop = packets
    assert len(first['rejections']) == 1 and first['rejections'][0]['type'] == 0xc0fa1
    assert first['before_position'] == first['after_position'] == first['saved_position']
    assert first['before_version'] == first['after_version']
    assert not check['rejections'] and not stop['rejections']
    assert check['after_position'] != first['after_position']
    assert check['after_version'] == first['after_version']+1
    assert stop['after_version'] == check['after_version']+1
    assert row['native_final_reached'] and row['final_position'] == row['final_saved_position']


async def check_case(native, row, catalog, grids):
    mid, target_mid = native['source_map'], native['target_map']
    landing = (target_mid, *native['unchanged_landing'])
    assert not maze_clear(grids[target_mid], *landing[1:], mask=1)
    assert valid_position(landing, catalog)
    leg = None
    for cell, target in sorted(catalog[mid]['portals'].items()):
        if tuple(target) == landing and maze_clear(grids[mid], cell[0]*16, cell[1]*16, mask=1):
            leg = approach(mid, cell, catalog, grids[mid])
            if leg is not None:
                break
    assert leg is not None, 'No original clear source approach'
    start, portal = map(tuple, leg)
    row.update(source_approach=start, source_portal=portal, phase='source_login')
    with tempfile.TemporaryDirectory(prefix='world-blocked-exit-runtime-') as directory:
        store = AccountStore(Path(directory)/'state.sqlite3')
        role = store.create_role(1111, '原报文复核', 11, 1010109)
        prepared = runtime_storage.prepare(store)
        checkpoint_fixture(store, role, (mid, *start))
        events = Events()
        runtime = GameRuntime(store, prepared, logger=events)
        try:
            peer = MapPeer(runtime)
            await peer.login(role)
            owner = runtime.roles[role['id']]
            assert not owner.newbie_pending and owner.position.value == (mid, *start)
            events.rows.clear()
            await peer.request(0xc0fa1, struct.pack('>hhhhQ', *start, *portal, mid))
            replies = await peer.request(0xc0faa, b'\0'+struct.pack('>hhQ', *portal, mid))
            row['phase'] = 'blocked_target_handoff'
            assert not events.rows, events.rows
            assert owner.position.value == landing and owner.transfer is None
            assert [scene_position(body) for kind, body in replies if kind == ENTER_SCENE] == [landing]
            assert store.position(1111, role['id']) == landing
            row['target_before_replay'] = dict(position=owner.position.value, version=owner.position.version)
            row['packets'] = []
            for packet in native['messages']:
                row['phase'] = 'replay_original_native_body'
                events.rows.clear()
                before = owner.position.value, owner.position.version
                replies = await peer.request(packet['kind'], bytes.fromhex(packet['body_hex']))
                row['packets'].append(dict(kind=packet['kind'], body_hex=packet['body_hex'],
                    before_position=before[0], before_version=before[1],
                    after_position=owner.position.value, after_version=owner.position.version,
                    rejections=list(events.rows), reply_kinds=[kind for kind, _ in replies],
                    saved_position=store.position(1111, role['id'])))
            row['final_position'] = owner.position.value
            row['final_saved_position'] = store.position(1111, role['id'])
            row['native_final_position'] = (target_mid, *native['messages'][-1]['current'])
            row['native_final_reached'] = owner.position.value == row['native_final_position']
            row['heartbeat_ok'] = await peer.request(100, b'exit') == [(100, b'exit')]
            assert row['heartbeat_ok'] and owner.battle is None and not runtime.battles
            assert row['final_position'] == row['final_saved_position']
            verify_observations(row)
            await peer.connection.close()
        finally:
            await runtime.close()
    row.update(status='observed', phase='complete')


def main():
    source = ARGS.runtime_source.resolve()
    manifest_path = source.parent/'manifest.json'
    manifest_hash = digest(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding='utf8'))['sha256']
    assert all(digest(source/name) == value for name, value in manifest.items())
    native_hash = digest(ARGS.native_report)
    native = json.loads(ARGS.native_report.read_text(encoding='utf8'))
    assert native['all_expected_observations_passed']
    assert native['image_sha256'] == '2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791'
    assert all(digest(Path(__file__).parent/name) == value
               for name, value in native['dependency_sha256'].items())
    selected = [case for case in native['cases'] if case['messages']]
    assert [case['source_map'] for case in selected] == [1301, 1305]
    before = sources()
    script_hash = digest(__file__)
    assets = {str(path): digest(path) for path in (ROOT/'artres/map.pfs', ROOT/'artres/config.pfs')}
    catalog, grids = maps(), maze_grids()
    report = dict(source=before, manifest=str(manifest_path), manifest_sha256=manifest_hash,
        production_files=len(manifest), native_report=str(ARGS.native_report.resolve()),
        native_report_sha256=native_hash, script_sha256=script_hash, asset_sha256=assets,
        native_bodies_unchanged=True, source_checkpoint_fixture=True,
        full_app_or_gui=False, server_policy_changed=False, live_server_changed=False,
        cases=[])

    async def run():
        for native_case in selected:
            row = dict(source_map=native_case['source_map'], target_map=native_case['target_map'], status='failed')
            report['cases'].append(row)
            try:
                await asyncio.wait_for(check_case(native_case, row, catalog, grids), 45)
            except Exception as error:
                row.update(error=repr(error), traceback=traceback.format_exc())

    try:
        asyncio.run(run())
    finally:
        report['inputs_stable'] = (before == sources() and script_hash == digest(__file__)
            and native_hash == digest(ARGS.native_report)
            and assets == {path: digest(path) for path in assets})
        report['production_stable'] = (manifest_hash == digest(manifest_path)
            and all(digest(source/name) == value for name, value in manifest.items()))
        report['production_imports'] = production_imports(source)
        report['all_cases_observed'] = len(report['cases']) == 2 and all(row['status']=='observed' for row in report['cases'])
        ARGS.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
    assert report['inputs_stable'] and report['production_stable'] and report['all_cases_observed']
    print(json.dumps(dict(observed=len(report['cases']),
        reached=sum(row['native_final_reached'] for row in report['cases']))), flush=True)


if __name__ == '__main__':
    main()
