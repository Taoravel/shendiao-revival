"""Actual Owner repair/pet recovery under the sole resource contract.

Disposable explicit legacy fixtures, original NPC proof and request routes.
No movement, battle, automatic migration, live listener or client GUI.
"""
import argparse
import asyncio
from contextlib import closing
from functools import partial
from pathlib import Path
import struct
import tempfile
from unittest.mock import patch
from accounts import AccountStore
from currency import read_wallet,apply_currency,CurrencyChange
from game_runtime import GameRuntime
from inventory import AssetChange,REFRESH_PET
from role_attribute_storage import read_attribute_snapshot
from role_equipment import resource_caps_from_projection
from role_equipment_storage import current_equipment_totals,current_resource_profile
from role_resource_plan import plan_resource_values,plan_resource_caps
from role_resource_storage import read_role_resources,apply_resource_transition,migrate_role_resources,ResourceNotInitialized
from verify_growth_runtime import GrowthPeer,role_values
from verify_resource_owner_runtime import fixture
from verify_npc_equipped_repair_runtime import seed_profile
from inspect_client import OUT,write_json
import runtime_storage
import npc_recovery


def state(store,owner,*,strict=True):
    inv=owner.inventory
    with closing(inv.accounts.connect()) as db:
        db.execute('BEGIN')
        snapshot=inv.immutable_snapshot_transaction(db)
        try:resources=read_role_resources(db,1111,owner.id,owner.epoch,store.resource_rules)
        except ResourceNotInitialized:resources=None
        else:
            if strict:current_resource_profile(db,1111,owner.id,owner.epoch,snapshot,
                equipment_rules=store.equipment_attribute_rules,resource_rules=store.resource_rules)
        wallet=read_wallet(db,1111,owner.id,owner.epoch,store.currency_rules)
        counts=tuple(db.execute('SELECT COUNT(*) FROM '+t+' WHERE role_id=?',(owner.id,)).fetchone()[0]
            for t in ('role_resource_receipts','role_wallet_receipts','npc_command_receipts',
                      'npc_recovery_receipts','inventory_equipment_receipts'))
        return snapshot,resources,next(r.balance for r in wallet if r.currency=='cash'),counts


