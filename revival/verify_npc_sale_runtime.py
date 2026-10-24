"""Native sale and buyback preserve wallet channels and real item metadata."""
import asyncio
from pathlib import Path
import struct
import tempfile
from dataclasses import replace
from accounts import AccountStore
from game_runtime import GameRuntime
from inventory import AssetChange
from world_entity_protocol import VISIT_NPC
from task_dialog_protocol import decode_visit_npc
from verify_runtime import Peer
from inspect_client import OUT,write_json
from wire import compact,read_compact
import runtime_storage


async def check(store,prepared,role,npc):
    rt=GameRuntime(store,prepared)
    try:
        p=Peer(rt);await p.login(role);owner=rt.roles[role['id']]
        await owner.io(runtime_storage.initialize_role_wallet,store,1111,role['id'],owner.epoch,(1000,0,0,0),'explicit_migration')
        await owner.mailbox.call('settle',AssetChange('sale-fixture',grants=((40200,1,1),)))
        item=(await owner.io(owner.inventory.snapshot))['items'][0]
        key=(npc.map_id<<32)|npc.placement_id
        menu=await p.request(VISIT_NPC,struct.pack('>q',key))
        assert 214 in decode_visit_npc(menu[-1][1])[1]
        body=struct.pack('>q',key)+compact(1)+struct.pack('>i',item['id'])
        sold=await owner.mailbox.call('receive',0xc232d,body,request_id='sale-once')
        assert any(k==0xc0434 for k,b in sold)
        from native_gameplay_probe import probe
        from native_inspect import u32
        listing=next(b for k,b in sold if k==0xc0434)
        decoded,_=probe(0xef64e0,u32(0x2284258),u32(0x228425c),payload=listing)
        assert decoded==listing
        assert (await owner.io(owner.inventory.snapshot))['items']==[]
        wallet=await owner.io(runtime_storage.wallet_snapshot,store,1111,role['id'],owner.epoch)
        assert {r.currency:r.balance for r in wallet}=={'cash':1000,'bound_silver':250,'yuanbao':0,'bound_yuanbao':0}
        await owner.mailbox.call('receive',0xc232d,body,request_id='sale-once')
        wallet=await owner.io(runtime_storage.wallet_snapshot,store,1111,role['id'],owner.epoch)
        assert next(r.balance for r in wallet if r.currency=='bound_silver')==250
        await p.connection.close();p=Peer(rt);await p.login(role);owner=rt.roles[role['id']]
        menu=await p.request(VISIT_NPC,struct.pack('>q',key))
        assert any(k==0xc0434 for k,b in menu)
        bought=await p.request(0xc232e,struct.pack('>qi',key,item['id']))
        assert any(k==0xc0434 for k,b in bought)
        restored=(await owner.io(owner.inventory.snapshot))['items'][0]
        assert restored==item
        wallet=await owner.io(runtime_storage.wallet_snapshot,store,1111,role['id'],owner.epoch)
        assert next(r.balance for r in wallet if r.currency=='cash')==750
        assert next(r.balance for r in wallet if r.currency=='bound_silver')==250
        assert await p.request(0xc232e,struct.pack('>qi',key,item['id']))==[]
        # Every item in a multi-sale is validated before any item is removed.
        before=await owner.io(owner.inventory.snapshot)
        assert await p.request(0xc232d,struct.pack('>q',key)+b'\2'+struct.pack('>ii',item['id'],2147483647))==[]
        assert await owner.io(owner.inventory.snapshot)==before
        await p.request(0xc232d,body)
        await owner.mailbox.call('settle',AssetChange('full-buyback-bag',grants=((40200,40),)))
        full=await owner.io(owner.inventory.snapshot)
        assert await p.request(0xc232e,struct.pack('>qi',key,item['id']))==[]
        assert await owner.io(owner.inventory.snapshot)==full
        wallet=await owner.io(runtime_storage.wallet_snapshot,store,1111,role['id'],owner.epoch)
        assert next(r.balance for r in wallet if r.currency=='cash')==750
        # Releasing a slot allows the same preserved cached item to be bought.
        await owner.mailbox.call('settle',AssetChange('free-buyback-slot',debits=((full['items'][0]['id'],1),)))
        await p.request(0xc232e,struct.pack('>qi',key,item['id']))
        assert any(i['id']==item['id'] for i in (await owner.io(owner.inventory.snapshot))['items'])
        carried=(await owner.io(owner.inventory.snapshot))['items']
        free=tuple((i['id'],1) for i in carried if i['id']!=item['id'])[:3]
        await owner.mailbox.call('settle',AssetChange('sale-channels',debits=free,
            grants=((40204,1,0),(40204,1,1),(32000,2))))
        selected=[i['id'] for i in (await owner.io(owner.inventory.snapshot))['items'] if i['template_id'] in (40204,32000)]
        mixed=await p.request(0xc232d,struct.pack('>q',key)+compact(3)+struct.pack('>3i',*selected))
        wallet=await owner.io(runtime_storage.wallet_snapshot,store,1111,role['id'],owner.epoch)
        assert next(r.balance for r in wallet if r.currency=='cash')==7500
        assert next(r.balance for r in wallet if r.currency=='bound_silver')==7650
        listing=next(b for k,b in mixed if k==0xc0434)
        assert probe(0xef64e0,u32(0x2284258),u32(0x228425c),payload=listing)[0]==listing
        carried=(await owner.io(owner.inventory.snapshot))['items']
        await owner.mailbox.call('settle',AssetChange('retention-fixture',
            debits=tuple((i['id'],i['quantity']) for i in carried),grants=((40200,21,1),)))
        keys=[i['id'] for i in (await owner.io(owner.inventory.snapshot))['items']]
        for offset in (0,10,20):
            batch=keys[offset:offset+10]
            retained=await p.request(0xc232d,struct.pack('>q',key)+compact(len(batch))+
                                    struct.pack('>'+'i'*len(batch),*batch))
        listing=next(b for k,b in retained if k==0xc0434)
        count,start=read_compact(listing,12)
        retained_keys=[struct.unpack_from('>i',listing,start+48*i+8)[0] for i in range(count)]
        assert count==20 and retained_keys==keys[1:]
        # Use an injected short test policy instead of changing the shared file
        # or forging persisted timestamps. Expiry is observable through wire.
        store.npc_sale_rules=replace(store.npc_sale_rules,ttl_seconds=1)
        await asyncio.sleep(1.1)
        assert await p.request(0xc232e,struct.pack('>qi',key,keys[-1]))==[]
        menu=await p.request(VISIT_NPC,struct.pack('>q',key))
        listing=next(b for k,b in menu if k==0xc0434)
        assert read_compact(listing,12)[0]==0
        return {'passed':['merchant10011 original service214','full native key vector sale',
            'original equipment coefficient250/current100/endure100 -> 250 bound silver',
            'same accepted sale does not credit again','buyback cache survives reconnect',
            'buyback debits native cash channel and restores exact key/condition/detail/binding',
            'already repurchased key rejected','mixed foreign-key sale leaves every item unchanged',
            'actual bag-full buyback rolls back payment and preserves cache; later retry succeeds',
            'production nonempty buyback response accepted by original decoder',
            'mixed unbound40 equipment cash7000, bound40 equipment bound7000 and explicit food bound150 settle together',
            '21 sold instances retain exactly20, and expired cache cannot be repurchased'],
            'native_gui_verified':False,'live_database_modified':False}
    finally: await rt.close()


def main():
    with tempfile.TemporaryDirectory() as temp:
        store=AccountStore(Path(temp)/'sale.sqlite3');role=store.create_role(1111,'出售测试',11,1010109)
        prepared=runtime_storage.prepare(store)
        npc=next(p for ps in store.npc_resources[0].values() for p in ps if p.npc_id==10011)
        store.save_position(1111,role['id'],(npc.map_id,npc.x,npc.y))
        report=asyncio.run(check(store,prepared,role,npc))
    write_json(OUT/'evidence/npc-sale-runtime.json',report);print(report)


if __name__=='__main__':main()
