"""Approved dream-return permits and atomic task/world settlement.

The role caller owns its transaction, final native encoding and publication.
Map operations/waits stay outside. Raw dialogue intents remain unauthorized.
"""
from dataclasses import asdict,dataclass,replace
import hashlib
import json
import struct
from types import MappingProxyType

from inspect_client import OUT
from task_prologue_return_dialogue import (RawDreamReturnIntent,ReturnDialogueTicket,RETURN_IDS,FIRST_RETURN_IDS,
    load_return_dialogue_resources,open_return_dialogue_transaction,inspect_return_commit_transaction)
from task_prologue_puzzle import read_completed_puzzle_proof
from task_battle import read_completed_task_battle_proof
from task_domain import TaskDomain,TaskEvidence,PROLOGUE_DREAM_RETURN_IDS,supports_prologue_dream_return
from task_newbie_chapter import read_newbie_chapter
from task_persistence import load_task_state,apply_task_plan
from task_workflow import complete_task_transaction,completion_messages
from task_chains import continue_task_chain
from task_rewards import update_reward_delivery
from task_growth_resources import current_task_resource_profile
from task_pet_experience import TaskPetExperienceResult,refresh_pet_experience,pet_experience_messages
from progression import read_experience
from role_growth import read_growth
from role_attribute_storage import attribute_snapshot_if_initialized
from role_attribute_protocol import growth_refresh
from task_dialog_protocol import S_REFRESH_USER_EXP,encode_user_experience
from world_owner import MapAddress,TransferCommit
from world_transfer_storage import commit_transfer_transaction,load_map_instance_transaction,MapInstanceCheckpoint
from world_catalog import valid_position
from world_collision import maze_clear,character_movement_mask
from world_story_instances import StoryInstanceIntent,load_story_instance_transaction
from inventory import pet_record


