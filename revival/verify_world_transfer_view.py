"""Player visibility follows map freeze/finalize/ready ownership boundaries."""
from dataclasses import replace
from inspect_client import OUT,write_json
from world_owner import MapOwner,MapAddress,Location,MoveCommand
import struct
from world_roles import RoleScene
from world_role_protocol import RoleBasic,S_REMOVE_USER_SCREEN,S_ADD_USER_SCREEN,S_ROLE_MOVE


def refused(action):
    try:action()
    except ValueError:return
    raise AssertionError('Invalid target view activated map membership')


def main():
    catalog={mid:dict(available=True,width=1024,height=1024,portals={}) for mid in (7,8)}
    source=MapOwner(MapAddress(7,1,0),catalog,capacity=2,transfer_capacity=2,mailbox_capacity=2)
    target=MapOwner(MapAddress(8,2,1),catalog,capacity=2,transfer_capacity=2,mailbox_capacity=2)
    source_view=RoleScene(source.address,catalog,radius=64,role_capacity=2,pair_capacity=1,batch_size=2)
    target_view=RoleScene(target.address,catalog,radius=64,role_capacity=2,pair_capacity=1,batch_size=2)
    loc=Location(1,'epoch-a',source.address,1,100,100)
    appearance=RoleBasic(1,'过图侠客',9,100,100,0x71)
    source.join_with_view(loc,appearance,source_view)
    source.join_with_view(replace(loc,role_id=2,login_epoch='epoch-b',x=120),
        RoleBasic(2,'源图侠客',10,120,100,0x32),source_view)
    target.join_with_view(Location(3,'epoch-c',target.address,1,120,100),
        RoleBasic(3,'目标侠客',9,120,100,0x71),target_view)
    offer=source.prepare_transfer(loc,(8,100,100),request_id='view-transfer',deadline_ms=1000,now_ms=0)
    reservation=target.reserve(offer,0)
    frozen=source.freeze(reservation,0)
    receipt=target.activate(frozen,0)
    assert source_view.snapshot(1).location==loc and target_view.snapshot(1) is None
    # Trusted caller has established its durable decision; this verifier tests
    # domain publication only, not a real SQL transaction or scene-send ACK.
    result,change=source.finalize_with_view(receipt,source_view)
    assert result==receipt and source.location(1) is None and source_view.snapshot(1) is None
    assert len(change.deliveries)==1 and change.deliveries[0].recipient_role_id==2
    assert change.deliveries[0].packets[0][0]==S_REMOVE_USER_SCREEN
    assert not source.finalize_with_view(receipt,source_view)[1].deliveries
    refused(lambda:target.ready_with_view(receipt.location,replace(appearance,name='甲'*300),target_view))
    assert target.location(1)==receipt.location and target_view.snapshot(1) is None
    active,entered=target.ready_with_view(receipt.location,appearance,target_view)
    assert active.state=='active' and target.location(1)==entered.presence.location
    assert {d.recipient_role_id for d in entered.deliveries}=={1,3}
    assert all(d.packets[0][0]==S_ADD_USER_SCREEN for d in entered.deliveries)
    command=MoveCommand(active,'target-player-move',1000,0xc0faa,b'\0'+struct.pack('>hhQ',110,100,0))
    moved,change=target.move_with_view(command,1,target_view)
    assert not moved.rejection and moved.location==target_view.snapshot(1).location
    assert change.deliveries[0].recipient_role_id==3 and change.deliveries[0].packets[0][0]==S_ROLE_MOVE
    report=dict(passed=['freeze/loading do not publish target player view',
        'source finalize removes authority and original player view in one command',
        'duplicate finalize does not repeat the removal',
        'failed original entry encoding preserves loading; valid ready publishes reciprocal target view',
        'accepted target movement keeps authority and projection synchronized'],
        durable_commit_tested=False,shared_runtime_integrated=False,gui_verified=False,live_server_changed=False)
    write_json(OUT/'evidence/world-transfer-view-verification.json',report)
    print(report)


if __name__=='__main__':main()
