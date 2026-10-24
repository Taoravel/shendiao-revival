"""Actual runtime storage completion: commit, post-read failure and safe replay.

Disposable trusted task fixture only; no listener, GUI or battle runs.
"""
from contextlib import closing
from pathlib import Path
import struct
import tempfile
from unittest.mock import patch
from accounts import AccountStore
from inventory import Inventory,REFRESH_PET_EXP
from inspect_client import OUT,write_json
from task_domain import TaskDomain,TaskEvidence
from task_persistence import load_task_state,apply_task_plan
from task_workflow import completion_messages
import runtime_storage


def main():
    with tempfile.TemporaryDirectory(prefix='task-pet-storage-') as directory:
        accounts=AccountStore(Path(directory)/'task-pet.sqlite3')
        # Explicit old-role fixture, not the newly authorized creation template.
        role=accounts.create_role(1111,'任务接线宠',11,1010109)
        prepared=runtime_storage.prepare(accounts)
        epoch=accounts.acquire_lease(1111,role['id'])
        leased=accounts.leased(1111,role['id'],epoch)
        inv=Inventory(leased,1111,role['id'])
        pet=inv.grant_pet(500001)
        inv.fight_pet(pet)
        resources=prepared[0]
        with closing(leased.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('UPDATE roles SET level=20 WHERE id=?',(role['id'],))
            current=inv.pet_progress(db,pet)
            amount=sum(inv.growth_rules.thresholds[x] for x in range(current.state.level,25))
            inv.change_pet_growth(db,pet,'fixture-level',current.state.version,'experience',amount)
            for action in ('offer','accept'):
                actor,state=load_task_state(db,1111,role['id'],epoch)
                apply_task_plan(db,actor,TaskDomain(resources).plan(actor,state,action,210002),action)
            actor,state=load_task_state(db,1111,role['id'],epoch)
            target=resources.definitions[210002]['target']
            evidence=TaskEvidence(210002,role['id'],epoch,'npc_dialogue_completed',
                'offline-storage-fixture',target['map_id'],target['npc_id'])
            plan=TaskDomain(resources).plan(actor,state,'complete',210002,evidence=evidence)
        calls=[]

        def fail_post_read(db,actor,completion,inventory):
            # A separate connection sees this only after the first COMMIT.
            with closing(accounts.connect()) as reader:
                assert reader.execute('SELECT state FROM task_journal WHERE role_id=? AND task_id=210002',
                                      (role['id'],)).fetchone()==('completed',)
            assert completion.rewards.pet_experience.current_pet is None
            calls.append('committed before post-read')
            raise RuntimeError('controlled post-commit read failure')

        with patch.object(runtime_storage,'refresh_completion_pet',fail_post_read):
            try:
                runtime_storage.complete_conversation(accounts,1111,role['id'],epoch,
                    actor,plan,'completion',resources,inv)
            except RuntimeError as error:
                assert str(error)=='controlled post-commit read failure'
            else:raise AssertionError('Post-commit failure was hidden')
        assert calls==['committed before post-read']
        other=inv.grant_pet(500001)
        inv.fight_pet(other)
        with closing(leased.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            current=inv.pet_progress(db,pet)
            assert (current.state.level,current.state.experience)==(25,10000)
            inv.change_pet_growth(db,pet,'later-income',current.state.version,'experience_capped',(7,25))
        completed=runtime_storage.complete_conversation(accounts,1111,role['id'],epoch,
            actor,plan,'completion',resources,inv)
        result=completed.completion.rewards.pet_experience
        assert result.current_pet.id==result.recipient_id==pet
        assert result.current_pet.progress.state.experience==10007
        messages=completion_messages(completed.completion)
        assert [body for kind,body in messages if kind==REFRESH_PET_EXP]==[struct.pack('>iQ',pet,10007)]
        with closing(leased.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            assert inv.selected_fighting_pet(db).id==other
            assert db.execute("SELECT COUNT(*) FROM task_reward_channels WHERE role_id=? AND task_id=210002 "
                              "AND channel='pet_experience'",(role['id'],)).fetchone()==(1,)
        assert leased.task_pet_experience_rules is accounts.task_pet_experience_rules
    report=dict(passed=['startup rules reach leased role storage and actual completion',
        'separate reader proves reward committed before post-read; pre-commit result has no sendable pet',
        'post-read failure retains committed award; same request retry pays once',
        'switching pets and later XP refresh fixed original key at current absolute 10007'],
        database='disposable',battle_executed=False,native_gui_verified=False,live_server_changed=False)
    write_json(OUT/'evidence/task-pet-storage-verification.json',report)
    print(report)


if __name__=='__main__':main()
