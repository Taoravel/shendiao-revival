"""Cancelled transfer resumes accepted position and visibility at one version."""
from dataclasses import replace
import struct
from inspect_client import OUT,write_json
from world_owner import MapOwner,MapAddress,Location,MoveCommand
from world_roles import RoleScene
from world_role_protocol import RoleBasic


def main():
    catalog={mid:dict(available=True,width=1024,height=1024,portals={}) for mid in (7,8)}
    source=MapOwner(MapAddress(7,1,0),catalog,capacity=2,transfer_capacity=2,mailbox_capacity=2)
    target=MapOwner(MapAddress(8,2,0),catalog,capacity=2,transfer_capacity=2,mailbox_capacity=2)
    view=RoleScene(source.address,catalog,radius=64,role_capacity=2,pair_capacity=1,batch_size=2)
    loc=Location(1,'epoch-a',source.address,1,100,100)
    source.join_with_view(loc,RoleBasic(1,'主角',9,100,100,0x71),view)
    source.join_with_view(replace(loc,role_id=2,login_epoch='epoch-b',x=120),
        RoleBasic(2,'同伴',10,120,100,0x32),view)
    offer=source.prepare_transfer(loc,(8,100,100),request_id='view-cancel',deadline_ms=1000,now_ms=0)
    reservation=target.reserve(offer,0);frozen=source.freeze(reservation,0)
    blocked,change=source.move_with_view(MoveCommand(frozen.source,'frozen-move',1000,0xc0faa,
        b'\0'+struct.pack('>hhQ',110,100,0)),1,view)
    assert blocked.rejection=='movement_frozen' and change is None and view.snapshot(1).location==loc
    cancelled=target.cancel(reservation)
    active,changed=source.resume_with_view(cancelled,view)
    assert active.state=='active' and active.version==3
    assert source.location(1)==view.snapshot(1).location==changed.presence.location
    again,duplicate=source.resume_with_view(cancelled,view)
    assert again==active and not duplicate.deliveries
    moved,changed=source.move_with_view(MoveCommand(active,'after-resume',1000,0xc0faa,
        b'\0'+struct.pack('>hhQ',110,100,0)),1,view)
    assert not moved.rejection and moved.location==changed.presence.location==source.location(1)
    report=dict(passed=['frozen movement leaves both snapshots unchanged',
        'explicit cancellation resumes both at the same active version',
        'duplicate cancellation produces no second view; ordinary movement continues'],
        shared_runtime_integrated=False,gui_verified=False,live_server_changed=False)
    write_json(OUT/'evidence/world-resume-view-verification.json',report)
    print(report)


if __name__=='__main__':main()
