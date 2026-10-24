"""Role-owned durable task/battle bindings and caller-transaction settlement.

No enemy generation, combat engine, connection, map mutation or automatic task
activation. Formal PVE support must explicitly enable task IDs at startup;
metadata eligibility never authorizes using training/wild battles as quest AI.
"""
from dataclasses import dataclass,asdict
import hashlib
import json
from types import MappingProxyType
from uuid import uuid4
from tasks import _freeze,_plain
from task_domain import TaskDomain,TaskEvidence,valid_task_epoch
from task_persistence import load_task_state
from task_workflow import complete_task_transaction,replay_completed_task_transaction,completion_messages
from task_protocol import S_REFRESH_SCENARIO_QUEST_STATE
from task_dialog_protocol import S_VISIT_NPC,encode_visit_npc,S_REFRESH_USER_EXP,encode_user_experience
from task_battle_protocol import TaskBattleRequest
from world_owner import Location
from world_npcs import NpcInteraction
from battle_owner import Participant,BattleAborted
from battle import Fighter
from training_battle import BattleFinished,TrainingPet
from battle_loadout import OwnedBattlePet
from task_growth_resources import current_task_resource_profile
from role_attribute_storage import attribute_snapshot_if_initialized
from role_growth import read_growth
from role_attribute_protocol import growth_refresh
from progression import read_experience
from currency import read_wallet,WalletNotInitialized
from currency_protocol import encode_currency_balance

TASK_BATTLE_SCOPE='task_quest_v1'  # designed server message contract, not wire
SETTLEMENT_PREFIX='task-battle:'
TASK_TERMINAL_RECOVERY_REVISION='2026-10-24.task-terminal-recovery.1'


