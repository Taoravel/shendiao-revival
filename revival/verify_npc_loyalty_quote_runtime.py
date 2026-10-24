"""Known power9 price through actual owners, source transaction and encrypted Peer."""
import asyncio
from contextlib import closing
from pathlib import Path
import sqlite3
import struct
import tempfile
from unittest.mock import patch
from accounts import AccountStore
from currency import apply_currency,CurrencyChange
from game_runtime import GameRuntime
from inventory import Inventory,REFRESH_PET
from inspect_client import OUT,write_json
from role_equipment_storage import synchronize_inventory_resource_source
from task_dialog_protocol import decode_visit_npc
from native_gameplay_probe import probe
from research_pet_blood import native_blood_record
from verify_resource_owner_runtime import fixture
from verify_resource_npc_care_runtime import state,complete_map
from verify_runtime import Peer
from world_entity_protocol import VISIT_NPC,VISIT_NPC_REPLY
import runtime_storage


def change_pet(store,inventory,*,initialize=False):
    with closing(inventory.accounts.connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        if initialize:
            pet=db.execute('INSERT INTO inventory_pets(role_id,template_id,name) VALUES(?,500001,?)',
                (inventory.role_id,'血脉个位九')).lastrowid
            inventory.initialize_pet_growth(db,pet)
            inventory.initialize_pet_care(db,pet,1,80,6000)
            inventory.initialize_pet_blood(db,pet,9)
            apply_currency(db,inventory.account_id,inventory.role_id,inventory.epoch,
                CurrencyChange('known-loyalty-cash','explicit_migration_fixture','controlled-owner-test',(('cash',8000),)),
                store.currency_rules)
        else:
            pet=inventory.immutable_snapshot_transaction(db).pets[0]
            inventory.change_pet_care(db,pet.id,'controlled-later-defeat',pet.care.version,'defeat',1)
        synchronize_inventory_resource_source(db,inventory.account_id,inventory.role_id,inventory.epoch,
            inventory.immutable_snapshot_transaction(db),'loyalty-fixture:'+str(initialize),
            resource_rules=store.resource_rules,equipment_rules=store.equipment_attribute_rules,replayed=False)


def dump(store):
    with closing(store.connect()) as db:return tuple(db.iterdump())


def original_refresh(messages):
    payload=next(body for kind,body in messages if kind==REFRESH_PET)
    _,raw=probe(0xf9d7b0,0xf9d840,0xf9d880,payload=payload)
    assert (struct.unpack_from('<i',raw,8+0x90)[0],struct.unpack_from('<i',raw,8+0xb0)[0])==(100,6000)
    blood=native_blood_record(payload)
    assert (blood['power'],blood['maximum_power'],blood['grade'],blood['level'])==(9,1139,1,0)
    return blood


async def refused(action):
    try:await action
    except (ValueError,sqlite3.DatabaseError,MemoryError):return
    raise AssertionError('Unsafe current-owner recovery accepted')


async def check(store,prepared,role,npc):
    runtime=GameRuntime(store,prepared)
    try:
        peer=Peer(runtime);await peer.login(role);owner=runtime.roles[role['id']]
        key=(npc.map_id<<32)|npc.placement_id;body=struct.pack('>qi',key,3)
        menu=await peer.request(VISIT_NPC,struct.pack('>q',key))
        assert next(decode_visit_npc(b)[1] for k,b in menu if k==VISIT_NPC_REPLY)==[295]
        before=await owner.io(state,store,owner)
        replies=await peer.request(0xc2333,body);complete_map(replies)
        native=await owner.io(original_refresh,replies)
        after=await owner.io(state,store,owner)
        assert before[2]-after[2]==1260 and after[2]==8740
        assert after[0].pets[0].care.loyalty==100 and after[0].pets[0].progress==before[0].pets[0].progress
        assert (after[1].hp,after[1].mp,after[1].version)==(10,20,before[1].version)
        with closing(store.connect()) as db:
            paid=db.execute('SELECT request_id FROM npc_recovery_receipts WHERE role_id=?',(owner.id,)).fetchone()[0]
        await owner.io(change_pet,store,owner.inventory)
        wounded=await owner.io(state,store,owner);unchanged=await owner.io(dump,store)
        complete_map(await owner.mailbox.call('receive',0xc2333,body,request_id=paid))
        assert await owner.io(dump,store)==unchanged and await owner.io(state,store,owner)==wounded
        identity='loyalty-source-failed-retry'
        with closing(store.connect()) as db,db:
            db.execute("CREATE TRIGGER fail_loyalty_source BEFORE INSERT ON role_resource_receipts "
                "WHEN NEW.cause='inventory_change' BEGIN SELECT RAISE(ABORT,'controlled source failure'); END")
        unchanged=await owner.io(dump,store)
        await refused(owner.mailbox.call('receive',0xc2333,body,request_id=identity))
        assert await owner.io(dump,store)==unchanged
        with closing(store.connect()) as db,db:db.execute('DROP TRIGGER fail_loyalty_source')
        original_pack_into=struct.pack_into
        def allocate_packet(fmt,buffer,offset,*values):
            if fmt=='>i' and offset==89:raise MemoryError('Controlled native allocation failure after source')
            return original_pack_into(fmt,buffer,offset,*values)
        unchanged=await owner.io(dump,store)
        with patch.object(struct,'pack_into',allocate_packet):
            await refused(owner.mailbox.call('receive',0xc2333,body,request_id=identity))
        assert await owner.io(dump,store)==unchanged
        complete_map(await owner.mailbox.call('receive',0xc2333,body,request_id=identity))
        final=await owner.io(state,store,owner);assert final[2]==7480
        assert (final[1].hp,final[1].mp,final[1].version)==(10,20,before[1].version)
        assert final[0].pets[0].care.loyalty==100 and final[0].pets[0].care.lifetime==5950
        old_owner=owner
        await peer.connection.close();peer=Peer(runtime);await peer.login(role);owner=runtime.roles[role['id']]
        assert await owner.io(state,store,owner)==final
        await refused(old_owner.mailbox.call('receive',0xc2333,body,request_id=identity))
        complete_map(await owner.mailbox.call('receive',0xc2333,body,request_id=identity))
        assert await owner.io(state,store,owner)==final
        return {'passed':['actual original295 menu and encrypted kind3 with known power9 charges1260',
            'role current10/20/caps/death/version preserved and sole source current',
            'paid replay after actual care loss is SQL read-only and preserves current wounds',
            'late real source SQL failure rolls cash/care/source/all receipts back',
            'late stdlib native encoding allocation failure rolls entire transaction back',
            'same failed identity succeeds once; cold reconnect and old-epoch refusal preserve current state'],
            'original_reply_blood_consumer':native,'original_reply_care_decoder':[100,6000],
            'fixture':'explicit known L21 resources/gear/cash/power9 in temporary storage',
            'native_gui_verified':False,'live_database_modified':False,'battle_executed':False,'deployed':False}
    finally:await runtime.close()


def main():
    with tempfile.TemporaryDirectory(prefix='npc-loyalty-runtime-') as directory:
        store=AccountStore(Path(directory)/'state.sqlite3')
        role=store.create_role(1111,'忠诚费用接线',11,1010109);prepared=runtime_storage.prepare(store)
        npc=next(p for rows in store.npc_resources[0].values() for p in rows if p.npc_id==10086)
        fixture(store,role,npc)
        epoch=store.acquire_lease(1111,role['id'])
        inventory=Inventory(store.leased(1111,role['id'],epoch),1111,role['id'])
        change_pet(store,inventory,initialize=True)
        assert store.save_checkpoint(1111,role['id'],epoch,(npc.map_id,npc.x,npc.y),1)
        store.release_lease(role['id'],epoch)
        result=asyncio.run(asyncio.wait_for(check(store,prepared,role,npc),60))
    write_json(OUT/'evidence/npc-loyalty-quote-runtime.json',result)
    print('PASS',len(result['passed']),'actual-owner loyalty fee groups')


if __name__=='__main__':main()
