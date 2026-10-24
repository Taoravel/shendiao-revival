"""Offline natural CCheckMove via full MainCharacter update, exclusive research."""
import hashlib
import json
import struct
from pathlib import Path

from native_inspect import DATA
from native_gameplay_probe import probe
from pfs import PfsArchive
from world_grids import maze_grid
from verify_world_click_arrival_native import ClickArrivalProbe
from unicorn.x86_const import (UC_X86_REG_ECX, UC_X86_REG_EIP, UC_X86_REG_ESP,
    UC_X86_REG_ESI, UC_X86_REG_EBX, UC_X86_REG_EBP)


class ClickCheckProbe(ClickArrivalProbe):
    def __init__(self,*args,**kwargs):
        self.tree_calls=[]
        self.check_trace=[]
        super().__init__(*args,**kwargs)
        self.uc.reg_write(UC_X86_REG_ESI,self.role)
        self.uc.reg_write(UC_X86_REG_EBX,1)
        self.uc.reg_write(UC_X86_REG_EBP,0)
        self.uc.reg_write(UC_X86_REG_ESP,self.stack-0x100)
        self.uc.emu_start(0x11f0e9b,0x11f0ec6,count=10000)
        assert self.uc.reg_read(UC_X86_REG_EIP)==0x11f0ec6
        # Original Character constructor default: no auxiliary +26c actor.
        # The earlier click fixture aliases it to main actor only to exercise
        # the existing mask-selector slice. It is not the movement actor +48.
        self.uc.reg_write(UC_X86_REG_EBX,0)
        self.uc.emu_start(0x120a449,0x120a44f,count=100)
        assert self.read(self.role+0x26c)==0

    def hook(self,emu,addr,size,user):
        if addr == 0x1039380:
            obj=emu.reg_read(UC_X86_REG_ECX)
            sp=emu.reg_read(UC_X86_REG_ESP)
            self.tree_calls.append({'object':hex(obj),'return':hex(self.read(sp)),
                'header':[hex(self.read(obj+x)) for x in (0,4,8)]})
        if addr in (0x12179a0,0x120c830,0x12179b7,0x12171d0,0x12160b0,0xe9cd00):
            sp=emu.reg_read(UC_X86_REG_ESP)
            record={'address':hex(addr)}
            if addr != 0x12179b7:
                record['return']=hex(self.read(sp))
            self.check_trace.append(record)
        super().hook(emu,addr,size,user)


def scenario(grid,rmp,*,scene_control=None):
    run=ClickCheckProbe(grid.width,grid.height,grid.cells,(1488,1152),
        render_size=struct.unpack_from('<II',rmp,8))
    run.w(run.scene+0x30,1100,0)
    initial=run.input_tick()
    run.call(0x6529b0,(0x3f800000,),ecx=run.actor)
    midpoint=run.actor_tick(1008,8)
    try:
        run.call(0x12179a0,(1499,499))
        before_deadline=run.snapshot()
        if scene_control is not None:
            # A single fixture input changes AFTER native MOVE, before CHECK.
            run.w(run.scene+0x30,scene_control & 0xffffffff,scene_control >> 32)
        run.call(0x12179a0,(1500,1))
        at_deadline=run.snapshot()
        if scene_control is None:
            run.call(0x12179a0,(2000,500))
            repeated=run.snapshot()
        else:
            repeated=None
    except Exception:
        print(json.dumps({'tree_calls':run.tree_calls,'recent':run.recent,
            'trace':run.arrival_trace,'messages':run.messages},indent=2))
        raise
    assert initial['original_current']==(1488,1152)
    assert initial['history_character']==[(1488,1152)]
    assert midpoint['current']==(1496,1152) and midpoint['actor_projected']==(2244.,1152.)
    assert before_deadline['messages']==1 and before_deadline['check_countdown']==1
    assert at_deadline['messages']==2 and at_deadline['check_countdown']==500
    assert at_deadline['history_character']==[]
    for snapshot in (midpoint,before_deadline,at_deadline):
        assert snapshot['current']==(1496,1152)
        assert snapshot['future_engine']==snapshot['future_character']==[(1504.,1152.)]
    check=run.messages[1]
    assert check['kind']==0xc0fa3 and check['sender_return']=='0x12172b1'
    assert check['current']==(1496,1152) and check['history']==[(1488,1152)]
    assert run.messages[0]['scene_u64']==1100
    assert check['scene_u64']==(1100 if scene_control is None else scene_control)
    if repeated is not None:
        assert repeated['messages']==3 and repeated['check_countdown']==500
        assert run.messages[2]['history']==[] and run.messages[2]['current']==(1496,1152)
        assert repeated['future_engine']==repeated['future_character']==[(1504.,1152.)]
    decoded=[]
    for sent in run.messages[1:]:
        observed=[]
        def observe(emu,target):
            read=lambda a:struct.unpack('<I',emu.mem_read(a,4))[0]
            head=read(target+20)
            node=read(head)
            while node != head:
                assert len(observed)<16
                observed.append(struct.unpack('<hh',emu.mem_read(node+12,4)))
                node=read(node)
            assert len(observed)==read(target+24)
        _, obj=probe(0xe9c770,0xe9cd00,0xe9cda0,
            payload=bytes.fromhex(sent['body_hex']),observer=observe)
        assert observed==sent['history']
        assert struct.unpack_from('<hh',obj,12)==sent['current']
        assert struct.unpack_from('<Q',obj,32)[0]==sent['scene_u64']
        decoded.append({'history':observed,'current':sent['current'],'scene_u64':sent['scene_u64']})
    addresses=[x['address'] for x in run.check_trace]
    assert addresses.count('0x12179b7')==addresses.count('0x12179a0')
    assert addresses.count('0x12160b0')==len(run.messages)-1
    assert all(x['return']=='0x1217a4c' for x in run.check_trace if x['address']=='0x12171d0')
    assert all(x['return']=='0x1217299' for x in run.check_trace if x['address']=='0x12160b0')
    assert len(run.tree_calls)==addresses.count('0x12179a0')
    assert all(x['object']==hex(run.role+0xc8) and x['return']=='0x11e9dd3' for x in run.tree_calls)
    return {'scene_control_after_move':scene_control,'initial':initial,'midpoint':midpoint,
        'before_deadline':before_deadline,'at_deadline':at_deadline,'repeated':repeated,
        'original_sender_messages':run.messages,'native_decoded_checks':decoded,
        'full_update_trace':run.check_trace,'tree_calls':run.tree_calls,
        'engine_events':run.engine_events,'native_DDA_samples':run.dda_trace}


