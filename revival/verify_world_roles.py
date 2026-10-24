"""Map-instance player visibility through the public scene/codec Interfaces."""
from dataclasses import replace
from unittest.mock import patch
from inspect_client import OUT,write_json
from world_owner import MapAddress,Location
from world_role_protocol import (RoleBasic,S_ADD_USER_SCREEN,S_REMOVE_USER_SCREEN,S_ROLE_MOVE,
                                 role_screen,remove_role_screen,role_move)
from world_roles import RoleScene


def refused(action):
    try: action()
    except ValueError: return
    raise AssertionError('Invalid or stale player visibility mutation accepted')


def main():
    catalog={7:dict(available=True,width=1024,height=1024,portals={})}
    address=MapAddress(7,1,0)
    scene=RoleScene(address,catalog,radius=64,role_capacity=4,pair_capacity=8,batch_size=2)
    a=Location(1,'role-a',address,1,100,100)
    b=Location(2,'role-b',address,1,164,100)
    va=RoleBasic(1,'甲侠',9,100,100,0x71)
    vb=RoleBasic(2,'乙侠',10,164,100,0x32)
    first=scene.join(a,va)
    assert first.presence.location==a and not first.deliveries
    second=scene.join(b,vb)
    deliveries={d.recipient_role_id:d for d in second.deliveries}
    assert deliveries[1].packets==((S_ADD_USER_SCREEN,role_screen((vb,))),)
    assert deliveries[2].packets==((S_ADD_USER_SCREEN,role_screen((va,))),)
    assert scene.visible_ids(1)==(2,) and scene.visible_ids(2)==(1,)
    assert all(scene.delivery_is_current(d) for d in second.deliveries)
    assert scene.join(b,vb).presence==second.presence and not scene.join(b,vb).deliveries
    refused(lambda: scene.join(replace(b,role_id=3,address=MapAddress(7,2,0)),replace(vb,role_id=3)))
    refused(lambda: scene.join(replace(b,role_id=3),replace(vb,role_id=3,properties=[])))
    c=Location(3,'role-c',address,1,400,100)
    vc=RoleBasic(3,'丙侠',9,400,100,0x71)
    third=scene.join(c,vc)
    assert not third.deliveries and not scene.visible_ids(3)
    crossing=scene.move(second.presence,replace(b,version=2,x=400))
    updates={d.recipient_role_id:d for d in crossing.deliveries}
    assert updates[1].packets==((S_REMOVE_USER_SCREEN,remove_role_screen((2,))),)
    assert updates[3].packets==((S_ADD_USER_SCREEN,role_screen((replace(vb,x=400),))),)
    assert updates[2].packets==((S_REMOVE_USER_SCREEN,remove_role_screen((1,))),
                               (S_ADD_USER_SCREEN,role_screen((vc,))))
    assert scene.visible_ids(1)==() and scene.visible_ids(2)==(3,) and scene.visible_ids(3)==(2,)
    step=scene.move(crossing.presence,replace(b,version=3,x=401))
    assert len(step.deliveries)==1 and step.deliveries[0].recipient_role_id==3
    assert step.deliveries[0].packets==((S_ROLE_MOVE,role_move(2,401,100)),)
    assert step.deliveries[0].sequence==updates[3].sequence+1
    assert step.presence.membership_revision==second.presence.membership_revision
    assert scene.delivery_is_current(updates[2])  # Moving preserves this membership.
    refused(lambda: scene.move(second.presence,replace(b,version=4,x=402)))
    refused(lambda: scene.move(step.presence,replace(b,version=3,x=402)))
    refused(lambda: scene.move(step.presence,replace(b,version=4,x=402,login_epoch='old')))
    left=scene.leave(step.presence)
    assert left.presence is None and len(left.deliveries)==1
    assert left.deliveries[0].recipient_role_id==3
    assert left.deliveries[0].packets==((S_REMOVE_USER_SCREEN,remove_role_screen((2,))),)
    assert scene.snapshot(2) is None and scene.visible_ids(3)==()
    assert not scene.delivery_is_current(updates[2])
    assert not scene.leave(step.presence).deliveries
    # A world transfer can return to the SAME scene/epoch without reconnecting.
    # Old delivery scope must not alias that fresh membership.
    returned=scene.join(replace(b,version=8,x=401),replace(vb,x=401))
    assert returned.presence.membership_revision>step.presence.membership_revision
    assert not scene.delivery_is_current(updates[2])
    assert all(scene.delivery_is_current(d) for d in returned.deliveries)
    assert scene.join(returned.presence.location,returned.presence.appearance).presence==returned.presence
    scene.leave(returned.presence)
    replacement=scene.join(replace(b,version=1,x=401,login_epoch='role-b-new'),replace(vb,x=401))
    assert replacement.presence.revision>step.presence.revision
    refused(lambda: scene.leave(step.presence))
    assert not scene.delivery_is_current(updates[2])
    restarted=RoleScene(address,catalog,radius=64,role_capacity=4,pair_capacity=8,batch_size=2)
    copy=restarted.join(replacement.presence.location,replacement.presence.appearance)
    refused(lambda: restarted.leave(replacement.presence))
    assert copy.presence.owner_generation!=replacement.presence.owner_generation
    isolated=RoleScene(MapAddress(7,2,0),catalog,radius=64,role_capacity=4,pair_capacity=8,batch_size=2)
    separate=isolated.join(replace(a,address=isolated.address),va)
    assert not separate.deliveries and isolated.visible_ids(1)==()
    assert not isolated.delivery_is_current(deliveries[1])

    limited=RoleScene(address,catalog,radius=64,role_capacity=3,pair_capacity=1,batch_size=1)
    la,lb,lc=(limited.join(p,v).presence for p,v in ((a,va),(b,vb),(c,vc)))
    refused(lambda: limited.move(lc,replace(c,version=2,x=150)))
    assert limited.snapshot(3)==lc and limited.visible_ids(1)==(2,) and limited.visible_ids(3)==()
    limited.leave(lb)
    with patch('builtins.open',side_effect=AssertionError('Hot-path file access')), \
         patch('io.open',side_effect=AssertionError('Hot-path file access')):
        admitted=limited.move(lc,replace(c,version=2,x=150))
    assert admitted.presence.location.x==150 and limited.visible_ids(1)==(3,)
    d=limited.join(replace(c,role_id=4,x=800),replace(vc,role_id=4,x=800))
    refused(lambda: limited.join(replace(c,role_id=5,x=900),replace(vc,role_id=5,x=900)))
    assert limited.snapshot(5) is None and limited.snapshot(4)==d.presence
    report=dict(passed=[
        'real reciprocal RoleBasic entry; exact circular radius edge; no own echo',
        'move visibility exit/entry updates both viewers; remaining peer gets original SRoleMove',
        'leave/retry, relogin key reuse and recreated owner reject stale callbacks/deliveries',
        'same-epoch scene reentry rejects old recipient deliveries; movement and join retry preserve membership',
        'same map template with different instance remains isolated',
        'role/pair capacity failures leave snapshots, buckets and links unchanged',
        'explicit immutable metadata and newer authoritative location required; no hot-path I/O'],
        policy='caller-supplied circle radius/capacities/batching; not original server AOI values',
        original_SRoleStop_emitted=False,queueing_or_shared_runtime_tested=False,
        native_GUI_verified=False,client_launched=False,live_server_changed=False)
    write_json(OUT/'evidence/world-role-scene-verification.json',report)
    print(report)


if __name__=='__main__':main()
