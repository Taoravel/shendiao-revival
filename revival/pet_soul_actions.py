"""Explicit pet soul asset-action policy and pure plans.

Original four/six fields and modifiers retain their separate authorities.
Server slot selection, new raw6 and zero cash are explicit local design.
Pure plans never authorize wire input, change assets, persist or send.
"""
from dataclasses import dataclass,replace
import json
from inspect_client import OUT
from pet_soul_item_storage import OrbRules,OrbBasis
from pet_soul_storage import SoulBasis
from pet_souls import SoulBean,SoulProfile
from inventory import ItemState
from pet_soul_item_data import OrbTips,display_tips_from_worn


REVISION='2026-10-24.pet-soul-actions.1'


@dataclass(frozen=True)
class SoulActionRules:
    revision: str
    orbs: OrbRules

    def __post_init__(self):
        if self.revision!=REVISION or type(self.orbs) is not OrbRules:
            raise ValueError('Frozen same-policy soul action rules required')

    @classmethod
    def load(cls):
        policy=json.loads((OUT/'design/pet-soul-actions-v1.json').read_text(encoding='utf-8'));orbs=OrbRules.load()
        if (any(type(policy[name]) is not int for name in ('maximum_slots','wear_cash','remove_cash',
                'removal_item','return_binding','return_nonbinding_flags'))
                or policy['revision']!=REVISION or policy['orb_policy']!=orbs.revision
                or policy['soul_policy']!=orbs.souls.revision or policy['maximum_slots']!=5
                or policy['slot_choice']!='lowest_free' or policy['duplicate_rule']!='exact_template'
                or policy['new_raw6']!='known_item_binding' or policy['retained_raw6']!='preserve_exact'
                or policy['wear_cash']!=0 or policy['remove_cash']!=0 or policy['removal_item']!=38045
                or policy['tool_selection']!='bound_first_then_key' or policy['return_binding']!=1
                or policy['return_nonbinding_flags']!=0):
            raise ValueError('Soul action policy requires explicit review')
        return cls(REVISION,orbs)


@dataclass(frozen=True)
class SoulActionAuthority:
    role_id: int
    pet_id: int
    login_epoch: int | str
    policy: str
    version: int
    allowed: bool
    known_flag22: int
    material_flags: tuple

    def __post_init__(self):
        if (type(self.role_id) is not int or not 0<self.role_id<2**63
                or type(self.pet_id) is not int or not 0<self.pet_id<=0x7fffffff
                or not (type(self.login_epoch) is int and 0<self.login_epoch<2**63
                    or type(self.login_epoch) is str and 1<=len(self.login_epoch)<=128)
                or type(self.policy) is not str or not 1<=len(self.policy)<=160
                or type(self.version) is not int or not 0<=self.version<2**63-1
                or type(self.allowed) is not bool or type(self.known_flag22) is not int or self.known_flag22 not in (0,1)
                or type(self.material_flags) is not tuple
                or any(type(p) is not tuple or len(p)!=2 or type(p[0]) is not int or not 0<p[0]<=0x7fffffff
                    or type(p[1]) is not int or not 0<=p[1]<=0xfffffffe or p[1]&1 for p in self.material_flags)
                or tuple(p[0] for p in self.material_flags)!=tuple(sorted({p[0] for p in self.material_flags}))):
            raise ValueError('Complete immutable current soul action clearance required')


@dataclass(frozen=True)
class SoulWearPlan:
    policy: str
    slot: int
    after: SoulProfile
    debits: tuple
    grants: tuple
    cash_cost: int
    effects: tuple


def plan_wear(rules,before,orb,authority):
    """Trusted frozen sources only; current lease/clearance must also be fenced
    by the later admitting/writing owner. Original XP is never cap-truncated.
    """
    if (type(rules) is not SoulActionRules or rules.revision!=REVISION
            or type(before) is not SoulBasis or type(orb) is not OrbBasis or type(authority) is not SoulActionAuthority
            or before.account_id!=orb.account_id or before.profile.role_id!=orb.source.role_id
            or before.profile.role_id!=authority.role_id or before.profile.pet_id!=authority.pet_id
            or before.inventory_revision!=orb.inventory_revision or not authority.allowed
            or authority.material_flags or before.pet.fighting!=1
            or orb.source.nonbinding_flags!=0 or orb.source.policy!=rules.orbs.revision):
        raise ValueError('Known current same-role unrestricted orb and active pet clearance required')
    souls=rules.orbs.souls;souls.validate_profile(before.profile)
    if (orb.source.template_id not in souls.souls
            or orb.source.tips.soul_skill_id!=0 and orb.source.tips.soul_skill_id not in souls.skill_ids
            or souls.has_template(before.profile,orb.item.template_id)):
        raise ValueError('Known nonduplicate original orb required')
    used={slot for slot,_ in before.profile.entries}
    slot=next((slot for slot in range(1,6) if slot not in used),None)
    if slot is None:raise ValueError('All five soul slots occupied')
    tips=orb.source.tips
    raw6=orb.item.binding if orb.source.retained_raw6 is None else orb.source.retained_raw6
    bean=SoulBean(orb.item.template_id,tips.cumulative_exp,tips.soul_skill_id,tips.raw4,tips.raw5,raw6)
    after=replace(before.profile,version=before.profile.version+1,entries=tuple(sorted(before.profile.entries+((slot,bean),))))
    effects=souls.effects(before.pet.template_id,after,authority.known_flag22)
    return SoulWearPlan(rules.revision,slot,after,((orb.item.id,1),),(),0,effects)


