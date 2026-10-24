"""Actual legacy entry must not request a native lock without an opening.

Disposable AccountStore + real encrypted owners -> original world decoder ->
original intro branch and normal-input predicate. No client/listener/real role.
"""
import argparse
import asyncio
from contextlib import closing
import hashlib
from pathlib import Path
import struct
import sys
import tempfile

from inspect_client import OUT,write_json
from native_gameplay_probe import probe
from native_inspect import DATA
from verify_world_intro_black_native import Replay
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ESI


def native_entry(decoded,*,initial_intro_flag=0):
    r=Replay()
    r.e.mem_write(r.packet,decoded)
    # Isolate the already-proven intro gate; other independent gates are clear.
    role=0x500a000
    for address in (0x2945620,0x2945594,0x294556c,0x29455c0,0x294d190):
        r.w(address,0)
    r.e.mem_write(0x2945438,bytes([initial_intro_flag]))
    r.e.reg_write(UC_X86_REG_ESI,r.packet)
    r.run(0x83380a,r.packet)
    effect=bool(r.r(r.scene+0x39c))
    flag=r.e.mem_read(0x2945438,1)[0]
    r.run(0x1211db0,role)
    allowed=bool(r.e.reg_read(UC_X86_REG_EAX)&255)
    return dict(initial_intro_flag=initial_intro_flag,intro_q64=struct.unpack_from('<q',decoded,0x48)[0],
        native_black_effect_created=effect,native_intro_lock=flag,
        native_normal_move_gate_allowed=allowed)


async def check(store,prepared,legacy):
    from game_runtime import GameRuntime
    from verify_growth_runtime import GrowthPeer
    import game_runtime
    runtime=GameRuntime(store,prepared)
    try:
        peer=GrowthPeer(runtime)
        await peer.login(legacy)
        owner=runtime.roles[legacy['id']]
        _,decoded=probe(0xfe4160,0xfe45f0,0xfe4630,payload=peer.world_body)
        original=native_entry(decoded)
        starts=[body.hex() for kind,body in peer.initial if kind==0xc0017]
        with closing(store.connect()) as db:
            tasks=list(db.execute('SELECT task_id,state FROM task_journal WHERE role_id=?',(legacy['id'],)))
        assert owner.newbie_chapter is None and owner.newbie_pending is False
        assert not starts and not tasks, 'Fixture must remain a genuine unadopted legacy chapter'
        # A counterfactual only, never sent to the runtime/client or persisted.
        positive=bytearray(decoded)
        struct.pack_into('<q',positive,0x48,1)
        alternative=native_entry(bytes(positive))
        assert not alternative['native_black_effect_created']
        assert alternative['native_intro_lock']==0 and alternative['native_normal_move_gate_allowed']
        stale=native_entry(bytes(positive),initial_intro_flag=1)
        assert stale['native_intro_lock']==0 and stale['native_normal_move_gate_allowed']
        result=dict(legacy_no_chapter=True,server_newbie_pending=owner.newbie_pending,
            actual_entry=original,start_movie_frames=starts,task_rows=tasks,
            actual_position=owner.position.value,positive_intro_only_counterfactual=alternative,
            positive_entry_with_preexisting_lock=stale,
            unsafe_entry_reproduced=bool(original['native_black_effect_created']
                and original['native_intro_lock'] and not original['native_normal_move_gate_allowed']
                and not starts),
            safe_entry=not original['native_black_effect_created']
                and original['native_normal_move_gate_allowed'],
            input_scope='original intro slice and original normal-move predicate, other gates explicitly clear',
            native_image_sha256=hashlib.sha256(DATA).hexdigest(),database='disposable',
            runtime_source=str(Path(game_runtime.__file__).resolve()),
            runtime_source_sha256=hashlib.sha256(Path(game_runtime.__file__).read_bytes()).hexdigest(),
            shared_runtime_modified=False,live_server_changed=False,gui_verified=False)
        await peer.connection.close()
        return result
    finally:
        await runtime.close()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--expect-blocked',action='store_true')
    parser.add_argument('--release-source',type=Path,
        help='Offline inspection of an explicitly named immutable source folder')
    parser.add_argument('--report-suffix',help='Separate baseline/candidate evidence filename')
    args=parser.parse_args()
    if args.report_suffix:
        assert args.report_suffix.replace('-','').isalnum() and '/' not in args.report_suffix
    if args.release_source:
        source=args.release_source.resolve(strict=True)
        assert source.is_dir() and (source/'game_runtime.py').is_file()
        sys.path.insert(0,str(source))
    from accounts import AccountStore
    import runtime_storage
    with tempfile.TemporaryDirectory(prefix='legacy-native-entry-') as folder:
        store=AccountStore(Path(folder)/'state.sqlite3')
        # Public historical create before startup chapter policy installation,
        # matching existing legacy fixtures; no source/position/task deletion.
        legacy=store.create_role(1111,'旧档开场检查',11,1010109)
        prepared=runtime_storage.prepare(store)
        result=asyncio.run(asyncio.wait_for(check(store,prepared,legacy),timeout=45))
    suffix='baseline' if args.expect_blocked else 'verification'
    if args.release_source:suffix+='-release'
    if args.report_suffix:suffix=args.report_suffix
    write_json(OUT/f'evidence/world-legacy-intro-entry-{suffix}.json',result)
    print(result)
    if args.expect_blocked:
        assert result['unsafe_entry_reproduced'], 'Legacy no-opening lock no longer reproduces'
    else:
        assert result['safe_entry'], 'Legacy receives native black/move lock without any authorized opening'


if __name__=='__main__':main()
