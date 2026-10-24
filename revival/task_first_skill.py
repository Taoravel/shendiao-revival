"""Approved original teaching permit, atomic120XP/skill/unique successor.

No battle execution or shared dispatch. RoleOwner owns one pending ticket and
revokes it on move/menu/transfer/battle/disconnect. Caller encodes all final
messages before committing, then publishes through its connection owner.
"""
from dataclasses import dataclass,asdict,replace
import hashlib
import json
from types import MappingProxyType
from uuid import uuid4
from inspect_client import OUT
from tasks import _plain
from task_domain import TaskDomain,TaskEvidence,PROLOGUE_FIRST_SKILL_IDS,supports_prologue_first_skill
from task_persistence import load_task_state,apply_task_plan
from task_workflow import complete_task_transaction,completion_messages
from task_chains import continue_task_chain
from task_battle import load_task_battle_resources,read_completed_task_battle_proof
from task_newbie_chapter import NewbieChapterRules,read_newbie_chapter
from task_protocol import (ScenarioQuestInfo,S_ACCEPT_SCENARIO_QUEST,S_REFRESH_SCENARIO_QUEST_STATE,
    SCENARIO_READY,SCENARIO_ACTIVE,C_COMMIT_SCENARIO_QUEST,encode_accept_scenario_quest,encode_scenario_state)
from task_dialog_protocol import S_VISIT_NPC,encode_visit_npc,S_REFRESH_USER_EXP,encode_user_experience
from task_session import TaskIntent
from task_growth_resources import current_task_resource_profile
from role_skills import (load_other_skill_rules,read_other_skills,grant_other_skill,other_skill_messages,
    LocalPrologueBaselineRules,LocalPrologueBaselinePermit,enroll_local_prologue_other_skills,
    LOCAL_BASELINE_REVISION,LOCAL_BASELINE_POLICY_SHA,LOCAL_BASELINE_EVIDENCE_SHA)
from role_growth import read_growth
from role_attribute_storage import attribute_snapshot_if_initialized,read_naked_attributes
from role_attribute_protocol import growth_refresh
from progression import read_experience
from task_rewards import plan_task_reward
from world_owner import Location
from world_npcs import NpcInteraction
from world_story_instances import StoryInstanceRules,StoryInstanceIntent,load_story_instance_transaction
from world_transfer_storage import load_map_instance_transaction


def _json(value):return json.dumps(value,sort_keys=True,separators=(',',':'))
def _hash(value):return hashlib.sha256(_json(value).encode()).hexdigest()
def _sha(value):return type(value) is str and len(value)==64 and all(c in '0123456789abcdef' for c in value)


@dataclass(frozen=True)
class FirstSkillRules:
    revision:str
    fingerprint:str
    policy_fingerprint:str
    definitions:object
    route_tasks:object
    chapter_rules:object
    story_rules:object
    skills:object
    battles:object
    minimum_ms:int=1000
    timeout_ms:int=300000


