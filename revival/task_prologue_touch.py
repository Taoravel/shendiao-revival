"""Timed original blood-handprint interaction and atomic task/world settlement.

Caller supplies an explicit designed clock/target policy, map-owned NPC proof,
current lease, transaction and transfer receipt. No server routing, live I/O,
automatic policy activation, map ownership mutation or combat is performed here.
"""
from dataclasses import asdict,dataclass,replace
import hashlib
import json
from types import MappingProxyType
from uuid import uuid4
from inspect_client import OUT
from tasks import _plain
from task_domain import TaskDomain,TaskEvidence,PROLOGUE_TOUCH_IDS,supports_prologue_touch
from task_persistence import load_task_state,apply_task_plan
from task_workflow import complete_task_transaction,completion_messages
from task_growth_resources import current_task_resource_profile
from task_rewards import update_reward_delivery
from task_protocol import (ScenarioQuestInfo,S_ACCEPT_SCENARIO_QUEST,encode_accept_scenario_quest,
    S_REFRESH_SCENARIO_QUEST_STATE,encode_scenario_state,SCENARIO_READY,SCENARIO_ACTIVE,C_COMMIT_SCENARIO_QUEST)
from task_dialog_protocol import S_VISIT_NPC,encode_visit_npc
from task_session import TaskIntent
from task_newbie_chapter import NewbieChapterRules,read_newbie_chapter
from world_owner import Location,TransferCommit,MapAddress
from world_npcs import NpcInteraction
from world_catalog import valid_position
from world_collision import maze_clear,character_movement_mask
from world_transfer_storage import commit_transfer_transaction,load_map_instance_transaction
from world_story_instances import StoryInstanceRules,StoryInstanceIntent,load_story_instance_transaction


