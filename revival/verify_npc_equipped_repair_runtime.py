"""Real encrypted NPC repair publishes same-transaction equipped role attributes.

Uses an explicit legacy fixture baseline, actual equip and repair wire routes,
normal server randomness and native RC4/MPPC. No substitute dispatcher/hook.
"""
import asyncio
from contextlib import closing
from dataclasses import replace
from pathlib import Path
import struct
import tempfile
from accounts import AccountStore
from game_runtime import GameRuntime
from inventory import AssetChange,EQUIP_ITEM
from inspect_client import OUT,write_json
from role_growth import initialize_growth
from role_attribute_storage import initialize_attribute_baseline
from role_equipment import EquipmentAttributeBasis
from role_equipment_storage import initialize_equipment_attribute_basis
from task_dialog_protocol import decode_visit_npc
from world_entity_protocol import VISIT_NPC
from wire import read_compact
from verify_runtime import Peer
import runtime_storage


def seed_profile(store,inventory):
    with closing(inventory.accounts.connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        growth=initialize_growth(db,inventory.account_id,inventory.role_id,inventory.epoch,
            store.growth_rules,expected_level=1,free_points=0)
        p=store.attribute_rules.initial_profile
        initialize_attribute_baseline(db,inventory.account_id,inventory.role_id,inventory.epoch,
            p.baseline(inventory.role_id),growth,store.attribute_rules,
            replace(p.vitals(inventory.role_id),hp=70,mp=40))
        initialize_equipment_attribute_basis(db,inventory.account_id,inventory.role_id,inventory.epoch,
            EquipmentAttributeBasis(inventory.role_id,9,0,store.equipment_attribute_rules.revision,
                11,'explicit-known-legacy-NPC-wire-fixture'),store.equipment_attribute_rules)


def wear(inventory,key):
    with closing(inventory.accounts.connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        condition=inventory.equipment_condition(db,key)
        assert (condition.current,condition.maximum)==(100,100)
        inventory.wear_equipment(db,key,'NPC-wire-wear20',condition.version,20)


def attributes(messages):
    maps=[]
    for kind,body in messages:
        if kind!=0xc32c8:continue
        count,pos=read_compact(body)
        assert len(body)==pos+count*8
        values=dict(struct.unpack_from('>if',body,pos+i*8) for i in range(count))
        if 80 in values:maps.append(values)
    assert len(maps)==1,'Expected exactly one final role attribute map'
    values=maps[0]
    assert len(values)==20 and (values[80],values[810],values[1230])==(45,35,19)
    assert (values[60],values[70])==(70,40)
    return values


async def check(store,prepared,role,npc):
    rt=GameRuntime(store,prepared)
    try:
        peer=Peer(rt);await peer.login(role);owner=rt.roles[role['id']]
        await owner.io(runtime_storage.initialize_role_wallet,store,1111,role['id'],owner.epoch,
            (1000,0,0,0),'explicit_migration')
        await owner.io(seed_profile,store,owner.inventory)
        await owner.mailbox.call('settle',AssetChange('equipped-NPC-fixture',grants=((49009,1,1),)))
        gear=(await owner.io(owner.inventory.snapshot))['items'][0]
        attributes(await peer.request(EQUIP_ITEM,struct.pack('>ii',gear['id'],0)))
        await owner.io(wear,owner.inventory,gear['id'])
        key=(npc.map_id<<32)|npc.placement_id
        menu=await peer.request(VISIT_NPC,struct.pack('>q',key))
        assert 513 in decode_visit_npc(menu[-1][1])[1]
        result=await peer.request(0xc0413,struct.pack('>iqii',2,key,4,gear['id']))
        final=attributes(result)
        assert (0xc03fa,struct.pack('>iq',1,960)) in result
        snapshot=await owner.io(owner.inventory.snapshot);item=snapshot['items'][0]
        assert item['equipment_slot']==0 and item['condition'].version==2
        assert (item['condition'].current,item['condition'].maximum) in ((100,100),(80,90))
        await peer.connection.close();peer=Peer(rt);await peer.login(role)
        assert attributes(peer.initial)==final
        owner=rt.roles[role['id']]
        assert (await owner.io(owner.inventory.snapshot))['items'][0]==item
        wallet=await owner.io(runtime_storage.wallet_snapshot,store,1111,role['id'],owner.epoch)
        assert next(r.balance for r in wallet if r.currency=='cash')==960
        return {'passed':['actual encrypted equip and ordinary NPC method2/column4 repair',
            'real repair_role_equipment hook emits one complete20entry final attribute map45/35/19',
            'HP70/MP40 preserved and cash1000->960 in native absolute refresh',
            'normal random success/failure persists correct condition without changing supported flat effects',
            'reconnect full map/current weapon condition/cash960 match committed state'],
            'replacement_dispatcher_or_projection':False,'native_gui_verified':False,'live_database_modified':False}
    finally:await rt.close()


def main():
    with tempfile.TemporaryDirectory() as temp:
        store=AccountStore(Path(temp)/'equipped-repair.sqlite3')
        role=store.create_role(1111,'装备修理',11,1010109);prepared=runtime_storage.prepare(store)
        npc=next(p for ps in store.npc_resources[0].values() for p in ps if p.npc_id==10004)
        store.save_position(1111,role['id'],(npc.map_id,npc.x,npc.y))
        report=asyncio.run(check(store,prepared,role,npc))
    write_json(OUT/'evidence/npc-equipped-repair-runtime.json',report);print(report)


if __name__=='__main__':main()
