"""Durable first-master cards and exact-received-instance equipment goals.

Caller owns lease, transaction and delivery. Startup loads all configuration;
commands accept frozen map proofs/tickets, never a mutable conversation owner.
"""
from dataclasses import asdict,dataclass,replace
import json
from types import MappingProxyType
from inspect_client import OUT
from inventory import AssetChange,InventorySnapshot,EquipmentEvent
from tasks import _plain,_freeze
from task_domain import TaskDomain,TaskEvidence
from task_persistence import load_task_state,apply_task_plan
from task_newbie_chapter import read_newbie_chapter
from task_rewards import update_reward_delivery
from task_workflow import complete_task_transaction,completion_messages
from task_growth_resources import current_task_resource_profile,synchronize_task_inventory_source
from task_protocol import (ScenarioQuestInfo,S_ACCEPT_SCENARIO_QUEST,encode_accept_scenario_quest,
    C_COMMIT_SCENARIO_QUEST,S_REFRESH_SCENARIO_QUEST_STATE,encode_scenario_state)
from task_dialog_protocol import S_VISIT_NPC,encode_visit_npc
from world_owner import Location
from world_npcs import NpcInteraction
from world_card_protocol import S_PLAY_CARD_EFFECT,play_card_effect,decode_get_card_item
from task_protocol import SCENARIO_ACTIVE, SCENARIO_READY


