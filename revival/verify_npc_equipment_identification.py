"""NPC query/confirmation, real clean asset CAS and cash/source transaction."""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
import sqlite3
import struct
import tempfile
import time
from unittest.mock import patch
from accounts import AccountStore
from inventory import Inventory,ITEM_TIPS_REPLY,AssetChange
from currency import read_wallet,apply_currency,CurrencyChange,initialize_wallet
from inspect_client import OUT,write_json
from role_equipment_storage import synchronize_inventory_resource_source
from role_resource_storage import read_role_resources
from research_equipment_detail_full import NativeEquipmentDetail
from verify_equipment_identification_cas import known_unidentified
from verify_resource_owner_runtime import fixture
from wire import read_octets
from world_npcs import NpcScene
from world_owner import MapAddress,Location
from world_role_delivery import RoleViewBinding
import npc_equipment_identification as identification
import npc_identification_query
import runtime_storage


def dump(store):
    with closing(store.connect()) as db:return tuple(db.iterdump())


def refused_without_writes(store,action):
    before=dump(store)
    try:action()
    except (ValueError,sqlite3.DatabaseError,MemoryError):pass
    else:raise AssertionError('Unsafe fixed identification accepted')
    assert dump(store)==before, 'Identification failure left a partial transaction'


def current_paid_readonly(action):
    connect=sqlite3.connect
    def readonly(*args,**kwargs):
        db=connect(*args,**kwargs)
        db.set_authorizer(lambda operation,*rest:sqlite3.SQLITE_DENY if operation in (
            sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE) else sqlite3.SQLITE_OK)
        return db
    # Replace only the external DB connector; AccountStore's real fenced
    # connection and every public domain/storage operation remain in place.
    with patch.object(sqlite3,'connect',readonly):return action()


