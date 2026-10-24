"""Isolated public wallet expense recipe; NPC grants are verified separately."""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from accounts import AccountStore
from currency import (CurrencyChange,apply_currency,initialize_wallet,load_currency_rules,
    prepare_wallet_storage,read_wallet)
from inspect_client import OUT,write_json


def main():
    rules=load_currency_rules()
    with TemporaryDirectory(prefix='bound-shop-wallet-') as directory:
        store=AccountStore(Path(directory)/'state.sqlite3')
        role=store.create_role(1111,'绑银购买账本',11,1010109)
        epoch=store.acquire_lease(1111,role['id'])
        with closing(store.connect()) as db:
            prepare_wallet_storage(db)
            def tx(action):
                with db:
                    db.execute('BEGIN IMMEDIATE')
                    return action()
            def wallet(lease=epoch):
                return {r.currency:(r.balance,r.revision) for r in read_wallet(db,1111,role['id'],lease,rules)}
            def pay(change,lease=epoch):
                return apply_currency(db,1111,role['id'],lease,change,rules)
            def refused(action):
                try:tx(action)
                except ValueError:return
                raise AssertionError('Invalid bound shop expense accepted')
            tx(lambda:initialize_wallet(db,1111,role['id'],epoch,(1000,500,0,0),'explicit_migration',rules))
            # Original ordinary shelf: item32000 costs150; actual two-unit order.
            purchase=CurrencyChange('bound-order','npc_shop_bound','npc:10157:item:32000:mode:1',(('bound_silver',-300),))
            first=tx(lambda:pay(purchase))
            assert tx(wallet)==dict(cash=(1000,0),bound_silver=(200,1),yuanbao=(0,0),bound_yuanbao=(0,0))
            assert tx(lambda:pay(purchase))==first
            assert tx(wallet)['bound_silver']==(200,1)
            refused(lambda:pay(replace(purchase,deltas=(('bound_silver',-301),))))
            refused(lambda:pay(replace(purchase,settlement_id='cash-substitute',deltas=(('cash',-300),))))
            refused(lambda:pay(replace(purchase,settlement_id='mixed-order',deltas=(('cash',-100),('bound_silver',-200)))))
            refused(lambda:pay(replace(purchase,settlement_id='insufficient',deltas=(('bound_silver',-201),))))
            refused(lambda:pay(replace(purchase,settlement_id='general-shop',purpose='npc_shop')))
            refused(lambda:pay(replace(purchase,settlement_id='trade',purpose='player_trade')))
            refused(lambda:pay(replace(purchase,settlement_id='yuanbao',deltas=(('yuanbao',-1),))))
            def abort():
                pay(replace(purchase,settlement_id='aborted-order',deltas=(('bound_silver',-150),)))
                raise RuntimeError('controlled caller failure')
            try:tx(abort)
            except RuntimeError:pass
            assert tx(wallet)['bound_silver']==(200,1)
            retry=replace(purchase,settlement_id='aborted-order',deltas=(('bound_silver',-150),))
            tx(lambda:pay(retry))
            assert tx(wallet)['bound_silver']==(50,2)
            # Receipt is historical confirmation; reply callers read current balances.
            assert tx(lambda:pay(purchase))==first
            assert tx(wallet)['bound_silver']==(50,2)
        new_epoch=store.acquire_lease(1111,role['id'])
        with closing(store.connect()) as db,db:
            db.execute('BEGIN')
            try:read_wallet(db,1111,role['id'],epoch,rules)
            except ValueError:pass
            else:raise AssertionError('Stale wallet owner accepted')
            balances={r.currency:r.balance for r in read_wallet(db,1111,role['id'],new_epoch,rules)}
            assert balances==dict(cash=1000,bound_silver=50,yuanbao=0,bound_yuanbao=0)
    result=dict(passed=['dedicated bound expense300 preserves cash1000; same ID once',
        'cash substitution/mixed/general-shop/trade/premium/insufficient/conflicting intent refuse',
        'late caller failure rolls expense/receipt back; same failed ID succeeds once',
        'historical receipt never used as current balance; reconnect50 and old lease refuses'],
        database='disposable',npc_grant_or_shared_route_verified=False,live_server_changed=False,native_gui_verified=False)
    write_json(OUT/'evidence/currency-bound-shop-verification.json',result)
    print(result)


if __name__=='__main__':main()
