"""Actual native auto-approach reports -> natural role's encrypted runtime.

Initial entities/models and clock inputs are explicit offline fixtures. The
optional native Scene branch executes original registration and lookup. The
server role reaches Jiaxing through its actual opening/tasks, without position
or quest writes. Opaque post-Visit packet c0fa7 is outside this check.
"""
import asyncio
import argparse
import hashlib
import json
from pathlib import Path
import struct
import tempfile

from accounts import AccountStore
from game_runtime import GameRuntime
from inspect_client import OUT, ROOT, write_json
from pfs import PfsArchive
import runtime_storage
from task_protocol import S_REFRESH_SCENARIO_QUEST_STATE
from verify_jiaxing_story_boundary_runtime import check as natural_boundary
from verify_runtime import Peer
from world_grids import maze_grid
from world_newbie import load_newbie_routes
from research_world_npc_approach_motion import Motion


class Events:
    def __init__(self):
        self.rows = []

    def emit(self, **event):
        self.rows.append(event)


def native_messages(*, native_scene_lookup=False):
    archive = PfsArchive(ROOT/'artres/map.pfs')
    maze = archive.read('map_1006_jiaxing/maze.dat')
    rmp = archive.read('map_1006_jiaxing/map.rmp')
    # Initial Scene-record fixture, before any input/constructor/sender runs.
    # This is the key assigned to original p13 by the actual runtime factory.
    key = (1006 << 32) | 13
    if native_scene_lookup:
        from research_world_scene_npc_lookup import NaturalLookup
        run = NaturalLookup(maze_grid(maze), struct.unpack_from('<II', rmp, 8),
                            final_radius=3, final_side=1, npc_key=key)
    else:
        run = Motion(maze_grid(maze), struct.unpack_from('<II', rmp, 8), 3, 1)
        run.w(run.npc+0x10, key & 0xffffffff, key >> 32)
    initial = run.navigate()
    run.call(0x6529b0, (0x3f800000,), ecx=run.actor)
    for now, delta in ((2000, 1000), (3000, 1000), (4000, 1000), (4001, 1)):
        run.now = now
        final = run.actor_tick(now, delta)
    run.w(run.stream, 0x224c100, run.stream_buffer, 0)
    run.w(run.stream_buffer-12, 4096, 0, 1)
    run.call(0xe52020, (run.stream,), ecx=run.packet_copy+0x100)
    visit = bytes(run.uc.mem_read(run.stream_buffer, run.read(run.stream_buffer-8)))
    assert visit == struct.pack('>Q', key)
    messages = []
    for message in run.messages:
        if message['kind'] == 0xc2329:
            message = dict(message, body_hex=visit.hex())
        if message['kind'] != 0xc0fa7:
            assert 'body_hex' in message
            messages.append(message)
    assert [m['kind'] for m in messages] == [0xc0fa1, 0xc0fa1, 0xc0fa1, 0xc0faa, 0xc2329]
    assert final['current'] == (1624, 1016)
    assert initial['messages'] == 1 and run.read(run.role+0x314) == 0
    assert bytes(run.uc.mem_read(run.maze_cells, len(maze)-12)) == maze[12:]
    if native_scene_lookup:
        assert any(entry['entry'] == '0x11d1870' and entry['return'] == '0x121742c'
                   and entry['arguments'][0] == 10498 for entry in run.real_lookup_entries), \
            'Natural arrival consumer bypassed the original template lookup'
        assert not any(event.get('adapter') == 'scene_NPC_template_lookup'
                       for event in run.navigation_events)
        assert [message['npc_key'] for message in run.messages
                if message['kind'] == 0xc2329] == [key]
    return dict(source=(1006, 360, 2264), destination=(1006, *final['current']),
                messages=messages, npc_key=key, final_snapshot=final,
                native_scope='original public navigation and actor-only ticks; no full Main timed CHECK loop',
                native_scene_lookup=native_scene_lookup,
                scene_lookup_entries=getattr(run, 'real_lookup_entries', []),
                source_maze_sha256=hashlib.sha256(maze).hexdigest())


