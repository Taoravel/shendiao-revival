"""Single actual NPC repair owner with an explicitly known resource profile."""
import asyncio
from functools import partial
from pathlib import Path
import struct
import tempfile
from accounts import AccountStore
from game_runtime import GameRuntime
from inspect_client import OUT,write_json
from verify_resource_owner_runtime import fixture
from verify_resource_npc_care_runtime import state,change_fixture,complete_map
from verify_runtime import Peer
import runtime_storage


async def check(store,prepared,role,npc,weapon):
    runtime=GameRuntime(store,prepared)
    try:
        peer=Peer(runtime);await peer.login(role);owner=runtime.roles[role['id']]
        await owner.io(partial(change_fixture,wear=weapon),store,owner.inventory,'repair-actual-owner-wear')
        before=await owner.io(state,store,owner)
        body=struct.pack('>iqii',2,(npc.map_id<<32)|npc.placement_id,4,weapon)
        # The real mailbox lets a refused encrypted request's exact cause reach
        # this feedback loop; there is no replacement dispatcher or fake reply.
        messages=await owner.mailbox.call('receive',0xc0413,body,request_id='repair-known-profile-once')
        complete_map(messages)
        after=await owner.io(state,store,owner)
        assert before[2]-after[2]==20
        assert (after[1].hp,after[1].mp,after[1].version)==(10,20,before[1].version)
        assert after[0].items[0].condition.version==before[0].items[0].condition.version+1
        current=await owner.io(state,store,owner)
        complete_map(await owner.mailbox.call('receive',0xc0413,body,request_id='repair-known-profile-once'))
        assert await owner.io(state,store,owner)==current
        return {'passed':['actual NPC method2 repairs known-profile worn equipment and charges20',
            'current10/20 and resource version preserved; current source and complete map',
            'paid same command is current-only without another charge'],
            'native_gui_verified':False,'live_database_modified':False,'battle_executed':False}
    finally:await runtime.close()


def main():
    with tempfile.TemporaryDirectory(prefix='npc-repair-known-owner-') as directory:
        store=AccountStore(Path(directory)/'state.sqlite3')
        role=store.create_role(1111,'修理资源门控',11,1010109);prepared=runtime_storage.prepare(store)
        npc=next(p for rows in store.npc_resources[0].values() for p in rows if p.npc_id==10004)
        weapon,_=fixture(store,role,npc)
        try:report=asyncio.run(asyncio.wait_for(check(store,prepared,role,npc,weapon),60))
        except (ValueError,AssertionError) as error:
            write_json(OUT/'evidence/npc-repair-resource-runtime-baseline.json',{
                'failure':str(error),'seam':'actual RoleOwner receive0xc0413 -> repair_role_equipment',
                'fixture':'explicit known L21 resources/current source/worn49009',
                'live_database_modified':False,'dispatcher_replaced':False})
            raise
    write_json(OUT/'evidence/npc-repair-resource-runtime-verification.json',report)
    print('PASS actual known-profile NPC repair owner and paid current-only')


if __name__=='__main__':main()
