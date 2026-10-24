"""Bound purchase: real resource source CAS, late rollback and legacy receipt."""
from contextlib import closing
from dataclasses import replace
import hashlib
import importlib.util
from pathlib import Path
import struct
import sys
import tempfile
import time
from accounts import AccountStore
from currency import initialize_wallet,read_wallet
from inventory import Inventory,AssetChange
from inspect_client import OUT,ROOT,write_json
from role_growth import initialize_growth,read_growth
from role_attribute_storage import initialize_attribute_baseline
from role_attribute_protocol import growth_refresh
from role_equipment import EquipmentAttributeBasis,resource_caps_from_projection
from role_equipment_storage import (initialize_equipment_attribute_basis,current_equipment_totals,
    current_resource_profile,synchronize_inventory_resource_source)
from role_resource_storage import migrate_role_resources,read_role_resources
from world_npcs import NpcScene
from world_owner import MapAddress,Location
import npc_gameplay
import runtime_storage


def main():
    with tempfile.TemporaryDirectory() as temp:
        store=AccountStore(Path(temp)/'bound-sources.sqlite3')
        role=store.create_role(1111,'绑银资源来源',11,1010109)
        prepared=runtime_storage.prepare(store)
        epoch=store.acquire_lease(1111,role['id'])
        inv=Inventory(store.leased(1111,role['id'],epoch),1111,role['id'])
        gear=store.equipment_attribute_rules;rules=store.resource_rules
        with closing(inv.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            growth=initialize_growth(db,1111,inv.role_id,epoch,store.growth_rules,expected_level=1,free_points=0)
            profile=store.attribute_rules.initial_profile
            before=initialize_attribute_baseline(db,1111,inv.role_id,epoch,profile.baseline(inv.role_id),growth,
                store.attribute_rules,replace(profile.vitals(inv.role_id),hp=70,mp=40)).vitals
            initialize_equipment_attribute_basis(db,1111,inv.role_id,epoch,
                EquipmentAttributeBasis(inv.role_id,9,0,gear.revision,11,'explicit-bound-shop-fixture'),gear)
            initialize_wallet(db,1111,inv.role_id,epoch,(1000,1000,0,0),'explicit_migration',store.currency_rules)
            totals=current_equipment_totals(db,1111,inv.role_id,epoch,inv.immutable_snapshot_transaction(db),gear)
            migrate_role_resources(db,1111,inv.role_id,epoch,before,resource_caps_from_projection(totals),
                origin='explicit_migration',migration_id='bound-shop-baseline',rules=rules,equipment_rules=gear)
        npc=next(p for ps in store.npc_resources[0].values() for p in ps if p.npc_id==10157)
        address=MapAddress(npc.map_id,npc.map_id,0)
        location=Location(inv.role_id,epoch,address,1,npc.x,npc.y)
        scene=NpcScene(address,(npc,),prepared[3],interaction_radius=32,binding_capacity=1)
        key=(npc.map_id<<32)|npc.placement_id;scene.bind(key,npc.placement_id)
        def intent(identity,mode=1,quantity=1):
            now=int(time.monotonic()*1000)
            proof=scene.interact(struct.pack('>q',key),location,location,
                request_id=identity,deadline_ms=now+10000,now_ms=now)
            return npc_gameplay.plan_purchase(store.npc_gameplay,struct.pack('>qiii',key,32000,quantity,mode),
                proof,location,request_id=identity,now_ms=now,deadline_ms=now+10000)
        def state():
            with closing(inv.accounts.connect()) as db,db:
                db.execute('BEGIN')
                snapshot=inv.immutable_snapshot_transaction(db)
                resources=read_role_resources(db,1111,inv.role_id,epoch,rules)
                assert resources.caps.source.inventory_revision==snapshot.inventory_revision
                audit=tuple((table,tuple(db.execute('SELECT * FROM '+table+' WHERE role_id=? ORDER BY rowid',
                    (inv.role_id,)))) for table in ('role_resource_receipts','role_wallet_receipts',
                    'npc_command_receipts','inventory_settlements'))
                return snapshot,resources,read_wallet(db,1111,inv.role_id,epoch,store.currency_rules),audit
        late=intent('bound-shop-late')
        baseline=state()
        def fail_after_source(db,inventory,snapshot,*,replayed):
            updated=synchronize_inventory_resource_source(db,1111,inv.role_id,epoch,snapshot,
                late.service.request_id,resource_rules=rules,equipment_rules=gear,replayed=replayed)
            assert updated.caps.source.inventory_revision==snapshot.inventory_revision
            assert (updated.hp,updated.mp,updated.version)==(70,40,0)
            projected=current_resource_profile(db,1111,inv.role_id,epoch,snapshot,
                equipment_rules=gear,resource_rules=rules)
            assert growth_refresh(read_growth(db,1111,inv.role_id),projected)
            raise ValueError('Controlled late failure after actual source CAS and native projection')
        try:npc_gameplay.purchase(store,inv,late,fail_after_source)
        except ValueError as error:
            assert str(error)=='Controlled late failure after actual source CAS and native projection'
        else:raise AssertionError('Late bound purchase failure committed')
        assert state()==baseline
        runtime_storage.npc_asset_operation(store,inv,late,npc_gameplay.purchase)
        paid=state()
        assert (paid[1].hp,paid[1].mp,paid[1].version)==(70,40,0)
        assert {r.currency:r.balance for r in paid[2]}=={
            'cash':1000,'bound_silver':850,'yuanbao':0,'bound_yuanbao':0}
        assert [(i.template_id,i.quantity,i.binding) for i in paid[0].items]==[(32000,1,1)]
        runtime_storage.npc_asset_operation(store,inv,late,npc_gameplay.purchase)
        assert state()==paid
        # Execute the actual previously deployed mode0 transaction, then replay
        # its persisted receipt through the new implementation on the same DB.
        path=ROOT/'revival/runtime/deployments/npc-20261023T102110Z/source/npc_gameplay.py'
        assert hashlib.sha256(path.read_bytes()).hexdigest()==(
            'ea920c4afd61ef5d9a649bee52b4c549db9c9373db5fbeb2dcf40af1e3b90f91')
        spec=importlib.util.spec_from_file_location('old_npc_shop_receipt',path)
        old=importlib.util.module_from_spec(spec);sys.modules[spec.name]=old;spec.loader.exec_module(old)
        legacy=intent('legacy-mode0-paid',0)
        current_resources=store.npc_gameplay
        old.prepare(store)
        try:
            old_intent=old.Purchase(legacy.service,legacy.item_id,legacy.quantity,legacy.unit_price)
            runtime_storage.npc_asset_operation(store,inv,old_intent,old.purchase)
        finally:store.npc_gameplay=current_resources
        historical=state()
        runtime_storage.npc_asset_operation(store,inv,legacy,npc_gameplay.purchase)
        assert state()==historical, 'Existing mode0 paid fingerprint was changed'
        assert sorted((i.binding,i.quantity) for i in historical[0].items)==[(0,1),(1,1)]
        try:runtime_storage.npc_asset_operation(store,inv,replace(legacy,mode=1),npc_gameplay.purchase)
        except ValueError:pass
        else:raise AssertionError('Legacy cash receipt was reused as bound payment')
        assert state()==historical
        store.npc_gameplay=replace(current_resources,
            payments=replace(current_resources.payments,revision='different-reviewed-payment-policy'))
        try:
            runtime_storage.npc_asset_operation(store,inv,legacy,npc_gameplay.purchase)
            assert state()==historical
            try:runtime_storage.npc_asset_operation(store,inv,late,npc_gameplay.purchase)
            except ValueError:pass
            else:raise AssertionError('Mode1 receipt ignored a changed payment policy')
            assert state()==historical
        finally:store.npc_gameplay=current_resources
        with closing(inv.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            inv.apply_settlement(db,AssetChange('bound-full-bag-fixture',grants=((32000,998,1),(40200,38))))
            synchronize_inventory_resource_source(db,1111,inv.role_id,epoch,inv.immutable_snapshot_transaction(db),
                'bound-full-bag-fixture',resource_rules=rules,equipment_rules=gear,replayed=False)
        full=state()
        assert len(full[0].items)==40
        try:runtime_storage.npc_asset_operation(store,inv,intent('bound-bag-full'),npc_gameplay.purchase)
        except ValueError as error:assert str(error)=='Bag full'
        else:raise AssertionError('A new bound stack was admitted into a full bag')
        assert state()==full, 'Grant failure left a bound debit or payment/source receipt'
    report={'passed':['bound wallet, binding1 item, source CAS and all receipts roll back after real late projection',
        'same failed identity retries successfully once; paid replay preserves current source and HP70/MP40/version0',
        'actual deployed mode0 receipt replays byte-compatible in new implementation without mutation',
        'legacy cash receipt cannot be reused for mode1; bound and unbound stacks remain separate',
        'changed payment policy conflicts with mode1 receipts while legacy mode0 replay stays compatible',
        'actual full bag and full bound stack reject after payment and roll back bound wallet and receipts'],
        'npc_gameplay_source':str(Path(npc_gameplay.__file__).resolve()),
        'npc_gameplay_sha256':hashlib.sha256(Path(npc_gameplay.__file__).read_bytes()).hexdigest(),
        'legacy_module_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'native_gui_verified':False,'live_database_modified':False}
    write_json(OUT/'evidence/npc-bound-shop-sources.json',report);print(report)


if __name__=='__main__':main()
