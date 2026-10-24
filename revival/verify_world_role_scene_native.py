"""Decode the actual AOI entry/removal batches with the original client codec."""
from dataclasses import replace
import struct
from inspect_client import OUT,write_json
from world_owner import MapAddress,Location
from world_role_protocol import RoleBasic,S_ADD_USER_SCREEN,S_REMOVE_USER_SCREEN
from world_roles import RoleScene
from verify_world_entities_native import probe


def main():
    address=MapAddress(7,1,0)
    catalog={7:dict(available=True,width=1024,height=1024,portals={})}
    scene=RoleScene(address,catalog,radius=64,role_capacity=5,pair_capacity=10,batch_size=2)
    for role_id in range(1,6):
        location=Location(role_id,f'epoch-{role_id}',address,1,100+role_id*8,100)
        changed=scene.join(location,RoleBasic(role_id,f'侠客{role_id}',9,location.x,100,0x71))
    entry=next(d for d in changed.deliveries if d.recipient_role_id==5)
    exit_change=scene.move(changed.presence,replace(location,version=2,x=900,y=900))
    exit=next(d for d in exit_change.deliveries if d.recipient_role_id==5)
    results=[]
    for label,delivery,kind,ctor,mar,decoder in (
        ('entry',entry,S_ADD_USER_SCREEN,0xfc5f40,0xfc68f0,0xfc69a0),
        ('exit',exit,S_REMOVE_USER_SCREEN,0xe6e9e0,0xe6ea90,0xe6eb20)):
        assert len(delivery.packets)==2
        for actual,body in delivery.packets:
            assert actual==kind
            _,raw=probe(ctor,mar,decoder,payload=body)
            assert struct.unpack_from('<I',raw,0x10)[0]==2
            assert struct.unpack_from('<I',raw,0x1c)[0]==0
            results.append(dict(case=label,role_count=2,npc_count=0,bytes=len(body)))
    write_json(OUT/'evidence/world-role-scene-native.json',dict(cases=results,
        source='actual RoleScene logical deliveries, original full outer decoder consumed payload',
        native_inner_metadata_coverage='WORLD_ROLE_PROTOCOL separate13cases',
        shared_runtime_tested=False,gui_verified=False,live_server_changed=False))
    print(results)


if __name__=='__main__':main()
