"""Original pet soul data and read-only projections, separate from role gear.

Complete six-field beans are explicit inputs. Cumulative XP and actual grade
survive effective-level caps; signed fractions and unknown raw fields survive
unchanged. No item consumption, implicit history, battle formula or admission.
"""
from dataclasses import dataclass
from fractions import Fraction
import json
from types import MappingProxyType
from inspect_client import OUT


REVISION='2026-10-24.pet-souls-source.1'


def _integer(value,minimum=0,maximum=0x7fffffff):
    if type(value) is not int or not minimum<=value<=maximum:
        raise ValueError('Explicit native soul integer required')


@dataclass(frozen=True)
class SoulBean:
    item_id: int
    cumulative_exp: int
    soul_skill_id: int
    raw4: int
    raw5: int
    raw6: int

    def __post_init__(self):
        _integer(self.item_id,1);_integer(self.cumulative_exp);_integer(self.soul_skill_id)
        for value in (self.raw4,self.raw5,self.raw6):_integer(value,-0x80000000)


@dataclass(frozen=True)
class SoulProfile:
    role_id: int
    pet_id: int
    version: int
    policy: str
    source_ref: str
    entries: tuple

    def __post_init__(self):
        _integer(self.role_id,1,2**63-1);_integer(self.pet_id,1)
        _integer(self.version,0,2**63-2)
        if (type(self.policy) is not str or self.policy!=REVISION
                or type(self.source_ref) is not str or not 1<=len(self.source_ref)<=160
                or type(self.entries) is not tuple or len(self.entries)>5
                or any(type(pair) is not tuple or len(pair)!=2 or type(pair[0]) is not int
                    or not 1<=pair[0]<=5 or type(pair[1]) is not SoulBean for pair in self.entries)
                or tuple(pair[0] for pair in self.entries)!=tuple(sorted({pair[0] for pair in self.entries}))):
            raise ValueError('Explicit complete immutable pet soul map required')


@dataclass(frozen=True)
class SoulTemplate:
    item_id: int
    soul_type: int
    attribute_id: int
    number_type: int
    values: tuple


