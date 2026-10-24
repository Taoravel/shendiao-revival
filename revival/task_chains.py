"""Unambiguous supported ordinary successors, joining the role transaction.

This narrow activation policy is designed restoration behavior, not a claim of
the original server's complete prerequisite/branch rules. Raw edges stay intact.
"""
from dataclasses import dataclass
import json
from task_domain import (TaskDomain, supports_plain_dialogue, supports_item_submission, supports_level_gate,
                         supports_native_effect_dialogue,supports_static_region,supports_npc_finish_dialogue,
                         supports_npc_start_dialogue,supports_npc_empty_scenario,supports_fixed_npc_quiz,
                         supports_money_submission,supports_fighting_pet_task)
from task_persistence import load_task_state, apply_task_plan
from task_rewards import update_reward_delivery


@dataclass(frozen=True)
class TaskChainDecision:
    source_id: int
    target_id: int | None
    status: str
    reason: str


def plan_task_chain(actor, snapshot, source_id, resources):
    """Pure decision: no multi-branch selection, terminal guessing or skipping."""
    domain = TaskDomain(resources)
    if source_id not in snapshot.completed:
        raise ValueError('Task chain source is not completed')
    source = resources.definitions.get(source_id)
    if source is None:
        raise ValueError('Task chain source definition missing')
    edges = tuple(dict.fromkeys(source['next_ids']))
    if not edges:
        return TaskChainDecision(source_id,None,'resolved','no_successor')
    if len(edges) != 1:
        return TaskChainDecision(source_id,None,'pending','branch_selection_unconfirmed')
    target_id = edges[0]
    if target_id == source_id:
        return TaskChainDecision(source_id,target_id,'pending','cycle_instance_unimplemented')
    target = resources.definitions.get(target_id)
    if target is None:
        return TaskChainDecision(source_id,target_id,'pending','successor_definition_missing')
    if target_id in snapshot.completed:
        return TaskChainDecision(source_id,target_id,'resolved','successor_already_completed')
    if target_id in snapshot.active:
        return TaskChainDecision(source_id,target_id,'resolved','successor_already_active')
    if target['request_mission_ids']:
        return TaskChainDecision(source_id,target_id,'pending','prerequisite_semantics_unconfirmed')
    if supports_level_gate(target):
        try:
            domain.plan(actor,snapshot,'wait_level',target_id)
        except ValueError:
            return TaskChainDecision(source_id,target_id,'pending','successor_character_or_level_requirement')
        return TaskChainDecision(source_id,target_id,'activate','unique_supported_level_gate')
    if not (supports_plain_dialogue(target) or supports_item_submission(target)
            or supports_native_effect_dialogue(target) or supports_static_region(target)
            or supports_npc_finish_dialogue(target) or supports_npc_start_dialogue(target)
            or supports_npc_empty_scenario(target) or supports_fixed_npc_quiz(target)
            or supports_money_submission(target) or supports_fighting_pet_task(target)) or not 1001 <= target_id <= 499999:
        return TaskChainDecision(source_id,target_id,'pending','successor_gameplay_unimplemented')
    try:
        offered = domain.plan(actor,snapshot,'offer',target_id)
        domain.plan(actor,offered.after,'accept',target_id)
    except ValueError:
        return TaskChainDecision(source_id,target_id,'pending','successor_character_or_level_requirement')
    reason=('unique_supported_item_submission' if supports_item_submission(target) else
            'unique_supported_static_region' if supports_static_region(target) else
            'unique_supported_npc_finish_dialogue' if supports_npc_finish_dialogue(target) else
            'unique_supported_npc_start_dialogue' if supports_npc_start_dialogue(target) else
            'unique_supported_npc_empty_scenario' if supports_npc_empty_scenario(target) else
            'unique_supported_fixed_npc_quiz' if supports_fixed_npc_quiz(target) else
            'unique_supported_money_submission' if supports_money_submission(target) else
            'unique_supported_fighting_pet_task' if supports_fighting_pet_task(target) else
            'unique_supported_native_effect_dialogue' if supports_native_effect_dialogue(target) else 'unique_supported_dialogue')
    return TaskChainDecision(source_id,target_id,'activate',reason)


def continue_task_chain(db, account_id, role_id, epoch, source_id, resources):
    """Apply at most one next quest in the caller's existing role transaction.

    Caller fences its lease. Task completion/rewards and this operation roll back
    together. Pending reasons survive in the original task effect for recovery.
    Returns only newly activated IDs so replay cannot reset an active client bean.
    """
    actor,snapshot = load_task_state(db,account_id,role_id,epoch)
    decision = plan_task_chain(actor,snapshot,source_id,resources)
    row = db.execute('SELECT payload FROM task_effects WHERE role_id=? AND task_id=?',(role_id,source_id)).fetchone()
    if row is None:
        raise ValueError('Task chain completion effect missing')
    effect = json.loads(row[0])
    started = ()
    if decision.status == 'activate':
        domain = TaskDomain(resources)
        if supports_level_gate(resources.definitions[decision.target_id]):
            wait=domain.plan(actor,snapshot,'wait_level',decision.target_id)
            apply_task_plan(db,actor,wait,f'chain:{source_id}:{decision.target_id}:wait-level')
        else:
            if decision.target_id not in snapshot.offered:
                offer = domain.plan(actor,snapshot,'offer',decision.target_id)
                apply_task_plan(db,actor,offer,f'chain:{source_id}:{decision.target_id}:offer')
                actor,snapshot = load_task_state(db,account_id,role_id,epoch)
            accept = domain.plan(actor,snapshot,'accept',decision.target_id)
            apply_task_plan(db,actor,accept,f'chain:{source_id}:{decision.target_id}:accept')
        started = (decision.target_id,)
    effect['chain_status'] = 'activated' if started else decision.status
    effect['chain_reason'] = decision.reason
    effect['chain_target'] = decision.target_id
    effect['chain_resolved'] = decision.status in ('activate','resolved')
    # Preserve raw next_ids and other continuation instructions for later owners.
    delivered = update_reward_delivery(effect)
    db.execute('UPDATE task_effects SET payload=?,delivered=? WHERE role_id=? AND task_id=?',
               (json.dumps(effect,ensure_ascii=False),int(delivered),role_id,source_id))
    return started