def main():
    if not hasattr(identification,'settle'):
        write_json(OUT/'evidence/npc-equipment-identification-settlement-baseline.json',{
            'failure':'NPC confirmed query has no atomic fixed clean identification settlement',
            'seam':'original query and confirmation -> public Inventory CAS/cash/source/native replies',
            'live_database_modified':False})
        raise AssertionError('NPC confirmed query has no atomic fixed clean identification settlement')
    with tempfile.TemporaryDirectory(prefix='npc-fixed-identification-') as directory:
        store=AccountStore(Path(directory)/'state.sqlite3')
        role=store.create_role(1111,'鉴定结算接缝',11,1010109);prepared=runtime_storage.prepare(store)
        npc_identification_query.prepare(store);identification.prepare(store)
        npc=next(p for p in store.npc_resources[0][1007] if p.npc_id==10890 and p.placement_id==75)
        fixture(store,role,npc)
        epoch=store.acquire_lease(1111,role['id'])
        inventory=Inventory(store.leased(1111,role['id'],epoch),1111,role['id'])
        key=known_unidentified(store,inventory,slot=2)
        with closing(inventory.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            synchronize_inventory_resource_source(db,1111,role['id'],epoch,
                inventory.immutable_snapshot_transaction(db),'known-identification-fixture',
                resource_rules=store.resource_rules,equipment_rules=store.equipment_attribute_rules,replayed=False)
            resources=read_role_resources(db,1111,role['id'],epoch,store.resource_rules)
        address=MapAddress(1007,1007,0);entity=(1007<<32)|75
        scene=NpcScene(address,(npc,),prepared[3],binding_capacity=1,interaction_rules=store.npc_interaction_rules)
        scene.bind(entity,75);location=Location(role['id'],epoch,address,1,npc.x,npc.y)
        binding=RoleViewBinding(address,'known-identify-owner',role['id'],epoch,1,1)
        def proof(identity,clock):return scene.interact(struct.pack('>q',entity),location,location,
            request_id=identity,now_ms=clock,deadline_ms=clock+30000)
        def again(ticket,key):
            now=int(time.monotonic()*1000)
            return identification.confirm(ticket,struct.pack('>iii',key,0,1),proof('confirm',now),
                location,binding,now_ms=now,deadline_ms=now+30000)
        def admit(key,identity):
            now=int(time.monotonic()*1000)
            dialogue=identification.query(inventory,b'\1'+struct.pack('>iQi',key,entity,1),
                proof('query',now),location,binding,rules=store.npc_identification_rules,
                request_id=identity,now_ms=now,deadline_ms=now+30000)
            return again(dialogue.ticket,key)
        def source(db,inv,snapshot,*,replayed):
            return synchronize_inventory_resource_source(db,1111,role['id'],epoch,snapshot,
                'known-identification-source:'+str(snapshot.inventory_revision),
                resource_rules=store.resource_rules,equipment_rules=store.equipment_attribute_rules,replayed=replayed)
        def import_known(template=40200,slot=4):
            result=known_unidentified(store,inventory,template,slot=slot)
            with closing(inventory.accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE');source(db,inventory,inventory.immutable_snapshot_transaction(db),replayed=False)
            return result
        def cash():
            with closing(inventory.accounts.connect()) as db:
                db.execute('BEGIN')
                return next(r.balance for r in read_wallet(db,1111,role['id'],epoch,store.currency_rules) if r.currency=='cash')
        intent=admit(key,'fixed-clean-first-confirmation')
        before=inventory.immutable_snapshot();old=next(item for item in before.items if item.id==key)
        messages=identification.settle(store,inventory,intent)
        after=inventory.immutable_snapshot();updated=next(item for item in after.items if item.id==key)
        assert updated==replace(old,detail=replace(old.detail,identified=1))
        assert after.inventory_revision==before.inventory_revision+1
        with closing(inventory.accounts.connect()) as db:
            db.execute('BEGIN')
            assert next(r.balance for r in read_wallet(db,1111,role['id'],epoch,store.currency_rules) if r.currency=='cash')==1900
            current=read_role_resources(db,1111,role['id'],epoch,store.resource_rules)
            assert (current.hp,current.mp,current.version,current.caps.hp_max,current.caps.mp_max)==(
                resources.hp,resources.mp,resources.version,resources.caps.hp_max,resources.caps.mp_max)
        tip=next(body for kind,body in messages if kind==ITEM_TIPS_REPLY)
        assert struct.unpack_from('>ii',tip)==(1,key)
        encoded,end=read_octets(tip,8);assert end==len(tip)
        parsed=NativeEquipmentDetail(40200).parse(encoded)
        assert (parsed['identified'],parsed['current'],parsed['maximum'],parsed['prefix_quality'],parsed['score'],parsed['color'])==(1,42,80,1,0,1)
        # Public move + same-transaction source advances the inventory after
        # payment. The old ticket reads CURRENT item/cash, never its old basis.
        inventory.move_item(key,3,precommit=source)
        with closing(inventory.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            apply_currency(db,1111,role['id'],epoch,
                CurrencyChange('later-other-service','npc_shop','controlled-later-shop',(('cash',-100),)),store.currency_rules)
        before=dump(store)
        with patch.object(Path,'read_text',side_effect=AssertionError('Hot identification policy read')):
            current_paid_readonly(lambda:identification.settle(store,inventory,again(intent.ticket,key)))
        assert dump(store)==before and cash()==1800
        refused_without_writes(store,lambda:identification.settle(store,inventory,admit(key,'fresh-already-identified')))
        failures=0
        for index,table in enumerate(('inventory_equipment_details','npc_command_receipts','role_resource_receipts')):
            target=import_known(slot=4+index);pending=admit(target,f'failed-fixed-{index}')
            operation='UPDATE' if table=='inventory_equipment_details' else 'INSERT'
            condition=" WHEN NEW.cause='inventory_change'" if table=='role_resource_receipts' else ''
            with closing(store.connect()) as db,db:
                db.execute(f"CREATE TRIGGER fail_fixed_identification BEFORE {operation} ON {table}{condition} "
                    "BEGIN SELECT RAISE(ABORT,'controlled fixed identification fault'); END")
            refused_without_writes(store,lambda:identification.settle(store,inventory,pending))
            with closing(store.connect()) as db,db:db.execute('DROP TRIGGER fail_fixed_identification')
            initial=cash();identification.settle(store,inventory,again(pending.ticket,target));assert cash()==initial-100
            unchanged=dump(store);identification.settle(store,inventory,again(pending.ticket,target));assert dump(store)==unchanged
            failures+=1
        target=import_known(slot=7);pending=admit(target,'failed-native-encoding')
        original_pack=struct.pack
        def allocation(fmt,*values):
            if fmt=='>7i':raise MemoryError('Controlled current tip allocation failure')
            return original_pack(fmt,*values)
        with patch.object(struct,'pack',allocation):
            refused_without_writes(store,lambda:identification.settle(store,inventory,pending))
        initial=cash();identification.settle(store,inventory,again(pending.ticket,target));assert cash()==initial-100
        failures+=1
        # The original exact50 quote is15000; available bound silver is not
        # considered, and a refusal does not consume this query's identity.
        target=import_known(40105,slot=8);pending=admit(target,'exact-level50-fee')
        refused_without_writes(store,lambda:identification.settle(store,inventory,pending))
        with closing(inventory.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            apply_currency(db,1111,role['id'],epoch,CurrencyChange('known-extra-identify-cash',
                'explicit_migration_fixture','controlled-known-fixture',(('cash',20000),)),store.currency_rules)
        initial=cash();identification.settle(store,inventory,again(pending.ticket,target));assert cash()==initial-15000
        target=import_known(slot=9);pending=admit(target,'stale-query-after-real-move')
        original_item=next(item for item in inventory.immutable_snapshot().items if item.id==target)
        inventory.move_item(target,12,precommit=source)
        inventory.move_item(target,9,precommit=source)
        assert next(item for item in inventory.immutable_snapshot().items if item.id==target)==original_item
        refused_without_writes(store,lambda:identification.settle(store,inventory,again(pending.ticket,target)))
        initial=cash();identification.settle(store,inventory,admit(target,'fresh-query-after-real-move'))
        assert cash()==initial-100
        first=import_known(slot=10);second=import_known(slot=11)
        clock=int(time.monotonic()*1000)
        multiple=identification.query(inventory,b'\2'+struct.pack('>2iQi',first,second,entity,1),
            proof('two-keys-query',clock),location,binding,rules=store.npc_identification_rules,
            request_id='one-dialogue-two-selections',now_ms=clock,deadline_ms=clock+30000)
        initial=cash();identification.settle(store,inventory,again(multiple.ticket,first));assert cash()==initial-100
        refused_without_writes(store,lambda:identification.settle(store,inventory,again(multiple.ticket,second)))
        identification.settle(store,inventory,admit(second,'second-item-fresh-query'));assert cash()==initial-200
        target=import_known(slot=13);pending=admit(target,'expired-after-actual-encoding')
        external_clock=[time.monotonic()]
        original_pack=struct.pack
        def advance_after_tip(fmt,*values):
            packet=original_pack(fmt,*values)
            if fmt=='>7i':external_clock[0]=(pending.deadline_ms+1)/1000
            return packet
        # Only the external clock/serialization boundaries change. The real
        # fee, asset CAS, source, receipts and encoders execute before expiry.
        with patch.object(time,'monotonic',side_effect=lambda:external_clock[0]),patch.object(struct,'pack',advance_after_tip):
            refused_without_writes(store,lambda:identification.settle(store,inventory,pending))
        initial=cash();identification.settle(store,inventory,again(pending.ticket,target));assert cash()==initial-100
        failures+=1
        with closing(inventory.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            inventory.apply_settlement(db,AssetChange('controlled-later-item-consumption',debits=((key,1),)))
            source(db,inventory,inventory.immutable_snapshot_transaction(db),replayed=False)
        consumed=dump(store)
        missing_reply=current_paid_readonly(lambda:identification.settle(store,inventory,again(intent.ticket,key)))
        assert dump(store)==consumed and all(kind!=ITEM_TIPS_REPLY for kind,body in missing_reply)
        assert all(item.id!=key for item in inventory.immutable_snapshot().items)
        current=inventory.immutable_snapshot()
        replacement=store.acquire_lease(1111,role['id'])
        refused_without_writes(store,lambda:identification.settle(store,inventory,again(pending.ticket,target)))
        new_inventory=Inventory(store.leased(1111,role['id'],replacement),1111,role['id'])
        assert new_inventory.immutable_snapshot()==current
        refused_without_writes(store,lambda:identification.settle(store,new_inventory,again(pending.ticket,target)))
        inventory=new_inventory;epoch=replacement
        location=replace(location,login_epoch=epoch);binding=replace(binding,login_epoch=epoch)
        paid_key=import_known(slot=14);unpaid_key=import_known(slot=15)
        paid=admit(paid_key,'current-owner-before-pending-source')
        identification.settle(store,inventory,paid)
        unpaid=admit(unpaid_key,'current-owner-unpaid-pending-source')
        inventory.grant_item(32000) # Controlled committed change without its required source hook.
        refused_without_writes(store,lambda:identification.settle(store,inventory,again(paid.ticket,paid_key)))
        refused_without_writes(store,lambda:identification.settle(store,inventory,unpaid))
        # A separate current owner deliberately lacks a resource/equipment
        # profile. A known item/wallet never authorizes implicit initialization.
        unknown_role=store.create_role(1111,'鉴定未知来源',11,1010109)
        unknown_epoch=store.acquire_lease(1111,unknown_role['id'])
        unknown=Inventory(store.leased(1111,unknown_role['id'],unknown_epoch),1111,unknown_role['id'])
        with closing(unknown.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            initialize_wallet(db,1111,unknown_role['id'],unknown_epoch,(2000,0,0,0),'explicit_migration',store.currency_rules)
        unknown_key=known_unidentified(store,unknown,slot=0)
        unknown_location=replace(location,role_id=unknown_role['id'],login_epoch=unknown_epoch)
        unknown_binding=replace(binding,role_id=unknown_role['id'],login_epoch=unknown_epoch)
        clock=int(time.monotonic()*1000)
        unknown_proof=scene.interact(struct.pack('>q',entity),unknown_location,unknown_location,
            request_id='unknown-profile-query',now_ms=clock,deadline_ms=clock+30000)
        unknown_dialogue=identification.query(unknown,b'\1'+struct.pack('>iQi',unknown_key,entity,1),
            unknown_proof,unknown_location,unknown_binding,rules=store.npc_identification_rules,
            request_id='unknown-profile-confirmation',now_ms=clock,deadline_ms=clock+30000)
        unknown_intent=identification.confirm(unknown_dialogue.ticket,struct.pack('>iii',unknown_key,0,1),
            unknown_proof,unknown_location,unknown_binding,now_ms=clock,deadline_ms=clock+30000)
        refused_without_writes(store,lambda:identification.settle(store,unknown,unknown_intent))
    write_json(OUT/'evidence/npc-equipment-identification-verification.json',{
        'passed':['actual query/confirmation accepts fixed complete clean result',
            'public asset CAS only flips identified, cash100 plus sole source commit together',
            'role resources/caps/version unchanged; original full detail consumer reads current result',
            'paid ticket after actual move and later wallet change reads current state SQL-readonly without hot files',
            'fresh identified1 refuses; four real SQL/native failures roll everything back and failed IDs retry once',
            'original exact50 fee15000: insufficient then trusted funding and same-ID success',
            'real move-away/back keeps full item equal but old query version refuses; fresh query succeeds',
            'one paid dialogue cannot charge a different selected key; a fresh query can identify it',
            'actual post-encoding deadline expiry rolls everything back; same failed ticket succeeds',
            'paid ticket after public same-transaction item consumption returns current bag without resurrecting tips',
            'real opaque lease replacement rejects stale intents and retains current persisted items',
            'current known item/wallet with missing role resource/basis refuses without initialization',
            'fresh and paid confirmations reject an unrelated pending source without repairing it'],
        'late_fault_rollback_cases':failures,
        'shared_route_implemented':False,'deployed':False,'live_database_modified':False,'native_gui_verified':False})
    print('PASS fixed clean NPC confirmation/payment/source and original full detail')


if __name__=='__main__':main()
