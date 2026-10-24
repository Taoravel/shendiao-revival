"""Current naked growth + explicitly supported equipped starter flat effects.

Pure Module: no SQL, implicit legacy basis, connection, incremental stat writes
or network effects. Callers supply immutable transaction-consistent snapshots.
"""
from dataclasses import dataclass, replace
import json
from types import MappingProxyType
import struct

from inspect_client import OUT
from inventory import InventorySnapshot, ItemState
from equipment_condition import EquipmentCondition
from equipment_detail import EquipmentDetail
from role_attribute_storage import RoleAttributeSnapshot
from role_attributes import RoleAttributes
from item_effects import VitalState
from role_resource_plan import ResourceProjection,ResourceCaps,RoleResources


def _number(value, minimum=0):
    if type(value) is not int or not minimum <= value <= 0x7fffffff:
        raise ValueError('Invalid or overflowing equipment attribute integer')
    return value


def _role(value):
    if type(value) is not int or not 0 < value < 2**63:
        raise ValueError('Invalid equipment attribute role')


@dataclass(frozen=True)
class EquipmentAttributeBasis:
    role_id: int
    character_id: int
    revision: int
    policy: str
    seal_strength: int
    source_id: str
    seal_resistance: int | None = None

    def __post_init__(self):
        _role(self.role_id)
        if type(self.character_id) is not int or not 1 <= self.character_id <= 10:
            raise ValueError('Original character configuration ID required')
        _number(self.revision)
        _number(self.seal_strength)
        if self.seal_resistance is not None:_number(self.seal_resistance)
        if (type(self.policy) is not str or not self.policy
                or type(self.source_id) is not str or not 1 <= len(self.source_id) <= 160):
            raise ValueError('Explicit equipment attribute provenance required')


@dataclass(frozen=True)
class StarterEffect:
    allowed_characters: tuple
    modifiers: tuple
    slot: int = 0
    minimum_level: int = 1
    sex: int = 0
    suiting: int = 0


@dataclass(frozen=True)
class EquipmentAttributeRules:
    revision: str
    attribute_policy: str
    flat_mapping: object
    templates: object
    new_role_seal_strength: int
    shape_characters: object
    new_role_seal_resistance: int | None = None
    character_sexes: object = None


@dataclass(frozen=True)
class EquipmentTotals:
    """Current final attributes and their source; no fabricated vital state."""
    attributes: RoleAttributes
    inventory_revision: int
    equipment_basis_revision: int
    equipment_policy: str
    seal_strength: int
    seal_resistance: int | None = None


@dataclass(frozen=True)
class EquipmentRoleSnapshot(RoleAttributeSnapshot):
    inventory_revision: int
    equipment_basis_revision: int
    equipment_policy: str
    seal_strength: int
    seal_resistance: int | None = None


def resource_caps_from_projection(snapshot):
    """Typed caps from a trusted final total, never from client maxima."""
    if type(snapshot) not in (EquipmentTotals,EquipmentRoleSnapshot):
        raise ValueError('Current final equipment projection required for resource caps')
    a=snapshot.attributes
    source=ResourceProjection(a.role_id,a.baseline_revision,a.growth_revision,a.policy_revision,
        snapshot.inventory_revision,snapshot.equipment_basis_revision,snapshot.equipment_policy)
    return ResourceCaps(source,a.hp_max,a.mp_max)


def combine_equipment_resources(totals,resources):
    """Combine final stats with the sole current resource state; no adjustment.

    A pending asset/growth change must first settle its resource transition in
    the caller transaction. Reading this profile never heals or clips HP/MP.
    """
    if (type(totals) is not EquipmentTotals or type(resources) is not RoleResources
            or resources.caps!=resource_caps_from_projection(totals)):
        raise ValueError('Final stats and resources must share exact caps and source')
    vitals=VitalState(totals.attributes.role_id,resources.version,resources.hp,
        resources.caps.hp_max,resources.mp,resources.caps.mp_max)
    return EquipmentRoleSnapshot(totals.attributes,vitals,totals.inventory_revision,
        totals.equipment_basis_revision,totals.equipment_policy,totals.seal_strength,totals.seal_resistance)


