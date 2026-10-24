"""Designed pet-growth v1, using original aptitude/growth/XP table integers.

Pure planning only. Existing zero-constructor instances require explicit migration.
"""
from dataclasses import dataclass, replace
import json
from types import MappingProxyType
from inspect_client import OUT
from pet_stones import StoneRules


@dataclass(frozen=True)
class Profile:
    template_id: int
    growth_raw: int
    aptitudes: tuple  # attack, defense, vitality, magic, speed


@dataclass(frozen=True)
class PetGrowth:
    version: int
    level: int
    experience: int
    allocated: tuple
    hp: int
    mp: int


@dataclass(frozen=True)
class GrowthPlan:
    version: int
    level: int
    experience: int
    allocated: tuple

    def __post_init__(self):
        if (any(type(v) is not int for v in (self.version,self.level,self.experience))
                or not 0<=self.version<2**63-1 or not 0<=self.level<=150 or not 0<=self.experience<=0x7fffffff
                or type(self.allocated) is not tuple or len(self.allocated)!=5
                or any(type(v) is not int or not 0<=v<=0x7fffffff for v in self.allocated)):
            raise ValueError('Exact immutable resource-free pet growth plan required')


@dataclass(frozen=True)
class Attributes:
    five_stats: tuple
    potential: int
    max_hp: int
    max_mp: int
    physical_attack: int
    physical_defense: int
    magic_attack: int
    magic_defense: int
    speed: int


@dataclass(frozen=True)
class GrowthRules:
    revision: str
    initial_level: int
    initial_stat: int
    cap: int
    maximum_exp: int
    thresholds: object
    stone_rules: object
    totals_rules: object = None

    @classmethod
    def load(cls):
        policy = json.loads((OUT/'design/pet-growth-v1.json').read_text(encoding='utf-8'))
        if policy['revision'] != '2026-10-23.pet.1':
            raise ValueError('Pet growth design revision requires implementation review')
        rows = json.loads((OUT/'catalogs/knight.gsp.pet.cpetnextexp.json').read_text(encoding='utf-8'))
        thresholds = MappingProxyType({int(r['attributes']['id']):int(r['attributes']['exp']) for r in rows})
        return cls(policy['revision'], policy['generation']['initial_level'],
                   policy['generation']['initial_five_stats'],
                   policy['experience_policy']['ordinary_level_cap'],
                   policy['experience_policy']['maximum_stored_experience'], thresholds,StoneRules.load())

    def profile(self, row):
        a = row['attributes']
        growth = tuple(map(int,row['lists']['growrate']))
        if not growth:
            raise ValueError('Pet growth tiers missing')
        aptitudes = tuple((int(a[name+'aptmin'])+int(a[name+'aptmax']))//2
                          for name in ('attack','defend','phyforce','magic','speed'))
        result = Profile(int(a['id']),growth[len(growth)//2],aptitudes)
        if result.growth_raw < 500 or min(aptitudes) < 0:
            raise ValueError('Pet profile incompatible with growth v1')
        return result

    def attributes(self, profile, level, allocated=(0,0,0,0,0), *, bonus_potential=0):
        if (type(level) is not int or not self.initial_level <= level <= self.cap
                or type(allocated) is not tuple or len(allocated) != 5
                or any(type(v) is not int or v < 0 for v in allocated)
                or profile.growth_raw < 500 or type(bonus_potential) is not int or not 0<=bonus_potential<=150):
            raise ValueError('Invalid pet level/allocation')
        elapsed = level-self.initial_level
        free = 5*elapsed
        if sum(allocated) > free+bonus_potential:
            raise ValueError('Not enough pet potential')
        automatic = profile.growth_raw*elapsed//100-free
        q,r = divmod(automatic,5)
        stats = tuple(self.initial_stat+q+int(i<r)+allocated[i] for i in range(5))
        v,inner,s,e,agility = stats
        qa,qd,qv,qm,qs = profile.aptitudes
        result = Attributes(stats,free+bonus_potential-sum(allocated),
                            50+10*v*qv//1000+2*level,
                            30+5*inner*qm//1000+level,
                            5+2*s*qa//1000+level,
                            5+3*e*qd//2000+level//2,
                            5+2*inner*qm//1000+level,
                            5+(inner+e)*qm//1000+level//2,
                            5+agility*qs//1000+level//5)
        if max(result.five_stats + (result.max_hp,result.max_mp,result.physical_attack,
                                    result.physical_defense,result.magic_attack,
                                    result.magic_defense,result.speed)) > 0x7fffffff:
            raise ValueError('Pet attribute overflow')
        return result

    def generate(self, profile):
        attr = self.attributes(profile,self.initial_level)
        return PetGrowth(0,self.initial_level,0,(0,0,0,0,0),attr.max_hp,attr.max_mp)

    def _change(self, profile, state, level, experience, allocated, *, bonus_potential=0):
        old = self.attributes(profile,state.level,state.allocated,bonus_potential=bonus_potential)
        new = self.attributes(profile,level,allocated,bonus_potential=bonus_potential)
        if not 0 <= state.hp <= old.max_hp or not 0 <= state.mp <= old.max_mp:
            raise ValueError('Pet resources outside derived bounds')
        hp = 0 if state.hp == 0 else min(new.max_hp,max(0,state.hp+new.max_hp-old.max_hp))
        mp = min(new.max_mp,max(0,state.mp+new.max_mp-old.max_mp))
        return PetGrowth(state.version+1,level,experience,allocated,hp,mp)

    def plan_award(self, profile, state, amount, *, award_cap=None,bonus_potential=0):
        """Original XP/points math only; no synthetic or adjusted HP/MP."""
        if (type(profile) is not Profile or type(state) is not PetGrowth
                or type(state.version) is not int or not 0<=state.version<2**63-2
                or type(state.experience) is not int or type(amount) is not int or amount < 0
                or not 0 <= state.experience <= self.maximum_exp):
            raise ValueError('Invalid pet experience award')
        self.attributes(profile,state.level,state.allocated,bonus_potential=bonus_potential)
        cap=self.cap if award_cap is None else award_cap
        if type(cap) is not int or not self.initial_level<=state.level<=cap<=self.cap:
            raise ValueError('Pet level exceeds award cap or cap is invalid')
        experience = state.experience+amount
        if experience > self.maximum_exp:
            raise ValueError('Pet experience overflow')
        level = state.level
        while level < cap:
            threshold = self.thresholds.get(level)
            if threshold is None or threshold <= 0:
                raise ValueError('Pet experience threshold missing')
            if experience < threshold:
                break
            level += 1
            experience -= threshold
        self.attributes(profile,level,state.allocated,bonus_potential=bonus_potential)
        return GrowthPlan(state.version+1,level,experience,state.allocated)

    def award(self, profile, state, amount, *, award_cap=None,bonus_potential=0):
        planned=self.plan_award(profile,state,amount,award_cap=award_cap,bonus_potential=bonus_potential)
        return self._change(profile,state,planned.level,planned.experience,planned.allocated,bonus_potential=bonus_potential)

    def allocate(self, profile, state, increments, *, bonus_potential=0):
        if type(increments) is not tuple or len(increments) != 5 or any(type(v) is not int or v < 0 for v in increments):
            raise ValueError('Invalid pet allocation command')
        allocated = tuple(a+b for a,b in zip(state.allocated,increments))
        return self._change(profile,state,state.level,state.experience,allocated,bonus_potential=bonus_potential)