def pending_fixture(inventory,identity):
    with closing(inventory.accounts.connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        inventory.apply_settlement(db,AssetChange(identity,grants=((32000,1,1),)))


def change_fixture(store,inv,identity,*,wear=None,pet=False,role_values=None):
    with closing(inv.accounts.connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        before=read_role_resources(db,1111,inv.role_id,inv.epoch,store.resource_rules)
        if wear is not None:
            condition=inv.equipment_condition(db,wear)
            inv.wear_equipment(db,wear,identity,condition.version,10)
            totals=current_equipment_totals(db,1111,inv.role_id,inv.epoch,
                inv.immutable_snapshot_transaction(db),store.equipment_attribute_rules)
            plan=plan_resource_caps(before,resource_caps_from_projection(totals),'equipment_wear',store.resource_rules)
            apply_resource_transition(db,1111,inv.role_id,inv.epoch,plan,identity,
                rules=store.resource_rules,equipment_rules=store.equipment_attribute_rules)
        if pet:
            snapshot=inv.immutable_snapshot_transaction(db)
            if not snapshot.pets:
                inv.apply_settlement(db,AssetChange(identity+':grant',pets=(500001,)))
                snapshot=inv.immutable_snapshot_transaction(db)
            for p in snapshot.pets:
                inv.change_pet_growth(db,p.id,identity,p.progress.state.version,'resources',(0,0))
                inv.change_pet_care(db,p.id,identity,p.care.version,'defeat',1)
            runtime_storage._synchronize_source(db,store,inv,identity+':source',replayed=False)
        if role_values is not None:
            totals=current_equipment_totals(db,1111,inv.role_id,inv.epoch,
                inv.immutable_snapshot_transaction(db),store.equipment_attribute_rules)
            plan=plan_resource_values(before,*role_values,'medicine',store.resource_rules,
                current_caps=resource_caps_from_projection(totals))
            apply_resource_transition(db,1111,inv.role_id,inv.epoch,plan,identity,
                rules=store.resource_rules,equipment_rules=store.equipment_attribute_rules)


def complete_map(messages,hp=10,mp=20):
    maps=[b for k,b in messages if k==0xc32c8]
    assert len(maps)==1,'Expected one final full character map from the real Owner route'
    values=role_values(messages)
    assert len(values)==20 and (values[60],values[70])==(hp,mp)


async def refused(command):
    try:await command
    except ValueError:return
    raise AssertionError('Unsafe resource operation unexpectedly accepted')


async def check(store,prepared,roles,npcs,keys,case):
    rt=GameRuntime(store,prepared)
    try:
        if case in ('all','repair'):
            peer=GrowthPeer(rt);await peer.login(roles[0]);owner=rt.roles[roles[0]['id']]
            npc=npcs[0];weapon=keys[0][0];key=(npc.map_id<<32)|npc.placement_id
            await owner.io(partial(change_fixture,wear=weapon),store,owner.inventory,'repair-owner-wear')
            body=struct.pack('>iqii',2,key,4,weapon)
            before=state(store,owner)
            first=await peer.request(0xc0413,body)
            complete_map(first)
            after=state(store,owner)
            assert after[2]==before[2]-20
            assert (after[1].hp,after[1].mp,after[1].version)==(10,20,before[1].version)
            assert after[0].items[0].condition.version==before[0].items[0].condition.version+1
            with closing(store.connect()) as db:
                accepted=db.execute('SELECT request_id FROM npc_command_receipts WHERE role_id=?',(owner.id,)).fetchone()[0]
            await owner.io(partial(change_fixture,role_values=(30,40)),store,owner.inventory,'later-role-resource')
            current=state(store,owner)
            complete_map(await owner.mailbox.call('receive',0xc0413,body,request_id=accepted),30,40)
            assert state(store,owner)==current
            await owner.io(partial(change_fixture,wear=weapon),store,owner.inventory,'repair-owner-wear-late')
            current=state(store,owner)
            with patch.object(runtime_storage,'equipment_projection_messages',side_effect=ValueError('controlled actual final repair map')):
                await refused(owner.mailbox.call('receive',0xc0413,body,request_id='repair-final-failure'))
            assert state(store,owner)==current
            complete_map(await owner.mailbox.call('receive',0xc0413,body,request_id='repair-final-failure'),30,40)
            final=state(store,owner)
            assert final[2]==current[2]-20
            old_owner=owner
            await peer.connection.close();peer=GrowthPeer(rt);await peer.login(roles[0]);owner=rt.roles[roles[0]['id']]
            assert state(store,owner)==final
            await refused(old_owner.mailbox.call('receive',0xc0413,body,request_id=accepted))
            complete_map(await owner.mailbox.call('receive',0xc0413,body,request_id=accepted),30,40)
            assert state(store,owner)==final
            await owner.io(pending_fixture,owner.inventory,'repair-unrelated-pending')
            pending=state(store,owner,strict=False)
            await refused(owner.mailbox.call('receive',0xc0413,body,request_id=accepted))
            assert state(store,owner,strict=False)==pending
            await peer.connection.close()
        if case in ('all','pet'):
            peer=GrowthPeer(rt);await peer.login(roles[1]);owner=rt.roles[roles[1]['id']]
            npc=npcs[1];key=(npc.map_id<<32)|npc.placement_id
            accepted_requests=[]
            for index,(kind,service) in enumerate(((2,None),(3,None),(4,None),(2,10),(3,11),(4,12))):
                await owner.io(partial(change_fixture,pet=True),store,owner.inventory,'pet-owner-fixture:'+str(index))
                before=state(store,owner)
                message=0xc2333 if service is None else 0xc232b
                body=struct.pack('>qi',key,kind if service is None else service)
                result=await peer.request(message,body)
                complete_map(result)
                with closing(store.connect()) as db:
                    request=db.execute('SELECT request_id FROM npc_recovery_receipts WHERE role_id=? ORDER BY rowid DESC LIMIT 1',
                        (owner.id,)).fetchone()[0]
                accepted_requests.append(request)
                assert len([k for k,b in result if k==REFRESH_PET])==1
                after=state(store,owner);pet=after[0].pets[0];old=before[0].pets[0]
                assert after[2]<before[2]
                assert (after[1].hp,after[1].mp,after[1].version)==(10,20,before[1].version)
                assert pet.care.lifetime==old.care.lifetime
                assert pet.care.loyalty==(100 if kind in (3,4) else old.care.loyalty)
                assert (pet.progress.state.hp,pet.progress.state.mp)==(
                    (pet.progress.attributes.max_hp,pet.progress.attributes.max_mp) if kind in (2,4) else (0,0))
                assert await owner.mailbox.call('receive',message,body,request_id=request)
                assert state(store,owner)==after
            await owner.io(partial(change_fixture,pet=True),store,owner.inventory,'pet-later-wounds')
            before=state(store,owner)
            assert await owner.mailbox.call('receive',0xc2333,struct.pack('>qi',key,2),request_id=accepted_requests[0])
            assert state(store,owner)==before,'Paid pet request must preserve later pet wounds'
            body=struct.pack('>qi',key,4)
            with patch.object(npc_recovery,'growth_refresh',side_effect=ValueError('controlled actual final pet map')):
                await refused(owner.mailbox.call('receive',0xc2333,body,request_id='pet-final-failure'))
            assert state(store,owner)==before
            complete_map(await owner.mailbox.call('receive',0xc2333,body,request_id='pet-final-failure'))
            final=state(store,owner)
            old_owner=owner
            await peer.connection.close();peer=GrowthPeer(rt);await peer.login(roles[1]);owner=rt.roles[roles[1]['id']]
            assert state(store,owner)==final
            await refused(old_owner.mailbox.call('receive',0xc2333,body,request_id='pet-final-failure'))
            assert await owner.mailbox.call('receive',0xc2333,body,request_id='pet-final-failure')
            assert state(store,owner)==final
            await owner.io(pending_fixture,owner.inventory,'pet-unrelated-pending')
            pending=state(store,owner,strict=False)
            await refused(owner.mailbox.call('receive',0xc2333,body,request_id='pet-final-failure'))
            assert state(store,owner,strict=False)==pending
            await peer.connection.close()
        if case in ('all','legacy'):
            peer=GrowthPeer(rt);await peer.login(roles[2]);owner=rt.roles[roles[2]['id']]
            await owner.io(seed_profile,store,owner.inventory)
            await owner.io(runtime_storage.initialize_role_wallet,store,1111,owner.id,owner.epoch,(1000,0,0,0),'explicit_migration')
            await owner.mailbox.call('settle',AssetChange('legacy-paid-weapon',grants=((49009,1,1),)))
            weapon=state(store,owner)[0].items[0].id
            await peer.request(0xc03f5,struct.pack('>ii',weapon,0))
            def wear_legacy():
                with closing(owner.inventory.accounts.connect()) as db,db:
                    db.execute('BEGIN IMMEDIATE')
                    cond=owner.inventory.equipment_condition(db,weapon)
                    owner.inventory.wear_equipment(db,weapon,'legacy-paid-wear',cond.version,20)
            await owner.io(wear_legacy)
            npc=npcs[0];key=(npc.map_id<<32)|npc.placement_id;body=struct.pack('>iqii',2,key,4,weapon)
            assert await owner.mailbox.call('receive',0xc0413,body,request_id='legacy-paid-owner')
            assert state(store,owner)[2]==960
            def migrate_legacy():
                inv=owner.inventory
                with closing(inv.accounts.connect()) as db,db:
                    db.execute('BEGIN IMMEDIATE')
                    old=read_attribute_snapshot(db,1111,owner.id,owner.epoch).vitals
                    totals=current_equipment_totals(db,1111,owner.id,owner.epoch,
                        inv.immutable_snapshot_transaction(db),store.equipment_attribute_rules)
                    migrate_role_resources(db,1111,owner.id,owner.epoch,old,resource_caps_from_projection(totals),
                        origin='explicit_migration',migration_id='legacy-owner-after-paid',rules=store.resource_rules,
                        equipment_rules=store.equipment_attribute_rules)
            await owner.io(migrate_legacy)
            before=state(store,owner)
            complete_map(await owner.mailbox.call('receive',0xc0413,body,request_id='legacy-paid-owner'),70,40)
            assert state(store,owner)==before
            with closing(store.connect()) as db:
                assert db.execute("SELECT COUNT(*) FROM role_resource_receipts WHERE role_id=? AND cause='equipment_repair'",
                    (owner.id,)).fetchone()[0]==0
            await peer.connection.close()
    finally:await rt.close()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--case',choices=('all','repair','pet','legacy'),default='all')
    case=parser.parse_args().case
    with tempfile.TemporaryDirectory(prefix='npc-care-resource-owner-') as folder:
        store=AccountStore(Path(folder)/'state.sqlite3')
        roles=[store.create_role(1111,name,11,1010109) for name in ('新资源修理','新资源宠物','旧付后迁移')]
        prepared=runtime_storage.prepare(store)
        npcs=[next(p for ps in store.npc_resources[0].values() for p in ps if p.npc_id==ident) for ident in (10004,10086)]
        keys=[fixture(store,role,npc) for role,npc in zip(roles[:2],npcs)]
        # Explicit known pet-recovery cash, not a gameplay grant.
        epoch=store.acquire_lease(1111,roles[1]['id'])
        with closing(store.leased(1111,roles[1]['id'],epoch).connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            apply_currency(db,1111,roles[1]['id'],epoch,
                CurrencyChange('explicit-pet-cash-fixture','explicit_migration_fixture','controlled-owner-test',(('cash',8000),)),
                store.currency_rules)
        store.save_position(1111,roles[2]['id'],(npcs[0].map_id,npcs[0].x,npcs[0].y))
        asyncio.run(check(store,prepared,roles,npcs,keys,case))
    result=dict(case=case,passed=[
        'actual encrypted ordinary repair and both CRecovery/services10/11/12 routes emit one final current full map',
        'actual condition/fees/pet healing/loyalty/source/receipts commit together, role10/20/version unchanged',
        'paid repair preserves later30/40 and paid pet recovery preserves later pet wounds without another debit',
        'final map failure rolls assets/cash/source/all receipts back and same failed command later succeeds',
        'reconnect preserves committed state, old Owner refuses and current NPC proof reads paid state',
        'paid repair/pet requests reject unrelated pending source without repair',
        'legacy paid repair after explicit migration reads current70/40/cash960 without retrospective transition'
        ] if case=='all' else [case],database='disposable',fixture='explicit known legacy resource/gear/cash/pet states',
        native_gui_verified=False,live_server_changed=False,battle_executed=False)
    if case=='all':write_json(OUT/'evidence/resource-npc-care-runtime-verification.json',result)
    print(result)


if __name__=='__main__':main()