def load_equipment_attribute_rules():
    """Startup-only load; validate the exact original scope before commands."""
    policy = json.loads((OUT/'design/role-equipment-v1.json').read_text(encoding='utf-8'))
    mapping = {int(key): value for key, value in policy['flat_mapping'].items()}
    identifiers = tuple(policy['template_ids'])
    if (policy['revision'] != '2026-10-23.role-equipment.1'
            or mapping != {81: 80, 811: 810, 1231: 1230}
            or identifiers != tuple(range(49001,49011))
            or policy['sealing_basis']['new_restoration_role'] != 0
            or policy['sealing_basis']['growth_per_level'] != 0):
        raise ValueError('Equipment attribute policy requires implementation review')
    descriptions = json.loads((OUT/'catalogs/knight.gsp.item.cattributedesconfig.json').read_text(encoding='utf-8'))
    families = {int(row['attributes']['id']): row['attributes'] for row in descriptions}
    if any(int(families[target]['numid']) != source for source, target in mapping.items()):
        raise ValueError('Equipment attribute mapping disagrees with original descriptions')
    rows = json.loads((OUT/'catalogs/knight.gsp.item.cequipeffect.json').read_text(encoding='utf-8'))
    templates = {}
    for row in rows:
        template = int(row['attributes']['id'])
        if template not in identifiers:
            continue
        fields = row['lists']
        kinds, values = tuple(map(int, fields['baseEffectType'])), tuple(map(int, fields['baseEffect']))
        allowed = tuple(map(int, fields['roleNeed']))
        if (kinds != (81,811,1231) or values != (25,15,8) or not allowed
                or len(set(allowed)) != len(allowed) or any(not 1 <= item <= 10 for item in allowed)):
            raise ValueError('Starter weapon source needs explicit policy reconciliation')
        templates[template] = StarterEffect(allowed, tuple(zip(kinds,values)))
    if set(templates) != set(identifiers):
        raise ValueError('Missing original starter weapon effects')
    characters = json.loads((OUT/'catalogs/knight.gsp.role.createroleconfig.json').read_text(encoding='utf-8'))
    shapes = {int(row['attributes'][color]): int(row['attributes']['id'])
              for row in characters for color in ('color1','color2','color3')}
    if len(shapes) != 30 or set(shapes.values()) != set(range(1,11)):
        raise ValueError('Equipment basis requires original character/shape mappings')
    return EquipmentAttributeRules(policy['revision'], policy['attribute_policy'],
        MappingProxyType(mapping), MappingProxyType(templates), policy['sealing_basis']['new_restoration_role'],
        MappingProxyType(shapes))


