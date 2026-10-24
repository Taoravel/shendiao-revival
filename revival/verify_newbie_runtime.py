"""Fresh creation -> school intro -> original successor via actual role owners.

Disposable storage and an in-memory encrypted connection; no client, listener,
battle, trusted task offer or manual character position/profile initialization.
"""
import argparse
import asyncio
from contextlib import closing
from pathlib import Path
import struct
import tempfile

from accounts import AccountStore
from game_runtime import GameRuntime
from inspect_client import OUT, write_json
from native_gameplay_probe import probe
from verify_growth_runtime import GrowthPeer
from world_newbie import load_newbie_routes, START_PLAY_CG, END_PLAY_CG
import runtime_storage


class MissingOpening(AssertionError):
    pass


def journal(store, role_id):
    with closing(store.connect()) as db:
        rows = tuple(db.execute('SELECT task_id,state FROM task_journal WHERE role_id=? ORDER BY task_id',
                                (role_id,)))
        effects = tuple(db.execute('SELECT task_id,payload FROM task_effects WHERE role_id=? ORDER BY task_id',
                                   (role_id,)))
        experience = db.execute('SELECT experience FROM role_progress WHERE role_id=?', (role_id,)).fetchone()
        revision = db.execute('SELECT revision FROM task_versions WHERE role_id=?', (role_id,)).fetchone()
    return rows, effects, experience, revision


def intro_field(peer):
    _, raw = probe(0xfe4160, 0xfe45f0, 0xfe4630, payload=peer.world_body)
    return struct.unpack_from('<q', raw, 0x48)[0]


def movie_frames(frames):
    return tuple(body for kind, body in frames if kind == START_PLAY_CG)


def require_opening(store, runtime, peer, role, route):
    actual = runtime.roles[role['id']].position.value
    expected = route.cinematic_endpoint
    rows = journal(store, role['id'])[0]
    starts = movie_frames(peer.initial)
    if actual != expected or rows != ((route.intro_task_id, 'active'),) or starts != (
            struct.pack('>i', route.intro_movie_id),):
        raise MissingOpening(str(dict(expected_position=expected, actual_position=actual,
            expected_root=route.intro_task_id, task_rows=rows,
            expected_movie=route.intro_movie_id, start_movies=[x.hex() for x in starts])))
    assert intro_field(peer) == 0, 'Pending intro did not retain its independent entry gate'
    _, decoded = probe(0xd574b0, 0xe410e0, 0xd57540, payload=starts[0])
    assert struct.unpack_from('<i', decoded, 8)[0] == route.intro_movie_id


async def check(store, prepared, legacy, fresh, routes):
    runtime = GameRuntime(store, prepared)
    try:
        old = GrowthPeer(runtime)
        await old.login(legacy)
        assert not movie_frames(old.initial), 'Legacy role acquired a fabricated intro'
        assert not journal(store, legacy['id'])[0]

        for index, role in enumerate(fresh):
            route = routes[(9, role['school'])]
            peer = GrowthPeer(runtime)
            await peer.login(role)
            require_opening(store, runtime, peer, role, route)
            before = journal(store, role['id'])
            # Waiting for a film must leave an unrelated role/map runnable.
            assert await asyncio.wait_for(old.request(100, bytes(4)), 1) == [(100, bytes(4))]
            other = runtime.roles[legacy['id']]
            location = await asyncio.wait_for(runtime.map(other.position.value[0]).mailbox.call(
                'location', other.id, other.epoch), 1)
            assert location.position == other.position.value
            try:
                await runtime.roles[role['id']].mailbox.call('offer_task', 100192)
            except ValueError:
                pass
            else:
                raise AssertionError('Trusted gameplay write bypassed the pending intro gate')
            assert journal(store, role['id']) == before
            # Wrong and malformed completion cannot turn into a task event.
            for body in (struct.pack('>i', route.intro_movie_id + 1), b'', bytes(3),
                         struct.pack('>i', route.intro_movie_id) + b'\0'):
                await peer.request(END_PLAY_CG, body)
                assert journal(store, role['id']) == before

            if index == 1:
                await peer.connection.close()
                peer = GrowthPeer(runtime)
                await peer.login(role)
                require_opening(store, runtime, peer, role, route)
                assert journal(store, role['id']) == before, 'Pending reconnect changed tasks or assets'

            end = struct.pack('>i', route.intro_movie_id)
            _, decoded = probe(0xd4f070, 0xe3fd70, 0xd4f110, payload=end)
            assert struct.unpack_from('<i', decoded, 8)[0] == route.intro_movie_id
            await peer.request(END_PLAY_CG, end)
            after = journal(store, role['id'])
            assert dict(after[0]) == {route.intro_task_id: 'completed', route.successor_task_id: 'active'}
            assert len(after[1]) == 1 and after[1][0][0] == route.intro_task_id
            assert after[2] == (0,), 'Original zero-XP intro was replaced with a fallback reward'
            await peer.request(END_PLAY_CG, end)
            assert journal(store, role['id']) == after, 'Repeated movie completion changed durable state'
            await peer.connection.close()
        await old.connection.close()
    finally:
        await runtime.close()

    # Recreate all owners and their storage Adapter; no old in-memory ticket survives.
    runtime = GameRuntime(store, prepared)
    try:
        for role in fresh:
            route = routes[(9, role['school'])]
            before = journal(store, role['id'])
            peer = GrowthPeer(runtime)
            await peer.login(role)
            assert not movie_frames(peer.initial), 'Completed chapter replayed after runtime reconstruction'
            assert intro_field(peer) == 1, 'Completed chapter did not project its designed positive entry value'
            assert runtime.roles[role['id']].position.value == route.cinematic_endpoint
            assert journal(store, role['id']) == before
            await peer.request(END_PLAY_CG, struct.pack('>i', route.intro_movie_id))
            assert journal(store, role['id']) == before
            await peer.connection.close()
    finally:
        await runtime.close()
    return dict(passed=[
        'fresh provenance naturally initializes original school root, designed spawn and native CG',
        'Gu Mu and Shaolin select different original movies and their character-specific successors',
        'wrong, malformed and duplicate movie completion cannot alter tasks or assets',
        'pending movie rejects trusted gameplay writes while another role heartbeat and map owner continue',
        'pending reconnect reauthorizes playback while preserving the active root',
        'completed reconnect and reconstructed runtime preserve position/tasks without replay',
        'real native codecs and continuous connection RC4/MPPC accept the messages'],
        database='disposable', trusted_task_offer_used=False, manual_spawn_used=False,
        battle_executed=False, native_gui_verified=False, live_server_changed=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--expect-missing', action='store_true')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='newbie-runtime-') as directory:
        store = AccountStore(Path(directory)/'state.sqlite3')
        legacy = store.create_role(1111, '旧剧情档', 11, 1010109)
        prepared = runtime_storage.prepare(store)
        fresh = (store.create_role(1111, '古墓新角', 11, 1010109),
                 store.create_role(1111, '少林新角', 111, 1010109))
        try:
            result = asyncio.run(check(store, prepared, legacy, fresh, load_newbie_routes()))
        except MissingOpening as error:
            if not args.expect_missing:
                raise
            result = dict(missing_opening_reproduced=True, observation=str(error), database='disposable',
                          native_gui_verified=False, live_server_changed=False, battle_executed=False)
        else:
            assert not args.expect_missing, 'Original missing-opening feedback no longer reproduces'
    suffix = 'baseline' if args.expect_missing else 'verification'
    write_json(OUT/f'evidence/newbie-runtime-{suffix}.json', result)
    print(result)


if __name__ == '__main__':
    main()
