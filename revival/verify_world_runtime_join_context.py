"""A rejected/idempotent runtime join must preserve current movement authority.

Actual MapOwner/SerialOwner commands and original maze/scene encoding. The
movement completion is an explicit controlled server callback fixture; this
does not execute ConnectionOwner, Writer.drain, a client ACK, DB or GUI.
"""
import argparse
import asyncio
from dataclasses import asdict, replace
import hashlib
import importlib
import json
from pathlib import Path
import struct
import sys

import inspect_client

if __name__ == '__main__':
    bootstrap = argparse.ArgumentParser(add_help=False)
    bootstrap.add_argument('--runtime-source', type=Path, required=True)
    selected, _ = bootstrap.parse_known_args()
    source = selected.runtime_source.resolve(strict=True)
    inspect_client.OUT = source
    sys.path.insert(0, str(source))
    for name in ('pfs', 'bxml'):
        sys.modules.pop(name, None)
    inspect_client.PfsArchive = importlib.import_module('pfs').PfsArchive
    inspect_client.decode = importlib.import_module('bxml').decode

from game_runtime import MapOwner, Position
from inspect_client import ROOT
from pfs import PfsArchive
from world_catalog import maps
from world_grids import maze_grid
from world_protocol import ENTER_SCENE, scene_entry


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def sources():
    names = ('game_runtime', 'runtime_core', 'runtime_movement', 'runtime_storage',
             'world_owner', 'world_movement', 'world_catalog', 'world_grids', 'world_protocol', 'pfs')
    result = {}
    for name in names:
        path = Path(importlib.import_module(name).__file__).resolve()
        result[name] = dict(path=str(path), sha256=digest(path))
    result['probe'] = dict(path=str(Path(__file__).resolve()), sha256=digest(__file__))
    return result


async def observe(kind, catalog, grid):
    owner = MapOwner(1006, catalog, maze=grid)
    try:
        position = Position(1, 'current-lease', (1006, 360, 2264), 1, (22, 141))
        await owner.mailbox.call('join', position)
        location = await owner.mailbox.call('location', 1, position.epoch)
        declaration = await owner.mailbox.call('declare_movement', 1, position.epoch,
            location, 1, 'controlled-scene-'+kind, ENTER_SCENE, scene_entry(location.position), 'normal_scene')
        await owner.mailbox.call('movement_will_send', 1, position.epoch, declaration)
        # Controlled exact completion Interface only, not an observed network
        # write/drain or a synthetic client readiness packet.
        await owner.mailbox.call('movement_sent', 1, position.epoch, declaration, False)
        stop = lambda x: b'\0'+struct.pack('>hhQ', x, 2264, 1006)
        before_cache, _ = await owner.mailbox.call('move_for_encounter', 1, position.epoch, 1, 0xc0faa, stop(361))
        before = await owner.mailbox.call('location', 1, position.epoch)
        assert before.position == (1006, 361, 2264) and before.version == 2
        row = dict(case=kind, initial_declared_move_passed=True,
                   before_location=asdict(before), before_cache=asdict(before_cache))
        attempted = None
        if kind == 'exact_retry':
            attempted = before_cache
        elif kind == 'stale_epoch':
            attempted = replace(before_cache, epoch='old-lease')
        elif kind == 'conflicting_position':
            attempted = replace(before_cache, value=(1006, 363, 2264))
        elif kind == 'other_role_join':
            attempted = replace(before_cache, role_id=2, epoch='other-lease')
        if attempted is not None:
            try:
                reply = await owner.mailbox.call('join', attempted)
            except ValueError as error:
                row['join_rejection'] = str(error)
                assert kind in ('stale_epoch', 'conflicting_position')
            else:
                row['join_accepted'] = True
                assert kind in ('exact_retry', 'other_role_join') and reply == attempted
        after = await owner.mailbox.call('location', 1, position.epoch)
        row['location_preserved_by_join'] = after == before
        row['cache_preserved_by_join'] = owner.positions.get(1) == before_cache
        assert row['location_preserved_by_join'] and row['cache_preserved_by_join']
        try:
            moved, _ = await owner.mailbox.call('move_for_encounter', 1, position.epoch,
                                               before.version, 0xc0faa, stop(362))
        except ValueError as error:
            row['later_move_passed'] = False
            row['later_move_rejection'] = str(error)
            assert await owner.mailbox.call('location', 1, position.epoch) == before
            assert owner.positions.get(1) == before_cache
            fresh = await owner.mailbox.call('declare_movement', 1, position.epoch,
                before, 1, 'controlled-recovery-'+kind, ENTER_SCENE, scene_entry(before.position), 'normal_scene')
            await owner.mailbox.call('movement_will_send', 1, position.epoch, fresh)
            await owner.mailbox.call('movement_sent', 1, position.epoch, fresh, False)
            recovered, _ = await owner.mailbox.call('move_for_encounter', 1, position.epoch,
                                                   before.version, 0xc0faa, stop(362))
            row['fresh_declaration_recovery_passed'] = (
                recovered.value == (1006, 362, 2264) and recovered.version == 3)
            assert row['fresh_declaration_recovery_passed']
        else:
            row['later_move_passed'] = moved.value == (1006, 362, 2264) and moved.version == 3
        return row
    finally:
        await owner.mailbox.close()


async def check(catalog, grid):
    return [await observe(kind, catalog, grid) for kind in
        ('control', 'other_role_join', 'exact_retry', 'stale_epoch', 'conflicting_position')]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runtime-source', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    source = args.runtime_source.resolve(strict=True)
    manifest_path = source.parent/'manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf8'))['sha256']
    manifest_hash = digest(manifest_path)
    assert all(digest(source/name) == value for name, value in manifest.items())
    before = sources()
    assert all(Path(before[name]['path']).parent == source for name in before if name != 'probe')
    catalog = maps()
    entry = catalog[1006]['resdir']+'/maze.dat'
    raw = PfsArchive(ROOT/'artres/map.pfs').read(entry)
    result = dict(all_passed=False, source=before, manifest=str(manifest_path),
        manifest_sha256=manifest_hash, production_files=len(manifest),
        original_maze_entry=entry, original_maze_sha256=hashlib.sha256(raw).hexdigest(),
        completion_fixture='actual declare/will_send/sent map Interfaces; no actual writer/drain/client ACK',
        database_used=False, shared_modified=False, live_server_changed=False,
        native_gui_verified=False, cases=[])
    try:
        result['cases'] = asyncio.run(asyncio.wait_for(check(catalog, maze_grid(raw)), 15))
        result['all_passed'] = all(case['later_move_passed'] for case in result['cases'])
    finally:
        result['inputs_stable'] = before == sources() and digest(manifest_path) == manifest_hash
        result['production_stable'] = all(digest(source/name) == value for name, value in manifest.items())
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf8')
    assert result['inputs_stable'] and result['production_stable']
    assert result['all_passed'], 'Runtime join revoked already admitted movement authority'
    print(json.dumps(dict(all_passed=True, cases=len(result['cases']), inputs_stable=True)))


if __name__ == '__main__':
    main()
