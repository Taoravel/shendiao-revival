"""Original dream-return dialogue -> raw intent, without transfer authority.

No task activation/completion, reward, coordinate conversion, world writes,
DDL or sends. A separately approved settlement policy must consume an intent.
Only an already-active original task in the adopted private directory is read.
"""
from dataclasses import dataclass,field
import hashlib
import json
from types import MappingProxyType
from uuid import uuid4

from tasks import _plain
from task_domain import PLAIN_DIALOGUE_BLOCKERS,PROLOGUE_PUZZLE_IDS,supports_plain_dialogue
from task_newbie_chapter import NewbieChapterRules,read_newbie_chapter
from task_persistence import load_task_state
from task_protocol import (C_COMMIT_SCENARIO_QUEST,ScenarioQuestInfo,S_ACCEPT_SCENARIO_QUEST,
    S_REFRESH_SCENARIO_QUEST_STATE,SCENARIO_ACTIVE,SCENARIO_READY,
    encode_accept_scenario_quest,encode_scenario_state)
from task_dialog_protocol import S_VISIT_NPC,encode_visit_npc
from task_session import TaskIntent
from world_owner import Location
from world_npcs import NpcInteraction
from world_story_instances import StoryInstanceRules,StoryInstanceIntent,load_story_instance_transaction
from world_transfer_storage import load_map_instance_transaction


FIRST_RETURN_IDS=frozenset((100111,100210,100310,100410,100510,100610,100710,100810,100910,103211))
SECOND_RETURN_IDS=frozenset((100121,100220,100320,100420,100520,100620,100720,100820,100920,103221))
RETURN_IDS=FIRST_RETURN_IDS|SECOND_RETURN_IDS
SOURCES={10085:(2,2426,640),10140:(6,5464,1993)}


