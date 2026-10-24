"""One native object: held click -> timed CHECK -> repeated CHECK -> STOP.

The host supplies tick arguments, never calls a movement packet builder.
"""
import hashlib
import json
import struct
from pathlib import Path

from native_inspect import DATA
from native_gameplay_probe import probe
from pfs import PfsArchive
from world_grids import maze_grid
from verify_world_click_check_native import ClickCheckProbe


def main():
    root=Path(__file__).resolve().parent
    archive=PfsArchive(root/'runtime/client/artres/map.pfs')
    entries=['map_1100_gumupai/maze.dat','map_1100_gumupai/map.rmp']
    maze,rmp=(archive.read(name) for name in entries)
    grid=maze_grid(maze)
    run=ClickCheckProbe(grid.width,grid.height,grid.cells,(1488,1152),
        render_size=struct.unpack_from('<II',rmp,8))
    run.w(run.scene+0x30,1100,0)
    initial=run.input_tick()
    run.call(0x6529b0,(0x3f800000,),ecx=run.actor)
    midpoint=run.actor_tick(1008,8)
    run.call(0x12179a0,(1499,499))
    before_deadline=run.snapshot()
    assert before_deadline['messages']==1 and before_deadline['check_countdown']==1
    run.call(0x12179a0,(1500,1))
    checked=run.snapshot()
    run.call(0x12179a0,(2000,500))
    repeated=run.snapshot()
    at_endpoint=run.actor_tick(2016,8)
    consumed=run.actor_tick(2017,1)
    assert [m['kind'] for m in run.messages]==[0xc0fa1,0xc0fa3,0xc0fa3,0xc0faa]
    assert initial['original_current']==(1488,1152)
    assert midpoint['current']==checked['current']==repeated['current']==(1496,1152)
    assert checked['history_character']==repeated['history_character']==[]
    assert at_endpoint['current']==(1504,1152) and at_endpoint['messages']==3
    assert consumed['current']==(1504,1152) and consumed['messages']==4
    assert consumed['future_engine']==consumed['future_character']==consumed['history_character']==[]
    stop=run.messages[-1]
    assert stop['history']==[] and stop['current']==(1504,1152)
    assert stop['scene_u64']==1100 and stop['sender_return']=='0x1217fce'
    observed=[]
    def observe(emu,target):
        read=lambda a:struct.unpack('<I',emu.mem_read(a,4))[0]
        head=read(target+12);node=read(head)
        while node!=head:
            assert len(observed)<16
            observed.append(struct.unpack('<hh',emu.mem_read(node+12,4)))
            node=read(node)
        assert len(observed)==read(target+16)
    _,decoded=probe(0xe9d5e0,0xe9d6d0,0xe9d780,
        payload=bytes.fromhex(stop['body_hex']),observer=observe)
    assert observed==[] and struct.unpack_from('<hh',decoded,24)==stop['current']
    assert struct.unpack_from('<Q',decoded,32)[0]==1100
    assert run.messages[1]['body_hex']=='05d804800105d00480000000000000044c'
    assert run.messages[2]['body_hex']=='05d8048000000000000000044c'
    assert stop['body_hex']=='0005e00480000000000000044c'
    assert all(m['scene_u64']==1100 for m in run.messages)
    for message in run.messages[1:-1]:
        history=[]
        def observe_check(emu,target):
            read=lambda a:struct.unpack('<I',emu.mem_read(a,4))[0]
            head=read(target+20);node=read(head)
            while node!=head:
                assert len(history)<16
                history.append(struct.unpack('<hh',emu.mem_read(node+12,4)))
                node=read(node)
            assert len(history)==read(target+24)
        _,decoded_check=probe(0xe9c770,0xe9cd00,0xe9cda0,
            payload=bytes.fromhex(message['body_hex']),observer=observe_check)
        assert history==message['history']
        assert struct.unpack_from('<hh',decoded_check,12)==message['current']
        assert struct.unpack_from('<Q',decoded_check,32)[0]==message['scene_u64']
    result=dict(all_passed=True,image_sha256=hashlib.sha256(DATA).hexdigest(),
        map_id=1100,source=[1488,1152],midpoint=[1496,1152],destination=[1504,1152],
        original_move_body_hex=run.messages[0]['body_hex'],
        original_check_body_hex=run.messages[1]['body_hex'],
        original_repeat_check_body_hex=run.messages[2]['body_hex'],
        original_stop_body_hex=stop['body_hex'],stop_message_type=0xc0faa,
        check_message_type=0xc0fa3,stop_native_decoder_verified=True,checks_native_decoder_verified=True,
        original_sender_messages=run.messages,initial=initial,midpoint_snapshot=midpoint,
        before_deadline=before_deadline,checked=checked,repeated=repeated,
        at_endpoint=at_endpoint,consumed=consumed,trace=run.arrival_trace,
        full_main_trace=run.check_trace,engine_events=run.engine_events,
        sources=[dict(entry=n,sha256=hashlib.sha256(raw).hexdigest(),CRC_checked=True)
            for n,raw in zip(entries,(maze,rmp))],
        scope='same native object click, full Main timed CHECK, repeat CHECK and natural actor arrival STOP',
        unverified=['full App frame / OS input / GPU','original server speed or clock units',
            'production transport and owner integration'])
    out=root/'evidence/world-click-check-arrival-native.json'
    out.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(dict(all_passed=True,messages=len(run.messages),stop_body_hex=stop['body_hex'])))


if __name__=='__main__':main()
