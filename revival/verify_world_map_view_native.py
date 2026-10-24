"""Original decode after coupled map commands and target view queue admission."""
import struct
from inspect_client import OUT,write_json
from world_owner import MapOwner,MapAddress,Location,MoveCommand
from world_roles import RoleScene
from world_role_protocol import RoleBasic,S_ADD_USER_SCREEN,S_REMOVE_USER_SCREEN,S_ROLE_MOVE
from world_role_delivery import bind_role_view,route_role_delivery,RoleViewInbox
from verify_world_entities_native import probe


def main():
    catalog={mid:dict(available=True,width=1024,height=1024,portals={}) for mid in (7,8)}
    source=MapOwner(MapAddress(7,1,0),catalog,capacity=2,transfer_capacity=2,mailbox_capacity=2)
    target=MapOwner(MapAddress(8,2,1),catalog,capacity=2,transfer_capacity=2,mailbox_capacity=2)
    sv=RoleScene(source.address,catalog,radius=64,role_capacity=2,pair_capacity=1,batch_size=2)
    tv=RoleScene(target.address,catalog,radius=64,role_capacity=2,pair_capacity=1,batch_size=2)
    a=Location(1,'epoch-a',source.address,1,100,100)
    appearance=RoleBasic(1,'主角',9,100,100,0x71)
    source.join_with_view(a,appearance,sv)
    _,entry=source.join_with_view(Location(2,'epoch-b',source.address,1,120,100),
        RoleBasic(2,'源同伴',10,120,100,0x32),sv)
    _,peer=target.join_with_view(Location(3,'epoch-c',target.address,1,120,100),
        RoleBasic(3,'目标同伴',9,120,100,0x71),tv)
    source_binding=bind_role_view(entry.presence,17)
    target_binding=bind_role_view(peer.presence,18)
    source_inbox=RoleViewInbox(source_binding,message_capacity=2,byte_capacity=4096)
    target_inbox=RoleViewInbox(target_binding,message_capacity=3,byte_capacity=4096)
    def queue(change,recipient,inbox,binding):
        delivery=next(d for d in change.deliveries if d.recipient_role_id==recipient)
        assert inbox.offer(route_role_delivery(delivery,binding),current=binding)=='accepted'
    queue(entry,2,source_inbox,source_binding)
    offer=source.prepare_transfer(a,(8,100,100),request_id='native-view',deadline_ms=1000,now_ms=0)
    reservation=target.reserve(offer,0);frozen=source.freeze(reservation,0);receipt=target.activate(frozen,0)
    _,removed=source.finalize_with_view(receipt,sv)
    queue(removed,2,source_inbox,source_binding)
    active,added=target.ready_with_view(receipt.location,appearance,tv)
    queue(added,3,target_inbox,target_binding)
    movement,moved=target.move_with_view(MoveCommand(active,'native-target-move',1000,0xc0faa,
        b'\0'+struct.pack('>hhQ',110,100,0)),1,tv)
    queue(moved,3,target_inbox,target_binding)
    _,departed=target.leave_with_view(movement.location,tv)
    queue(departed,3,target_inbox,target_binding)
    codecs={S_ADD_USER_SCREEN:(0xfc5f40,0xfc68f0,0xfc69a0),
            S_REMOVE_USER_SCREEN:(0xe6e9e0,0xe6ea90,0xe6eb20),
            S_ROLE_MOVE:(0xdacd10,0xe50d90,0xdacdc0)}
    rows=[]
    for label,inbox,binding,kinds in (
            ('source',source_inbox,source_binding,(S_ADD_USER_SCREEN,S_REMOVE_USER_SCREEN)),
            ('target',target_inbox,target_binding,(S_ADD_USER_SCREEN,S_ROLE_MOVE,S_REMOVE_USER_SCREEN))):
        for sequence,expected_kind in enumerate(kinds,1):
            delivery=inbox.pop(current=binding)
            assert delivery.sequence==sequence and len(delivery.packets)==1
            kind,body=delivery.packets[0];assert kind==expected_kind
            _,raw=probe(*codecs[kind],payload=body)
            if kind==S_ROLE_MOVE:
                assert struct.unpack_from('<q',raw,8)[0]==1
                assert struct.unpack_from('<hh',raw,0x14)==(110,100)
            else:
                assert struct.unpack_from('<I',raw,0x10)[0]==1
                assert struct.unpack_from('<I',raw,0x1c)[0]==0
            rows.append(dict(view=label,sequence=sequence,kind=kind,bytes=len(body)))
        assert inbox.pop(current=binding) is None and inbox.pending==(0,0)
    report=dict(cases=rows,scope='coupled map/view commands -> captured route -> inbox -> original decoder',
        durable_commit_tested=False,shared_runtime_integrated=False,gui_verified=False,live_server_changed=False)
    write_json(OUT/'evidence/world-map-view-native.json',report)
    print(report)


if __name__=='__main__':main()
