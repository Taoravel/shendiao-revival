"""Explicit local gem scoring; never reinterpret enhancement coefficients.

Pure projection only. The owner must persist the known pre-gem score separately
and compose score/color, material/cash/gem state and root resources atomically.
"""
from dataclasses import dataclass,replace
import json
from inspect_client import OUT
from inventory import ItemState
from equipment_detail import EquipmentDetail
from equipment_condition import EquipmentCondition
from equipment_gems import GemState


@dataclass(frozen=True)
class GemScoreRules:
    revision: str
    grade_points: tuple

    def __post_init__(self):
        if (type(self.revision) is not str or self.revision!='2026-10-24.gem-score.1'
                or type(self.grade_points) is not tuple or len(self.grade_points)!=15
                or any(type(v) is not int for v in self.grade_points)
                or self.grade_points!=(50,55,60,65,70,75,80,85,90,95,100,105,110,115,120)):
            raise ValueError('Frozen explicitly reviewed gem score policy required')

    @classmethod
    def load(cls):
        policy=json.loads((OUT/'design/equipment-gem-score-v1.json').read_text(encoding='utf-8'))
        return cls(policy['revision'],tuple(policy['grade_points']))

    def contribution(self,gem_rules,state):
        return sum(self.grade_points[g.level-1] for g in gem_rules.validate(state))


@dataclass(frozen=True)
class GemScoreBasis:
    role_id: int
    item_key: int
    policy: str
    plain_score: int
    source_ref: str

    def __post_init__(self):
        if (type(self.role_id) is not int or not 0<self.role_id<2**63
                or type(self.item_key) is not int or not 0<self.item_key<=0x7fffffff
                or type(self.policy) is not str or not 1<=len(self.policy)<=160
                or type(self.plain_score) is not int or not 0<=self.plain_score<=0x7fffffff
                or type(self.source_ref) is not str or not 1<=len(self.source_ref)<=160):
            raise ValueError('Complete explicit pre-gem score basis required')


@dataclass(frozen=True)
class GemScoreChange:
    basis: GemScoreBasis
    before: ItemState
    after: ItemState
    old_contribution: int
    new_contribution: int


def validate_current(rules,gem_rules,item,state,basis):
    """Validate a current source without constructing a future gem state."""
    if (type(rules) is not GemScoreRules or type(basis) is not GemScoreBasis or basis.policy!=rules.revision
            or type(item) is not ItemState or type(item.id) is not int or type(item.role_id) is not int
            or item.id!=basis.item_key or item.role_id!=basis.role_id
            or type(item.template_id) is not int or item.template_id not in gem_rules.equipment
            or type(item.detail) is not EquipmentDetail or type(item.condition) is not EquipmentCondition
            or type(state) is not GemState):
        raise ValueError('Current complete same-equipment score sources required')
    contribution=rules.contribution(gem_rules,state)
    if (item.detail.score!=basis.plain_score+contribution
            or gem_rules.detail_rules.color(item.template_id,item.detail)!=item.condition.color_tier):
        raise ValueError('Current score/color does not match the explicit pre-gem source')
    return contribution


def project(rules,gem_rules,item,before,after,basis):
    """Plan a next score/color without writing or authorizing a socket action."""
    if type(before) is not GemState or type(after) is not GemState or after.version!=before.version+1:
        raise ValueError('Exactly the next gem state is required for score changes')
    old=validate_current(rules,gem_rules,item,before,basis)
    new=rules.contribution(gem_rules,after)
    score=basis.plain_score+new
    if score>0x7fffffff:raise ValueError('Gem score overflows native signed32')
    detail=replace(item.detail,score=score)
    color=gem_rules.detail_rules.color(item.template_id,detail)
    condition=item.condition if color==item.condition.color_tier else replace(
        item.condition,version=item.condition.version+1,color_tier=color)
    return GemScoreChange(basis,item,replace(item,detail=detail,condition=condition),old,new)
