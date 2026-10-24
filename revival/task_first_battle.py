"""First dream battle eligibility, not an enemy engine or shared dispatcher.

The role caller supplies an adopted full checkpoint and fresh map proof in its
transaction. This Module joins original chapter/private identity to the generic
TaskBattle admission; it never enables a running server, sends or commits.
"""
from dataclasses import dataclass
import hashlib
import json
from types import MappingProxyType
from inspect_client import OUT
from tasks import _plain
from task_battle import (TaskBattleResources,TaskBattleTicket,open_task_battle_dialogue,
    admit_task_battle_transaction)
from task_persistence import load_task_state
from task_newbie_chapter import NewbieChapterRules,read_newbie_chapter
from world_story_instances import StoryInstanceRules,StoryInstanceIntent,load_story_instance_transaction
from world_transfer_storage import load_map_instance_transaction
from world_owner import Location
from world_npcs import NpcInteraction


FIRST_DREAM_TASK_IDS=frozenset((100107,100205,100305,100405,100505,100605,100705,100805,100905,103207))
POLICY_SHA256='2cbbe2cafe3151e49f21a4ec35dab0dd9d4aa9dca82b4b28016dfcb3c13a3c56'


def _hash(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


@dataclass(frozen=True)
class FirstBattleRules:
    fingerprint:str
    definitions:object
    route_tasks:object
    chapter_rules:object
    story_rules:object
    battles:object


@dataclass(frozen=True)
class FirstBattleTicket:
    battle_ticket:TaskBattleTicket
    chapter_id:str
    map_generation:str
    rules_fingerprint:str


@dataclass(frozen=True)
class FirstBattleMenu:
    ticket:FirstBattleTicket
    messages:tuple


def load_first_battle_rules(resources,chapter_rules,story_rules,battles,placements,*,
        path=OUT/'design/task-pve-ai8001-v1.json'):
    """Startup only. Adopt root's exact policy; keep caller capability selection.

    An empty generic registry remains disabled. The caller must obtain an
    enabled registry/revision from its actual approved dedicated engine.
    """
    raw=path.read_bytes();policy=json.loads(raw)
    if (hashlib.sha256(raw).hexdigest()!=POLICY_SHA256
            or not isinstance(chapter_rules,NewbieChapterRules) or len(chapter_rules.routes)!=43
            or not isinstance(story_rules,StoryInstanceRules) or story_rules.chapter_rules!=chapter_rules
            or type(battles) is not TaskBattleResources
            or not battles.enabled_task_ids<=FIRST_DREAM_TASK_IDS
            or battles.enabled_task_ids and battles.engine_revision!=policy['revision']):
        raise ValueError('Reviewed first-dream policy, chapter, directory and actual engine capability required')
    original=tuple(p for p in placements.get(1501,()) if p.npc_id==10908)
    if len(original)!=1 or (original[0].placement_id,original[0].x,original[0].y)!=(10,1049,1559):
        raise ValueError('Original first-dream NPC placement changed')
    routes={};definitions={}
    for key in chapter_rules.routes:
        bloodmark=resources.definitions[story_rules.source_tasks[key]]
        edges=tuple(bloodmark['next_ids'])
        if len(edges)!=1 or edges[0] not in FIRST_DREAM_TASK_IDS:
            raise ValueError('Original bloodmark-to-first-battle edge changed')
        q=edges[0];task=resources.definitions[q];a=task['attributes']
        if (task['type']!=40 or (task['target']['map_id'],task['target']['npc_id'])!=(1501,10908)
                or tuple(task['incoming_ids'])!=(bloodmark['id'],)
                or any(int(a[k])!=v for k,v in (('AIInfoAIID',8001),('AIInfoBattleResult',1),
                    ('ProcessBarTime',0),('ScenarioInfoAnimationID',10019),('ExpReward',120),
                    ('SMoney',400),('PetExpReward',0))) or len(task['next_ids'])!=1
                or q not in battles.definitions
                or _plain(battles.definitions[q].attributes)!=_plain(task['attributes'])
                or _plain(battles.definitions[q].lists)!=_plain(task['lists'])):
            raise ValueError('Original first battle or selected generic registry changed')
        routes[key]=q;definitions[q]=task
    if set(definitions)!=FIRST_DREAM_TASK_IDS:
        raise ValueError('Original43 routes must cover exactly ten first battles')
    fingerprint=_hash((POLICY_SHA256,sorted(routes.items()),{q:_plain(t) for q,t in definitions.items()},
        chapter_rules.revision,story_rules.revision,sorted(battles.enabled_task_ids),battles.engine_revision))
    return FirstBattleRules(fingerprint,MappingProxyType(definitions),MappingProxyType(routes),
        chapter_rules,story_rules,battles)


def _context(db,aid,rid,epoch,resources,rules,q,proof,current,movement_state):
    actor,state=load_task_state(db,aid,rid,epoch)
    chapter=read_newbie_chapter(db,aid,rid,epoch,rules.chapter_rules)
    task=rules.definitions.get(q)
    if (chapter is None or chapter.phase!='completed' or task is None
            or _plain(task)!=_plain(resources.definitions.get(q))
            or tuple(sorted(x for x in state.active if 100000<=x<200000))!=(q,)):
        raise ValueError('First battle requires the current original active creation route')
    origin=chapter.origin;route=origin.route;key=(route.character_id,route.school_id)
    school=db.execute('SELECT school FROM roles WHERE id=?',(rid,)).fetchone()[0]
    bloodmark=rules.story_rules.source_tasks[key]
    if (rules.route_tasks.get(key)!=q or school!=route.school_id
            or resources.shape_to_role_config.get(actor.shape)!=route.character_id
            or route.intro_task_id not in state.completed or bloodmark not in state.completed):
        raise ValueError('First battle route, original completed intro or bloodmark differs')
    if (type(current) is not Location or current.state!='active'
            or (current.role_id,current.login_epoch)!=(rid,epoch) or current.address.map_id!=1501
            or type(movement_state) is not int or movement_state!=0
            or not isinstance(proof,NpcInteraction) or (proof.role_id,proof.login_epoch)!=(rid,epoch)
            or proof.address!=current.address or proof.position_version!=current.version
            or (proof.npc_id,proof.placement_id)!=(10908,10)
            or proof.kind!='npc_interacted' or proof.position_validation!='bounds_version_distance'):
        raise ValueError('Current original first-battle map/NPC proof and normal state required')
    checkpoint=load_map_instance_transaction(db,aid,rid,epoch)
    if checkpoint is None or (checkpoint.address,checkpoint.position,checkpoint.version)!=(
            current.address,current.position,current.version):
        raise ValueError('First battle requires its exact adopted durable checkpoint')
    canonical=StoryInstanceIntent(origin.chapter_id,origin.creation_id,origin.policy,origin.route_fingerprint,bloodmark)
    load_story_instance_transaction(db,aid,rid,epoch,canonical,rules.story_rules,expected_address=current.address)
    return chapter


def _map_generation(value):
    if type(value) is not str or not 1<=len(value)<=128:
        raise ValueError('Current map projection generation required')


def open_first_battle_transaction(db,aid,rid,epoch,resources,rules,q,proof,current,*,
        generation,map_generation,now_ms,deadline_ms,movement_state):
    """Read-only original menu. Caller already sent the correct active0 bean."""
    _map_generation(map_generation)
    chapter=_context(db,aid,rid,epoch,resources,rules,q,proof,current,movement_state)
    if db.execute("SELECT 1 FROM task_battle_admissions WHERE role_id=? AND phase='admitted'",(rid,)).fetchone():
        raise ValueError('A task battle is already admitted')
    result=open_task_battle_dialogue(db,aid,rid,epoch,resources,rules.battles,q,proof,current,
        generation=generation,now_ms=now_ms,deadline_ms=deadline_ms)
    return FirstBattleMenu(FirstBattleTicket(result.ticket,chapter.origin.chapter_id,map_generation,
        rules.fingerprint),result.messages)


def admit_first_battle_transaction(db,aid,rid,epoch,resources,rules,ticket,request,proof,current,participant,battle_id,*,
        generation,map_generation,now_ms,movement_state):
    """Fresh map proof + frozen ticket -> durable admission, never engine launch.

    Host freezes conflicting gameplay in its role mailbox and creates the real
    dedicated battle only after the outer transaction commits. Accepted/paid
    battles are recovered through the generic terminal/ack Interfaces.
    """
    _map_generation(map_generation)
    if (type(ticket) is not FirstBattleTicket or type(ticket.battle_ticket) is not TaskBattleTicket
            or ticket.rules_fingerprint!=rules.fingerprint or ticket.map_generation!=map_generation):
        raise ValueError('First battle ticket policy or map projection changed')
    frozen=ticket.battle_ticket
    chapter=_context(db,aid,rid,epoch,resources,rules,frozen.task_id,proof,current,movement_state)
    if chapter.origin.chapter_id!=ticket.chapter_id or proof.entity_key!=frozen.entity_key:
        raise ValueError('First battle chapter or fresh NPC entity changed')
    return admit_task_battle_transaction(db,aid,rid,epoch,resources,rules.battles,frozen,request,current,
        participant,battle_id,generation=generation,now_ms=now_ms)
