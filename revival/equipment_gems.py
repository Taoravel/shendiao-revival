"""Ordered ordinary gem state and independent original effect/return rules.

The list is a separate equipment modifier source, never folded into its base
properties. Pure plans do not debit assets or manufacture score/color values.
"""
from dataclasses import dataclass
import json
import struct
from types import MappingProxyType
from inspect_client import OUT
from inventory import ItemState
from equipment_condition import EquipmentCondition
from equipment_detail import EquipmentDetail,DetailRules,encode
from wire import octets


@dataclass(frozen=True)
class SocketRequest:
    operation: str
    equipment_key: int
    source_column: int
    gem_key: int | None = None
    selection: int | None = None

    def __post_init__(self):
        if (type(self.equipment_key) is not int or not 0<self.equipment_key<=0x7fffffff
                or type(self.source_column) is not int or self.source_column not in (1,4)
                or self.operation not in ('embed','remove')
                or self.operation=='embed' and (type(self.gem_key) is not int
                    or not 0<self.gem_key<=0x7fffffff or self.selection is not None)
                or self.operation=='remove' and (self.gem_key is not None or type(self.selection) is not int
                    or self.selection!=-1 and not 0<self.selection<=0x7fffffff)):
            raise ValueError('Invalid immutable ordinary socket request')


def decode(kind,payload):
    if type(kind) is not int or kind not in (0xc0425,0xc04ea) or type(payload) is not bytes or len(payload)!=9:
        raise ValueError('Exact ordinary insertion/removal request required')
    if kind==0xc0425:
        equipment,source,gem=struct.unpack('>iBi',payload)
        if source not in (0,1):raise ValueError('Only proven carried/equipped source bytes supported')
        return SocketRequest('embed',equipment,1 if source==0 else 4,gem_key=gem)
    selection,equipment,source=struct.unpack('>iiB',payload)
    if source not in (0,1):raise ValueError('Only proven carried/equipped source bytes supported')
    return SocketRequest('remove',equipment,1 if source==0 else 4,selection=selection)


@dataclass(frozen=True)
class GemState:
    version: int
    templates: tuple
    policy: str

    def __post_init__(self):
        if (type(self.version) is not int or not 0<=self.version<2**63-1
                or type(self.templates) is not tuple or len(self.templates)>15
                or any(type(x) is not int or not 0<x<=0x7fffffff for x in self.templates)
                or len(set(self.templates))!=len(self.templates)
                or type(self.policy) is not str or not 1<=len(self.policy)<=160):
            raise ValueError('Invalid immutable equipment gem state')


@dataclass(frozen=True)
class SocketGem:
    template: int
    family: int
    level: int
    slots: tuple
    effects: tuple
    tool: int
    tool_count: int
    return_template: int


