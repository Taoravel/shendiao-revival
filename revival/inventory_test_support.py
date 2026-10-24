"""Explicit temporary-fixture wallet authority for inventory protocol checks.

Never called by production. Unknown-wallet tests deliberately do not use this.
"""
from contextlib import closing
from currency import load_currency_rules,prepare_wallet_storage,initialize_wallet


def known_cash_context(store, account_id, role_id, *, epoch=None, balances=(0,0,0,0)):
    rules=load_currency_rules()
    with closing(store.connect()) as db:prepare_wallet_storage(db)
    epoch=store.acquire_lease(account_id,role_id) if epoch is None else epoch
    with closing(store.connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        initialize_wallet(db,account_id,role_id,epoch,balances,'explicit_migration',rules)
    return {'epoch':epoch,'currency_rules':rules}
