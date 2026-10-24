"""A fenced old transfer retires map authority and its player projection."""
from dataclasses import replace
import struct
from inspect_client import OUT,write_json
from world_owner import MapOwner,MapAddress,Location,MoveCommand,TransferRecoveryDecision
from world_roles import RoleScene
from world_role_protocol import RoleBasic,S_REMOVE_USER_SCREEN


def refused(action):
    try:action()
    except ValueError:return
    raise AssertionError('Old recovery removed a replacement membership')


def check(committed):
    catalog={mid:dict(available=True,width=1024,height=1024,portals={}) for mid in (7,8)}
    source=MapOwner(MapAddress(7,1,0),catalog,capacity=2,transfer_capacity=2,mailbox_capacity=2)
    target=MapOwner(MapAddress(8,2,1),catalog,capacity=2,transfer_capacity=2,mailbox_capacity=2)
    sv=RoleScene(source.address,catalog,radius=64,role_capacity=2,pair_capacity=1,batch_size=2)
    tv=RoleScene(target.address,catalog,radius=64,role_capacity=2,pair_capacity=1,batch_size=2)
    loc=Location(1,'old-epoch',source.address,1,100,100)
    appearance=RoleBasic(1,'过图侠客',9,100,100,0x71)
    source.join_with_view(loc,appearance,sv)
    source.join_with_view(replace(loc,role_id=2,login_epoch='source-peer',x=120),
        RoleBasic(2,'源同伴',10,120,100,0x32),sv)
    target.join_with_view(Location(3,'target-peer',target.address,1,120,100),
        RoleBasic(3,'目标同伴',9,120,100,0x71),tv)
    offer=source.prepare_transfer(loc,(8,100,100),request_id='recovery-view',deadline_ms=1000,now_ms=0)
    reservation=target.reserve(offer,0);frozen=source.freeze(reservation,0);receipt=target.activate(frozen,0)
    authority=loc
    if committed:
        source.finalize_with_view(receipt,sv)
        active,_=target.ready_with_view(receipt.location,appearance,tv)
        result,_=target.move_with_view(MoveCommand(active,'after-target-ready',1000,0xc0faa,
            b'\0'+struct.pack('>hhQ',110,100,0)),1,tv)
        authority=result.location
    # Trusted decision shape; final SQL authority is verified separately by
    # verify_world_transfer_recovery. This test observes the map/view seam.
    decision=TransferRecoveryDecision(offer.transfer_id,loc,offer.target_position,'new-epoch',
        authority.position,authority.version,committed,offer,receipt if committed else None)
    source_snapshot=source.inspect_transfer(1,offer.transfer_id)
    target_snapshot=target.inspect_transfer(1,offer.transfer_id)
    a,source_change=source.retire_recovered_transfer_with_view(source_snapshot,decision,sv)
    b,target_change=target.retire_recovered_transfer_with_view(target_snapshot,decision,tv)
    assert source.location(1) is None and target.location(1) is None
    assert sv.snapshot(1) is None and tv.snapshot(1) is None
    change=target_change if committed else source_change
    assert len(change.deliveries)==1 and change.deliveries[0].packets[0][0]==S_REMOVE_USER_SCREEN
    assert not (source_change if committed else target_change).deliveries
    owner,view,snapshot=(target,tv,target_snapshot) if committed else (source,sv,source_snapshot)
    new=Location(1,'new-epoch',owner.address,decision.authority_version,*decision.authority_position[1:])
    owner.join_with_view(new,replace(appearance,x=new.x,y=new.y),view)
    current=view.snapshot(1)
    refused(lambda:owner.retire_recovered_transfer_with_view(snapshot,decision,view))
    assert owner.location(1)==new and view.snapshot(1)==current
    return dict(committed=committed,authority=new.position,new_epoch_preserved=True)


def main():
    report=dict(cases=[check(False),check(True)],
        scope='map/projection command; durable decision authorization covered by separate storage verifier',
        shared_runtime_integrated=False,gui_verified=False,live_server_changed=False)
    write_json(OUT/'evidence/world-recovery-view-verification.json',report)
    print(report)


if __name__=='__main__':main()