def _json(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'))


def _hash(value):
    return hashlib.sha256(_json(value).encode()).hexdigest()


def _sha(value):
    return type(value) is str and len(value)==64 and all(c in '0123456789abcdef' for c in value)


@dataclass(frozen=True)
class TaskBattleDefinition:
    task_id:int
    ai_id:int
    map_id:int
    npc_id:int
    fingerprint:str
    attributes:object
    lists:object


@dataclass(frozen=True)
class TaskBattleResources:
    definitions:object
    exclusions:object
    enabled_task_ids:frozenset
    engine_revision:str


def _exclusion(task):
    a=task['attributes']
    if int(a.get('AIInfoAIID',0))<=0:return 'original_ai_missing'
    if int(a.get('AIInfoBattleResult',0))!=1:return 'unconfirmed_result_mode'
    if task['target']['map_id']<=0 or task['target']['npc_id']<=0:return 'non_npc_battle_trigger'
    # Animation/finish/transfer literals are POST-completion continuations and
    # remain pending. Extra objective work cannot be silently satisfied by won.
    for name in ('ProcessBarTime','ScenarioInfoBranchNpcID','ActiveInfoTargetID','ActiveInfoTargetNum',
                 'ActiveInfoTimeLimit','ActiveInfoGiveBackMoney','ActiveInfoGiveBackPetID','ActiveInfoUseItemID',
                 'ActiveInfoOtherType','ActiveInfoMaxStep','ActiveInfoMiniStep','QuestionInfoNpcID','TransformID',
                 'TransMinLevel','TransMaxLevel'):
        if int(a.get(name,0)):return 'extra_objective:'+name
    return ''


def load_task_battle_resources(resources,*,enabled_task_ids=frozenset(),engine_revision=''):
    """Startup: classify original metadata; default enables ZERO formal fights.

    enabled IDs must come from a real PVE module's approved implementation,
    including its original AI/team/capture rules. Client AI IDs do not supply
    an enemy roster or numeric recipe. Revision identifies that combat recipe.
    """
    if (type(enabled_task_ids) is not frozenset or any(type(q) is not int for q in enabled_task_ids)
            or type(engine_revision) is not str or len(engine_revision)>128
            or enabled_task_ids and not engine_revision):
        raise ValueError('Explicit frozen formal task battle capabilities required')
    definitions={};excluded={}
    for q,task in resources.definitions.items():
        if task['type']!=40:continue
        reason=_exclusion(task)
        if reason:excluded[q]=reason;continue
        definitions[q]=TaskBattleDefinition(q,int(task['attributes']['AIInfoAIID']),task['target']['map_id'],
            task['target']['npc_id'],_hash(_plain(task)),task['attributes'],task['lists'])
    if not enabled_task_ids<=definitions.keys():
        raise ValueError('Enabled battle task has extra/unimplemented objective metadata')
    return TaskBattleResources(MappingProxyType(definitions),MappingProxyType(excluded),enabled_task_ids,engine_revision)


def prepare_task_battle_storage(db):
    """Startup DDL; no role is enrolled or battle started by migration."""
    db.executescript('''CREATE TABLE IF NOT EXISTS task_battle_admissions (
        role_id INTEGER NOT NULL REFERENCES roles(id),battle_id TEXT NOT NULL,
        request_id TEXT NOT NULL,task_id INTEGER NOT NULL,phase TEXT NOT NULL
          CHECK(phase IN ('admitted','won','lost','cancelled')),
        fingerprint TEXT NOT NULL,plan TEXT NOT NULL,result_fingerprint TEXT,receipt TEXT,
        PRIMARY KEY(role_id,battle_id),UNIQUE(role_id,request_id));
        CREATE UNIQUE INDEX IF NOT EXISTS task_battle_one_pending
          ON task_battle_admissions(role_id) WHERE phase='admitted';''')


@dataclass(frozen=True)
class TaskBattleTicket:
    task_id:int
    location:Location
    generation:int
    task_revision:int
    npc_id:int
    entity_key:int
    source_id:str
    request_id:str
    deadline_ms:int
    definition_fingerprint:str


@dataclass(frozen=True)
class TaskBattleDialogue:
    ticket:TaskBattleTicket
    messages:tuple


@dataclass(frozen=True)
class TaskBattleAdmission:
    battle_id:str
    task_id:int
    phase:str
    fingerprint:str
    plan:object
    replayed:bool=False


@dataclass(frozen=True)
class TaskBattleSettlement:
    admission:TaskBattleAdmission
    outcome:str
    completion:object=None
    messages:tuple=()
    replayed:bool=False


@dataclass(frozen=True)
class TaskBattleRecoveryWitness:
    """Trusted caller's verified durable producer/current-source evidence.

    Never construct from a client packet. The host verifies the immutable
    producer outbox and full current resource/source CAS before constructing it;
    these IDs/hashes are evidence bindings, not independent authorization.
    """
    role_id:int
    current_epoch:object
    admission_fingerprint:str
    terminal_fingerprint:str
    producer_receipt_id:str
    producer_fingerprint:str
    source_fingerprint:str
    recovery_revision:str=TASK_TERMINAL_RECOVERY_REVISION


def _owner(db,account_id,role_id,epoch):
    if (not db.in_transaction or not valid_task_epoch(epoch)
            or not db.execute('SELECT 1 FROM roles r JOIN role_leases l ON l.role_id=r.id '
                'WHERE r.id=? AND r.account_id=? AND l.epoch=? AND l.active=1',(role_id,account_id,epoch)).fetchone()):
        raise ValueError('Task battle requires current owned role transaction')


def _definition(resources,registry,task_id,*,admission=False):
    definition=registry.definitions.get(task_id)
    if (definition is None or task_id not in resources.definitions
            or definition.fingerprint!=_hash(_plain(resources.definitions[task_id]))):
        raise ValueError('Unsupported or changed original task battle definition')
    if admission and task_id not in registry.enabled_task_ids:
        raise ValueError('Formal PVE implementation has not enabled this task battle')
    return definition


def _clock(generation,now_ms):
    if type(generation) is not int or generation<=0 or type(now_ms) is not int or not 0<=now_ms<=2**63-1:
        raise ValueError('Trusted task battle clock/generation required')


def open_task_battle_dialogue(db,account_id,role_id,epoch,resources,registry,task_id,proof,location,*,
                              generation,now_ms,deadline_ms):
    """Caller has synchronized the correct active bean; native type40 is UI3.

    Only SVisitNpc is returned: active/failed/ready wire projections belong to
    the shared integration and are not inferred from native menu class3.
    """
    _owner(db,account_id,role_id,epoch);_clock(generation,now_ms)
    definition=_definition(resources,registry,task_id,admission=True)
    actor,state=load_task_state(db,account_id,role_id,epoch)
    if (task_id not in state.active
            or not isinstance(proof,NpcInteraction) or not isinstance(location,Location)
            or proof.kind!='npc_interacted' or proof.position_validation!='bounds_version_distance'
            or type(deadline_ms) is not int or not now_ms<deadline_ms<=2**63-1
            or (location.role_id,location.login_epoch)!=(role_id,epoch) or location.state!='active'
            or (proof.role_id,proof.login_epoch)!=(role_id,epoch) or proof.address!=location.address
            or proof.position_version!=location.version
            or (proof.address.map_id,proof.npc_id)!=(definition.map_id,definition.npc_id)
            or type(proof.entity_key) is not int or not 0<proof.entity_key<2**63
            or type(proof.source_id) is not str or not 1<=len(proof.source_id)<=160):
        raise ValueError('Invalid task battle NPC authorization')
    # Public domain eligibility check; active task means this offers nothing
    # new and the returned pure plan is deliberately not persisted.
    TaskDomain(resources).plan(actor,state,'offer',task_id)
    ticket=TaskBattleTicket(task_id,location,generation,state.revision,definition.npc_id,proof.entity_key,
        proof.source_id,uuid4().hex,deadline_ms,definition.fingerprint)
    return TaskBattleDialogue(ticket,((S_VISIT_NPC,encode_visit_npc(proof.entity_key,(),(task_id,))),))


def _read(db,role_id,battle_id,*,replayed=False):
    row=db.execute('SELECT task_id,phase,fingerprint,plan FROM task_battle_admissions WHERE role_id=? AND battle_id=?',
        (role_id,battle_id)).fetchone()
    if row is None:raise ValueError('No durable task battle admission')
    plan=json.loads(row[3])
    if _hash(plan)!=row[2]:raise ValueError('Task battle admission fingerprint mismatch')
    return TaskBattleAdmission(battle_id,row[0],row[1],row[2],_freeze(plan),replayed)


def read_completed_task_battle_proof(db,account_id,role_id,epoch,resources,registry,task_id):
    """Read a unique task-settlement receipt; never enable or acknowledge combat.

    The current read lease differs from the historical battle epoch. No new
    result or reward recovery is accepted through this query.
    """
    _owner(db,account_id,role_id,epoch)
    definition=_definition(resources,registry,task_id)
    _,state=load_task_state(db,account_id,role_id,epoch)
    rows=tuple(db.execute('SELECT battle_id,result_fingerprint,receipt FROM task_battle_admissions '
        "WHERE role_id=? AND task_id=? AND phase='won'",(role_id,task_id)))
    if task_id not in state.completed or len(rows)!=1:
        raise ValueError('Completed task battle lacks one trusted victory receipt')
    battle_id,result_fingerprint,encoded=rows[0]
    admission=_read(db,role_id,battle_id);plan=admission.plan
    receipt=json.loads(encoded) if encoded else {}
    settlement_id=SETTLEMENT_PREFIX+battle_id
    effect=db.execute('SELECT payload FROM task_effects WHERE role_id=? AND task_id=?',(role_id,task_id)).fetchone()
    if (plan.get('task_id')!=task_id or plan.get('role_id')!=role_id or plan.get('battle_id')!=battle_id
            or plan.get('ai_id')!=definition.ai_id or plan.get('scope')!=TASK_BATTLE_SCOPE
            or plan.get('settlement_id')!=settlement_id or plan.get('definition_fingerprint')!=definition.fingerprint
            or type(plan.get('engine_revision')) is not str or not plan['engine_revision']
            or type(result_fingerprint) is not str or len(result_fingerprint)!=64
            or any(c not in '0123456789abcdef' for c in result_fingerprint)
            or receipt!={'battle_id':battle_id,'task_id':task_id,'settlement_id':settlement_id,
                'outcome':'victory','phase':'won'}
            or effect is None or json.loads(effect[0]).get('source_event')!=settlement_id):
        raise ValueError('Completed task battle receipt/evidence disagrees with original admission')
    return (battle_id,settlement_id,admission.fingerprint,result_fingerprint)


def admit_task_battle_transaction(db,account_id,role_id,epoch,resources,registry,ticket,request,location,participant,battle_id,*,
                                  generation,now_ms):
    """Persist original AI/role/epoch/loadout/NPC binding BEFORE battle opening.

    Participant must be the role owner's actual current versioned loadout. The
    host freezes conflicting gameplay and launches the approved formal engine
    only after commit. A replayed/terminal admission must not launch it again.
    """
    _owner(db,account_id,role_id,epoch);_clock(generation,now_ms)
    if (not isinstance(ticket,TaskBattleTicket) or not isinstance(request,TaskBattleRequest)
            or not isinstance(participant,Participant) or not isinstance(location,Location)
            or type(battle_id) is not str or not 1<=len(battle_id)<=128
            or ticket.location!=location or (location.role_id,location.login_epoch)!=(role_id,epoch)
            or location.state!='active' or ticket.generation!=generation
            or request.task_id!=ticket.task_id or request.npc_key!=ticket.entity_key
            or participant.role_id!=role_id or participant.login_epoch!=epoch
            or participant.connection_generation!=generation
            or type(participant.attribute_version) is not int or participant.attribute_version<=0
            or not isinstance(participant.stats,Fighter)
            or any(type(v) is not int or v<=0 for v in (participant.role_id,participant.level,participant.shape))
            or (participant.stats.id,participant.stats.side)!=(1,0)
            or any(type(v) is not int or v<0 for v in (participant.stats.hp,participant.stats.max_hp,
                participant.stats.mp,participant.stats.max_mp,participant.stats.attack,participant.stats.defense,participant.stats.speed))
            or not 0<participant.stats.hp<=participant.stats.max_hp or participant.stats.mp>participant.stats.max_mp
            or type(participant.authorized_skills) is not tuple or type(participant.stats.skills) is not tuple
            or isinstance(participant.pet,TrainingPet)
            or participant.pet is not None and not isinstance(participant.pet,OwnedBattlePet)):
        raise ValueError('Task battle needs a current formal owned combat snapshot and NPC ticket')
    definition=_definition(resources,registry,request.task_id,admission=True)
    if ticket.definition_fingerprint!=definition.fingerprint or ticket.npc_id!=definition.npc_id:
        raise ValueError('Task battle ticket disagrees with original definition')
    plan=dict(task_id=definition.task_id,ai_id=definition.ai_id,role_id=role_id,epoch=epoch,
        battle_id=battle_id,scope=TASK_BATTLE_SCOPE,settlement_id=SETTLEMENT_PREFIX+battle_id,
        engine_revision=registry.engine_revision,definition_fingerprint=definition.fingerprint,
        ticket=asdict(ticket),participant=asdict(participant))
    fingerprint=_hash(plan)
    existing=db.execute('SELECT fingerprint FROM task_battle_admissions WHERE role_id=? AND battle_id=?',(role_id,battle_id)).fetchone()
    if existing:
        if existing[0]!=fingerprint:raise ValueError('Task battle ID reused with different intent')
        return _read(db,role_id,battle_id,replayed=True)
    actor,state=load_task_state(db,account_id,role_id,epoch)
    if (now_ms>=ticket.deadline_ms or state.revision!=ticket.task_revision or definition.task_id not in state.active
            or (participant.level,participant.shape)!=(actor.level,actor.shape)):
        raise ValueError('Stale task battle eligibility or deadline')
    TaskDomain(resources).plan(actor,state,'offer',definition.task_id)
    if db.execute("SELECT 1 FROM task_battle_admissions WHERE role_id=? AND phase='admitted'",(role_id,)).fetchone():
        raise ValueError('Another unresolved task battle is already admitted')
    db.execute('INSERT INTO task_battle_admissions VALUES(?,?,?,?,?,?,?,NULL,NULL)',
        (role_id,battle_id,ticket.request_id,definition.task_id,'admitted',fingerprint,_json(plan)))
    return _read(db,role_id,battle_id)


def _inventory_scope(inventory,account_id,role_id):
    if inventory.account_id!=account_id or inventory.role_id!=role_id:
        raise ValueError('Task battle settlement inventory owner mismatch')


def _ack(db,account_id,role_id,epoch,resources,registry,admission,inventory,reward_rules,*,
         resource_rules=None,equipment_rules=None):
    definition=_definition(resources,registry,admission.task_id)
    if definition.fingerprint!=admission.plan['definition_fingerprint']:
        raise ValueError('Completed battle definition needs reconciliation')
    row=db.execute('SELECT receipt FROM task_battle_admissions WHERE role_id=? AND battle_id=?',
        (role_id,admission.battle_id)).fetchone()
    receipt=json.loads(row[0]) if row and row[0] else None
    if receipt is None or admission.phase=='admitted':raise ValueError('Task battle has no terminal receipt')
    if admission.phase!='won':return TaskBattleSettlement(admission,receipt['outcome'],replayed=True)
    actor,state=load_task_state(db,account_id,role_id,epoch)
    if admission.task_id not in state.completed:raise ValueError('Battle receipt and completed task disagree')
    completion=replay_completed_task_transaction(db,actor,admission.task_id,resources,inventory,*reward_rules,
        resource_rules=resource_rules,equipment_rules=equipment_rules)
    # A repeated battle state1 may replay finish dialogue/movie/effects. History
    # acknowledgement returns current balances without replaying presentation.
    messages=tuple(x for x in completion_messages(completion) if x[0]!=S_REFRESH_SCENARIO_QUEST_STATE)
    return TaskBattleSettlement(admission,receipt['outcome'],completion,messages,True)


def acknowledge_task_battle_transaction(db,account_id,role_id,epoch,resources,registry,battle_id,inventory,*,
                                       growth_rules=None,attribute_rules=None,currency_rules=None,pet_experience_rules=None,
                                       resource_rules=None,equipment_rules=None):
    """Trusted current-lease recovery of an EXISTING terminal receipt only."""
    _owner(db,account_id,role_id,epoch);_inventory_scope(inventory,account_id,role_id)
    admission=_read(db,role_id,battle_id,replayed=True)
    return _ack(db,account_id,role_id,epoch,resources,registry,admission,inventory,
        (growth_rules,attribute_rules,currency_rules,pet_experience_rules),
        resource_rules=resource_rules,equipment_rules=equipment_rules)


def settle_task_battle_transaction(db,account_id,role_id,epoch,resources,registry,finished,inventory,*,
                                   growth_rules=None,attribute_rules=None,currency_rules=None,pet_experience_rules=None,
                                   resource_rules=None,equipment_rules=None):
    """Authoritative formal-PVE terminal event, never an inbound client result.

    Combat HP/MP, captured assets and battle outbox receipt must join the host's
    SAME outer transaction. This Module writes only task/common reward receipts.
    The initial NPC deadline is not a combat timeout; admitted long fights may
    settle after it. Current lease and the frozen combat snapshot still match.
    """
    _owner(db,account_id,role_id,epoch);_inventory_scope(inventory,account_id,role_id)
    admission,definition=_validated_terminal(db,role_id,epoch,resources,registry,finished)
    return _settle_terminal(db,account_id,role_id,epoch,resources,registry,finished,inventory,admission,definition,
        (growth_rules,attribute_rules,currency_rules,pet_experience_rules),
        resource_rules=resource_rules,equipment_rules=equipment_rules)


def _validated_terminal(db,role_id,expected_epoch,resources,registry,finished):
    if (not isinstance(finished,BattleFinished) or finished.scope!=TASK_BATTLE_SCOPE
            or finished.task_event_eligible is not True or finished.role_id!=role_id or finished.login_epoch!=expected_epoch
            or type(finished.battle_id) is not str or not 1<=len(finished.battle_id)<=128
            or finished.settlement_id!=SETTLEMENT_PREFIX+finished.battle_id
            or type(finished.won) is not bool or type(finished.rounds) is not int or finished.rounds<1
            or type(finished.snapshot_version) is not int or finished.snapshot_version<=0
            or type(finished.winner_side) is not int or finished.winner_side not in (-1,0,1)
            or finished.outcome not in ('victory','defeat','draw','escape')
            or finished.won!=(finished.outcome=='victory' and finished.winner_side==0)
            or finished.outcome=='victory' and (not finished.won or finished.winner_side!=0)
            or finished.outcome=='defeat' and finished.winner_side!=1
            or finished.outcome=='draw' and finished.winner_side!=-1
            or finished.outcome=='escape' and finished.winner_side==0
            or type(finished.currency_reward) is not int or finished.currency_reward!=0
            or finished.item_rewards!=() or type(finished.combat_resources) is not tuple):
        raise ValueError('Invalid/unqualified task-PVE terminal event; training/wild are not task evidence')
    admission=_read(db,role_id,finished.battle_id)
    plan=admission.plan
    definition=_definition(resources,registry,admission.task_id)
    if (plan['epoch']!=expected_epoch or plan['engine_revision']!=finished.revision
            or plan['participant']['attribute_version']!=finished.snapshot_version
            or definition.fingerprint!=plan['definition_fingerprint']
            or (plan['battle_id'],plan['role_id'],plan['scope'],plan['settlement_id'],plan['ai_id'])
                !=(finished.battle_id,role_id,TASK_BATTLE_SCOPE,finished.settlement_id,definition.ai_id)
            or (plan['participant']['role_id'],plan['participant']['login_epoch'])!=(role_id,expected_epoch)):
        raise ValueError('Task battle result changed its admission identity/snapshot')
    return admission,definition


def _settle_terminal(db,account_id,role_id,epoch,resources,registry,finished,inventory,admission,definition,
        reward_rules,*,resource_rules=None,equipment_rules=None):
    """Write only after ordinary epoch or explicit recovery evidence validated."""
    fingerprint=_hash(asdict(finished))
    old=db.execute('SELECT result_fingerprint FROM task_battle_admissions WHERE role_id=? AND battle_id=?',
        (role_id,finished.battle_id)).fetchone()[0]
    if old is not None:
        if old!=fingerprint:raise ValueError('Conflicting task battle terminal result')
        return _ack(db,account_id,role_id,epoch,resources,registry,_read(db,role_id,finished.battle_id,replayed=True),
            inventory,reward_rules,resource_rules=resource_rules,equipment_rules=equipment_rules)
    if admission.phase!='admitted':raise ValueError('Task battle is not awaiting a result')
    actor,state=load_task_state(db,account_id,role_id,epoch)
    if admission.task_id not in state.active:raise ValueError('Admitted task is no longer active')
    completion=None;messages=()
    phase='lost'
    if finished.won:
        evidence=TaskEvidence(admission.task_id,role_id,epoch,'battle_won',finished.settlement_id,
            definition.map_id,definition.npc_id,definition.ai_id)
        task_plan=TaskDomain(resources).plan(actor,state,'complete',admission.task_id,evidence=evidence)
        completion=complete_task_transaction(db,actor,task_plan,finished.settlement_id,resources,inventory,*reward_rules,
            resource_rules=resource_rules,equipment_rules=equipment_rules)
        messages=completion_messages(completion);phase='won'
    receipt=dict(battle_id=finished.battle_id,task_id=admission.task_id,settlement_id=finished.settlement_id,
        outcome=finished.outcome,phase=phase)
    db.execute('UPDATE task_battle_admissions SET phase=?,result_fingerprint=?,receipt=? WHERE role_id=? AND battle_id=?',
        (phase,fingerprint,_json(receipt),role_id,finished.battle_id))
    return TaskBattleSettlement(_read(db,role_id,finished.battle_id),finished.outcome,completion,messages)


def _recovered_current_ack(db,account_id,role_id,epoch,resources,registry,admission,finished,inventory,*,
        currency_rules=None,resource_rules=None,equipment_rules=None):
    """Paid recovery is a pure current query, not reward/chain reconciliation."""
    receipt=db.execute('SELECT receipt FROM task_battle_admissions WHERE role_id=? AND battle_id=?',
        (role_id,finished.battle_id)).fetchone()[0]
    expected=dict(battle_id=finished.battle_id,task_id=admission.task_id,settlement_id=finished.settlement_id,
        outcome=finished.outcome,phase='won' if finished.won else 'lost')
    if admission.phase!=expected['phase'] or not receipt or json.loads(receipt)!=expected:
        raise ValueError('Recovered terminal receipt differs from the original outcome')
    if admission.phase!='won':
        return TaskBattleSettlement(admission,finished.outcome,replayed=True)
    read_completed_task_battle_proof(db,account_id,role_id,epoch,resources,registry,admission.task_id)
    actor,_=load_task_state(db,account_id,role_id,epoch)
    profile=current_task_resource_profile(db,actor,inventory,resource_rules,equipment_rules)
    if profile is None:profile=attribute_snapshot_if_initialized(db,account_id,role_id,epoch)
    growth=(growth_refresh(read_growth(db,account_id,role_id),profile),) if profile is not None else ()
    wallet=()
    if currency_rules is not None:
        try:wallet=read_wallet(db,account_id,role_id,epoch,currency_rules)
        except WalletNotInitialized:pass
    messages=((S_REFRESH_USER_EXP,encode_user_experience(read_experience(db,account_id,role_id).experience)),)+tuple(
        encode_currency_balance(row.currency,row.balance) for row in wallet if row.currency in ('cash','bound_silver'))+growth
    return TaskBattleSettlement(admission,finished.outcome,messages=messages,replayed=True)


def read_task_battle_current_transaction(db,account_id,role_id,epoch,resources,registry,finished,inventory,*,
        currency_rules=None,resource_rules=None,equipment_rules=None):
    """Pure paid-terminal query under the same OR a new current lease.

    Requires an already stored identical original terminal. Does not recover a
    pending battle, verify a new producer, reconcile rewards or activate tasks.
    """
    _owner(db,account_id,role_id,epoch);_inventory_scope(inventory,account_id,role_id)
    if not isinstance(finished,BattleFinished) or not valid_task_epoch(finished.login_epoch):
        raise ValueError('Original formal terminal required for paid current query')
    admission,_=_validated_terminal(db,role_id,finished.login_epoch,resources,registry,finished)
    old=db.execute('SELECT result_fingerprint FROM task_battle_admissions WHERE role_id=? AND battle_id=?',
        (role_id,finished.battle_id)).fetchone()[0]
    if old is None or old!=_hash(asdict(finished)):
        raise ValueError('No identical settled original task terminal')
    return _recovered_current_ack(db,account_id,role_id,epoch,resources,registry,
        _read(db,role_id,finished.battle_id,replayed=True),finished,inventory,
        currency_rules=currency_rules,resource_rules=resource_rules,equipment_rules=equipment_rules)


def recover_task_battle_transaction(db,account_id,role_id,epoch,resources,registry,finished,inventory,witness,*,
        growth_rules=None,attribute_rules=None,currency_rules=None,pet_experience_rules=None,
        resource_rules=None,equipment_rules=None):
    """Current-lease consume of a verified OLD-lease durable formal terminal.

    Host verifies the original producer, complete Participant/resource sources
    and current CAS; resource writes, Task rewards/terminal and its consumer
    receipt/outbox-settled marker join this SAME transaction. Missing producer
    or drift leaves it pending. Never edit finished.login_epoch to make it fit.
    The ordinary settle/ack Interfaces keep their original epoch/receipt rules.
    """
    _owner(db,account_id,role_id,epoch);_inventory_scope(inventory,account_id,role_id)
    if (type(witness) is not TaskBattleRecoveryWitness or type(witness.role_id) is not int
            or witness.role_id!=role_id or witness.current_epoch!=epoch or type(witness.current_epoch) is not type(epoch)
            or witness.recovery_revision!=TASK_TERMINAL_RECOVERY_REVISION
            or any(not _sha(v) for v in (witness.admission_fingerprint,witness.terminal_fingerprint,
                witness.producer_fingerprint,witness.source_fingerprint))
            or type(witness.producer_receipt_id) is not str or not 1<=len(witness.producer_receipt_id)<=160
            or not isinstance(finished,BattleFinished) or not valid_task_epoch(finished.login_epoch)
            or str(finished.login_epoch)==str(epoch)):
        raise ValueError('Verified original producer and current-lease recovery witness required')
    admission,definition=_validated_terminal(db,role_id,finished.login_epoch,resources,registry,finished)
    fingerprint=_hash(asdict(finished))
    if (witness.admission_fingerprint!=admission.fingerprint or witness.terminal_fingerprint!=fingerprint
            or admission.task_id not in registry.enabled_task_ids
            or registry.engine_revision!=admission.plan['engine_revision']):
        raise ValueError('Recovery witness or current formal capability differs from original admission/terminal')
    old=db.execute('SELECT result_fingerprint FROM task_battle_admissions WHERE role_id=? AND battle_id=?',
        (role_id,finished.battle_id)).fetchone()[0]
    if old is not None:
        if old!=fingerprint:raise ValueError('Conflicting durable task battle terminal')
        return _recovered_current_ack(db,account_id,role_id,epoch,resources,registry,
            _read(db,role_id,finished.battle_id,replayed=True),finished,inventory,
            currency_rules=currency_rules,resource_rules=resource_rules,equipment_rules=equipment_rules)
    actor,state=load_task_state(db,account_id,role_id,epoch)
    if admission.task_id not in state.active:
        raise ValueError('Pending terminal recovery requires its original active task')
    TaskDomain(resources).plan(actor,state,'offer',admission.task_id)
    return _settle_terminal(db,account_id,role_id,epoch,resources,registry,finished,inventory,admission,definition,
        (growth_rules,attribute_rules,currency_rules,pet_experience_rules),
        resource_rules=resource_rules,equipment_rules=equipment_rules)


def cancel_task_battle_transaction(db,account_id,role_id,epoch,aborted):
    """Host-confirmed BattleAborted; a new valid lease may retire an old battle.

    Merely expiring a client/dialogue wait never calls this. Host first retires
    the authoritative old battle; no task/reward/HP/MP changes are inferred.
    """
    _owner(db,account_id,role_id,epoch)
    if not isinstance(aborted,BattleAborted) or aborted.role_id!=role_id:
        raise ValueError('Authoritative task battle cancellation required')
    admission=_read(db,role_id,aborted.battle_id)
    if admission.plan['epoch']!=aborted.login_epoch or not aborted.reason:
        raise ValueError('Battle cancellation scope mismatch')
    fingerprint=_hash(asdict(aborted))
    if admission.phase=='cancelled':
        old=db.execute('SELECT result_fingerprint FROM task_battle_admissions WHERE role_id=? AND battle_id=?',
            (role_id,aborted.battle_id)).fetchone()[0]
        if old!=fingerprint:raise ValueError('Conflicting battle cancellation')
        return TaskBattleSettlement(admission,'cancelled',replayed=True)
    if admission.phase!='admitted':raise ValueError('Terminal task battle cannot be cancelled')
    receipt=dict(battle_id=aborted.battle_id,task_id=admission.task_id,outcome='cancelled',reason=aborted.reason)
    db.execute("UPDATE task_battle_admissions SET phase='cancelled',result_fingerprint=?,receipt=? WHERE role_id=? AND battle_id=?",
        (fingerprint,_json(receipt),role_id,aborted.battle_id))
    return TaskBattleSettlement(_read(db,role_id,aborted.battle_id),'cancelled')
