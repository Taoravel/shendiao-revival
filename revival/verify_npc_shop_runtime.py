"""Native NPC merchant -> atomic purchase -> current wallet/bag -> reconnect."""
import asyncio
from pathlib import Path
import struct
import tempfile
from accounts import AccountStore
from game_runtime import GameRuntime
from inspect_client import OUT, write_json
import runtime_storage
from task_dialog_protocol import decode_visit_npc
from verify_runtime import Peer
from world_entity_protocol import VISIT_NPC
from inventory import QUERY_BAG, BAG_INFO,AssetChange


async def check(store, prepared, role, npc):
    rt = GameRuntime(store, prepared)
    try:
        peer = Peer(rt)
        await peer.login(role)
        owner = rt.roles[role['id']]
        await owner.io(runtime_storage.initialize_role_wallet, store, 1111, role['id'], owner.epoch,
                       (1000,0,0,0), 'explicit_migration')
        key = (npc.map_id << 32) | npc.placement_id
        menu = await peer.request(VISIT_NPC, struct.pack('>q',key))
        assert decode_visit_npc(menu[-1][1]) == (key,[2,3],[])
        purchase = struct.pack('>qiii',key,32000,2,0)
        result = await peer.request(0xc232c,purchase)
        assert any(kind==BAG_INFO for kind,body in result)
        wallet = await owner.io(runtime_storage.wallet_snapshot, store,1111,role['id'],owner.epoch)
        assert next(r.balance for r in wallet if r.currency=='cash') == 700
        items = (await owner.io(owner.inventory.snapshot))['items']
        assert [(i['template_id'],i['quantity']) for i in items] == [(32000,2)]
        before = await owner.io(owner.inventory.snapshot)
        # Another merchant's item, negative count and unsupported shop mode fail closed.
        for body in (struct.pack('>qiii',key,33006,1,0),struct.pack('>qiii',key,32000,-1,0),
                     struct.pack('>qiii',key,32000,1,2),struct.pack('>qiii',key,32000,99,0)):
            assert await peer.request(0xc232c,body) == []
        assert await owner.io(owner.inventory.snapshot) == before
        one=struct.pack('>qiii',key,32000,1,0)
        await owner.mailbox.call('receive',0xc232c,one,request_id='same-shop-command')
        after_once=await owner.io(owner.inventory.snapshot)
        await owner.mailbox.call('receive',0xc232c,one,request_id='same-shop-command')
        assert await owner.io(owner.inventory.snapshot)==after_once
        try:
            await owner.mailbox.call('receive',0xc232c,purchase,request_id='same-shop-command')
        except ValueError: pass
        else: raise AssertionError('Purchase retry intent conflict accepted')
        wallet=await owner.io(runtime_storage.wallet_snapshot,store,1111,role['id'],owner.epoch)
        assert next(r.balance for r in wallet if r.currency=='cash')==550
        # Fill every carried slot and the merchant item's existing stack. The
        # next affordable purchase reaches the real grant failure after payment;
        # the caller transaction must roll payment and receipt back together.
        await owner.mailbox.call('settle',AssetChange('shop-full-bag',grants=((32000,996),(40200,39))))
        full=await owner.io(owner.inventory.snapshot)
        assert await peer.request(0xc232c,one)==[]
        assert await owner.io(owner.inventory.snapshot)==full
        wallet=await owner.io(runtime_storage.wallet_snapshot,store,1111,role['id'],owner.epoch)
        assert next(r.balance for r in wallet if r.currency=='cash')==550
        await peer.connection.close()
        peer = Peer(rt)
        await peer.login(role)
        bag = await peer.request(QUERY_BAG,struct.pack('>iQ',1,0))
        assert bag[0][0] == BAG_INFO and struct.unpack_from('>Q',bag[0][1],4)[0] == 550
        return {'passed':['original NPC10157 service2 menu','native purchase item32000 x2 at150 each',
            'cash1000->700 plus bag atomic','foreign stock/count/mode/insufficient funds refused',
            'same accepted command charged once; conflicting retry refused',
            'real bag-full failure after payment rolls back cash and assets',
            'reconnect current balance550 and persisted items'], 'native_gui_verified':False,
            'live_database_modified':False}
    finally:
        await rt.close()


def main():
    with tempfile.TemporaryDirectory() as temp:
        store=AccountStore(Path(temp)/'shop.sqlite3')
        role=store.create_role(1111,'商店测试',11,1010109)
        prepared=runtime_storage.prepare(store)
        npc=next(p for ps in store.npc_resources[0].values() for p in ps if p.npc_id==10157)
        store.save_position(1111,role['id'],(npc.map_id,npc.x,npc.y))
        result=asyncio.run(check(store,prepared,role,npc))
    write_json(OUT/'evidence/npc-shop-runtime.json',result)
    print(result)


if __name__=='__main__': main()
