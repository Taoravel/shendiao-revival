"""Public identification/fee composition with the actual sole resource source."""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import sqlite3
from accounts import AccountStore
from inventory import Inventory
from currency import CurrencyChange,apply_currency,read_wallet
from verify_resource_owner_runtime import fixture
from role_equipment_storage import current_resource_profile
from role_resource_storage import read_role_resources
from inspect_client import OUT,write_json
import runtime_storage


def main():
    with TemporaryDirectory(prefix='identify-source-') as tmp:
        store=AccountStore(Path(tmp)/'state.sqlite3');role=store.create_role(1111,'鉴定来源',11,1010109)
        runtime_storage.prepare(store)
        npc=next(p for rows in store.npc_resources[0].values() for p in rows if p.npc_id==10004)
        fixture(store,role,npc)
        with closing(store.connect()) as db:
            epoch=db.execute('SELECT epoch FROM role_leases WHERE role_id=?',(role['id'],)).fetchone()[0]
        inv=Inventory(store.leased(1111,role['id'],epoch),1111,role['id'])
        with closing(inv.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            key=db.execute('INSERT INTO inventory_items(role_id,template_id,quantity,slot,binding) VALUES(?,40200,1,2,1)',(role['id'],)).lastrowid
            inv.initialize_equipment_condition(db,key,42,80,1)
            inv.initialize_equipment_detail(db,key,replace(inv.detail_rules.generate(40200),identified=0))
            runtime_storage._synchronize_source(db,store,inv,'identify:explicit-fixture-source',replayed=False)
        def current():
            with closing(inv.accounts.connect()) as db:
                db.execute('BEGIN');assets=inv.immutable_snapshot_transaction(db)
                profile=current_resource_profile(db,1111,role['id'],epoch,assets,
                    equipment_rules=store.equipment_attribute_rules,resource_rules=store.resource_rules)
                resources=read_role_resources(db,1111,role['id'],epoch,store.resource_rules)
                assert (profile.vitals.hp,profile.vitals.mp,profile.vitals.version)==(10,20,0)
                counts=tuple(db.execute('SELECT COUNT(*) FROM '+table+' WHERE role_id=?',(role['id'],)).fetchone()[0]
                    for table in ('role_resource_receipts','role_wallet_receipts'))
                return assets,resources,read_wallet(db,1111,role['id'],epoch,store.currency_rules),counts
        fee=CurrencyChange('identify:source-fee','npc_equipment_identify','known-level1-fixed-result',(('cash',-100),))
        def perform(*,fail_after_source=False):
            with closing(inv.accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE');basis=inv.equipment_identification_basis(db,key,epoch)
                apply_currency(db,1111,role['id'],epoch,fee,store.currency_rules)
                def hook(db,inventory,assets,*,replayed):
                    assert not replayed and inventory is inv
                    result=runtime_storage._synchronize_source(db,store,inv,'identify:source-operation',replayed=replayed)
                    assert result.caps.source.inventory_revision==assets.inventory_revision
                    if fail_after_source:raise RuntimeError('after actual resource source CAS')
                inv.identify_equipment_clean_transaction(db,basis,epoch,precommit=hook)
                inv.equipment_tip_message(db,key,epoch);inv.equipment_bag_messages(db,epoch)
        before=current()
        for table in ('role_resource_receipts',):
            with closing(store.connect()) as db,db:
                db.execute(f"CREATE TRIGGER identify_root_fault BEFORE INSERT ON {table} BEGIN SELECT RAISE(ABORT,'real identification source receipt failed'); END")
            try:perform()
            except sqlite3.IntegrityError:pass
            else:raise AssertionError('Real root source receipt failure committed identification')
            assert current()==before
            with closing(store.connect()) as db,db:db.execute('DROP TRIGGER identify_root_fault')
        try:perform(fail_after_source=True)
        except RuntimeError:pass
        else:raise AssertionError('Post-source failure committed fee/detail/source')
        assert current()==before
        with patch('equipment_detail.encode',side_effect=RuntimeError('late current native detail')):
            try:perform()
            except RuntimeError:pass
            else:raise AssertionError('Late native representation failure committed')
        assert current()==before
        perform();after=current()
        assert after[0].inventory_revision==before[0].inventory_revision+1
        assert after[2][0].balance==1900 and after[1].version==before[1].version==0
        assert (after[1].hp,after[1].mp,after[1].caps.hp_max,after[1].caps.mp_max)==(
            before[1].hp,before[1].mp,before[1].caps.hp_max,before[1].caps.mp_max)
        assert after[1].caps.source!=before[1].caps.source
        # Paid caller validates its own NPC intent/receipt, skips the mutator,
        # and strictly reads current item/wallet/source. No pending repair.
        with closing(store.connect()) as db:
            db.execute('BEGIN');db.set_authorizer(lambda a,*args:sqlite3.SQLITE_DENY if a in
                (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE) else sqlite3.SQLITE_OK)
            apply_currency(db,1111,role['id'],epoch,fee,store.currency_rules)
            runtime_storage._synchronize_source(db,store,inv,'identify:source-operation',replayed=True)
            inv.equipment_tip_message(db,key,epoch);inv.equipment_bag_messages(db,epoch)
        assert current()==after
    write_json(OUT/'evidence/equipment-identification-source-verification.json',{'passed':[
        'public clean CAS and actual cash fee synchronize the sole current root source in the caller transaction, default role equipment policy unchanged',
        'actual resource receipt insert, exception after actual source CAS and late current detail encoding all roll item/cash/source/all receipts back; failed stable fee ID retries once',
        'HP10/MP20/version0 and equipped final caps preserved; asset/source revision changes, no second resource store or healing',
        'paid fee/current tips/bags/actual replayed root-source branch are strictly SQL-readonly'],
        'npc_confirmation_or_shared_route_tested':False,'database':'disposable','shared_files_changed':False,'live_server_changed':False,'native_gui_verified':False})
    print('PASS actual sole root source + cash + public clean CAS atomic rollback and strict current read-only paid branch')


if __name__=='__main__':main()