def _json(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'))


@dataclass(frozen=True)
class MasterCardRoute:
    character_id:int
    school_id:int
    home_map_id:int
    master_task_id:int
    npc_id:int
    card_effect_id:int
    choices:tuple
    equipment_task_id:int
    cart_task_id:int


@dataclass(frozen=True)
class MasterCardRules:
    revision:str
    timeout_ms:int
    binding:int
    routes:object
    chapter_rules:object


def load_master_card_rules(resources,chapter_rules,inventory_config):
    """Startup: validate43 original route/choice pairs and all10 exact59 goals."""
    policy=json.loads((OUT/'design/newbie-master-card-v1.json').read_text(encoding='utf-8'))
    catalog=json.loads((OUT/'catalogs/newbie-master-cards.json').read_text(encoding='utf-8'))
    if (policy['revision']!='2026-10-23.master-card.1' or policy['choice']['binding']!=1
            or policy['choice']['timeout_ms']!=300000 or len(catalog['routes'])!=43):
        raise ValueError('Master card policy requires implementation review')
    routes={}
    for row in catalog['routes']:
        key=row['character_id'],row['school_id']
        intro=chapter_rules.routes.get(key)
        task=resources.definitions[row['master_task_id']]
        choices=tuple((x['item_id'],x['quantity']) for x in row['choices'])
        if (intro is None or intro.successor_task_id!=task['id'] or task['type']!=10
                or intro.successor_card_effect_id!=row['card_effect_id']
                or int(task['attributes']['ScenarioInfoAnimationID'])!=row['card_effect_id']
                or (task['target']['map_id'],task['target']['npc_id'])!=(row['home_map_id'],row['npc_id'])
                or (intro.home_map_id,intro.first_npc_id)!=(row['home_map_id'],row['npc_id'])
                or len(task['dialogue']['start'])!=3 or len(task['next_ids'])!=1
                or len(choices)!=2 or len({x[0] for x in choices})!=2 or any(n!=1 for _,n in choices)
                or key in routes):
            raise ValueError('Original master card route disagrees with task/chapter')
        for item_id,_ in choices:
            item=inventory_config.items.get(item_id)
            equipment=inventory_config.equipment.get(item_id)
            roles=inventory_config.equipment_rules.get(item_id,((),()))[0]
            if (item is None or equipment is None or int(item.get('maxNum',1))!=1
                    or (int(item['itemtypeid'])>>4)&15!=0 or int(item.get('needLevel',0))>1
                    or roles and row['character_id'] not in roles):
                raise ValueError('Master choice is not ordinary original equipment')
        equip=resources.definitions[task['next_ids'][0]]
        if equip['type']!=59 or len(equip['next_ids'])!=1 or equip['id'] not in policy['equipment_objective']['tasks']:
            raise ValueError('Unsupported original master equipment successor')
        cart=resources.definitions[equip['next_ids'][0]]
        if cart['type']!=10 or cart['target']['map_id']!=row['home_map_id'] or cart['target']['npc_id']<=0:
            raise ValueError('Original cart-driver successor unavailable')
        routes[key]=MasterCardRoute(*key,row['home_map_id'],task['id'],row['npc_id'],row['card_effect_id'],
            choices,equip['id'],cart['id'])
    if set(routes)!=set(chapter_rules.routes) or {x.equipment_task_id for x in routes.values()}!=set(policy['equipment_objective']['tasks']):
        raise ValueError('Master card43 route coverage mismatch')
    return MasterCardRules(policy['revision'],policy['choice']['timeout_ms'],policy['choice']['binding'],
        MappingProxyType(routes),chapter_rules)


def prepare_master_card_storage(db):
    """Startup-only migration, before accepting connections."""
    db.executescript('''CREATE TABLE IF NOT EXISTS task_master_choices (
        role_id INTEGER NOT NULL REFERENCES roles(id), task_id INTEGER NOT NULL,
        chapter_id TEXT NOT NULL, policy TEXT NOT NULL, route TEXT NOT NULL,
        permit TEXT NOT NULL, selected_item INTEGER, item_key INTEGER,
        PRIMARY KEY(role_id,task_id), UNIQUE(role_id,chapter_id),
        CHECK((selected_item IS NULL AND item_key IS NULL) OR (selected_item>0 AND item_key>0)));''')


@dataclass(frozen=True)
class MasterDialogueTicket:
    chapter_id:str
    task_id:int
    location:Location
    generation:int
    source_id:str
    npc_id:int
    entity_key:int
    deadline_ms:int


@dataclass(frozen=True)
class MasterDialogue:
    ticket:MasterDialogueTicket
    messages:tuple


@dataclass(frozen=True)
class MasterChoice:
    role_id:int
    route:MasterCardRoute
    chapter_id:str
    permit:object
    selected_item:int | None
    item_key:int | None


@dataclass(frozen=True)
class MasterResult:
    choice:MasterChoice | None
    completion:object
    messages:tuple
    replayed:bool=False
    equipment_event:object=None


def _scope(db,account_id,role_id,epoch,resources,rules):
    chapter=read_newbie_chapter(db,account_id,role_id,epoch,rules.chapter_rules)
    if chapter is None or chapter.phase!='completed':
        raise ValueError('Master card needs an explicitly completed newbie chapter')
    actor,state=load_task_state(db,account_id,role_id,epoch)
    origin=chapter.origin.route
    route=rules.routes.get((origin.character_id,origin.school_id))
    school=db.execute('SELECT school FROM roles WHERE id=?',(role_id,)).fetchone()[0]
    if (route is None or origin.successor_task_id!=route.master_task_id
            or resources.shape_to_role_config.get(actor.shape)!=route.character_id or school!=route.school_id
            or origin.intro_task_id not in state.completed):
        raise ValueError('Current master card role disagrees with frozen chapter')
    return actor,state,chapter,route


def _choice(db,role_id,chapter,route,rules):
    row=db.execute('SELECT chapter_id,policy,route,permit,selected_item,item_key FROM task_master_choices '
        'WHERE role_id=? AND task_id=?',(role_id,route.master_task_id)).fetchone()
    if row is None:return None
    if row[0]!=chapter.origin.chapter_id or row[1]!=rules.revision or row[2]!=_json(asdict(route)):
        raise ValueError('Master choice route/policy reconciliation required')
    return MasterChoice(role_id,route,row[0],_freeze(json.loads(row[3])),row[4],row[5])


def read_master_choice(db,account_id,role_id,epoch,resources,rules):
    """Current lease/chapter/character-fenced immutable card choice for callers.

    A pending choice is not receipt/equipment evidence; callers must separately
    require its selected item/key and the appropriate current task states.
    """
    _,_,chapter,route=_scope(db,account_id,role_id,epoch,resources,rules)
    return _choice(db,role_id,chapter,route,rules)


def _clock(now_ms,generation,timeout):
    if (type(now_ms) is not int or not 0<=now_ms<=2**63-1-timeout
            or type(generation) is not int or generation<=0):
        raise ValueError('Trusted master card clock/generation required')


def _ticket_context(ticket,chapter,route,location,epoch,generation,now_ms):
    if (not isinstance(ticket,MasterDialogueTicket) or not isinstance(location,Location)
            or ticket.chapter_id!=chapter.origin.chapter_id or ticket.task_id!=route.master_task_id
            or ticket.location!=location or location.login_epoch!=epoch or location.state!='active'
            or location.role_id!=chapter.origin.role_id or location.address.map_id!=route.home_map_id
            or ticket.generation!=generation or now_ms>=ticket.deadline_ms
            or ticket.npc_id!=route.npc_id or not ticket.source_id or ticket.entity_key<=0):
        raise ValueError('Stale master dialogue authorization')


def open_master_dialogue(db,account_id,role_id,epoch,resources,rules,proof,location,*,generation,now_ms):
    """After map distance validation; return frozen ticket for the role owner."""
    _clock(now_ms,generation,rules.timeout_ms)
    actor,state,chapter,route=_scope(db,account_id,role_id,epoch,resources,rules)
    if (not isinstance(proof,NpcInteraction) or not isinstance(location,Location)
            or proof.kind!='npc_interacted' or proof.position_validation!='bounds_version_distance'
            or proof.address!=location.address or proof.position_version!=location.version
            or location.state!='active'):
        raise ValueError('Stale master NPC interaction')
    if (route.master_task_id not in state.active or proof.role_id!=role_id or proof.login_epoch!=epoch
            or (proof.npc_id,proof.address.map_id)!=(route.npc_id,route.home_map_id)
            or type(proof.source_id) is not str or not 1<=len(proof.source_id)<=160 or proof.entity_key<=0):
        raise ValueError('Wrong master NPC or inactive master task')
    ticket=MasterDialogueTicket(chapter.origin.chapter_id,route.master_task_id,location,generation,
        proof.source_id,proof.npc_id,proof.entity_key,now_ms+rules.timeout_ms)
    bean=ScenarioQuestInfo(route.master_task_id,SCENARIO_READY,0,0,proof.entity_key)
    # Native SAccept ignores an existing bean. Login/intro already sent state0;
    # refresh it before SVisitNpc classifies the task and opens Start dialogue.
    return MasterDialogue(ticket,((S_ACCEPT_SCENARIO_QUEST,encode_accept_scenario_quest(bean)),
        (S_REFRESH_SCENARIO_QUEST_STATE,encode_scenario_state(route.master_task_id,SCENARIO_READY)),
        (S_VISIT_NPC,encode_visit_npc(proof.entity_key,(),(route.master_task_id,)))))


def authorize_master_card(db,account_id,role_id,epoch,resources,rules,ticket,intent,location,*,generation,now_ms):
    """Original Start phase2 ends with CCommit and authorizes the weapon card.

    CQuestDialogEnd belongs to Finish phase3. These Start-only master tasks do
    not emit it, so requiring it leaves the real client waiting after dialogue.
    """
    _clock(now_ms,generation,rules.timeout_ms)
    _,state,chapter,route=_scope(db,account_id,role_id,epoch,resources,rules)
    _ticket_context(ticket,chapter,route,location,epoch,generation,now_ms)
    if intent.task_id!=route.master_task_id or route.master_task_id not in state.active:
        raise ValueError('No active master conversation')
    if (intent.kind!=C_COMMIT_SCENARIO_QUEST or intent.npc_key!=ticket.entity_key or intent.opaque!=0):
        raise ValueError('Master card requires the original Start dialogue commit')
    choice=_choice(db,role_id,chapter,route,rules)
    if choice is not None and choice.item_key is not None:
        raise ValueError('Master choice already committed')
    permit=asdict(ticket)
    # Duplicate commits retain the existing expiry, rather than extending it.
    if choice is None:
        db.execute('INSERT INTO task_master_choices VALUES(?,?,?,?,?,?,NULL,NULL)',
            (role_id,route.master_task_id,chapter.origin.chapter_id,rules.revision,_json(asdict(route)),_json(permit)))
    elif _plain(choice.permit)!=permit:
        db.execute('UPDATE task_master_choices SET permit=? WHERE role_id=? AND task_id=?',
            (_json(permit),role_id,route.master_task_id))
    return ((S_PLAY_CARD_EFFECT,play_card_effect(route.card_effect_id)),)


def _inventory_snapshot(inventory,db,epoch,role_id):
    snapshot=inventory.immutable_snapshot_transaction(db,epoch=epoch)
    if not isinstance(snapshot,InventorySnapshot) or snapshot.role_id!=role_id:
        raise ValueError('Inventory returned a different role snapshot')
    return snapshot


def _activate(db,actor,state,target_id,resources,key):
    if target_id in state.active|state.completed:return ()
    domain=TaskDomain(resources)
    if target_id not in state.offered:
        apply_task_plan(db,actor,domain.plan(actor,state,'offer',target_id),key+':offer')
        actor,state=load_task_state(db,actor.account_id,actor.role_id,actor.login_epoch)
    apply_task_plan(db,actor,domain.plan(actor,state,'accept',target_id),key+':accept')
    return (target_id,)


def _resolve(db,role_id,source,target,*,animation=False):
    row=db.execute('SELECT payload FROM task_effects WHERE role_id=? AND task_id=?',(role_id,source)).fetchone()
    if row is None:raise ValueError('Master task completion effect missing')
    effect=json.loads(row[0])
    effect.update(chain_status='activated',chain_reason='original_master_card_route',chain_target=target,chain_resolved=True)
    if animation:
        effect['continuation_resolved_fields']=sorted(set(effect.get('continuation_resolved_fields',()))|{'ScenarioInfoAnimationID'})
    delivered=update_reward_delivery(effect)
    db.execute('UPDATE task_effects SET payload=?,delivered=? WHERE role_id=? AND task_id=?',
        (_json(effect),int(delivered),role_id,source))


def _started(completion,ids):
    ids=tuple(dict.fromkeys(completion.started_tasks+ids))
    return replace(completion,started_tasks=ids,started_infos=tuple(ScenarioQuestInfo(q,SCENARIO_ACTIVE,0,0,0) for q in ids))


def _current_messages(state,route):
    return tuple((S_ACCEPT_SCENARIO_QUEST,encode_accept_scenario_quest(ScenarioQuestInfo(q,SCENARIO_ACTIVE,0,0,0)))
        for q in (route.master_task_id,route.equipment_task_id,route.cart_task_id) if q in state.active)


def master_resume_messages(db,account_id,role_id,epoch,resources,rules):
    """Current active card/59/cart beans only; reconnect never opens the card.

    Legacy roles and unfinished intro chapters have no master authorization.
    Reading current beans neither extends a pending permit nor replays dialogue.
    """
    chapter=read_newbie_chapter(db,account_id,role_id,epoch,rules.chapter_rules)
    if chapter is None or chapter.phase!='completed':return ()
    _,state,_,route=_scope(db,account_id,role_id,epoch,resources,rules)
    return _current_messages(state,route)


def choose_master_card(db,account_id,role_id,epoch,resources,rules,body,location,inventory,*,generation,now_ms,
                       growth_rules=None,attribute_rules=None,currency_rules=None,pet_experience_rules=None,
                       resource_rules=None,equipment_rules=None):
    """Grant selected bound instance + master complete +59 active, same caller txn.

    Inventory public snapshot uses THIS db; no inventory-private/table access.
    Any exception requires caller rollback. Send returned logical messages after
    commit. A committed duplicate reads current state and never grants again.
    """
    _clock(now_ms,generation,rules.timeout_ms)
    effect,item_id=decode_get_card_item(body)
    actor,state,chapter,route=_scope(db,account_id,role_id,epoch,resources,rules)
    choice=_choice(db,role_id,chapter,route,rules)
    if choice is None or effect!=route.card_effect_id or (item_id,1) not in route.choices:
        raise ValueError('Unsolicited card or illegal original choice')
    current_task_resource_profile(db,actor,inventory,resource_rules,equipment_rules)
    if choice.item_key is not None:
        if choice.selected_item!=item_id or route.master_task_id not in state.completed:
            raise ValueError('Committed master choice differs from request or task')
        messages=inventory.equipment_bag_messages(db,epoch)+_current_messages(state,route)
        return MasterResult(choice,None,messages,True)
    permit=choice.permit
    if (route.master_task_id not in state.active or not isinstance(location,Location)
            or _json(_plain(permit['location']))!=_json(asdict(location))
            or location.role_id!=role_id or location.login_epoch!=epoch or location.state!='active'
            or permit['generation']!=generation or now_ms>=permit['deadline_ms']):
        raise ValueError('Master card session expired or location changed')
    before=_inventory_snapshot(inventory,db,epoch,role_id)
    key=f'master-card:{role_id}:{route.master_task_id}'
    inventory.apply_settlement(db,AssetChange(key,grants=((item_id,1,rules.binding),)))
    after=_inventory_snapshot(inventory,db,epoch,role_id)
    old_keys={i.id for i in before.items}
    created=tuple(i for i in after.items if i.id not in old_keys)
    if (len(created)!=1 or created[0].role_id!=role_id or created[0].template_id!=item_id
            or created[0].quantity!=1 or created[0].binding!=rules.binding or created[0].equipment_slot is not None
            or after.inventory_revision<=before.inventory_revision):
        raise ValueError('Master grant did not produce exactly one new carried equipment instance')
    item_key=created[0].id
    synchronize_task_inventory_source(db,account_id,role_id,epoch,route.master_task_id,inventory,
        resource_rules,equipment_rules,phase='master-card')
    evidence=TaskEvidence(route.master_task_id,role_id,epoch,'master_card_chosen',key,
        route.home_map_id,route.npc_id,route.card_effect_id)
    plan=TaskDomain(resources).plan(actor,state,'complete',route.master_task_id,evidence=evidence)
    complete=complete_task_transaction(db,actor,plan,key+':complete',resources,inventory,
        growth_rules,attribute_rules,currency_rules,pet_experience_rules,
        resource_rules=resource_rules,equipment_rules=equipment_rules)
    actor,state=load_task_state(db,account_id,role_id,epoch)
    started=_activate(db,actor,state,route.equipment_task_id,resources,key+':next')
    _resolve(db,role_id,route.master_task_id,route.equipment_task_id,animation=True)
    db.execute('UPDATE task_master_choices SET selected_item=?,item_key=? WHERE role_id=? AND task_id=?',
        (item_id,item_key,role_id,route.master_task_id))
    complete=_started(complete,started)
    choice=_choice(db,role_id,chapter,route,rules)
    messages=inventory.equipment_bag_messages(db,epoch)+completion_messages(complete)
    return MasterResult(choice,complete,messages)


def reconcile_master_equipment(db,account_id,role_id,epoch,resources,rules,inventory,*,event=None,
                               growth_rules=None,attribute_rules=None,currency_rules=None,pet_experience_rules=None,
                               resource_rules=None,equipment_rules=None):
    """Current exact selected instance in slot0 is the objective, not old intent.

    Run after equip_transaction in the same txn, or as trusted login recovery.
    An EquipmentEvent replay is historical; only the fresh snapshot can satisfy
    recovery. This function never equips, repairs, moves or recreates an item.
    For migrated profiles the caller applies the actual equipment resource
    transition first in this transaction. This function strictly reads that
    current profile and never invents another equipment/source transition.
    """
    actor,state,chapter,route=_scope(db,account_id,role_id,epoch,resources,rules)
    current_task_resource_profile(db,actor,inventory,resource_rules,equipment_rules)
    choice=_choice(db,role_id,chapter,route,rules)
    if choice is None or choice.item_key is None or route.equipment_task_id not in state.active:
        return MasterResult(choice,None,(),True,event)
    current=_inventory_snapshot(inventory,db,epoch,role_id)
    if event is not None and (not isinstance(event,EquipmentEvent) or event.role_id!=role_id
            or not event.replayed and (event.login_epoch!=epoch or event.inventory_revision!=current.inventory_revision)):
        raise ValueError('Equipment event scope/revision mismatch')
    matches=tuple(i for i in current.items if i.id==choice.item_key and i.role_id==role_id
        and i.template_id==choice.selected_item and i.quantity==1 and i.equipment_slot==0)
    if not matches:return MasterResult(choice,None,(),False,event)
    key=f'master-equipped:{role_id}:{route.equipment_task_id}'
    evidence=TaskEvidence(route.equipment_task_id,role_id,epoch,'starter_weapon_equipped',key,
        reference_id=choice.item_key)
    plan=TaskDomain(resources).plan(actor,state,'complete',route.equipment_task_id,evidence=evidence)
    complete=complete_task_transaction(db,actor,plan,key,resources,inventory,
        growth_rules,attribute_rules,currency_rules,pet_experience_rules,
        resource_rules=resource_rules,equipment_rules=equipment_rules)
    actor,state=load_task_state(db,account_id,role_id,epoch)
    started=_activate(db,actor,state,route.cart_task_id,resources,key+':next')
    _resolve(db,role_id,route.equipment_task_id,route.cart_task_id)
    complete=_started(complete,started)
    return MasterResult(choice,complete,completion_messages(complete),False,event)


def equip_master_transaction(db,account_id,role_id,epoch,resources,rules,inventory,item_key,slot,request_id,**reward_rules):
    """Legacy wrapper; migrated callers stage equip/resources then reconcile.

    The equipment resource transition belongs to the equipment command owner,
    outside this wrapper. Reject before mutation rather than applying it twice.
    """
    actor,_,_,_=_scope(db,account_id,role_id,epoch,resources,rules)
    if current_task_resource_profile(db,actor,inventory,reward_rules.get('resource_rules'),
            reward_rules.get('equipment_rules')) is not None:
        raise ValueError('Migrated equipment requires an explicit equipment resource transition then reconcile')
    event=inventory.equip_transaction(db,item_key,slot,epoch,request_id)
    result=reconcile_master_equipment(db,account_id,role_id,epoch,resources,rules,inventory,event=event,**reward_rules)
    return replace(result,messages=inventory.equipment_bag_messages(db,epoch)+result.messages)
