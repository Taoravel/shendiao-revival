"""Decode packets after actual map projection and target inbox consumption."""
from dataclasses import replace
import struct
from inspect_client import OUT,write_json
from verify_world_role_delivery import fixture
from world_role_delivery import bind_role_view,route_role_delivery,RoleViewInbox
from world_role_protocol import S_ADD_USER_SCREEN,S_REMOVE_USER_SCREEN,S_ROLE_MOVE
from verify_world_entities_native import probe


def main():
    scene,pa,pb,entry=fixture()
    moved=scene.move(pb,replace(pb.location,version=2,x=124))
    movement=next(d for d in moved.deliveries if d.recipient_role_id==1)
    left=scene.leave(moved.presence)
    removal=next(d for d in left.deliveries if d.recipient_role_id==1)
    binding=bind_role_view(pa,11)
    inbox=RoleViewInbox(binding,message_capacity=3,byte_capacity=4096)
    for delivery in (entry,movement,removal):
        assert inbox.offer(route_role_delivery(delivery,binding),current=binding)=='accepted'
    cases=[]
    layouts={S_ADD_USER_SCREEN:(0xfc5f40,0xfc68f0,0xfc69a0),
             S_ROLE_MOVE:(0xdacd10,0xe50d90,0xdacdc0),
             S_REMOVE_USER_SCREEN:(0xe6e9e0,0xe6ea90,0xe6eb20)}
    for expected in (entry,movement,removal):
        received=inbox.pop(current=binding)
        assert received==expected
        for kind,body in received.packets:
            _,raw=probe(*layouts[kind],payload=body)
            if kind==S_ROLE_MOVE:
                assert struct.unpack_from('<q',raw,8)[0]==2
                assert struct.unpack_from('<hh',raw,0x14)==(124,100)
            else:
                assert struct.unpack_from('<I',raw,0x10)[0]==1
                assert struct.unpack_from('<I',raw,0x1c)[0]==0
            cases.append(dict(sequence=received.sequence,kind=kind,bytes=len(body)))
    assert inbox.pop(current=binding) is None and inbox.pending==(0,0)
    report=dict(cases=cases,source='actual RoleScene -> captured route -> target inbox -> original decoder',
        shared_runtime_tested=False,gui_verified=False,live_server_changed=False)
    write_json(OUT/'evidence/world-role-delivery-native.json',report)
    print(report)


if __name__=='__main__':main()
