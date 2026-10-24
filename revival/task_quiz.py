"""Fixed original NPC quizzes, in the existing leased role transaction.

The original client renders and shuffles local options; answer code0 identifies
its CorrectAnswer item. This Module owns no connection, NPC or activation loop.
Wrong-answer retry is an explicit bounded restoration behavior, not recovered
event-specific failure/branch semantics. Raw successor branches stay pending.
"""
from dataclasses import dataclass
import hashlib
import json
from types import MappingProxyType
from tasks import _plain
from task_domain import supports_fixed_npc_quiz
from task_conversation import TaskConversation,TaskConversationTicket
from task_persistence import load_task_state
from task_quiz_protocol import TaskQuizAnswer
from task_workflow import complete_task_transaction,replay_completed_task_transaction,completion_messages
from task_protocol import S_REFRESH_SCENARIO_QUEST_STATE
from world_owner import Location


def _hash(task):
    return hashlib.sha256(json.dumps(_plain(task),sort_keys=True,separators=(',',':')).encode()).hexdigest()


@dataclass(frozen=True)
class TaskQuizDefinition:
    task_id:int
    question:str
    # Stable source identities, not shuffled display positions.
    answers:tuple
    fingerprint:str


@dataclass(frozen=True)
class TaskQuizResources:
    definitions:object
    exclusions:object


def load_task_quiz_resources(resources):
    """Startup-only capabilities; five fixed source questions, no enrollment."""
    definitions={};excluded={}
    for q,task in resources.definitions.items():
        if task['type']!=17:continue
        if not supports_fixed_npc_quiz(task):
            excluded[q]='dynamic_or_cyclic_question_source_unimplemented';continue
        a=task['attributes']
        definitions[q]=TaskQuizDefinition(q,a['QuestionInfoConversion'],
            tuple(enumerate((a['QuestionInfoCorrectAnswer'],)+tuple(task['lists']['QuestionInfoWrongAnswerList']))),_hash(task))
    return TaskQuizResources(MappingProxyType(definitions),MappingProxyType(excluded))


@dataclass(frozen=True)
class TaskQuizPermit:
    ticket:TaskConversationTicket
    generation:int
    task_revision:int
    definition_fingerprint:str


@dataclass(frozen=True)
class TaskQuizOpening:
    permit:TaskQuizPermit
    definition:TaskQuizDefinition
    messages:tuple


@dataclass(frozen=True)
class TaskQuizResult:
    task_id:int
    outcome:str
    completion:object=None
    messages:tuple=()
    replayed:bool=False


def _clock(generation,now_ms):
    if type(generation) is not int or generation<=0 or type(now_ms) is not int or not 0<=now_ms<2**63:
        raise ValueError('Current quiz generation and server clock required')


def _scope(db,account_id,role_id,epoch,inventory):
    if inventory.account_id!=account_id or inventory.role_id!=role_id:
        raise ValueError('Quiz inventory owner mismatch')
    inventory.immutable_snapshot_transaction(db,epoch=epoch)
    return load_task_state(db,account_id,role_id,epoch)


def _definition(task_id,resources,quiz):
    definition=quiz.definitions.get(task_id);task=resources.definitions.get(task_id)
    if definition is None or task is None or definition.fingerprint!=_hash(task):
        raise ValueError('Unsupported or changed original quiz definition')
    return definition


def open_task_quiz_transaction(db,account_id,role_id,epoch,resources,quiz,inventory,task_id,proof,location,*,
        generation,now_ms,deadline_ms):
    """Current authorized active quest + actual NPC; local text needs no packet.

    Caller retains the frozen permit only after its transaction commits. The
    source definition is audit metadata; only ready3 + original SVisitNpc send.
    """
    _clock(generation,now_ms)
    if type(deadline_ms) is not int or not now_ms<deadline_ms<2**63:
        raise ValueError('Bounded quiz NPC deadline required')
    actor,state=_scope(db,account_id,role_id,epoch,inventory)
    definition=_definition(task_id,resources,quiz)
    local=TaskConversation(resources,role_id,epoch)
    opening=local.open(actor,state,task_id,proof,location,now_ms=now_ms,deadline_ms=deadline_ms)
    permit=TaskQuizPermit(opening.ticket,generation,state.revision,definition.fingerprint)
    return TaskQuizOpening(permit,definition,local.opening_messages())


