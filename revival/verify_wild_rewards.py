"""Real disposable inventory/XP/wallet transactions for wild battle rewards."""
from contextlib import closing
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
from types import MappingProxyType
from accounts import AccountStore
from inventory import Inventory
from battle import Fighter
from battle_owner import Participant
from training_battle import BattleFinished
from world_owner import Location,MapAddress
from wild_encounters import EncounterTicket, load_wild_rules
from wild_rewards import load_wild_reward_rules, prepare_wild_reward_storage,register_wild_reward,settle_wild_reward
from currency import load_currency_rules,prepare_wallet_storage,initialize_wallet,read_wallet
from progression import read_experience

ROOT = Path(__file__).parent


def main():
    checks = []
    rules, reward, money = load_wild_rules(), load_wild_reward_rules(version='v1'), load_currency_rules()
    with tempfile.TemporaryDirectory(prefix='wild-rewards-') as folder:
        accounts = AccountStore(Path(folder)/'state.sqlite3')
        role = accounts.create_role(1111,'暗雷奖励',11,1010109)
        config = Inventory.prepare(accounts)
        inventory = Inventory(accounts,1111,role['id'],config)
        epoch = accounts.acquire_lease(1111,role['id'])
        area = rules.maps[1014]
        location = Location(role['id'],epoch,MapAddress(1014,1,0),1,896,3776)
        participant = Participant(role['id'],epoch,1,7,role['name'],role['shape'],5,Fighter(1,0))
        ticket = EncounterTicket('reward-fixture',location,area.monsters[0],area.level,area.background,
                                 Fighter(21,1,hp=60,max_hp=60),rules.revision)
        with closing(accounts.connect()) as db:
            prepare_wallet_storage(db); prepare_wild_reward_storage(db); db.commit()
        def tx(call):
            with closing(accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                return call(db)
        tx(lambda db: initialize_wallet(db,1111,role['id'],epoch,(0,0,0,0),'new_restoration_role',money))
        def admission(battle, actor=participant):
            tx(lambda db:register_wild_reward(db,1111,actor,ticket,battle,inventory,reward))
            return BattleFinished(battle,'wild:'+battle,role['id'],0,True,1,rules.revision,
                epoch,7,scope='wild_encounter_v1',outcome='victory')
        def settle(result, inv=inventory):
            return tx(lambda db:settle_wild_reward(db,1111,role['id'],epoch,result,inv,money))
        def balances():
            return tx(lambda db:(read_experience(db,1111,role['id']).experience,
                {r.currency:r.balance for r in read_wallet(db,1111,role['id'],epoch,money)}))
        def rejected(call, error=ValueError):
            try: call()
            except error: return
            raise AssertionError('Invalid command accepted')
        # Pick a deterministic server-ID fixture whose persisted roll drops 白芍.
        index = next(i for i in range(1000) if int.from_bytes(hashlib.sha256(
            ('wild-drop-v1:reward-fixture:drop-'+str(i)).encode()).digest()[:8],'big') % 10000 < 1000)
        result = admission('drop-'+str(index))
        receipt = settle(result)
        assert receipt['items_awarded'] == [[33001,1,1]]
        expected_exp = max(1,reward.costs[5]//100)
        assert receipt['experience_awarded'] == expected_exp
        assert balances() == (expected_exp,dict(cash=0,bound_silver=10,yuanbao=0,bound_yuanbao=0))
        assert [(i['template_id'],i['quantity'],i['binding']) for i in inventory.snapshot()['items']] == [(33001,1,1)]
        assert settle(result)['replayed']
        assert balances()[0] == expected_exp
        checks.append('victory atomically credits real XP, bound silver and bound original item; retry grants once')
        rejected(lambda:settle(replace(result,rounds=2)))
        checks.append('same battle with conflicting terminal result rejected')
        # Caller failure after all channels: entire transaction rolls back.
        pending = admission('outer-failure')
        before = balances()
        def fail(db):
            settle_wild_reward(db,1111,role['id'],epoch,pending,inventory,money)
            raise RuntimeError('outer resource settlement failed')
        rejected(lambda:tx(fail),RuntimeError)
        assert balances() == before
        assert tx(lambda db:db.execute('SELECT receipt FROM wild_reward_admissions WHERE battle_id=?',
                                      (pending.battle_id,)).fetchone()[0]) is None
        assert not settle(pending)['replayed']
        checks.append('outer combat-resource failure rolls back all rewards and receipt; same admission can retry')
        # Force a different-item drop into a capacity-zero bag; no money/XP leak.
        index = next(i for i in range(1000) if 1000 <= int.from_bytes(hashlib.sha256(
            ('wild-drop-v1:reward-fixture:mana-'+str(i)).encode()).digest()[:8],'big') % 10000 < 2000)
        full = admission('mana-'+str(index))
        tiny = Inventory(accounts,1111,role['id'],replace(config,policy=MappingProxyType({**config.policy,'bag_capacity':0})))
        before = balances()
        rejected(lambda:settle(full,tiny))
        assert balances() == before
        assert not settle(full)['replayed']
        checks.append('full bag rolls back XP/money/items together; persisted drop is retained for retry')
        for outcome,winner in (('escape',1),('defeat',1),('draw',-1)):
            loss = replace(admission(outcome),won=False,outcome=outcome,winner_side=winner)
            before = balances()
            receipt = settle(loss)
            assert not receipt['experience_awarded'] and not receipt['silver_awarded'] and not receipt['items_awarded']
            assert balances() == before
        checks.append('escape defeat and draw award nothing')
        high = admission('overlevel',replace(participant,level=16))
        receipt = settle(high)
        assert receipt['experience_awarded'] == receipt['silver_awarded'] == 0 and not receipt['items_awarded']
        checks.append('overlevel suppression uses frozen admission level')
        rejected(lambda:settle(replace(result,battle_id='unregistered',settlement_id='wild:unregistered')))
        rejected(lambda:settle(replace(result,scope='local_training_only')))
        rejected(lambda:admission(result.battle_id,replace(participant,level=6)))
        checks.append('unregistered battle, training scope and changed admission rejected')
        accounts.acquire_lease(1111,role['id'])
        rejected(lambda:settle(result))
        checks.append('old login lease cannot replay even an existing receipt')
    report = dict(checks=checks,passed=len(checks),database='disposable',live_server_changed=False,
        runtime_integrated=False,pet_experience_integrated=False)
    (ROOT/'evidence/wild-rewards-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__ == '__main__': main()
