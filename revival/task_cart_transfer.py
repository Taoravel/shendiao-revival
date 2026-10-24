"""First-cart transfer policy, without shared routing or map ownership writes.

Coordinates use the planner's explicit inferred/designed policy, never a claim
that RewardMap fields were proved to be cells by the type56 native consumer.
"""
from dataclasses import dataclass,asdict,replace
import hashlib
import json
from types import MappingProxyType
from inspect_client import OUT
from task_cart_dialogue import CartTransferIntent
from task_master_card import read_master_choice
from task_persistence import load_task_state
from task_domain import TaskDomain,TaskEvidence
from task_rewards import update_reward_delivery
from task_workflow import complete_task_transaction,replay_completed_task_transaction,completion_messages
from task_protocol import S_REFRESH_SCENARIO_QUEST_STATE
from world_transfer_storage import commit_transfer_transaction
from world_owner import TransferCommit,Location
from world_collision import maze_clear,character_movement_mask
from world_catalog import valid_position


def _json(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'))


def _hash(value):
    return hashlib.sha256(_json(value).encode()).hexdigest()


def _policy_fingerprint(policy):
    # Progress reports are documentation, not the durable retry contract.
    # Keep this exclusion explicit: new/changed gameplay fields still fence it.
    progress=('implementation_status','native_gui_verified','live_server_changed')
    return _hash({key:value for key,value in policy.items() if key not in progress})


@dataclass(frozen=True)
class CartTransferRules:
    revision:str
    fingerprint:str
    targets:object


@dataclass(frozen=True)
class ResolvedCartTransfer:
    intent:CartTransferIntent
    target_position:tuple
    policy_revision:str
    policy_fingerprint:str


@dataclass(frozen=True)
class CartTransferResult:
    transfer_id:str
    task_id:int
    target:object
    completion:object
    messages:tuple
    replayed:bool=False


def prepare_cart_transfer_storage(db):
    """Startup-only task receipts; world handoff storage stays in its Module."""
    db.executescript('''CREATE TABLE IF NOT EXISTS task_cart_transfers (
        role_id INTEGER NOT NULL REFERENCES roles(id),task_id INTEGER NOT NULL,
        transfer_id TEXT NOT NULL,chapter_id TEXT NOT NULL,policy TEXT NOT NULL,
        policy_fingerprint TEXT NOT NULL,fingerprint TEXT NOT NULL,intent TEXT NOT NULL,
        world_receipt TEXT NOT NULL,source_event TEXT NOT NULL,
        PRIMARY KEY(role_id,task_id),UNIQUE(transfer_id));''')


def load_cart_transfer_rules(cart,catalog,grids):
    """Startup: original10 route targets, approved conversion and mask1 checks."""
    policy=json.loads((OUT/'design/newbie-cart-transfer-v1.json').read_text(encoding='utf-8'))
    destination=policy['destination']
    if (policy['revision']!='2026-10-23.newbie-cart-transfer.1'
            or set(policy['task_ids'])!=set(cart.routes) or len(policy['task_ids'])!=10
            or destination['map_id']!=1006 or destination['coordinate_scale']!=16
            or destination['coordinate_explanation_status']!='inferred'
            or destination['adopted_conversion_status']!='designed'
            or policy['authorization']['option_index']!=0):
        raise ValueError('Cart transfer policy requires implementation review')
    originals={tuple(p) for p in destination['raw_positions']}
    if originals!={(36,221),(71,242)} or {tuple(p) for p in destination['logical_positions']}!=set(
            (x*destination['coordinate_scale'],y*destination['coordinate_scale']) for x,y in originals):
        raise ValueError('Cart target policy is inconsistent')
    targets={}
    for q,route in cart.routes.items():
        raw=route.destination
        if (raw.coordinate_space!='original_reward_fields_unresolved' or raw.map_id!=destination['map_id']
                or (raw.x,raw.y) not in originals):
            raise ValueError('Original cart route differs from approved target recipe')
        position=(raw.map_id,raw.x*destination['coordinate_scale'],raw.y*destination['coordinate_scale'])
        grid=grids.get(position[0])
        if (not valid_position(position,catalog) or grid is None
                or not maze_clear(grid,*position[1:],mask=character_movement_mask(0))):
            raise ValueError('Approved cart target is unavailable or blocked for normal movement')
        targets[q]=position
    return CartTransferRules(policy['revision'],_policy_fingerprint(policy),MappingProxyType(targets))


def resolve_cart_transfer(intent,cart,rules,*,movement_state):
    """Pure server-selected destination; it grants no completion or map change.

    The actual accepted intent must come from authorize_cart_transfer_transaction.
    The subsequent task/world transaction must revalidate its durable identity.
    """
    if (not isinstance(intent,CartTransferIntent) or type(movement_state) is not int or movement_state!=0):
        raise ValueError('Cart requires an authorized intent and normal movement state0')
    route=cart.routes.get(intent.task_id)
    position=rules.targets.get(intent.task_id)
    if (route is None or position is None or intent.destination!=route.destination
            or intent.route_fingerprint!=route.source_fingerprint
            or type(intent.option_index) is not int or intent.option_index!=0
            or intent.npc_id!=route.npc_id or intent.source.address.map_id!=route.map_id
            or intent.successor_id!=route.successor_id):
        raise ValueError('Cart transfer intent differs from its original approved route')
    return ResolvedCartTransfer(intent,position,rules.revision,rules.fingerprint)


def _scope(db,account_id,role_id,epoch,resources,cart,inventory):
    if inventory.account_id!=account_id or inventory.role_id!=role_id:
        raise ValueError('Cart inventory owner mismatch')
    inventory.immutable_snapshot_transaction(db,epoch=epoch)
    choice=read_master_choice(db,account_id,role_id,epoch,resources,cart.master_rules)
    actor,state=load_task_state(db,account_id,role_id,epoch)
    route=cart.routes.get(choice.route.cart_task_id) if choice is not None else None
    if (choice is None or route is None or choice.selected_item is None or choice.item_key is None
            or choice.route.master_task_id not in state.completed
            or route.equipment_task_id not in state.completed):
        raise ValueError('Cart requires explicit completed chapter, choice and received-instance equipment')
    return actor,state,choice,route


def _receipt(resolved,receipt):
    intent=resolved.intent
    if not isinstance(receipt,TransferCommit):
        raise ValueError('Cart requires the world target loading receipt')
    offer=receipt.frozen.reservation.offer
    frozen=receipt.frozen.source
    target=receipt.location
    if (offer.transfer_id!=intent.request_id or offer.source!=intent.source
            or offer.deadline_ms!=intent.deadline_ms or offer.target_position!=resolved.target_position
            or intent.source.state!='active' or frozen.state!='frozen' or target.state!='loading'
            or frozen!=replace(intent.source,version=intent.source.version+1,state='frozen')
            or target!=replace(frozen,address=receipt.frozen.reservation.target,
                version=frozen.version+1,x=resolved.target_position[1],y=resolved.target_position[2],state='loading')
            or target.address.map_id!=resolved.target_position[0]
            or target.address==intent.source.address):
        raise ValueError('Cart source, target and world transfer receipt differ')
    return offer,target


def cart_completion_messages(completion):
    """Encode after shared final equipment projection, before caller commit.

    Rebuild from the projected completion instead of appending a second full
    attribute map after the common workflow's original bare-growth map.
    """
    messages=completion_messages(completion)
    if completion.replayed:
        messages=tuple((kind,body) for kind,body in messages if kind!=S_REFRESH_SCENARIO_QUEST_STATE)
    return messages


def _result(db,actor,receipt,completion,inventory,*,replayed):
    messages=cart_completion_messages(completion)
    messages=inventory.equipment_bag_messages(db,actor.login_epoch)+messages
    return CartTransferResult(receipt.frozen.reservation.offer.transfer_id,completion.rewards.task_id,
        receipt.location,completion,messages,replayed)


def complete_cart_transfer_transaction(db,account_id,role_id,epoch,resources,cart,rules,intent,receipt,inventory,*,
        generation,now_ms,movement_state,growth_rules=None,attribute_rules=None,currency_rules=None,
        pet_experience_rules=None,resource_rules=None,equipment_rules=None):
    """Compose the public world commit and cart settlement in ONE caller txn.

    Caller already obtained target reservation/source freeze/target loading via
    the map owners. Do not separately commit the world first. This entry calls
    the public world transaction Interface, never copies its SQL or commits.
    Encode final target scene/role snapshot in this same txn before caller commit.
    On failure, caller rolls everything back and fences uncertain memory owners;
    target loading is not evidence that source can safely be resumed.
    """
    if (not isinstance(intent,CartTransferIntent) or not isinstance(intent.source,Location)
            or type(generation) is not int or generation<=0
            or type(intent.generation) is not int or intent.generation!=generation
            or type(now_ms) is not int or not 0<=now_ms<=2**63-1
            or (intent.source.role_id,intent.source.login_epoch)!=(role_id,epoch)
            or type(intent.request_id) is not str or not 1<=len(intent.request_id)<=128
            or type(intent.task_revision) is not int or intent.task_revision<0
            or type(intent.deadline_ms) is not int or not 0<intent.deadline_ms<=2**63-1
            or type(intent.entity_key) is not int or not 0<intent.entity_key<2**63):
        raise ValueError('Current cart owner intent/lease/generation required')
    actor,state,choice,route=_scope(db,account_id,role_id,epoch,resources,cart,inventory)
    if intent.chapter_id!=choice.chapter_id or intent.task_id!=route.task_id:
        raise ValueError('Cart intent differs from current explicit chapter/route')
    resolved=resolve_cart_transfer(intent,cart,rules,movement_state=movement_state)
    _,target=_receipt(resolved,receipt)
    encoded_intent=_json(asdict(intent));encoded_receipt=_json(asdict(receipt))
    fingerprint=_hash((rules.fingerprint,asdict(intent),asdict(receipt)))
    source='newbie-cart:'+fingerprint
    old=db.execute('SELECT transfer_id,chapter_id,policy,policy_fingerprint,fingerprint,intent,world_receipt,source_event '
        'FROM task_cart_transfers WHERE role_id=? AND task_id=?',(role_id,route.task_id)).fetchone()
    expected=(intent.request_id,intent.chapter_id,rules.revision,rules.fingerprint,fingerprint,
        encoded_intent,encoded_receipt,source)
    reward_rules=(growth_rules,attribute_rules,currency_rules,pet_experience_rules)
    if old is not None:
        if tuple(old)!=expected or route.task_id not in state.completed:
            raise ValueError('Cart transfer retry conflicts with durable completion')
        # False proves an exact committed/ready world receipt and performs no
        # position write, even if the role has subsequently moved elsewhere.
        if commit_transfer_transaction(db,account_id,role_id,epoch,receipt):
            raise ValueError('Cart receipt exists without the matching committed world decision')
        effect=db.execute('SELECT payload FROM task_effects WHERE role_id=? AND task_id=?',
            (role_id,route.task_id)).fetchone()
        if effect is None or json.loads(effect[0]).get('source_event')!=source:
            raise ValueError('Cart receipt differs from task evidence')
        completion=replay_completed_task_transaction(db,actor,route.task_id,resources,inventory,*reward_rules,
            resource_rules=resource_rules,equipment_rules=equipment_rules)
        return _result(db,actor,receipt,completion,inventory,replayed=True)
    if (now_ms>=intent.deadline_ms or state.revision!=intent.task_revision
            or route.task_id not in state.active or route.successor_id in state.active|state.completed):
        raise ValueError('Expired or stale cart task/next phase')
    if not commit_transfer_transaction(db,account_id,role_id,epoch,receipt):
        raise ValueError('World was already committed without the atomic cart completion')
    evidence=TaskEvidence(route.task_id,role_id,epoch,'newbie_cart_transfer_committed',source,
        map_id=route.map_id,npc_id=route.npc_id,reference_id=target.address.map_id)
    plan=TaskDomain(resources).plan(actor,state,'complete',route.task_id,evidence=evidence)
    completion=complete_task_transaction(db,actor,plan,intent.request_id,resources,inventory,*reward_rules,
        resource_rules=resource_rules,equipment_rules=equipment_rules)
    if completion.started_tasks!=(route.successor_id,):
        raise ValueError('Cart must activate its unique original Jiaxing successor in the same transaction')
    effect=json.loads(db.execute('SELECT payload FROM task_effects WHERE role_id=? AND task_id=?',
        (role_id,route.task_id)).fetchone()[0])
    effect['continuation_resolved_fields']=sorted(set(effect.get('continuation_resolved_fields',()))|{
        'RewardMapJumpType','RewardMapID','RewardMapXPos','RewardMapYPos'})
    effect['cart_transfer']={'transfer_id':intent.request_id,'policy':rules.revision,
        'policy_fingerprint':rules.fingerprint,'receipt_fingerprint':_hash(asdict(receipt)),
        'status':'durable_target_loading','target':asdict(target),'gui_confirmed':False}
    delivered=update_reward_delivery(effect)
    db.execute('UPDATE task_effects SET payload=?,delivered=? WHERE role_id=? AND task_id=?',
        (json.dumps(effect,ensure_ascii=False),int(delivered),role_id,route.task_id))
    db.execute('INSERT INTO task_cart_transfers VALUES(?,?,?,?,?,?,?,?,?,?)',
        (role_id,route.task_id,*expected))
    return _result(db,actor,receipt,completion,inventory,replayed=False)
