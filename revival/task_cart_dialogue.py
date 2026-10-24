"""Trusted original cart menu and immutable, coordinate-unresolved travel intent.

This Module authorizes no position writes, quest completion or reward. World
policy must resolve the original coordinate units and join durable transfer and
task completion before an intent may become an actual handoff.
"""
from dataclasses import dataclass
import hashlib
import json
from types import MappingProxyType
from uuid import uuid4
from tasks import _plain
from task_master_card import read_master_choice
from task_persistence import load_task_state
from task_domain import supports_native_effect_dialogue
from task_protocol import (C_COMMIT_SCENARIO_QUEST,ScenarioQuestInfo,S_ACCEPT_SCENARIO_QUEST,
    encode_accept_scenario_quest,S_REFRESH_SCENARIO_QUEST_STATE,encode_scenario_state,SCENARIO_READY)
from task_dialog_protocol import S_VISIT_NPC,encode_visit_npc
from task_session import TaskIntent
from world_owner import Location
from world_npcs import NpcInteraction


@dataclass(frozen=True)
class RawCartDestination:
    map_id:int
    x:int
    y:int
    coordinate_space:str='original_reward_fields_unresolved'


@dataclass(frozen=True)
class CartRoute:
    task_id:int
    equipment_task_id:int
    map_id:int
    npc_id:int
    branch_npc_id:int
    options:tuple
    destination:RawCartDestination
    successor_id:int
    source_fingerprint:str


@dataclass(frozen=True)
class CartResources:
    routes:object
    master_rules:object


def load_cart_resources(resources,master_rules):
    """Startup: original10, including the unchanged Shaolin BranchNpc mismatch."""
    result={}
    for master in master_rules.routes.values():
        task=resources.definitions[master.cart_task_id]
        a=task['attributes'];options=tuple(task['lists'].get('ScenarioInfoBranchOptionList',()))
        if (task['type']!=10 or len(task['dialogue']['start'])!=2 or task['dialogue']['finish']
                or len(options)!=1 or not a.get('ScenarioInfoBranchNote')
                or int(a.get('ScenarioInfoAnimationID',0))!=0 or int(a.get('ProcessBarTime',0))!=0
                or int(a.get('RewardMapJumpType',0))!=1 or int(a.get('RewardMapID',0))!=1006
                or task['target']['map_id']!=master.home_map_id or task['target']['npc_id']<=0
                or len(task['next_ids'])!=1
                or not supports_native_effect_dialogue(resources.definitions[task['next_ids'][0]])):
            raise ValueError('Original cart menu route requires implementation review')
        fingerprint=hashlib.sha256(json.dumps(_plain(task),sort_keys=True,separators=(',',':')).encode()).hexdigest()
        route=CartRoute(task['id'],master.equipment_task_id,task['target']['map_id'],task['target']['npc_id'],
            int(a['ScenarioInfoBranchNpcID']),options,
            RawCartDestination(int(a['RewardMapID']),int(a['RewardMapXPos']),int(a['RewardMapYPos'])),
            task['next_ids'][0],fingerprint)
        if route.task_id in result and result[route.task_id]!=route:
            raise ValueError('Character-specific original cart route conflict')
        result[route.task_id]=route
    if len(result)!=10:
        raise ValueError('Original cart10 coverage mismatch')
    return CartResources(MappingProxyType(result),master_rules)


@dataclass(frozen=True)
class CartDialogueTicket:
    task_id:int
    chapter_id:str
    location:Location
    generation:int
    task_revision:int
    npc_id:int
    entity_key:int
    source_id:str
    request_id:str
    deadline_ms:int
    route_fingerprint:str


@dataclass(frozen=True)
class CartDialogue:
    ticket:CartDialogueTicket
    messages:tuple


@dataclass(frozen=True)
class CartTransferIntent:
    request_id:str
    task_id:int
    chapter_id:str
    source:Location
    generation:int
    task_revision:int
    npc_id:int
    entity_key:int
    option_index:int
    destination:RawCartDestination
    successor_id:int
    deadline_ms:int
    route_fingerprint:str


def _scope(db,account_id,role_id,epoch,resources,cart):
    choice=read_master_choice(db,account_id,role_id,epoch,resources,cart.master_rules)
    actor,state=load_task_state(db,account_id,role_id,epoch)
    route=cart.routes.get(choice.route.cart_task_id) if choice is not None else None
    if (choice is None or choice.item_key is None or choice.selected_item is None or route is None
            or choice.route.master_task_id not in state.completed
            or route.equipment_task_id not in state.completed or route.task_id not in state.active):
        raise ValueError('Cart requires the completed explicit master/received-equipment chain')
    return actor,state,choice,route


