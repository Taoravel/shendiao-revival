"""Actual encrypted Peer query495 route; no live listener, GUI or settlement."""
import asyncio
from pathlib import Path
import struct
import tempfile
from accounts import AccountStore
from game_runtime import GameRuntime
from inventory import Inventory
from inspect_client import OUT,write_json
from npc_identification_protocol import QUERY_IDENTIFICATION,IDENTIFICATION_STATES
from task_dialog_protocol import decode_visit_npc
from verify_runtime import Peer
from world_entity_protocol import VISIT_NPC,VISIT_NPC_REPLY
import runtime_storage


async def check(store,prepared,role,npc,item_key):
    runtime=GameRuntime(store,prepared)
    try:
        peer=Peer(runtime);await peer.login(role)
        owner=runtime.roles[role['id']];key=(npc.map_id<<32)|npc.placement_id
        menu=await peer.request(VISIT_NPC,struct.pack('>q',key))
        assert any(kind==VISIT_NPC_REPLY for kind,body in menu), 'Original identification NPC visit returned no menu'
        services=next(decode_visit_npc(body)[1] for kind,body in menu if kind==VISIT_NPC_REPLY)
        assert 495 in services, 'Original identification NPC menu does not expose approved local service495'
        before=await owner.io(owner.inventory.immutable_snapshot)
        body=b'\2'+struct.pack('>2iQi',item_key,item_key,key,1)
        # Original local495 sends this directly; no CNpcService495 is sent.
        replies=await peer.request(QUERY_IDENTIFICATION,body)
        expected=struct.pack('>Q',key)+b'\2'+struct.pack('>5i',item_key,1,item_key,1,1)
        assert replies==[(IDENTIFICATION_STATES,expected)], 'Actual original identification query was not routed to current read-only state'
        assert await owner.io(owner.inventory.immutable_snapshot)==before
        assert getattr(store,'npc_identification_query_rules',None) is not None
        return {'passed':['actual original NPC visit exposes approved local495',
            'actual encrypted c04cc directly returns ordered duplicate current-state c04cd without CNpcService495',
            'actual current inventory is unchanged; shared startup rules exist'],
            'late_scene_reply_fences_verified':False,'native_gui_verified':False,
            'live_database_modified':False,'paid_identification_restored':False}
    finally:await runtime.close()


def main():
    with tempfile.TemporaryDirectory(prefix='npc-identification-query-runtime-') as directory:
        store=AccountStore(Path(directory)/'state.sqlite3')
        role=store.create_role(1111,'鉴定查询接线',12,1010101)
        prepared=runtime_storage.prepare(store)
        npc=next(p for p in store.npc_resources[0][1007] if p.placement_id==75 and p.npc_id==10890)
        epoch=store.acquire_lease(1111,role['id'])
        inventory=Inventory(store.leased(1111,role['id'],epoch),1111,role['id'])
        inventory.grant_item(40200)
        item_key=inventory.immutable_snapshot().items[0].id
        assert store.save_checkpoint(1111,role['id'],epoch,(npc.map_id,npc.x,npc.y),1)
        store.release_lease(role['id'],epoch)
        try:result=asyncio.run(asyncio.wait_for(check(store,prepared,role,npc,item_key),60))
        except AssertionError as error:
            write_json(OUT/'evidence/npc-identification-query-runtime-baseline.json',{
                'failure':str(error),'seam':'actual GameRuntime/Peer original local495 query route',
                'live_database_modified':False,'dispatcher_replaced':False})
            raise
    write_json(OUT/'evidence/npc-identification-query-runtime.json',result);print(result)


if __name__=='__main__':main()