def load_first_skill_rules(resources,chapter_rules,story_rules,placements,*,path=OUT/'design/newbie-first-skill-v1.json'):
    """Startup-only strict adoption of central design and original10/43/3 tables."""
    policy=json.loads(path.read_text(encoding='utf8'))
    required={'revision':'2026-10-24.newbie-first-skill.1','skill_id':100008,'grant_value':1,'fee':0,
        'minimum_elapsed_ms':1000,'deadline_ms':300000,'npc_id':10908,'map_template_id':1501,
        'maximum_other_skills':128,'wire_type':0xc36c3,'snapshot_flag':1}
    if (any(type(policy.get(k)) is not type(v) or policy[k]!=v for k,v in required.items())
            or type(policy.get('task_ids')) is not list or len(policy['task_ids'])!=10
            or any(type(q) is not int for q in policy['task_ids']) or set(policy['task_ids'])!=PROLOGUE_FIRST_SKILL_IDS
            or not isinstance(chapter_rules,NewbieChapterRules) or len(chapter_rules.routes)!=43
            or not isinstance(story_rules,StoryInstanceRules) or story_rules.chapter_rules!=chapter_rules):
        raise ValueError('Approved first-skill policy and original chapter/directory required')
    definitions={q:resources.definitions[q] for q in PROLOGUE_FIRST_SKILL_IDS
        if q in resources.definitions and supports_prologue_first_skill(resources.definitions[q])}
    if set(definitions)!=PROLOGUE_FIRST_SKILL_IDS:raise ValueError('Original first-skill teaching nodes changed')
    source=tuple(p for p in placements.get(1501,()) if p.npc_id==10908)
    if len(source)!=1 or (source[0].placement_id,source[0].x,source[0].y)!=(10,1049,1559):
        raise ValueError('Original teaching NPC placement changed')
    routes={}
    for key,route in chapter_rules.routes.items():
        q=route.successor_task_id;seen=set()
        while q not in definitions:
            if q in seen or q not in resources.definitions or len(seen)>=32:raise ValueError('Original teaching path missing')
            seen.add(q);edges=tuple(resources.definitions[q]['next_ids'])
            if len(edges)!=1:raise ValueError('Ambiguous original teaching path')
            q=edges[0]
        routes[key]=q;t=definitions[q]
        before=resources.definitions[t['incoming_ids'][0]];after=resources.definitions[t['next_ids'][0]]
        if (before['type']!=40 or int(before['attributes'].get('AIInfoAIID',0))!=8001
                or tuple(before['next_ids'])!=(q,) or (before['target']['map_id'],before['target']['npc_id'])!=(1501,10908)
                or after['type']!=40 or tuple(after['incoming_ids'])!=(q,)
                or (after['target']['map_id'],after['target']['npc_id'])!=(1501,10908)):
            raise ValueError('Original teaching battle edges changed')
    if set(routes.values())!=PROLOGUE_FIRST_SKILL_IDS:raise ValueError('43 original routes must cover ten teaching nodes')
    skills=load_other_skill_rules();battles=load_task_battle_resources(resources)
    fingerprint=_hash((policy,{q:_plain(t) for q,t in definitions.items()},sorted(routes.items()),
        chapter_rules.revision,story_rules.revision,skills.fingerprint))
    return FirstSkillRules(policy['revision'],fingerprint,_hash(policy),MappingProxyType(definitions),
        MappingProxyType(routes),chapter_rules,story_rules,skills,battles)


@dataclass(frozen=True)
class FirstSkillTicket:
    task_id:int
    chapter_id:str
    directory_intent:StoryInstanceIntent
    source:Location
    task_revision:int
    skill_revision:int | None
    generation:int
    map_generation:str
    entity_key:int
    opened_ms:int
    earliest_ms:int
    deadline_ms:int
    operation_id:str
    fingerprint:str
    baseline_eligibility:str | None=None


@dataclass(frozen=True)
class FirstSkillMenu:
    ticket:FirstSkillTicket
    messages:tuple


@dataclass(frozen=True)
class FirstSkillResult:
    completion:object
    skills:object
    messages:tuple
    replayed:bool


def prepare_first_skill_storage(db):
    db.execute('''CREATE TABLE IF NOT EXISTS task_first_skills (
        role_id INTEGER NOT NULL REFERENCES roles(id),task_id INTEGER NOT NULL,
        operation_id TEXT UNIQUE NOT NULL,fingerprint TEXT NOT NULL,ticket TEXT NOT NULL,
        predecessor TEXT NOT NULL,source_event TEXT NOT NULL,grant_receipt TEXT NOT NULL,
        PRIMARY KEY(role_id,task_id))''')


def _scope(db,aid,rid,epoch,resources,rules,q):
    actor,state=load_task_state(db,aid,rid,epoch)
    chapter=read_newbie_chapter(db,aid,rid,epoch,rules.chapter_rules)
    task=rules.definitions.get(q)
    if chapter is None or chapter.phase!='completed' or task is None or _plain(task)!=_plain(resources.definitions.get(q)):
        raise ValueError('Original completed creation chapter and teaching task required')
    origin=chapter.origin;route=origin.route
    school=db.execute('SELECT school FROM roles WHERE id=?',(rid,)).fetchone()[0]
    if (rules.route_tasks.get((route.character_id,route.school_id))!=q or school!=route.school_id
            or resources.shape_to_role_config.get(actor.shape)!=route.character_id or route.intro_task_id not in state.completed):
        raise ValueError('Teaching differs from the original creation route')
    prior=read_completed_task_battle_proof(db,aid,rid,epoch,resources,rules.battles,task['incoming_ids'][0])
    canonical=StoryInstanceIntent(origin.chapter_id,origin.creation_id,origin.policy,origin.route_fingerprint,
        rules.story_rules.source_tasks[(route.character_id,route.school_id)])
    return actor,state,task,chapter,prior,canonical