def answer_task_quiz_transaction(db,account_id,role_id,epoch,resources,quiz,inventory,answer,permit,location,request_id,*,
        generation,now_ms,growth_rules=None,attribute_rules=None,currency_rules=None,pet_experience_rules=None,
        resource_rules=None,equipment_rules=None):
    """Correct answer + original reward/next/evidence in ONE caller txn.

    A legal wrong answer leaves the active task intact with no packet invented.
    Native phase4 already closes; retry requires another real NPC interaction.
    Clear the owner's permit after successful handling/commit for either result.
    Completed exact-answer acknowledgement may omit historical permit/location,
    but needs the durable quiz manifest and current lease; it cannot grant again.
    """
    _clock(generation,now_ms)
    if (not isinstance(answer,TaskQuizAnswer) or type(answer.answer_code) is not int
            or type(answer.npc_key) is not int or not 0<answer.npc_key<2**63
            or type(request_id) is not str or not 1<=len(request_id)<=160):
        raise ValueError('Original quiz answer and stable server request required')
    actor,state=_scope(db,account_id,role_id,epoch,inventory)
    definition=_definition(answer.task_id,resources,quiz)
    rules=(growth_rules,attribute_rules,currency_rules,pet_experience_rules)
    manifest={'definition_fingerprint':definition.fingerprint,'npc_key':answer.npc_key,'answer_code':0}
    if answer.task_id in state.completed:
        row=db.execute('SELECT payload FROM task_effects WHERE role_id=? AND task_id=?',(role_id,answer.task_id)).fetchone()
        effect=json.loads(row[0]) if row else {}
        if answer.answer_code!=0 or effect.get('quiz_answer')!=manifest:
            raise ValueError('Completed quiz acknowledgement differs from original answer evidence')
        completion=replay_completed_task_transaction(db,actor,answer.task_id,resources,inventory,*rules,
            resource_rules=resource_rules,equipment_rules=equipment_rules)
        messages=tuple((kind,body) for kind,body in completion_messages(completion) if kind!=S_REFRESH_SCENARIO_QUEST_STATE)
        return TaskQuizResult(answer.task_id,'correct',completion,inventory.equipment_bag_messages(db,epoch)+messages,True)
    if (not isinstance(permit,TaskQuizPermit) or not isinstance(permit.ticket,TaskConversationTicket)
            or (permit.ticket.role_id,permit.ticket.login_epoch)!=(role_id,epoch)
            or not isinstance(location,Location)
            or type(permit.generation) is not int or permit.generation!=generation
            or permit.task_revision!=state.revision or permit.definition_fingerprint!=definition.fingerprint):
        raise ValueError('Quiz permit or task revision is stale')
    local=TaskConversation(resources,role_id,epoch);local.ticket=permit.ticket
    plan=local.plan_quiz_answer(actor,state,answer,location,now_ms=now_ms)
    if plan is None:return TaskQuizResult(answer.task_id,'incorrect')
    completion=complete_task_transaction(db,actor,plan,request_id,resources,inventory,*rules,
        resource_rules=resource_rules,equipment_rules=equipment_rules)
    effect=json.loads(db.execute('SELECT payload FROM task_effects WHERE role_id=? AND task_id=?',
        (role_id,answer.task_id)).fetchone()[0]);effect['quiz_answer']=manifest
    db.execute('UPDATE task_effects SET payload=? WHERE role_id=? AND task_id=?',
        (json.dumps(effect,ensure_ascii=False),role_id,answer.task_id))
    messages=inventory.equipment_bag_messages(db,epoch)+completion_messages(completion)
    return TaskQuizResult(answer.task_id,'correct',completion,messages)
