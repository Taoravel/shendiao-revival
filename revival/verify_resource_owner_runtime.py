"""Explicitly migrated known legacy resources through actual shared owners.

Controlled L21/XP/gear/medicine/wounds/cash/vigor and NPC position fixtures in
disposable storage; no automatic activation, natural quest claim, GUI or battle.
"""
import asyncio
from contextlib import closing
from pathlib import Path
import struct
import tempfile
import time
from unittest.mock import patch
from accounts import AccountStore
from currency import initialize_wallet
from game_runtime import GameRuntime
from inventory import Inventory,AssetChange,EQUIP_ITEM,UNEQUIP_ITEM,USE_ITEM,MOVE_ITEM
from item_effects import VitalState
from role_attributes import AttributeBaseline
from role_attribute_storage import initialize_attribute_baseline
from role_equipment import EquipmentAttributeBasis,resource_caps_from_projection
from role_equipment_storage import initialize_equipment_attribute_basis,current_equipment_totals
from role_growth import initialize_growth
from role_growth_protocol import C_REQ_LEVEL_UP,C_ADD_POINT_TO_ATTR
from role_resource_plan import load_resource_rules
from role_resource_storage import migrate_role_resources,read_role_resources
from verify_growth_runtime import GrowthPeer,role_values,world_vitals
from inspect_client import OUT,write_json
import role_vigor
import runtime_storage


