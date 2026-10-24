"""Original repair request reaches real fee/condition transaction and reconnect."""
import asyncio
from contextlib import closing
from pathlib import Path
import struct
import tempfile
from accounts import AccountStore
from game_runtime import GameRuntime
from inventory import AssetChange
from world_entity_protocol import VISIT_NPC
from task_dialog_protocol import decode_visit_npc
from equipment_protocol import REFRESH_ENDURE,REFRESH_MAX_ENDURE
from verify_runtime import Peer
from inspect_client import OUT,write_json
import runtime_storage


def damage(inventory,key):
    with closing(inventory.accounts.connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        inventory.wear_equipment(db,key,'repair-fixture',0,20)


async def check(store,prepared,role,npc):
    rt=GameRuntime(store,prepared)
    try:
        peer=Peer(rt);await peer.login(role);owner=rt.roles[role['id']]
        await owner.io(runtime_storage.initialize_role_wallet,store,1111,role['id'],owner.epoch,(1000,0,0,0),'explicit_migration')
        await owner.mailbox.call('settle',AssetChange('repair-gear',grants=((40200,1,1),)))
        gear=(await owner.io(owner.inventory.snapshot))['items'][0]
        await owner.io(damage,owner.inventory,gear['id'])
        key=(npc.map_id<<32)|npc.placement_id
        menu=await peer.request(VISIT_NPC,struct.pack('>q',key))
        assert 513 in decode_visit_npc(menu[-1][1])[1]
        request=struct.pack('>iqii',2,key,1,gear['id'])
        messages=await owner.mailbox.call('receive',0xc0413,request,request_id='one-repair-command')
        assert {REFRESH_ENDURE,REFRESH_MAX_ENDURE}<={k for k,b in messages}
        repaired=(await owner.io(owner.inventory.snapshot))['items'][0]
        state=repaired['condition']
        assert (state.current,state.maximum) in ((100,100),(80,90)) and state.version==2
        wallet=await owner.io(runtime_storage.wallet_snapshot,store,1111,role['id'],owner.epoch)
        assert next(r.balance for r in wallet if r.currency=='cash')==960
        await owner.mailbox.call('receive',0xc0413,request,request_id='one-repair-command')
        assert (await owner.io(owner.inventory.snapshot))['items'][0]==repaired
        # Raw client method1 is family repair, not ordinary method2.
        assert await peer.request(0xc0413,struct.pack('>iqii',1,key,1,gear['id']))==[]
        assert await peer.request(0xc0413,struct.pack('>iqii',2,key,4,gear['id']))==[]
        await peer.connection.close();peer=Peer(rt);await peer.login(role)
        owner=rt.roles[role['id']]
        assert (await owner.io(owner.inventory.snapshot))['items'][0]==repaired
        wallet=await owner.io(runtime_storage.wallet_snapshot,store,1111,role['id'],owner.epoch)
        assert next(r.balance for r in wallet if r.currency=='cash')==960
        return {'passed':['weapon-shop NPC10004 ordinary service513','native method2/column1/item key',
            'cash1000->960 matches original level1 cost2 x20','actual success or failure condition persisted',
            'same accepted command does not resample or charge again','family method and wrong column rejected',
            'reconnect restores condition and current cash960'],'native_gui_verified':False,'live_database_modified':False}
    finally:await rt.close()


def main():
    with tempfile.TemporaryDirectory() as temp:
        store=AccountStore(Path(temp)/'repair.sqlite3');role=store.create_role(1111,'修理测试',11,1010109)
        prepared=runtime_storage.prepare(store)
        npc=next(p for ps in store.npc_resources[0].values() for p in ps if p.npc_id==10004)
        store.save_position(1111,role['id'],(npc.map_id,npc.x,npc.y))
        report=asyncio.run(check(store,prepared,role,npc))
    write_json(OUT/'evidence/npc-repair-runtime.json',report);print(report)


if __name__=='__main__':main()