def _clock(generation,now_ms):
    if type(generation) is not int or generation<=0 or type(now_ms) is not int or not 0<=now_ms<=2**63-1:
        raise ValueError('Trusted cart command generation/clock required')


def open_cart_dialogue_transaction(db,account_id,role_id,epoch,resources,cart,proof,location,*,
                                   generation,now_ms,deadline_ms):
    """Validated actual ActiveNpc; BranchNpc is preserved source, not substituted.

    Caller publishes only this frozen ticket to its role owner after committing
    the read transaction. Deadline is supplied by the integration's NPC policy;
    this Module invents neither a new timeout nor a destination conversion.
    """
    _clock(generation,now_ms)
    _,state,choice,route=_scope(db,account_id,role_id,epoch,resources,cart)
    if (not isinstance(proof,NpcInteraction) or not isinstance(location,Location)
            or type(deadline_ms) is not int or not now_ms<deadline_ms<=2**63-1
            or proof.kind!='npc_interacted' or proof.position_validation!='bounds_version_distance'
            or (proof.role_id,proof.login_epoch)!=(role_id,epoch)
            or (location.role_id,location.login_epoch)!=(role_id,epoch) or location.state!='active'
            or location.address!=proof.address or location.version!=proof.position_version
            or (proof.npc_id,proof.address.map_id)!=(route.npc_id,route.map_id)
            or type(proof.entity_key) is not int or not 0<proof.entity_key<2**63
            or type(proof.source_id) is not str or not 1<=len(proof.source_id)<=160):
        raise ValueError('Wrong or stale cart NPC interaction')
    request_id=f'quest-cart:{role_id}:{route.task_id}:{uuid4().hex}'
    ticket=CartDialogueTicket(route.task_id,choice.chapter_id,location,generation,state.revision,route.npc_id,
        proof.entity_key,proof.source_id,request_id,deadline_ms,route.source_fingerprint)
    bean=ScenarioQuestInfo(route.task_id,SCENARIO_READY,0,0,proof.entity_key)
    # Cart is already active in the client. Duplicate acceptance cannot change
    # its state; the explicit refresh must precede native menu classification.
    return CartDialogue(ticket,((S_ACCEPT_SCENARIO_QUEST,encode_accept_scenario_quest(bean)),
        (S_REFRESH_SCENARIO_QUEST_STATE,encode_scenario_state(route.task_id,SCENARIO_READY)),
        (S_VISIT_NPC,encode_visit_npc(proof.entity_key,(),(route.task_id,)))))


def authorize_cart_transfer_transaction(db,account_id,role_id,epoch,resources,cart,ticket,intent,location,*,
                                        generation,now_ms):
    """Return raw server-chosen travel intent only; no grant/complete/move/send.

    Retrying the same frozen ticket keeps request_id for the world's journal.
    It still needs destination-policy resolution and a durable handoff receipt.
    Wire option0 does not prove the human finished reading the local dialogue.
    """
    _clock(generation,now_ms)
    _,state,choice,route=_scope(db,account_id,role_id,epoch,resources,cart)
    if (not isinstance(ticket,CartDialogueTicket) or not isinstance(intent,TaskIntent)
            or not isinstance(location,Location) or ticket.location!=location
            or (location.role_id,location.login_epoch)!=(role_id,epoch) or location.state!='active'
            or ticket.chapter_id!=choice.chapter_id or ticket.task_id!=route.task_id
            or ticket.generation!=generation or ticket.task_revision!=state.revision
            or ticket.npc_id!=route.npc_id or location.address.map_id!=route.map_id
            or ticket.route_fingerprint!=route.source_fingerprint or now_ms>=ticket.deadline_ms
            or intent.kind!=C_COMMIT_SCENARIO_QUEST or intent.task_id!=route.task_id
            or intent.npc_key!=ticket.entity_key or type(intent.opaque) is not int or intent.opaque!=0):
        raise ValueError('Cart branch needs current original option0/NPC/task authorization')
    return CartTransferIntent(ticket.request_id,route.task_id,choice.chapter_id,location,generation,state.revision,
        route.npc_id,ticket.entity_key,0,route.destination,route.successor_id,ticket.deadline_ms,route.source_fingerprint)
