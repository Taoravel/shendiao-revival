"""Current equipped totals through real growth owners, controlled legacy fixture.

Independent of natural master verification: this explicitly supplies known L10
growth, wounds, sealing basis, XP and one weapon in a disposable database.
"""
import asyncio
from contextlib import closing
from pathlib import Path
import struct
import tempfile
from unittest.mock import patch
from accounts import AccountStore
from currency import initialize_wallet
from game_runtime import GameRuntime
from inventory import Inventory,AssetChange,EQUIP_ITEM,UNEQUIP_ITEM
from item_effects import VitalState
from role_attributes import AttributeBaseline
from role_attribute_storage import initialize_attribute_baseline
from role_equipment import EquipmentAttributeBasis
from role_equipment_storage import initialize_equipment_attribute_basis
from role_growth import initialize_growth
from role_growth_protocol import C_REQ_LEVEL_UP,C_ADD_POINT_TO_ATTR
from verify_growth_runtime import GrowthPeer,role_values
from inspect_client import OUT,write_json
import runtime_storage


def totals(frames):
    values=role_values(frames)
    return tuple(values[k] for k in (80,810,1230))


async def check(store,prepared,role,key):
    runtime=GameRuntime(store,prepared)
    try:
        peer=GrowthPeer(runtime);await peer.login(role)
        assert totals(peer.initial)==(45,35,8)
        raised=await peer.request(C_REQ_LEVEL_UP,bytes(4))
        assert totals(raised)==(49,38,8)
        allocated=await peer.request(C_ADD_POINT_TO_ATTR,struct.pack('>5i',0,0,1,0,0))
        assert totals(allocated)==(51,39,8), role_values(allocated)
        assert role_values(allocated)[500]==4
        unequipped=await peer.request(UNEQUIP_ITEM,struct.pack('>ii',key,-1))
        assert totals(unequipped)==(26,24,0)
        with closing(store.connect()) as db:
            before=db.execute('SELECT equipment_slot FROM inventory_items WHERE id=?',(key,)).fetchone()
            receipts=db.execute('SELECT count(*) FROM inventory_equipment_commands').fetchone()
        # Fail the actual final encoder after the inventory mutation; neither
        # equipment nor its command receipt may escape the outer transaction.
        with patch.object(runtime_storage,'growth_refresh',side_effect=ValueError('controlled native display failure')):
            assert await peer.request(EQUIP_ITEM,struct.pack('>ii',key,0))==[]
        with closing(store.connect()) as db:
            assert db.execute('SELECT equipment_slot FROM inventory_items WHERE id=?',(key,)).fetchone()==before
            assert db.execute('SELECT count(*) FROM inventory_equipment_commands').fetchone()==receipts
        assert totals(await peer.request(EQUIP_ITEM,struct.pack('>ii',key,0)))==(51,39,8)
        await peer.connection.close()
        peer=GrowthPeer(runtime);await peer.login(role)
        assert totals(peer.initial)==(51,39,8)
        await peer.connection.close()
    finally:await runtime.close()


def main():
    with tempfile.TemporaryDirectory(prefix='equipped-growth-') as folder:
        store=AccountStore(Path(folder)/'state.sqlite3')
        role=store.create_role(1111,'装备成长',11,1010109)
        prepared=runtime_storage.prepare(store)
        epoch=store.acquire_lease(1111,role['id'])
        inventory=Inventory(store.leased(1111,role['id'],epoch),1111,role['id'])
        with closing(inventory.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('UPDATE roles SET level=10 WHERE id=?',(role['id'],))
            db.execute('INSERT INTO role_progress VALUES(?,?)',(role['id'],store.growth_rules.costs[10]))
            growth=initialize_growth(db,1111,role['id'],epoch,store.growth_rules,expected_level=10,free_points=0)
            initialize_attribute_baseline(db,1111,role['id'],epoch,
                AttributeBaseline(role['id'],10,0,(10,10,10,10,10),(100,100,20,5,40,20,10,20,5)),
                growth,store.attribute_rules,VitalState(role['id'],0,70,100,40,100))
            rules=store.equipment_attribute_rules
            initialize_equipment_attribute_basis(db,1111,role['id'],epoch,
                EquipmentAttributeBasis(role['id'],9,0,rules.revision,0,'controlled-known-legacy-sealing'),rules)
            initialize_wallet(db,1111,role['id'],epoch,(0,0,0,0),'explicit_migration',store.currency_rules)
            inventory.apply_settlement(db,AssetChange('controlled-weapon',grants=((49009,1,1),)))
            key=inventory.immutable_snapshot_transaction(db).items[0].id
            inventory.equip_transaction(db,key,0,epoch,'controlled-initial-equip')
        asyncio.run(check(store,prepared,role,key))
    result=dict(passed=['equipped login45/35/8 -> manual level49/38/8 -> strength allocation51/39/8',
        'unequip restores current26/24/0, re-equip and reconnect restore current51/39/8',
        'final native encoding failure rolls back actual equip and command receipt'],
        fixture='controlled known legacy growth/XP/gear/basis; not a natural creation test',
        database='disposable',native_gui_verified=False,live_server_changed=False,battle_executed=False)
    write_json(OUT/'evidence/equipped-growth-runtime-verification.json',result)
    print(result)


if __name__=='__main__':main()
