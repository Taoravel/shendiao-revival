"""Real equipped repair and final projection share a caller precommit seam.

Only NPC/inventory/attribute startup dependencies are prepared; this does not
replace or claim to verify the shared runtime/organization startup route.
"""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
import struct
import tempfile
import time
from accounts import AccountStore
from inventory import Inventory,AssetChange
from currency import load_currency_rules,prepare_wallet_storage,initialize_wallet,read_wallet
from role_growth import load_growth_rules,prepare_growth_storage,initialize_growth,read_growth
from role_attributes import load_attribute_rules
from role_attribute_storage import prepare_attribute_storage,initialize_attribute_baseline
from role_attribute_protocol import growth_refresh
from role_equipment import EquipmentAttributeBasis,load_equipment_attribute_rules
from role_equipment_storage import (prepare_equipment_attribute_storage,
    initialize_equipment_attribute_basis,current_equipment_projection)
from world_owner import MapAddress,Location
from world_npcs import NpcScene,load_placements,load_npc_definitions
from world_catalog import maps
from inspect_client import OUT,write_json
import npc_gameplay
import npc_repairs


def main():
    with tempfile.TemporaryDirectory() as temp:
        store=AccountStore(Path(temp)/'repair-projection.sqlite3')
        role=store.create_role(1111,'修理属性',11,1010109)
        store.inventory_config=Inventory.prepare(store)
        store.currency_rules=load_currency_rules();store.growth_rules=load_growth_rules()
        store.attribute_rules=load_attribute_rules();gear_rules=load_equipment_attribute_rules()
        store.npc_resources=(load_placements(),load_npc_definitions());npc_gameplay.prepare(store)
        with closing(store.connect()) as db:
            prepare_wallet_storage(db);prepare_growth_storage(db);prepare_attribute_storage(db)
            prepare_equipment_attribute_storage(db)
        epoch=store.acquire_lease(1111,role['id']);inv=Inventory(store.leased(1111,role['id'],epoch),1111,role['id'])
        with closing(inv.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            initialize_wallet(db,1111,role['id'],epoch,(100000,0,0,0),'explicit_migration',store.currency_rules)
            growth=initialize_growth(db,1111,role['id'],epoch,store.growth_rules,expected_level=1,free_points=0)
            p=store.attribute_rules.initial_profile
            initialize_attribute_baseline(db,1111,role['id'],epoch,p.baseline(role['id']),growth,
                store.attribute_rules,replace(p.vitals(role['id']),hp=70,mp=40))
            initialize_equipment_attribute_basis(db,1111,role['id'],epoch,
                EquipmentAttributeBasis(role['id'],9,0,gear_rules.revision,11,'explicit-repair-fixture'),gear_rules)
            inv.apply_settlement(db,AssetChange('repair-fixture',grants=((49009,1,1),)))
            key=inv.immutable_snapshot_transaction(db).items[0].id
            inv.equip_transaction(db,key,0,epoch,'repair-equip')
            condition=inv.equipment_condition(db,key)
            inv.wear_equipment(db,key,'broken-fixture',condition.version,condition.current)
        npc=next(p for ps in store.npc_resources[0].values() for p in ps if p.npc_id==10004)
        address=MapAddress(npc.map_id,npc.map_id,0);location=Location(role['id'],epoch,address,1,npc.x,npc.y)
        scene=NpcScene(address,(npc,),maps(),interaction_radius=32,binding_capacity=1)
        npc_key=(npc.map_id<<32)|npc.placement_id;scene.bind(npc_key,npc.placement_id)
        now=int(time.monotonic()*1000)
        proof=scene.interact(struct.pack('>q',npc_key),location,location,
            request_id='same-repair',now_ms=now,deadline_ms=now+10000)
        intent=npc_repairs.plan(store.npc_gameplay,struct.pack('>iqii',2,npc_key,4,key),proof,location,
            request_id='same-repair',now_ms=now,deadline_ms=now+10000)
        def current():
            with closing(inv.accounts.connect()) as db:
                db.execute('BEGIN')
                state=inv.immutable_snapshot_transaction(db)
                return state,read_wallet(db,1111,role['id'],epoch,store.currency_rules),current_equipment_projection(
                    db,1111,role['id'],epoch,state,gear_rules)
        before=current();assert before[2].attributes.physical_attack<45
        calls=[]
        def project(db,inventory,state):
            assert db.in_transaction and state.items[0].condition.current>0
            final=current_equipment_projection(db,1111,role['id'],epoch,state,gear_rules)
            assert (final.attributes.physical_attack,final.attributes.magic_attack,final.seal_strength)==(45,35,19)
            assert (final.vitals.hp,final.vitals.mp)==(70,40)
            calls.append(state.inventory_revision)
            return (growth_refresh(read_growth(db,1111,role['id']),final),)
        def fail_after_encoding(db,inventory,state):
            project(db,inventory,state)
            raise ValueError('Controlled post-projection/precommit failure')
        try:npc_repairs.repair(store,inv,intent,fail_after_encoding,draw_source=lambda bound:0)
        except ValueError:pass
        else:raise AssertionError('Failed final projection committed repair')
        assert calls and current()==before
        result=npc_repairs.repair(store,inv,intent,project,draw_source=lambda bound:0)
        assert any(kind==0xc32c8 for kind,body in result)
        after=current();assert after[1][0].balance<before[1][0].balance
        def forbidden(bound):raise AssertionError('Committed repair redrew randomness')
        npc_repairs.repair(store,inv,intent,project,draw_source=forbidden)
        assert current()==after and len(calls)==3
        # Trusted fixture has an exactly representable naked seal baseline,
        # but its equipped total16777217 cannot cross the native float32 seam.
        with closing(inv.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM role_equipment_attribute_bases WHERE role_id=?',(role['id'],))
            initialize_equipment_attribute_basis(db,1111,role['id'],epoch,
                EquipmentAttributeBasis(role['id'],9,0,gear_rules.revision,16777209,'explicit-float-limit-fixture'),gear_rules)
            condition=inv.equipment_condition(db,key)
            inv.wear_equipment(db,key,'second-broken-fixture',condition.version,condition.current)
        before_float=current()
        fresh=replace(intent,service=replace(intent.service,request_id='float-refusal'))
        def encode_current(db,inventory,state):
            final=current_equipment_projection(db,1111,role['id'],epoch,state,gear_rules)
            assert final.seal_strength==16777217
            return (growth_refresh(read_growth(db,1111,role['id']),final),)
        try:npc_repairs.repair(store,inv,fresh,encode_current,draw_source=lambda bound:0)
        except ValueError as error:
            assert 'float' in str(error).lower(),str(error)
        else:raise AssertionError('Native inexact final equipment attribute committed repair')
        assert current()==before_float
        report={'passed':['equipped broken weapon repair restores same-transaction45/35/19 projection',
            'precommit real growth encoding uses current HP70/MP40',
            'post-projection failure rolls back condition/cash/repair and common receipts',
            'same aborted command succeeds later; committed retry projects current state without drawing again',
            'real native float32 encoding refusal for final seal16777217 rolls back repair and cash'],
            'shared_runtime_route_verified':False,'native_gui_verified':False,'live_database_modified':False}
    write_json(OUT/'evidence/npc-repair-projection.json',report);print(report)


if __name__=='__main__':main()
