"""Public owned identification CAS and same-transaction native current replies."""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import struct
import sqlite3
import json
from unittest.mock import patch
from accounts import AccountStore
from inventory import Inventory,ITEM_TIPS_REPLY
from inventory_test_support import known_cash_context
from research_equipment_detail_full import NativeEquipmentDetail
from wire import read_octets
from currency import CurrencyChange,apply_currency,read_wallet
from native_gameplay_probe import probe
from inspect_client import OUT,write_json


def refused(action,errors=(ValueError,)):
    try:action()
    except errors:return
    raise AssertionError('Invalid fixed identification or injected fault committed')


def known_unidentified(store,inv,template=40200,*,binding=1,quality=99,slot=0):
    """Explicit complete fixed-result fixture, not a generation policy."""
    with closing(store.connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        key=db.execute('INSERT INTO inventory_items(role_id,template_id,quantity,slot,binding,quality) VALUES(?,?,1,?,?,?)',
            (inv.role_id,template,slot,binding,quality)).lastrowid
        inv.initialize_equipment_condition(db,key,42,80,1)
        inv.initialize_equipment_detail(db,key,replace(inv.detail_rules.generate(template),identified=0))
    return key


def main():
    with TemporaryDirectory(prefix='identification-cas-') as tmp:
        store=AccountStore(Path(tmp)/'state.sqlite3');role=store.create_role(1111,'鉴定资产',12,1010101)
        config=Inventory.prepare(store)
        store.inventory_config=config
        inv=Inventory(store,1111,role['id'],config,**known_cash_context(store,1111,role['id'],balances=(20000,0,0,0)))
        key=known_unidentified(store,inv)
        before=inv.immutable_snapshot();old=before.items[0]
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            basis=inv.equipment_identification_basis(db,key,inv.epoch)
            changed=inv.identify_equipment_clean_transaction(db,basis,inv.epoch)
            message=inv.equipment_tip_message(db,key,inv.epoch)
            probe(0xd9c110,0xe4e5c0,0xe0a240,payload=message[1])
            assert message[0]==ITEM_TIPS_REPLY and struct.unpack_from('>ii',message[1])==(1,key)
            body,end=read_octets(message[1],8);assert end==len(message[1])
            parsed=NativeEquipmentDetail(40200).parse(body)
            assert (parsed['identified'],parsed['current'],parsed['maximum'],parsed['prefix_quality'],parsed['score'],parsed['color'])==(1,42,80,1,0,1)
            assert parsed['properties']==[(81,20),(811,20),(1231,6)]
        after=inv.immutable_snapshot()
        assert after.inventory_revision==before.inventory_revision+1
        assert after.items==(replace(old,detail=replace(old.detail,identified=1)),)
        assert changed.before==basis and changed.item==after.items[0]
        assert changed.inventory_revision==after.inventory_revision
        # The NPC owns the fee/receipt: its cash debit composes with the public
        # asset CAS in exactly this caller-owned transaction, never two commits.
        second=known_unidentified(store,inv,slot=1)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            basis=inv.equipment_identification_basis(db,second,inv.epoch)
            fee=CurrencyChange('identify:known-level1','npc_equipment_identify','known-npc-identify-fixture',(('cash',-100),))
            apply_currency(db,1111,role['id'],inv.epoch,fee,inv.currency_rules)
            inv.identify_equipment_clean_transaction(db,basis,inv.epoch)
            assert read_wallet(db,1111,role['id'],inv.epoch,inv.currency_rules)[0].balance==19900
        assert inv.immutable_snapshot().items[1].detail.identified==1
        # Six real original50-level templates; identification never grants
        # wearing rights or modifies the role's selected equipment policy.
        for slot,template in enumerate((40105,42010,43005,44010,45005,46005),2):
            item_key=known_unidentified(store,inv,template,slot=slot,binding=slot%2)
            before=inv.immutable_snapshot()
            old=next(i for i in before.items if i.id==item_key)
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                basis=inv.equipment_identification_basis(db,item_key,inv.epoch)
                inv.identify_equipment_clean_transaction(db,basis,inv.epoch)
                body,end=read_octets(inv.equipment_tip_message(db,item_key,inv.epoch)[1],8)
                parsed=NativeEquipmentDetail(template).parse(body)
                assert parsed['identified']==1 and parsed['properties']==sorted(old.detail.base_properties)
                assert (parsed['current'],parsed['maximum'],parsed['score'],parsed['color'])==(42,80,0,1)
            after=inv.immutable_snapshot()
            assert after.items==tuple(replace(i,detail=replace(i.detail,identified=1)) if i.id==item_key else i for i in before.items)
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                refused(lambda:inv.equipment_identification_basis(db,item_key,inv.epoch))
                refused(lambda:inv.identify_equipment_clean_transaction(db,basis,inv.epoch))
            assert inv.immutable_snapshot()==after
        # A move away and back invalidates the old quote even when physical
        # fields match; the inventory source version is part of the CAS.
        item_key=known_unidentified(store,inv,slot=8)
        with closing(store.connect()) as db:
            db.execute('BEGIN');stale=inv.equipment_identification_basis(db,item_key,inv.epoch)
        inv.move_item(item_key,9);inv.move_item(item_key,8)
        before=inv.immutable_snapshot()
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            refused(lambda:inv.identify_equipment_clean_transaction(db,stale,inv.epoch))
            refused(lambda:inv.equipment_identification_basis(db,item_key,inv.epoch,expected_inventory_revision=stale.inventory_revision))
            refused(lambda:inv.equipment_identification_basis(db,item_key,False))
            refused(lambda:inv.equipment_identification_basis(db,True,inv.epoch))
        assert inv.immutable_snapshot()==before
        # The quote's complete server-frozen item is mandatory; stale or forged
        # revision/origin/quality/binding/state cannot weaken the current CAS.
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');basis=inv.equipment_identification_basis(db,item_key,inv.epoch)
            for bad in (replace(basis,inventory_revision=basis.inventory_revision+1),
                    replace(basis,detail_revision='future'),replace(basis,detail_origin='restoration_grant'),
                    replace(basis,item=replace(basis.item,binding=0)),
                    replace(basis,item=replace(basis.item,quality=98))):
                writes=db.total_changes
                refused(lambda:inv.identify_equipment_clean_transaction(db,bad,inv.epoch))
                assert db.total_changes==writes
            refused(lambda:replace(basis,item=replace(basis.item,detail={})))
            refused(lambda:replace(basis,item=replace(basis.item,condition={})))
        # Raw full source CAS rejects semantically equal JSON replacements too.
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');stale=inv.equipment_identification_basis(db,item_key,inv.epoch)
            db.execute('UPDATE inventory_equipment_details SET detail=? WHERE item_key=?',
                (json.dumps(json.loads(stale.detail_json),indent=2),item_key))
            writes=db.total_changes
            refused(lambda:inv.identify_equipment_clean_transaction(db,stale,inv.epoch))
            assert db.total_changes==writes
        # Origin is authority: a default granted clean item remains identified1,
        # and a forged0 under restoration_grant is never charged by this CAS.
        inv.grant_item(40200)
        granted=next(i for i in inv.immutable_snapshot().items if i.detail.identified==1 and i.slot>=9)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');row=db.execute('SELECT detail FROM inventory_equipment_details WHERE item_key=?',(granted.id,)).fetchone()
            value=json.loads(row[0]);value['identified']=0
            db.execute('UPDATE inventory_equipment_details SET detail=? WHERE item_key=?',(json.dumps(value),granted.id))
            writes=db.total_changes
            refused(lambda:inv.equipment_identification_basis(db,granted.id,inv.epoch))
            assert db.total_changes==writes
        # Changing source, fee ledger, revision or final native representation
        # rolls back every asset and the durable wallet acknowledgement.
        def wallet():
            with closing(store.connect()) as db:
                db.execute('BEGIN');return read_wallet(db,1111,role['id'],inv.epoch,inv.currency_rules)
        def identify(request='identify:fault',hook=None):
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE');basis=inv.equipment_identification_basis(db,item_key,inv.epoch)
                change=CurrencyChange(request,'npc_equipment_identify','known-level1-fixed-result',(('cash',-100),))
                apply_currency(db,1111,role['id'],inv.epoch,change,inv.currency_rules)
                result=inv.identify_equipment_clean_transaction(db,basis,inv.epoch,precommit=hook)
                inv.equipment_tip_message(db,item_key,inv.epoch)
                inv.equipment_bag_messages(db,inv.epoch)
                return result
        for table in ('inventory_equipment_details','inventory_versions','role_wallet_balances','role_wallet_receipts'):
            action='INSERT' if table=='role_wallet_receipts' else 'UPDATE'
            with closing(store.connect()) as db,db:
                db.execute(f"CREATE TRIGGER identify_fault BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT,'fixed identification persistence failed'); END")
            before=inv.immutable_snapshot();cash=wallet()
            refused(identify,(sqlite3.IntegrityError,))
            assert inv.immutable_snapshot()==before and wallet()==cash
            with closing(store.connect()) as db,db:db.execute('DROP TRIGGER identify_fault')
        def fail_source(db,inventory,snapshot,*,replayed):
            assert not replayed and next(i for i in snapshot.items if i.id==item_key).detail.identified==1
            assert read_wallet(db,1111,role['id'],inv.epoch,inv.currency_rules)[0].balance==19800
            raise RuntimeError('caller source precommit failed')
        refused(lambda:identify(hook=fail_source),(RuntimeError,))
        for target in ('equipment_detail.encode','inventory.item_record'):
            with patch(target,side_effect=RuntimeError('late identification representation failed')):
                refused(identify,(RuntimeError,))
            assert inv.immutable_snapshot()==before and wallet()==cash
        with patch.object(Path,'read_text',side_effect=AssertionError('hot identification policy')):
            result=identify()
        assert result.item.detail.identified==1 and wallet()[0].balance==19800
        # Caller has committed: a paid NPC must skip the CAS and read current
        # item/wallet/source. These interfaces remain strictly SQL-readonly.
        frozen=inv.immutable_snapshot();cash=wallet()
        with closing(store.connect()) as db:
            db.execute('BEGIN');db.set_authorizer(lambda a,*args:sqlite3.SQLITE_DENY if a in
                (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE) else sqlite3.SQLITE_OK)
            inv.equipment_tip_message(db,item_key,inv.epoch);inv.equipment_bag_messages(db,inv.epoch)
            same=CurrencyChange('identify:fault','npc_equipment_identify','known-level1-fixed-result',(('cash',-100),))
            apply_currency(db,1111,role['id'],inv.epoch,same,inv.currency_rules)
        assert inv.immutable_snapshot()==frozen and wallet()==cash
        foreign=store.create_role(1111,'鉴定他物',12,1010101)
        foreign_inv=Inventory(store,1111,foreign['id'],config,**known_cash_context(store,1111,foreign['id']))
        foreign_key=known_unidentified(store,foreign_inv)
        worn=known_unidentified(store,inv,slot=10);inv.equip(worn,0)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            refused(lambda:inv.equipment_identification_basis(db,foreign_key,inv.epoch))
            refused(lambda:inv.equipment_identification_basis(db,worn,inv.epoch))
        inv.unequip(worn,10)
        unknown=known_unidentified(store,inv,slot=11)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM inventory_equipment_details WHERE item_key=?',(unknown,))
            writes=db.total_changes
            refused(lambda:inv.equipment_identification_basis(db,unknown,inv.epoch))
            assert db.total_changes==writes
        # Missing condition and unknown origin/revision are left untouched.
        malformed=known_unidentified(store,inv,slot=12)
        for column,value in (('revision','future'),('origin','unknown')):
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                db.execute(f'UPDATE inventory_equipment_details SET {column}=? WHERE item_key=?',(value,malformed))
                writes=db.total_changes
                refused(lambda:inv.equipment_identification_basis(db,malformed,inv.epoch))
                assert db.total_changes==writes
                db.rollback()
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');db.execute('DELETE FROM inventory_equipment_conditions WHERE item_key=?',(malformed,))
            writes=db.total_changes
            refused(lambda:inv.equipment_identification_basis(db,malformed,inv.epoch))
            assert db.total_changes==writes
        frozen=inv.immutable_snapshot()
        # Replaced login rejects old epoch even for read-only current tips.
        epoch=store.acquire_lease(1111,role['id'])
        replacement=Inventory(store.leased(1111,role['id'],epoch),1111,role['id'],config,currency_rules=inv.currency_rules)
        with closing(store.connect()) as db:
            db.execute('BEGIN')
            refused(lambda:inv.equipment_tip_message(db,item_key,inv.epoch))
            assert replacement.equipment_tip_message(db,item_key,epoch)[0]==ITEM_TIPS_REPLY
        reopened=Inventory(AccountStore(store.path),1111,role['id'],config,epoch=epoch,currency_rules=inv.currency_rules)
        assert reopened.immutable_snapshot()==frozen
    write_json(OUT/'evidence/equipment-identification-cas-verification.json',{'passed':[
        'explicit carried fixed clean0->1 public CAS and current staged SItemTips: original codec/full parser; only identified changes, inventory revision+1',
        'six original50level templates full native details preserve binding/quality/durability/prefix/score/color/base properties without wearing-policy activation',
        'exact inventory revision and full before JSON/origin plus current role lease; move away/back, changed raw source, restoration-grant0, already1 and bool key/epoch reject',
        'caller cash-only fee composes in same transaction; four actual persistence faults, source callback and late tip/bag encoding roll assets/wallet/receipt back; failed ID retries once',
        'strict readonly current tips/bags/paid cash receipt, no hot configuration, reopen and actual opaque replacement/old-epoch fencing'],
        'npc_ticket_fee_domain_receipt_implemented_here':False,'shared_route_activated':False,'live_server_changed':False,'native_gui_verified':False})
    print('PASS current owned clean0->1 CAS preserves fixed fields and native staged detail; inventory advances once')


if __name__=='__main__':main()
