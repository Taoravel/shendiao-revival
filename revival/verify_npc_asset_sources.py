"""NPC self-owned transactions synchronize unique resources before commit.

Actual domain methods, map proofs and root source helper. No shared dispatcher,
client GUI, live store or automatic resource profile activation is substituted.
"""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
import struct
import tempfile
import time
from accounts import AccountStore
from inventory import Inventory,AssetChange,MOVE_ITEM,QUERY_BAG
from role_growth import initialize_growth,read_growth
from role_attribute_storage import initialize_attribute_baseline
from role_attributes import AttributeBaseline
from item_effects import VitalState
from role_equipment import EquipmentAttributeBasis,resource_caps_from_projection
from role_equipment_storage import (initialize_equipment_attribute_basis,current_equipment_totals,
    current_resource_profile,synchronize_inventory_resource_source)
from role_resource_plan import load_resource_rules
from role_resource_storage import migrate_role_resources,read_role_resources
from role_attribute_protocol import growth_refresh
from currency import initialize_wallet,read_wallet
from world_owner import MapAddress,Location
from world_npcs import NpcScene
from inspect_client import OUT,write_json
import runtime_storage
import npc_gameplay
import npc_shop_sales
import npc_depot
import npc_recovery


def main():
    rules=load_resource_rules()
    with tempfile.TemporaryDirectory() as temp:
        store=AccountStore(Path(temp)/'npc-sources.sqlite3')
        role=store.create_role(1111,'商店资源来源',11,1010109)
        late_role=store.create_role(1111,'宠物编码回滚',11,1010109)
        with closing(store.connect()) as db,db:
            db.execute('UPDATE roles SET level=21 WHERE id=?',(late_role['id'],))
        prepared=runtime_storage.prepare(store)
        gear=store.equipment_attribute_rules;epoch=store.acquire_lease(1111,role['id'])
        inv=Inventory(store.leased(1111,role['id'],epoch),1111,role['id'])
        with closing(inv.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            growth=initialize_growth(db,1111,inv.role_id,epoch,store.growth_rules,expected_level=1,free_points=0)
            p=store.attribute_rules.initial_profile
            before=initialize_attribute_baseline(db,1111,inv.role_id,epoch,p.baseline(inv.role_id),growth,
                store.attribute_rules,replace(p.vitals(inv.role_id),hp=70,mp=40)).vitals
            initialize_equipment_attribute_basis(db,1111,inv.role_id,epoch,
                EquipmentAttributeBasis(inv.role_id,9,0,gear.revision,11,'explicit-NPC-source-fixture'),gear)
            initialize_wallet(db,1111,inv.role_id,epoch,(10000,0,0,0),'explicit_migration',store.currency_rules)
            inv.apply_settlement(db,AssetChange('known-NPC-weapon',grants=((49009,1,1),),pets=(500001,)))
            key=inv.immutable_snapshot_transaction(db).items[0].id
            inv.equip_transaction(db,key,0,epoch,'known-NPC-equip')
            pet=inv.immutable_snapshot_transaction(db).pets[0]
            inv.change_pet_growth(db,pet.id,'known-pet-damage',pet.progress.state.version,'resources',(0,0))
            inv.change_pet_care(db,pet.id,'known-pet-defeat',pet.care.version,'defeat',1)
            totals=current_equipment_totals(db,1111,inv.role_id,epoch,inv.immutable_snapshot_transaction(db),gear)
            migrate_role_resources(db,1111,inv.role_id,epoch,before,resource_caps_from_projection(totals),
                origin='explicit_migration',migration_id='explicit-NPC-source',rules=rules,equipment_rules=gear)
        def command(npc_id,service_id,identity,*,inventory=None):
            owner=inv if inventory is None else inventory
            p=next(p for ps in store.npc_resources[0].values() for p in ps if p.npc_id==npc_id)
            address=MapAddress(p.map_id,p.map_id,0);loc=Location(owner.role_id,owner.epoch,address,1,p.x,p.y)
            scene=NpcScene(address,(p,),prepared[3],interaction_radius=32,binding_capacity=1)
            key=(p.map_id<<32)|p.placement_id;scene.bind(key,p.placement_id)
            now=int(time.monotonic()*1000)
            proof=scene.interact(struct.pack('>q',key),loc,loc,request_id=identity,now_ms=now,deadline_ms=now+10000)
            return store.npc_gameplay.services.plan(struct.pack('>qi',key,service_id),proof,loc,
                request_id=identity,now_ms=now,deadline_ms=now+10000)
        observations=[]
        def hook(identity,*,fail=False):
            def precommit(db,inventory,snapshot,*,replayed):
                assert db.in_transaction and type(replayed) is bool
                observations.append((identity,replayed))
                resources=synchronize_inventory_resource_source(db,1111,inv.role_id,epoch,snapshot,identity,
                    resource_rules=rules,equipment_rules=gear,replayed=replayed)
                assert resources is not None and (resources.hp,resources.mp,resources.version)==(70,40,0)
                assert resources.caps.source.inventory_revision==snapshot.inventory_revision
                profile=current_resource_profile(db,1111,inv.role_id,epoch,snapshot,equipment_rules=gear,resource_rules=rules)
                encoded=growth_refresh(read_growth(db,1111,inv.role_id),profile)
                if fail:raise ValueError('Controlled failure after real source CAS and native encoding')
                return (encoded,)
            return precommit
        def state(*,require_current=True,inventory=None):
            owner=inv if inventory is None else inventory
            with closing(owner.accounts.connect()) as db:
                db.execute('BEGIN')
                snapshot=owner.immutable_snapshot_transaction(db)
                resources=read_role_resources(db,1111,owner.role_id,owner.epoch,rules)
                if require_current:assert resources.caps.source.inventory_revision==snapshot.inventory_revision
                audit=tuple((table,tuple(db.execute('SELECT * FROM '+table+' WHERE role_id=? ORDER BY rowid',
                    (owner.role_id,)).fetchall())) for table in ('role_resource_receipts','role_wallet_receipts',
                    'npc_command_receipts','npc_buyback_items','npc_shop_journal','npc_depot_items',
                    'inventory_settlements','inventory_pet_growth_receipts','inventory_pet_care_receipts',
                    'npc_recovery_receipts'))
                return snapshot,resources,read_wallet(db,1111,owner.role_id,owner.epoch,store.currency_rules),audit
        def refused(action,*,message=None):
            try:action()
            except ValueError as error:
                if message is not None:assert str(error)==message
                return
            raise AssertionError('Unsafe transaction accepted')
        service=command(10157,2,'purchase-once')
        purchase=npc_gameplay.Purchase(service,32000,2,150)
        messages=npc_gameplay.purchase(store,inv,purchase,hook(service.request_id))
        assert any(k==0xc32c8 for k,b in messages)
        bought=state();assert bought[2][0].balance==9700
        assert observations==[('purchase-once',False)]
        npc_gameplay.purchase(store,inv,purchase,hook(service.request_id))
        assert state()==bought and observations[-1]==('purchase-once',True)
        food=next(i for i in bought[0].items if i.template_id==32000)
        sale_service=command(10011,214,'sell-once')
        sale=npc_shop_sales.SaleIntent(sale_service,'sell',(food.id,))
        npc_shop_sales.settle(store,inv,sale,hook(sale_service.request_id))
        # Original citemsell32000 sellprice75 (distinct from shop buyprice150).
        sold=state();assert sold[2][0].balance==9700 and sold[2][1].balance==150
        assert not any(i.id==food.id for i in sold[0].items)
        npc_shop_sales.settle(store,inv,sale,hook(sale_service.request_id))
        assert state()==sold and observations[-1]==('sell-once',True)
        buy_service=command(10011,214,'buyback-once')
        buyback=npc_shop_sales.SaleIntent(buy_service,'buyback',(food.id,))
        npc_shop_sales.settle(store,inv,buyback,hook(buy_service.request_id))
        bought_back=state();assert bought_back[2][0].balance==9550 and bought_back[2][1].balance==150
        assert next(i for i in bought_back[0].items if i.id==food.id)==food
        npc_shop_sales.settle(store,inv,buyback,hook(buy_service.request_id))
        assert state()==bought_back and observations[-1]==('buyback-once',True)
        npc_gameplay.initialize_depot(inv,98765,'explicit_migration')
        put_service=command(10003,6,'depot-put')
        put=struct.pack('>6iq',1,food.id,food.slot,2,0,0,0)
        npc_gameplay.depot_operation(store,inv,put_service,MOVE_ITEM,put,hook(put_service.request_id))
        stored=state();assert not any(i.id==food.id for i in stored[0].items)
        npc_gameplay.depot_operation(store,inv,put_service,MOVE_ITEM,put,hook(put_service.request_id))
        assert state()==stored and observations[-1]==('depot-put',True)
        take_service=command(10003,6,'depot-take')
        take=struct.pack('>6iq',2,food.id,0,1,food.slot,0,0)
        npc_gameplay.depot_operation(store,inv,take_service,MOVE_ITEM,take,hook(take_service.request_id))
        withdrawn=state();assert next(i for i in withdrawn[0].items if i.id==food.id)==food
        def forbidden_read_hook(*args,**kwargs):raise AssertionError('Read/cash warehouse path invoked inventory mutation hook')
        read_service=command(10003,6,'depot-read')
        assert npc_gameplay.depot_operation(store,inv,read_service,QUERY_BAG,
            struct.pack('>iQ',2,0),forbidden_read_hook)
        assert state()==withdrawn
        # A failure after real source CAS and real native encoding must undo the
        # whole caller transaction. Then the identical accepted command succeeds.
        def rollback_retry(action,identity):
            before=state()
            refused(lambda:action(hook(identity,fail=True)))
            assert state()==before
            action(hook(identity))
            after=state();assert after!=before
            action(hook(identity))
            assert state()==after and observations[-1]==(identity,True)
        late_buy_service=command(10157,2,'purchase-late')
        late_purchase=npc_gameplay.Purchase(late_buy_service,32000,1,150)
        rollback_retry(lambda cb:npc_gameplay.purchase(store,inv,late_purchase,cb),'purchase-late')
        food=next(i for i in state()[0].items if i.template_id==32000)
        late_sale_service=command(10011,214,'sale-late')
        late_sale=npc_shop_sales.SaleIntent(late_sale_service,'sell',(food.id,))
        rollback_retry(lambda cb:npc_shop_sales.settle(store,inv,late_sale,cb),'sale-late')
        late_back_service=command(10011,214,'buyback-late')
        late_back=npc_shop_sales.SaleIntent(late_back_service,'buyback',(food.id,))
        rollback_retry(lambda cb:npc_shop_sales.settle(store,inv,late_back,cb),'buyback-late')
        put_late=command(10003,6,'put-late');take_late=command(10003,6,'take-late')
        rollback_retry(lambda cb:npc_gameplay.depot_operation(store,inv,put_late,MOVE_ITEM,put,cb),'put-late')
        rollback_retry(lambda cb:npc_gameplay.depot_operation(store,inv,take_late,MOVE_ITEM,take,cb),'take-late')
        mutable_service=command(10157,2,'mutable-messages')
        mutable_purchase=npc_gameplay.Purchase(mutable_service,32000,1,150)
        def mutable_hook(*args,**kwargs):return list(hook('mutable-messages')(*args,**kwargs))
        before=state()
        refused(lambda:npc_gameplay.purchase(store,inv,mutable_purchase,mutable_hook))
        assert state()==before
        # Real pet care changes the shared inventory revision. It must advance
        # only the character's source, never copy pet HP into character vitals.
        for kind,expected_loyalty in ((2,80),(3,100)):
            pet_service=command(10086,npc_recovery.SERVICES[kind],f'pet-kind{kind}')
            care=npc_recovery.RecoveryIntent(pet_service,kind);before=state()
            messages=npc_recovery.settle(store,inv,care,resource_rules=rules,equipment_rules=gear)
            after=state();pet=after[0].pets[0]
            assert pet.care.loyalty==expected_loyalty and pet.care.lifetime==5950
            assert (pet.progress.state.hp,pet.progress.state.mp)==(pet.progress.attributes.max_hp,pet.progress.attributes.max_mp)
            assert (after[1].hp,after[1].mp,after[1].version)==(70,40,0)
            assert after[1].caps.source.inventory_revision>before[1].caps.source.inventory_revision
            assert any(k==0xc32c8 for k,b in messages)
            npc_recovery.settle(store,inv,care,resource_rules=rules,equipment_rules=gear)
            assert state()==after
        with closing(inv.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');pet=inv.immutable_snapshot_transaction(db).pets[0]
            inv.change_pet_growth(db,pet.id,'later-pet-damage',pet.progress.state.version,'resources',(0,0))
            inv.change_pet_care(db,pet.id,'later-pet-defeat',pet.care.version,'defeat',1)
            synchronize_inventory_resource_source(db,1111,inv.role_id,epoch,inv.immutable_snapshot_transaction(db),
                'later-pet-fixture',resource_rules=rules,equipment_rules=gear,replayed=False)
        combined=npc_recovery.RecoveryIntent(command(10086,12,'pet-kind4'),4)
        npc_recovery.settle(store,inv,combined,resource_rules=rules,equipment_rules=gear)
        after=state();pet=after[0].pets[0]
        assert (pet.care.loyalty,pet.care.lifetime)==(100,5900)
        assert (pet.progress.state.hp,pet.progress.state.mp)==(pet.progress.attributes.max_hp,pet.progress.attributes.max_mp)
        assert (after[1].hp,after[1].mp,after[1].version)==(70,40,0)
        npc_recovery.settle(store,inv,combined,resource_rules=rules,equipment_rules=gear)
        assert state()==after
        # Actual acquire_lease invalidates old inventory access; an equivalent
        # command with a newly proved map visit reads current paid state only.
        previous=inv;epoch=store.acquire_lease(1111,inv.role_id)
        inv=Inventory(store.leased(1111,inv.role_id,epoch),1111,inv.role_id)
        current=state()
        refused(lambda:npc_gameplay.purchase(store,previous,purchase,hook('purchase-once')))
        purchase=npc_gameplay.Purchase(command(10157,2,'purchase-once'),32000,2,150)
        npc_gameplay.purchase(store,inv,purchase,hook('purchase-once'))
        assert state()==current
        combined=npc_recovery.RecoveryIntent(command(10086,12,'pet-kind4'),4)
        npc_recovery.settle(store,inv,combined,resource_rules=rules,equipment_rules=gear)
        assert state()==current
        # Real final growth_refresh fails after pet care, fee and source writes.
        # The fixture is known level21 so this also exercises a nonzero fee.
        late_epoch=store.acquire_lease(1111,late_role['id'])
        late_inv=Inventory(store.leased(1111,late_role['id'],late_epoch),1111,late_role['id'])
        with closing(late_inv.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            growth=initialize_growth(db,1111,late_inv.role_id,late_epoch,store.growth_rules,expected_level=21,free_points=0)
            baseline=AttributeBaseline(late_inv.role_id,21,0,(10,10,10,10,10),
                (500,1000,20,5,16777217,20,10,20,5))
            vitals=initialize_attribute_baseline(db,1111,late_inv.role_id,late_epoch,baseline,growth,
                store.attribute_rules,VitalState(late_inv.role_id,0,70,500,40,1000)).vitals
            initialize_equipment_attribute_basis(db,1111,late_inv.role_id,late_epoch,
                EquipmentAttributeBasis(late_inv.role_id,9,0,gear.revision,11,'explicit-pet-native-failure'),gear)
            initialize_wallet(db,1111,late_inv.role_id,late_epoch,(2000,0,0,0),'explicit_migration',store.currency_rules)
            late_inv.apply_settlement(db,AssetChange('known-late-pet',pets=(500001,)))
            pet=late_inv.immutable_snapshot_transaction(db).pets[0]
            late_inv.change_pet_growth(db,pet.id,'known-late-damage',pet.progress.state.version,'resources',(0,0))
            late_inv.change_pet_care(db,pet.id,'known-late-defeat',pet.care.version,'defeat',1)
            totals=current_equipment_totals(db,1111,late_inv.role_id,late_epoch,late_inv.immutable_snapshot_transaction(db),gear)
            migrate_role_resources(db,1111,late_inv.role_id,late_epoch,vitals,resource_caps_from_projection(totals),
                origin='explicit_migration',migration_id='explicit-late-pet-profile',rules=rules,equipment_rules=gear)
        late_care=npc_recovery.RecoveryIntent(command(10086,12,'pet-late-native',inventory=late_inv),4)
        late_before=state(inventory=late_inv)
        refused(lambda:npc_recovery.settle(store,late_inv,late_care,resource_rules=rules,equipment_rules=gear),
            message='Ordinary role attribute is not exactly representable by native float')
        assert state(inventory=late_inv)==late_before and late_before[2][0].balance==2000
        # Deliberately corrupt provenance in this disposable fixture. Historical
        # paid requests may NOT silently repair unrelated later asset changes.
        with closing(inv.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            inv.apply_settlement(db,AssetChange('unrelated-pending-source',grants=((32000,1,0),)))
        pending=state(require_current=False)
        assert pending[1].caps.source.inventory_revision<pending[0].inventory_revision
        late_sale=npc_shop_sales.SaleIntent(command(10011,214,'sale-late'),'sell',(food.id,))
        put_late=command(10003,6,'put-late')
        refused(lambda:npc_gameplay.purchase(store,inv,purchase,hook(service.request_id)))
        refused(lambda:npc_shop_sales.settle(store,inv,late_sale,hook('sale-late')))
        refused(lambda:npc_gameplay.depot_operation(store,inv,put_late,MOVE_ITEM,put,hook('put-late')))
        refused(lambda:npc_recovery.settle(store,inv,combined,resource_rules=rules,equipment_rules=gear))
        assert state(require_current=False)==pending
        report={'passed':['actual purchase syncs root unique resource source in caller transaction',
            'HP70/MP40/version0 retained while inventory source advances; current full map encoded',
            'domain-paid purchase replay explicitly passesTrue and only reads current profile',
            'actual sale/buyback synchronize same source, preserve instances and use real replay decisions',
            'depot put/take join actual source CAS, duplicate put is readonly, ordinary query skips mutation hook',
            'late source-CAS/native-encoding failure rolls purchase/sell/buyback/depot put/take and all receipts back; same request then succeeds',
            'mutable precommit result refuses and rolls actual purchase/source/fee/receipts back',
            'pet kinds2/3/4 synchronize only character source, preserving HP70/MP40/version0; current native map and readonly replays',
            'actual new lease refuses stale purchase owner; freshly proved paid purchase/pet replay preserves all current state',
            'real float32 hit16777217 native encoding failure rolls level21 pet care/nonzero fee/source/all receipts back',
            'paid purchase/sale/depot/pet replays reject unrelated pending source without repairing it'],
            'shared_wire_route_verified':False,'automatic_profile_activation':False,
            'native_gui_verified':False,'live_database_modified':False}
    write_json(OUT/'evidence/npc-asset-sources.json',report);print(report)


if __name__=='__main__':main()