def _world(db,aid,rid,epoch,rules,canonical,proof,current,*,entity_key=None):
    if (not isinstance(current,Location) or current.state!='active' or (current.role_id,current.login_epoch)!=(rid,epoch)
            or current.address.map_id!=1501 or not isinstance(proof,NpcInteraction)
            or (proof.role_id,proof.login_epoch)!=(rid,epoch) or proof.address!=current.address
            or proof.position_version!=current.version or (proof.npc_id,proof.placement_id)!=(10908,10)
            or proof.kind!='npc_interacted' or proof.position_validation!='bounds_version_distance'
            or type(proof.entity_key) is not int or not 0<proof.entity_key<2**63
            or type(proof.source_id) is not str or not 1<=len(proof.source_id)<=160
            or entity_key is not None and proof.entity_key!=entity_key):
        raise ValueError('Current original teaching NPC proof required')
    checkpoint=load_map_instance_transaction(db,aid,rid,epoch)
    if checkpoint is None or (checkpoint.address,checkpoint.position,checkpoint.version)!=(current.address,current.position,current.version):
        raise ValueError('Teaching requires exact adopted private checkpoint')
    load_story_instance_transaction(db,aid,rid,epoch,canonical,rules.story_rules,expected_address=current.address)
    if db.execute("SELECT 1 FROM task_battle_admissions WHERE role_id=? AND phase='admitted'",(rid,)).fetchone():
        raise ValueError('Teaching cannot run during a task battle')


def _activate(db,aid,rid,epoch,resources,q,request_id):
    for action in ('offer','accept'):
        actor,state=load_task_state(db,aid,rid,epoch)
        if action=='offer' and q in state.offered:continue
        apply_task_plan(db,actor,TaskDomain(resources).plan(actor,state,action,q),request_id+':'+action)


