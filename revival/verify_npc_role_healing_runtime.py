"""Original female-doctor294 through actual encrypted Peer and role/map owners."""
import asyncio
from contextlib import closing
from dataclasses import replace
from pathlib import Path
import struct
import tempfile
from accounts import AccountStore
from game_runtime import GameRuntime
from inventory import Inventory
from inspect_client import OUT,write_json
from currency import initialize_wallet
from role_growth import initialize_growth
from role_attribute_storage import initialize_attribute_baseline
from role_equipment import EquipmentAttributeBasis,resource_caps_from_projection
from role_equipment_storage import initialize_equipment_attribute_basis,current_equipment_totals
from role_resource_storage import migrate_role_resources,read_role_resources
from task_dialog_protocol import decode_visit_npc
from verify_growth_runtime import role_values
from verify_runtime import Peer
from world_entity_protocol import VISIT_NPC,VISIT_NPC_REPLY,NPC_SERVICE
import runtime_storage


def known_profile(store,role,*,hit=None,migrated=True):
    epoch=store.acquire_lease(1111,role['id'])
    inventory=Inventory(store.leased(1111,role['id'],epoch),1111,role['id'])
    with closing(inventory.accounts.connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        growth=initialize_growth(db,1111,role['id'],epoch,store.growth_rules,expected_level=1,free_points=0)
        profile=store.attribute_rules.initial_profile
        baseline=profile.baseline(role['id'])
        if hit is not None:baseline=replace(baseline,values=baseline.values[:4]+(hit,)+baseline.values[5:])
        old=initialize_attribute_baseline(db,1111,role['id'],epoch,baseline,growth,
            store.attribute_rules,replace(profile.vitals(role['id']),hp=70,mp=40)).vitals
        initialize_equipment_attribute_basis(db,1111,role['id'],epoch,
            EquipmentAttributeBasis(role['id'],9,0,store.equipment_attribute_rules.revision,11,
                'explicit-healer-fixture'),store.equipment_attribute_rules)
        initialize_wallet(db,1111,role['id'],epoch,(1000,500,0,0),'explicit_migration',store.currency_rules)
        totals=current_equipment_totals(db,1111,role['id'],epoch,inventory.immutable_snapshot_transaction(db),
            store.equipment_attribute_rules)
        if migrated:
            migrate_role_resources(db,1111,role['id'],epoch,old,resource_caps_from_projection(totals),
                origin='explicit_migration',migration_id='known-healer-profile',rules=store.resource_rules,
                equipment_rules=store.equipment_attribute_rules)
    return inventory


async def check(store,prepared,role,npc):
    runtime=GameRuntime(store,prepared)
    try:
        peer=Peer(runtime);await peer.login(role);owner=runtime.roles[role['id']]
        key=(npc.map_id<<32)|npc.placement_id
        menu=await peer.request(VISIT_NPC,struct.pack('>q',key))
        ids=next(decode_visit_npc(body)[1] for kind,body in menu if kind==VISIT_NPC_REPLY)
        assert 294 in ids, 'Original doctor10380 has no authorized healing294 menu'
        before=await owner.io(owner.inventory.snapshot)
        messages=await peer.request(NPC_SERVICE,struct.pack('>qi',key,294))
        values=role_values(messages)
        assert 60 in values, 'Healing294 is registered but RoleOwner has no settlement route'
        assert (values[60],values[70],values[140],values[150])==(100,100,100,100)
        balances=await owner.io(runtime_storage.wallet_snapshot,store,1111,role['id'],owner.epoch)
        assert {r.currency:r.balance for r in balances}=={
            'cash':970,'bound_silver':500,'yuanbao':0,'bound_yuanbao':0}
        assert await owner.io(owner.inventory.snapshot)==before
        with closing(store.leased(1111,role['id'],owner.epoch).connect()) as db,db:
            db.execute('BEGIN')
            resources=read_role_resources(db,1111,role['id'],owner.epoch,store.resource_rules)
            assert (resources.hp,resources.mp,resources.version)==(100,100,1)
        return {'passed':['actual original10380/placement34 offers designed294 alongside its existing menu',
            'native CNpcService294 heals known70/40 to current final100/100 and charges30 cash',
            'bound500 and actual inventory remain unchanged; unique resource version advances once'],
            'native_gui_verified':False,'live_database_modified':False,'battle_executed':False}
    finally:await runtime.close()


def main():
    with tempfile.TemporaryDirectory() as temp:
        store=AccountStore(Path(temp)/'role-healing.sqlite3')
        role=store.create_role(1111,'NPC人物治疗',11,1010109)
        prepared=runtime_storage.prepare(store);known_profile(store,role)
        npc=next(p for ps in store.npc_resources[0].values() for p in ps if p.npc_id==10380)
        store.save_position(1111,role['id'],(npc.map_id,npc.x,npc.y))
        try:report=asyncio.run(check(store,prepared,role,npc))
        except (AssertionError,KeyError) as error:
            write_json(OUT/'evidence/npc-role-healing-runtime-baseline.json',{
                'failure':str(error),'live_database_modified':False})
            raise
    write_json(OUT/'evidence/npc-role-healing-runtime.json',report);print(report)


if __name__=='__main__':main()