@dataclass(frozen=True)
class SoulRules:
    revision: str
    souls: object
    thresholds: object
    removal_costs: object
    pet_templates: object
    skill_ids: frozenset

    @classmethod
    def load(cls):
        """Startup-only original catalog load; no hot reload or fallback rows."""
        policy=json.loads((OUT/'design/pet-souls-source-v1.json').read_text(encoding='utf-8'))
        if (policy['revision']!=REVISION or policy['removal_item']!=38045
                or policy['xp_first_threshold_row']!=2 or policy['maximum_level']!=15
                or policy['maximum_slots']!=5 or policy['cap_skills']!=[10001,10002]):
            raise ValueError('Pet soul source policy requires explicit review')
        def rows(name):
            data=json.loads((OUT/f'catalogs/knight.gsp.{name}.json').read_text(encoding='utf-8'))
            result={int(row['attributes']['id']):row for row in data}
            if len(result)!=len(data):raise ValueError('Repeated original soul configuration identity')
            return result
        originals=rows('pet.cpetsoulattrcfg');items=rows('item.citemattr')
        attributes=(81,811,101,821,151,141,131,1551,1561,741,1581,1591,112,122)
        if (set(originals)!=set(range(31276,31304))
                or {key for key,row in items.items() if int(row['attributes']['itemtypeid'])==145}!=set(originals)):
            raise ValueError('Original 28 pet soul item identities changed')
        souls={}
        for key,row in originals.items():
            attr=row['attributes'];index=(key-31276)//2
            values=tuple(Fraction(value) for value in row['lists']['attrvalue'])
            kind=int(attr['soulType']);modifier=int(attr['attrid']);number=int(attr['shuzitype'])
            if (kind!=1+(key-31276)%2 or modifier!=attributes[index]
                    or number!=(1 if index<7 else 2) or len(values)!=15
                    or any(not value for value in values)
                    or number==1 and any(value.denominator!=1 or value<0 for value in values)):
                raise ValueError('Original soul scalar/ratio vectors require reconciliation')
            souls[key]=SoulTemplate(key,kind,modifier,number,values)
        experience=rows('pet.cpetsoulnextexp');cost=rows('pet.cpetsoulzhaichu')
        if set(experience)!=set(range(1,16)) or set(cost)!=set(range(1,16)):
            raise ValueError('Complete original soul grade tables required')
        thresholds={};costs={}
        for kind,field in ((1,'petSoul'),(2,'gaojipetSoul')):
            thresholds[kind]=tuple(int(experience[level]['attributes'][field]) for level in range(1,16))
            costs[kind]=tuple(int(cost[level]['attributes'][field]) for level in range(1,16))
            if (thresholds[kind][0]!=20 or any(value<=0 for value in thresholds[kind]+costs[kind])
                    or tuple(sorted(set(thresholds[kind])))!=thresholds[kind]):
                raise ValueError('Original cumulative soul thresholds/costs invalid')
        pets={key:(int(row['attributes']['kind']),int(row['attributes']['uselevel']))
            for key,row in rows('pet.cpetattr').items()}
        skills=frozenset(rows('skill.cpetsoulskill'))
        if len(pets)!=158 or skills!=frozenset(range(10001,10023)) or any(kind<1 or level<0 for kind,level in pets.values()):
            raise ValueError('Complete known original soul pet/skill catalog required')
        return cls(REVISION,MappingProxyType(souls),MappingProxyType(thresholds),
            MappingProxyType(costs),MappingProxyType(pets),skills)

    def _bean(self,bean):
        if (type(bean) is not SoulBean or bean.item_id not in self.souls
                or bean.soul_skill_id!=0 and bean.soul_skill_id not in self.skill_ids):
            raise ValueError('Known original soul template and explicit soul skill required')
        return self.souls[bean.item_id]

    def validate_profile(self,profile):
        if type(profile) is not SoulProfile or profile.policy!=self.revision:
            raise ValueError('Complete same-policy pet soul map required')
        for _,bean in profile.entries:self._bean(bean)

    def grade(self,bean):
        row=self._bean(bean)
        # Original GetAllID is1..15, but the loop starts at vector index1.
        # Row1 is preserved above, and is deliberately not an upgrade threshold.
        return 1+sum(bean.cumulative_exp>=value for value in self.thresholds[row.soul_type][1:])

    def effective_cap(self,pet_template,profile,known_flag22):
        self.validate_profile(profile)
        if type(pet_template) is not int or pet_template not in self.pet_templates:
            raise ValueError('Known original pet kind/uselevel required')
        if type(known_flag22) is not int or known_flag22 not in (0,1):
            raise ValueError('Explicit known privilege22 required, never implicit zero')
        kind,uselevel=self.pet_templates[pet_template]
        skills={bean.soul_skill_id for _,bean in profile.entries}
        if kind!=1 or 10002 in skills:return 15
        return max(1,uselevel//10)+int(10001 in skills)+known_flag22

    def has_template(self,profile,item_id):
        self.validate_profile(profile)
        if type(item_id) is not int or item_id not in self.souls:raise ValueError('Known candidate soul template required')
        return any(bean.item_id==item_id for _,bean in profile.entries)

    def effects(self,pet_template,profile,known_flag22):
        """Return exact per-slot raw modifiers; do not invent a battle formula."""
        cap=self.effective_cap(pet_template,profile,known_flag22);effects=[]
        for slot,bean in profile.entries:
            row=self._bean(bean);actual=self.grade(bean);effective=min(actual,cap)
            effects.append((slot,bean.item_id,actual,effective,row.attribute_id,row.number_type,row.values[effective-1]))
        return tuple(effects)

    def removal_quote(self,bean):
        row=self._bean(bean)
        return 38045,self.removal_costs[row.soul_type][self.grade(bean)-1]