async def check(store, prepared, role, route, witness, native, *, report_path):
    await natural_boundary(store, prepared, role, route, witness)
    events = Events()
    runtime = GameRuntime(store, prepared, prologue_touch=True, logger=events)
    result = dict(native=native, policy=store.npc_interaction_rules.revision,
                  natural_opening_task_prefix=True, approach_position_fixture=False,
                  source_updates=[], native_gui_verified=False, live_server_changed=False,
                  battle_executed=False)
    try:
        peer = Peer(runtime)
        await peer.login(role)
        owner = runtime.roles[role['id']]
        assert owner.position.value == tuple(native['source'])
        _, tasks = await owner.io(runtime_storage.task_state, store, 1111, role['id'], owner.epoch)
        assert 100106 in tasks.active
        for message in native['messages']:
            kind, body = message['kind'], bytes.fromhex(message['body_hex'])
            before = len(events.rows)
            replies = await peer.request(kind, body)
            rejected = [e for e in events.rows[before:] if e.get('event') == 'gameplay_rejected']
            result['source_updates'].append(dict(kind=kind, position=owner.position.value,
                rejections=rejected, reply_types=[k for k, _ in replies]))
            if rejected:
                result.update(all_passed=False, first_rejected_type=kind,
                    gap='Actual original actor-only stream was refused; full Main CHECK sequencing remains separate')
                write_json(report_path, result)
                raise AssertionError(('Original approach stream rejected', kind, rejected))
            if kind == 0xc2329:
                assert (S_REFRESH_SCENARIO_QUEST_STATE, struct.pack('>ii', 100106, 3)) in replies
        assert owner.position.value == tuple(native['destination']) and owner.battle is None
        await peer.connection.close()
        peer = Peer(runtime)
        await peer.login(role)
        assert runtime.roles[role['id']].position.value == tuple(native['destination'])
        result.update(all_passed=True, original_visit_opens_bloodmark_menu=True,
                      stop_checkpoint_reconnect_preserved=True,
                      private_transfer_or_battle_verified=False)
        return result
    finally:
        await runtime.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--native-scene-lookup', action='store_true',
                        help='Use original Scene registry and lookup, retaining explicit entity/model fixtures')
    args = parser.parse_args()
    suffix = '-native-scene' if args.native_scene_lookup else ''
    report_path = OUT/f'evidence/world-npc-approach-owner{suffix}-verification.json'
    names = ('game_runtime.py', 'runtime_storage.py', 'runtime_story_maps.py', 'world_owner.py',
             'world_movement.py', 'world_newbie.py', 'world_npcs.py', 'npc_interaction.py',
             'design/npc-interaction-v2.json', 'research_world_npc_approach_motion.py',
             'verify_world_npc_approach_owner.py')
    if args.native_scene_lookup:
        names += ('research_world_scene_npc_lookup.py',)
    before = {name: hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in names}
    # CPU-heavy original x86 runs before any live async owner loop exists.
    native = native_messages(native_scene_lookup=args.native_scene_lookup)
    write_json(OUT/f'evidence/world-npc-approach-owner{suffix}-native-input.json', native)
    route = load_newbie_routes()[(9, 11)]
    births = json.loads((OUT/'evidence/newbie-birth-sites-audit.json').read_text(encoding='utf-8'))
    witness = next(r for r in births['routes'] if (r['character_id'], r['school_id']) == (9, 11))
    with tempfile.TemporaryDirectory(prefix='world-native-approach-owner-') as folder:
        store = AccountStore(Path(folder)/'state.sqlite3')
        prepared = runtime_storage.prepare(store)
        role = store.create_role(1111, '原生血印接近', 11, 1010109)
        result = asyncio.run(asyncio.wait_for(check(store, prepared, role, route, witness, native,
            report_path=report_path), 45))
    after = {name: hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in names}
    assert before == after, 'Source changed during original-stream owner verification'
    result.update(source_sha256=before, inputs_stable=True)
    write_json(report_path, result)
    print({'all_passed': result['all_passed'], 'policy': result['policy'],
           'position': result['source_updates'][-1]['position'],
           'original_visit_opens_menu': True, 'reconnect_preserved': True})


if __name__ == '__main__':
    main()