def _local_baseline_basis(db,aid,rid,epoch,resources,rules,policy,q,chapter,prior):
    """Read-only audit of the explicitly designed local pre-teaching cohort."""
    task=rules.definitions[q];origin=chapter.origin;route=origin.route
    if (type(policy) is not LocalPrologueBaselineRules or policy.revision!=LOCAL_BASELINE_REVISION
            or policy.policy_sha256!=LOCAL_BASELINE_POLICY_SHA or policy.evidence_sha256!=LOCAL_BASELINE_EVIDENCE_SHA
            or (q,task['incoming_ids'][0]) not in policy.task_pairs
            or read_other_skills(db,aid,rid,epoch,rules.skills) is not None):
        raise ValueError('Explicit designed policy and missing ledger required for cohort audit')
    restored=db.execute('SELECT origin,wallet_policy,creation_profile FROM role_restoration_origins WHERE role_id=?',(rid,)).fetchone()
    try:creation=json.loads(restored[2]) if restored else None
    except (TypeError,ValueError):raise ValueError('Malformed local creation evidence') from None
    if (restored is None or restored[0]!='new_restoration_role' or restored[1]!=policy.creation_wallet_policy
            or _json(creation)!=policy.creation_profile):
        raise ValueError('Consistent trusted local creation profile required, not a lone marker')
    growth=read_growth(db,aid,rid);attributes=read_naked_attributes(db,aid,rid,epoch)
    if (growth.policy!=creation['growth_policy'] or attributes.policy_revision!=creation['attribute_policy']
            or growth.baseline_level!=creation['profile']['level']):
        raise ValueError('Current ordinary profile differs from its frozen local creation source')
    completed={route.intro_task_id};node=route.successor_task_id
    while node!=q:
        if node in completed or node not in resources.definitions or len(completed)>32:
            raise ValueError('Missing, cyclic or unsupported original pre-teaching route')
        completed.add(node);edges=tuple(resources.definitions[node]['next_ids'])
        if len(edges)!=1:raise ValueError('Ambiguous pre-teaching original route')
        node=edges[0]
    _,state=load_task_state(db,aid,rid,epoch)
    main=lambda values:{v for v in values if 100000<=v<200000}
    if (main(state.completed)!=completed or main(state.active)!={q}
            or not main(state.offered|state.tracked)<=completed|{q}
            or db.execute('SELECT 1 FROM task_first_skills WHERE role_id=?',(rid,)).fetchone()):
        raise ValueError('Incomplete/cross-route journal or already paid teaching/downstream state')
    commands=tuple(db.execute('SELECT request_id,fingerprint,receipt FROM task_command_receipts WHERE role_id=? ORDER BY request_id',(rid,)))
    command_completions=set()
    for request,fingerprint,encoded in commands:
        try:receipt=json.loads(encoded)
        except (TypeError,ValueError):raise ValueError('Malformed local task command receipt') from None
        if (not _sha(fingerprint) or type(receipt) is not dict or receipt.get('role_id')!=rid
                or receipt.get('request_id')!=request or type(receipt.get('revision')) is not int
                or receipt['revision']<0 or type(receipt.get('effect_id')) is not str):
            raise ValueError('Conflicting local task command receipt')
        effect=receipt['effect_id']
        if effect:
            prefix=f'task:{rid}:'
            if not effect.startswith(prefix) or not effect[len(prefix):].isdigit():
                raise ValueError('Unknown local completion receipt source')
            target=int(effect[len(prefix):])
            if 100000<=target<200000:command_completions.add(target)
    effects=tuple(db.execute('SELECT task_id,payload FROM task_effects WHERE role_id=? AND task_id>=100000 AND task_id<200000 ORDER BY task_id',(rid,)))
    if command_completions!=completed or {row[0] for row in effects}!=completed:
        raise ValueError('Missing or downstream original completion evidence')
    for target,encoded in effects:
        try:effect=json.loads(encoded)
        except (TypeError,ValueError):raise ValueError('Malformed original task effect') from None
        if (type(effect) is not dict or effect.get('task_id')!=target or effect.get('settlement_id')!=f'task:{rid}:{target}'
                or effect.get('next_ids')!=list(resources.definitions[target]['next_ids'])):
            raise ValueError('Original completion effect differs from the local route')
    rewards=tuple(db.execute('SELECT task_id,channel,fingerprint,receipt FROM task_reward_channels WHERE role_id=? ORDER BY task_id,channel',(rid,)))
    reward_rows={}
    for target,channel,fingerprint,encoded in rewards:
        if 100000<=target<200000 and target not in completed:
            raise ValueError('Teaching or downstream reward already paid')
        if not _sha(fingerprint):raise ValueError('Malformed reward source fingerprint')
        try:decoded=json.loads(encoded)
        except (TypeError,ValueError):raise ValueError('Malformed reward receipt') from None
        if target in completed:
            if type(decoded) is not dict:raise ValueError('Original reward receipt must be a complete record')
            reward_rows[(target,channel)]=(fingerprint,decoded)
    for target,encoded in effects:
        effect=json.loads(encoded)
        # These approved first-teaching prefixes have no item or pet awards.
        # The public planner validates original metadata and fingerprints with
        # an intentionally empty catalog; it never authorizes an item grant.
        plan=plan_task_reward(rid,target,effect,resources,{})
        if effect['display_items'] or any(effect['display_rewards'][k] for k in ('PetExpReward','MoneyReward','ShengWang')):
            raise ValueError('Original local pre-teaching reward scope changed')
        currencies={field:(name,effect['display_rewards'][field]) for field,name in policy.currency_fields
            if effect['display_rewards'].get(field,0)}
        expected={'character_exp','items','pet_experience'}|{'currency:'+field for field in currencies}
        if {channel for qid,channel in reward_rows if qid==target}!=expected:
            raise ValueError('Missing or unknown original pre-teaching reward channel')
        fingerprint,receipt=reward_rows[(target,'character_exp')]
        if (fingerprint!=plan.fingerprint or set(receipt)!={'awarded','balance_after'}
                or type(receipt['awarded']) is not int or receipt['awarded']!=plan.experience
                or type(receipt['balance_after']) is not int or not 0<=receipt['balance_after']<2**63):
            raise ValueError('Original character experience receipt differs from its source')
        fingerprint,receipt=reward_rows[(target,'items')]
        if fingerprint!=plan.item_fingerprint or receipt!={'grants':[]}:
            raise ValueError('Original empty-item receipt differs from its source')
        decision=db.execute('SELECT payload FROM task_pet_reward_decisions WHERE role_id=? AND task_id=?',(rid,target)).fetchone()
        try:decision=json.loads(decision[0]) if decision else None
        except (TypeError,ValueError):raise ValueError('Malformed original pet reward decision') from None
        if (type(decision) is not dict or type(decision.get('amount')) is not int or decision['amount']!=0
                or decision.get('recipient_id') is not None or decision.get('status')!='zero'
                or decision.get('reason')!='original_zero'):
            raise ValueError('Original zero-pet reward decision missing or changed')
        fingerprint,receipt=reward_rows[(target,'pet_experience')]
        if fingerprint!=plan.fingerprint or _json(receipt)!=_json(dict(decision=_hash(decision),status='zero',
                amount=0,recipient_id=None,reason='original_zero')):
            raise ValueError('Original pet reward receipt differs from its frozen decision')
        for field,(name,amount) in currencies.items():
            fingerprint,receipt=reward_rows[(target,'currency:'+field)]
            wanted=dict(field=field,currency=name,amount=amount,policy=policy.creation_wallet_policy,
                source_ref=f'task:{target}:{field}',settlement_id=f'task:{rid}:{target}:currency:{field}')
            if fingerprint!=plan.fingerprint or _json(receipt)!=_json(wanted):
                raise ValueError('Original currency reward receipt differs from its source')
    asset_receipts=[]
    for table in ('role_settlements','role_wallet_receipts'):
        values=tuple(row[0] for row in db.execute(f'SELECT settlement_id FROM {table} WHERE role_id=? ORDER BY settlement_id',(rid,)))
        for value in values:
            prefix=f'task:{rid}:'
            if value.startswith(prefix):
                encoded=value[len(prefix):].split(':',1)[0]
                if not encoded.isdigit() or 100000<=int(encoded)<200000 and int(encoded) not in completed:
                    raise ValueError('Downstream or cross-route asset reward receipt')
        asset_receipts.append((table,values))
    return _hash((policy.revision,policy.policy_sha256,policy.evidence_sha256,policy.creation_profile,
        origin.creation_id,origin.chapter_id,origin.route_fingerprint,q,prior,tuple(restored),state.revision,
        sorted(completed),commands,effects,rewards,asset_receipts))


