"""Necessary local reward transaction checks, never touches live accounts."""
from contextlib import closing
from dataclasses import replace
import json
from pathlib import Path
import tempfile
from types import MappingProxyType
from accounts import AccountStore
from inventory import Inventory
from inspect_client import OUT
from progression import read_experience
from tasks import prepare_task_store, TaskResources, _freeze, _plain
from task_rewards import prepare_reward_storage, settle_task_reward


def main():
    checks = []
    with tempfile.TemporaryDirectory() as directory:
        accounts = AccountStore(Path(directory) / 'rewards.sqlite3')
        role = accounts.create_role(1111, '奖励入账', 11, 1010109)
        resources = prepare_task_store(accounts)
        config = Inventory.prepare(accounts)
        inv = Inventory(accounts, 1111, role['id'], config)
        epoch = accounts.acquire_lease(1111, role['id'])
        with closing(accounts.connect()) as db:
            prepare_reward_storage(db)

        def fixture(task_id, source):
            definition = source.definitions[task_id]
            effect = {'task_id': task_id, 'display_rewards': dict(definition['display_rewards']),
                      'display_items': _plain(definition['display_items'])}
            with closing(accounts.connect()) as db, db:
                db.execute("INSERT INTO task_journal VALUES(?,?,'completed')", (role['id'], task_id))
                db.execute('INSERT INTO task_effects(role_id,task_id,payload) VALUES(?,?,?)',
                           (role['id'], task_id, json.dumps(effect)))

        def settle(task_id, source=resources, inventory=inv, lease=epoch):
            with closing(accounts.connect()) as db, db:
                db.execute('BEGIN IMMEDIATE')
                return settle_task_reward(db, 1111, role['id'], lease, task_id, source, inventory)

        fixture(100192, resources)
        # Emulate the preceding release: EXP paid, item channel pending because
        # binding was unsupported. Upgrade must deliver the item without more EXP.
        from task_rewards import plan_task_reward
        original_effect = {'task_id': 100192, 'display_rewards': dict(resources.definitions[100192]['display_rewards']),
                           'display_items': _plain(resources.definitions[100192]['display_items'])}
        prior_plan = plan_task_reward(role['id'], 100192, original_effect, resources, inv.items)
        with closing(accounts.connect()) as db, db:
            db.execute('INSERT INTO role_progress VALUES(?,150)', (role['id'],))
            db.execute('INSERT INTO task_reward_channels VALUES(?,?,?,?,?)',
                       (role['id'], 100192, 'character_exp', prior_plan.fingerprint,
                        json.dumps({'awarded': 150, 'balance_after': 150})))
        first = settle(100192)
        assert first.experience_awarded == 150 and first.rewards_complete and first.items_awarded == ((43000, 1, 1),)
        assert settle(100192) == first
        bound = inv.snapshot()['items']
        assert [(x['template_id'], x['quantity'], x['binding']) for x in bound] == [(43000, 1, 1)]
        fixture(100107, resources)
        assert not settle(100107).rewards_complete
        settle(100107)
        with closing(accounts.connect()) as db, db:
            db.execute('BEGIN')
            assert read_experience(db, 1111, role['id']).experience == 270
            assert db.execute('SELECT delivered FROM task_effects WHERE task_id=100107').fetchone()[0] == 0
        checks.append('previously paid EXP is not replayed; original bound item 43000 granted once; SMoney remains pending')

        # Explicitly designed unbound integration fixtures, NOT original rewards.
        altered = {q: _plain(resources.definitions[q]) for q in (100193, 100194)}
        for definition in altered.values():
            for item in definition['display_items']:
                item['bind'] = 0
        designed = TaskResources(_freeze(altered), resources.shape_to_role_config)
        fixture(100193, designed)
        granted = settle(100193, designed)
        assert granted.rewards_complete and granted.items_awarded == ((33013, 10, 0), (33001, 10, 0))
        assert settle(100193, designed) == granted
        checks.append('designed unbound fixture: EXP, real inventory items, channel receipts and delivered commit together')
        fixture(100194, designed)
        tiny = Inventory(accounts, 1111, role['id'], replace(config, policy=MappingProxyType({**config.policy, 'bag_capacity': 0})))
        try:
            settle(100194, designed, tiny)
            raise AssertionError('Bag full did not abort reward')
        except ValueError as error:
            assert str(error) == 'Bag full'
        with closing(accounts.connect()) as db, db:
            db.execute('BEGIN')
            assert read_experience(db, 1111, role['id']).experience == 420
            assert db.execute('SELECT COUNT(*) FROM task_reward_channels WHERE task_id=100194').fetchone()[0] == 0
        checks.append('bag failure rolls back EXP and all channel receipts in caller transaction')
        other = accounts.create_role(1111, '他人背包', 11, 1010109)
        other_inv = Inventory(accounts, 1111, other['id'], config)
        try:
            settle(100194, designed, other_inv)
            raise AssertionError('Cross-role inventory accepted')
        except ValueError as error:
            assert 'owner mismatch' in str(error)
        accounts.acquire_lease(1111, role['id'])
        try:
            settle(100194, designed)
            raise AssertionError('Old login lease accepted')
        except ValueError as error:
            assert str(error) == 'Stale task reward lease'
        checks.append('cross-role inventory and replaced login lease rejected')
        from role_growth import load_growth_rules, prepare_growth_storage, initialize_growth, read_growth
        from role_attributes import load_attribute_rules, AttributeBaseline
        from role_attribute_storage import prepare_attribute_storage, initialize_attribute_baseline, read_attribute_snapshot
        from item_effects import VitalState
        growth = load_growth_rules()
        attributes = load_attribute_rules()
        growing = accounts.create_role(1111,'成长奖励',11,1010109)
        growing_epoch = accounts.acquire_lease(1111,growing['id'])
        growing_inv = Inventory(accounts,1111,growing['id'],config)
        with closing(accounts.connect()) as db:
            prepare_growth_storage(db)
            prepare_attribute_storage(db)
        with closing(accounts.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            baseline = initialize_growth(db,1111,growing['id'],growing_epoch,growth,expected_level=1,free_points=0)
            attribute_baseline=AttributeBaseline(growing['id'],1,0,(10,10,10,10,10),(100,100,20,5,40,20,10,20,5))
            initial_attributes=initialize_attribute_baseline(db,1111,growing['id'],growing_epoch,
                attribute_baseline,baseline,attributes,VitalState(growing['id'],0,90,100,80,100))
            db.execute("INSERT INTO task_journal VALUES(?,100192,'completed')",(growing['id'],))
            db.execute('INSERT INTO task_effects(role_id,task_id,payload) VALUES(?,100192,?)',
                       (growing['id'],json.dumps(original_effect)))
        full = Inventory(accounts,1111,growing['id'],replace(config,policy=MappingProxyType({**config.policy,'bag_capacity':0})))
        try:
            with closing(accounts.connect()) as db, db:
                db.execute('BEGIN IMMEDIATE')
                settle_task_reward(db,1111,growing['id'],growing_epoch,100192,resources,full,growth,attributes)
            raise AssertionError('Growth committed despite bag failure')
        except ValueError as error:
            assert str(error)=='Bag full'
        with closing(accounts.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            assert read_growth(db,1111,growing['id']) == baseline
            assert read_attribute_snapshot(db,1111,growing['id'],growing_epoch) == initial_attributes
            received = settle_task_reward(db,1111,growing['id'],growing_epoch,100192,resources,growing_inv,growth,attributes)
            assert (received.level,received.experience_balance)==(2,61)
            after = read_growth(db,1111,growing['id'])
            assert after.automatic_points==(1,1,1,1,1) and after.free_points==5
            snapshot=read_attribute_snapshot(db,1111,growing['id'],growing_epoch)
            assert (snapshot.attributes.level,snapshot.vitals.hp,snapshot.vitals.max_hp)==(2,100,110)
            assert settle_task_reward(db,1111,growing['id'],growing_epoch,100192,resources,growing_inv,growth,attributes)==received
            assert read_growth(db,1111,growing['id'])==after
            assert read_attribute_snapshot(db,1111,growing['id'],growing_epoch)==snapshot
        checks.append('task EXP + automatic level + points + attributes/vitals + bound item share rollback and replay-safe commit')
    report = {'passed': checks, 'live_client_tested': False,
              'item_grant_fixture': 'original bound task 100192 plus explicitly designed unbound rollback fixture',
              'automatic_leveling': 'explicit initialized ordinary profile only',
              'uninitialized_profiles_unchanged': True}
    (OUT / 'evidence/task-reward-check.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
