"""Necessary offline task/pet reward checks; temporary databases only."""
from contextlib import closing
from dataclasses import replace
import json
from pathlib import Path
import struct
import tempfile
from accounts import AccountStore
from inventory import Inventory, pet_record
from inspect_client import OUT
from tasks import prepare_task_store
from task_domain import TaskDomain, TaskEvidence
from task_persistence import load_task_state, apply_task_plan
from task_rewards import prepare_reward_storage, settle_task_reward
from task_workflow import complete_task_transaction, completion_messages, refresh_completion_pet
from task_pet_experience import load_task_pet_experience_rules
from role_growth import load_growth_rules, prepare_growth_storage, initialize_growth
from progression import read_experience
from role_attributes import load_attribute_rules, AttributeBaseline
from role_attribute_storage import prepare_attribute_storage, initialize_attribute_baseline
from role_attribute_protocol import growth_refresh
from role_growth import read_growth
from item_effects import VitalState


def main():
    rules = load_task_pet_experience_rules()
    character_rules = load_growth_rules()
    attribute_rules = load_attribute_rules()
    checks = []
    with tempfile.TemporaryDirectory() as directory:
        count = 0

        def fixture(role_level=20, pet_level=25, selected=True, task_id=210002, character_growth=False,
                    attribute_growth=False, hp_max=100):
            nonlocal count
            count += 1
            accounts = AccountStore(Path(directory)/f'pet-task-{count}.sqlite3')
            role = accounts.create_role(1111,'任务宠经验',11,1010109)
            epoch = accounts.acquire_lease(1111,role['id'])
            resources = prepare_task_store(accounts)
            inv = Inventory(accounts,1111,role['id'],Inventory.prepare(accounts))
            with closing(accounts.connect()) as db:
                prepare_reward_storage(db)
                prepare_growth_storage(db)
                prepare_attribute_storage(db)
            with closing(accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                db.execute('UPDATE roles SET level=? WHERE id=?',(role_level,role['id']))
                if character_growth:
                    baseline = initialize_growth(db,1111,role['id'],epoch,character_rules,
                                                 expected_level=role_level,free_points=0)
                    if attribute_growth:
                        attributes = AttributeBaseline(role['id'],role_level,0,(10,10,10,10,10),
                                                        (hp_max,100,20,5,40,20,10,20,5))
                        initialize_attribute_baseline(db,1111,role['id'],epoch,attributes,baseline,
                            attribute_rules,VitalState(role['id'],0,90,hp_max,80,100))
            pet = inv.grant_pet(500001)
            if selected:
                inv.fight_pet(pet)
            with closing(accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                old = inv.pet_progress(db,pet)
                amount = sum(inv.growth_rules.thresholds[x] for x in range(old.state.level,pet_level))
                if amount:
                    inv.change_pet_growth(db,pet,'fixture-level',old.state.version,'experience',amount)
                for action in ('offer','accept'):
                    actor,state = load_task_state(db,1111,role['id'],epoch)
                    apply_task_plan(db,actor,TaskDomain(resources).plan(actor,state,action,task_id),action)
                actor,state = load_task_state(db,1111,role['id'],epoch)
                target = resources.definitions[task_id]['target']
                evidence = TaskEvidence(task_id,role['id'],epoch,'npc_dialogue_completed',
                                        'controlled-offline-proof',target['map_id'],target['npc_id'])
                plan = TaskDomain(resources).plan(actor,state,'complete',task_id,evidence=evidence)
            return accounts,inv,resources,actor,plan,pet

        def finish(fixture, **kwargs):
            accounts,inv,resources,actor,plan,pet = fixture
            with closing(accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                result = complete_task_transaction(db,actor,plan,'complete',resources,inv,
                    pet_experience_rules=rules,**kwargs)
            return result

        f = fixture()
        accounts,inv,resources,actor,plan,pet = f
        paid = finish(f)
        assert paid.rewards.pet_experience.status == 'awarded'
        assert not any(kind in (0xc07d5,0xc07d6) for kind,_ in completion_messages(paid))
        other = inv.grant_pet(500001)
        inv.fight_pet(other)
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            p = inv.pet_progress(db,pet)
            assert (p.state.level,p.state.experience) == (25,10000)
            inv.change_pet_growth(db,pet,'later-credit',p.state.version,'experience_capped',(7,25))
        replay = finish(f)
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN')
            current = refresh_completion_pet(db,actor,replay,inv)
            assert inv.pet_progress(db,other).state.experience == 0
            assert read_experience(db,1111,actor.role_id).experience == 20000
            snapshot = current.rewards.pet_experience.current_pet
            assert snapshot.id == pet and snapshot.progress.state.experience == 10007
            assert completion_messages(current)[-2:] == (
                (0xc07d5,pet_record(snapshot.__dict__)),(0xc07d6,struct.pack('>iQ',pet,10007)))
            decision = json.loads(db.execute('SELECT payload FROM task_pet_reward_decisions').fetchone()[0])
            assert decision['recipient_id'] == pet and decision['award_cap'] == 25
        inv.free_pet(pet)
        missing = finish(f)
        assert missing.rewards.pet_experience.reason == 'original_recipient_unavailable_audit'
        checks.append('original210002: +5 pet retains10000XP at cap; switch/retry never reroutes; refresh re-reads10007 for original key; released recipient stays audit')

        before = fixture(role_level=5,pet_level=10,character_growth=True,attribute_growth=True)
        result = finish(before,growth_rules=character_rules,attribute_rules=attribute_rules)
        assert result.rewards.level == 10
        with closing(before[0].connect()) as db,db:
            db.execute('BEGIN')
            state = before[1].pet_progress(db,before[5]).state
            decision = json.loads(db.execute('SELECT payload FROM task_pet_reward_decisions').fetchone()[0])
            assert (state.level,state.experience,decision['role_level'],decision['award_cap']) == (10,10000,5,10)
            assert result.growth_messages == (growth_refresh(read_growth(db,1111,before[3].role_id),result.attributes),)
            assert result.growth_messages[0][0] == 0xc32c8
        checks.append('capture before character EXP: role5->10 still uses pet cap10; current19-field native role growth refresh preencoded')

        for pet_level,selected,dead,reason in ((26,True,False,'pet_above_captured_level_cap'),
                (25,False,False,'no_selected_pet'),(25,True,True,'pet_dead')):
            f = fixture(pet_level=pet_level,selected=selected)
            if dead:
                with closing(f[0].connect()) as db,db:
                    db.execute('BEGIN IMMEDIATE')
                    p = f[1].pet_progress(db,f[5])
                    f[1].change_pet_growth(db,f[5],'fixture-dead',p.state.version,'resources',(0,p.state.mp))
            result = finish(f)
            assert (result.rewards.pet_experience.status,result.rewards.pet_experience.reason) == ('not_awarded',reason)
            assert not any(x[0]=='PetExpReward' for x in result.rewards.pending)
            with closing(f[0].connect()) as db,db:
                db.execute('BEGIN')
                assert f[1].pet_progress(db,f[5]).state.experience == 0
            assert finish(f).rewards.pet_experience.status == 'not_awarded'
        checks.append('+6/no selected/dead: terminal original-amount not_awarded, no growth mutation or later reclaim')
        under = fixture(role_level=1,pet_level=0)
        result = finish(under)
        assert result.rewards.pet_experience.reason == 'role_below_original_uselevel'

        unknown = fixture()
        with closing(unknown[0].connect()) as db,db:
            db.execute('DELETE FROM inventory_pet_growth WHERE pet_id=?',(unknown[5],))
        result = finish(unknown)
        assert result.rewards.pet_experience.reason == 'explicit_pet_baseline_reconciliation'
        with closing(unknown[0].connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            unknown[1].initialize_pet_growth(db,unknown[5])
        assert finish(unknown).rewards.pet_experience.status == 'pending'
        # Old completed row with no capture must never select the current pet.
        legacy = fixture()
        with closing(legacy[0].connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            apply_task_plan(db,legacy[3],legacy[4],'old-completion-without-recipient')
            old = settle_task_reward(db,1111,legacy[3].role_id,legacy[3].login_epoch,210002,
                                     legacy[2],legacy[1],pet_experience_rules=rules)
            assert old.pet_experience.reason == 'explicit_recipient_reconciliation'
            assert db.execute('SELECT COUNT(*) FROM task_pet_reward_decisions').fetchone()[0] == 0
            assert legacy[1].pet_progress(db,legacy[5]).state.experience == 0
        checks.append('unknown growth freezes original pet; later initialization still requires reconciliation; old completed task never picks current pet')

        overflow = fixture()
        with closing(overflow[0].connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            p = overflow[1].pet_progress(db,overflow[5])
            overflow[1].change_pet_growth(db,overflow[5],'fixture-full',p.state.version,
                                         'experience_capped',(2147483647-9999,25))
        try:
            finish(overflow)
            raise AssertionError('Overflow award committed')
        except ValueError as error:
            assert 'overflow' in str(error)
        with closing(overflow[0].connect()) as db,db:
            db.execute('BEGIN')
            assert db.execute('SELECT state FROM task_journal').fetchone()[0] == 'active'
            assert db.execute('SELECT COUNT(*) FROM task_pet_reward_decisions').fetchone()[0] == 0
            assert db.execute('SELECT COUNT(*) FROM task_reward_channels').fetchone()[0] == 0
            assert read_experience(db,1111,overflow[3].role_id).experience == 0
        zero = fixture(task_id=100192)
        result = finish(zero)
        assert result.rewards.pet_experience.status == 'zero'
        with closing(zero[0].connect()) as db,db:
            db.execute('BEGIN')
            assert zero[1].pet_progress(db,zero[5]).state.version == 1  # only fixture-level
        checks.append('pet XP overflow rolls back task/recipient/characterXP/receipts; original100192 zero does not mutate pet')
        failed_items = fixture()
        class FailingInventory(Inventory):
            def apply_settlement(self, db, change):
                super().apply_settlement(db,change)
                raise RuntimeError('controlled item channel failure after pet XP')
        failing = FailingInventory(failed_items[0],1111,failed_items[3].role_id)
        try:
            finish((*failed_items[:1],failing,*failed_items[2:]))
            raise AssertionError('Partial pet reward committed after item failure')
        except RuntimeError:
            pass
        with closing(failed_items[0].connect()) as db,db:
            db.execute('BEGIN')
            assert failed_items[1].pet_progress(db,failed_items[5]).state.experience == 0
            assert db.execute('SELECT state FROM task_journal').fetchone()[0] == 'active'
            assert db.execute('SELECT COUNT(*) FROM task_reward_channels').fetchone()[0] == 0
            assert read_experience(db,1111,failed_items[3].role_id).experience == 0
        checks.append('failure after pet and character XP rolls back both assets, task and channel receipts')
        invalid_wire = fixture(task_id=100192,character_growth=True,attribute_growth=True,hp_max=16777217)
        try:
            finish(invalid_wire,growth_rules=character_rules,attribute_rules=attribute_rules)
            raise AssertionError('Unrepresentable native role value committed')
        except ValueError as error:
            assert 'exactly representable' in str(error)
        with closing(invalid_wire[0].connect()) as db,db:
            db.execute('BEGIN')
            assert db.execute('SELECT state FROM task_journal').fetchone()[0] == 'active'
            assert db.execute('SELECT COUNT(*) FROM task_reward_channels').fetchone()[0] == 0
            assert db.execute('SELECT COUNT(*) FROM inventory_items').fetchone()[0] == 0
            assert read_experience(db,1111,invalid_wire[3].role_id).experience == 0
        checks.append('original uselevel5 disqualifies role1; native role float precision failure rolls back task/XP/bound item/receipts')
    report = dict(passed=checks,source_amount='client_verified',recipient_policy='designed',
                  live_runtime_tested=False,live_client_tested=False)
    (OUT/'evidence/task-pet-experience-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__ == '__main__':
    main()
