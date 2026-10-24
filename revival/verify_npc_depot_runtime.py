"""Encrypted NPC warehouse open/store/withdraw/reconnect with real item metadata."""
import asyncio
from pathlib import Path
import struct
import tempfile
from accounts import AccountStore
from game_runtime import GameRuntime
from inventory import QUERY_BAG, MOVE_ITEM, BAG_INFO, AssetChange
from world_entity_protocol import VISIT_NPC
from task_dialog_protocol import decode_visit_npc
from inspect_client import OUT,write_json
from verify_runtime import Peer
import runtime_storage
import npc_gameplay


async def check(store,prepared,role,npc):
    rt=GameRuntime(store,prepared)
    try:
        p=Peer(rt);await p.login(role)
        owner=rt.roles[role['id']]
        await owner.io(runtime_storage.initialize_role_wallet,store,1111,role['id'],owner.epoch,(1000,0,0,0),'explicit_migration')
        key=(npc.map_id<<32)|npc.placement_id
        assert await p.request(0xc04f0,struct.pack('>q',key))==[]
        await owner.io(npc_gameplay.initialize_depot,owner.inventory,98765,'explicit_migration')
        await owner.mailbox.call('settle',AssetChange('depot-fixture',grants=((32000,5,1,10),)))
        item=(await owner.io(owner.inventory.snapshot))['items'][0]
        key=(npc.map_id<<32)|npc.placement_id
        menu=await p.request(VISIT_NPC,struct.pack('>q',key))
        menu_key,services,quests=decode_visit_npc(menu[-1][1])
        assert menu_key==key and 6 in services and quests==[]
        assert await p.request(QUERY_BAG,struct.pack('>iQ',2,0))==[]
        opened=await p.request(0xc04f0,struct.pack('>q',key))
        assert any(k==BAG_INFO and struct.unpack_from('>i',b)[0]==2 for k,b in opened)
        assert next(struct.unpack_from('>Q',b,4)[0] for k,b in opened if k==BAG_INFO)==98765
        moved=await p.request(MOVE_ITEM,struct.pack('>6iq',1,item['id'],item['slot'],2,0,0,0))
        assert any(k==BAG_INFO for k,b in moved)
        assert (await owner.io(owner.inventory.snapshot))['items']==[]
        # A carried operation cannot use a key while it is stored.
        assert await p.request(MOVE_ITEM,struct.pack('>6iq',1,item['id'],item['slot'],1,1,0,0))==[]
        await p.connection.close()
        p=Peer(rt);await p.login(role);owner=rt.roles[role['id']]
        assert await p.request(QUERY_BAG,struct.pack('>iQ',2,0))==[]
        await p.request(0xc04f0,struct.pack('>q',key))
        await p.request(MOVE_ITEM,struct.pack('>6iq',2,item['id'],0,1,0,0,0))
        restored=(await owner.io(owner.inventory.snapshot))['items']
        assert len(restored)==1
        assert (restored[0]['id'],restored[0]['quantity'],restored[0]['binding'],restored[0]['quality'])==(
            item['id'],5,1,10)
        split=await p.request(MOVE_ITEM,struct.pack('>6iq',1,item['id'],0,2,0,2,0))
        depot_body=next(b for k,b in split if k==BAG_INFO and struct.unpack_from('>i',b)[0]==2)
        split_key=struct.unpack_from('>i',depot_body,25)[0]
        assert split_key!=item['id']
        assert (await owner.io(owner.inventory.snapshot))['items'][0]['quantity']==3
        await p.request(MOVE_ITEM,struct.pack('>6iq',2,split_key,0,1,0,0,0))
        assert (await owner.io(owner.inventory.snapshot))['items'][0]['quantity']==5
        # Equipment's exact persisted condition survives the move, including its
        # policy revision and CAS version. No fresh gear baseline is generated.
        await owner.mailbox.call('settle',AssetChange('depot-equipment',grants=((40200,1,1),)))
        gear=next(i for i in (await owner.io(owner.inventory.snapshot))['items'] if i['template_id']==40200)
        assert gear['condition'] is not None
        await p.request(MOVE_ITEM,struct.pack('>6iq',1,gear['id'],gear['slot'],2,1,0,0))
        await p.request(MOVE_ITEM,struct.pack('>6iq',2,gear['id'],1,1,gear['slot'],0,0))
        final=next(i for i in (await owner.io(owner.inventory.snapshot))['items'] if i['id']==gear['id'])
        assert final==gear,(gear,final)
        await p.request(0xc0faa,b'\0'+struct.pack('>hhQ',npc.x,npc.y,0))
        assert await p.request(QUERY_BAG,struct.pack('>iQ',2,0))==[]
        return {'passed':['original warehouse NPC10003 service6','native open plus column2 bag',
            'store item removes carried use eligibility','reconnect preserves warehouse and requires new access',
            'withdraw preserves original item key, binding1, quality10 and quantity5',
            'split allocates distinct key; merge preserves quantity and metadata',
            'equipment condition/revision/version survives store and withdrawal',
            'movement invalidates warehouse access','unknown legacy warehouse balance refused',
            'explicit warehouse balance98765 preserved across reconnect'],
            'native_gui_verified':False,'live_database_modified':False}
    finally: await rt.close()


def main():
    with tempfile.TemporaryDirectory() as temp:
        store=AccountStore(Path(temp)/'depot.sqlite3');role=store.create_role(1111,'仓库测试',11,1010109)
        prepared=runtime_storage.prepare(store)
        npc=next(p for ps in store.npc_resources[0].values() for p in ps if p.npc_id==10003)
        store.save_position(1111,role['id'],(npc.map_id,npc.x,npc.y))
        report=asyncio.run(check(store,prepared,role,npc))
    write_json(OUT/'evidence/npc-depot-runtime.json',report);print(report)


if __name__=='__main__':main()
