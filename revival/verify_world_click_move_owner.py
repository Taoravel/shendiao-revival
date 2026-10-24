"""Native held-ground-input body -> encrypted connection -> actual role/map.

The original emulator supplies intention and optional timed CHECK/arrival STOP.
No invented report, position write, socket listener, GUI, or live DB is used.
"""
import argparse
import asyncio
from contextlib import closing
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import time

from inspect_client import OUT,write_json


class Events:
    def __init__(self):self.rows=[]
    def emit(self,**event):self.rows.append(event)
    def rejected_moves(self):
        return [r for r in self.rows if r.get('event')=='gameplay_rejected' and r.get('type')==0xc0fa1]


async def check(store,prepared,role,native,arrival=None,opening=None,transit=None):
    from game_runtime import GameRuntime
    import game_runtime
    from verify_growth_runtime import GrowthPeer
    from world_newbie import load_newbie_routes
    events=Events();runtime=GameRuntime(store,prepared,logger=events)
    timing={};started=time.monotonic()
    try:
        route=load_newbie_routes()[(9,11)]
        peer=GrowthPeer(runtime);await peer.login(role)
        owner=runtime.roles[role['id']]
        body=bytes.fromhex(native['original_body_hex'])
        assert (native['map_id'],*native['source'])==route.cinematic_endpoint
        address=runtime.map(route.home_map_id)
        async def location():
            return await address.mailbox.call('location',owner.id,owner.epoch)
        before=await location()
        assert before.position==route.cinematic_endpoint and owner.newbie_pending
        before_rejections=len(events.rejected_moves())
        await peer.request(0xc0fa1,body)
        assert len(events.rejected_moves())==before_rejections+1
        assert await location()==before
        if transit is not None:
            for message in transit['original_sender_messages'][1:]:
                count=len(events.rows)
                assert await peer.request(message['kind'],bytes.fromhex(message['body_hex']))==[]
                assert any(r.get('event')=='gameplay_rejected' and r.get('type')==message['kind']
                    for r in events.rows[count:]), 'Pending chapter accepted a native movement checkpoint'
                assert await location()==before
        end=struct.pack('>i',route.intro_movie_id)
        if opening is not None:
            original=opening['skip_event_result']
            starts=[payload for kind,payload in peer.initial if kind==0xc0017]
            assert starts==[bytes.fromhex(opening['wire_body_hex'])]
            assert opening['decoded_movie_id']==route.intro_movie_id
            assert original['movie_id']==route.intro_movie_id and original['actual_end_type']==0xc0018
            assert original['manager_3c_after']==0 and original['ordinary_input_allowed']
            end=bytes.fromhex(original['actual_end_body_hex'])
        await peer.request(0xc0018,end)
        assert not owner.newbie_pending
        active=await location()
        with closing(store.connect()) as db:
            saved_before=db.execute('SELECT map_id,x,y FROM role_positions WHERE role_id=?',(owner.id,)).fetchone()
        rejections=len(events.rejected_moves())
        assert await peer.request(0xc0fa1,body)==[]
        assert len(events.rejected_moves())==rejections, 'Actual original movement body was rejected'
        assert await location()==active, 'Movement intention was mistaken for arrival'
        with closing(store.connect()) as db:
            saved_after=db.execute('SELECT map_id,x,y FROM role_positions WHERE role_id=?',(owner.id,)).fetchone()
        assert saved_after==saved_before==route.cinematic_endpoint
        assert await peer.request(100,b'abcd')==[(100,b'abcd')]
        result=dict(pending_original_intention_rejected=True,
            completed_original_intention_accepted=True,authority_remains_at_start=True,
            durable_position_unchanged=True,continuous_rc4_mppc_heartbeat=True,
            original_body_hex=body.hex(),map_id=route.home_map_id,
            current=list(active.position),original_client_goal=native['expected_goal'],
            source=str(Path(game_runtime.__file__).resolve()),
            source_sha256=hashlib.sha256(Path(game_runtime.__file__).read_bytes()).hexdigest(),
            movement_scope='original intention only; native motion tick/CHECK/STOP/arrival not executed',
            end_scope='matching server completion request, not native movie end producer',
            shared_runtime_modified=False,live_server_changed=False,gui_verified=False)
        if opening is not None:
            result.update(native_start_matches_actual_server_body=True,
                native_event_end_body_hex=end.hex(),
                end_scope='original controlled event -> Return/End queue -> actual CEnd body; Scene restore is an Adapter, OS ESC/complete movie rendering unverified')
        if transit is not None:
            assert transit is arrival
            assert transit['original_move_body_hex']==body.hex()
            updates=[]
            last=active
            for message in transit['original_sender_messages'][1:-1]:
                assert message['kind']==0xc0fa3
                count=len(events.rows)
                assert await peer.request(message['kind'],bytes.fromhex(message['body_hex']))==[]
                assert not any(r.get('event')=='gameplay_rejected' for r in events.rows[count:])
                confirmed=await location()
                assert confirmed.position==(route.home_map_id,*message['current'])
                assert confirmed.version>last.version
                with closing(store.connect()) as db:
                    durable=db.execute('SELECT map_id,x,y FROM role_positions WHERE role_id=?',(owner.id,)).fetchone()
                assert durable==saved_before, 'CHECK bypassed the coalesced checkpoint policy'
                updates.append(dict(body_hex=message['body_hex'],position=list(confirmed.position),
                    version=confirmed.version,history=message['history'],durable_position=list(durable)))
                last=confirmed
            assert len(updates)==2
            result.update(natural_timed_checks_accepted=True,check_updates=updates,
                pending_native_checks_and_stop_rejected=True,checks_coalesced_before_stop=True)
        if arrival is not None:
            assert arrival['original_move_body_hex']==body.hex()
            assert arrival['map_id']==route.home_map_id and arrival['source']==list(active.position[1:])
            stop=bytes.fromhex(arrival['original_stop_body_hex'])
            rejected_before=len(events.rows)
            assert await peer.request(arrival['stop_message_type'],stop)==[]
            assert not any(r.get('event')=='gameplay_rejected' for r in events.rows[rejected_before:])
            arrived=await location()
            target=(route.home_map_id,*arrival['destination'])
            assert arrived.position==target and arrived.version>(last.version if transit is not None else active.version)
            with closing(store.connect()) as db:
                saved=db.execute('SELECT p.map_id,p.x,p.y,v.version FROM role_positions p '
                    'JOIN position_versions v ON v.role_id=p.role_id WHERE p.role_id=?',(owner.id,)).fetchone()
            assert saved==(*target,arrived.version), 'Natural STOP did not reach the durable checkpoint'
            timing['stop_committed_seconds']=time.monotonic()-started
            await peer.connection.close()
            timing['first_close_seconds']=time.monotonic()-started
            peer=GrowthPeer(runtime);await peer.login(role)
            timing['reconnect_seconds']=time.monotonic()-started
            restored=runtime.roles[role['id']]
            current=await runtime.map(route.home_map_id).mailbox.call('location',restored.id,restored.epoch)
            assert current.position==target and current.version>=arrived.version
            assert not restored.newbie_pending and not any(k==0xc0017 for k,_ in peer.initial)
            assert await peer.request(100,b'efgh')==[(100,b'efgh')]
            result.update(natural_stop_accepted=True,natural_stop_body_hex=stop.hex(),
                natural_stop_committed_position=list(target),natural_stop_checkpoint_version=arrived.version,
                reconnect_preserved_arrival=True,completed_chapter_not_replayed=True,
                movement_scope='original click/actor tick/arrival STOP -> actual encrypted owners -> durable checkpoint -> reconnect; no timed CHECK/speed/GUI proof')
            if transit is not None:
                result['movement_scope']='same native object MOVE/full Main timed CHECK/repeat CHECK/natural STOP -> actual encrypted owners -> coalesced durable checkpoint -> reconnect; no original speed/GUI proof'
        await peer.connection.close()
        result['elapsed_seconds']=round(time.monotonic()-started,3)
        if arrival is not None:result['phase_timing_seconds']=timing
        return result
    finally:
        await runtime.close()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--runtime-source',type=Path)
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--arrival',action='store_true',help='Include original actor arrival and durable reconnect')
    mode.add_argument('--check-arrival',action='store_true',help='Include same-object full Main CHECK, repeat CHECK, natural STOP and reconnect')
    parser.add_argument('--native-opening-report',type=Path,
        help='Explicit original intro-dispatch capture to replay, including native CEnd')
    parser.add_argument('--report-label',default='',help='Separate immutable/current/candidate evidence')
    args=parser.parse_args()
    assert not args.report_label or args.report_label.replace('-','').isalnum()
    native_run=subprocess.run([sys.executable,'-B',str(OUT/'verify_world_click_move_native.py')],
        capture_output=True,text=True,timeout=30)
    assert native_run.returncode==0,native_run.stderr or native_run.stdout
    native=json.loads((OUT/'evidence/world-click-move-native.json').read_text(encoding='utf-8'))
    assert native['all_passed'] and native['native_decoder_verified']
    arrival=None
    transit=None
    arrival_name='world-click-check-arrival' if args.check_arrival else 'world-click-arrival'
    if args.arrival or args.check_arrival:
        arrived=subprocess.run([sys.executable,'-B',str(OUT/f'verify_{arrival_name.replace("-","_")}_native.py')],
            capture_output=True,text=True,timeout=30)
        assert arrived.returncode==0,arrived.stderr or arrived.stdout
        arrival=json.loads((OUT/f'evidence/{arrival_name}-native.json').read_text(encoding='utf-8'))
        assert arrival['all_passed'] and arrival['stop_native_decoder_verified']
        if args.check_arrival:transit=arrival
    if args.runtime_source:
        source=args.runtime_source.resolve(strict=True)
        assert (source/'game_runtime.py').is_file()
        sys.path.insert(0,str(source))
    opening=None
    if args.native_opening_report:
        opening=json.loads(args.native_opening_report.read_text(encoding='utf-8'))['cold_ui_and_skip_event']
        assert opening['cold_ui'] and opening['skip_event_result'] is not None
    from accounts import AccountStore
    import runtime_storage
    with tempfile.TemporaryDirectory(prefix='native-click-role-owner-') as folder:
        store=AccountStore(Path(folder)/'state.sqlite3')
        prepared=runtime_storage.prepare(store)
        role=store.create_role(1111,'原生点地上行',11,1010109)
        result=asyncio.run(asyncio.wait_for(check(store,prepared,role,native,arrival,opening,transit),timeout=45))
    result['native_evidence_sha256']=hashlib.sha256((OUT/'evidence/world-click-move-native.json').read_bytes()).hexdigest()
    result['native_verifier_sha256']=hashlib.sha256((OUT/'verify_world_click_move_native.py').read_bytes()).hexdigest()
    suffix='check-arrival' if args.check_arrival else ('arrival' if args.arrival else 'move')
    if args.report_label:suffix+='-'+args.report_label
    if arrival is not None:
        result['native_arrival_evidence_sha256']=hashlib.sha256((OUT/f'evidence/{arrival_name}-native.json').read_bytes()).hexdigest()
        result['native_arrival_verifier_sha256']=hashlib.sha256((OUT/f'verify_{arrival_name.replace("-","_")}_native.py').read_bytes()).hexdigest()
    if opening is not None:
        result['native_opening_report_sha256']=hashlib.sha256(args.native_opening_report.read_bytes()).hexdigest()
    write_json(OUT/f'evidence/world-click-{suffix}-owner-verification.json',result)
    print(result)


if __name__=='__main__':main()