def load_ordinary_equipment_attribute_rules():
    """Explicit startup v2; default v1 and existing stored bases stay unchanged.

    Keep original eligibility/set metadata. Nonzero sets, unknown effects and
    advanced instances are not silently flattened into a complete role total.
    """
    policy=json.loads((OUT/'design/role-equipment-v2.json').read_text(encoding='utf-8'))
    mapping={int(key):value for key,value in policy['flat_mapping'].items()}
    expected={81:80,101:100,111:110,121:120,131:130,141:140,151:150,
        811:810,821:820,1231:1230,1241:1240}
    if (policy['revision']!='2026-10-23.role-equipment.2' or mapping!=expected
            or policy['attribute_policy']!='2026-10-23.attributes.1'
            or policy['expected_templates']!=973 or policy['expected_suiting_deferred']!=212
            or any(policy['sealing_basis'][key]!=0 for key in (
                'new_restoration_role_strength','new_restoration_role_resistance','growth_per_level'))):
        raise ValueError('Ordinary equipment policy requires implementation review')
    def rows(name):
        return json.loads((OUT/f'catalogs/knight.gsp.{name}.json').read_text(encoding='utf-8'))
    families={int(row['attributes']['id']):row['attributes'] for row in rows('item.cattributedesconfig')}
    if any(int(families[target]['numid'])!=source for source,target in mapping.items()):
        raise ValueError('Ordinary flat mappings disagree with original descriptions')
    items={int(row['attributes']['id']):row['attributes'] for row in rows('item.citemattr')}
    gods={int(row['attributes']['id']) for row in rows('item.cgodweapon')}
    templates={}
    for row in rows('item.cequipeffect'):
        attributes,fields=row['attributes'],row['lists']
        key=int(attributes['id']);item=items[key];kind=int(item['itemtypeid']);slot=(kind>>4)&15
        if key in gods or kind&15!=8 or not 0<=slot<=5:continue
        kinds=tuple(map(int,fields.get('baseEffectType',())))
        values=tuple(map(int,fields.get('baseEffect',())))
        if len(values)>len(kinds) and all(v==0 for v in values[len(kinds):]):values=values[:len(kinds)]
        if len(kinds)!=len(values):raise ValueError('Ordinary base effect length mismatch')
        if not kinds or any(key not in mapping for key in kinds):continue
        allowed=tuple(map(int,fields.get('roleNeed',())))
        sex=int(attributes['sexNeed']);minimum=int(item['needLevel']);suiting=int(attributes['suiting'])
        if (len(set(kinds))!=len(kinds) or any(type(v) is not int or v<=0 for v in values)
                or len(set(allowed))!=len(allowed) or any(not 1<=v<=0x7fffffff for v in allowed)
                or sex not in (0,1,2) or not 0<=minimum<=0x7fffffff or not 0<=suiting<=0x7fffffff
                or slot!=0 and allowed):
            raise ValueError('Ordinary source eligibility or base effects require reconciliation')
        templates[key]=StarterEffect(allowed,tuple(zip(kinds,values)),slot,minimum,sex,suiting)
    if len(templates)!=973 or sum(t.suiting!=0 for t in templates.values())!=212:
        raise ValueError('Ordinary flat/set template scope changed')
    shapes,sexes={},{}
    for row in rows('role.createroleconfig'):
        attrs=row['attributes'];character=int(attrs['id'])
        for color in ('color1','color2','color3'):
            shape=int(attrs[color]);remainder=shape%10
            if (remainder or 10)!=character:raise ValueError('Original character/shape identity changed')
            sex=1 if 1<=remainder<=5 else 2
            if character in sexes and sexes[character]!=sex:raise ValueError('Original shape sex mismatch')
            shapes[shape]=character;sexes[character]=sex
    if len(shapes)!=30 or set(sexes)!=set(range(1,11)):
        raise ValueError('Original ordinary character/sex mappings required')
    return EquipmentAttributeRules(policy['revision'],policy['attribute_policy'],MappingProxyType(mapping),
        MappingProxyType(templates),0,MappingProxyType(shapes),0,MappingProxyType(sexes))


def load_equipment_attribute_policies():
    """Startup-only available policies; loading does not select or upgrade roles."""
    policies=(load_equipment_attribute_rules(),load_ordinary_equipment_attribute_rules())
    return MappingProxyType({rules.revision:rules for rules in policies})


def project_equipment(growth_snapshot, inventory_snapshot, basis, rules):
    """Recompute one immutable final snapshot, never re-project a prior total.

    Caller reads both snapshots and the explicit basis in its fenced role
    transaction, validates encoding, commits, then publishes this result. A
    missing/unsupported modifier is an error, not permission to drop a stat.
    """
    if type(growth_snapshot) is not RoleAttributeSnapshot:
        raise ValueError('Plain naked growth and explicit immutable equipment inputs required')
    if type(rules) is not EquipmentAttributeRules or rules.revision!='2026-10-23.role-equipment.1':
        raise ValueError('Ordinary equipment requires resource-aware totals and combination')
    attrs, vitals = growth_snapshot.attributes, growth_snapshot.vitals
    if (vitals.target_id != attrs.role_id
            or (vitals.max_hp,vitals.max_mp) != (attrs.hp_max,attrs.mp_max)):
        raise ValueError('Equipment projection role, basis, policy or vital scope mismatch')
    totals=project_equipment_totals(attrs,inventory_snapshot,basis,rules)
    return EquipmentRoleSnapshot(totals.attributes,vitals,totals.inventory_revision,
        totals.equipment_basis_revision,totals.equipment_policy,totals.seal_strength,totals.seal_resistance)


