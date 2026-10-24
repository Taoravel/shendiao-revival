"""Frozen NPC495 admission and current, read-only role inventory state.

The native local menu sends c04cc directly. No preceding CNpcService495 or
identification settlement is invented. Shared callers own modal-state checks,
fresh map proof and final full-scene/connection delivery fences.
"""
from collections.abc import Mapping
from contextlib import closing
from dataclasses import dataclass
import json
from pathlib import Path
import time
from inspect_client import OUT
from equipment_detail import DetailRules,EquipmentDetail
from npc_services import NpcServices
from npc_identification_protocol import (QUERY_IDENTIFICATION,IDENTIFICATION_STATES,
    decode_identification_query,encode_identification_states)
from world_npcs import NpcInteraction
from world_owner import MapAddress,Location


@dataclass(frozen=True)
class IdentificationQueryRules:
    revision: str
    npc_id: int
    map_id: int
    placement_id: int
    placement_position: tuple
    service_id: int
    handler: str
    mode: int
    max_items: int
    detail_rules: DetailRules

    def __post_init__(self):
        numbers=(self.npc_id,self.map_id,self.placement_id,self.service_id,self.mode,self.max_items)
        if (self.revision!='2026-10-24.npc-identification-query.1'
                or any(type(value) is not int for value in numbers)
                or numbers!=(10890,1007,75,495,1,128)
                or self.handler!='equipment.identification.query'
                or type(self.placement_position) is not tuple
                or any(type(value) is not int for value in self.placement_position)
                or self.placement_position!=(3972,5299)
                or type(self.detail_rules) is not DetailRules
                or self.detail_rules.revision!='2026-10-23.equipment-detail.1'
                or not self.detail_rules.templates):
            raise ValueError('Explicit supported frozen NPC identification query policy required')


def load_query_rules(placements,definitions,services,detail_rules,*,path=None):
    """Startup only; validate original sources without changing global services."""
    policy=json.loads((Path(path) if path is not None else OUT/'design/npc-identification-query-v1.json')
        .read_text(encoding='utf-8'))
    if type(policy) is not dict or type(policy.get('placement_position')) is not list:
        raise ValueError('Invalid NPC identification query policy structure')
    wire=(policy.get('request_type'),policy.get('response_type'),policy.get('key_minimum'),policy.get('key_maximum'))
    if any(type(value) is not int for value in wire) or wire!=(QUERY_IDENTIFICATION,IDENTIFICATION_STATES,1,2**31-1):
        raise ValueError('Unsupported NPC identification query wire contract')
    rules=IdentificationQueryRules(*(policy.get(key) for key in
        ('revision','npc_id','map_id','placement_id')),tuple(policy['placement_position']),
        *(policy.get(key) for key in ('service_id','handler','mode','max_items')),detail_rules)
    if (not isinstance(placements,Mapping) or not isinstance(definitions,Mapping)
            or type(services) is not NpcServices or services.labels.get(rules.service_id)!='鉴定装备'):
        raise ValueError('Current original NPC/service snapshots required')
    rows=tuple(p for p in placements.get(rules.map_id,()) if p.placement_id==rules.placement_id)
    definition=definitions.get(rules.npc_id)
    if (len(rows)!=1 or any(type(value) is not int for value in
            (rows[0].map_id,rows[0].placement_id,rows[0].npc_id,rows[0].x,rows[0].y))
            or (rows[0].map_id,rows[0].npc_id,rows[0].x,rows[0].y)!=(
            rules.map_id,rules.npc_id,*rules.placement_position)
            or not isinstance(definition,Mapping) or str(definition.get('id'))!=str(rules.npc_id)):
        raise ValueError('Exact original identification NPC definition and placement required')
    return rules


def prepare(accounts,*,path=None):
    """After NPC/gameplay/inventory preparation, before role admission."""
    resources=getattr(accounts,'npc_resources',None)
    gameplay=getattr(accounts,'npc_gameplay',None);config=getattr(accounts,'inventory_config',None)
    if type(resources) is not tuple or len(resources)!=2 or gameplay is None or config is None:
        raise ValueError('NPC and inventory startup preparation must precede identification query')
    rules=load_query_rules(*resources,getattr(gameplay,'services',None),getattr(config,'detail_rules',None),path=path)
    accounts.npc_identification_query_rules=rules
    return rules


@dataclass(frozen=True)
class IdentificationQueryIntent:
    rules: IdentificationQueryRules
    proof: NpcInteraction
    location: Location
    inventory_revision: int
    item_keys: tuple
    deadline_ms: int


