"""Additive cash-purpose compatibility and current-wallet payment composition."""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from types import MappingProxyType
import sqlite3
from unittest.mock import patch
from accounts import AccountStore
from currency import (load_currency_rules,prepare_wallet_storage,initialize_wallet,read_wallet,apply_currency,CurrencyChange)
from currency_protocol import encode_currency_balance
from inspect_client import OUT,write_json
import struct


def main():
    with TemporaryDirectory(prefix='identify-currency-') as tmp:
        store=AccountStore(Path(tmp)/'state.sqlite3');role=store.create_role(1111,'鉴定货币',12,1010101)
        epoch=store.acquire_lease(1111,role['id']);rules=load_currency_rules()
        assert 'npc_equipment_identify' in rules.spend_purposes['cash']
        assert all('npc_equipment_identify' not in rules.spend_purposes[name] for name in rules.currencies if name!='cash')
        # Exact earlier policy snapshot: additive purpose changes no revision,
        # baseline, old fingerprint or receipt contents.
        earlier=replace(rules,spend_purposes=MappingProxyType({name:frozenset(p for p in purposes if p!='npc_equipment_identify')
            for name,purposes in rules.spend_purposes.items()}))
        with closing(store.connect()) as db,db:
            prepare_wallet_storage(db);db.execute('BEGIN IMMEDIATE')
            initialize_wallet(db,1111,role['id'],epoch,(30000,90000,300,700),'explicit_migration',earlier)
            old=CurrencyChange('identify:old-shop','npc_shop','old-valid-receipt',(('cash',-1000),))
            historical=apply_currency(db,1111,role['id'],epoch,old,earlier)
            raw=db.execute('SELECT fingerprint,receipt FROM role_wallet_receipts WHERE role_id=? AND settlement_id=?',(role['id'],old.settlement_id)).fetchone()
            fee=CurrencyChange('identify:new50','npc_equipment_identify','known-original50level15000',(('cash',-15000),))
            apply_currency(db,1111,role['id'],epoch,fee,rules)
            assert tuple(r.balance for r in read_wallet(db,1111,role['id'],epoch,rules))==(14000,90000,300,700)
        for deltas in ((('bound_silver',-1),),(('yuanbao',-1),),(('bound_yuanbao',-1),),
                (('cash',-1),('bound_silver',-1)),(('cash',-15000),)):
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE');before=read_wallet(db,1111,role['id'],epoch,rules)
                change=CurrencyChange('identify:refused','npc_equipment_identify','no-substitution',deltas)
                try:apply_currency(db,1111,role['id'],epoch,change,rules)
                except ValueError:pass
                else:raise AssertionError('Noncash/mixed/insufficient identification payment accepted')
                assert read_wallet(db,1111,role['id'],epoch,rules)==before
                assert db.execute('SELECT 1 FROM role_wallet_receipts WHERE role_id=? AND settlement_id=?',(role['id'],change.settlement_id)).fetchone() is None
        with closing(store.connect()) as db:
            db.execute('BEGIN');db.set_authorizer(lambda action,*args:sqlite3.SQLITE_DENY if action in
                (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE) else sqlite3.SQLITE_OK)
            with patch.object(Path,'read_text',side_effect=AssertionError('hot identification currency policy')):
                assert apply_currency(db,1111,role['id'],epoch,old,rules)==historical
                assert db.execute('SELECT fingerprint,receipt FROM role_wallet_receipts WHERE role_id=? AND settlement_id=?',(role['id'],old.settlement_id)).fetchone()==raw
                apply_currency(db,1111,role['id'],epoch,fee,rules)
                current=read_wallet(db,1111,role['id'],epoch,rules)
                assert encode_currency_balance('cash',current[0].balance)==(0xc03fa,struct.pack('>iq',1,14000))
    write_json(OUT/'evidence/equipment-identification-currency-verification.json',{'passed':[
        'additive npc_equipment_identify is cash debit only; original policy revision/old wallet/old receipt fingerprint and body unchanged',
        'original50 quote15000 example cash30000->shop29000->14000; other three balances unchanged, paid emits current absolute14000',
        'noncash/mixed debits and insufficient cash refuse even with bound90000; plans do not partially debit or create a paid receipt',
        'old and new historical receipts SQL-readonly/no hot policy reads under additive rules'],
        'shared_route_activated':False,'live_database_changed':False})
    print('PASS additive cash-only identification purpose, legacy receipt stability, no substitution and read-only current-wallet replay')


if __name__=='__main__':main()
