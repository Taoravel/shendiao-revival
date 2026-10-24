"""Task currency channels: explicit wallet, delayed settlement and atomic rollback."""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
import json
import struct
import tempfile
from accounts import AccountStore
from inspect_client import OUT
from inventory import Inventory
from tasks import prepare_task_store,_plain
from task_rewards import prepare_reward_storage,settle_task_reward
from progression import read_experience
from task_workflow import TaskCompletion,completion_messages
from currency import (load_currency_rules,prepare_wallet_storage,initialize_wallet,
    read_wallet,apply_currency,CurrencyChange,LIMIT)


def main():
    rules=load_currency_rules()
    with tempfile.TemporaryDirectory() as directory:
        accounts=AccountStore(Path(directory)/'task-currency.sqlite3')
        resources=prepare_task_store(accounts)
        config=Inventory.prepare(accounts)
        with closing(accounts.connect()) as db:
            prepare_reward_storage(db);prepare_wallet_storage(db)
        def role_and_effect(name):
            role=accounts.create_role(1111,name,11,1010109)
            epoch=accounts.acquire_lease(1111,role['id'])
            inv=Inventory(accounts,1111,role['id'],config)
            definition=resources.definitions[210002]
            effect={'task_id':210002,'display_rewards':dict(definition['display_rewards']),
                    'display_items':_plain(definition['display_items'])}
            with closing(accounts.connect()) as db,db:
                db.execute("INSERT INTO task_journal VALUES(?,210002,'completed')",(role['id'],))
                db.execute('INSERT INTO task_effects(role_id,task_id,payload) VALUES(?,210002,?)',
                           (role['id'],json.dumps(effect)))
            return role,epoch,inv
        role,epoch,inv=role_and_effect('货币任务')
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            pending=settle_task_reward(db,1111,role['id'],epoch,210002,resources,inv,currency_rules=rules)
            assert pending.experience_awarded==20000 and pending.currency_awarded==()
            assert ('SMoney',5000,'wallet_not_initialized') in pending.pending
            assert db.execute('SELECT COUNT(*) FROM role_wallet_profiles').fetchone()[0]==0
            initialize_wallet(db,1111,role['id'],epoch,(100,0,0,0),'explicit_migration',rules)
            paid=settle_task_reward(db,1111,role['id'],epoch,210002,resources,inv,currency_rules=rules)
            assert paid.currency_awarded==(('SMoney','bound_silver',5000),)
            assert [x.balance for x in paid.wallet]==[100,5000,0,0]
            assert ('PetExpReward',10000,'explicit_recipient_reconciliation') in paid.pending
            assert not paid.rewards_complete
            apply_currency(db,1111,role['id'],epoch,
                CurrencyChange('later-spend','npc_shop','explicit-test-spend',(('cash',-10),)),rules)
            apply_currency(db,1111,role['id'],epoch,
                CurrencyChange('later-bound-credit','test_reward','separate-reward-fixture',(('bound_silver',700),)),rules)
            again=settle_task_reward(db,1111,role['id'],epoch,210002,resources,inv,currency_rules=rules)
            assert [x.balance for x in again.wallet]==[90,5700,0,0]
            assert read_experience(db,1111,role['id']).experience==20000
            assert db.execute('SELECT delivered FROM task_effects WHERE role_id=?',(role['id'],)).fetchone()[0]==0
        # Generate logical refreshes only after the transaction committed.
        messages=completion_messages(TaskCompletion(None,again))
        assert messages[2:]==((0xc03fa,struct.pack('>iq',1,90)),(0xc0012,struct.pack('>q',5700)))
        assert len(completion_messages(TaskCompletion(None,pending)))==2
        try:
            with closing(accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                settle_task_reward(db,1111,role['id'],epoch,210002,resources,inv,currency_rules=replace(rules,revision='future-policy'))
            raise AssertionError('Wallet policy changed without migration')
        except ValueError as error:
            assert 'migration required' in str(error)
        over,over_epoch,over_inv=role_and_effect('货币溢出')
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            initialize_wallet(db,1111,over['id'],over_epoch,(0,LIMIT-4999,0,0),'explicit_migration',rules)
        try:
            with closing(accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                settle_task_reward(db,1111,over['id'],over_epoch,210002,resources,over_inv,currency_rules=rules)
            raise AssertionError('Overflowing currency committed')
        except ValueError as error:
            assert 'overflowing currency' in str(error)
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN')
            assert read_experience(db,1111,over['id']).experience==0
            assert db.execute('SELECT COUNT(*) FROM task_reward_channels WHERE role_id=?',(over['id'],)).fetchone()[0]==0
            assert read_wallet(db,1111,over['id'],over_epoch,rules)[1].balance==LIMIT-4999
        report={'passed':['original task210002: 20000 XP once; no wallet stays pending without creating profile',
            'explicit wallet enables one SMoney5000 bound-silver credit; cash unchanged',
            'replay does not repeat XP/currency and returns current wallet after later spending',
            'post-commit cash/bound-silver refresh uses 90/5700 current balances, no yuanbao or unknown-wallet packets',
            'PetExpReward remains pending; policy mismatch refuses migration; overflow rolls back all channels'],
            'currency_mapping':'designed','native_currency_ui_tested':False}
    (OUT/'evidence/task-currency-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__': main()
