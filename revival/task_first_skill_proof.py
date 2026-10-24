"""Pure current-lease read of the original committed first teaching.

This Module owns interpretation of teaching receipts for later Task callers.
It grants no skill, reward, repair or menu permission. A historical teaching
epoch stays historical; the current lease only authorizes reading its proof.
"""
from dataclasses import asdict,dataclass
import hashlib
import json
from task_first_skill import FirstSkillRules,FirstSkillTicket
from task_newbie_chapter import read_newbie_chapter
from task_persistence import load_task_state,get_task_receipt
from task_battle import read_completed_task_battle_proof
from task_domain import valid_task_epoch
from task_rewards import plan_task_reward
from role_skills import read_other_skills
from tasks import _plain
from world_owner import MapAddress,Location
from world_story_instances import StoryInstanceIntent


def _json(value):return json.dumps(value,sort_keys=True,separators=(',',':'))
def _hash(value):return hashlib.sha256(_json(value).encode()).hexdigest()
def _sha(value):return type(value) is str and len(value)==64 and all(c in '0123456789abcdef' for c in value)


@dataclass(frozen=True)
class CompletedFirstSkillProof:
    task_id:int
    chapter_id:str
    operation_id:str
    fingerprint:str
    predecessor:tuple
    source_address:MapAddress
    skills:object


def _ticket(encoded):
    try:
        raw=json.loads(encoded)
        source=dict(raw['source']);source['address']=MapAddress(**source['address'])
        raw['source']=Location(**source)
        raw['directory_intent']=StoryInstanceIntent(**raw['directory_intent'])
        ticket=FirstSkillTicket(**raw)
        record=asdict(ticket)
        if ticket.baseline_eligibility is None:record.pop('baseline_eligibility')
        if _json(record)!=encoded:raise ValueError('Noncanonical teaching ticket')
        return ticket
    except (TypeError,ValueError,KeyError,AttributeError):
        raise ValueError('Malformed committed teaching ticket') from None


def _rewards(db,rid,q,resources,effect):
    plan=plan_task_reward(rid,q,effect,resources,{})
    if (plan.experience!=120 or plan.grants or plan.pending or effect.get('reward_status')!='settled'
            or effect.get('reward_pending')!=[]):
        raise ValueError('Teaching must retain its settled original120XP and zero other rewards')
    rows={name:(fingerprint,json.loads(encoded)) for name,fingerprint,encoded in db.execute(
        'SELECT channel,fingerprint,receipt FROM task_reward_channels WHERE role_id=? AND task_id=?',(rid,q))}
    if set(rows)!={'character_exp','items','pet_experience'}:
        raise ValueError('Teaching reward channels missing or unexpected')
    fingerprint,receipt=rows['character_exp']
    if (fingerprint!=plan.fingerprint or type(receipt) is not dict or set(receipt)!={'awarded','balance_after'}
            or type(receipt['awarded']) is not int or receipt['awarded']!=120
            or type(receipt['balance_after']) is not int or not 0<=receipt['balance_after']<2**63):
        raise ValueError('Teaching original experience receipt changed')
    if rows['items']!=(plan.item_fingerprint,{'grants':[]}):
        raise ValueError('Teaching zero-item receipt changed')
    raw=db.execute('SELECT payload FROM task_pet_reward_decisions WHERE role_id=? AND task_id=?',(rid,q)).fetchone()
    decision=json.loads(raw[0]) if raw else None
    if (type(decision) is not dict or type(decision.get('amount')) is not int or decision['amount']!=0
            or decision.get('recipient_id') is not None or decision.get('status')!='zero'
            or decision.get('reason')!='original_zero'):
        raise ValueError('Teaching original zero-pet decision required')
    expected={'decision':_hash(decision),'status':'zero','amount':0,'recipient_id':None,'reason':'original_zero'}
    if rows['pet_experience'][0]!=plan.fingerprint or _json(rows['pet_experience'][1])!=_json(expected):
        raise ValueError('Teaching zero-pet receipt changed')