@dataclass(frozen=True)
class GemRules:
    revision: str
    gems: object
    equipment: object
    detail_rules: DetailRules

    @classmethod
    def load(cls):
        policy=json.loads((OUT/'design/equipment-gems-v1.json').read_text(encoding='utf-8'))
        if (policy['revision']!='2026-10-24.equipment-gems.1' or policy['client_verified']!={
                'maximum_gem_level':15,'maximum_families':3,'socket_skill_ids':[0,410006,410007],
                'normal_diamond':36949,'advanced_diamond':39649,
                'cash_quote':'50*(original equipment effective level+10*gem level)','grade_equals_hole':True}):
            raise ValueError('Equipment gem policy requires explicit implementation review')
        def rows(name):
            return {int(r['attributes']['id']):r for r in json.loads(
                (OUT/f'catalogs/knight.gsp.item.{name}.json').read_text(encoding='utf-8'))}
        items,effects,gods=rows('citemattr'),rows('cgemeffect'),rows('cgodweapon')
        gems={}
        for family in range(14):
            for level in range(1,16):
                key=35000+family+13*(level-1) if family<13 else 35199+level
                item,row=items[key]['attributes'],effects[key]
                attr,lists=row['attributes'],row['lists']
                kinds,values=tuple(map(int,lists['effecttype'])),tuple(map(int,lists['effect']))
                slots=tuple(map(int,lists['equiptype']))
                normal,advanced=int(attr['removegem']),int(attr['superremovegem'])
                returned=key if level<=6 else int(attr['Diamondid'])
                if (int(item['itemtypeid'])!=5 or int(item['level'])!=level or int(item['maxNum'])!=30
                        or int(attr['load'])!=0 or not kinds or len(kinds)!=len(values)
                        or len(set(kinds))!=len(kinds) or min(kinds)<=0 or min(values)<=0
                        or not slots or len(set(slots))!=len(slots) or any(not 0<=s<=5 for s in slots)
                        or ((normal<=0 or advanced!=0) if level<=6 else (normal!=0 or advanced<=0))):
                    raise ValueError('Original ordinary gem rows require reconciliation')
                gems[key]=SocketGem(key,family,level,slots,tuple(zip(kinds,values)),
                    36949 if level<=6 else 39649,normal if level<=6 else advanced,returned)
        for gem in gems.values():
            other=gems.get(gem.return_template)
            if other is None or other.family!=gem.family or other.level!=(gem.level if gem.level<=6 else gem.level-1):
                raise ValueError('Original gem removal return chain changed')
        details=DetailRules.load()
        equipment={key:(((int(items[key]['attributes']['itemtypeid'])>>4)&15),int(items[key]['attributes']['level']))
            for key in details.templates if key not in gods and int(items[key]['attributes']['itemtypeid']) not in (0x1c8,0x2c8,0x3c8)}
        return cls(policy['revision'],MappingProxyType(gems),MappingProxyType(equipment),details)

    def validate(self,state):
        if type(state) is not GemState or state.policy!=self.revision or any(k not in self.gems for k in state.templates):
            raise ValueError('Current known ordinary gem state required')
        gems=tuple(self.gems[key] for key in state.templates)
        if len({g.level for g in gems})!=len(gems) or len({g.family for g in gems})>3:
            raise ValueError('One gem per grade and at most three families required')
        return gems

    def effects(self,state):
        totals={}
        for gem in self.validate(state):
            for key,value in gem.effects:totals[key]=totals.get(key,0)+value
        return tuple(sorted(totals.items()))

    def holes(self,template,equipment_skill):
        if (type(template) is not int or template not in self.equipment
                or type(equipment_skill) is not int or equipment_skill not in (0,410006,410007)):
            raise ValueError('Ordinary equipment and explicit supported socket skill required')
        return 15 if equipment_skill==410006 else min(15,self.equipment[template][1]//10+(equipment_skill==410007))


@dataclass(frozen=True)
class EmbedPlan:
    before: GemState
    after: GemState
    material_debit: tuple
    cash_cost: int
    equipment_binding: int
    replaced_template: int | None


@dataclass(frozen=True)
class RemovePlan:
    before: GemState
    after: GemState
    tools: tuple
    grants: tuple


def validate_equipment(rules,item,state,skill):
    gems=rules.validate(state)
    if (type(item) is not ItemState or type(item.id) is not int or not 0<item.id<=0x7fffffff
            or type(item.role_id) is not int or item.role_id<=0 or type(item.template_id) is not int
            or item.template_id not in rules.equipment or type(item.quantity) is not int or item.quantity!=1
            or type(item.binding) is not int or item.binding not in (0,1) or item.quality is not None
            or type(item.condition) is not EquipmentCondition or type(item.detail) is not EquipmentDetail
            or item.detail.identified!=1 or item.detail.base_properties!=rules.detail_rules.templates[item.template_id][0]
            or rules.detail_rules.color(item.template_id,item.detail)!=item.condition.color_tier):
        raise ValueError('Known identified ordinary equipment and independent valid details required')
    slot,level=rules.equipment[item.template_id]
    if (type(item.slot) is not int or (item.equipment_slot is None and item.slot<0)
            or item.equipment_slot is not None and (type(item.equipment_slot) is not int
                or item.equipment_slot!=slot or item.slot!=-slot-1)):
        raise ValueError('Current carried/equipped item slot required')
    limit=rules.holes(item.template_id,skill)
    if any(g.level>limit or slot not in g.slots for g in gems):
        raise ValueError('Stored gems conflict with original equipment slots or holes')
    return slot,level,limit


def embed(rules,equipment,state,material,equipment_skill,*,flags):
    slot,level,limit=validate_equipment(rules,equipment,state,equipment_skill)
    if type(flags) is not tuple or len(flags)!=2 or any(type(v) is not int or v!=0 for v in flags):
        raise ValueError('Explicit unrestricted equipment and material flags required')
    if (type(material) is not ItemState or type(material.template_id) is not int or material.template_id not in rules.gems
            or type(material.id) is not int or not 0<material.id<=0x7fffffff
            or material.id==equipment.id
            or material.role_id!=equipment.role_id or type(material.role_id) is not int
            or type(material.quantity) is not int or not 1<=material.quantity<=30
            or material.equipment_slot is not None or type(material.slot) is not int or material.slot<0
            or type(material.binding) is not int or material.binding not in (0,1) or material.quality is not None
            or material.condition is not None or material.detail is not None):
        raise ValueError('Known owned carried ordinary gem material required')
    gem=rules.gems[material.template_id]
    if gem.level>limit or slot not in gem.slots:raise ValueError('Gem does not fit equipment slot or grade')
    after=list(state.templates);index=next((i for i,key in enumerate(after) if rules.gems[key].level==gem.level),None)
    replaced=after[index] if index is not None else None
    if index is None:after.append(gem.template)
    else:after[index]=gem.template
    result=GemState(state.version+1,tuple(after),state.policy)
    rules.validate(result)
    return EmbedPlan(state,result,(material.id,1),50*(level+10*gem.level),max(equipment.binding,material.binding),replaced)


def remove(rules,equipment,state,selection,equipment_skill,*,flags):
    validate_equipment(rules,equipment,state,equipment_skill)
    if type(flags) is not int or flags!=0:raise ValueError('Explicit unrestricted equipment flags required')
    if type(selection) is not int or selection!=-1 and selection not in state.templates:
        raise ValueError('Exact installed gem template or all=-1 required')
    selected=tuple(key for key in state.templates if selection==-1 or key==selection)
    if not selected:raise ValueError('No gems selected for removal')
    tools,grants={},{}
    for key in selected:
        gem=rules.gems[key]
        tools[gem.tool]=tools.get(gem.tool,0)+gem.tool_count
        grants[gem.return_template]=grants.get(gem.return_template,0)+1
    after=GemState(state.version+1,tuple(key for key in state.templates if key not in selected),state.policy)
    return RemovePlan(state,after,tuple(sorted(tools.items())),tuple((key,count,1) for key,count in grants.items()))


def encode_detail(rules,equipment,state,equipment_skill):
    """Extend the public clean encoder at the original ordered gem vector.

    Score and color remain separately supplied authoritative fields; the list
    never invents or incrementally modifies them or the original base map.
    """
    validate_equipment(rules,equipment,state,equipment_skill)
    original=encode(equipment.template_id,equipment.detail,equipment.condition,rules.detail_rules)
    offset=28+len(octets(b''))+12+4+8*len(equipment.detail.base_properties)+4
    if len(original)!=116+8*len(equipment.detail.base_properties) or original[offset-4:offset+4]!=bytes(8):
        raise ValueError('Clean native detail layout changed; gem extension needs review')
    gems=struct.pack('>i',len(state.templates))+b''.join(struct.pack('>i',key) for key in state.templates)
    return original[:offset]+gems+original[offset+4:]
