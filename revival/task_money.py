"""Original fixed NPC money objectives in the caller's leased transaction.

Payment recipes are explicitly supplied and must already be allowed by the
currency owner. This Module never extends wallet permissions, substitutes a
shop expense, initializes a wallet, commits, or sends a message.
"""
from dataclasses import dataclass
import hashlib
import json
from types import MappingProxyType
from currency import CurrencyRules,CurrencyChange,read_wallet,apply_currency
from tasks import _plain
from task_domain import supports_money_submission
from task_conversation import TaskConversation,TaskConversationTicket
from task_money_protocol import TaskMoneySubmission,encode_task_money_submission
from task_persistence import load_task_state
from task_growth_resources import current_task_resource_profile
from task_workflow import complete_task_transaction,replay_completed_task_transaction,completion_messages
from task_protocol import S_REFRESH_SCENARIO_QUEST_STATE
from world_owner import Location


def _hash(value):
    return hashlib.sha256(json.dumps(_plain(value),sort_keys=True,separators=(',',':')).encode()).hexdigest()


@dataclass(frozen=True)
class TaskMoneyDefinition:
    task_id:int
    amount:int
    fingerprint:str


@dataclass(frozen=True)
class TaskMoneyResources:
    definitions:object
    exclusions:object


def load_task_money_resources(resources):
    """Startup-only original amounts; does not grant payment/activation rights."""
    definitions={};exclusions={}
    for task_id,task in resources.definitions.items():
        if task['type']!=11:continue
        if not supports_money_submission(task):
            exclusions[task_id]='money_objective_has_additional_unimplemented_mechanics';continue
        definitions[task_id]=TaskMoneyDefinition(task_id,int(task['attributes']['ActiveInfoGiveBackMoney']),_hash(task))
    return TaskMoneyResources(MappingProxyType(definitions),MappingProxyType(exclusions))


@dataclass(frozen=True)
class TaskMoneyPaymentRule:
    revision:str
    currency:str
    purpose:str

    def __post_init__(self):
        if (type(self.revision) is not str or not 1<=len(self.revision)<=160
                or self.currency!='cash' or self.purpose!='task_money_submission'):
            raise ValueError('Explicit task payment policy and separate expense purpose required')


@dataclass(frozen=True)
class TaskMoneyPermit:
    ticket:TaskConversationTicket
    generation:int
    task_revision:int
    definition_fingerprint:str
    payment_fingerprint:str


@dataclass(frozen=True)
class TaskMoneyOpening:
    permit:TaskMoneyPermit
    definition:TaskMoneyDefinition
    messages:tuple


@dataclass(frozen=True)
class TaskMoneyResult:
    task_id:int
    completion:object
    messages:tuple
    replayed:bool=False


def _payment(currency_rules,payment_rule):
    if (type(currency_rules) is not CurrencyRules or type(payment_rule) is not TaskMoneyPaymentRule
            or payment_rule.purpose not in currency_rules.spend_purposes.get(payment_rule.currency,())):
        raise ValueError('Task money payment recipe requires explicit currency-owner approval')
    return _hash((currency_rules.revision,payment_rule.revision,payment_rule.currency,payment_rule.purpose))


def _scope(db,account_id,role_id,epoch,inventory,currency_rules):
    if (inventory.account_id,inventory.role_id)!=(account_id,role_id):
        raise ValueError('Task money inventory owner mismatch')
    inventory.immutable_snapshot_transaction(db,epoch=epoch)
    wallet=read_wallet(db,account_id,role_id,epoch,currency_rules)
    actor,state=load_task_state(db,account_id,role_id,epoch)
    return actor,state,wallet


def _definition(task_id,resources,money):
    definition=money.definitions.get(task_id);task=resources.definitions.get(task_id)
    if definition is None or task is None or definition.fingerprint!=_hash(task):
        raise ValueError('Unsupported or changed original task money definition')
    return definition


def _clock(generation,now_ms):
    if type(generation) is not int or generation<=0 or type(now_ms) is not int or not 0<=now_ms<2**63:
        raise ValueError('Trusted current task money generation/clock required')


