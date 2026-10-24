"""Native inn rest consumes known vigor and cash with authoritative vitals."""
import asyncio
from contextlib import closing
from dataclasses import replace
from pathlib import Path
import struct
import tempfile
from accounts import AccountStore
from game_runtime import GameRuntime
from item_effects import VitalState
from role_attributes import AttributeBaseline
from role_growth import initialize_growth
from role_attribute_storage import initialize_attribute_baseline,read_attribute_snapshot,update_role_vitals
from world_entity_protocol import VISIT_NPC
from task_dialog_protocol import decode_visit_npc
from verify_runtime import Peer
from inspect_client import OUT,write_json
import runtime_storage
import role_vigor


def fixture_profile(store,inventory):
    with closing(inventory.accounts.connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        growth=initialize_growth(db,inventory.account_id,inventory.role_id,inventory.epoch,store.growth_rules,
                                expected_level=21,free_points=0)
        basis=AttributeBaseline(inventory.role_id,21,0,(10,10,10,10,10),(500,1000,20,5,40,20,10,20,5))
        initialize_attribute_baseline(db,inventory.account_id,inventory.role_id,inventory.epoch,basis,growth,
            store.attribute_rules,VitalState(inventory.role_id,0,10,500,20,1000))


def current(store,inventory,damage=False):
    with closing(inventory.accounts.connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        role=read_attribute_snapshot(db,inventory.account_id,inventory.role_id,inventory.epoch)
        if damage:
            role=update_role_vitals(db,inventory.account_id,inventory.role_id,inventory.epoch,role.vitals,
                                   replace(role.vitals,version=role.vitals.version+1,hp=50,mp=50))
        return role.vitals,role_vigor.read(db,inventory,store.vigor_rules)


async def check(store,prepared,role,npc):
    rt=GameRuntime(store,prepared)
    try:
        p=Peer(rt);await p.login(role);owner=rt.roles[role['id']]
        await owner.io(fixture_profile,store,owner.inventory)
        await owner.io(runtime_storage.initialize_role_wallet,store,1111,role['id'],owner.epoch,(1000,0,0,0),'explicit_migration')
        key=(npc.map_id<<32)|npc.placement_id;body=struct.pack('>qi',key,1)
        assert await p.request(0xc2333,body)==[] # Legacy vigor is still unknown.
        await owner.mailbox.call('initialize_vigor',100,100,'explicit_migration')
        menu=await p.request(VISIT_NPC,struct.pack('>q',key))
        assert 3 in decode_visit_npc(menu[-1][1])[1]
        messages=await owner.mailbox.call('receive',0xc2333,body,request_id='inn-once')
        assert len([k for k,b in messages if k==0xc32c8])==2
        vitals,vigor=await owner.io(current,store,owner.inventory)
        assert (vitals.hp,vitals.mp,vigor.value)==(500,1000,85)
        wallet=await owner.io(runtime_storage.wallet_snapshot,store,1111,role['id'],owner.epoch)
        assert next(r.balance for r in wallet if r.currency=='cash')==500
        hurt,_=await owner.io(current,store,owner.inventory,True)
        await owner.mailbox.call('receive',0xc2333,body,request_id='inn-once')
        assert (await owner.io(current,store,owner.inventory))[0]==hurt
        await p.request(0xc2333,body)
        assert (await owner.io(current,store,owner.inventory))[1].value==70
        await owner.io(current,store,owner.inventory,True)
        before=await owner.io(current,store,owner.inventory)
        assert await p.request(0xc2333,body)==[] # Payment fails after vigor planning.
        assert await owner.io(current,store,owner.inventory)==before
        await p.connection.close();p=Peer(rt);await p.login(role);owner=rt.roles[role['id']]
        assert (await owner.io(current,store,owner.inventory))[1].value==70
        assert any(k==0xc32c8 and struct.pack('>i',440) in b for k,b in p.initial)
        return {'passed':['original inn service3 / CRecovery kind1','unknown old vigor profile refused',
            'known HP/MP restored with vigor100->85 and cash1000->500','committed retry does not heal later damage',
            'new rest vigor85->70; insufficient cash leaves vigor and vitals unchanged',
            'reconnect publishes current vigor70 and preserves wounds'],'native_gui_verified':False,
            'live_database_modified':False}
    finally:await rt.close()


def main():
    with tempfile.TemporaryDirectory() as temp:
        store=AccountStore(Path(temp)/'inn.sqlite3');role=store.create_role(1111,'客栈休息',11,1010109)
        with closing(store.connect()) as db,db:db.execute('UPDATE roles SET level=21 WHERE id=?',(role['id'],))
        role=store.owned_role(1111,role['id']);prepared=runtime_storage.prepare(store)
        npc=next(p for ps in store.npc_resources[0].values() for p in ps if p.npc_id==10157)
        store.save_position(1111,role['id'],(npc.map_id,npc.x,npc.y))
        report=asyncio.run(check(store,prepared,role,npc))
    write_json(OUT/'evidence/npc-inn-runtime.json',report);print(report)


if __name__=='__main__':main()
