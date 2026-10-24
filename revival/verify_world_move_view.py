"""One map command must publish accepted position and player view together."""
from dataclasses import replace
import struct
from unittest.mock import patch
from inspect_client import OUT,write_json
from world_owner import MapOwner,MapAddress,Location,MoveCommand
from world_roles import RoleScene
from world_role_protocol import RoleBasic,S_ADD_USER_SCREEN


def main():
    catalog={7:dict(available=True,width=1024,height=1024,portals={(6,6):(8,100,100)}),
             8:dict(available=True,width=1024,height=1024,portals={})}
    address=MapAddress(7,1,0)
    owner=MapOwner(address,catalog,capacity=3,transfer_capacity=3,mailbox_capacity=3)
    view=RoleScene(address,catalog,radius=64,role_capacity=3,pair_capacity=1,batch_size=2)
    locations={};presences={}
    for role_id,x in ((1,100),(2,120),(3,500)):
        location=Location(role_id,f'epoch-{role_id}',address,1,x,100)
        locations[role_id]=owner.join(location)
        presences[role_id]=view.join(location,RoleBasic(role_id,f'侠客{role_id}',9,x,100,0x71)).presence
    command=MoveCommand(locations[3],'view-move',10000,0xc0faa,b'\0'+struct.pack('>hhQ',110,100,0))
    result,change=owner.move_with_view(command,1,view)
    assert result.rejection and change is None
    assert owner.location(3)==locations[3] and view.snapshot(3)==presences[3]
    assert view.visible_ids(1)==(2,) and view.visible_ids(3)==()
    # Release one pair and retry the same actual command. No source state was
    # published on rejection, so its expected version remains valid.
    owner.leave(locations[2]);view.leave(presences[2])
    with patch('builtins.open',side_effect=AssertionError('Movement hot-path I/O')), \
         patch('io.open',side_effect=AssertionError('Movement hot-path I/O')):
        result,change=owner.move_with_view(command,1,view)
    assert not result.rejection and result.checkpoint==owner.location(3)==change.presence.location
    assert view.snapshot(3)==change.presence and owner.location(3).position==(7,110,100)
    assert result.offer.target_position==(8,100,100) and result.offer.source==result.location
    assert {d.recipient_role_id for d in change.deliveries}=={1,3}
    assert all(d.packets[0][0]==S_ADD_USER_SCREEN for d in change.deliveries)
    accepted=result.location;accepted_view=view.snapshot(3)
    stale,change=owner.move_with_view(command,2,view)
    assert stale.rejection=='stale_position' and change is None
    intention=MoveCommand(accepted,'intention',10000,0xc0fa1,struct.pack('>hhhhQ',110,100,120,100,0))
    intended,change=owner.move_with_view(intention,2,view)
    assert intended.location==accepted and intended.checkpoint is None and change is None
    assert owner.location(3)==accepted and view.snapshot(3)==accepted_view
    # A failed projection must also preserve an already registered source
    # offer. Its exact public freeze can still succeed after the refusal.
    b=replace(locations[2],x=500)
    owner.join_with_view(b,RoleBasic(2,'乙侠',10,500,100,0x32),view)
    kept=owner.prepare_transfer(b,(8,200,200),request_id='existing-offer',deadline_ms=10000,now_ms=0)
    rejected,_=owner.move_with_view(MoveCommand(b,'rejected-offer',10000,0xc0faa,
        b'\0'+struct.pack('>hhQ',110,100,0)),2,view)
    assert rejected.rejection and owner.location(2)==b
    target=MapOwner(MapAddress(8,5,1),catalog,capacity=1,transfer_capacity=1,mailbox_capacity=1)
    assert owner.freeze(target.reserve(kept,2),2).reservation.offer==kept
    report=dict(passed=['pair-capacity refusal preserves authority and player projection',
        'retry after capacity release publishes checkpoint, reciprocal view and portal proposal together',
        'stale/intent-only reports do not advance either snapshot',
        'failed view preserves an existing offer for exact source freeze',
        'no hot-path I/O'],shared_runtime_integrated=False,gui_verified=False,live_server_changed=False)
    write_json(OUT/'evidence/world-move-view-verification.json',report)
    print(report)


if __name__=='__main__':main()
