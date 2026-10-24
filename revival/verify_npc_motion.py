"""Map-owned movement through the lifecycle public seam, controlled grid."""
import struct
from dataclasses import replace
from world_catalog import maps,maze_grids
from world_grids import SceneGrid
from world_owner import MapAddress,Location
from world_npcs import load_placements,load_npc_definitions
from npc_lifecycle import (NpcLifecycle,NpcLifecycleCommand,NpcSpawn,NpcMove,npc_move_to,
    load_npc_motion_rules,NPC_MOVE_TO)
from verify_npc_movement_native import original_consumer
from inspect_client import OUT,write_json


def main():
    address=MapAddress(1007,77,0);placements=load_placements()[1007]
    p=next(p for p in placements if p.npc_id==10000)
    grid=SceneGrid(512,512,bytes(512*512),12)
    scene=NpcLifecycle(address,placements,maps(),generation='motion-map-a',
        interaction_radius=32,binding_capacity=4,receipt_capacity=4,
        motion_rules=load_npc_motion_rules(),maze=grid)
    key=(1007<<32)|p.placement_id
    scene.spawn(((key,p.placement_id),),load_npc_definitions(),batch_size=2)
    target=(p.x+100,p.y)
    move=NpcLifecycleCommand(address,'motion-map-a','move-a',scene.revision,10000,
        'move',(NpcMove(key,target,1000,1),),'trusted-patrol-fixture')
    result=scene.apply(move,now_ms=100)
    assert result.messages==(npc_move_to(key,1000,(p.x,p.y),target),)
    at_quarter=scene.view(now_ms=350)[0]
    assert (at_quarter.placement.x,at_quarter.placement.y)==(1705,5311)
    location=Location(1,'role-a',address,1,p.x,p.y)
    assert scene.interact(struct.pack('>q',key),location,location,
        request_id='near',deadline_ms=10000,now_ms=350).npc_id==10000
    try:scene.interact(struct.pack('>q',key),location,location,
        request_id='far-now',deadline_ms=10000,now_ms=750)
    except ValueError:pass
    else:raise AssertionError('NPC interaction used its old position during travel')
    snapshot=scene.snapshot(batch_size=2,now_ms=350)
    assert snapshot[-1]==npc_move_to(key,750,(1705,5311),target)
    seen,native=original_consumer(snapshot[-1][1])
    assert seen==[key] and native==(*target,1705,5311,750)
    arrivals=scene.advance(now_ms=1100)
    assert len(arrivals)==1 and arrivals[0].entity_key==key and arrivals[0].position==target
    assert scene.advance(now_ms=1100)==()
    assert not any(kind==NPC_MOVE_TO for kind,body in scene.snapshot(batch_size=2,now_ms=1100))
    def command(s,identity,target,*,duration=1000,mask=1):
        return NpcLifecycleCommand(address,'motion-map-a',identity,s.revision,10000,
            'move',(NpcMove(key,target,duration,mask),),'trusted-patrol-fixture')
    second=command(scene,'move-b',(1880,5311))
    scene.apply(second,now_ms=1200)
    replay=scene.apply(second,now_ms=1450)
    assert replay.replayed and replay.messages[-1]==npc_move_to(key,750,(1805,5311),(1880,5311))
    interrupted=command(scene,'interrupt',(1830,5411))
    assert scene.apply(interrupted,now_ms=1700).messages==(
        npc_move_to(key,1000,(1830,5311),(1830,5411)),)
    assert scene.advance(now_ms=2200)==(), 'Superseded move emitted its old arrival'
    later=scene.advance(now_ms=2700)
    assert len(later)==1 and later[0].position==(1830,5411) and later[0].event_id!=arrivals[0].event_id
    replay=scene.apply(second,now_ms=2800)
    assert replay.replayed and not any(k==NPC_MOVE_TO for k,b in replay.messages)
    assert (scene.view(now_ms=2800)[0].placement.x,scene.view(now_ms=2800)[0].placement.y)==(1830,5411)
    moving=command(scene,'remove-during-motion',(1930,5411))
    scene.apply(moving,now_ms=2800)
    removal=NpcLifecycleCommand(address,'motion-map-a','remove',scene.revision,10000,
        'remove',(key,),'trusted-patrol-fixture')
    scene.apply(removal,now_ms=2900)
    assert scene.advance(now_ms=4000)==() and not scene.view(now_ms=4000)
    assert not any(k==NPC_MOVE_TO for k,b in scene.apply(moving,now_ms=4000).messages)

    def fresh(maze=grid,rules=None):
        s=NpcLifecycle(address,placements,maps(),generation='motion-map-a',interaction_radius=32,
            binding_capacity=4,receipt_capacity=4,motion_rules=rules or load_npc_motion_rules(),maze=maze)
        s.spawn(((key,p.placement_id),),load_npc_definitions(),batch_size=2)
        return s
    def refused(s,cmd,now=100):
        before=s.view(now_ms=now),s.revision,s.next_entity_key,s.snapshot(batch_size=2,now_ms=now)
        try:s.apply(cmd,now_ms=now)
        except ValueError:pass
        else:raise AssertionError('Invalid NPC motion command accepted')
        assert (s.view(now_ms=now),s.revision,s.next_entity_key,s.snapshot(batch_size=2,now_ms=now))==before
    wall=bytearray(grid.cells);wall[(p.y//16)*grid.width+(p.x+50)//16]=1
    blocked=fresh(SceneGrid(grid.width,grid.height,bytes(wall),12))
    wall_move=command(blocked,'wall',target)
    refused(blocked,wall_move)
    assert blocked.apply(replace(wall_move,entities=(replace(wall_move.entities[0],collision_mask=8),)),now_ms=100).messages
    limited=fresh(rules=replace(load_npc_motion_rules(),max_path_pixels=50))
    refused(limited,command(limited,'budget',target))
    unknown=fresh(SceneGrid(grid.width,grid.height,grid.cells,12,bytes(len(grid.cells))))
    refused(unknown,command(unknown,'unknown-grid',target))
    mixed=fresh();mixed_move=command(mixed,'mixed',target)
    refused(mixed,replace(mixed_move,entities=(mixed_move.entities[0],replace(mixed_move.entities[0],entity_key=key+1))))
    assert mixed.advance(now_ms=2000)==()
    assert mixed.apply(mixed_move,now_ms=2000).messages
    for invalid in (replace(mixed_move.entities[0],duration_ms=0),
                    replace(mixed_move.entities[0],collision_mask=True),
                    replace(mixed_move.entities[0],target=(32768,5311))):
        s=fresh();refused(s,replace(command(s,'invalid',target),entities=(invalid,)))
    short=fresh();accepted=replace(command(short,'short-deadline',target),deadline_ms=150)
    short.apply(accepted,now_ms=100)
    assert len(short.advance(now_ms=1100))==1, 'Admission deadline cancelled an already accepted trajectory'
    visible=fresh()
    visible.apply(NpcLifecycleCommand(address,'motion-map-a','extra',visible.revision,10000,
        'spawn',(NpcSpawn(key+1,10000,p.x,p.y+20),),'trusted-visibility-fixture'),now_ms=10)
    visible.apply(replace(command(visible,'two-movers',target),entities=(
        NpcMove(key,target,1000,1),NpcMove(key+1,(p.x+100,p.y+20),1000,1))),now_ms=100)
    one=visible.snapshot(batch_size=2,now_ms=350,entity_keys=(key,))
    assert len(one)==2 and one[-1]==npc_move_to(key,750,(1705,5311),target)
    assert struct.unpack_from('>q',one[0][1],2)[0]==key
    assert visible.snapshot(batch_size=2,now_ms=350,entity_keys=())==()
    original=fresh(maze_grids()[1007])
    # Independent literal route checked against the shipped Linan maze. Mask1
    # is explicit fixture policy, not a recovered generic NPC movement mode.
    left=command(original,'original-linan',(1580,5311))
    original.apply(left,now_ms=100)
    actual=original.view(now_ms=350)[0].placement
    assert (actual.x,actual.y)==(1655,5311)
    resume=original.snapshot(batch_size=2,now_ms=350)[-1]
    assert resume==npc_move_to(key,750,(1655,5311),(1580,5311))
    assert original_consumer(resume[1])==([key],(1580,5311,1655,5311,750))
    other_direction=fresh(maze_grids()[1007])
    refused(other_direction,command(other_direction,'original-obstructed',(1780,5311)))
    report={'passed':['trusted move emits original duration/source/target message',
        'authoritative quarter position1705,5311 and moving distance changes interaction eligibility',
        'late snapshot resumes from current position for remaining750ms through original consumer',
        'arrival commits target once; later snapshots carry no obsolete move',
        'retry resumes remaining time without restarting; interruption rebases current position and cancels old arrival',
        'removal cancels travel; replay after later arrival/removal never restores an old move',
        'interior blocked cell rejects while explicit different mask preserves native bit semantics',
        'sparse unknown maze/path budget/mixed batch/bad fields fail atomically without consuming request',
        'accepted motion survives admission deadline; no extra assets or old arrival emitted',
        'trusted visibility subset includes only selected current presence and its remaining movement',
        'original Linan maze mask1 permits1680->1580, quarter1655 and native750ms resume; obstructed opposite route refused'],
        'grid':'controlled dense/sparse SceneGrid plus original Linan544x464 maze; native-proven collision implementation',
        'interpolation':'explicit designed reconstruction profile; not original animation fidelity',
        'shared_runtime_integrated':False,'native_gui_verified':False}
    write_json(OUT/'evidence/npc-motion-verification.json',report);print(report)


if __name__=='__main__':main()
