"""Complete ordinary worn gem projection, separate from canonical base effects.

No persistence, resource values, implicit baselines or publication. The root's
ordinary projection is reused only for its canonical base component; final
totals carry the distinct gem policy and preserve all six additional fields.
"""
from dataclasses import dataclass,replace
import json
import struct
from types import MappingProxyType
from inspect_client import OUT
from inventory import InventorySnapshot,ItemState
from equipment_gems import GemRules,validate_equipment
from equipment_gem_storage import EquipmentGemBasis
from equipment_gem_score import GemScoreRules,GemScoreBasis,validate_current
from equipment_condition import EquipmentRules
from role_attributes import RoleAttributes
from role_equipment import (EquipmentAttributeBasis,EquipmentTotals,
    load_ordinary_equipment_attribute_rules,project_equipment_totals)


EXTRA_IDS=(350,360,370,380,1130,1530)
CORE_NAMES=MappingProxyType({80:'physical_attack',100:'physical_defense',110:'hit',120:'dodge',130:'speed',
    140:'hp_max',810:'magic_attack',820:'magic_defense'})


def _native(value,*,signed=False):
    if (type(value) is not int or not (-0x80000000 if signed else 0)<=value<=0x7fffffff
            or struct.unpack('>f',struct.pack('>f',value))[0]!=value):
        raise ValueError('Gem role value must be an exactly representable native integer')
    return value


@dataclass(frozen=True)
class GemExtraBasis:
    role_id: int
    equipment_basis_revision: int
    policy: str
    source_ref: str
    values: tuple

    def __post_init__(self):
        if (type(self.role_id) is not int or not 0<self.role_id<2**63
                or type(self.equipment_basis_revision) is not int or not 0<=self.equipment_basis_revision<=0x7fffffff
                or type(self.policy) is not str or not 1<=len(self.policy)<=160
                or type(self.source_ref) is not str or not 1<=len(self.source_ref)<=160
                or type(self.values) is not tuple or len(self.values)!=6
                or any(type(p) is not tuple or len(p)!=2 or type(p[0]) is not int for p in self.values)
                or tuple(p[0] for p in self.values)!=EXTRA_IDS):
            raise ValueError('Complete immutable ungemmed extra attribute basis required')
        for _,value in self.values:_native(value,signed=True)


@dataclass(frozen=True)
class GemEquipmentSource:
    socket: EquipmentGemBasis
    score_basis: GemScoreBasis

    def __post_init__(self):
        if (type(self.socket) is not EquipmentGemBasis or type(self.score_basis) is not GemScoreBasis
                or self.socket.item.id!=self.score_basis.item_key or self.socket.item.role_id!=self.score_basis.role_id):
            raise ValueError('Frozen complete same-item socket and score sources required')


@dataclass(frozen=True)
class GemEquipmentRules:
    revision: str
    base_rules: object
    carrier_rules: object
    gem_rules: GemRules
    score_rules: GemScoreRules
    condition_policy: str
    mapping: object

    @classmethod
    def load(cls):
        policy=json.loads((OUT/'design/role-equipment-gems-v1.json').read_text(encoding='utf-8'))
        base=load_ordinary_equipment_attribute_rules();gems=GemRules.load();scores=GemScoreRules.load()
        condition=EquipmentRules.load();mapping={int(k):v for k,v in policy['gem_mapping'].items()}
        expected={81:80,101:100,111:110,121:120,131:130,141:140,811:810,821:820,
            351:350,361:360,371:370,381:380,1131:1130,1531:1530}
        if (policy['revision']!='2026-10-24.role-equipment-gems.1'
                or policy['base_equipment_policy']!=base.revision or policy['gem_policy']!=gems.revision
                or policy['score_policy']!=scores.revision or policy['condition_policy']!=condition.revision
                or policy['extra_ids']!=list(EXTRA_IDS) or mapping!=expected or policy['resource_cause']!='equip'):
            raise ValueError('Gem equipment source policy requires explicit review')
        rows=json.loads((OUT/'catalogs/knight.gsp.item.cattributedesconfig.json').read_text(encoding='utf-8'))
        descriptions={int(r['attributes']['id']):r['attributes'] for r in rows}
        if (any(int(descriptions[target]['numid'])!=modifier for modifier,target in mapping.items())
                or {key for gem in gems.gems.values() for key,_ in gem.effects}!=set(mapping)):
            raise ValueError('Gem effect identities disagree with original numeric families')
        # Reference for the existing root's ownership/source validator only.
        # Existing project_equipment_totals correctly refuses this new policy.
        carrier=replace(base,revision=policy['revision'])
        return cls(policy['revision'],base,carrier,gems,scores,condition.revision,MappingProxyType(mapping))