def _json(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'))


def _hash(value):
    return hashlib.sha256(_json(value).encode()).hexdigest()


def _same(actual,expected):
    if type(actual) is not type(expected):return False
    if isinstance(expected,dict):return set(actual)==set(expected) and all(_same(actual[k],v) for k,v in expected.items())
    if isinstance(expected,list):return len(actual)==len(expected) and all(_same(a,b) for a,b in zip(actual,expected))
    return actual==expected


@dataclass(frozen=True)
class DreamReturnRules:
    revision:str
    policy_fingerprint:str
    fingerprint:str
    dialogue:object
    puzzles:object
    battles:object
    targets:object
    target_address:MapAddress
    timeout_ms:int
    minimum_ms:int


def load_dream_return_rules(resources,chapters,story,placements,catalog,grids,*,puzzles,battles,
        path=OUT/'design/newbie-dream-return-v1.json'):
    """Startup only: freeze the exact central policy and original20 resources."""
    policy=json.loads(path.read_text(encoding='utf-8'))
    text_fields=('scope','research','dialogue_resources','target_validation','authorization','dialogue_limit',
        'dialogue_invalidation','admission','handoff','reward_channels','successor','retry','failure_before_commit',
        'failure_after_commit','private_cleanup','cinematics','compatibility','activation')
    fixed={'revision':'2026-10-24.newbie-dream-return.1','coordinate_scale':16,
        'target_address':[1006,1006,0],'dialogue_deadline_ms':300000,'minimum_reading_ms':0}
    required=set(text_fields)|set(fixed)|{'source_status','first','second'}
    if (type(policy) is not dict or set(policy)!=required
            or any(type(policy.get(k)) is not str or not policy[k] for k in text_fields)
            or any(not _same(policy.get(k),v) for k,v in fixed.items())
            or policy.get('research')!='evidence/PROLOGUE_DREAM_RETURN_RESEARCH.md'
            or not isinstance(policy.get('source_status'),dict)
            or set(policy['source_status'])!={'tasks_edges_npcs_raw_jump_and_rewards','coordinate_units',
                'adopted_conversion_handoff_and_deadline','original_server_instance_semantics'}
            or any(type(v) is not str or not v for v in policy['source_status'].values())
            or policy['source_status']['tasks_edges_npcs_raw_jump_and_rewards']!='client_verified'
            or policy['source_status']['adopted_conversion_handoff_and_deadline']!='designed'):
        raise ValueError('Published dream-return policy requires implementation review')
    expected=(dict(npc_id=10085,placement_id=2,source_position=[2426,640],raw_jump=[3,1006,170,70],
            logical_target=[1006,2720,1120],character_experience=125,pet_experience=0),
        dict(npc_id=10140,placement_id=6,source_position=[5464,1993],raw_jump=[3,1006,335,144],
            logical_target=[1006,5360,2304],character_experience=450,pet_experience=450))
    for name,values in zip(('first','second'),expected):
        row=policy.get(name)
        if (type(row) is not dict or set(row)!=set(values)|{'predecessor'}
                or any(not _same(row.get(k),v) for k,v in values.items())
                or type(row.get('predecessor')) is not str or not row['predecessor']):
            raise ValueError('Dream-return family changed its approved source/target/reward')
    dialogue=load_return_dialogue_resources(resources,chapters,story,placements)
    if RETURN_IDS!=PROLOGUE_DREAM_RETURN_IDS or any(not supports_prologue_dream_return(t) for t in dialogue.definitions.values()):
        raise ValueError('Dream-return task capability differs from original20')
    if (puzzles.chapter_rules!=chapters or puzzles.story_rules!=story
            or puzzles.policy.revision!='2026-10-23.newbie-puzzle.1'
            or puzzles.policy.minimum_elapsed_ms!=0 or puzzles.policy.timeout_ms!=300000
            or len(puzzles.policy.source_fingerprint)!=64):
        raise ValueError('Puzzle proof resources differ from the frozen creation/directory rules')
    required_battles={dialogue.definitions[q]['incoming_ids'][0] for q in FIRST_RETURN_IDS}
    if len(required_battles)!=10 or not required_battles<=set(battles.definitions):
        raise ValueError('All original first-return battle definitions are required without enabling them')
    targets={}
    for q in dialogue.definitions:
        point=tuple(expected[0 if q in FIRST_RETURN_IDS else 1]['logical_target'])
        grid=grids.get(point[0])
        if not valid_position(point,catalog) or grid is None or not maze_clear(grid,*point[1:],mask=character_movement_mask(0)):
            raise ValueError('Approved exact public dream-return target is unavailable')
        targets[q]=point
    fingerprint=_hash((_hash(policy),dialogue.fingerprint,puzzles.fingerprint,
        sorted((q,t.fingerprint) for q,t in battles.definitions.items() if q in {
            dialogue.definitions[x]['incoming_ids'][0] for x in FIRST_RETURN_IDS}),targets))
    return DreamReturnRules(policy['revision'],_hash(policy),fingerprint,dialogue,puzzles,battles,
        MappingProxyType(targets),MapAddress(*policy['target_address']),policy['dialogue_deadline_ms'],policy['minimum_reading_ms'])


@dataclass(frozen=True)
class AuthorizedDreamReturn:
    raw:RawDreamReturnIntent
    command:object
    npc_proof:object
    predecessor_proof:tuple
    target_address:MapAddress
    target_position:tuple
    policy_revision:str
    policy_fingerprint:str
    fingerprint:str


@dataclass(frozen=True)
class DreamReturnResult:
    transfer_id:str
    target:object
    completion:object
    messages:tuple
    replayed:bool=False
    current_position:object=None


def prepare_dream_return_storage(db):
    """Startup only; other Modules prepare their own prerequisite tables."""
    db.execute('''CREATE TABLE IF NOT EXISTS task_dream_returns (
        role_id INTEGER NOT NULL REFERENCES roles(id),task_id INTEGER NOT NULL,
        transfer_id TEXT NOT NULL UNIQUE,fingerprint TEXT NOT NULL,intent TEXT NOT NULL,
        world_receipt TEXT NOT NULL,source_event TEXT NOT NULL,reward_state TEXT NOT NULL,
        PRIMARY KEY(role_id,task_id))''')


def _predecessor(db,aid,rid,epoch,resources,rules,q):
    task=rules.dialogue.definitions.get(q)
    if task is None:raise ValueError('Not an original approved dream-return task')
    before=task['incoming_ids'][0]
    if q in FIRST_RETURN_IDS:
        return read_completed_task_battle_proof(db,aid,rid,epoch,resources,rules.battles,before)
    return read_completed_puzzle_proof(db,aid,rid,epoch,resources,rules.puzzles,before)


def reconcile_dream_return_successor_transaction(db,aid,rid,epoch,resources,rules,previous_task_id):
    """Activate only the original return after its trusted predecessor settles.

    Invoke in the SAME role transaction as battle/puzzle settlement, before
    final encoding/commit. Recovery may read an existing trusted receipt. No
    predecessor, private directory, origin or reward is manufactured here.
    """
    chapter=read_newbie_chapter(db,aid,rid,epoch,rules.dialogue.chapter_rules)
    if chapter is None or chapter.phase!='completed':
        raise ValueError('Completed creation chapter required for dream-return continuation')
    route=chapter.origin.route
    ids=rules.dialogue.route_tasks.get((route.character_id,route.school_id),())
    matches=tuple(q for q in ids if tuple(rules.dialogue.definitions[q]['incoming_ids'])==(previous_task_id,))
    if not matches:return ()
    if len(matches)!=1:raise ValueError('Ambiguous original dream-return successor')
    q=matches[0];_predecessor(db,aid,rid,epoch,resources,rules,q)
    actor,state=load_task_state(db,aid,rid,epoch)
    school=db.execute('SELECT school FROM roles WHERE id=?',(rid,)).fetchone()[0]
    if (school!=route.school_id or resources.shape_to_role_config.get(actor.shape)!=route.character_id
            or route.intro_task_id not in state.completed):
        raise ValueError('Dream-return continuation differs from original creation route')
    if q in state.active|state.completed:return ()
    if (state.active&PROLOGUE_DREAM_RETURN_IDS
            or rules.dialogue.definitions[q]['next_ids'][0] in state.active|state.completed):
        raise ValueError('Conflicting original dream-return continuation')
    checkpoint=load_map_instance_transaction(db,aid,rid,epoch)
    if checkpoint is None or checkpoint.address.map_id!=1501:
        raise ValueError('Dream-return continuation requires its adopted private source')
    origin=chapter.origin
    canonical=StoryInstanceIntent(origin.chapter_id,origin.creation_id,origin.policy,origin.route_fingerprint,
        rules.dialogue.story_rules.source_tasks[(route.character_id,route.school_id)])
    load_story_instance_transaction(db,aid,rid,epoch,canonical,rules.dialogue.story_rules,
        expected_address=checkpoint.address)
    for action in ('offer','accept'):
        if action=='offer' and q in state.offered:continue
        apply_task_plan(db,actor,TaskDomain(resources).plan(actor,state,action,q),
            f'dream-return-next:{previous_task_id}:{q}:{action}')
        actor,state=load_task_state(db,aid,rid,epoch)
    # The chain Module owns its completion envelope; our strict activation is
    # already durable in this same transaction, so its public read resolves it.
    continue_task_chain(db,aid,rid,epoch,previous_task_id,resources)
    return (q,)


def open_dream_return_transaction(db,aid,rid,epoch,resources,rules,q,proof,current,*,generation,map_generation,now_ms):
    if type(now_ms) is not int or not 0<=now_ms<2**63-rules.timeout_ms:
        raise ValueError('Bounded dream-return server clock required')
    _predecessor(db,aid,rid,epoch,resources,rules,q)
    return open_return_dialogue_transaction(db,aid,rid,epoch,resources,rules.dialogue,q,proof,current,
        generation=generation,map_generation=map_generation,now_ms=now_ms,deadline_ms=now_ms+rules.timeout_ms)


def resolve_dream_return_transaction(db,aid,rid,epoch,resources,rules,raw,command,proof,current,*,
        generation,map_generation,now_ms,movement_state):
    if not isinstance(raw,RawDreamReturnIntent) or raw.settlement_authorized is not False:
        raise ValueError('Original unresolved dialogue intent required')
    ticket=raw.ticket
    if (not isinstance(ticket,ReturnDialogueTicket) or ticket.deadline_ms!=ticket.opened_ms+rules.timeout_ms
            or not ticket.opened_ms+rules.minimum_ms<=now_ms<ticket.deadline_ms
            or type(movement_state) is not int or movement_state!=0):
        raise ValueError('Dream return requires current normal state and approved dialogue deadline')
    checked=inspect_return_commit_transaction(db,aid,rid,epoch,resources,rules.dialogue,ticket,command,proof,current,
        generation=generation,map_generation=map_generation,now_ms=now_ms)
    if checked!=raw:raise ValueError('Raw dream-return intent differs from its fresh current proof')
    predecessor=_predecessor(db,aid,rid,epoch,resources,rules,ticket.task_id)
    return AuthorizedDreamReturn(raw,command,proof,predecessor,rules.target_address,rules.targets[ticket.task_id],
        rules.revision,rules.policy_fingerprint,rules.fingerprint)


def _identity(db,aid,rid,epoch,resources,rules,permit):
    if not isinstance(permit,AuthorizedDreamReturn) or not isinstance(permit.raw,RawDreamReturnIntent):
        raise ValueError('Approved dream-return permit required; raw intent is not settlement authority')
    ticket=permit.raw.ticket
    if (not isinstance(ticket,ReturnDialogueTicket) or ticket.fingerprint!=rules.dialogue.fingerprint
            or permit.raw.settlement_authorized is not False or permit.fingerprint!=rules.fingerprint
            or permit.policy_revision!=rules.revision or permit.policy_fingerprint!=rules.policy_fingerprint
            or permit.target_address!=rules.target_address or permit.target_position!=rules.targets.get(ticket.task_id)):
        raise ValueError('Dream-return permit differs from frozen policy/resources')
    actor,state=load_task_state(db,aid,rid,epoch)
    chapter=read_newbie_chapter(db,aid,rid,epoch,rules.dialogue.chapter_rules)
    task=rules.dialogue.definitions.get(ticket.task_id)
    if chapter is None or chapter.phase!='completed' or task is None:
        raise ValueError('Dream-return chapter/definition missing')
    route=chapter.origin.route
    school=db.execute('SELECT school FROM roles WHERE id=?',(rid,)).fetchone()[0]
    if (chapter.origin.chapter_id!=ticket.chapter_id
            or ticket.task_id not in rules.dialogue.route_tasks.get((route.character_id,route.school_id),())
            or school!=route.school_id or resources.shape_to_role_config.get(actor.shape)!=route.character_id
            or route.intro_task_id not in state.completed):
        raise ValueError('Dream-return permit belongs to another creation route')
    return actor,state,task,ticket


def _world_receipt(permit,receipt):
    if not isinstance(receipt,TransferCommit):raise ValueError('Actual world target loading receipt required')
    source=permit.raw.ticket.location;frozen=receipt.frozen;reservation=frozen.reservation;offer=reservation.offer
    target=receipt.location
    if (offer.transfer_id!=permit.raw.ticket.request_id or offer.source!=source
            or offer.target_position!=permit.target_position or offer.deadline_ms!=permit.raw.ticket.deadline_ms
            or frozen.source!=replace(source,version=source.version+1,state='frozen')
            or reservation.target!=permit.target_address
            or target!=replace(frozen.source,address=permit.target_address,version=source.version+2,
                x=permit.target_position[1],y=permit.target_position[2],state='loading')):
        raise ValueError('World receipt differs from the approved exact dream-return handoff')
    return target


def _current_messages(db,actor,inventory,reward_state,resource_rules,equipment_rules):
    balance=read_experience(db,actor.account_id,actor.role_id)
    profile=current_task_resource_profile(db,actor,inventory,resource_rules,equipment_rules)
    if profile is None:profile=attribute_snapshot_if_initialized(db,actor.account_id,actor.role_id,actor.login_epoch)
    pet=TaskPetExperienceResult(**reward_state['pet'])
    pet=refresh_pet_experience(db,actor.account_id,actor.role_id,actor.login_epoch,pet,inventory)
    growth=(growth_refresh(read_growth(db,actor.account_id,actor.role_id),profile),) if profile is not None else ()
    return ((S_REFRESH_USER_EXP,encode_user_experience(balance.experience)),)+growth+pet_experience_messages(pet)


def complete_dream_return_transaction(db,aid,rid,epoch,resources,rules,permit,receipt,inventory,*,
        generation,map_generation,now_ms,movement_state,read_committed_world=None,
        growth_rules=None,attribute_rules=None,currency_rules=None,pet_experience_rules=None,
        resource_rules=None,equipment_rules=None):
    """One caller transaction. Caller encodes final role/scene before commit.

    read_committed_world is the world's PURE historical-receipt Interface for
    paid recovery, returning (stored receipt, current MapInstanceCheckpoint).
    Absent injection rejects replay, never uses a mutating recovery API.
    """
    actor,state,task,ticket=_identity(db,aid,rid,epoch,resources,rules,permit)
    if ((ticket.location.role_id,ticket.location.login_epoch)!=(rid,epoch)
            or type(generation) is not int or generation<=0 or generation!=ticket.generation
            or type(now_ms) is not int or not 0<=now_ms<2**63
            or (inventory.account_id,inventory.role_id)!=(aid,rid)):
        raise ValueError('Dream-return connection/lease/inventory scope changed')
    inventory.immutable_snapshot_transaction(db,epoch=epoch)
    current_task_resource_profile(db,actor,inventory,resource_rules,equipment_rules)
    target=_world_receipt(permit,receipt)
    encoded=_json(asdict(permit));world=_json(asdict(receipt));fingerprint=_hash((rules.fingerprint,encoded,world))
    source='dream-return:'+fingerprint
    expected=(ticket.request_id,fingerprint,encoded,world,source)
    old=db.execute('SELECT transfer_id,fingerprint,intent,world_receipt,source_event,reward_state '
        'FROM task_dream_returns WHERE role_id=? AND task_id=?',(rid,ticket.task_id)).fetchone()
    if old is not None:
        effect=db.execute('SELECT payload FROM task_effects WHERE role_id=? AND task_id=?',(rid,ticket.task_id)).fetchone()
        if tuple(old[:5])!=expected or ticket.task_id not in state.completed or effect is None or json.loads(effect[0]).get('source_event')!=source:
            raise ValueError('Conflicting dream-return paid operation')
        if not callable(read_committed_world):raise ValueError('Public pure committed-world receipt reader required')
        confirmed=read_committed_world(db,aid,rid,epoch,receipt)
        if (type(confirmed) is not tuple or len(confirmed)!=2 or confirmed[0]!=receipt
                or not isinstance(confirmed[1],MapInstanceCheckpoint)
                or (confirmed[1].role_id,confirmed[1].login_epoch)!=(rid,epoch)
                or confirmed[1].version<target.version
                or confirmed[1].version==target.version and (
                    confirmed[1].address!=target.address or confirmed[1].position!=target.position)):
            raise ValueError('World historical receipt/current checkpoint proof disagrees')
        saved=json.loads(old[5])
        if saved.get('character_experience')!=task['display_rewards']['ExpReward'] or saved.get('pet',{}).get('amount')!=task['display_rewards']['PetExpReward']:
            raise ValueError('Dream-return frozen reward receipt changed')
        messages=_current_messages(db,actor,inventory,saved,resource_rules,equipment_rules)
        return DreamReturnResult(ticket.request_id,None,None,messages,True,confirmed[1])
    if (ticket.task_id not in state.active or state.revision!=ticket.task_revision
            or task['next_ids'][0] in state.active|state.completed or map_generation!=ticket.map_generation):
        raise ValueError('Dream-return task or source map generation is no longer current')
    checked=resolve_dream_return_transaction(db,aid,rid,epoch,resources,rules,permit.raw,permit.command,
        permit.npc_proof,ticket.location,generation=generation,map_generation=map_generation,now_ms=now_ms,movement_state=movement_state)
    if checked!=permit:raise ValueError('Dream-return predecessor/proof changed before atomic settlement')
    checkpoint=load_map_instance_transaction(db,aid,rid,epoch)
    if checkpoint is None or (checkpoint.address,checkpoint.position,checkpoint.version)!=(
            ticket.location.address,ticket.location.position,ticket.location.version):
        raise ValueError('Exact private source checkpoint must be adopted before settlement')
    if not commit_transfer_transaction(db,aid,rid,epoch,receipt):
        raise ValueError('World committed without the same atomic dream-return task receipt')
    evidence=TaskEvidence(ticket.task_id,rid,epoch,'prologue_dream_return_committed',source,1501,task['target']['npc_id'],1006)
    plan=TaskDomain(resources).plan(actor,state,'complete',ticket.task_id,evidence=evidence)
    done=complete_task_transaction(db,actor,plan,ticket.request_id,resources,inventory,growth_rules,attribute_rules,
        currency_rules,pet_experience_rules,resource_rules=resource_rules,equipment_rules=equipment_rules)
    if done.started_tasks!=(task['next_ids'][0],) or not done.rewards.rewards_complete:
        raise ValueError('Dream return must settle original rewards and only its unique successor')
    pet=done.rewards.pet_experience
    saved={'character_experience':done.rewards.experience_awarded,
        'pet':{k:getattr(pet,k) for k in ('status','reason','amount','recipient_id')}}
    if pet.status=='awarded':
        current_pet=inventory.read_pet_state(db,pet.recipient_id)
        if current_pet is None or current_pet.progress is None:raise ValueError('Captured reward pet unavailable')
        pet_record(current_pet.__dict__);struct.pack('>iQ',current_pet.id,current_pet.progress.state.experience)
    effect=json.loads(db.execute('SELECT payload FROM task_effects WHERE role_id=? AND task_id=?',(rid,ticket.task_id)).fetchone()[0])
    effect['continuation_resolved_fields']=sorted(set(effect.get('continuation_resolved_fields',()))|{
        'RewardMapJumpType','RewardMapID','RewardMapXPos','RewardMapYPos'})
    effect['dream_return']={'policy':rules.revision,'fingerprint':rules.fingerprint,'transfer_id':ticket.request_id,
        'target':asdict(target),'gui_confirmed':False}
    delivered=update_reward_delivery(effect)
    db.execute('UPDATE task_effects SET payload=?,delivered=? WHERE role_id=? AND task_id=?',(_json(effect),int(delivered),rid,ticket.task_id))
    db.execute('INSERT INTO task_dream_returns VALUES(?,?,?,?,?,?,?,?)',(rid,ticket.task_id,*expected,_json(saved)))
    return DreamReturnResult(ticket.request_id,target,done,completion_messages(done))