def read_completed_first_skill_proof(db,aid,rid,epoch,resources,rules,q):
    """Read a genuine completed teaching and its CURRENT complete skill map.

    Requires the caller's current owned transaction. It performs only reads,
    including after reconnect or later skill growth; no old ticket is redeemed.
    World/NPC freshness and engine capabilities belong to the next action.
    """
    if type(rules) is not FirstSkillRules:raise ValueError('Prepared first-teaching rules required')
    actor,state=load_task_state(db,aid,rid,epoch)
    skills=read_other_skills(db,aid,rid,epoch,rules.skills)
    chapter=read_newbie_chapter(db,aid,rid,epoch,rules.chapter_rules)
    task=rules.definitions.get(q)
    if (chapter is None or chapter.phase!='completed' or task is None or q not in state.completed
            or _plain(task)!=_plain(resources.definitions.get(q)) or skills is None
            or dict(skills.entries).get(100008,0)<1):
        raise ValueError('Completed original teaching and current known learned100008 required')
    origin=chapter.origin;route=origin.route;key=(route.character_id,route.school_id)
    school=db.execute('SELECT school FROM roles WHERE id=?',(rid,)).fetchone()[0]
    if (rules.route_tasks.get(key)!=q or school!=route.school_id
            or resources.shape_to_role_config.get(actor.shape)!=route.character_id
            or route.intro_task_id not in state.completed):
        raise ValueError('Completed teaching differs from the original creation route')
    prior=read_completed_task_battle_proof(db,aid,rid,epoch,resources,rules.battles,task['incoming_ids'][0])
    row=db.execute('SELECT operation_id,fingerprint,ticket,predecessor,source_event,grant_receipt '
        'FROM task_first_skills WHERE role_id=? AND task_id=?',(rid,q)).fetchone()
    if row is None:raise ValueError('Completed teaching has no committed grant receipt')
    operation,fingerprint,encoded,previous,source,grant=row
    ticket=_ticket(encoded);saved=json.loads(grant)
    canonical=StoryInstanceIntent(origin.chapter_id,origin.creation_id,origin.policy,origin.route_fingerprint,
        rules.story_rules.source_tasks[key])
    address=ticket.source.address
    if (ticket.task_id!=q or ticket.chapter_id!=origin.chapter_id or ticket.directory_intent!=canonical
            or ticket.fingerprint!=rules.fingerprint or ticket.operation_id!=operation
            or type(operation) is not str or not 1<=len(operation)<=128
            or ticket.source.role_id!=rid or not valid_task_epoch(ticket.source.login_epoch)
            or ticket.source.state!='active' or address.map_id!=1501
            or any(type(v) is not int or v<0 for v in (address.instance_id,address.partition_id,ticket.source.version))
            or address.instance_id==0 or type(ticket.generation) is not int or ticket.generation<=0
            or type(ticket.map_generation) is not str or not 1<=len(ticket.map_generation)<=128
            or type(ticket.entity_key) is not int or not 0<ticket.entity_key<2**63
            or type(ticket.task_revision) is not int or ticket.task_revision<0
            or type(ticket.opened_ms) is not int or not 0<=ticket.opened_ms<2**63-rules.timeout_ms
            or ticket.earliest_ms!=ticket.opened_ms+rules.minimum_ms
            or ticket.deadline_ms!=ticket.opened_ms+rules.timeout_ms
            or not (type(ticket.skill_revision) is int and ticket.skill_revision>=0 and ticket.baseline_eligibility is None
                or ticket.skill_revision is None and _sha(ticket.baseline_eligibility))
            or previous!=_json(prior) or fingerprint!=_hash((rules.fingerprint,encoded,previous))
            or source!='first-skill:'+fingerprint):
        raise ValueError('Committed teaching ticket, chapter or predecessor changed')
    before=0 if ticket.skill_revision is None else ticket.skill_revision
    if (type(saved) is not dict or set(saved)!={'policy','skill_id','value','baseline','before_revision','after_revision'}
            or saved['policy']!=rules.revision or type(saved['skill_id']) is not int or saved['skill_id']!=100008
            or saved['baseline']!=skills.baseline_fingerprint or type(saved['value']) is not int
            or not 1<=saved['value']<=dict(skills.entries)[100008]
            or type(saved['before_revision']) is not int or saved['before_revision']!=before
            or type(saved['after_revision']) is not int or saved['after_revision'] not in (before,before+1)
            or skills.revision<saved['after_revision']):
        raise ValueError('Committed teaching grant differs from current complete skills')
    effect_row=db.execute('SELECT payload FROM task_effects WHERE role_id=? AND task_id=?',(rid,q)).fetchone()
    effect=json.loads(effect_row[0]) if effect_row else None
    receipt=get_task_receipt(db,aid,rid,operation)
    if (type(effect) is not dict or effect.get('source_event')!=source or receipt is None
            or (receipt.role_id,receipt.request_id,receipt.revision,receipt.effect_id)
                !=(rid,operation,ticket.task_revision+1,f'task:{rid}:{q}')):
        raise ValueError('Teaching task completion receipt/evidence changed')
    _rewards(db,rid,q,resources,effect)
    return CompletedFirstSkillProof(q,origin.chapter_id,operation,
        _hash((fingerprint,previous,source,saved)),prior,address,skills)
