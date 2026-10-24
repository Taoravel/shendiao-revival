"""Faction carriage goes through the durable map handoff and exact send barrier."""
import asyncio
from pathlib import Path
import struct
import tempfile
from accounts import AccountStore
from game_runtime import GameRuntime
from task_dialog_protocol import decode_visit_npc
from world_entity_protocol import VISIT_NPC,NPC_SERVICE
from verify_runtime import Peer
from inspect_client import OUT,write_json
import runtime_storage


async def check(store,prepared,role,npc):
    rt=GameRuntime(store,prepared)
    try:
        p=Peer(rt);await p.login(role)
        key=(npc.map_id<<32)|npc.placement_id
        menu=await p.request(VISIT_NPC,struct.pack('>q',key))
        assert 216 in decode_visit_npc(menu[-1][1])[1]
        assert await p.request(NPC_SERVICE,struct.pack('>qi',key,217))==[]
        assert rt.roles[role['id']].position.value[0]==1100
        result=await p.request(NPC_SERVICE,struct.pack('>qi',key,216))
        assert result[0][0]==0xc0fa9
        owner=rt.roles[role['id']]
        assert owner.position.value==(1007,5402,3142) and owner.transfer is None
        assert role['id'] not in rt.map(1100).positions
        await p.connection.close()
    finally: await rt.close()
    rt=GameRuntime(store,prepared)
    try:
        p=Peer(rt);await p.login(role)
        assert rt.roles[role['id']].position.value==(1007,5402,3142)
    finally: await rt.close()
    return {'passed':['faction carriage original service216 label','unbound service217 refused',
        'native service -> reserve/freeze/activate -> durable target -> scene send barrier',
        'source membership removed; target active','new runtime reloads target position'],
        'destination_and_free_fare':'designed from original target NPC placement',
        'explicit_source_checkpoint_fixture':True,
        'native_gui_verified':False,'live_database_modified':False}


def main():
    with tempfile.TemporaryDirectory() as temp:
        store=AccountStore(Path(temp)/'transport.sqlite3');role=store.create_role(1111,'车夫测试',11,1010109)
        prepared=runtime_storage.prepare(store)
        npc=next(p for ps in store.npc_resources[0].values() for p in ps if p.npc_id==10260)
        # Trusted isolated fixture: persist both position and version. A lone
        # legacy position row is corruption under the current transfer contract.
        epoch=store.acquire_lease(1111,role['id'])
        assert store.save_checkpoint(1111,role['id'],epoch,(npc.map_id,npc.x,npc.y),1)
        report=asyncio.run(check(store,prepared,role,npc))
    write_json(OUT/'evidence/npc-transport-runtime.json',report);print(report)


if __name__=='__main__':main()
