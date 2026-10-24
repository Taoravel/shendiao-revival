"""Disposable wallet transaction check; never touches the live store or client."""
from contextlib import closing
from pathlib import Path
import tempfile

from accounts import AccountStore
from currency import (CurrencyChange, WalletNotInitialized, apply_currency,
                      initialize_wallet, load_currency_rules, prepare_wallet_storage,
                      read_wallet, task_currency_channels)
from inspect_client import OUT, write_json


def main():
    rules = load_currency_rules()
    result = {'database': 'disposable', 'live_server_changed': False, 'policy': rules.revision}
    with tempfile.TemporaryDirectory(prefix='currency-check-') as folder:
        store = AccountStore(Path(folder)/'state.sqlite3')
        role = store.create_role(1111, '钱包检查', 12, 1010101)
        role_id = role['id']
        epoch = store.acquire_lease(1111, role_id)
        with closing(store.connect()) as db:
            prepare_wallet_storage(db)

            def tx(operation, lease=epoch):
                with db:
                    db.execute('BEGIN IMMEDIATE')
                    return operation(lease)

            def wallet(lease=epoch):
                return {x.currency: x.balance for x in read_wallet(db,1111,role_id,lease,rules)}

            def change(key, currency, delta, purpose='task_reward', lease=epoch):
                return apply_currency(db,1111,role_id,lease,
                    CurrencyChange(key,purpose,'verified-task:210002:SMoney',((currency,delta),)),rules)

            def rejected(operation, error=ValueError):
                try:
                    tx(operation)
                except error:
                    return
                raise AssertionError('Invalid operation was accepted')

            rejected(lambda _: wallet(), WalletNotInitialized)
            tx(lambda _: initialize_wallet(db,1111,role_id,epoch,(0,0,0,0),'new_restoration_role',rules))
            assert task_currency_channels({'MoneyReward':0,'SMoney':5000,'PetExpReward':10000},rules) == (
                ('SMoney','bound_silver',5000),)
            first = tx(lambda _: change('task:210002:instance1','bound_silver',5000))
            assert first == tx(lambda _: change('task:210002:instance1','bound_silver',5000))
            assert tx(lambda _: wallet()) == dict(cash=0,bound_silver=5000,yuanbao=0,bound_yuanbao=0)
            result['task_retry_once_separate_from_cash'] = True
            rejected(lambda _: change('task:210002:instance1','bound_silver',5001))
            rejected(lambda _: change('bound-trade','bound_silver',-1,'player_trade'))
            rejected(lambda _: change('cash-missing','cash',-1,'npc_shop'))
            tx(lambda _: change('known-cash-credit','cash',100))
            tx(lambda _: change('shop-payment','cash',-30,'npc_shop'))
            result['cash_payment_and_bound_spend_refusal'] = True

            def rollback(_):
                change('rollback-credit','cash',999)
                db.execute('UPDATE roles SET level=2 WHERE id=?',(role_id,))
                raise RuntimeError('Caller task/item transaction failed')
            rejected(rollback, RuntimeError)
            assert tx(lambda _: wallet())['cash'] == 70
            assert db.execute('SELECT level FROM roles WHERE id=?',(role_id,)).fetchone()[0] == 1
            assert not db.execute('SELECT 1 FROM role_wallet_receipts WHERE settlement_id=?',('rollback-credit',)).fetchone()
            result['outer_transaction_rolls_back_balance_receipt_and_role'] = True
            # Initialization retries return current state, never the initial zeroes.
            current = tx(lambda _: initialize_wallet(db,1111,role_id,epoch,(0,0,0,0),'new_restoration_role',rules))
            assert {x.currency:x.balance for x in current}['cash'] == 70
            rejected(lambda _: initialize_wallet(db,1111,role_id,epoch,(999,0,0,0),'explicit_migration',rules))
            result['baseline_cannot_reset_existing_balance'] = True
            old_receipt = tx(lambda _: change('task:210002:instance1','bound_silver',5000))
            assert old_receipt == first and tx(lambda _: wallet())['cash'] == 70
            new_epoch = store.acquire_lease(1111,role_id)
            rejected(lambda _: change('expired','cash',1))
            assert tx(lambda lease: wallet(lease), new_epoch)['cash'] == 70
            result['expired_epoch_rejected'] = True
    write_json(OUT/'evidence/currency-verification.json',result)
    print(result)


if __name__ == '__main__':
    main()