def _hash(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


@dataclass(frozen=True)
class DreamReturnResources:
    chapter_rules:object
    story_rules:object
    definitions:object
    route_tasks:object
    fingerprint:str


def load_return_dialogue_resources(resources,chapter_rules,story_rules,placements):
    """Startup only: exact20 raw nodes, original43 paths and two real NPCs.

    This resource snapshot is not a gameplay policy or a generic type10 gate.
    In particular it chooses neither RewardMap units nor a transfer timeout.
    """
    if (not isinstance(chapter_rules,NewbieChapterRules) or len(chapter_rules.routes)!=43
            or not isinstance(story_rules,StoryInstanceRules) or story_rules.chapter_rules!=chapter_rules):
        raise ValueError('Original chapter and currently approved story-directory rules required')
    definitions={}
    for q in RETURN_IDS:
        task=resources.definitions.get(q)
        if task is None:raise ValueError('Original dream-return task missing')
        first=q in FIRST_RETURN_IDS;npc=10085 if first else 10140
        expected_jump=(3,1006,170,70) if first else (3,1006,335,144)
        expected_speakers=(10085,1,10085,10085) if first else (10140,1,10140,1,10140)
        a=task['attributes'];edges=tuple(task['next_ids']);incoming=tuple(task['incoming_ids'])
        if (task['type']!=10 or (task['target']['map_id'],task['target']['npc_id'])!=(1501,npc)
                or tuple(int(a.get(k,0)) for k in ('RewardMapJumpType','RewardMapID','RewardMapXPos','RewardMapYPos'))!=expected_jump
                or any(int(a.get(k,0)) for k in PLAIN_DIALOGUE_BLOCKERS if k!='RewardMapJumpType')
                or tuple(line['speaker'] for line in task['dialogue']['start'])!=expected_speakers
                or task['dialogue']['finish'] or task['text']['note']
                or a.get('ScenarioInfoBranchNote') or task['lists'].get('ScenarioInfoBranchOptionList')
                or task['request_mission_ids'] or task['role_config_ids'] or task['display_items']
                or len(edges)!=1 or len(incoming)!=1
                or task['display_rewards']!={'ExpReward':125 if first else 450,'MoneyReward':0,
                    'PetExpReward':0 if first else 450,'ShengWang':0,'SMoney':0}):
            raise ValueError('Original dream-return mechanism or reward changed')
        before=resources.definitions[incoming[0]];after=resources.definitions[edges[0]]
        if (tuple(before['next_ids'])!=(q,) or not supports_plain_dialogue(after)
                or after['target']['map_id']!=1006
                or first and (before['type']!=40 or int(before['attributes'].get('AIInfoAIID',0))!=8002)
                or not first and before['id'] not in PROLOGUE_PUZZLE_IDS):
            raise ValueError('Original dream-return predecessor/successor changed')
        definitions[q]=task
    for npc,expected in SOURCES.items():
        actual=tuple(p for p in placements.get(1501,()) if p.npc_id==npc)
        if len(actual)!=1 or (actual[0].placement_id,actual[0].x,actual[0].y)!=expected:
            raise ValueError('Original dream-return NPC placement changed')
    route_tasks={}
    for key,route in chapter_rules.routes.items():
        q=route.successor_task_id;seen=set();found=[]
        while len(found)<2:
            if q in seen or q not in resources.definitions or len(seen)>=64:
                raise ValueError('Original route does not reach both dream returns')
            seen.add(q)
            if q in definitions:found.append(q)
            edges=tuple(resources.definitions[q]['next_ids'])
            if len(edges)!=1:raise ValueError('Ambiguous original dream-return path')
            q=edges[0]
        if found[0] not in FIRST_RETURN_IDS or found[1] not in SECOND_RETURN_IDS:
            raise ValueError('Original dream-return order changed')
        route_tasks[key]=tuple(found)
    if {q for pair in route_tasks.values() for q in pair}!=RETURN_IDS:
        raise ValueError('Original43 routes do not cover exactly20 dream returns')
    fingerprint=_hash(({q:_plain(t) for q,t in definitions.items()},sorted(route_tasks.items()),
        chapter_rules.revision,story_rules.revision,SOURCES))
    return DreamReturnResources(chapter_rules,story_rules,MappingProxyType(definitions),
        MappingProxyType(route_tasks),fingerprint)


@dataclass(frozen=True)
class ReturnDialogueTicket:
    task_id:int
    chapter_id:str
    directory_intent:StoryInstanceIntent
    location:Location
    generation:int
    map_generation:str
    task_revision:int
    entity_key:int
    opened_ms:int
    deadline_ms:int
    request_id:str
    fingerprint:str


@dataclass(frozen=True)
class ReturnDialogue:
    ticket:ReturnDialogueTicket
    messages:tuple


@dataclass(frozen=True)
class RawDreamReturnIntent:
    ticket:ReturnDialogueTicket
    original_jump:tuple
    successor_id:int
    coordinate_space:str=field(default='original_reward_fields_unresolved',init=False)
    settlement_authorized:bool=field(default=False,init=False)


def _scope(db,account_id,role_id,epoch,resources,returns,task_id):
    chapter=read_newbie_chapter(db,account_id,role_id,epoch,returns.chapter_rules)
    actor,state=load_task_state(db,account_id,role_id,epoch)
    task=returns.definitions.get(task_id)
    if (chapter is None or chapter.phase!='completed' or task is None
            or _plain(task)!=_plain(resources.definitions.get(task_id))):
        raise ValueError('Dream return requires its original completed creation chapter')
    route=chapter.origin.route
    school=db.execute('SELECT school FROM roles WHERE id=?',(role_id,)).fetchone()[0]
    if (task_id not in returns.route_tasks.get((route.character_id,route.school_id),())
            or school!=route.school_id or resources.shape_to_role_config.get(actor.shape)!=route.character_id
            or route.intro_task_id not in state.completed or task_id not in state.active
            or task['incoming_ids'][0] not in state.completed):
        raise ValueError('Dream return differs from current route or existing task/predecessor')
    return state,task,chapter


def _context(db,account_id,role_id,epoch,returns,task,chapter,proof,current):
    npc=task['target']['npc_id'];placement=SOURCES[npc][0]
    if (not isinstance(current,Location) or not isinstance(proof,NpcInteraction)
            or (current.role_id,current.login_epoch)!=(role_id,epoch) or current.state!='active'
            or (proof.role_id,proof.login_epoch)!=(role_id,epoch)
            or proof.address!=current.address or proof.position_version!=current.version
            or (current.address.map_id,proof.npc_id,proof.placement_id)!=(1501,npc,placement)
            or proof.kind!='npc_interacted' or proof.position_validation!='bounds_version_distance'
            or type(proof.entity_key) is not int or not 0<proof.entity_key<2**63
            or type(proof.source_id) is not str or not 1<=len(proof.source_id)<=160):
        raise ValueError('Dream return requires its current actual map-owned NPC proof')
    origin=chapter.origin;route=origin.route
    canonical=StoryInstanceIntent(origin.chapter_id,origin.creation_id,origin.policy,origin.route_fingerprint,
        returns.story_rules.source_tasks[(route.character_id,route.school_id)])
    load_story_instance_transaction(db,account_id,role_id,epoch,canonical,returns.story_rules,
        expected_address=current.address)
    bound=load_map_instance_transaction(db,account_id,role_id,epoch)
    if bound is None or bound.address!=current.address:
        raise ValueError('Dream-return private source has not been adopted')
    return canonical


def _clock(generation,map_generation,now_ms):
    if (type(generation) is not int or generation<=0 or type(now_ms) is not int or not 0<=now_ms<2**63
            or type(map_generation) is not str or not 1<=len(map_generation)<=128):
        raise ValueError('Trusted current connection/map generations and server clock required')


def open_return_dialogue_transaction(db,account_id,role_id,epoch,resources,returns,task_id,proof,current,*,
                                    generation,map_generation,now_ms,deadline_ms):
    """Read existing task -> original Start menu; caller supplies NPC deadline.

    Caller keeps the map generation pinned, publishes after its read transaction
    and revokes the ticket on observed movement/menu/battle/scene/lease changes.
    No new default expiry or permitted settlement is designed here.
    """
    _clock(generation,map_generation,now_ms)
    if type(deadline_ms) is not int or not now_ms<deadline_ms<2**63:
        raise ValueError('Explicit current NPC interaction deadline required')
    state,task,chapter=_scope(db,account_id,role_id,epoch,resources,returns,task_id)
    directory=_context(db,account_id,role_id,epoch,returns,task,chapter,proof,current)
    ticket=ReturnDialogueTicket(task_id,chapter.origin.chapter_id,directory,current,generation,map_generation,
        state.revision,proof.entity_key,now_ms,deadline_ms,f'dream-return:{role_id}:{task_id}:{uuid4().hex}',
        returns.fingerprint)
    return ReturnDialogue(ticket,((S_ACCEPT_SCENARIO_QUEST,encode_accept_scenario_quest(
        ScenarioQuestInfo(task_id,SCENARIO_READY,0,0,proof.entity_key))),
        (S_REFRESH_SCENARIO_QUEST_STATE,encode_scenario_state(task_id,SCENARIO_READY)),
        (S_VISIT_NPC,encode_visit_npc(proof.entity_key,(),(task_id,)))))


def inspect_return_commit_transaction(db,account_id,role_id,epoch,resources,returns,ticket,command,proof,current,*,
                                     generation,map_generation,now_ms):
    """Original real-key CCommit -> immutable raw intent; NEVER TaskEvidence.

    This proves only current server-scoped dialogue intent. It neither proves
    reading nor authorizes a world handoff, reward or task completion.
    """
    _clock(generation,map_generation,now_ms)
    if not isinstance(ticket,ReturnDialogueTicket) or not isinstance(command,TaskIntent):
        raise ValueError('Current server-issued dream-return ticket required')
    state,task,chapter=_scope(db,account_id,role_id,epoch,resources,returns,ticket.task_id)
    directory=_context(db,account_id,role_id,epoch,returns,task,chapter,proof,current)
    if (ticket.location!=current or ticket.directory_intent!=directory or ticket.chapter_id!=chapter.origin.chapter_id
            or ticket.generation!=generation or ticket.map_generation!=map_generation
            or ticket.task_revision!=state.revision or ticket.fingerprint!=returns.fingerprint
            or proof.entity_key!=ticket.entity_key or not ticket.opened_ms<=now_ms<ticket.deadline_ms
            or command.kind!=C_COMMIT_SCENARIO_QUEST or command.task_id!=ticket.task_id
            or command.npc_key!=ticket.entity_key or type(command.opaque) is not int or command.opaque!=0):
        raise ValueError('Wrong or stale original dream-return commit')
    a=task['attributes']
    return RawDreamReturnIntent(ticket,tuple(int(a[k]) for k in
        ('RewardMapJumpType','RewardMapID','RewardMapXPos','RewardMapYPos')),task['next_ids'][0])


def resume_return_messages(db,account_id,role_id,epoch,resources,returns,*,already_projected=()):
    """Only restore an existing current-route task bean; no ticket or grant."""
    _,state=load_task_state(db,account_id,role_id,epoch)
    active=state.active&RETURN_IDS
    if len(active)>1:raise ValueError('Conflicting active dream returns require recovery')
    if not active:return ()
    task_id=next(iter(active));_scope(db,account_id,role_id,epoch,resources,returns,task_id)
    if task_id in already_projected:return ()
    return ((S_ACCEPT_SCENARIO_QUEST,encode_accept_scenario_quest(
        ScenarioQuestInfo(task_id,SCENARIO_ACTIVE,0,0,0))),)
