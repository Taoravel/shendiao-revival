"""One role transaction for trusted task completion and supported rewards.

The role owner controls its mailbox and the caller's transaction. After commit
it acknowledges the conversation ticket and delivers logical messages through
the connection owner. This module never connects, commits, sends or encrypts.
"""
from dataclasses import dataclass, replace
from task_persistence import apply_task_plan
from task_rewards import settle_task_reward
from task_protocol import (S_REFRESH_SCENARIO_QUEST_STATE, encode_scenario_state,
    S_ACCEPT_SCENARIO_QUEST, ScenarioQuestInfo, encode_accept_scenario_quest)
from task_dialog_protocol import S_REFRESH_USER_EXP, encode_user_experience
from task_chains import continue_task_chain
from role_attribute_storage import attribute_snapshot_if_initialized
from currency_protocol import encode_currency_balance
from task_pet_experience import capture_fresh_recipient, pet_experience_messages, refresh_pet_experience
from role_growth import read_growth
from role_attribute_protocol import growth_refresh
from inventory import AssetChange
from task_item_protocol import NpcItemSubmission
from task_domain import supports_level_gate,supports_native_effect_dialogue,supports_npc_finish_dialogue
from task_protocol import SCENARIO_ACTIVE, SCENARIO_REMOVE
from task_growth_resources import current_task_resource_profile
import json


@dataclass(frozen=True)
class TaskCompletion:
    task: object
    rewards: object
    started_tasks: tuple = ()
    attributes: object = None
    growth_messages: tuple = ()
    consumed_items: tuple = ()
    started_infos: tuple = ()
    native_completion_effect_id: int = 0
    replayed: bool = False
    suppress_replayed_state: bool = False


def complete_task_transaction(db, actor, plan, request_id, resources, inventory, growth_rules=None, attribute_rules=None, currency_rules=None, pet_experience_rules=None,*,resource_rules=None,equipment_rules=None):
    if plan.action != 'complete':
        raise ValueError('Completion workflow requires a completed objective')
    # Validate migrated entry before objective debits or captured pet rewards.
    current_task_resource_profile(db,actor,inventory,resource_rules,equipment_rules)
    state = db.execute('SELECT state FROM task_journal WHERE role_id=? AND task_id=?',
                       (actor.role_id,plan.task_id)).fetchone()
    if state and state[0] == 'active':
        capture_fresh_recipient(db,actor,plan.task_id,resources,inventory,pet_experience_rules)
    task = apply_task_plan(db, actor, plan, request_id)
    if plan.objective_debits:
        inventory.apply_settlement(db,AssetChange(f'task:{actor.role_id}:{plan.task_id}:objective_items',
                                                  debits=plan.objective_debits))
    return _settle_completion(db,actor,task,plan.task_id,plan.objective_debits,resources,inventory,
                              growth_rules,attribute_rules,currency_rules,pet_experience_rules,
                              replayed=bool(state and state[0]=='completed'),
                              resource_rules=resource_rules,equipment_rules=equipment_rules)


def _settle_completion(db,actor,task,task_id,consumed_items,resources,inventory,
                       growth_rules,attribute_rules,currency_rules,pet_experience_rules,*,replayed=False,
                       resource_rules=None,equipment_rules=None):
    rewards = settle_task_reward(db, actor.account_id, actor.role_id, actor.login_epoch,
                                 task_id, resources, inventory, growth_rules,attribute_rules,currency_rules,pet_experience_rules,
                                 resource_rules=resource_rules,equipment_rules=equipment_rules)
    started = continue_task_chain(db,actor.account_id,actor.role_id,actor.login_epoch,task_id,resources)
    attributes=current_task_resource_profile(db,actor,inventory,resource_rules,equipment_rules)
    if attributes is None:
        attributes=attribute_snapshot_if_initialized(db,actor.account_id,actor.role_id,actor.login_epoch)
    growth_messages = (growth_refresh(read_growth(db,actor.account_id,actor.role_id),attributes),) if attributes is not None else ()
    infos=tuple(ScenarioQuestInfo(ident,SCENARIO_ACTIVE,rewards.level if supports_level_gate(resources.definitions[ident]) else 0,0,0)
                for ident in started)
    native=60001 if supports_native_effect_dialogue(resources.definitions[task_id]) else 0
    return TaskCompletion(task,rewards,started,attributes,growth_messages,consumed_items,infos,native,replayed,
        supports_npc_finish_dialogue(resources.definitions[task_id]))


