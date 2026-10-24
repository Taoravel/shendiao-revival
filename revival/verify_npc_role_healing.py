"""Original doctor proof -> dedicated healing transaction and current replay."""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
import sqlite3
import struct
import tempfile
import time
from accounts import AccountStore
from currency import read_wallet,apply_currency,CurrencyChange
from inventory import Inventory,AssetChange
from inspect_client import OUT,write_json
from npc_services import load_services
from role_resource_plan import plan_combat_resources
from role_resource_storage import read_role_resources,apply_resource_transition,ResourceNotInitialized
from role_growth import read_growth,plan_growth_credit,apply_growth_plan,GrowthResourceContext
from role_equipment_storage import synchronize_inventory_resource_source
from verify_growth_runtime import role_values
from verify_npc_role_healing_runtime import known_profile
from world_npcs import NpcScene
from world_owner import MapAddress,Location
import npc_role_healing as healing
import runtime_storage


def main():
    with tempfile.TemporaryDirectory() as temp:
        store=AccountStore(Path(temp)/'healer-domain.sqlite3')
        roles={name:store.create_role(1111,name,11,1010109) for name in ('治疗已知','治疗晚错','治疗未知')}
        prepared=runtime_storage.prepare(store)
        services=load_services(healing.prepare(store))
        npc=next(p for ps in store.npc_resources[0].values() for p in ps if p.npc_id==10380)
        address=MapAddress(npc.map_id,npc.map_id,0);key=(npc.map_id<<32)|npc.placement_id
        scene=NpcScene(address,(npc,),prepared[3],interaction_radius=32,binding_capacity=1)
        scene.bind(key,npc.placement_id)
        def command(inv,identity):
            now=int(time.monotonic()*1000)
            current=Location(inv.role_id,inv.epoch,address,1,npc.x,npc.y)
            proof=scene.interact(struct.pack('>q',key),current,current,
                request_id=identity,deadline_ms=now+10000,now_ms=now)
            return services.plan(struct.pack('>qi',key,294),proof,current,
                request_id=identity,deadline_ms=now+10000,now_ms=now)
        def state(inv):
            with closing(inv.accounts.connect()) as db,db:
                db.execute('BEGIN')
                try:resources=read_role_resources(db,1111,inv.role_id,inv.epoch,store.resource_rules)
                except ResourceNotInitialized:resources=None
                snapshot=inv.immutable_snapshot_transaction(db)
                wallet=read_wallet(db,1111,inv.role_id,inv.epoch,store.currency_rules)
                audit=tuple((table,tuple(db.execute('SELECT * FROM '+table+' WHERE role_id=? ORDER BY rowid',
                    (inv.role_id,)))) for table in ('role_resource_receipts','role_wallet_receipts',
                    'npc_role_healing_receipts','npc_command_receipts'))
                return resources,snapshot,wallet,audit
        def refused(action):
            try:action()
            except ValueError:return
            raise AssertionError('Unauthorized or unsupported NPC role healing was accepted')
        def damage(inv,identity,hp,mp):
            with closing(inv.accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                before=read_role_resources(db,1111,inv.role_id,inv.epoch,store.resource_rules)
                transition=plan_combat_resources(before,hp,mp,store.resource_rules)
                apply_resource_transition(db,1111,inv.role_id,inv.epoch,transition,identity,
                    rules=store.resource_rules,equipment_rules=store.equipment_attribute_rules)
        inv=known_profile(store,roles['治疗已知']);once=command(inv,'heal-once')
        before=state(inv);values=role_values(healing.settle(store,inv,once));after=state(inv)
        assert (values[60],values[70],values[140],values[150])==(100,100,100,100)
        assert (after[0].hp,after[0].mp,after[0].version)==(100,100,1)
        assert after[0].caps==before[0].caps and after[1]==before[1]
        assert {r.currency:r.balance for r in after[2]}=={
            'cash':970,'bound_silver':500,'yuanbao':0,'bound_yuanbao':0}
        healing.settle(store,inv,once);assert state(inv)==after
        refused(lambda:healing.settle(store,inv,command(inv,'full-new-request')))
        assert state(inv)==after
        damage(inv,'later-trusted-damage',80,60);wounded=state(inv)
        replay=role_values(healing.settle(store,inv,once))
        assert (replay[60],replay[70])==(80,60) and state(inv)==wounded
        with closing(inv.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            growth=read_growth(db,1111,inv.role_id)
            plan=plan_growth_credit(growth,89,store.growth_rules)  # Original level1 cost89.
            apply_growth_plan(db,1111,inv.role_id,inv.epoch,plan,'trusted-level2-fixture',store.growth_rules,
                store.attribute_rules,resource_context=GrowthResourceContext(inv.immutable_snapshot_transaction(db),
                    store.equipment_attribute_rules,store.resource_rules))
            assert read_growth(db,1111,inv.role_id).level==2
        wounded=state(inv)
        healing.settle(store,inv,once);assert state(inv)==wounded
        with closing(inv.accounts.connect()) as db:
            assert db.execute('SELECT fee FROM npc_role_healing_receipts WHERE role_id=? AND request_id=?',
                (inv.role_id,'heal-once')).fetchone()==(30,)
        for invalid in (replace(once,npc_id=10054),replace(once,service_id=92),
                replace(once,handler='recovery.rest'),replace(once,placement_id=999)):
            refused(lambda:healing.settle(store,inv,invalid))
            assert state(inv)==wounded
        late=command(inv,'heal-sql-retry')
        with closing(store.connect()) as db,db:
            db.execute("CREATE TRIGGER controlled_heal_late BEFORE INSERT ON npc_command_receipts "
                "WHEN NEW.request_id='heal-sql-retry' BEGIN SELECT RAISE(ABORT,'late healer storage failure'); END")
        try:healing.settle(store,inv,late)
        except sqlite3.IntegrityError as error:assert str(error)=='late healer storage failure'
        else:raise AssertionError('Late receipt write fault committed treatment')
        assert state(inv)==wounded
        with closing(store.connect()) as db,db:db.execute('DROP TRIGGER controlled_heal_late')
        healing.settle(store,inv,late);successful=state(inv)
        assert successful[2][0].balance==910 and successful[0].version==wounded[0].version+1
        healing.settle(store,inv,late);assert state(inv)==successful
        damage(inv,'controlled-death-fixture',0,30);dead=state(inv)
        refused(lambda:healing.settle(store,inv,command(inv,'no-revival')))
        assert role_values(healing.settle(store,inv,once))[60]==0 and state(inv)==dead
        previous=inv;epoch=store.acquire_lease(1111,inv.role_id)
        inv=Inventory(store.leased(1111,inv.role_id,epoch),1111,inv.role_id)
        new_lease=state(inv)
        refused(lambda:healing.settle(store,previous,once))
        assert state(inv)==new_lease
        assert role_values(healing.settle(store,inv,command(inv,'heal-once')))[60]==0
        assert state(inv)==new_lease
        bad=known_profile(store,roles['治疗晚错'],hit=16777217);bad_before=state(bad)
        try:healing.settle(store,bad,command(bad,'heal-native-late'))
        except ValueError as error:assert 'float' in str(error).lower()
        else:raise AssertionError('Real unencodable final projection committed a fee/heal')
        assert state(bad)==bad_before
        unknown=known_profile(store,roles['治疗未知'],migrated=False);unknown_before=state(unknown)
        refused(lambda:healing.settle(store,unknown,command(unknown,'unknown-resource')))
        assert state(unknown)==unknown_before and unknown_before[0] is None
        store=AccountStore(Path(temp)/'healer-funds.sqlite3')
        funds_role=store.create_role(1111,'治疗余额',11,1010109)
        runtime_storage.prepare(store)
        funds=known_profile(store,funds_role)
        def funding(identity,amount):
            with closing(funds.accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                apply_currency(db,1111,funds.role_id,funds.epoch,
                    CurrencyChange(identity,'npc_role_heal','explicit-disposable-funding-fixture',(('cash',amount),)),
                    store.currency_rules)
        funding('fixture-empty-cash',-1000)
        waiting=command(funds,'heal-funds-retry');empty=state(funds)
        refused(lambda:healing.settle(store,funds,waiting));assert state(funds)==empty
        funding('fixture-fund-cash',30)
        healing.settle(store,funds,waiting);assert state(funds)[2][0].balance==0
        damage(funds,'pending-source-damage',80,60);funding('fixture-next-cash',30)
        with closing(funds.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            funds.apply_settlement(db,AssetChange('controlled-pending-source',grants=((32000,1),)))
        pending=state(funds);fresh=command(funds,'healing-pending-source')
        refused(lambda:healing.settle(store,funds,waiting))
        refused(lambda:healing.settle(store,funds,fresh))
        assert state(funds)==pending
        with closing(funds.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            synchronize_inventory_resource_source(db,1111,funds.role_id,funds.epoch,
                funds.immutable_snapshot_transaction(db),'actual-inventory-owner-reconciliation',
                resource_rules=store.resource_rules,equipment_rules=store.equipment_attribute_rules,replayed=False)
        synchronized=state(funds)
        assert (role_values(healing.settle(store,funds,waiting))[60],state(funds)[2][0].balance)==(80,30)
        assert state(funds)==synchronized
        healing.settle(store,funds,fresh)
        assert state(funds)[0].hp==100 and state(funds)[2][0].balance==0
    report={'passed':['original doctor proof settles one resource carrier70/40->100/100 with30 cash and unchanged bound500/assets/caps',
        'paid full replay and fresh full refusal preserve current state; later damage80/60 is never healed by replay',
        'actual ordinary growth to level2 preserves old paid fee30; a new healing admission charges60',
        'foreign doctor/service/handler/placement refuse without writes',
        'real late SQL receipt failure rolls back fee/resources/all receipts; same failed ID retries once',
        'fresh HP0 rejects while paid replay preserves death',
        'actual new lease rejects old owner; freshly proved paid retry preserves current death and balances',
        'real native float32 final-map failure rolls back fee/heal and receipts',
        'unknown resource profile rejects without migration or fee',
        'insufficient cash cannot consume bound500 or a request ID; trusted funding permits the same retry',
        'pending source rejects fresh and paid reads without reconciliation; actual inventory-owner sync permits read-only replay'],
        'native_gui_verified':False,'live_database_modified':False,'battle_executed':False}
    write_json(OUT/'evidence/npc-role-healing-domain.json',report);print(report)


if __name__=='__main__':main()
