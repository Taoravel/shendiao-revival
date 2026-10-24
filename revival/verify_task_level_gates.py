"""Necessary trusted level-goal waiting/completion checks; temporary DB only."""
from contextlib import closing
from pathlib import Path
import json
import tempfile
from accounts import AccountStore
from inspect_client import OUT
from inventory import Inventory
from tasks import prepare_task_store
from task_domain import TaskDomain,TaskEvidence,supports_level_gate
from task_persistence import load_task_state,apply_task_plan
from task_rewards import prepare_reward_storage
from task_level_gates import advance_level_gates,level_gate_messages
from task_conversation import TaskConversation
from task_protocol import decode_accept_scenario_quest,decode_scenario_values


def main():
    with tempfile.TemporaryDirectory() as directory:
        accounts=AccountStore(Path(directory)/'level-goals.sqlite3')
        resources=prepare_task_store(accounts)
        role=accounts.create_role(1111,'等级目标',11,1010109)
        epoch=accounts.acquire_lease(1111,role['id'])
        inv=Inventory(accounts,1111,role['id'],Inventory.prepare(accounts))
        with closing(accounts.connect()) as db:
            prepare_reward_storage(db)
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('UPDATE roles SET level=17 WHERE id=?',(role['id'],))
            actor,state=load_task_state(db,1111,role['id'],epoch)
            wait=TaskDomain(resources).plan(actor,state,'wait_level',102061)
            apply_task_plan(db,actor,wait,'authorized-chapter-level-wait')
            actor,state=load_task_state(db,1111,role['id'],epoch)
            restored=TaskConversation(resources,role['id'],epoch).resume_messages(actor,state)
            assert decode_accept_scenario_quest(restored[0][1]).value1==17
            before=advance_level_gates(db,1111,role['id'],epoch,resources,inv)
            assert not before.completions and decode_scenario_values(before.progress[0][1])==(102061,17,0)
            try:
                TaskDomain(resources).plan(actor,state,'complete',102061,evidence=TaskEvidence(
                    102061,role['id'],epoch,'role_level_reached','forged-level',reference_id=18))
                raise AssertionError('Claimed level bypassed actor')
            except ValueError:
                pass
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('UPDATE roles SET level=18 WHERE id=?',(role['id'],))
            done=advance_level_gates(db,1111,role['id'],epoch,resources,inv)
            assert tuple(c.rewards.task_id for c in done.completions)==(102061,)
            assert done.completions[0].rewards.experience_awarded==0
            assert not advance_level_gates(db,1111,role['id'],epoch,resources,inv).completions
            assert any(kind==0xc4a47 for kind,_ in level_gate_messages(done))
            assert db.execute("SELECT state FROM task_journal WHERE role_id=? AND task_id=102061",(role['id'],)).fetchone()[0]=='completed'
        assert not supports_level_gate(resources.definitions[209302])
        assert not supports_level_gate(resources.definitions[224302])
        # A real reward-bearing level goal is rolled back with the outer level.
        try:
            with closing(accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                actor,state=load_task_state(db,1111,role['id'],epoch)
                apply_task_plan(db,actor,TaskDomain(resources).plan(actor,state,'wait_level',102094),'gift-wait')
                gift=advance_level_gates(db,1111,role['id'],epoch,resources,inv)
                assert gift.completions[0].rewards.experience_awarded==10000
                raise RuntimeError('controlled outer rollback')
        except RuntimeError:
            pass
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN')
            assert db.execute('SELECT 1 FROM task_journal WHERE role_id=? AND task_id=102094',(role['id'],)).fetchone() is None
        count=sum(supports_level_gate(t) for t in resources.definitions.values())
        report=dict(passed=['102061 enrolls at17 without relaxing normal offer minimum; resume/current value1=17',
            'forged18 cannot complete current17; authoritative18 completes once with original zero reward',
            '102094 original10000XP and task receipts roll back with outer failure; phone-bind/special58 excluded'],
            independent_level_goals=count,client_verified='resources and value1 renderer',
            completion_timing='designed',live_runtime_tested=False,live_client_tested=False)
    (OUT/'evidence/task-level-gates-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':
    main()
