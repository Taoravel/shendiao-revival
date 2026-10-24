"""Original portrait puzzle: authorized menu and one atomic client claim.

The original wire carries no board or move proof. This Module explicitly
accepts an authorized client assertion; it never claims to verify a solution.
Policy, resources, current map proof and the leased transaction are injected.
No default policy, shared routing, network, world mutation or combat lives here.
"""
from dataclasses import asdict,dataclass,replace
import hashlib
import json
from types import MappingProxyType
from uuid import uuid4
from inspect_client import OUT
from task_domain import TaskDomain,TaskEvidence,PROLOGUE_PUZZLE_IDS,supports_prologue_puzzle
from task_persistence import load_task_state,apply_task_plan
from task_newbie_chapter import NewbieChapterRules,read_newbie_chapter
from task_growth_resources import current_task_resource_profile
from task_workflow import complete_task_transaction,replay_completed_task_transaction,completion_messages
from task_rewards import update_reward_delivery
from task_protocol import (C_COMMIT_SCENARIO_QUEST,S_ACCEPT_SCENARIO_QUEST,
    ScenarioQuestInfo,SCENARIO_ACTIVE,encode_accept_scenario_quest)
from task_dialog_protocol import S_VISIT_NPC,encode_visit_npc
from task_session import TaskIntent
from tasks import _plain
from world_owner import Location
from world_npcs import NpcInteraction
from world_story_instances import StoryInstanceIntent,StoryInstanceRules,load_story_instance_transaction
from world_transfer_storage import load_map_instance_transaction


