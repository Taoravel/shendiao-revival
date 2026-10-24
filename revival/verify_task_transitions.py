"""Small offline acceptance check; no live server or account mutations."""
from contextlib import closing
import builtins
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
from accounts import AccountStore
from inspect_client import OUT
from tasks import prepare_task_store, TaskStore
from task_domain import TaskDomain, TaskEvidence, TaskSnapshot
from task_persistence import load_task_state, apply_task_plan, get_task_receipt


def main():
    checks = []
    with tempfile.TemporaryDirectory() as directory:
        accounts = AccountStore(Path(directory) / 'tasks.sqlite3')
        role = accounts.create_role(1111, '任务推进', 11, 1010109)
        resources = prepare_task_store(accounts)
        domain = TaskDomain(resources)
        with closing(accounts.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            actor, state = load_task_state(db, 1111, role['id'], 1)
            offer = domain.plan(actor, state, 'offer', 100192)
            apply_task_plan(db, actor, offer, 'offer-100192')
        with closing(accounts.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            actor, state = load_task_state(db, 1111, role['id'], 1)
            with patch.object(builtins, 'open', side_effect=AssertionError('Domain read a file')):
                assert domain.available(actor, state) == (100192,)
                accept = domain.plan(actor, state, 'accept', 100192)
            apply_task_plan(db, actor, accept, 'accept-100192')
        evidence = TaskEvidence(100192, role['id'], 1, 'npc_dialogue_completed', 'map-event-1', 1006, 10899)
        with closing(accounts.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            actor, state = load_task_state(db, 1111, role['id'], 1)
            complete = domain.plan(actor, state, 'complete', 100192, evidence=evidence)
            assert complete.reward_scalars == (('ExpReward', 150), ('MoneyReward', 0), ('PetExpReward', 0), ('SMoney', 0), ('ShengWang', 0))
            assert complete.reward_items == ((43000, 1, 1),)
            receipt = apply_task_plan(db, actor, complete, 'complete-100192')
            assert apply_task_plan(db, actor, complete, 'complete-100192') == receipt
        checks.append('native task 100192 offer/accept/complete; original 150 EXP and bound item preserved as pending')
        with closing(accounts.connect()) as db, db:
            db.execute('BEGIN')
            _, state = load_task_state(db, 1111, role['id'], 2)
            assert 100192 in state.completed
            assert get_task_receipt(db, 1111, role['id'], 'complete-100192') == receipt
            assert db.execute('SELECT COUNT(*) FROM task_effects').fetchone()[0] == 1
        checks.append('one durable completion effect and receipt recoverable after reconnect')
        # Caller rollback must undo task state and receipt together.
        try:
            with closing(accounts.connect()) as db, db:
                db.execute('BEGIN IMMEDIATE')
                actor, state = load_task_state(db, 1111, role['id'], 2)
                plan = domain.plan(actor, state, 'offer', 100160)
                apply_task_plan(db, actor, plan, 'rollback-offer')
                raise RuntimeError('controlled caller rollback')
        except RuntimeError:
            pass
        with closing(accounts.connect()) as db, db:
            db.execute('BEGIN')
            actor, state = load_task_state(db, 1111, role['id'], 2)
            assert 100160 not in state.offered
            assert get_task_receipt(db, 1111, role['id'], 'rollback-offer') is None
        checks.append('caller transaction rollback removes both task mutation and receipt')
        stale = domain.plan(actor, state, 'offer', 100160)
        TaskStore(accounts, resources=resources).offer(1111, role['id'], 100160)
        try:
            with closing(accounts.connect()) as db, db:
                db.execute('BEGIN IMMEDIATE')
                apply_task_plan(db, actor, stale, 'stale-offer')
            raise AssertionError('Stale plan survived legacy write')
        except ValueError as error:
            assert str(error) == 'Stale task or character snapshot'
        checks.append('legacy adapter mutation invalidates older task plans')
        # Original 100107 names AI 8001; an unrelated victory is not proof.
        battle_state = TaskSnapshot(role['id'], active=frozenset({100107}))
        wrong = TaskEvidence(100107, role['id'], 2, 'battle_won', 'battle-1', reference_id=8002)
        try:
            domain.plan(actor, battle_state, 'complete', 100107, evidence=wrong)
            raise AssertionError('Accepted unrelated battle')
        except ValueError:
            pass
        checks.append('unrelated task battle rejected')
    report = {'passed': checks, 'live_client_tested': False, 'rewards_granted': False,
              'concurrency_capacity_tested': False}
    (OUT / 'evidence/task-transition-check.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
