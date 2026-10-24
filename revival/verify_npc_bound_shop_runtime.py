"""Ordinary bound-silver purchase through actual encrypted owner routing."""
import asyncio
import hashlib
from pathlib import Path
import struct
import tempfile
from accounts import AccountStore
from game_runtime import GameRuntime
from inspect_client import OUT,write_json
from inventory import BAG_INFO
from currency_protocol import encode_currency_balance
from verify_runtime import Peer
from world_entity_protocol import VISIT_NPC
import npc_gameplay
import runtime_storage


async def check(store,prepared,role,npc,unknown):
    runtime=GameRuntime(store,prepared)
    try:
        peer=Peer(runtime);await peer.login(role)
        owner=runtime.roles[role['id']]
        await owner.io(runtime_storage.initialize_role_wallet,store,1111,role['id'],owner.epoch,
            (1000,1000,0,0),'explicit_migration')
        key=(npc.map_id<<32)|npc.placement_id
        assert await peer.request(VISIT_NPC,struct.pack('>q',key))
        body=struct.pack('>qiii',key,32000,2,1)
        messages=await peer.request(npc_gameplay.BUY_FROM_NPC,body)
        assert any(kind==BAG_INFO for kind,payload in messages), 'Ordinary mode1 bound-silver purchase was not admitted'
        balances=await owner.io(runtime_storage.wallet_snapshot,store,1111,role['id'],owner.epoch)
        assert {r.currency:r.balance for r in balances}=={
            'cash':1000,'bound_silver':700,'yuanbao':0,'bound_yuanbao':0}
        items=(await owner.io(owner.inventory.snapshot))['items']
        assert [(i['template_id'],i['quantity'],i['binding']) for i in items]==[(32000,2,1)]
        one=struct.pack('>qiii',key,32000,1,1)
        assert await peer.request(npc_gameplay.BUY_FROM_NPC,struct.pack('>qiii',key,32000,1,0))
        assert await peer.request(npc_gameplay.BUY_FROM_NPC,one)
        await owner.mailbox.call('receive',npc_gameplay.BUY_FROM_NPC,one,request_id='bound-shop-once')
        before=await owner.io(owner.inventory.snapshot)
        await owner.mailbox.call('receive',npc_gameplay.BUY_FROM_NPC,one,request_id='bound-shop-once')
        assert await owner.io(owner.inventory.snapshot)==before
        try:
            await owner.mailbox.call('receive',npc_gameplay.BUY_FROM_NPC,
                struct.pack('>qiii',key,32000,1,0),request_id='bound-shop-once')
        except ValueError:pass
        else:raise AssertionError('Payment mode changed under an accepted request identity')
        assert await owner.io(owner.inventory.snapshot)==before
        assert await peer.request(npc_gameplay.BUY_FROM_NPC,one)
        replay=await owner.mailbox.call('receive',npc_gameplay.BUY_FROM_NPC,one,request_id='bound-shop-once')
        assert encode_currency_balance('bound_silver',250) in replay
        assert await peer.request(npc_gameplay.BUY_FROM_NPC,one)
        before=await owner.io(owner.inventory.snapshot)
        assert await peer.request(npc_gameplay.BUY_FROM_NPC,one)==[], 'Cash substituted for insufficient bound silver'
        for mode in (2,11,-1):
            assert await peer.request(npc_gameplay.BUY_FROM_NPC,struct.pack('>qiii',key,32000,1,mode))==[]
        assert await owner.io(owner.inventory.snapshot)==before
        items=before['items']
        assert sorted((i['binding'],i['quantity']) for i in items)==[(0,1),(1,6)]
        balances=await owner.io(runtime_storage.wallet_snapshot,store,1111,role['id'],owner.epoch)
        assert {r.currency:r.balance for r in balances}=={
            'cash':850,'bound_silver':100,'yuanbao':0,'bound_yuanbao':0}
        await peer.connection.close();peer=Peer(runtime);await peer.login(role)
        owner=runtime.roles[role['id']]
        assert (await owner.io(owner.inventory.snapshot))['items']==items
        unknown_peer=Peer(runtime);await unknown_peer.login(unknown)
        unknown_owner=runtime.roles[unknown['id']]
        assert await unknown_owner.io(runtime_storage.wallet_snapshot,store,1111,unknown['id'],unknown_owner.epoch) is None
        unknown_before=await unknown_owner.io(unknown_owner.inventory.snapshot)
        assert await unknown_peer.request(npc_gameplay.BUY_FROM_NPC,one)==[]
        assert await unknown_owner.io(unknown_owner.inventory.snapshot)==unknown_before
        assert await unknown_owner.io(runtime_storage.wallet_snapshot,store,1111,unknown['id'],unknown_owner.epoch) is None
        return {'passed':['actual native mode1 purchases two original32000 for300 bound silver',
            'cash remains1000 and actual inventory output is binding1',
            'mode0 unbound goods stay separate; compatible bound goods merge',
            'accepted retry once; mode conflict rejects; paid reply reads current250 rather than historical400',
            'identical fresh native packets each purchase; insufficient bound silver cannot consume cash',
            'special modes reject and reconnect preserves distinct bindings and current balances',
            'unknown legacy wallet rejects bound purchase without creating a baseline or granting items'],
            'npc_gameplay_source':str(Path(npc_gameplay.__file__).resolve()),
            'npc_gameplay_sha256':hashlib.sha256(Path(npc_gameplay.__file__).read_bytes()).hexdigest(),
            'native_gui_verified':False,'live_database_modified':False}
    finally:await runtime.close()


def main():
    with tempfile.TemporaryDirectory() as temp:
        store=AccountStore(Path(temp)/'bound-shop.sqlite3')
        role=store.create_role(1111,'绑银NPC购买',11,1010109)
        unknown=store.create_role(1111,'未知钱包购买',11,1010109)
        prepared=runtime_storage.prepare(store)
        npc=next(p for ps in store.npc_resources[0].values() for p in ps if p.npc_id==10157)
        store.save_position(1111,role['id'],(npc.map_id,npc.x,npc.y))
        store.save_position(1111,unknown['id'],(npc.map_id,npc.x,npc.y))
        try:report=asyncio.run(check(store,prepared,role,npc,unknown))
        except AssertionError as error:
            write_json(OUT/'evidence/npc-bound-shop-runtime-baseline.json',{
                'failure':str(error),'live_database_modified':False})
            raise
    write_json(OUT/'evidence/npc-bound-shop-runtime.json',report);print(report)


if __name__=='__main__':main()
