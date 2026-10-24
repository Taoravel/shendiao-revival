"""Migrated resources through real NPC purchase/sale/depot Owner routes.

Known legacy profile/item/cash/NPC-position fixtures; no natural quest claim.
The hooks are the actual shared source helper, not a replacement dispatcher.
"""
import asyncio
from contextlib import closing
from pathlib import Path
import struct
import tempfile
from unittest.mock import patch
from accounts import AccountStore
from game_runtime import GameRuntime
from inventory import MOVE_ITEM,BAG_INFO
from verify_growth_runtime import GrowthPeer
from verify_resource_owner_runtime import fixture,resources
from inspect_client import OUT,write_json
from wire import compact
import npc_gameplay
import runtime_storage


def counts(store,role_id):
    with closing(store.connect()) as db:
        return tuple(db.execute('SELECT count(*) FROM '+t+' WHERE role_id=?',(role_id,)).fetchone()[0]
            for t in ('role_resource_receipts','role_wallet_receipts','npc_command_receipts'))


async def check(store,prepared,roles,npcs,items):
    rt=GameRuntime(store,prepared)
    try:
        for index,(role,npc,keys) in enumerate(zip(roles,npcs,items)):
            peer=GrowthPeer(rt);await peer.login(role);owner=rt.roles[role['id']]
            before=resources(store,owner)
            key=(npc.map_id<<32)|npc.placement_id
            if index==0:
                body=struct.pack('>qiii',key,32000,2,0)
                reply=await owner.mailbox.call('receive',0xc232c,body,request_id='resource-shop-once')
                assert any(k==BAG_INFO for k,_ in reply)
                paid=await owner.io(owner.inventory.snapshot);paid_resource=resources(store,owner)
                paid_counts=counts(store,owner.id)
                await owner.mailbox.call('receive',0xc232c,body,request_id='resource-shop-once')
                assert await owner.io(owner.inventory.snapshot)==paid
                assert resources(store,owner)==paid_resource and counts(store,owner.id)==paid_counts
                with patch.object(owner.inventory,'equipment_bag_messages',side_effect=ValueError('controlled NPC final bag encoding')):
                    assert await peer.request(0xc232c,struct.pack('>qiii',key,32000,1,0))==[]
                assert await owner.io(owner.inventory.snapshot)==paid
                assert resources(store,owner)==paid_resource and counts(store,owner.id)==paid_counts
            elif index==1:
                medicine=keys[1]
                body=struct.pack('>q',key)+compact(1)+struct.pack('>i',medicine)
                sold=await owner.mailbox.call('receive',0xc232d,body,request_id='resource-sale-once')
                assert any(k==0xc0434 for k,_ in sold)
                paid=await owner.io(owner.inventory.snapshot);paid_resource=resources(store,owner);paid_counts=counts(store,owner.id)
                await owner.mailbox.call('receive',0xc232d,body,request_id='resource-sale-once')
                assert await owner.io(owner.inventory.snapshot)==paid
                assert resources(store,owner)==paid_resource and counts(store,owner.id)==paid_counts
                body=struct.pack('>qi',key,medicine)
                assert await owner.mailbox.call('receive',0xc232e,body,request_id='resource-buyback-once')
                paid=await owner.io(owner.inventory.snapshot);paid_counts=counts(store,owner.id)
                assert next(i for i in paid['items'] if i['id']==medicine)['quantity']==3
                await owner.mailbox.call('receive',0xc232e,body,request_id='resource-buyback-once')
                assert await owner.io(owner.inventory.snapshot)==paid and counts(store,owner.id)==paid_counts
            else:
                await owner.io(npc_gameplay.initialize_depot,owner.inventory,100,'explicit_migration')
                assert await peer.request(0xc04f0,struct.pack('>q',key))
                medicine=keys[1]
                item=next(i for i in (await owner.io(owner.inventory.snapshot))['items'] if i['id']==medicine)
                body=struct.pack('>6iq',1,medicine,item['slot'],2,0,0,0)
                assert await owner.mailbox.call('receive',MOVE_ITEM,body,request_id='resource-depot-once')
                paid=await owner.io(owner.inventory.snapshot);paid_resource=resources(store,owner);paid_counts=counts(store,owner.id)
                assert all(i['id']!=medicine for i in paid['items'])
                await owner.mailbox.call('receive',MOVE_ITEM,body,request_id='resource-depot-once')
                assert await owner.io(owner.inventory.snapshot)==paid
                assert resources(store,owner)==paid_resource and counts(store,owner.id)==paid_counts
                assert await peer.request(MOVE_ITEM,struct.pack('>6iq',2,medicine,0,1,0,0,0))
                assert next(i for i in (await owner.io(owner.inventory.snapshot))['items'] if i['id']==medicine)['quantity']==3
            after=resources(store,owner)
            assert (after.hp,after.mp,after.version)==(before.hp,before.mp,before.version)
            assert after.caps.source.inventory_revision>before.caps.source.inventory_revision
            profile=await owner.io(runtime_storage.role_load_profile,store,1111,owner.id,owner.epoch)
            assert (profile.attributes.vitals.hp,profile.attributes.vitals.mp)==(10,20)
            await peer.connection.close();peer=GrowthPeer(rt);await peer.login(role)
            assert resources(store,rt.roles[role['id']])==after
            await peer.connection.close()
    finally:await rt.close()


def main():
    with tempfile.TemporaryDirectory(prefix='resource-npc-assets-') as folder:
        store=AccountStore(Path(folder)/'state.sqlite3')
        roles=[store.create_role(1111,'资源商'+str(i),11,1010109) for i in range(3)]
        prepared=runtime_storage.prepare(store)
        npcs=[next(p for ps in store.npc_resources[0].values() for p in ps if p.npc_id==ident)
            for ident in (10157,10011,10003)]
        items=[fixture(store,role,npc) for role,npc in zip(roles,npcs)]
        asyncio.run(check(store,prepared,roles,npcs,items))
    result=dict(passed=['actual migrated Owner purchase/sale/buyback/depot moves synchronize inventory source before commit',
        'NPC common receipts make paid retries current strict reads without repeated asset or source writes',
        'real NPC final bag encoding failure rolls back assets/cash/source/receipts',
        'known10/20 resources and resource version remain unchanged through mutation and reconnect'],
        fixture='explicit known legacy profiles/items/cash and actual NPC position fixtures',
        database='disposable',native_gui_verified=False,live_server_changed=False,battle_executed=False)
    write_json(OUT/'evidence/resource-npc-assets-runtime-verification.json',result);print(result)


if __name__=='__main__':main()