def fixture(store,role,npc):
    rules=load_resource_rules();epoch=store.acquire_lease(1111,role['id'])
    inv=Inventory(store.leased(1111,role['id'],epoch),1111,role['id'])
    gear=store.equipment_attribute_rules
    with closing(inv.accounts.connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        db.execute('UPDATE roles SET level=21 WHERE id=?',(role['id'],))
        db.execute('INSERT INTO role_progress VALUES(?,?)',(role['id'],store.growth_rules.costs[21]))
        growth=initialize_growth(db,1111,role['id'],epoch,store.growth_rules,expected_level=21,free_points=0)
        old=initialize_attribute_baseline(db,1111,role['id'],epoch,
            AttributeBaseline(role['id'],21,0,(10,10,10,10,10),(500,1000,20,5,40,20,10,20,5)),
            growth,store.attribute_rules,VitalState(role['id'],0,10,500,20,1000))
        initialize_equipment_attribute_basis(db,1111,role['id'],epoch,
            EquipmentAttributeBasis(role['id'],9,0,gear.revision,11,'controlled-known-sealing'),gear)
        initialize_wallet(db,1111,role['id'],epoch,(2000,0,0,0),'explicit_migration',store.currency_rules)
        inv.apply_settlement(db,AssetChange('controlled-migrated-items',grants=((49009,1,1),(32000,3,1))))
        assets=inv.immutable_snapshot_transaction(db)
        weapon=next(i.id for i in assets.items if i.template_id==49009)
        medicine=next(i.id for i in assets.items if i.template_id==32000)
        inv.equip_transaction(db,weapon,0,epoch,'controlled-initial-equip')
        assets=inv.immutable_snapshot_transaction(db)
        caps=resource_caps_from_projection(current_equipment_totals(db,1111,role['id'],epoch,assets,gear))
        migrate_role_resources(db,1111,role['id'],epoch,old.vitals,caps,origin='explicit_migration',
            migration_id='controlled-resource-owner',rules=rules,equipment_rules=gear)
    role_vigor.initialize_profile(store,inv,100,100,'explicit_migration',int(time.monotonic()*1000))
    store.save_position(1111,role['id'],(npc.map_id,npc.x,npc.y))
    return weapon,medicine


def resources(store,owner):
    with closing(owner.inventory.accounts.connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        return read_role_resources(db,1111,owner.id,owner.epoch,store.resource_rules)


async def check(store,prepared,a,b,npc,items):
    rt=GameRuntime(store,prepared)
    try:
        peer=GrowthPeer(rt);await peer.login(a);owner=rt.roles[a['id']]
        assert world_vitals(peer)==(21,(10,500,500,20,1000)), 'Login must preserve the migrated wounds'
        assert role_values(peer.initial)[1230]==19
        first=await peer.request(C_REQ_LEVEL_UP,bytes(4))
        assert role_values(first)[60]==20 and role_values(first)[140]==510
        allocated=await peer.request(C_ADD_POINT_TO_ATTR,struct.pack('>5i',1,0,0,0,0))
        assert role_values(allocated)[60]==30 and role_values(allocated)[140]==520
        assert role_values(allocated)[500]==4
        weapon,medicine=items
        healed=await peer.request(USE_ITEM,struct.pack('>iiQ',medicine,0,owner.id))
        assert role_values(healed)[60]==230
        key=(npc.map_id<<32)|npc.placement_id
        rested=await peer.request(0xc2333,struct.pack('>qi',key,1))
        assert role_values(rested)[60]==520 and role_values(rested)[140]==520
        full=resources(store,owner)
        assert full.hp==full.caps.hp_max and full.mp==full.caps.mp_max
        with closing(store.connect()) as db:
            medicine_request=db.execute('SELECT settlement_id FROM inventory_role_consumables WHERE role_id=?',
                (owner.id,)).fetchone()[0]
            level_request=db.execute('SELECT request_id FROM role_growth_receipts WHERE role_id=? ORDER BY rowid LIMIT 1',
                (owner.id,)).fetchone()[0]
        bag=await owner.io(owner.inventory.snapshot)
        replay=await owner.mailbox.call('receive',USE_ITEM,struct.pack('>iiQ',medicine,0,owner.id),request_id=medicine_request)
        assert role_values(replay)[60]==full.hp and await owner.io(owner.inventory.snapshot)==bag
        replay=await owner.mailbox.call('receive',C_REQ_LEVEL_UP,bytes(4),request_id=level_request)
        assert role_values(replay)[60]==full.hp and resources(store,owner)==full
        # Final encoding must happen before the actual gear/source/receipt commit.
        with patch.object(runtime_storage,'growth_refresh',side_effect=ValueError('controlled migrated final encoding')):
            assert await peer.request(UNEQUIP_ITEM,struct.pack('>ii',weapon,-1))==[]
        assert resources(store,owner)==full and await owner.io(owner.inventory.snapshot)==bag
        await peer.request(UNEQUIP_ITEM,struct.pack('>ii',weapon,-1))
        bare=resources(store,owner)
        assert (bare.hp,bare.mp,bare.version)==(full.hp,full.mp,full.version)
        await peer.request(EQUIP_ITEM,struct.pack('>ii',weapon,0))
        assert resources(store,owner).version==full.version
        carried=next(i for i in (await owner.io(owner.inventory.snapshot))['items'] if i['id']==medicine)
        await peer.request(MOVE_ITEM,struct.pack('>6iq',1,medicine,carried['slot'],1,9,0,0))
        assert next(i for i in (await owner.io(owner.inventory.snapshot))['items'] if i['id']==medicine)['slot']==9
        # The actual source-only move cannot leave drift or heal on a read.
        after=resources(store,owner)
        assert (after.hp,after.mp,after.version)==(full.hp,full.mp,full.version)
        profile=await owner.io(runtime_storage.role_load_profile,store,1111,owner.id,owner.epoch)
        assert profile.attributes.vitals.hp==full.hp
        await peer.connection.close();peer=GrowthPeer(rt);await peer.login(a)
        owner=rt.roles[a['id']]
        assert resources(store,owner).hp==full.hp
        other=GrowthPeer(rt);await other.login(b)
        service=await other.request(0xc232b,struct.pack('>qi',key,3))
        assert role_values(service)[60]==500 and role_values(service)[70]==1000
        await other.connection.close();await peer.connection.close()
        # New-role activation remains off even though rules are injected.
        fresh=store.create_role(1111,'资源未自动转交',11,1010109)
        fresh_peer=GrowthPeer(rt);await fresh_peer.login(fresh)
        with closing(store.connect()) as db:
            assert db.execute('SELECT 1 FROM role_resource_profiles WHERE role_id=?',(fresh['id'],)).fetchone() is None
        await fresh_peer.connection.close()
    finally:await rt.close()


def main():
    with tempfile.TemporaryDirectory(prefix='resource-owner-') as folder:
        store=AccountStore(Path(folder)/'state.sqlite3')
        a=store.create_role(1111,'资源接线甲',11,1010109);b=store.create_role(1111,'资源接线乙',11,1010109)
        prepared=runtime_storage.prepare(store)
        npc=next(p for ps in store.npc_resources[0].values() for p in ps if p.npc_id==10157)
        items=fixture(store,a,npc);fixture(store,b,npc)
        asyncio.run(check(store,prepared,a,b,npc,items))
    result=dict(passed=['migrated resource login preserves known wounds and current weapon totals',
        'manual growth/allocation, actual medicine, both native inn routes use the new contract',
        'paid medicine/level replay reads current healed resources without repeat debit',
        'late final encoding failure rolls back gear/source/receipts; generic inventory cannot commit source drift',
        'unequip/equip preserve resource amounts and no-op resource version, reconnect does not heal',
        'fresh creation still does not auto-activate resource migration'],database='disposable',
        fixture='explicit known legacy resources/XP/gear/wounds and NPC position, not natural quests',
        native_gui_verified=False,live_server_changed=False,battle_executed=False)
    write_json(OUT/'evidence/resource-owner-runtime-verification.json',result);print(result)


if __name__=='__main__':main()