def _ticket_record(ticket):
    record=asdict(ticket)
    # Keep the already reviewed known-ledger ticket encoding unchanged.
    if ticket.baseline_eligibility is None:record.pop('baseline_eligibility')
    return _json(record)


def reconcile_first_skill_successor_transaction(db,aid,rid,epoch,resources,rules,previous_task_id):
    """After trusted AI8001 task settlement, same transaction; never grant yet."""
    source=resources.definitions.get(previous_task_id);edges=tuple(source['next_ids']) if source else ()
    if len(edges)!=1 or edges[0] not in rules.definitions:raise ValueError('No original teaching successor')
    q=edges[0];actor,state,task,chapter,prior,canonical=_scope(db,aid,rid,epoch,resources,rules,q)
    if q in state.active|state.completed:return ()
    checkpoint=load_map_instance_transaction(db,aid,rid,epoch)
    if checkpoint is None or checkpoint.address.map_id!=1501:raise ValueError('Teaching continuation needs adopted private source')
    load_story_instance_transaction(db,aid,rid,epoch,canonical,rules.story_rules,expected_address=checkpoint.address)
    if task['next_ids'][0] in state.active|state.completed:raise ValueError('Later teaching successor already started')
    _activate(db,aid,rid,epoch,resources,q,f'first-skill-next:{previous_task_id}:{q}')
    continue_task_chain(db,aid,rid,epoch,previous_task_id,resources)
    return (q,)


def open_first_skill_transaction(db,aid,rid,epoch,resources,rules,q,proof,current,*,generation,map_generation,now_ms,movement_state,
        baseline_policy=None):
    actor,state,task,chapter,prior,canonical=_scope(db,aid,rid,epoch,resources,rules,q)
    skills=read_other_skills(db,aid,rid,epoch,rules.skills)
    if (tuple(sorted(x for x in state.active if 100000<=x<200000))!=(q,)
            or type(generation) is not int or generation<=0 or type(map_generation) is not str or not 1<=len(map_generation)<=128
            or type(now_ms) is not int or not 0<=now_ms<2**63-rules.timeout_ms
            or type(movement_state) is not int or movement_state!=0):
        raise ValueError('Teaching needs current active task, known full skills and normal owner state')
    _world(db,aid,rid,epoch,rules,canonical,proof,current)
    basis=_local_baseline_basis(db,aid,rid,epoch,resources,rules,baseline_policy,q,chapter,prior) if skills is None else None
    ticket=FirstSkillTicket(q,chapter.origin.chapter_id,canonical,current,state.revision,None if skills is None else skills.revision,generation,
        map_generation,proof.entity_key,now_ms,now_ms+rules.minimum_ms,now_ms+rules.timeout_ms,
        'first-skill:'+uuid4().hex,rules.fingerprint,basis)
    return FirstSkillMenu(ticket,((S_ACCEPT_SCENARIO_QUEST,encode_accept_scenario_quest(
        ScenarioQuestInfo(q,SCENARIO_READY,0,0,proof.entity_key))),
        (S_REFRESH_SCENARIO_QUEST_STATE,encode_scenario_state(q,SCENARIO_READY)),
        (S_VISIT_NPC,encode_visit_npc(proof.entity_key,(),(q,)))))