def _json(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'))


def _hash(value):
    return hashlib.sha256(_json(value).encode()).hexdigest()


@dataclass(frozen=True)
class TouchPolicy:
    revision:str
    minimum_duration_ms:int
    timeout_ms:int
    target_position:tuple
    provenance:str
    source_placement_id:int
    directory_revision:str
    private_instance_min:int
    private_instance_max:int
    target_partition_id:int


def load_touch_policy(path=OUT/'design/newbie-bloodmark-v1.json',directory_path=OUT/'design/story-instance-v1.json'):
    """Read the planner's two approved startup policies, without activation."""
    policy=json.loads(path.read_text(encoding='utf-8'))
    directory=json.loads(directory_path.read_text(encoding='utf-8'))
    target=policy['target'];scope=directory['scope']
    if (policy['revision']!='2026-10-23.newbie-bloodmark.1'
            or len(policy['tasks'])!=10 or set(policy['tasks'])!=PROLOGUE_TOUCH_IDS
            or policy['source']!={'map_id':1006,'npc_id':10498,'placement_id':13}
            or policy['original_progress']['value']!=3 or policy['original_progress']['text']!='触摸血手印'
            or policy['server_minimum_elapsed_ms']!=3000 or policy['ticket_timeout_ms']!=15000
            or tuple(target[k] for k in ('map_id','raw_x','raw_y','x','y','movement_state','walk_mask'))
                !=(1501,63,79,1008,1264,0,1)
            or directory['revision']!=policy['private_directory_policy']
            or directory['revision']!='2026-10-23.story-instance.1'
            or scope!={'kind':'newbie_bloodmark_dream','map_id':1501,'partition_id':0}
            or (directory['instance_id_min_inclusive'],directory['instance_id_max_exclusive'])!=(2**62,2**63)):
        raise ValueError('Approved bloodmark/private-instance policy requires review')
    return TouchPolicy(policy['revision'],3000,15000,(1501,1008,1264),'designed',13,
        directory['revision'],directory['instance_id_min_inclusive'],directory['instance_id_max_exclusive'],0)


@dataclass(frozen=True)
class TouchResources:
    policy:TouchPolicy
    fingerprint:str
    definitions:object
    chapter_rules:object
    route_tasks:object
    story_rules:object


def load_touch_resources(resources,policy,catalog,grids,*,chapter_rules,story_rules):
    """Startup only. This Interface never invents/loads an approved policy.

    Original scalar3 and target(1501,63,79) are facts. Milliseconds and resolved
    logical pixels are supplied explicitly by the policy owner, not inferred by
    the packet decoder. Every configured target must be normal-mask walkable.
    """
    if (not isinstance(policy,TouchPolicy) or type(policy.revision) is not str
            or not 1<=len(policy.revision)<=128 or policy.provenance!='designed'
            or type(policy.minimum_duration_ms) is not int or not 1<=policy.minimum_duration_ms<=60000
            or type(policy.timeout_ms) is not int or not policy.minimum_duration_ms<policy.timeout_ms<=300000
            or policy.source_placement_id!=13 or policy.directory_revision!='2026-10-23.story-instance.1'
            or (policy.private_instance_min,policy.private_instance_max,policy.target_partition_id)!=(2**62,2**63,0)
            or type(policy.target_position) is not tuple or len(policy.target_position)!=3
            or any(type(v) is not int for v in policy.target_position)
            or policy.target_position[0]!=1501 or not valid_position(policy.target_position,catalog)
            or 1501 not in grids or not maze_clear(grids[1501],*policy.target_position[1:],mask=1)):
        raise ValueError('Explicit reviewed touch clock/target policy required')
    definitions={q:resources.definitions[q] for q in PROLOGUE_TOUCH_IDS
                 if q in resources.definitions and supports_prologue_touch(resources.definitions[q])}
    if set(definitions)!=PROLOGUE_TOUCH_IDS:
        raise ValueError('Original current-route blood-handprint source changed')
    for task in definitions.values():
        successor=resources.definitions.get(task['next_ids'][0])
        if (successor is None or successor['type']!=40 or successor['target']['map_id']!=1501
                or successor['target']['npc_id']!=10908 or int(successor['attributes'].get('AIInfoAIID',0))!=8001):
            raise ValueError('Original handprint battle successor changed')
    if not isinstance(chapter_rules,NewbieChapterRules) or len(chapter_rules.routes)!=43:
        raise ValueError('Explicit original newbie chapter rules required')
    route_tasks={}
    for key,route in chapter_rules.routes.items():
        q=route.successor_task_id;seen=set()
        while q not in definitions:
            if q in seen or len(seen)>=20 or q not in resources.definitions:
                raise ValueError('Creation route does not reach an original handprint')
            seen.add(q);edges=tuple(resources.definitions[q]['next_ids'])
            if len(edges)!=1:
                raise ValueError('Ambiguous original path to handprint')
            q=edges[0]
        route_tasks[key]=q
    if set(route_tasks.values())!=PROLOGUE_TOUCH_IDS:
        raise ValueError('Original43 routes do not cover the exact ten handprints')
    if (not isinstance(story_rules,StoryInstanceRules) or story_rules.revision!=policy.directory_revision
            or story_rules.chapter_rules!=chapter_rules or dict(story_rules.source_tasks)!=route_tasks
            or (story_rules.map_id,story_rules.partition_id,story_rules.minimum_id,story_rules.maximum_id)
                !=(1501,policy.target_partition_id,policy.private_instance_min,policy.private_instance_max)):
        raise ValueError('Touch and world directory policy/route snapshots disagree')
    route_basis=[(asdict(chapter_rules.routes[key]),q) for key,q in sorted(route_tasks.items())]
    fingerprint=_hash((asdict(policy),{q:_plain(t) for q,t in definitions.items()},chapter_rules.revision,route_basis))
    return TouchResources(policy,fingerprint,MappingProxyType(definitions),chapter_rules,
        MappingProxyType(route_tasks),story_rules)


@dataclass(frozen=True)
class TouchTransferIntent:
    task_id:int
    source:Location
    task_revision:int
    generation:int
    entity_key:int
    npc_source_id:str
    opened_ms:int
    earliest_ms:int
    deadline_ms:int
    request_id:str
    policy_fingerprint:str
    target_position:tuple
    target_address:MapAddress
    chapter_id:str
    directory_intent:StoryInstanceIntent


@dataclass(frozen=True)
class TouchDialogue:
    intent:TouchTransferIntent
    messages:tuple


@dataclass(frozen=True)
class TouchResult:
    transfer_id:str
    target:Location | None
    completion:object
    messages:tuple
    replayed:bool


def prepare_touch_storage(db):
    """Startup only. World persistence and inventory schemas remain external."""
    db.executescript('''CREATE TABLE IF NOT EXISTS task_prologue_touches (
        role_id INTEGER NOT NULL REFERENCES roles(id),task_id INTEGER NOT NULL,
        transfer_id TEXT NOT NULL UNIQUE,fingerprint TEXT NOT NULL,
        intent TEXT NOT NULL,world_receipt TEXT NOT NULL,source_event TEXT NOT NULL,
        PRIMARY KEY(role_id,task_id));''')


def _scope(db,account_id,role_id,epoch,resources,touch,task_id):
    chapter=read_newbie_chapter(db,account_id,role_id,epoch,touch.chapter_rules)
    actor,state=load_task_state(db,account_id,role_id,epoch)
    task=touch.definitions.get(task_id)
    if (task is None or _plain(task)!=_plain(resources.definitions.get(task_id))
            or task['incoming_ids'][0] not in state.completed):
        raise ValueError('Touch requires its exact completed original predecessor')
    if chapter is None or chapter.phase!='completed':
        raise ValueError('Touch requires explicit completed newbie creation provenance')
    route=chapter.origin.route
    school=db.execute('SELECT school FROM roles WHERE id=?',(role_id,)).fetchone()[0]
    if (touch.route_tasks.get((route.character_id,route.school_id))!=task_id
            or route.school_id!=school or resources.shape_to_role_config.get(actor.shape)!=route.character_id
            or route.intro_task_id not in state.completed):
        raise ValueError('Touch task differs from the frozen character/school chapter')
    return actor,state,task,chapter


def _bound_source(db,account_id,role_id,epoch,location,*,exact_checkpoint=False):
    """Private travel cannot silently retain the legacy unknown-instance path."""
    current=load_map_instance_transaction(db,account_id,role_id,epoch)
    if (current is None or current.address!=location.address
            or exact_checkpoint and (current.position!=location.position or current.version!=location.version)):
        raise ValueError('Touch requires an explicitly adopted current source instance')


def _directory_intent(chapter,task_id):
    origin=chapter.origin
    return StoryInstanceIntent(origin.chapter_id,origin.creation_id,origin.policy,origin.route_fingerprint,task_id)


def _directory(db,account_id,role_id,epoch,touch,chapter,task_id,address,*,expected_intent=None):
    intent=_directory_intent(chapter,task_id)
    if expected_intent is not None and expected_intent!=intent:
        raise ValueError('Touch directory identity differs from the frozen creation chapter')
    # The world public Interface checks its complete persistent identity and
    # exact address; the task Module neither allocates nor copies directory SQL.
    load_story_instance_transaction(db,account_id,role_id,epoch,intent,touch.story_rules,expected_address=address)
    return intent


def _npc_context(proof,location,role_id,epoch,touch,*,entity_key=None):
    if (not isinstance(proof,NpcInteraction) or not isinstance(location,Location) or location.state!='active'
            or (proof.role_id,proof.login_epoch)!=(role_id,epoch)
            or (location.role_id,location.login_epoch)!=(role_id,epoch)
            or proof.address!=location.address or proof.position_version!=location.version
            or (proof.npc_id,location.address.map_id)!=(10498,1006)
            or proof.placement_id!=touch.policy.source_placement_id
            or proof.kind!='npc_interacted' or proof.position_validation!='bounds_version_distance'
            or type(proof.entity_key) is not int or not 0<proof.entity_key<2**63
            or entity_key is not None and proof.entity_key!=entity_key
            or type(proof.source_id) is not str or not 1<=len(proof.source_id)<=160):
        raise ValueError('Current blood-handprint map proof required')


def reconcile_touch_successor_transaction(db,account_id,role_id,epoch,resources,touch,predecessor_id):
    """Activate the exact touch edge only when the caller supplied its policy.

    Invoke after predecessor completion in the same transaction, or during
    trusted recovery of that durable pending edge. Generic TaskChain stays
    unchanged: without this Module's explicit policy the edge remains pending.
    Return only NEW IDs for bean publication, never reset an existing bean.
    """
    source=resources.definitions.get(predecessor_id)
    edges=tuple(source['next_ids']) if source is not None else ()
    if len(edges)!=1 or edges[0] not in touch.definitions:
        raise ValueError('No original handprint successor for this predecessor')
    task_id=edges[0]
    actor,state,_,_=_scope(db,account_id,role_id,epoch,resources,touch,task_id)
    if task_id in state.active|state.completed:
        return ()
    row=db.execute('SELECT payload FROM task_effects WHERE role_id=? AND task_id=?',
        (role_id,predecessor_id)).fetchone()
    if row is None:
        raise ValueError('Touch predecessor has no durable completion effect')
    effect=json.loads(row[0])
    if tuple(effect.get('next_ids',()))!=(task_id,):
        raise ValueError('Touch edge differs from predecessor completion')
    for action in ('offer','accept'):
        if action=='offer' and task_id in state.offered:
            continue
        apply_task_plan(db,actor,TaskDomain(resources).plan(actor,state,action,task_id),
            f'prologue-touch-activate:{predecessor_id}:{task_id}:{action}')
        actor,state=load_task_state(db,account_id,role_id,epoch)
    effect.update(chain_status='activated',chain_reason='approved_prologue_touch_policy',
        chain_target=task_id,chain_resolved=True)
    delivered=update_reward_delivery(effect)
    db.execute('UPDATE task_effects SET payload=?,delivered=? WHERE role_id=? AND task_id=?',
        (_json(effect),int(delivered),role_id,predecessor_id))
    return (task_id,)


def open_touch_transaction(db,account_id,role_id,epoch,resources,touch,task_id,proof,location,*,target_address,generation,now_ms):
    """Map validation already succeeded; return one role-owned pending intent.

    Owner replaces its prior pending intent on opening/movement/disconnect/map
    change. A menu timestamp is a designed earliest-submission fence, never a
    claim that the client acknowledged starting its local progress animation.
    """
    actor,state,task,chapter=_scope(db,account_id,role_id,epoch,resources,touch,task_id)
    _npc_context(proof,location,role_id,epoch,touch)
    if (task_id not in state.active or type(generation) is not int or generation<=0
            or type(now_ms) is not int or not 0<=now_ms<=2**63-1-touch.policy.timeout_ms
            or not isinstance(target_address,MapAddress) or target_address.map_id!=1501
            or type(target_address.instance_id) is not int
            or not touch.policy.private_instance_min<=target_address.instance_id<touch.policy.private_instance_max
            or type(target_address.partition_id) is not int or target_address.partition_id!=touch.policy.target_partition_id):
        raise ValueError('Current blood-handprint NPC/owner/clock required')
    _bound_source(db,account_id,role_id,epoch,location)
    directory_intent=_directory(db,account_id,role_id,epoch,touch,chapter,task_id,target_address)
    intent=TouchTransferIntent(task_id,location,state.revision,generation,proof.entity_key,proof.source_id,
        now_ms,now_ms+touch.policy.minimum_duration_ms,now_ms+touch.policy.timeout_ms,
        'touch:'+uuid4().hex,touch.fingerprint,touch.policy.target_position,target_address,
        chapter.origin.chapter_id,directory_intent)
    return TouchDialogue(intent,(
        (S_ACCEPT_SCENARIO_QUEST,encode_accept_scenario_quest(ScenarioQuestInfo(task_id,SCENARIO_READY,0,0,proof.entity_key))),
        (S_REFRESH_SCENARIO_QUEST_STATE,encode_scenario_state(task_id,SCENARIO_READY)),
        (S_VISIT_NPC,encode_visit_npc(proof.entity_key,(),(task_id,)))))


def _intent(intent,touch,role_id,epoch,generation,now_ms):
    if (not isinstance(intent,TouchTransferIntent) or not isinstance(intent.source,Location)
            or (intent.source.role_id,intent.source.login_epoch)!=(role_id,epoch)
            or intent.source.state!='active' or intent.source.address.map_id!=1006
            or intent.policy_fingerprint!=touch.fingerprint or intent.target_position!=touch.policy.target_position
            or not isinstance(intent.target_address,MapAddress) or intent.target_address.map_id!=1501
            or type(intent.target_address.instance_id) is not int
            or not touch.policy.private_instance_min<=intent.target_address.instance_id<touch.policy.private_instance_max
            or type(intent.target_address.partition_id) is not int or intent.target_address.partition_id!=touch.policy.target_partition_id
            or type(generation) is not int or generation<=0 or intent.generation!=generation
            or type(now_ms) is not int or not 0<=now_ms<=2**63-1
            or type(intent.opened_ms) is not int or intent.opened_ms<0
            or intent.earliest_ms!=intent.opened_ms+touch.policy.minimum_duration_ms
            or intent.deadline_ms!=intent.opened_ms+touch.policy.timeout_ms
            or type(intent.entity_key) is not int or not 0<intent.entity_key<2**63
            or type(intent.request_id) is not str or not 1<=len(intent.request_id)<=128
            or type(intent.chapter_id) is not str or not 1<=len(intent.chapter_id)<=128
            or not isinstance(intent.directory_intent,StoryInstanceIntent)
            or intent.directory_intent.chapter_id!=intent.chapter_id or intent.directory_intent.source_task_id!=intent.task_id
            or type(intent.task_revision) is not int or intent.task_revision<0):
        raise ValueError('Invalid or stale touch intent')


def authorize_touch_transfer(db,account_id,role_id,epoch,resources,touch,intent,command,location,*,proof,generation,now_ms):
    """Require a newly map-validated NPC proof and a mature original CCommit.

    Caller obtains this proof from the map owner before opening the SQL txn;
    no cross-owner await occurs while this Module holds a persistence transaction.
    """
    _intent(intent,touch,role_id,epoch,generation,now_ms)
    _npc_context(proof,location,role_id,epoch,touch,entity_key=intent.entity_key)
    _,state,_,chapter=_scope(db,account_id,role_id,epoch,resources,touch,intent.task_id)
    _directory(db,account_id,role_id,epoch,touch,chapter,intent.task_id,intent.target_address,
        expected_intent=intent.directory_intent)
    if (intent.task_id not in state.active or state.revision!=intent.task_revision or location!=intent.source
            or intent.chapter_id!=chapter.origin.chapter_id
            or not intent.earliest_ms<=now_ms<intent.deadline_ms or not isinstance(command,TaskIntent)
            or (command.kind,command.task_id,command.npc_key,command.opaque)!=
                (C_COMMIT_SCENARIO_QUEST,intent.task_id,intent.entity_key,0)):
        raise ValueError('Premature, moved or mismatched blood-handprint commit')
    return intent


def _receipt(intent,receipt):
    if not isinstance(receipt,TransferCommit):
        raise ValueError('Touch requires the world loading receipt')
    frozen=receipt.frozen.source
    reservation=receipt.frozen.reservation
    offer=reservation.offer
    target=receipt.location
    if (offer.transfer_id!=intent.request_id or offer.source!=intent.source
            or offer.target_position!=intent.target_position or offer.deadline_ms!=intent.deadline_ms
            or frozen!=replace(intent.source,version=intent.source.version+1,state='frozen')
            or target!=replace(frozen,address=reservation.target,version=frozen.version+1,
                x=intent.target_position[1],y=intent.target_position[2],state='loading')
            or reservation.target!=intent.target_address
            or target.address.map_id!=1501 or target.address==intent.source.address):
        raise ValueError('Touch and world transfer receipt differ')
    return target


def complete_touch_transfer_transaction(db,account_id,role_id,epoch,resources,touch,intent,receipt,inventory,*,
        generation,now_ms,movement_state,growth_rules=None,attribute_rules=None,currency_rules=None,
        pet_experience_rules=None,resource_rules=None,equipment_rules=None):
    """Commit target and completion in the caller transaction; encode before commit.

    Map owners reserve/freeze/create the loading receipt first. On later failure
    the caller rolls back and fences uncertain owners, following the existing
    world recovery contract. No actor/world state is changed by this Module.
    """
    _intent(intent,touch,role_id,epoch,generation,now_ms)
    actor,state,task,chapter=_scope(db,account_id,role_id,epoch,resources,touch,intent.task_id)
    if intent.chapter_id!=chapter.origin.chapter_id:
        raise ValueError('Touch intent belongs to another newbie chapter')
    _directory(db,account_id,role_id,epoch,touch,chapter,intent.task_id,intent.target_address,
        expected_intent=intent.directory_intent)
    snapshot=inventory.immutable_snapshot_transaction(db,epoch=epoch)
    if snapshot.role_id!=role_id or inventory.account_id!=account_id:
        raise ValueError('Touch inventory belongs to another role')
    current_task_resource_profile(db,actor,inventory,resource_rules,equipment_rules)
    target=_receipt(intent,receipt)
    if character_movement_mask(movement_state)!=1:
        raise ValueError('Touch travel requires normal movement state')
    encoded_intent=_json(asdict(intent));encoded_receipt=_json(asdict(receipt))
    fingerprint=_hash((touch.fingerprint,asdict(intent),asdict(receipt)))
    source='prologue-touch:'+fingerprint
    expected=(intent.request_id,fingerprint,encoded_intent,encoded_receipt,source)
    old=db.execute('SELECT transfer_id,fingerprint,intent,world_receipt,source_event '
        'FROM task_prologue_touches WHERE role_id=? AND task_id=?',(role_id,intent.task_id)).fetchone()
    reward_rules=(growth_rules,attribute_rules,currency_rules,pet_experience_rules)
    if old is not None:
        if tuple(old)!=expected or intent.task_id not in state.completed:
            raise ValueError('Conflicting touch completion replay')
        effect=db.execute('SELECT payload FROM task_effects WHERE role_id=? AND task_id=?',
            (role_id,intent.task_id)).fetchone()
        if effect is None or json.loads(effect[0]).get('source_event')!=source:
            raise ValueError('Touch receipt differs from its durable task evidence')
        if commit_transfer_transaction(db,account_id,role_id,epoch,receipt):
            raise ValueError('Touch completion lacks matching committed world decision')
        # These exact original tasks award zero in every channel. There is
        # nothing left to settle. Re-running the general recovery workflow
        # would rewrite effects and attempt successor activation again.
        # No historical target/messages are returned for callers to republish.
        return TouchResult(intent.request_id,None,None,(),True)
    if (intent.task_id not in state.active or state.revision!=intent.task_revision
            or task['next_ids'][0] in state.active|state.completed
            or not intent.earliest_ms<=now_ms<intent.deadline_ms):
        raise ValueError('Premature or stale touch transfer')
    _bound_source(db,account_id,role_id,epoch,intent.source,exact_checkpoint=True)
    if not commit_transfer_transaction(db,account_id,role_id,epoch,receipt):
        raise ValueError('World committed without atomic touch completion')
    evidence=TaskEvidence(intent.task_id,role_id,epoch,'prologue_touch_transfer_committed',source,
        map_id=1006,npc_id=10498,reference_id=1501)
    plan=TaskDomain(resources).plan(actor,state,'complete',intent.task_id,evidence=evidence)
    completion=complete_task_transaction(db,actor,plan,intent.request_id,resources,inventory,*reward_rules,
        resource_rules=resource_rules,equipment_rules=equipment_rules)
    successor=task['next_ids'][0]
    actor,after=load_task_state(db,account_id,role_id,epoch)
    if successor not in after.active:
        for action in ('offer','accept'):
            if action=='offer' and successor in after.offered:
                continue
            apply_task_plan(db,actor,TaskDomain(resources).plan(actor,after,action,successor),
                f'prologue-touch-next:{intent.task_id}:{successor}:{action}')
            actor,after=load_task_state(db,account_id,role_id,epoch)
        completion=replace(completion,started_tasks=completion.started_tasks+(successor,),
            started_infos=completion.started_infos+(ScenarioQuestInfo(successor,SCENARIO_ACTIVE,0,0,0),))
    if completion.started_tasks!=(successor,):
        raise ValueError('Touch must activate only its original paused battle successor')
    effect=json.loads(db.execute('SELECT payload FROM task_effects WHERE role_id=? AND task_id=?',
        (role_id,intent.task_id)).fetchone()[0])
    effect['continuation_resolved_fields']=sorted(set(effect.get('continuation_resolved_fields',()))|{
        'RewardMapJumpType','RewardMapID','RewardMapXPos','RewardMapYPos'})
    effect['touch_transfer']={'transfer_id':intent.request_id,'policy':touch.policy.revision,
        'policy_fingerprint':touch.fingerprint,'target':asdict(target),'gui_confirmed':False}
    effect.update(chain_status='activated',chain_reason='approved_prologue_touch_successor',
        chain_target=successor,chain_resolved=True)
    delivered=update_reward_delivery(effect)
    db.execute('UPDATE task_effects SET payload=?,delivered=? WHERE role_id=? AND task_id=?',
        (_json(effect),int(delivered),role_id,intent.task_id))
    db.execute('INSERT INTO task_prologue_touches VALUES(?,?,?,?,?,?,?)',(role_id,intent.task_id,*expected))
    return TouchResult(intent.request_id,target,completion,completion_messages(completion),False)


def resume_touch_messages(db,account_id,role_id,epoch,resources,touch):
    """Restore this original chapter's active touch/battle bean, never combat."""
    chapter=read_newbie_chapter(db,account_id,role_id,epoch,touch.chapter_rules)
    if chapter is None or chapter.phase!='completed':
        return ()
    route=chapter.origin.route
    task_id=touch.route_tasks.get((route.character_id,route.school_id))
    if task_id is None:
        raise ValueError('Unknown touch chapter route')
    actor,state=load_task_state(db,account_id,role_id,epoch)
    if task_id not in state.active|state.completed:
        return ()
    _,state,task,_=_scope(db,account_id,role_id,epoch,resources,touch,task_id)
    successor=task['next_ids'][0]
    if task_id in state.active and successor in state.active|state.completed:
        raise ValueError('Touch and successor phases conflict')
    active=(task_id,) if task_id in state.active else ((successor,) if successor in state.active else ())
    return tuple((S_ACCEPT_SCENARIO_QUEST,encode_accept_scenario_quest(ScenarioQuestInfo(q,SCENARIO_ACTIVE,0,0,0)))
        for q in active)