def _json(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'))


def _hash(value):
    return hashlib.sha256(_json(value).encode()).hexdigest()


@dataclass(frozen=True)
class PuzzlePolicy:
    revision:str
    minimum_elapsed_ms:int
    timeout_ms:int
    admission:str='authorized_client_assertion'
    source_fingerprint:str=''


def load_puzzle_policy(path=OUT/'design/newbie-puzzle-v1.json'):
    """Startup only: freeze the single published central policy, never fixture values."""
    policy=json.loads(path.read_text(encoding='utf-8'))
    if (type(policy) is not dict or policy.get('revision')!='2026-10-23.newbie-puzzle.1'
            or type(policy.get('tasks')) is not list or len(policy['tasks'])!=10
            or any(type(q) is not int for q in policy['tasks']) or set(policy['tasks'])!=PROLOGUE_PUZZLE_IDS
            or policy.get('source')!={'map_id':1501,'npc_id':11106,'placement_id':16,'x':5870,'y':1541}
            or type(policy.get('service_id')) is not int or policy['service_id']!=553
            or policy.get('admission')!='authorized_client_assertion'
            or type(policy.get('minimum_elapsed_ms')) is not int or policy['minimum_elapsed_ms']!=0
            or type(policy.get('timeout_ms')) is not int or policy['timeout_ms']!=300000
            or policy.get('server_verified_board') is not False
            or any(type(policy.get(k)) is not str or not policy[k] for k in
                ('provenance','scope','time_provenance','request','authorization','invalidation',
                 'recovery','reward','transaction','replay','successor','activation'))):
        raise ValueError('Published portrait-puzzle policy requires implementation review')
    return PuzzlePolicy(policy['revision'],policy['minimum_elapsed_ms'],policy['timeout_ms'],
        policy['admission'],_hash(policy))


@dataclass(frozen=True)
class PuzzleResources:
    policy:PuzzlePolicy
    fingerprint:str
    definitions:object
    chapter_rules:object
    story_rules:object
    route_tasks:object


def load_puzzle_resources(resources,chapter_rules,story_rules,placements,*,policy):
    """Startup only. Caller supplies policy; no production defaults are inferred.

    Shared callers must inject a published planner policy. A disposable fixture
    can supply its explicitly unapproved policy to exercise this isolated Module.
    Merely loading these resources does not enable TaskChain or any wire route.
    """
    if (type(policy) is not PuzzlePolicy or type(policy.revision) is not str
            or not 1<=len(policy.revision)<=128 or policy.admission!='authorized_client_assertion'
            or type(policy.source_fingerprint) is not str
            or policy.source_fingerprint and (len(policy.source_fingerprint)!=64
                or any(c not in '0123456789abcdef' for c in policy.source_fingerprint))
            or type(policy.minimum_elapsed_ms) is not int or not 0<=policy.minimum_elapsed_ms<=60000
            or type(policy.timeout_ms) is not int or not policy.minimum_elapsed_ms<policy.timeout_ms<=1800000
            or not isinstance(chapter_rules,NewbieChapterRules) or len(chapter_rules.routes)!=43
            or not isinstance(story_rules,StoryInstanceRules) or story_rules.chapter_rules!=chapter_rules):
        raise ValueError('Explicit portrait-puzzle admission policy and original chapter/directory rules required')
    definitions={q:resources.definitions[q] for q in PROLOGUE_PUZZLE_IDS
        if q in resources.definitions and supports_prologue_puzzle(resources.definitions[q])}
    if set(definitions)!=PROLOGUE_PUZZLE_IDS:
        raise ValueError('Original ten portrait-puzzle definitions changed')
    npcs=tuple(p for p in placements.get(1501,()) if p.npc_id==11106)
    if len(npcs)!=1 or (npcs[0].placement_id,npcs[0].x,npcs[0].y)!=(16,5870,1541):
        raise ValueError('Original portrait NPC placement changed')
    route_tasks={}
    for key,route in chapter_rules.routes.items():
        current=route.successor_task_id;seen=set()
        while current not in definitions:
            if current not in resources.definitions or current in seen or len(seen)>=64:
                raise ValueError('Original creation path does not reach the portrait puzzle')
            seen.add(current);edges=tuple(resources.definitions[current]['next_ids'])
            if len(edges)!=1:raise ValueError('Ambiguous original path to portrait puzzle')
            current=edges[0]
        route_tasks[key]=current
        task=definitions[current];before=resources.definitions[task['incoming_ids'][0]]
        after=resources.definitions[task['next_ids'][0]]
        if (before['type']!=10 or (before['target']['map_id'],before['target']['npc_id'])!=(1501,10139)
                or tuple(before['next_ids'])!=(current,) or after['type']!=10
                or (after['target']['map_id'],after['target']['npc_id'])!=(1501,10140)
                or tuple(int(after['attributes'][k]) for k in
                    ('RewardMapJumpType','RewardMapID','RewardMapXPos','RewardMapYPos'))!=(3,1006,335,144)):
            raise ValueError('Original portrait-puzzle predecessor/successor changed')
    if set(route_tasks.values())!=PROLOGUE_PUZZLE_IDS:
        raise ValueError('Original43 routes do not cover the exact ten portrait puzzles')
    fingerprint=_hash((asdict(policy),{q:_plain(t) for q,t in definitions.items()},
        [(key,q) for key,q in sorted(route_tasks.items())],chapter_rules.revision,story_rules.revision))
    return PuzzleResources(policy,fingerprint,MappingProxyType(definitions),chapter_rules,
        story_rules,MappingProxyType(route_tasks))


@dataclass(frozen=True)
class PuzzleTicket:
    task_id:int
    chapter_id:str
    directory_intent:StoryInstanceIntent
    source:Location
    task_revision:int
    generation:int
    map_generation:str
    entity_key:int
    opened_ms:int
    earliest_ms:int
    deadline_ms:int
    operation_id:str
    fingerprint:str


@dataclass(frozen=True)
class PuzzleMenu:
    ticket:PuzzleTicket
    messages:tuple


@dataclass(frozen=True)
class PuzzleResult:
    completion:object
    messages:tuple
    replayed:bool


def prepare_puzzle_storage(db):
    """Startup ordinary connection only; all subsequent writes join the caller."""
    db.execute('''CREATE TABLE IF NOT EXISTS task_prologue_puzzles (
        role_id INTEGER NOT NULL REFERENCES roles(id),task_id INTEGER NOT NULL,
        operation_id TEXT UNIQUE NOT NULL,fingerprint TEXT NOT NULL,
        ticket TEXT NOT NULL,source_event TEXT NOT NULL,PRIMARY KEY(role_id,task_id))''')


def _scope(db,account_id,role_id,epoch,resources,puzzles,task_id):
    chapter=read_newbie_chapter(db,account_id,role_id,epoch,puzzles.chapter_rules)
    actor,state=load_task_state(db,account_id,role_id,epoch)
    task=puzzles.definitions.get(task_id)
    if (chapter is None or chapter.phase!='completed' or task is None
            or _plain(task)!=_plain(resources.definitions.get(task_id))):
        raise ValueError('Portrait puzzle requires its original completed creation chapter')
    route=chapter.origin.route
    school=db.execute('SELECT school FROM roles WHERE id=?',(role_id,)).fetchone()[0]
    if (puzzles.route_tasks.get((route.character_id,route.school_id))!=task_id
            or school!=route.school_id or resources.shape_to_role_config.get(actor.shape)!=route.character_id
            or route.intro_task_id not in state.completed or task['incoming_ids'][0] not in state.completed):
        raise ValueError('Portrait puzzle differs from the frozen creation route or predecessor')
    return actor,state,task,chapter


def _directory_intent(chapter,puzzles):
    origin=chapter.origin;route=origin.route
    return StoryInstanceIntent(origin.chapter_id,origin.creation_id,origin.policy,origin.route_fingerprint,
        puzzles.story_rules.source_tasks[(route.character_id,route.school_id)])


def _world(db,account_id,role_id,epoch,chapter,puzzles,location):
    intent=_directory_intent(chapter,puzzles)
    if (not isinstance(location,Location) or (location.role_id,location.login_epoch)!=(role_id,epoch)
            or location.state!='active' or location.address.map_id!=1501):
        raise ValueError('Portrait puzzle requires its current private dream location')
    load_story_instance_transaction(db,account_id,role_id,epoch,intent,puzzles.story_rules,
        expected_address=location.address)
    bound=load_map_instance_transaction(db,account_id,role_id,epoch)
    if bound is None or bound.address!=location.address:
        raise ValueError('Portrait puzzle source instance has not been adopted')
    return intent


def _npc(proof,current,role_id,epoch,*,entity_key=None):
    if (not isinstance(proof,NpcInteraction) or not isinstance(current,Location)
            or (proof.role_id,proof.login_epoch)!=(role_id,epoch)
            or (current.role_id,current.login_epoch)!=(role_id,epoch) or current.state!='active'
            or proof.address!=current.address or proof.position_version!=current.version
            or (current.address.map_id,proof.npc_id,proof.placement_id)!=(1501,11106,16)
            or proof.kind!='npc_interacted' or proof.position_validation!='bounds_version_distance'
            or type(proof.entity_key) is not int or not 0<proof.entity_key<2**63
            or type(proof.source_id) is not str or not 1<=len(proof.source_id)<=160
            or entity_key is not None and proof.entity_key!=entity_key):
        raise ValueError('Portrait puzzle requires a current map-owned NPC11106 proof')


def _activate(db,actor,state,task_id,resources,request_id):
    if task_id in state.active|state.completed:return ()
    for action in ('offer','accept'):
        if action=='offer' and task_id in state.offered:continue
        apply_task_plan(db,actor,TaskDomain(resources).plan(actor,state,action,task_id),request_id+':'+action)
        actor,state=load_task_state(db,actor.account_id,actor.role_id,actor.login_epoch)
    return (task_id,)


def reconcile_puzzle_successor_transaction(db,account_id,role_id,epoch,resources,puzzles,predecessor_id):
    """Explicit isolated policy only; generic TaskChain never enables this family."""
    source=resources.definitions.get(predecessor_id);edges=tuple(source['next_ids']) if source else ()
    if len(edges)!=1 or edges[0] not in puzzles.definitions:
        raise ValueError('No original portrait puzzle follows this task')
    actor,state,_,_=_scope(db,account_id,role_id,epoch,resources,puzzles,edges[0])
    if edges[0] in state.active|state.completed:return ()
    row=db.execute('SELECT payload FROM task_effects WHERE role_id=? AND task_id=?',
        (role_id,predecessor_id)).fetchone()
    effect=json.loads(row[0]) if row else {}
    if tuple(effect.get('next_ids',()))!=edges:
        raise ValueError('Portrait puzzle predecessor lacks its durable original edge')
    started=_activate(db,actor,state,edges[0],resources,f'puzzle-activate:{predecessor_id}:{edges[0]}')
    effect.update(chain_status='activated',chain_reason='explicit_portrait_puzzle_policy',chain_target=edges[0],chain_resolved=True)
    delivered=update_reward_delivery(effect)
    db.execute('UPDATE task_effects SET payload=?,delivered=? WHERE role_id=? AND task_id=?',
        (_json(effect),int(delivered),role_id,predecessor_id))
    return started


def open_puzzle_menu_transaction(db,account_id,role_id,epoch,resources,puzzles,task_id,proof,location,*,generation,map_generation,now_ms):
    """Publish menu553 and one role-owned permit, without completing/granting.

    Owner invalidates it on movement/other menu/battle/map/disconnect/task change.
    A re-login requires a new NPC visit; no former-epoch ticket is restored.
    """
    actor,state,task,chapter=_scope(db,account_id,role_id,epoch,resources,puzzles,task_id)
    _npc(proof,location,role_id,epoch)
    directory_intent=_world(db,account_id,role_id,epoch,chapter,puzzles,location)
    mains=tuple(sorted(q for q in state.active if 100000<=q<200000))
    if (mains!=(task_id,) or type(generation) is not int or generation<=0
            or type(map_generation) is not str or not 1<=len(map_generation)<=128
            or type(now_ms) is not int or not 0<=now_ms<=2**63-1-puzzles.policy.timeout_ms):
        raise ValueError('Portrait menu requires one unambiguous active original main task and current clock')
    ticket=PuzzleTicket(task_id,chapter.origin.chapter_id,directory_intent,location,state.revision,generation,map_generation,
        proof.entity_key,now_ms,now_ms+puzzles.policy.minimum_elapsed_ms,now_ms+puzzles.policy.timeout_ms,
        'puzzle:'+uuid4().hex,puzzles.fingerprint)
    return PuzzleMenu(ticket,((S_ACCEPT_SCENARIO_QUEST,encode_accept_scenario_quest(
        ScenarioQuestInfo(task_id,SCENARIO_ACTIVE,0,0,0))),
        (S_VISIT_NPC,encode_visit_npc(proof.entity_key,(553,),()))))


def _ticket(ticket,puzzles,role_id,epoch,generation,now_ms):
    if (not isinstance(ticket,PuzzleTicket) or not isinstance(ticket.source,Location)
            or (ticket.source.role_id,ticket.source.login_epoch)!=(role_id,epoch)
            or ticket.source.state!='active' or ticket.fingerprint!=puzzles.fingerprint
            or type(generation) is not int or generation<=0 or ticket.generation!=generation
            or type(ticket.map_generation) is not str or not 1<=len(ticket.map_generation)<=128
            or type(now_ms) is not int or not 0<=now_ms<2**63
            or type(ticket.opened_ms) is not int or ticket.opened_ms<0
            or type(ticket.task_revision) is not int or ticket.task_revision<0
            or type(ticket.entity_key) is not int or not 0<ticket.entity_key<2**63
            or ticket.earliest_ms!=ticket.opened_ms+puzzles.policy.minimum_elapsed_ms
            or ticket.deadline_ms!=ticket.opened_ms+puzzles.policy.timeout_ms
            or type(ticket.operation_id) is not str or not 1<=len(ticket.operation_id)<=128):
        raise ValueError('Invalid or stale portrait-puzzle ticket')


def complete_puzzle_transaction(db,account_id,role_id,epoch,resources,puzzles,ticket,command,inventory,*,
        proof,location,generation,map_generation,now_ms,growth_rules=None,attribute_rules=None,currency_rules=None,
        pet_experience_rules=None,resource_rules=None,equipment_rules=None):
    """Accept an authorized client claim, settle once, return logical messages.

    Obtain fresh proof using the ticket's SERVER-owned NPC key before this SQL
    transaction. The wire NPC key is zero and never selects a server entity.
    Encode all outputs before caller commit, publish/consume ticket afterwards.
    """
    _ticket(ticket,puzzles,role_id,epoch,generation,now_ms)
    if (not isinstance(command,TaskIntent) or (command.kind,command.task_id,command.npc_key,command.opaque)
            !=(C_COMMIT_SCENARIO_QUEST,ticket.task_id,0,0)):
        raise ValueError('Portrait puzzle requires its original zero-NPC CCommit')
    actor,state,task,chapter=_scope(db,account_id,role_id,epoch,resources,puzzles,ticket.task_id)
    if ticket.chapter_id!=chapter.origin.chapter_id or ticket.directory_intent!=_directory_intent(chapter,puzzles):
        raise ValueError('Portrait ticket belongs to a different creation chapter')
    load_story_instance_transaction(db,account_id,role_id,epoch,ticket.directory_intent,puzzles.story_rules,
        expected_address=ticket.source.address)
    if (inventory.account_id,inventory.role_id)!=(account_id,role_id):
        raise ValueError('Portrait puzzle inventory owner mismatch')
    inventory.immutable_snapshot_transaction(db,epoch=epoch)
    current_task_resource_profile(db,actor,inventory,resource_rules,equipment_rules)
    encoded=_json(asdict(ticket));fingerprint=_hash((puzzles.fingerprint,encoded))
    source='portrait-claim:'+fingerprint
    expected=(ticket.operation_id,fingerprint,encoded,source)
    old=db.execute('SELECT operation_id,fingerprint,ticket,source_event FROM task_prologue_puzzles '
        'WHERE role_id=? AND task_id=?',(role_id,ticket.task_id)).fetchone()
    reward_rules=(growth_rules,attribute_rules,currency_rules,pet_experience_rules)
    if old is not None:
        if tuple(old)!=expected or ticket.task_id not in state.completed:
            raise ValueError('Conflicting portrait-puzzle claim replay')
        row=db.execute('SELECT payload FROM task_effects WHERE role_id=? AND task_id=?',
            (role_id,ticket.task_id)).fetchone()
        if row is None or json.loads(row[0]).get('source_event')!=source:
            raise ValueError('Portrait claim differs from its durable task evidence')
        done=replay_completed_task_transaction(db,actor,ticket.task_id,resources,inventory,*reward_rules,
            resource_rules=resource_rules,equipment_rules=equipment_rules)
        done=replace(done,suppress_replayed_state=True)
        return PuzzleResult(done,completion_messages(done),True)
    if map_generation!=ticket.map_generation:
        raise ValueError('Portrait-puzzle map projection generation changed')
    _npc(proof,location,role_id,epoch,entity_key=ticket.entity_key)
    _world(db,account_id,role_id,epoch,chapter,puzzles,location)
    if (location!=ticket.source or ticket.task_id not in state.active or state.revision!=ticket.task_revision
            or not ticket.earliest_ms<=now_ms<ticket.deadline_ms
            or tuple(sorted(q for q in state.active if 100000<=q<200000))!=(ticket.task_id,)
            or task['next_ids'][0] in state.active|state.completed):
        raise ValueError('Premature, moved, expired or changed portrait-puzzle claim')
    evidence=TaskEvidence(ticket.task_id,role_id,epoch,'prologue_puzzle_claim_accepted',source,
        map_id=1501,npc_id=11106,reference_id=553)
    plan=TaskDomain(resources).plan(actor,state,'complete',ticket.task_id,evidence=evidence)
    done=complete_task_transaction(db,actor,plan,ticket.operation_id,resources,inventory,*reward_rules,
        resource_rules=resource_rules,equipment_rules=equipment_rules)
    successor=task['next_ids'][0]
    actor,after=load_task_state(db,account_id,role_id,epoch)
    started=_activate(db,actor,after,successor,resources,f'puzzle-next:{ticket.task_id}:{successor}')
    if started:
        done=replace(done,started_tasks=done.started_tasks+started,
            started_infos=done.started_infos+(ScenarioQuestInfo(successor,SCENARIO_ACTIVE,0,0,0),))
    if done.started_tasks!=(successor,):
        raise ValueError('Portrait puzzle must activate only its original successor')
    effect=json.loads(db.execute('SELECT payload FROM task_effects WHERE role_id=? AND task_id=?',
        (role_id,ticket.task_id)).fetchone()[0])
    effect['portrait_claim']={'admission':puzzles.policy.admission,'policy':puzzles.policy.revision,
        'operation_id':ticket.operation_id,'server_verified_board':False}
    effect.update(chain_status='activated',chain_reason='original_portrait_puzzle_successor',
        chain_target=successor,chain_resolved=True)
    delivered=update_reward_delivery(effect)
    db.execute('UPDATE task_effects SET payload=?,delivered=? WHERE role_id=? AND task_id=?',
        (_json(effect),int(delivered),role_id,ticket.task_id))
    db.execute('INSERT INTO task_prologue_puzzles VALUES(?,?,?,?,?,?)',(role_id,ticket.task_id,*expected))
    return PuzzleResult(done,completion_messages(done),False)


def read_completed_puzzle_proof(db,account_id,role_id,epoch,resources,puzzles,task_id):
    """Pure current-lease query of an approved historical portrait claim.

    No settlement, task activation or reward recovery occurs. A historical
    ticket's old lease does not turn it into a new permit or invalidate proof.
    """
    _,state,_,chapter=_scope(db,account_id,role_id,epoch,resources,puzzles,task_id)
    row=db.execute('SELECT operation_id,fingerprint,ticket,source_event FROM task_prologue_puzzles '
        'WHERE role_id=? AND task_id=?',(role_id,task_id)).fetchone()
    if row is None or task_id not in state.completed:
        raise ValueError('Completed portrait puzzle lacks an approved claim receipt')
    operation_id,fingerprint,encoded,source=row
    ticket=json.loads(encoded)
    effect=db.execute('SELECT payload FROM task_effects WHERE role_id=? AND task_id=?',(role_id,task_id)).fetchone()
    payload=json.loads(effect[0]) if effect else {}
    if (fingerprint!=_hash((puzzles.fingerprint,encoded)) or source!='portrait-claim:'+fingerprint
            or ticket.get('task_id')!=task_id or ticket.get('operation_id')!=operation_id
            or ticket.get('chapter_id')!=chapter.origin.chapter_id
            or ticket.get('directory_intent')!=asdict(_directory_intent(chapter,puzzles))
            or ticket.get('source',{}).get('role_id')!=role_id or ticket.get('fingerprint')!=puzzles.fingerprint
            or payload.get('source_event')!=source
            or payload.get('portrait_claim')!={'admission':puzzles.policy.admission,'policy':puzzles.policy.revision,
                'operation_id':operation_id,'server_verified_board':False}):
        raise ValueError('Portrait puzzle receipt/evidence differs from approved source')
    return (operation_id,fingerprint,source)


def resume_puzzle_messages(db,account_id,role_id,epoch,resources,puzzles,*,already_projected=()):
    """Project only existing current-route puzzle/successor beans, never a permit.

    The successor has an unimplemented transfer and would be absent from the
    generic plain-dialogue projection. Restoring its tracker grants no ability
    to finish it, transfer, replay the puzzle or restart a past Finish dialogue.
    """
    chapter=read_newbie_chapter(db,account_id,role_id,epoch,puzzles.chapter_rules)
    if chapter is None or chapter.phase!='completed':return ()
    route=chapter.origin.route
    task_id=puzzles.route_tasks.get((route.character_id,route.school_id))
    if task_id is None:raise ValueError('Unknown original portrait-puzzle chapter')
    actor,state=load_task_state(db,account_id,role_id,epoch)
    if task_id not in state.active|state.completed:return ()
    _scope(db,account_id,role_id,epoch,resources,puzzles,task_id)
    successor=puzzles.definitions[task_id]['next_ids'][0]
    if task_id in state.active and successor in state.active|state.completed:
        raise ValueError('Conflicting portrait-puzzle phases')
    ids=tuple(q for q in (task_id,successor) if q in state.active and q not in already_projected)
    return tuple((S_ACCEPT_SCENARIO_QUEST,encode_accept_scenario_quest(
        ScenarioQuestInfo(q,SCENARIO_ACTIVE,0,0,0))) for q in ids)