def complete_first_skill_transaction(db,aid,rid,epoch,resources,rules,ticket,command,inventory,*,
        proof,location,generation,map_generation,now_ms,movement_state,growth_rules=None,attribute_rules=None,
        currency_rules=None,pet_experience_rules=None,resource_rules=None,equipment_rules=None,baseline_policy=None):
    """Receipt-first retry is pure CURRENT full skills/XP/profile, never reward replay.

    Old-epoch ticket rejects; new lease reads current ledger via login Interface.
    Non-task battles and other menu revocation are caller's owner state contract.
    """
    if (type(ticket) is not FirstSkillTicket or not isinstance(ticket.source,Location)
            or (ticket.source.role_id,ticket.source.login_epoch)!=(rid,epoch) or ticket.source.state!='active'
            or ticket.fingerprint!=rules.fingerprint or type(generation) is not int or generation<=0
            or type(ticket.generation) is not int or generation!=ticket.generation
            or type(ticket.map_generation) is not str or not 1<=len(ticket.map_generation)<=128
            or type(now_ms) is not int or not 0<=now_ms<2**63 or type(ticket.opened_ms) is not int
            or not 0<=ticket.opened_ms<2**63-rules.timeout_ms
            or type(ticket.earliest_ms) is not int or type(ticket.deadline_ms) is not int
            or ticket.earliest_ms!=ticket.opened_ms+rules.minimum_ms or ticket.deadline_ms!=ticket.opened_ms+rules.timeout_ms
            or type(ticket.task_revision) is not int or ticket.task_revision<0
            or not (type(ticket.skill_revision) is int and ticket.skill_revision>=0 and ticket.baseline_eligibility is None
                or ticket.skill_revision is None and _sha(ticket.baseline_eligibility) and baseline_policy is not None)
            or type(ticket.entity_key) is not int or not 0<ticket.entity_key<2**63
            or type(ticket.operation_id) is not str or not 1<=len(ticket.operation_id)<=128
            or not isinstance(command,TaskIntent) or (command.kind,command.task_id,command.npc_key,command.opaque)
                !=(C_COMMIT_SCENARIO_QUEST,ticket.task_id,ticket.entity_key,0)
            or (inventory.account_id,inventory.role_id)!=(aid,rid)):
        raise ValueError('Invalid, stale or changed teaching command/ticket')
    actor,state,task,chapter,prior,canonical=_scope(db,aid,rid,epoch,resources,rules,ticket.task_id)
    if ticket.chapter_id!=chapter.origin.chapter_id or ticket.directory_intent!=canonical:raise ValueError('Teaching chapter changed')
    skills=read_other_skills(db,aid,rid,epoch,rules.skills)
    inventory.immutable_snapshot_transaction(db,epoch=epoch)
    profile=current_task_resource_profile(db,actor,inventory,resource_rules,equipment_rules)
    encoded=_ticket_record(ticket);previous=_json(prior);fingerprint=_hash((rules.fingerprint,encoded,previous))
    source='first-skill:'+fingerprint;expected=(ticket.operation_id,fingerprint,encoded,previous,source)
    old=db.execute('SELECT operation_id,fingerprint,ticket,predecessor,source_event,grant_receipt '
        'FROM task_first_skills WHERE role_id=? AND task_id=?',(rid,ticket.task_id)).fetchone()
    if old is not None:
        if skills is None:raise ValueError('Paid teaching has lost its complete current skill ledger')
        effect=db.execute('SELECT payload FROM task_effects WHERE role_id=? AND task_id=?',(rid,ticket.task_id)).fetchone()
        saved=json.loads(old[5]);value=saved.get('value');after_revision=saved.get('after_revision')
        if (tuple(old[:5])!=expected or ticket.task_id not in state.completed or effect is None
                or json.loads(effect[0]).get('source_event')!=source or saved.get('policy')!=rules.revision
                or saved.get('skill_id')!=100008 or type(value) is not int or not 1<=value<2**31
                or saved.get('baseline')!=skills.baseline_fingerprint
                or type(saved.get('before_revision')) is not int or saved['before_revision']!=(0 if ticket.skill_revision is None else ticket.skill_revision)
                or type(after_revision) is not int or after_revision not in
                    ((0,1) if ticket.skill_revision is None else (ticket.skill_revision,ticket.skill_revision+1))):
            raise ValueError('Conflicting teaching paid operation')
        if profile is None:profile=attribute_snapshot_if_initialized(db,aid,rid,epoch)
        growth=(growth_refresh(read_growth(db,aid,rid),profile),) if profile is not None else ()
        messages=((S_REFRESH_USER_EXP,encode_user_experience(read_experience(db,aid,rid).experience)),)+growth+other_skill_messages(skills,rules.skills)
        return FirstSkillResult(None,skills,messages,True)
    if (ticket.task_id not in state.active or state.revision!=ticket.task_revision
            or (None if skills is None else skills.revision)!=ticket.skill_revision
            or tuple(sorted(x for x in state.active if 100000<=x<200000))!=(ticket.task_id,)
            or task['next_ids'][0] in state.active|state.completed or location!=ticket.source
            or map_generation!=ticket.map_generation or not ticket.earliest_ms<=now_ms<ticket.deadline_ms
            or type(movement_state) is not int or movement_state!=0):
        raise ValueError('Premature, moved, expired or changed teaching operation')
    _world(db,aid,rid,epoch,rules,canonical,proof,location,entity_key=ticket.entity_key)
    if skills is None:
        basis=_local_baseline_basis(db,aid,rid,epoch,resources,rules,baseline_policy,ticket.task_id,chapter,prior)
        if basis!=ticket.baseline_eligibility:raise ValueError('Local compatibility cohort/source changed since opening')
        origin=chapter.origin
        permit=LocalPrologueBaselinePermit(aid,rid,baseline_policy.revision,baseline_policy.policy_sha256,
            baseline_policy.evidence_sha256,f'local-prologue:{rid}:{baseline_policy.revision}',origin.creation_id,
            origin.chapter_id,origin.route_fingerprint,ticket.task_id,task['incoming_ids'][0],prior[0],prior[2],prior[3],
            basis,ticket.operation_id,epoch)
        skills=enroll_local_prologue_other_skills(db,aid,rid,epoch,rules.skills,baseline_policy,permit)
    after=grant_other_skill(db,aid,rid,epoch,rules.skills,100008,1,expected_revision=skills.revision)
    evidence=TaskEvidence(ticket.task_id,rid,epoch,'prologue_first_skill_granted',source,1501,10908,100008)
    done=complete_task_transaction(db,actor,TaskDomain(resources).plan(actor,state,'complete',ticket.task_id,evidence=evidence),
        ticket.operation_id,resources,inventory,growth_rules,attribute_rules,currency_rules,pet_experience_rules,
        resource_rules=resource_rules,equipment_rules=equipment_rules)
    # The next original type40 is made active; its registry remains disabled.
    successor=task['next_ids'][0]
    if not done.started_tasks:
        _activate(db,aid,rid,epoch,resources,successor,'first-skill-after:'+ticket.operation_id)
        continue_task_chain(db,aid,rid,epoch,ticket.task_id,resources)
        done=replace(done,started_tasks=(successor,),started_infos=(ScenarioQuestInfo(successor,SCENARIO_ACTIVE,0,0,0),))
    if done.started_tasks!=(successor,):raise ValueError('Teaching must activate only its original successor')
    saved=dict(policy=rules.revision,skill_id=100008,value=dict(after.entries)[100008],baseline=after.baseline_fingerprint,
        before_revision=skills.revision,after_revision=after.revision)
    db.execute('INSERT INTO task_first_skills VALUES(?,?,?,?,?,?,?,?)',(rid,ticket.task_id,*expected,_json(saved)))
    return FirstSkillResult(done,after,completion_messages(done)+other_skill_messages(after,rules.skills),False)
