"""One Task continuation contract; synthetic trusted external terminal, no AI8027.

Natural creation/first real AI8001/teaching precede this check. Only the second
battle's terminal is an explicit external-Module fixture. No completed journal
is inserted or updated by the harness; actual public Task settlement does it.
"""
from functools import partial
import sqlite3
from verify_local_prologue_teaching import main
from verify_task_second_battle import check,refused


def after_admission(db,store,rules,admission,participant,inventory):
    from task_second_battle_continuation import reconcile_second_battle_successor_transaction
    from training_battle import BattleFinished
    from task_battle import settle_task_battle_transaction,TASK_BATTLE_SCOPE
    from task_persistence import load_task_state
    from progression import read_experience
    from currency import read_wallet
    from verify_world_committed_transfer_read import readonly
    rid=participant.role_id;epoch=participant.login_epoch;resources=store.task_resources
    def continuation():
        return reconcile_second_battle_successor_transaction(db,1111,rid,epoch,resources,rules,100190)
    refused(continuation)
    # Trusted external terminal DTO fixture, not relabelled Training/Wild or a
    # claimed AI8027 engine result. Its identity comes from the real admission.
    event=BattleFinished(admission.battle_id,'task-battle:'+admission.battle_id,rid,0,True,1,
        rules.battles.engine_revision,epoch,participant.attribute_version,scope=TASK_BATTLE_SCOPE,
        task_event_eligible=True,outcome='victory')
    rewards=dict(growth_rules=store.growth_rules,attribute_rules=store.attribute_rules,
        currency_rules=store.currency_rules,pet_experience_rules=store.task_pet_experience_rules,
        resource_rules=store.resource_rules,equipment_rules=store.equipment_attribute_rules)
    def settle():
        return settle_task_battle_transaction(db,1111,rid,epoch,resources,rules.battles,event,inventory,**rewards)
    before=(load_task_state(db,1111,rid,epoch),read_experience(db,1111,rid),
        read_wallet(db,1111,rid,epoch,store.currency_rules))
    db.execute("CREATE TEMP TRIGGER fail_cg_activation BEFORE INSERT ON task_journal WHEN NEW.task_id=100161 "
        "BEGIN SELECT RAISE(ABORT,'CG activation late failure'); END")
    db.execute('SAVEPOINT cg_late_failure')
    try:settle();continuation()
    except sqlite3.DatabaseError:pass
    else:raise AssertionError('Late CG task activation failure did not execute')
    db.execute('ROLLBACK TO cg_late_failure');db.execute('RELEASE cg_late_failure')
    db.execute('DROP TRIGGER fail_cg_activation')
    assert before==(load_task_state(db,1111,rid,epoch),read_experience(db,1111,rid),
        read_wallet(db,1111,rid,epoch,store.currency_rules))
    result=settle()
    assert result.completion.rewards.experience_awarded==255
    assert result.completion.rewards.currency_awarded==(('SMoney','bound_silver',600),)
    assert continuation()==(100161,)
    state=load_task_state(db,1111,rid,epoch)[1]
    assert 100190 in state.completed and 100161 in state.active
    assert not {100161,100110,100111}&state.completed and 100110 not in state.active
    assert readonly(db,continuation)==()
    return dict(synthetic_external_second_terminal=True,second_ai_engine_executed=False,
        original_cg_task_only_active=True,late_failure_rolls_back_task_and_rewards=True,
        already_active_repeat_readonly=True,movie_or_transfer_or_ai8002_not_executed=True)


if __name__=='__main__':
    main(after_teaching_check=partial(check,after_admission=after_admission),
        extra_sources=('task_first_skill_proof.py','task_second_battle.py','task_second_battle_continuation.py'),
        extra_policies=('task-pve-ai8027-v1.json',))