def replay_completed_task_transaction(db,actor,task_id,resources,inventory,growth_rules=None,
                                      attribute_rules=None,currency_rules=None,pet_experience_rules=None,*,
                                      resource_rules=None,equipment_rules=None):
    """Trusted durable chapter/operation acknowledgement, never a wire grant API.

    settle_task_reward requires current ownership/lease and completed journal.
    Callers must first validate their own durable operation identity. Historical
    receipts prevent paying again; returned balances/attributes are current.
    """
    current_task_resource_profile(db,actor,inventory,resource_rules,equipment_rules)
    return _settle_completion(db,actor,None,task_id,(),resources,inventory,growth_rules,
                              attribute_rules,currency_rules,pet_experience_rules,replayed=True,
                              resource_rules=resource_rules,equipment_rules=equipment_rules)


def replay_item_completion_transaction(db, actor, command, resources, inventory, growth_rules=None,
                                       attribute_rules=None, currency_rules=None, pet_experience_rules=None,*,
                                       resource_rules=None,equipment_rules=None):
    """Reconnect acknowledgement of an already completed selected-item command.

    Requires durable objective debits matching the original exact selection.
    Never reads/consumes replacement items or chooses a reward pet. The common
    reward receipts may finish previously pending eligible channels once.
    """
    if (not db.in_transaction or not isinstance(command,NpcItemSubmission) or command.submit_type!=1
            or type(command.units) is not tuple or not command.units
            or any(type(x) is not tuple or len(x)!=2 or any(type(v) is not int or v<=0 for v in x) for x in command.units)
            or len({key for key,_ in command.units})!=len(command.units)):
        raise ValueError('Invalid completed task item replay')
    row=db.execute("SELECT e.payload FROM task_effects e JOIN task_journal j ON j.role_id=e.role_id AND j.task_id=e.task_id "
                   "WHERE e.role_id=? AND e.task_id=? AND j.state='completed'",(actor.role_id,command.task_id)).fetchone()
    effect=json.loads(row[0]) if row else {}
    consumed=tuple(tuple(x) for x in effect.get('objective_debits',()))
    if not consumed or consumed!=tuple(sorted(command.units)):
        raise ValueError('Completed task item replay differs from original submission')
    current_task_resource_profile(db,actor,inventory,resource_rules,equipment_rules)
    return _settle_completion(db,actor,None,command.task_id,consumed,resources,inventory,
                              growth_rules,attribute_rules,currency_rules,pet_experience_rules,replayed=True,
                              resource_rules=resource_rules,equipment_rules=equipment_rules)


def refresh_completion_pet(db, actor, completion, inventory):
    """After commit, read the fixed recipient in a new fenced role transaction.

    The role owner calls this before producing refresh messages; a later pet
    change or release cannot be overwritten by a historical settlement receipt.
    """
    pet = refresh_pet_experience(db,actor.account_id,actor.role_id,actor.login_epoch,
                                completion.rewards.pet_experience,inventory)
    return replace(completion,rewards=replace(completion.rewards,pet_experience=pet))


def completion_messages(completion):
    """Call after successful commit. EXP is the current balance, never a delta.

    State 1 follows native completion/removal handling. Only proven cash and
    bound-silver display slots receive current wallet snapshots; other channels
    retain their durable pending status and receive no guessed UI refresh.
    """
    # Original60001 and type50 Finish repeat even without the completed bean.
    # A replay acknowledges current balances without issuing that state1 again.
    state=() if completion.replayed and (completion.native_completion_effect_id or completion.suppress_replayed_state) else (
        (S_REFRESH_SCENARIO_QUEST_STATE,encode_scenario_state(completion.rewards.task_id,SCENARIO_REMOVE)),)
    return state+((S_REFRESH_USER_EXP,encode_user_experience(completion.rewards.experience_balance)),)+tuple(
                encode_currency_balance(row.currency,row.balance)
                for row in (completion.rewards.wallet or ()) if row.currency in ('cash','bound_silver')) + tuple(
                (S_ACCEPT_SCENARIO_QUEST, encode_accept_scenario_quest(info))
                for info in (completion.started_infos or tuple(ScenarioQuestInfo(ident,SCENARIO_ACTIVE,0,0,0)
                    for ident in completion.started_tasks))) + completion.growth_messages + pet_experience_messages(completion.rewards.pet_experience)