@dataclass(frozen=True)
class GemEquipmentTotals:
    core: EquipmentTotals
    extras: tuple
    raw_modifiers: tuple
    source_items: tuple


def project(rules,attrs,inventory,basis,extra_basis,sources):
    """Compute all ordinary gem totals from known same-source frozen inputs."""
    if (type(rules) is not GemEquipmentRules or type(attrs) is not RoleAttributes
            or type(inventory) is not InventorySnapshot or type(inventory.items) is not tuple
            or any(type(i) is not ItemState for i in inventory.items)
            or type(inventory.role_id) is not int or type(inventory.inventory_revision) is not int
            or type(basis) is not EquipmentAttributeBasis or type(extra_basis) is not GemExtraBasis
            or type(sources) is not tuple or any(type(s) is not GemEquipmentSource for s in sources)
            or attrs.role_id!=inventory.role_id or basis.role_id!=attrs.role_id or extra_basis.role_id!=attrs.role_id
            or basis.policy!=rules.revision or extra_basis.policy!=rules.revision
            or extra_basis.equipment_basis_revision!=basis.revision or extra_basis.source_ref!=basis.source_id
            or type(attrs.level) is not int or attrs.level<=0):
        raise ValueError('Complete same-role gem policy/basis/snapshots required')
    by_key={s.socket.item.id:s for s in sources}
    worn={i.id for i in inventory.items if i.equipment_slot is not None}
    if len(by_key)!=len(sources) or set(by_key)!=worn or len({s.socket.account_id for s in sources})>1:
        raise ValueError('Exactly one complete known source per worn equipment required')
    active={};base_items=[];source_items=[]
    for item in inventory.items:
        if item.equipment_slot is None:
            base_items.append(item);continue
        source=by_key[item.id];socket=source.socket
        if (socket.item!=item or socket.inventory_revision!=inventory.inventory_revision
                or socket.origin not in ('explicit_known_socket_profile','socket_change')
                or socket.detail_source[:2] not in ((rules.gem_rules.detail_rules.revision,'restoration_grant'),
                    (rules.gem_rules.detail_rules.revision,'explicit_known_clean_instance'))
                or socket.condition_source[0]!=rules.condition_policy or item.detail.prefix_quality!=1):
            raise ValueError('Stale, unknown or advanced worn gem source')
        validate_equipment(rules.gem_rules,item,socket.state,socket.equipment_skill)
        validate_current(rules.score_rules,rules.gem_rules,item,socket.state,source.score_basis)
        source_items.append((item.id,socket.state.version))
        if item.condition.current>0:
            for key,value in rules.gem_rules.effects(socket.state):active[key]=active.get(key,0)+value
        # This is ONLY the canonical base calculation input. Original details,
        # actual color and independent gem sources remain intact for storage/UI.
        base_items.append(replace(item,detail=replace(item.detail,score=0),condition=replace(item.condition,color_tier=1)))
    base_inventory=replace(inventory,items=tuple(base_items))
    base=project_equipment_totals(attrs,base_inventory,replace(basis,policy=rules.base_rules.revision),rules.base_rules)
    extras=dict(extra_basis.values);changes={}
    for modifier,value in active.items():
        target=rules.mapping[modifier]
        if target in CORE_NAMES:
            name=CORE_NAMES[target];changes[name]=changes.get(name,getattr(base.attributes,name))+value
        else:extras[target]+=value
    for value in changes.values():_native(value)
    for value in extras.values():_native(value,signed=True)
    final=replace(base,attributes=replace(base.attributes,**changes),equipment_policy=rules.revision)
    return GemEquipmentTotals(final,tuple(sorted(extras.items())),tuple(sorted(active.items())),tuple(sorted(source_items)))