def project_equipment_totals(attrs,inventory_snapshot,basis,rules):
    """Compute final stats from current naked attributes, never from resources.

    Caller supplies the persisted naked result and same-transaction assets.
    This Interface has no HP/MP values or resource cap transition side effects.
    """
    if (type(attrs) is not RoleAttributes or type(inventory_snapshot) is not InventorySnapshot
            or type(basis) is not EquipmentAttributeBasis or type(rules) is not EquipmentAttributeRules):
        raise ValueError('Naked attributes and immutable current equipment inputs required')
    if (attrs.role_id != inventory_snapshot.role_id or attrs.role_id != basis.role_id
            or attrs.policy_revision != rules.attribute_policy or basis.policy != rules.revision):
        raise ValueError('Equipment totals role, basis or policy mismatch')
    ordinary=rules.revision=='2026-10-23.role-equipment.2'
    if (not ordinary and rules.revision!='2026-10-23.role-equipment.1'
            or ordinary and (basis.seal_resistance is None or rules.new_role_seal_resistance is None)
            or not ordinary and basis.seal_resistance is not None):
        raise ValueError('Explicit equipment policy and known sealing resistance basis required')
    _role(attrs.role_id)
    _number(inventory_snapshot.inventory_revision)
    if type(inventory_snapshot.items) is not tuple:
        raise ValueError('Immutable current inventory items required')
    names={80:'physical_attack',100:'physical_defense',110:'hit',120:'dodge',130:'speed',
        140:'hp_max',150:'mp_max',810:'magic_attack',820:'magic_defense'}
    totals={key:_number(getattr(attrs,name),1 if key==140 else 0) for key,name in names.items()}
    totals[1230]=basis.seal_strength
    if ordinary:totals[1240]=basis.seal_resistance
    seen, slots = set(), set()
    for item in inventory_snapshot.items:
        if type(item) is not ItemState or item.role_id != attrs.role_id:
            raise ValueError('Foreign or mutable inventory item in equipment projection')
        _number(item.id,1)
        if item.id in seen:
            raise ValueError('Duplicate inventory instance in equipment projection')
        seen.add(item.id)
        if item.equipment_slot is None:
            continue
        _number(item.template_id,1)
        if (type(item.equipment_slot) is not int or not 0<=item.equipment_slot<=(5 if ordinary else 0)
                or item.equipment_slot in slots or type(item.quantity) is not int or item.quantity != 1
                or type(item.slot) is not int or item.slot != (-item.equipment_slot-1 if ordinary else -1)
                or item.quality is not None or type(item.condition) is not EquipmentCondition):
            raise ValueError('Unsupported equipped slot, quantity, quality or missing condition')
        slots.add(item.equipment_slot)
        template = rules.templates.get(item.template_id)
        if (template is None or item.equipment_slot!=template.slot
                or (template.allowed_characters and (not ordinary or template.slot==0)
                    and basis.character_id not in template.allowed_characters)):
            raise ValueError('Unsupported or incompatible equipped starter template')
        if ordinary and (attrs.level<template.minimum_level or template.suiting!=0
                or template.sex and rules.character_sexes.get(basis.character_id)!=template.sex):
            raise ValueError('Equipment level, sex or unresolved set semantics refuse projection')
        if (type(item.detail) is not EquipmentDetail or item.detail.identified != 1
                or item.detail.base_properties != template.modifiers):
            raise ValueError('Explicit identified clean starter detail required; unknown modifiers cannot be dropped')
        if ordinary and (item.detail.prefix_quality,item.detail.score,item.condition.color_tier)!=(1,0,1):
            raise ValueError('Only explicit clean ordinary prefix1/score0/color1 is restored')
        if item.condition.current == 0:
            continue
        for modifier, value in template.modifiers:
            target = rules.flat_mapping.get(modifier)
            if target is None:
                raise ValueError('Unknown equipment modifier family')
            totals[target] = _number(totals[target] + value)
    for value in (totals.values() if ordinary else (totals[80],totals[810],totals[1230])):
        if struct.unpack('>f', struct.pack('>f',value))[0] != value:
            raise ValueError('Final equipment attribute cannot be represented exactly by native float32')
    projected = replace(attrs,**{name:totals[key] for key,name in names.items()})
    return EquipmentTotals(projected, inventory_snapshot.inventory_revision,
        basis.revision, rules.revision, totals[1230],totals.get(1240))
