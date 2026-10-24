"""Public map-output to target-connection inbox seam; no live server or GUI."""
from dataclasses import replace
from unittest.mock import patch
from inspect_client import OUT,write_json
from world_owner import MapAddress,Location
from world_role_protocol import RoleBasic
from world_roles import RoleScene
from world_role_delivery import bind_role_view,route_role_delivery,RoleViewInbox


def refused(action):
    try: action()
    except ValueError: return
    raise AssertionError('Invalid player view binding accepted')


def fixture():
    address=MapAddress(7,1,0)
    catalog={7:dict(available=True,width=1024,height=1024,portals={})}
    scene=RoleScene(address,catalog,radius=64,role_capacity=4,pair_capacity=6,batch_size=2)
    a=Location(1,'epoch-a',address,1,100,100)
    b=Location(2,'epoch-b',address,1,120,100)
    pa=scene.join(a,RoleBasic(1,'甲侠',9,100,100,0x71)).presence
    joined=scene.join(b,RoleBasic(2,'乙侠',10,120,100,0x32))
    entry=next(d for d in joined.deliveries if d.recipient_role_id==1)
    return scene,pa,joined.presence,entry


def main():
    scene,pa,pb,entry=fixture()
    binding=bind_role_view(pa,11)
    inbox=RoleViewInbox(binding,message_capacity=4,byte_capacity=4096)
    routed=route_role_delivery(entry,binding)
    assert inbox.offer(routed,current=binding)=='accepted'
    assert inbox.pop(current=binding)==entry
    assert inbox.pop(current=binding) is None
    # Replacing the socket must reject an envelope captured for its predecessor.
    new_connection=replace(binding,connection_generation=12)
    successor=RoleViewInbox(new_connection,message_capacity=4,byte_capacity=4096)
    assert successor.offer(routed,current=new_connection)=='stale'
    assert successor.pop(current=new_connection) is None and not successor.failure
    assert successor.offer(route_role_delivery(entry,new_connection),current=new_connection)=='accepted'
    # Recheck the trusted current binding at consumption, too. A closed old
    # inbox cannot be revived by later supplying its previous binding.
    assert successor.pop(current=binding) is None
    assert successor.failure=='binding_changed'
    assert successor.offer(route_role_delivery(entry,new_connection),current=new_connection)=='resync_required'
    # Same login, same scene, same socket; only the membership has changed.
    scene.leave(pa)
    returned=scene.join(replace(pa.location,version=8),pa.appearance)
    back=bind_role_view(returned.presence,11)
    returning=RoleViewInbox(back,message_capacity=4,byte_capacity=4096)
    assert returning.offer(routed,current=back)=='stale'
    fresh=next(d for d in returned.deliveries if d.recipient_role_id==1)
    assert returning.offer(route_role_delivery(fresh,back),current=back)=='accepted'
    assert returning.pop(current=back)==fresh

    scene,pa,pb,entry=fixture()
    binding=bind_role_view(pa,11)
    moved=scene.move(pb,replace(pb.location,version=2,x=124))
    movement=next(d for d in moved.deliveries if d.recipient_role_id==1)
    later=scene.move(moved.presence,replace(moved.presence.location,version=3,x=128))
    third=next(d for d in later.deliveries if d.recipient_role_id==1)
    ordered=RoleViewInbox(binding,message_capacity=4,byte_capacity=4096)
    assert ordered.offer(route_role_delivery(entry,binding),current=binding)=='accepted'
    assert ordered.offer(route_role_delivery(entry,binding),current=binding)=='duplicate'
    assert ordered.offer(route_role_delivery(movement,binding),current=binding)=='accepted'
    assert ordered.pop(current=binding)==entry
    assert ordered.pop(current=binding)==movement
    assert ordered.offer(route_role_delivery(entry,binding),current=binding)=='duplicate'
    assert ordered.pop(current=binding) is None
    gap=RoleViewInbox(binding,message_capacity=4,byte_capacity=4096)
    assert gap.offer(route_role_delivery(entry,binding),current=binding)=='accepted'
    assert gap.offer(route_role_delivery(third,binding),current=binding)=='resync_required'
    assert gap.failure=='sequence_gap' and gap.pop(current=binding) is None
    assert gap.offer(route_role_delivery(movement,binding),current=binding)=='resync_required'
    full=RoleViewInbox(binding,message_capacity=1,byte_capacity=4096)
    assert full.offer(route_role_delivery(entry,binding),current=binding)=='accepted'
    assert full.offer(route_role_delivery(movement,binding),current=binding)=='resync_required'
    assert full.failure=='backpressure' and full.pending==(0,0)
    assert full.pop(current=binding) is None
    entry_bytes=sum(len(body)+10 for kind,body in entry.packets)
    exact=RoleViewInbox(binding,message_capacity=4,byte_capacity=entry_bytes)
    assert exact.offer(route_role_delivery(entry,binding),current=binding)=='accepted'
    assert exact.pending==(1,entry_bytes)
    assert exact.pop(current=binding)==entry and exact.pending==(0,0)
    small=RoleViewInbox(binding,message_capacity=4,byte_capacity=entry_bytes-1)
    assert small.offer(route_role_delivery(entry,binding),current=binding)=='resync_required'
    assert small.failure=='backpressure' and small.pop(current=binding) is None
    # One actual map change contains two native entry batches. Never accept a
    # partial batch because its first packet happened to fit the queue.
    crowded=RoleScene(pa.location.address,scene.catalog,radius=64,role_capacity=5,pair_capacity=10,batch_size=2)
    for role_id in range(10,15):
        loc=replace(pa.location,role_id=role_id,login_epoch=f'epoch-{role_id}',x=100+role_id)
        change=crowded.join(loc,RoleBasic(role_id,f'侠客{role_id}',9,loc.x,loc.y,0x71))
    batch=next(d for d in change.deliveries if d.recipient_role_id==14)
    assert len(batch.packets)==2
    crowded_binding=bind_role_view(change.presence,14)
    atomic=RoleViewInbox(crowded_binding,message_capacity=1,byte_capacity=4096)
    assert atomic.offer(route_role_delivery(batch,crowded_binding),current=crowded_binding)=='resync_required'
    assert atomic.pending==(0,0) and atomic.pop(current=crowded_binding) is None
    assert ordered.offer(route_role_delivery(third,binding),current=binding)=='accepted'
    assert ordered.pop(current=binding)==third  # Another target failure is local.
    closed=RoleViewInbox(binding,message_capacity=4,byte_capacity=4096)
    assert closed.offer(route_role_delivery(entry,binding),current=binding)=='accepted'
    closed.close()
    closed.close()
    assert closed.failure=='closed' and closed.pending==(0,0)
    assert closed.pop(current=binding) is None
    assert closed.offer(route_role_delivery(movement,binding),current=binding)=='resync_required'
    full.close()
    assert full.failure=='backpressure'  # Preserve the first failure for diagnosis.
    refused(lambda: bind_role_view(replace(pa,location=replace(pa.location,state='loading')),11))
    refused(lambda: route_role_delivery(entry,replace(binding,role_id=99)))
    for invalid,reason in (
            (replace(entry,sequence=True),'invalid_sequence'),
            (replace(entry,packets=((entry.packets[0][0],bytearray(entry.packets[0][1])),)),'malformed_packets'),
            (replace(entry,packets=((0x12345,b''),)),'malformed_packets')):
        defensive=RoleViewInbox(binding,message_capacity=4,byte_capacity=4096)
        assert defensive.offer(route_role_delivery(invalid,binding),current=binding)=='resync_required'
        assert defensive.failure==reason and defensive.pop(current=binding) is None
    without_io=RoleViewInbox(binding,message_capacity=4,byte_capacity=4096)
    with patch('builtins.open',side_effect=AssertionError('View hot-path file access')), \
         patch('io.open',side_effect=AssertionError('View hot-path file access')):
        assert without_io.offer(route_role_delivery(entry,binding),current=binding)=='accepted'
        assert without_io.pop(current=binding)==entry
    report=dict(passed=['actual reciprocal player entry reaches its bound target once',
                       'captured connection generation and same-epoch membership isolate stale envelopes',
                       'binding is rechecked before consumption; obsolete inbox cannot reopen',
                       'actual entry/movement retain sequence order, retries do not duplicate effects',
                       'sequence gap invalidates queued view; late missing message cannot revive it',
                       'packet/byte limits are atomic, exact fit accepted and freed on consumption',
                       'one slow target fails locally; another inbox continues',
                       'connection close discards pending view and permanently ends the inbox',
                       'loading membership, malformed sequence/packets and foreign routing rejected; no hot-path I/O'],
                shared_runtime_tested=False,gui_verified=False,live_server_changed=False)
    write_json(OUT/'evidence/world-role-delivery-verification.json',report)
    print(report)


if __name__=='__main__':main()
