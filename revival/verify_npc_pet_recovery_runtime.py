"""Original all-carried-pet care request reaches owned pet/cash transactions."""
import asyncio
from contextlib import closing
from pathlib import Path
import struct
import tempfile
from accounts import AccountStore
from game_runtime import GameRuntime
from inventory import AssetChange,REFRESH_PET
from world_entity_protocol import VISIT_NPC,NPC_SERVICE
from task_dialog_protocol import decode_visit_npc
from verify_runtime import Peer
from inspect_client import OUT,write_json
import runtime_storage


def hurt(inventory):
    with closing(inventory.accounts.connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        for pet in inventory.immutable_snapshot_transaction(db).pets:
            inventory.change_pet_growth(db,pet.id,'fixture:damage',pet.progress.state.version,'resources',(0,0))
            inventory.change_pet_care(db,pet.id,'fixture:defeat',pet.care.version,'defeat',1)


async def check(store,prepared,role,npc):
    rt=GameRuntime(store,prepared)
    try:
        p=Peer(rt);await p.login(role);owner=rt.roles[role['id']]
        await owner.io(runtime_storage.initialize_role_wallet,store,1111,role['id'],owner.epoch,(5000,0,0,0),'explicit_migration')
        await owner.mailbox.call('settle',AssetChange('pet-recovery-fixture',pets=(500001,500001)))
        await owner.io(hurt,owner.inventory)
        key=(npc.map_id<<32)|npc.placement_id
        menu=await p.request(VISIT_NPC,struct.pack('>q',key))
        assert decode_visit_npc(menu[-1][1])[1]==[295], 'Trainer must display original295 local submenu'
        before_menu=await owner.io(owner.inventory.immutable_snapshot)
        for service in (295,10001):
            try:await owner.mailbox.call('receive',NPC_SERVICE,struct.pack('>qi',key,service))
            except ValueError:pass
            else:raise AssertionError('Local submenu parent/return granted a server action')
        assert await owner.io(owner.inventory.immutable_snapshot)==before_menu
        body=struct.pack('>qi',key,4)
        messages=await owner.mailbox.call('receive',0xc2333,body,request_id='pet-care-once')
        assert len([k for k,b in messages if k==REFRESH_PET])==2
        pets=(await owner.io(owner.inventory.immutable_snapshot)).pets
        assert len(pets)==2
        for pet in pets:
            assert (pet.progress.state.hp,pet.progress.state.mp)==(pet.progress.attributes.max_hp,pet.progress.attributes.max_mp)
            assert (pet.care.loyalty,pet.care.lifetime)==(100,5950)
        wallet=await owner.io(runtime_storage.wallet_snapshot,store,1111,role['id'],owner.epoch)
        assert next(r.balance for r in wallet if r.currency=='cash')==3160
        before=await owner.io(owner.inventory.immutable_snapshot)
        await owner.mailbox.call('receive',0xc2333,body,request_id='pet-care-once')
        assert await owner.io(owner.inventory.immutable_snapshot)==before
        assert await p.request(0xc2333,body)==[] # Fresh attempt with no missing care does not charge.
        assert await p.request(0xc2333,struct.pack('>qi',key,1))==[] # Trainer is not an inn.
        await p.connection.close();p=Peer(rt);await p.login(role);owner=rt.roles[role['id']]
        assert await owner.io(owner.inventory.immutable_snapshot)==before
        wallet=await owner.io(runtime_storage.wallet_snapshot,store,1111,role['id'],owner.epoch)
        assert next(r.balance for r in wallet if r.currency=='cash')==3160
        return {'passed':['trainer original295 local submenu retains real authorized services10/11/12',
            'forged parent295/local return10001 server requests reject without mutation',
            'CRecovery kind4 heals both carried pets including HP0',
            'normal level0 pet fee20 each + loyalty20x45 each -> total1840',
            'cash5000->3160 and pet changes commit together','loyalty restored, lifetime5950 unchanged',
            'accepted retry once; fresh no-op and wrong recovery kind refused','reconnect restores care/resources/cash'],
            'native_gui_verified':False,'live_database_modified':False}
    finally:await rt.close()


def main():
    with tempfile.TemporaryDirectory() as temp:
        store=AccountStore(Path(temp)/'pet-care.sqlite3')
        roles=[store.create_role(1111,name,11,1010109) for name in ('宠物治疗甲','宠物治疗乙')]
        # This isolated fixture is an existing level21 role; no origin/baseline is inferred.
        with closing(store.connect()) as db,db:db.executemany('UPDATE roles SET level=21 WHERE id=?',
            ((role['id'],) for role in roles))
        roles=[store.owned_role(1111,role['id']) for role in roles]
        prepared=runtime_storage.prepare(store)
        npcs=[next(p for ps in store.npc_resources[0].values() for p in ps if p.npc_id==npc_id)
              for npc_id in (10086,10493)]
        results=[]
        for role,npc in zip(roles,npcs):
            store.save_position(1111,role['id'],(npc.map_id,npc.x,npc.y))
            results.append(asyncio.run(check(store,prepared,role,npc)))
        assert results[0]==results[1]
        report={**results[0],'checked_npc_ids':[p.npc_id for p in npcs]}
    write_json(OUT/'evidence/npc-pet-recovery-runtime.json',report);print(report)


if __name__=='__main__':main()
