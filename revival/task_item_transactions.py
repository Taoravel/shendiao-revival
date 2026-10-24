"""NPC item submission using only public inventory/quest transaction Interfaces.

Role owner retains a frozen permit; each call builds its own local conversation
and reads current assets in the caller transaction. Nothing connects or sends.
"""
from dataclasses import dataclass
from inventory import InventorySnapshot
from task_conversation import TaskConversation,TaskConversationTicket
from task_item_protocol import NpcItemSubmission
from task_item_submission import plan_item_objective
from task_persistence import load_task_state
from task_workflow import (complete_task_transaction,replay_item_completion_transaction,completion_messages)


@dataclass(frozen=True)
class ItemTaskPermit:
    ticket:TaskConversationTicket
    generation:int


@dataclass(frozen=True)
class ItemTaskOpening:
    permit:ItemTaskPermit
    messages:tuple
    prompt_messages:tuple


@dataclass(frozen=True)
class ItemTaskResult:
    completion:object
    messages:tuple
    replayed:bool


def _read(db,account_id,role_id,epoch,inventory):
    if inventory.account_id!=account_id or inventory.role_id!=role_id:
        raise ValueError('NPC item inventory owner mismatch')
    snapshot=inventory.immutable_snapshot_transaction(db,epoch=epoch)
    if not isinstance(snapshot,InventorySnapshot) or snapshot.role_id!=role_id:
        raise ValueError('NPC item inventory snapshot owner mismatch')
    return snapshot


def _clock(now_ms,generation):
    if type(now_ms) is not int or not 0<=now_ms<=2**63-1 or type(generation) is not int or generation<=0:
        raise ValueError('Trusted NPC item command clock/generation required')


def open_item_task_transaction(db,account_id,role_id,epoch,resources,inventory,task_id,proof,location,*,
                               generation,now_ms,deadline_ms):
    """Ready active task only; insufficient items leave no consumable permit.

    The ordinary menu can still display ongoing state using its existing
    item_states argument. Publish this frozen permit only after caller commit.
    prompt_messages is an alternate original selector path, not an extra popup.
    """
    _clock(now_ms,generation)
    if type(deadline_ms) is not int or not now_ms<deadline_ms<=2**63-1:
        raise ValueError('Bounded NPC item dialogue deadline required')
    assets=_read(db,account_id,role_id,epoch,inventory)
    actor,state=load_task_state(db,account_id,role_id,epoch)
    local=TaskConversation(resources,role_id,epoch)
    dialogue=local.open_items(actor,state,task_id,proof,location,assets.items,now_ms=now_ms,deadline_ms=deadline_ms)
    return ItemTaskOpening(ItemTaskPermit(dialogue.ticket,generation),local.opening_messages(),local.item_prompt_messages())


def submit_item_task_transaction(db,account_id,role_id,epoch,resources,inventory,command,permit,location,request_id,*,
                                 generation,now_ms,growth_rules=None,attribute_rules=None,currency_rules=None,
                                 pet_experience_rules=None,resource_rules=None,equipment_rules=None):
    """Fresh selected debit, all rewards and current bag encoding share one txn.

    Completed exact-manifest retry can omit the old permit/location: this only
    acknowledges a durable paid operation under the new current lease. Fresh
    work requires matching immutable generation and a current same-NPC ticket.
    On any exception roll back the entire caller transaction and retain permit.
    After success commit, clear the owner's permit, then deliver messages. Pet
    refresh follows refresh_completion_pet in a new fenced transaction.
    """
    _clock(now_ms,generation)
    if (not isinstance(command,NpcItemSubmission) or command.submit_type!=1
            or type(request_id) is not str or not 1<=len(request_id)<=160):
        raise ValueError('Original NPC task submission and stable command identity required')
    assets=_read(db,account_id,role_id,epoch,inventory)
    actor,state=load_task_state(db,account_id,role_id,epoch)
    replayed=command.task_id in state.completed
    reward_rules=(growth_rules,attribute_rules,currency_rules,pet_experience_rules)
    if replayed:
        completion=replay_item_completion_transaction(db,actor,command,resources,inventory,*reward_rules,
            resource_rules=resource_rules,equipment_rules=equipment_rules)
    else:
        if (not isinstance(permit,ItemTaskPermit) or not isinstance(permit.ticket,TaskConversationTicket)
                or permit.generation!=generation):
            raise ValueError('Missing or stale NPC item connection permit')
        plan=plan_item_objective(actor,state,command,permit.ticket,location,assets.items,resources,now_ms=now_ms)
        completion=complete_task_transaction(db,actor,plan,request_id,resources,inventory,*reward_rules,
            resource_rules=resource_rules,equipment_rules=equipment_rules)
    # Encoding is part of acceptance: missing wallet/overflow/codec errors roll
    # back debits, task, rewards and every idempotency receipt together.
    messages=inventory.equipment_bag_messages(db,epoch)+completion_messages(completion)
    return ItemTaskResult(completion,messages,replayed)