def main():
    root=Path(__file__).resolve().parent
    archive=PfsArchive(root/'runtime/client/artres/map.pfs')
    entries=['map_1100_gumupai/maze.dat','map_1100_gumupai/map.rmp']
    maze,rmp=(archive.read(name) for name in entries)
    grid=maze_grid(maze)
    normal=scenario(grid,rmp)
    control=scenario(grid,rmp,scene_control=0x1122334455667788)
    # A narrow control requested after discovering the auxiliary-actor alias:
    # corrected constructor defaults, actor tick/arrival only, no Main timer.
    arrival=ClickCheckProbe(grid.width,grid.height,grid.cells,(1488,1152),
        render_size=struct.unpack_from('<II',rmp,8))
    arrival.w(arrival.scene+0x30,1100,0)
    assert arrival.read(arrival.role+0x26c)==0
    arrival_initial=arrival.input_tick()
    arrival.call(0x6529b0,(0x3f800000,),ecx=arrival.actor)
    arrival_equal=arrival.actor_tick(1016,16)
    arrival_consumed=arrival.actor_tick(1017,1)
    assert [m['kind'] for m in arrival.messages]==[0xc0fa1,0xc0faa]
    assert arrival.messages[0]['body_hex']=='05d0048005e00480000000000000044c'
    assert arrival.messages[1]['body_hex']=='0105d0048005e00480000000000000044c'
    assert arrival.messages[1]['history']==[(1488,1152)]
    assert arrival.messages[1]['current']==(1504,1152)
    assert not arrival.check_trace  # No Main/base/CHECK calls in this control.
    check=normal['original_sender_messages'][1]
    assert check['body_hex']=='05d804800105d00480000000000000044c'
    assert normal['original_sender_messages'][2]['body_hex']=='05d8048000000000000000044c'
    assert control['original_sender_messages'][1]['body_hex']=='05d804800105d004801122334455667788'
    result={'all_passed':True,'scenarios':2,'image_sha256':hashlib.sha256(DATA).hexdigest(),
        'map_id':1100,'source':[1488,1152],'planned_goal':[1504,1152],
        'reported_current':[1496,1152],'check_message_type':0xc0fa3,
        'original_check_body_hex':check['body_hex'],
        'original_move_body_hex':normal['original_sender_messages'][0]['body_hex'],
        'original_repeat_check_body_hex':normal['original_sender_messages'][2]['body_hex'],
        'check_scene_u64':1100,'native_decoder_verified':True,
        'normal':normal,'scene_q64_single_variable':control,
        'auxiliary_default_move_stop_control':{'auxiliary_26c':0,'main_timer_entered':False,
            'initial':arrival_initial,'equal_budget':arrival_equal,'consumed':arrival_consumed,
            'original_sender_messages':arrival.messages,'original_trace':arrival.arrival_trace,
            'old_move_and_stop_bodies_unchanged':True},
        'constructor_slices':{'empty_state_tree':['0x11f0e9b','0x11f0ec6'],
            'auxiliary_actor_null':['0x120a449','0x120a44f']},
        'fixture_arguments':{'actor_multiplier':1.0,'actor_tick':[1008,8],
            'main_ticks':[[1499,499],[1500,1],[2000,500]],
            'units':'native deterministic inputs only; no physical speed or clock-unit claim'},
        'sources':[{'entry':n,'sha256':hashlib.sha256(raw).hexdigest(),'CRC_checked':True}
            for n,raw in zip(entries,(maze,rmp))],
        'scope':'same native input/actor -> full Main/base update -> natural timed CHECK builder and marshal',
        'unverified':['full App frame / OS input','production transport / owner integration',
            'original server speed and time units','nonempty state trees and optional auxiliary actors']}
    out=root/'evidence/world-click-check-native.json'
    out.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'all_passed':True,'scenarios':2,'original_check_body_hex':check['body_hex'],
        'result':str(out)}))


if __name__=='__main__':
    main()
