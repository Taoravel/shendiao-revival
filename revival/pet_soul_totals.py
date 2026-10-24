"""All14 soul modifiers over canonical pet growth and explicit seven extras.

Original mappings/values; explicitly designed composition. Final native/battle
consumers cannot read unsettled caps through the ordinary attribute Interface.
"""
from dataclasses import dataclass,replace
from fractions import Fraction
from types import MappingProxyType
import json
from math import gcd
from inspect_client import OUT
from pet_growth import Attributes
from pet_souls import SoulRules,SoulProfile
from role_mingwen import MingwenRules

REVISION='2026-10-24.pet-soul-totals.1'
EXTRA_IDS=(110,120,740,1550,1560,1580,1590)
FLATS=MappingProxyType({81:'physical_attack',811:'magic_attack',101:'physical_defense',821:'magic_defense',151:'max_mp',141:'max_hp',131:'speed'})
RATIOS=MappingProxyType({741:740,1551:1550,1561:1560,1581:1580,1591:1590})
PERCENTS=MappingProxyType({112:110,122:120})


@dataclass(frozen=True)
class PetSoulExtraBasis:
    role_id: int
    pet_id: int
    policy: str
    source_ref: str
    values: tuple

    def __post_init__(self):
        if (type(self.role_id) is not int or not 0<self.role_id<2**63 or type(self.pet_id) is not int
                or not 0<self.pet_id<=0x7fffffff or type(self.policy) is not str or self.policy!=REVISION
                or type(self.source_ref) is not str or not 1<=len(self.source_ref)<=160
                or type(self.values) is not tuple or len(self.values)!=7
                or any(type(p) is not tuple or len(p)!=3 or any(type(v) is not int for v in p)
                    or not -0x80000000<=p[1]<=0x7fffffff or not 0<p[2]<=0x7fffffff or gcd(p[1],p[2])!=1 for p in self.values)
                or tuple(p[0] for p in self.values)!=EXTRA_IDS):
            raise ValueError('Complete exact seven-field known pet extra baseline required')
        for key,n,d in self.values:
            if key in (110,120):
                if n<0 or d!=1:raise ValueError('Known native integer hit/dodge baseline required')
            elif not -1<=Fraction(n,d)<=1:raise ValueError('Known ratio baseline outside selected policy bounds')


@dataclass(frozen=True)
class PetSoulTotalsRules:
    revision: str
    souls: SoulRules
    mingwen: MingwenRules

    @classmethod
    def load(cls):
        p=json.loads((OUT/'design/pet-soul-totals-v1.json').read_text(encoding='utf-8'))
        if (p['revision']!=REVISION or {int(k):v for k,v in p['flat_mapping'].items()}!=FLATS
                or {int(k):v for k,v in p['ratio_mapping'].items()}!=RATIOS
                or {int(k):v for k,v in p['percent_mapping'].items()}!=PERCENTS or p['extra_ids']!=list(EXTRA_IDS)
                or p['composition_mode']!='flat_add__percent_sum_floor__ratio_signed_add'
                or p['ratio_bounds']!=[-1,1] or any(type(v) is not int for v in p['ratio_bounds'])
                or p['resource_cause_mode']!='absolute_clip_no_revive'):
            raise ValueError('Pet soul totals policy requires explicit reconciliation')
        rows=json.loads((OUT/'catalogs/knight.gsp.item.cattributedesconfig.json').read_text(encoding='utf-8'))
        definitions={int(r['attributes']['id']):r['attributes'] for r in rows}
        cores={81:80,811:810,101:100,821:820,151:150,141:140,131:130,**RATIOS}
        if (any(int(definitions[core]['numid'])!=modifier for modifier,core in cores.items())
                or any(int(definitions[core]['percentid'])!=modifier for modifier,core in PERCENTS.items())):
            raise ValueError('Original explicit pet modifier relationships changed')
        return cls(REVISION,SoulRules.load(),MingwenRules.load())

    def __post_init__(self):
        if self.revision!=REVISION or type(self.souls) is not SoulRules or type(self.mingwen) is not MingwenRules:
            raise ValueError('Frozen complete pet soul projection rules required')


@dataclass(frozen=True)
class PetSoulAttributes:
    core: Attributes
    extra_values: tuple
    policy: str
    source_stamp: str
    settled: bool

    def __post_init__(self):
        if (type(self.core) is not Attributes or self.policy!=REVISION or type(self.source_stamp) is not str
                or len(self.source_stamp)!=64 or any(c not in '0123456789abcdef' for c in self.source_stamp)
                or type(self.settled) is not bool or type(self.extra_values) is not tuple or len(self.extra_values)!=7
                or any(type(p) is not tuple or len(p)!=3 or any(type(v) is not int for v in p)
                    or p[2]<=0 or gcd(p[1],p[2])!=1 for p in self.extra_values)
                or tuple(p[0] for p in self.extra_values)!=EXTRA_IDS):
            raise ValueError('Complete immutable selected final pet attributes required')

    def __getattr__(self,name):
        if name in Attributes.__dataclass_fields__:
            if not self.settled:raise ValueError('Pet final attributes/resources require settled current source')
            return getattr(self.core,name)
        raise AttributeError(name)

    @property
    def extras(self):
        if not self.settled:raise ValueError('Pet ratios require settled current source')
        return tuple((key,Fraction(n,d)) for key,n,d in self.extra_values)


def project(rules,bare,profile,known_flag22,extra):
    """Return all final core/extras; no resources, storage, rounding-to-float."""
    from pet_growth_store import PetProgress
    if (type(rules) is not PetSoulTotalsRules or type(bare) is not PetProgress or type(bare.attributes) is not Attributes
            or type(profile) is not SoulProfile or type(extra) is not PetSoulExtraBasis
            or (bare.role_id,bare.pet_id)!=(profile.role_id,profile.pet_id)
            or (bare.role_id,bare.pet_id)!=(extra.role_id,extra.pet_id)):
        raise ValueError('Current canonical growth and complete same-pet soul/extra sources required')
    effects=rules.souls.effects(bare.profile.template_id,profile,known_flag22)
    sums={}
    for _,_,_,_,key,_,value in effects:sums[key]=sums.get(key,Fraction(0))+value
    values={key:Fraction(n,d) for key,n,d in extra.values}
    core={field:getattr(bare.attributes,field)+int(sums.get(key,0)) for key,field in FLATS.items()}
    for modifier,key in PERCENTS.items():
        value=values[key]*(1+sums.get(modifier,0));values[key]=Fraction(value.numerator//value.denominator)
    for modifier,key in RATIOS.items():values[key]+=sums.get(modifier,0)
    if (any(type(v) is not int or not 0<=v<=0x7fffffff for v in core.values())
            or core['max_hp']<1 or core['speed']<1
            or any(not 0<=values[key]<=0x7fffffff for key in (110,120))
            or any(not -1<=values[key]<=1 for key in RATIOS.values())):
        raise ValueError('Final pet soul totals exceed explicitly selected policy bounds')
    final=replace(bare.attributes,**core)
    extras=tuple((key,values[key].numerator,values[key].denominator) for key in EXTRA_IDS)
    return final,extras
