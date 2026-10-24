"""Map authority and original player screen joins/departures are one command."""
from dataclasses import replace
from inspect_client import OUT,write_json
from world_owner import MapOwner,MapAddress,Location
from world_roles import RoleScene
from world_role_protocol import RoleBasic,S_ADD_USER_SCREEN,S_REMOVE_USER_SCREEN


def refused(action):
    try:action()
    except ValueError:return
    raise AssertionError('Rejected membership changed map or view')


def main():
    catalog={7:dict(available=True,width=1024,height=1024,portals={})}
    address=MapAddress(7,1,0)
    owner=MapOwner(address,catalog,capacity=2,transfer_capacity=2,mailbox_capacity=2)
    view=RoleScene(address,catalog,radius=64,role_capacity=3,pair_capacity=3,batch_size=2)
    a=Location(1,'epoch-a',address,1,100,100);b=replace(a,role_id=2,login_epoch='epoch-b',x=120)
    va=RoleBasic(1,'甲侠',9,100,100,0x71);vb=RoleBasic(2,'乙侠',10,120,100,0x32)
    loc,changed=owner.join_with_view(a,va,view)
    assert loc==a and changed.presence.location==a and not changed.deliveries
    second,joined=owner.join_with_view(b,vb,view)
    assert second==owner.location(2)==joined.presence.location
    assert {d.recipient_role_id for d in joined.deliveries}=={1,2}
    assert all(d.packets[0][0]==S_ADD_USER_SCREEN for d in joined.deliveries)
    assert not owner.join_with_view(b,vb,view)[1].deliveries
    # The view has a third slot, but authoritative map capacity is only two.
    c=replace(b,role_id=3,login_epoch='epoch-c',x=140)
    refused(lambda:owner.join_with_view(c,replace(vb,role_id=3,x=140),view))
    assert owner.location(3) is None and view.snapshot(3) is None
    # Original RoleBasic encoding must fail before the authoritative join.
    empty=MapOwner(address,catalog,capacity=1,transfer_capacity=1,mailbox_capacity=1)
    empty_view=RoleScene(address,catalog,radius=64,role_capacity=1,pair_capacity=0,batch_size=1)
    refused(lambda:empty.join_with_view(c,replace(vb,role_id=3,x=140,name='甲'*300),empty_view))
    assert empty.location(3) is None and empty_view.snapshot(3) is None
    room=MapOwner(address,catalog,capacity=2,transfer_capacity=1,mailbox_capacity=1)
    small=RoleScene(address,catalog,radius=64,role_capacity=1,pair_capacity=0,batch_size=1)
    room.join_with_view(a,va,small)
    refused(lambda:room.join_with_view(b,vb,small))
    assert room.location(2) is None and small.snapshot(2) is None
    refused(lambda:owner.leave_with_view(replace(b,version=2),view))
    assert owner.location(2)==b and view.snapshot(2)==joined.presence
    left,change=owner.leave_with_view(b,view)
    assert left==b and owner.location(2) is None and view.snapshot(2) is None
    assert len(change.deliveries)==1 and change.deliveries[0].recipient_role_id==1
    assert change.deliveries[0].packets[0][0]==S_REMOVE_USER_SCREEN
    assert owner.leave_with_view(b,view)[0] is None and not owner.leave_with_view(b,view)[1].deliveries
    replacement=replace(b,login_epoch='epoch-b-new')
    new,changed=owner.join_with_view(replacement,vb,view)
    refused(lambda:owner.leave_with_view(b,view))
    assert owner.location(2)==new and view.snapshot(2)==changed.presence
    report=dict(passed=['reciprocal join/retry and map capacity checked before view publication',
        'view capacity refusal leaves an otherwise available map slot absent',
        'invalid original RoleBasic leaves authority absent',
        'departure checks both snapshots, removes both and emits one native removal',
        'duplicate departure is empty; old departure cannot remove replacement login'],
        shared_runtime_integrated=False,gui_verified=False,live_server_changed=False)
    write_json(OUT/'evidence/world-membership-view-verification.json',report)
    print(report)


if __name__=='__main__':main()
