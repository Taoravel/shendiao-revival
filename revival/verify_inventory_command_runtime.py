"""Stable accepted command retries through the actual migrated RoleOwner."""
import asyncio
from contextlib import closing
from pathlib import Path
import struct
import sqlite3
import tempfile
from unittest.mock import patch
from accounts import AccountStore
from game_runtime import GameRuntime
from inventory import AssetChange,MOVE_ITEM,ADD_PET_POINT,USE_ITEM,REFRESH_PET,BAG_INFO,FREE_PET
from verify_growth_runtime import GrowthPeer
from verify_resource_owner_runtime import fixture,resources
from inspect_client import OUT,write_json
import runtime_storage


def pet_fixture(store,role):
    epoch=store.acquire_lease(1111,role['id'])
    inv=runtime_storage._inventory(store,1111,role['id'],epoch)
    with closing(inv.accounts.connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        inv.apply_settlement(db,AssetChange('controlled-pet-command',pets=(500001,)))
        key=inv.immutable_snapshot_transaction(db).pets[0].id
        state=inv.pet_progress(db,key).state
        inv.change_pet_growth(db,key,'controlled-pet-xp',state.version,'experience',50)
        runtime_storage._synchronize_source(db,store,inv,'controlled-pet-source',replayed=False)
    return key


def receipt_counts(store,rid):
    with closing(store.connect()) as db:
        return tuple(db.execute('SELECT COUNT(*) FROM '+table+' WHERE role_id=?',(rid,)).fetchone()[0]
            for table in ('role_inventory_commands','role_resource_receipts'))


async def check(store,prepared,role,medicine,pet):
    rt=GameRuntime(store,prepared)
    try:
        peer=GrowthPeer(rt);await peer.login(role);owner=rt.roles[role['id']]
        async def request(kind,body,key):
            return await owner.mailbox.call('receive',kind,body,request_id=key)
        before=resources(store,owner)
        body=struct.pack('>6i',pet,1,0,0,0,0)
        first=await request(ADD_PET_POINT,body,'stable-pet-point')
        snapshot=await owner.io(owner.inventory.snapshot)
        # This exact retry used to run allocation again then hit a source
        # conflict, instead of returning a legal current native response.
        replay=await request(ADD_PET_POINT,body,'stable-pet-point')
        assert any(k==REFRESH_PET for k,b in replay),'Paid allocation must return current PetData'
        assert await owner.io(owner.inventory.snapshot)==snapshot,'Potential spent twice'
        counts=receipt_counts(store,owner.id)
        # A second independently accepted identical click is a new operation.
        later=await request(ADD_PET_POINT,body,'new-pet-point')
        current=await owner.io(owner.inventory.snapshot)
        assert current!=snapshot
        reply=await request(ADD_PET_POINT,body,'stable-pet-point')
        assert next(b for k,b in reply if k==REFRESH_PET)==next(b for k,b in later if k==REFRESH_PET)
        assert await owner.io(owner.inventory.snapshot)==current
        try:await request(ADD_PET_POINT,struct.pack('>6i',pet,0,1,0,0,0),'stable-pet-point')
        except ValueError:pass
        else:raise AssertionError('Conflicting body reused accepted command ID')
        # Actual pet medicine consumes once, later current state survives retry.
        med=struct.pack('>iiQ',medicine,1,pet)
        with closing(owner.inventory.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            state=owner.inventory.pet_progress(db,pet).state
            owner.inventory.change_pet_growth(db,pet,'controlled-command-wounds',state.version,'resources',(1,1))
            runtime_storage._synchronize_source(db,store,owner.inventory,'controlled-wounds-source',replayed=False)
        assert await request(USE_ITEM,med,'stable-pet-medicine')
        paid=await owner.io(owner.inventory.snapshot);paid_counts=receipt_counts(store,owner.id)
        assert await request(USE_ITEM,med,'stable-pet-medicine')
        assert await owner.io(owner.inventory.snapshot)==paid and receipt_counts(store,owner.id)==paid_counts
        # Movement paid reply reads a later slot, even when original source is gone.
        item=next(i for i in paid['items'] if i['id']==medicine)
        move=struct.pack('>6iq',1,medicine,item['slot'],1,7,0,0)
        assert await request(MOVE_ITEM,move,'stable-move')
        assert await request(MOVE_ITEM,struct.pack('>6iq',1,medicine,7,1,2,0,0),'later-move')
        expected=await owner.io(owner.inventory.receive,0xc03f2,struct.pack('>iQ',1,0))
        assert tuple(await request(MOVE_ITEM,move,'stable-move'))==tuple(expected)
        # Final original bag encoding fails AFTER source/receipt work; everything rolls back.
        snap=await owner.io(owner.inventory.snapshot);state=resources(store,owner);paid_counts=receipt_counts(store,owner.id)
        move2=struct.pack('>6iq',1,medicine,2,1,9,0,0)
        with patch.object(owner.inventory,'_bag_reply',side_effect=ValueError('controlled final command bag')):
            try:await request(MOVE_ITEM,move2,'retry-after-encoding-failure')
            except ValueError:pass
            else:raise AssertionError('Expected final native encoding failure')
        assert await owner.io(owner.inventory.snapshot)==snap
        assert resources(store,owner)==state and receipt_counts(store,owner.id)==paid_counts
        assert await request(MOVE_ITEM,move2,'retry-after-encoding-failure')
        assert next(i for i in (await owner.io(owner.inventory.snapshot))['items'] if i['id']==medicine)['slot']==9
        # A released original pet does not invalidate a paid read or resurrect it.
        assert await request(FREE_PET,struct.pack('>i',pet),'free-old-pet')
        paid=await owner.io(owner.inventory.snapshot);paid_counts=receipt_counts(store,owner.id)
        reply=await request(ADD_PET_POINT,body,'stable-pet-point')
        assert (0xc07dd,struct.pack('>ii',1,pet)) in reply and (0xc07db,b'') in reply
        assert await owner.io(owner.inventory.snapshot)==paid and receipt_counts(store,owner.id)==paid_counts
        after=resources(store,owner)
        assert (after.hp,after.mp,after.version)==(before.hp,before.mp,before.version)
        await peer.connection.close();peer=GrowthPeer(rt);await peer.login(role);owner=rt.roles[role['id']]
        assert resources(store,owner)==after
        assert await request(MOVE_ITEM,move,'stable-move')
        assert receipt_counts(store,owner.id)==paid_counts
        original_connect=store.connect
        def read_only_connect():
            db=original_connect()
            db.set_authorizer(lambda action,*args:sqlite3.SQLITE_DENY if action in (
                sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE,
                sqlite3.SQLITE_CREATE_TABLE,sqlite3.SQLITE_DROP_TABLE) else sqlite3.SQLITE_OK)
            return db
        with patch.object(store,'connect',side_effect=read_only_connect):
            assert await request(MOVE_ITEM,move,'stable-move')
        # An intentionally unsynchronized trusted fixture cannot be repaired
        # by a paid receipt read; retain both the drift and old resource record.
        with closing(owner.inventory.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            owner.inventory.apply_settlement(db,AssetChange('controlled-pending-source',grants=((32000,1,1),)))
        pending=await owner.io(owner.inventory.snapshot)
        state=resources(store,owner)
        try:await request(MOVE_ITEM,move,'stable-move')
        except ValueError:pass
        else:raise AssertionError('Paid command repaired an unrelated pending source')
        assert resources(store,owner)==state and await owner.io(owner.inventory.snapshot)==pending
        assert receipt_counts(store,owner.id)==paid_counts
        await peer.connection.close()
    finally:await rt.close()


def main():
    with tempfile.TemporaryDirectory(prefix='inventory-command-runtime-') as directory:
        store=AccountStore(Path(directory)/'state.sqlite3')
        role=store.create_role(1111,'通用凭据验证',11,1010109)
        prepared=runtime_storage.prepare(store)
        npc=next(p for ps in store.npc_resources[0].values() for p in ps if p.npc_id==10157)
        _,medicine=fixture(store,role,npc);pet=pet_fixture(store,role)
        asyncio.run(check(store,prepared,role,medicine,pet))
    result=dict(passed=['actual Owner stable point/medicine commands consume once and return current native messages',
        'new identical accepted command executes; conflicting body with old ID rejects',
        'old move reads later slot; old pet request after release reads current removal/rest',
        'late bag encoding failure rolls back asset/source/common receipt and same key later succeeds',
        'reconnect preserves wounds/resource version and durable paid command identity',
        'paid path passes SQL no-write authorizer and refuses pending source without repair'],database='disposable',
        fixture='explicit legacy role/pet XP/resources/medicine/wounds',live_server_changed=False,native_gui_verified=False)
    write_json(OUT/'evidence/inventory-command-runtime-verification.json',result);print(result)


if __name__=='__main__':main()
