"""Original static type56 objectives, joined to the caller's role transaction.

World/role owners supply the current Location and frozen command; wire commits
alone never prove arrival. No movement, activation, connection, commit or send.
"""
from dataclasses import dataclass,asdict,replace
import hashlib
import json
from types import MappingProxyType
from tasks import _plain
from task_domain import TaskDomain,TaskEvidence,supports_static_region
from task_persistence import load_task_state
from task_session import TaskIntent
from task_protocol import C_COMMIT_SCENARIO_QUEST,S_REFRESH_SCENARIO_QUEST_STATE
from task_workflow import complete_task_transaction,replay_completed_task_transaction,completion_messages
from world_owner import Location,MapAddress


def _json(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'))


def _hash(value):
    return hashlib.sha256(_json(value).encode()).hexdigest()


@dataclass(frozen=True)
class RegionDefinition:
    task_id:int
    map_id:int
    rectangle:tuple
    fingerprint:str


@dataclass(frozen=True)
class RegionResources:
    definitions:object
    exclusions:object


def load_region_resources(resources):
    """Startup, immutable original definitions; no file reads or enrollment."""
    definitions={};exclusions={}
    for q,task in resources.definitions.items():
        if task['type']!=56:continue
        if not supports_static_region(task):
            exclusions[q]='extra_mechanic_or_invalid_original_rectangle'
            continue
        a=task['attributes']
        rect=tuple(int(a[k])*16 for k in (
            'ActiveInfoLeftPos','ActiveInfoTopPos','ActiveInfoRightPos','ActiveInfoBottomPos'))
        definitions[q]=RegionDefinition(q,task['target']['map_id'],rect,_hash(_plain(task)))
    return RegionResources(MappingProxyType(definitions),MappingProxyType(exclusions))


def prepare_region_storage(db):
    """Startup DDL only. Caller provides the storage connection."""
    db.executescript('''CREATE TABLE IF NOT EXISTS task_region_receipts (
        role_id INTEGER NOT NULL REFERENCES roles(id),task_id INTEGER NOT NULL,
        request_id TEXT NOT NULL,command_fingerprint TEXT NOT NULL,
        definition_fingerprint TEXT NOT NULL,source_event TEXT NOT NULL,evidence TEXT NOT NULL,
        PRIMARY KEY(role_id,task_id),UNIQUE(role_id,request_id));''')


@dataclass(frozen=True)
class RegionCommand:
    intent:TaskIntent
    location:Location
    generation:int
    task_revision:int
    request_id:str
    source_id:str
    deadline_ms:int
    definition_fingerprint:str


@dataclass(frozen=True)
class RegionResult:
    task_id:int
    request_id:str
    source_event:str
    completion:object
    messages:tuple
    replayed:bool


def _intent(intent):
    if (not isinstance(intent,TaskIntent) or intent.kind!=C_COMMIT_SCENARIO_QUEST
            or type(intent.task_id) is not int or not 1001<=intent.task_id<=499999
            or type(intent.npc_key) is not int or intent.npc_key!=0
            or type(intent.opaque) is not int or intent.opaque!=0):
        raise ValueError('Region requires original CCommit(taskID,npcKey0,option0)')


def _context(command,generation,now_ms):
    if (not isinstance(command,RegionCommand) or type(generation) is not int or generation<=0
            or command.generation!=generation or type(command.generation) is not int
            or type(now_ms) is not int or not 0<=now_ms<=2**63-1
            or type(command.deadline_ms) is not int or not 0<command.deadline_ms<=2**63-1
            or type(command.task_revision) is not int or command.task_revision<0
            or any(type(v) is not str or not 1<=len(v)<=160 for v in (command.request_id,command.source_id))):
        raise ValueError('Invalid region owner command context')
    _intent(command.intent)


def _location(location,role_id,epoch):
    if (not isinstance(location,Location) or not isinstance(location.address,MapAddress)
            or (location.role_id,location.login_epoch)!=(role_id,epoch)
            or location.state!='active' or type(location.version) is not int or location.version<=0
            or type(location.address.map_id) is not int or location.address.map_id<=0
            or any(type(v) is not int or v<0 for v in (location.x,location.y,
                location.address.instance_id,location.address.partition_id))
            or not 0<=location.x<32768 or not 0<=location.y<32768):
        raise ValueError('Missing active, versioned authoritative region location')


def plan_region_completion(actor,snapshot,command,current,resources,regions,*,generation,now_ms):
    """Pure objective Interface. current must come from the owning map Adapter.

    Designed freshness policy: require the captured Location to equal the
    authoritative current Location, including instance/version, when admitted.
    Moving/loading commands are retried with a new observation and request ID.
    The caller preserves that admission order when the DB work is dispatched;
    later movement cannot revoke an already accepted fact or change its coords.
    """
    _context(command,generation,now_ms)
    _location(command.location,actor.role_id,actor.login_epoch)
    _location(current,actor.role_id,actor.login_epoch)
    definition=regions.definitions.get(command.intent.task_id)
    if (now_ms>=command.deadline_ms or command.location!=current
            or command.task_revision!=snapshot.revision or definition is None
            or definition.fingerprint!=command.definition_fingerprint
            or current.address.map_id!=definition.map_id):
        raise ValueError('Expired, moved or unsupported region objective')
    source='region:'+_hash(asdict(command))
    evidence=TaskEvidence(command.intent.task_id,actor.role_id,actor.login_epoch,
        'region_reached',source,map_id=current.address.map_id,
        region_position=(current.x,current.y),region_version=current.version)
    plan=TaskDomain(resources).plan(actor,snapshot,'complete',command.intent.task_id,evidence=evidence)
    # Keep original post-completion text even though its UI consumption remains
    # unconfirmed. Existing common plans already retain finish/NPC/next literals.
    note=resources.definitions[command.intent.task_id]['attributes'].get('NoteInfo','')
    if note:plan=replace(plan,continuation_fields=plan.continuation_fields+(('NoteInfo',note),))
    return plan


def _scope(db,account_id,role_id,epoch,inventory):
    if inventory.account_id!=account_id or inventory.role_id!=role_id:
        raise ValueError('Region inventory owner mismatch')
    # Public caller-transaction reader fences the actual current lease before
    # any journal, reward, pending-channel reconciliation or receipt mutation.
    inventory.immutable_snapshot_transaction(db,epoch=epoch)
    return load_task_state(db,account_id,role_id,epoch)


def _record(db,role_id,task_id):
    return db.execute('SELECT request_id,command_fingerprint,definition_fingerprint,source_event,evidence '
        'FROM task_region_receipts WHERE role_id=? AND task_id=?',(role_id,task_id)).fetchone()


def _result(db,actor,row,completion,inventory,*,replayed):
    messages=completion_messages(completion)
    if replayed:
        messages=tuple((kind,body) for kind,body in messages if kind!=S_REFRESH_SCENARIO_QUEST_STATE)
    # Pre-encode before commit: missing wallet/native bag errors roll back the
    # complete objective, rewards, chain and regional receipt together.
    messages=inventory.equipment_bag_messages(db,actor.login_epoch)+messages
    return RegionResult(completion.rewards.task_id,row[0],row[3],completion,messages,replayed)


def _ack(db,actor,state,intent,resources,regions,inventory,reward_rules,*,resource_rules=None,equipment_rules=None):
    _intent(intent)
    row=_record(db,actor.role_id,intent.task_id)
    definition=regions.definitions.get(intent.task_id)
    if (row is None or definition is None or row[2]!=definition.fingerprint
            or intent.task_id not in state.completed):
        raise ValueError('No matching durable region completion to acknowledge')
    effect=db.execute('SELECT payload FROM task_effects WHERE role_id=? AND task_id=?',
        (actor.role_id,intent.task_id)).fetchone()
    if effect is None or json.loads(effect[0]).get('source_event')!=row[3]:
        raise ValueError('Region receipt and completed task evidence differ')
    completion=replay_completed_task_transaction(db,actor,intent.task_id,resources,inventory,*reward_rules,
        resource_rules=resource_rules,equipment_rules=equipment_rules)
    return _result(db,actor,row,completion,inventory,replayed=True)


def complete_region_transaction(db,account_id,role_id,epoch,command,current,resources,regions,inventory,*,
        generation,now_ms,growth_rules=None,attribute_rules=None,currency_rules=None,pet_experience_rules=None,
        resource_rules=None,equipment_rules=None):
    """One requested task, original rewards and durable world evidence, one txn.

    Role/map admission must already be ordered and bounded. No map ownership is
    inferred from this dataclass's construction; raw wire data is insufficient.
    Caller commits before sending, rolls back on any exception. Paid retries
    acknowledge current balances without requiring the old position/deadline.
    Old lease/generation callbacks are refused even if a receipt already exists.
    """
    _context(command,generation,now_ms)
    _location(command.location,role_id,epoch)
    actor,state=_scope(db,account_id,role_id,epoch,inventory)
    fingerprint=_hash(asdict(command))
    request=db.execute('SELECT task_id,command_fingerprint FROM task_region_receipts '
        'WHERE role_id=? AND request_id=?',(role_id,command.request_id)).fetchone()
    if request and tuple(request)!=(command.intent.task_id,fingerprint):
        raise ValueError('Region request ID reused with different intent')
    rules=(growth_rules,attribute_rules,currency_rules,pet_experience_rules)
    row=_record(db,role_id,command.intent.task_id)
    if row is not None:
        definition=regions.definitions.get(command.intent.task_id)
        if definition is None or command.definition_fingerprint!=definition.fingerprint:
            raise ValueError('Region retry source definition changed')
        return _ack(db,actor,state,command.intent,resources,regions,inventory,rules,
            resource_rules=resource_rules,equipment_rules=equipment_rules)
    plan=plan_region_completion(actor,state,command,current,resources,regions,generation=generation,now_ms=now_ms)
    completion=complete_task_transaction(db,actor,plan,command.request_id,resources,inventory,*rules,
        resource_rules=resource_rules,equipment_rules=equipment_rules)
    db.execute('INSERT INTO task_region_receipts VALUES(?,?,?,?,?,?,?)',
        (role_id,plan.task_id,command.request_id,fingerprint,command.definition_fingerprint,
         plan.source_event,_json(asdict(command))))
    return _result(db,actor,_record(db,role_id,plan.task_id),completion,inventory,replayed=False)


def acknowledge_region_transaction(db,account_id,role_id,epoch,intent,resources,regions,inventory,*,
        growth_rules=None,attribute_rules=None,currency_rules=None,pet_experience_rules=None,
        resource_rules=None,equipment_rules=None):
    """Current owner reconnect acknowledgement; never creates arrival evidence."""
    actor,state=_scope(db,account_id,role_id,epoch,inventory)
    return _ack(db,actor,state,intent,resources,regions,inventory,
        (growth_rules,attribute_rules,currency_rules,pet_experience_rules),
        resource_rules=resource_rules,equipment_rules=equipment_rules)


