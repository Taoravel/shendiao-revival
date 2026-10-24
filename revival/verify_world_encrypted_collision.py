"""Actual legacy role MOVE/STOP -> map authority -> durable blocked-node check.

Explicit temporary starting checkpoint, original maze and actual encrypted Peer.
Default requires collision rejection; --expect-gap verifies the exact old gap.
"""
import argparse
import asyncio
import hashlib
import importlib
from pathlib import Path
import struct
import sys
import tempfile

# Cache the original client root, then select one coherent runtime type graph.
import inspect_client
if __name__ == '__main__':
    bootstrap = argparse.ArgumentParser(add_help=False)
    bootstrap.add_argument('--runtime-source', type=Path)
    selected, _ = bootstrap.parse_known_args()
    if selected.runtime_source is not None:
        source = selected.runtime_source.resolve(strict=True)
        sys.path.insert(0, str(source))
        inspect_client.OUT = source

from accounts import AccountStore
from game_runtime import GameRuntime
from inspect_client import OUT, ROOT, write_json
import runtime_storage
from verify_world_resource_runtime import MapPeer, Events, checkpoint_fixture, scene_position
from world_catalog import maze_grids
from world_collision import maze_clear


def sources():
    names = ('game_runtime', 'runtime_storage', 'world_movement', 'world_owner',
        'world_catalog', 'world_collision', 'verify_world_resource_runtime',
        'verify_world_encrypted_collision')
    return {name: dict(path=str(Path(importlib.import_module(name).__file__).resolve()),
        sha256=hashlib.sha256(Path(importlib.import_module(name).__file__).read_bytes()).hexdigest())
        for name in names}


async def check(store, prepared, role):
    grid = maze_grids()[1006]
    initial, step, wall = (360, 2264), (361, 2264), (1664, 960)
    assert maze_clear(grid, *initial, mask=1) and maze_clear(grid, *step, mask=1)
    assert not maze_clear(grid, *wall, mask=1)
    checkpoint_fixture(store, role, (1006, *initial))
    events = Events()
    runtime = GameRuntime(store, prepared, logger=events)
    try:
        peer = MapPeer(runtime)
        await peer.login(role)
        owner = runtime.roles[role['id']]
        assert scene_position(peer.scenes[0]) == (1006, *initial)
        # The actual emitted ordinary entry sends state A0. Original consumer
        # and its successful-load exceptions are separately established in
        # WORLD_SCENE_MOVEMENT_STATE_RESEARCH, not simulated as GUI here.
        from wire import read_octets
        _, offset = read_octets(peer.scenes[0])
        entry_state = peer.scenes[0][offset+4]
        assert entry_state == 0
        await peer.request(0xc0fa1, struct.pack('>hhhhQ', *initial, *step, 1006))
        await peer.request(0xc0faa, b'\0'+struct.pack('>hhQ', *step, 1006))
        assert owner.position.value == (1006, *step) and not events.rows
        before, version = owner.position.value, owner.position.version
        await peer.request(0xc0faa, b'\0'+struct.pack('>hhQ', *wall, 1006))
        after, durable = owner.position.value, store.position(1111, role['id'])
        assert owner.battle is None and not runtime.battles
        return dict(ordinary_entry_state_byte=entry_state, clear_same_cell_control=True,
            source=before, blocked_target=(1006, *wall),
            blocked_grid_byte=grid.cells[(wall[1]//16)*grid.width+wall[0]//16],
            source_version=version, resulting_version=owner.position.version,
            resulting_position=after, durable_position=durable, rejection_events=events.rows,
            blocked_stop_rejected=(after == before and durable == before and bool(events.rows)),
            blocked_stop_accepted_and_saved=(after == (1006, *wall) and durable == after),
            scope='same-cell clear control, then actual encrypted STOP into original blocked node; not trajectory/GUI',
            initial_checkpoint_fixture=True, native_gui_verified=False,
            live_server_changed=False, battle_executed=False)
    finally:
        await runtime.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runtime-source', type=Path)
    parser.add_argument('--expect-gap', action='store_true')
    parser.add_argument('--report', type=Path,
        default=Path(__file__).parent/'evidence/world-encrypted-collision-verification.json')
    args = parser.parse_args()
    before = sources()
    with tempfile.TemporaryDirectory(prefix='world-encrypted-collision-') as directory:
        store = AccountStore(Path(directory)/'state.sqlite3')
        role = store.create_role(1111, '碰撞离线核查', 11, 1010109)
        result = asyncio.run(asyncio.wait_for(check(store, runtime_storage.prepare(store), role), 45))
    result.update(source=before, inputs_stable=before == sources(),
                  expect_gap=args.expect_gap, client_root=str(ROOT))
    write_json(args.report, result)
    print({name: result[name] for name in ('clear_same_cell_control', 'blocked_stop_rejected',
        'blocked_stop_accepted_and_saved', 'inputs_stable')})
    assert result['inputs_stable']
    if args.expect_gap:
        assert result['blocked_stop_accepted_and_saved'], 'Expected collision gap no longer reproduced'
    else:
        assert result['blocked_stop_rejected'], 'Actual encrypted STOP entered and saved an original blocked node'


if __name__ == '__main__':
    main()