def _admit(rules,proof,current,deadline_ms,now_ms):
    if (type(rules) is not IdentificationQueryRules or type(proof) is not NpcInteraction
            or type(current) is not Location or type(current.address) is not MapAddress
            or type(proof.address) is not MapAddress
            or type(deadline_ms) is not int or type(now_ms) is not int or not 0<=now_ms<deadline_ms
            or type(proof.source_id) is not str or not 1<=len(proof.source_id)<=128
            or any(type(value) is not int or value<0 for value in
                (current.role_id,current.version,current.x,current.y,current.address.map_id,
                 current.address.instance_id,current.address.partition_id))
            or current.role_id==0 or current.address.instance_id==0
            or any(type(value) is not int for value in
                (proof.role_id,proof.position_version,proof.npc_id,proof.placement_id,
                 proof.address.map_id,proof.address.instance_id,proof.address.partition_id))
            or not ((type(current.login_epoch) is str and 1<=len(current.login_epoch)<=128)
                or (type(current.login_epoch) is int and 0<current.login_epoch<2**63))
            or type(proof.login_epoch) is not type(current.login_epoch)
            or current.state!='active' or proof.kind!='npc_interacted'
            or proof.position_validation!='bounds_version_distance'
            or (proof.role_id,proof.login_epoch,proof.address,proof.position_version)!=(
                current.role_id,current.login_epoch,current.address,current.version)
            or (proof.npc_id,proof.placement_id,current.address.map_id)!=(rules.npc_id,rules.placement_id,rules.map_id)
            or type(proof.entity_key) is not int or not 0<=proof.entity_key<2**63):
        raise ValueError('Stale or unsupported current NPC identification query scope')


def plan_query(body,proof,current,inventory_revision,*,rules,now_ms,deadline_ms):
    """Called after a fresh owning-map proof and the role's modal-state gate."""
    _admit(rules,proof,current,deadline_ms,now_ms)
    query=decode_identification_query(body,max_items=rules.max_items)
    if (type(inventory_revision) is not int or inventory_revision<0
            or query.npc_key!=proof.entity_key or query.mode!=rules.mode
            or any(not 0<key<2**31 for key in query.item_keys)):
        raise ValueError('Identification query identity, mode or asset version mismatch')
    return IdentificationQueryIntent(rules,proof,current,inventory_revision,query.item_keys,deadline_ms)


def query_states(inventory,intent):
    """Bounded role I/O: read current known flags, never initialize or settle.

    The caller owns the supplied proof's freshness and must fence the logical
    reply again at actual sending. This returns no authorization for c4276.
    """
    if type(intent) is not IdentificationQueryIntent:
        raise ValueError('Frozen identification query intent required')
    _admit(intent.rules,intent.proof,intent.location,intent.deadline_ms,int(time.monotonic()*1000))
    rules=intent.rules
    if ((intent.proof.role_id,intent.proof.login_epoch)!=(inventory.role_id,inventory.epoch)
            or inventory.detail_rules is not rules.detail_rules
            or type(intent.inventory_revision) is not int or intent.inventory_revision<0
            or type(intent.item_keys) is not tuple or len(intent.item_keys)>rules.max_items
            or any(type(key) is not int or not 0<key<2**31 for key in intent.item_keys)):
        raise ValueError('Identification query owner, profile or item budget mismatch')
    with closing(inventory.accounts.connect()) as db:
        db.execute('PRAGMA query_only=ON')
        db.execute('BEGIN')
        snapshot=inventory.immutable_snapshot_transaction(db)
        if snapshot.inventory_revision!=intent.inventory_revision:
            raise ValueError('Stale identification inventory revision')
        items={item.id:item for item in snapshot.items}
        states=[]
        for key in intent.item_keys:
            item=items.get(key)
            if (item is None or item.role_id!=inventory.role_id or item.quantity!=1
                    or item.equipment_slot is not None or item.template_id not in rules.detail_rules.templates
                    or type(item.detail) is not EquipmentDetail or item.detail.identified not in (0,1)):
                raise ValueError('Identification query requires current owned carried known ordinary details')
            states.append((key,item.detail.identified))
        body=encode_identification_states(intent.proof.entity_key,tuple(states),rules.mode,max_items=rules.max_items)
        _admit(rules,intent.proof,intent.location,intent.deadline_ms,int(time.monotonic()*1000))
        return ((IDENTIFICATION_STATES,body),)
