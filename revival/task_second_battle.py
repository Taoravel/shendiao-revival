"""Second dream battle Task eligibility, separate from actual AI8027 execution.

The role caller owns transactions and freezes a real combat source snapshot.
This Module checks original growth, committed teaching, current full skills
and private-map authority. It does not enable an engine, commit or send.
"""
from dataclasses import asdict,dataclass
import hashlib
import json
from types import MappingProxyType
from inspect_client import OUT
from tasks import _plain
from task_first_skill import FirstSkillRules
from task_first_skill_proof import read_completed_first_skill_proof
from task_battle import (TaskBattleResources,TaskBattleTicket,open_task_battle_dialogue,
    admit_task_battle_transaction)
from battle_owner import Participant
from task_persistence import load_task_state
from task_newbie_chapter import read_newbie_chapter
from world_story_instances import StoryInstanceIntent,load_story_instance_transaction
from world_transfer_storage import load_map_instance_transaction
from world_owner import Location
from world_npcs import NpcInteraction


SECOND_DREAM_TASK_IDS=frozenset((100190,100290,100390,100490,100590,100690,100790,100890,100990,103290))
POLICY_SHA256='7bbef4665a11366718fee6c2d465902286fa0b7f7adec1e138fac84f2e65ba59'


def _hash(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


@dataclass(frozen=True)
class SecondBattleRules:
    fingerprint:str
    definitions:object
    route_tasks:object
    first_skills:FirstSkillRules
    battles:TaskBattleResources


@dataclass(frozen=True)
class SecondBattleTicket:
    battle_ticket:TaskBattleTicket
    chapter_id:str
    map_generation:str
    rules_fingerprint:str
    teaching_fingerprint:str
    skills_fingerprint:str


@dataclass(frozen=True)
class SecondBattleMenu:
    ticket:SecondBattleTicket
    messages:tuple
    skills:object


def load_second_battle_rules(resources,first_skills,battles,placements,*,path=OUT/'design/task-pve-ai8027-v1.json'):
    """Startup only. An explicit disabled registry still enables no battles.

    The caller selects a registry supplied by its approved actual engine.
    AI8001 retains its own immutable registry/revision for pending recovery.
    """
    raw=path.read_bytes();policy=json.loads(raw)
    if (hashlib.sha256(raw).hexdigest()!=POLICY_SHA256 or type(first_skills) is not FirstSkillRules
            or len(first_skills.route_tasks)!=43 or type(battles) is not TaskBattleResources
            or not battles.enabled_task_ids<=SECOND_DREAM_TASK_IDS
            or battles.enabled_task_ids and battles.engine_revision!=policy['revision']):
        raise ValueError('Reviewed second-dream policy, original teaching and explicit engine registry required')
    original=tuple(p for p in placements.get(1501,()) if p.npc_id==10908)
    if len(original)!=1 or (original[0].placement_id,original[0].x,original[0].y)!=(10,1049,1559):
        raise ValueError('Original second-dream storyteller placement changed')
    policy_routes={row['battle_task_id']:(row['teaching_task_id'],row['first_battle_task_id'],row['next_task_id'])
        for row in policy['routes']}
    routes={};definitions={};followups={}
    for key,teaching_id in first_skills.route_tasks.items():
        teaching=resources.definitions[teaching_id];edges=tuple(teaching['next_ids'])
        if len(edges)!=1 or edges[0] not in SECOND_DREAM_TASK_IDS:
            raise ValueError('Original teaching-to-second-battle edge changed')
        q=edges[0];task=resources.definitions[q];a=task['attributes']
        if (task['type']!=40 or (task['target']['map_id'],task['target']['npc_id'])!=(1501,10908)
                or tuple(task['incoming_ids'])!=(teaching_id,) or len(task['next_ids'])!=1
                or any(int(a[k])!=v for k,v in (('AIInfoAIID',8027),('AIInfoBattleResult',1),
                    ('ProcessBarTime',0),('ScenarioInfoAnimationID',0),('ExpReward',255),('SMoney',600),
                    ('MoneyReward',0),('PetExpReward',0),('AIInfoDeathPunish',0)))
                or q not in battles.definitions
                or _plain(battles.definitions[q].attributes)!=_plain(task['attributes'])
                or _plain(battles.definitions[q].lists)!=_plain(task['lists'])
                or policy_routes.get(q)!=(teaching_id,teaching['incoming_ids'][0],task['next_ids'][0])):
            raise ValueError('Original second battle or selected registry changed')
        cg=resources.definitions[task['next_ids'][0]]
        if (cg['type']!=10 or (cg['target']['map_id'],cg['target']['npc_id'])!=(1501,10084)
                or int(cg['attributes']['ScenarioInfoAnimationID'])!=10001
                or any(cg['display_rewards'].values()) or cg['display_items']):
            raise ValueError('Original separate CG10001 successor changed')
        routes[key]=q;definitions[q]=task;followups[cg['id']]=cg
    if set(definitions)!=SECOND_DREAM_TASK_IDS:
        raise ValueError('Original43 routes must cover exactly ten second battles')
    fingerprint=_hash((POLICY_SHA256,first_skills.fingerprint,sorted(routes.items()),
        {q:_plain(t) for q,t in definitions.items()},{q:_plain(t) for q,t in followups.items()},
        sorted(battles.enabled_task_ids),battles.engine_revision))
    return SecondBattleRules(fingerprint,MappingProxyType(definitions),MappingProxyType(routes),first_skills,battles)


def _context(db,aid,rid,epoch,resources,rules,q,proof,current,movement_state):
    actor,state=load_task_state(db,aid,rid,epoch)
    chapter=read_newbie_chapter(db,aid,rid,epoch,rules.first_skills.chapter_rules)
    task=rules.definitions.get(q)
    if (chapter is None or chapter.phase!='completed' or task is None
            or _plain(task)!=_plain(resources.definitions.get(q))
            or tuple(sorted(x for x in state.active if 100000<=x<200000))!=(q,)):
        raise ValueError('Second battle requires the current original active creation route')
    origin=chapter.origin;route=origin.route;key=(route.character_id,route.school_id)
    if rules.route_tasks.get(key)!=q:raise ValueError('Second battle differs from original creation route')
    completed=read_completed_first_skill_proof(db,aid,rid,epoch,resources,rules.first_skills,task['incoming_ids'][0])
    bloodmark=rules.first_skills.story_rules.source_tasks[key]
    if bloodmark not in state.completed:
        raise ValueError('Second battle requires the original completed bloodmark')
    if (type(current) is not Location or current.state!='active' or (current.role_id,current.login_epoch)!=(rid,epoch)
            or current.address.map_id!=1501 or completed.source_address!=current.address
            or type(movement_state) is not int or movement_state!=0 or not isinstance(proof,NpcInteraction)
            or (proof.role_id,proof.login_epoch)!=(rid,epoch) or proof.address!=current.address
            or proof.position_version!=current.version or (proof.npc_id,proof.placement_id)!=(10908,10)
            or proof.kind!='npc_interacted' or proof.position_validation!='bounds_version_distance'):
        raise ValueError('Second battle needs fresh original private-map NPC proof and normal state')
    checkpoint=load_map_instance_transaction(db,aid,rid,epoch)
    if checkpoint is None or (checkpoint.address,checkpoint.position,checkpoint.version)!=(
            current.address,current.position,current.version):
        raise ValueError('Second battle requires its exact adopted durable checkpoint')
    canonical=StoryInstanceIntent(origin.chapter_id,origin.creation_id,origin.policy,origin.route_fingerprint,bloodmark)
    load_story_instance_transaction(db,aid,rid,epoch,canonical,rules.first_skills.story_rules,expected_address=current.address)
    return completed


def _map_generation(value):
    if type(value) is not str or not 1<=len(value)<=128:raise ValueError('Current map projection generation required')


def open_second_battle_transaction(db,aid,rid,epoch,resources,rules,q,proof,current,*,
        generation,map_generation,now_ms,deadline_ms,movement_state):
    """Read-only original menu plus exact current full skills for the role host.

    Caller has sent this task's active0 bean. MapOwner supplies a fresh proof;
    the returned ticket is revoked on movement/menu/battle/transfer/disconnect.
    """
    _map_generation(map_generation)
    completed=_context(db,aid,rid,epoch,resources,rules,q,proof,current,movement_state)
    if db.execute("SELECT 1 FROM task_battle_admissions WHERE role_id=? AND phase='admitted'",(rid,)).fetchone():
        raise ValueError('A task battle is already admitted')
    result=open_task_battle_dialogue(db,aid,rid,epoch,resources,rules.battles,q,proof,current,
        generation=generation,now_ms=now_ms,deadline_ms=deadline_ms)
    ticket=SecondBattleTicket(result.ticket,completed.chapter_id,map_generation,rules.fingerprint,
        completed.fingerprint,_hash(asdict(completed.skills)))
    return SecondBattleMenu(ticket,result.messages,completed.skills)


def admit_second_battle_transaction(db,aid,rid,epoch,resources,rules,ticket,request,proof,current,participant,battle_id,*,
        generation,map_generation,now_ms,movement_state):
    """Recheck growth/map/skill versions, then use the original durable admission.

    Caller binds this WHOLE wrapper ticket and full combat sources in its new
    durable battle record in the SAME transaction. Generic admission retains
    its existing schema; it does not store the wrapper teaching/skills hashes.
    Only after commit may the host launch its approved real AI8027 engine.
    An admitted retry is acknowledged here; terminal recovery uses the original
    admission's recipe/registry and must not reopen or relabel that battle.
    """
    _map_generation(map_generation)
    if (type(ticket) is not SecondBattleTicket or type(ticket.battle_ticket) is not TaskBattleTicket
            or ticket.rules_fingerprint!=rules.fingerprint or ticket.map_generation!=map_generation
            or not isinstance(participant,Participant) or participant.authorized_skills!=(100008,)):
        raise ValueError('Second battle needs unchanged ticket and only implemented learned100008 capability')
    frozen=ticket.battle_ticket
    completed=_context(db,aid,rid,epoch,resources,rules,frozen.task_id,proof,current,movement_state)
    if (completed.chapter_id!=ticket.chapter_id or completed.fingerprint!=ticket.teaching_fingerprint
            or _hash(asdict(completed.skills))!=ticket.skills_fingerprint or proof.entity_key!=frozen.entity_key):
        raise ValueError('Second battle chapter, committed teaching, skills or fresh NPC entity changed')
    return admit_task_battle_transaction(db,aid,rid,epoch,resources,rules.battles,frozen,request,current,
        participant,battle_id,generation=generation,now_ms=now_ms)