@dataclass(frozen=True)
class SoulRemovePlan:
    policy: str
    slot: int
    after: SoulProfile
    debits: tuple
    grants: tuple
    cash_cost: int
    effects: tuple
    tool_template: int
    tool_count: int
    returned_tips: OrbTips
    retained_raw6: int
    returned_nonbinding_flags: int


def _tool_debits(tools,role_id,template,count):
    if type(tools) is not tuple or len(tools)>40 or len({i.id for i in tools if type(i) is ItemState})!=len(tools):
        raise ValueError('Unique immutable carried removal tool stacks required')
    for item in tools:
        if (type(item) is not ItemState or any(type(v) is not int for v in
                (item.id,item.role_id,item.template_id,item.quantity,item.slot,item.binding))
                or not 0<item.id<=0x7fffffff or item.role_id!=role_id or item.template_id!=template
                or not 0<item.quantity<=0x7fffffff or item.slot<0 or item.binding not in (0,1)
                or item.equipment_slot is not None or item.quality is not None
                or item.condition is not None or item.detail is not None):
            raise ValueError('Known owned ordinary removal tools required')
    remaining=count;debits=[]
    for item in sorted(tools,key=lambda i:(-i.binding,i.id)):
        take=min(remaining,item.quantity)
        if take:debits.append((item.id,take));remaining-=take
        if remaining==0:break
    if remaining:raise ValueError('Insufficient soul removal tools')
    return tuple(debits)


@dataclass(frozen=True)
class SoulRemovalMaterials:
    bean: SoulBean
    template: int
    count: int
    debits: tuple


def removal_materials(rules,before,slot,tools):
    """Quote/allocate before requesting actual per-key clearance; no permission.

    Admission and the pure authorized plan share this original quote and local
    allocation, without fabricating flags0 merely to find the required keys.
    """
    if (type(rules) is not SoulActionRules or rules.revision!=REVISION or type(before) is not SoulBasis
            or type(slot) is not int or not 1<=slot<=5):
        raise ValueError('Known current soul source and exact slot required')
    rules.orbs.souls.validate_profile(before.profile)
    bean=next((bean for key,bean in before.profile.entries if key==slot),None)
    if bean is None:raise ValueError('Selected soul slot is empty')
    template,count=rules.orbs.souls.removal_quote(bean)
    return SoulRemovalMaterials(bean,template,count,_tool_debits(tools,before.profile.role_id,template,count))


def plan_remove(rules,before,slot,tools,authority):
    """Pure single-slot removal, original tool quote and explicit bound return.

    The returned orb is a newly designed fully bound result; its four native
    fields and exact historical raw6 copy the selected bean without loss.
    """
    if (type(rules) is not SoulActionRules or rules.revision!=REVISION or type(before) is not SoulBasis
            or type(authority) is not SoulActionAuthority or not authority.allowed
            or before.profile.role_id!=authority.role_id or before.profile.pet_id!=authority.pet_id
            or type(slot) is not int or not 1<=slot<=5):
        raise ValueError('Known current owned soul and removal clearance required')
    souls=rules.orbs.souls
    materials=removal_materials(rules,before,slot,tools)
    bean,template,count,debits=materials.bean,materials.template,materials.count,materials.debits
    if authority.material_flags!=tuple((key,0) for key in sorted(key for key,_ in debits)):
        raise ValueError('Explicit unrestricted flags for each debited tool stack required')
    after=replace(before.profile,version=before.profile.version+1,
        entries=tuple(pair for pair in before.profile.entries if pair[0]!=slot))
    tips,_=display_tips_from_worn(bean)  # Only four fields used; marker is not history.
    effects=souls.effects(before.pet.template_id,after,authority.known_flag22)
    return SoulRemovePlan(rules.revision,slot,after,debits,((bean.item_id,1,1),),0,effects,
        template,count,tips,bean.raw6,0)