def open_task_money_transaction(db,account_id,role_id,epoch,resources,money,inventory,task_id,proof,location,*,
        generation,now_ms,deadline_ms,currency_rules,payment_rule):
    """Current NPC menu invokes the client's original mode3 UI after dialogue.

    No extra server popup or invented amount prompt. The original local UI
    collects the player's amount; the server verifies the configured amount.
    """
    _clock(generation,now_ms)
    if type(deadline_ms) is not int or not now_ms<deadline_ms<2**63:
        raise ValueError('Bounded task money interaction deadline required')
    payment=_payment(currency_rules,payment_rule)
    actor,state,_=_scope(db,account_id,role_id,epoch,inventory,currency_rules)
    definition=_definition(task_id,resources,money)
    local=TaskConversation(resources,role_id,epoch)
    opening=local.open(actor,state,task_id,proof,location,now_ms=now_ms,deadline_ms=deadline_ms)
    permit=TaskMoneyPermit(opening.ticket,generation,state.revision,definition.fingerprint,payment)
    return TaskMoneyOpening(permit,definition,local.opening_messages())


def submit_task_money_transaction(db,account_id,role_id,epoch,resources,money,inventory,command,permit,location,request_id,*,
        generation,now_ms,currency_rules,payment_rule,growth_rules=None,attribute_rules=None,pet_experience_rules=None,
        resource_rules=None,equipment_rules=None):
    """Exact debit, original rewards/Finish/next and all receipts share one txn.

    On exception caller rolls back and retains its frozen permit. On commit it
    clears the permit and sends messages. Paid acknowledgement may omit the old
    NPC permit/location but requires the same durable payment manifest and
    current lease; it reads current balances and never replays the debit.
    """
    _clock(generation,now_ms)
    encode_task_money_submission(command)
    if type(request_id) is not str or not 1<=len(request_id)<=160:
        raise ValueError('Stable server task money request identity required')
    payment=_payment(currency_rules,payment_rule)
    actor,state,_=_scope(db,account_id,role_id,epoch,inventory,currency_rules)
    definition=_definition(command.task_id,resources,money)
    if command.amount!=definition.amount:
        raise ValueError('Task money amount must equal original configuration')
    current_task_resource_profile(db,actor,inventory,resource_rules,equipment_rules)
    manifest={'definition_fingerprint':definition.fingerprint,'payment_fingerprint':payment,
        'npc_key':command.npc_key,'amount':definition.amount,'currency':payment_rule.currency,
        'purpose':payment_rule.purpose,'payment_policy':payment_rule.revision}
    reward_rules=(growth_rules,attribute_rules,currency_rules,pet_experience_rules)
    replayed=command.task_id in state.completed
    if replayed:
        row=db.execute('SELECT payload FROM task_effects WHERE role_id=? AND task_id=?',
            (role_id,command.task_id)).fetchone()
        effect=json.loads(row[0]) if row else {}
        if effect.get('money_submission')!=manifest:
            raise ValueError('Paid task money acknowledgement differs from original payment')
        completion=replay_completed_task_transaction(db,actor,command.task_id,resources,inventory,*reward_rules,
            resource_rules=resource_rules,equipment_rules=equipment_rules)
    else:
        if (not isinstance(permit,TaskMoneyPermit) or not isinstance(permit.ticket,TaskConversationTicket)
                or type(permit.generation) is not int or permit.generation!=generation or permit.task_revision!=state.revision
                or permit.definition_fingerprint!=definition.fingerprint or permit.payment_fingerprint!=payment
                or not isinstance(location,Location)):
            raise ValueError('Task money permit or current task/policy version is stale')
        local=TaskConversation(resources,role_id,epoch);local.ticket=permit.ticket
        plan=local.plan_money_submission(actor,state,command,location,now_ms=now_ms)
        change=CurrencyChange(f'task:{role_id}:{command.task_id}:objective_money',payment_rule.purpose,
            f'task:{command.task_id}:ActiveInfoGiveBackMoney:{payment_rule.revision}',((payment_rule.currency,-definition.amount),))
        apply_currency(db,account_id,role_id,epoch,change,currency_rules)
        completion=complete_task_transaction(db,actor,plan,request_id,resources,inventory,*reward_rules,
            resource_rules=resource_rules,equipment_rules=equipment_rules)
        effect=json.loads(db.execute('SELECT payload FROM task_effects WHERE role_id=? AND task_id=?',
            (role_id,command.task_id)).fetchone()[0]);effect['money_submission']=manifest
        db.execute('UPDATE task_effects SET payload=? WHERE role_id=? AND task_id=?',
            (json.dumps(effect,ensure_ascii=False),role_id,command.task_id))
    messages=completion_messages(completion)
    if replayed:messages=tuple((kind,body) for kind,body in messages if kind!=S_REFRESH_SCENARIO_QUEST_STATE)
    return TaskMoneyResult(command.task_id,completion,inventory.equipment_bag_messages(db,epoch)+messages,replayed)
