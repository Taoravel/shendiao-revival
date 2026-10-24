"""Pure resource transitions for an explicitly migrated uninjured profile.

One immutable resource state, independent naked/final attribute projection.
No SQL, initialization of legacy roles, asset mutation, commit, network or heal
on reads. Actual storage and every consumer must adopt this contract together.
"""
from dataclasses import dataclass
import json
import struct

from inspect_client import OUT


def _version(value):
    if type(value) is not int or not 0<=value<2**63:
        raise ValueError('Nonnegative signed63 resource/source version required')


def _native(value,minimum=0):
    if type(value) is not int or not minimum<=value<=0x7fffffff:
        raise ValueError('Invalid native resource integer')
    if struct.unpack('>f',struct.pack('>f',value))[0]!=value:
        raise ValueError('Resource cannot be represented exactly as native float32')


def _policy(value):
    if type(value) is not str or not 1<=len(value)<=160:
        raise ValueError('Explicit resource projection policy required')


@dataclass(frozen=True)
class ResourceProjection:
    role_id:int
    baseline_revision:int
    growth_revision:int
    attribute_policy:str
    inventory_revision:int
    equipment_basis_revision:int
    equipment_policy:str

    def __post_init__(self):
        if type(self.role_id) is not int or not 0<self.role_id<2**63:
            raise ValueError('Resource role ID required')
        for value in (self.baseline_revision,self.growth_revision,self.inventory_revision,self.equipment_basis_revision):
            _version(value)
        _policy(self.attribute_policy);_policy(self.equipment_policy)


@dataclass(frozen=True)
class ResourceCaps:
    source:ResourceProjection
    hp_max:int
    mp_max:int

    def __post_init__(self):
        if type(self.source) is not ResourceProjection:
            raise ValueError('Explicit immutable resource projection source required')
        _native(self.hp_max,1);_native(self.mp_max)

    @property
    def wound_hp_max(self):
        # Only the policy's explicitly uninjured profile is represented here.
        return self.hp_max


@dataclass(frozen=True)
class RoleResources:
    version:int
    hp:int
    mp:int
    caps:ResourceCaps
    policy:str

    def __post_init__(self):
        _version(self.version);_native(self.hp);_native(self.mp);_policy(self.policy)
        if type(self.caps) is not ResourceCaps or self.hp>self.caps.hp_max or self.mp>self.caps.mp_max:
            raise ValueError('Current resources must fit their known final caps')


@dataclass(frozen=True)
class ResourceTransition:
    before:RoleResources
    after:RoleResources
    cause:str

    @property
    def changed(self):
        return self.before!=self.after


@dataclass(frozen=True)
class ResourceRules:
    revision:str
    equipment_causes:frozenset
    resource_causes:frozenset
    source_causes:frozenset
    combat_causes:frozenset=frozenset()

    def __post_init__(self):
        _policy(self.revision)
        if any(type(causes) is not frozenset or not causes
               or any(type(cause) is not str or not cause for cause in causes)
               for causes in (self.equipment_causes,self.resource_causes,self.source_causes)):
            raise ValueError('Immutable explicit resource cause rules required')
        if (type(self.combat_causes) is not frozenset
                or any(type(cause) is not str or not cause for cause in self.combat_causes)):
            raise ValueError('Immutable explicit combat resource causes required')


def load_resource_rules():
    """Startup-only immutable rules; does not activate any character profile."""
    policy=json.loads((OUT/'design/role-resources-v1.json').read_text(encoding='utf-8'))
    if (policy['revision']!='2026-10-23.role-resources.1'
            or policy['injury_profile']!='known_uninjured_max_equals_hp_max'
            or policy['equipment_causes']!=['equip','unequip','equipment_wear','equipment_repair']
            or policy['resource_causes']!=['medicine','inn_rest','npc_heal']
            or policy['source_only_causes']!=['inventory_change']
            or policy['combat_causes']!=['battle_terminal']):
        raise ValueError('Resource policy needs implementation review')
    return ResourceRules(policy['revision'],frozenset(policy['equipment_causes']),
        frozenset(policy['resource_causes']),frozenset(policy['source_only_causes']),
        frozenset(policy['combat_causes']))


def _scope(before,caps,rules):
    if (type(before) is not RoleResources or type(caps) is not ResourceCaps
            or type(rules) is not ResourceRules or before.policy!=rules.revision
            or before.caps.source.role_id!=caps.source.role_id):
        raise ValueError('Resource profile, projection role or policy mismatch')


def _transition(before,caps,hp,mp,cause):
    changed=(hp,mp,caps.hp_max,caps.mp_max)!=(before.hp,before.mp,before.caps.hp_max,before.caps.mp_max)
    after=RoleResources(before.version+int(changed),hp,mp,caps,before.policy)
    return ResourceTransition(before,before if after==before else after,cause)


def plan_resource_caps(before,caps,cause,rules):
    """Plan one reason-limited cap transition; caller owns complete-before CAS."""
    _scope(before,caps,rules)
    if type(cause) is not str:
        raise ValueError('Explicit resource transition cause required')
    a,b=before.caps.source,caps.source
    if cause=='explicit_migration':
        # Staged known legacy data only. The storage caller must prove its old
        # profile/current assets, write the migration receipt and retire the
        # old writer once; this pure plan creates no such authorization.
        return _transition(before,caps,min(before.hp,caps.hp_max),min(before.mp,caps.mp_max),cause)
    if cause=='ordinary_growth':
        if ((a.baseline_revision,a.attribute_policy,a.inventory_revision,a.equipment_basis_revision,a.equipment_policy)!=
                (b.baseline_revision,b.attribute_policy,b.inventory_revision,b.equipment_basis_revision,b.equipment_policy)
                or b.growth_revision<a.growth_revision or caps.hp_max<before.caps.hp_max
                or caps.mp_max<before.caps.mp_max):
            raise ValueError('Ordinary growth requires current unchanged equipment and nondecreasing final caps')
        if caps!=before.caps and b.growth_revision==a.growth_revision:
            raise ValueError('Changed growth caps need a newer actual growth revision')
        hp=0 if before.hp==0 else before.hp+caps.hp_max-before.caps.hp_max
        mp=before.mp+caps.mp_max-before.caps.mp_max
        return _transition(before,caps,hp,mp,cause)
    if cause not in rules.equipment_causes:
        raise ValueError('Unsupported resource cap transition cause')
    if ((a.baseline_revision,a.growth_revision,a.attribute_policy,a.equipment_basis_revision,a.equipment_policy)!=
            (b.baseline_revision,b.growth_revision,b.attribute_policy,b.equipment_basis_revision,b.equipment_policy)
            or b.inventory_revision<a.inventory_revision):
        raise ValueError('Equipment transition cannot alter naked growth or rewind assets')
    if (caps.hp_max,caps.mp_max)!=(before.caps.hp_max,before.caps.mp_max) and b.inventory_revision==a.inventory_revision:
        raise ValueError('Changed equipment caps need a newer actual inventory revision')
    return _transition(before,caps,min(before.hp,caps.hp_max),min(before.mp,caps.mp_max),cause)


def plan_resource_values(before,hp,mp,cause,rules,*,current_caps=None):
    """Accept a trusted medicine/rest result, bounded by the current final caps.

    The effect/price/authorization stays with its owning Module. This does not
    grant medicine, spend money or authorize revival. Caller applies this once
    with its asset/fee receipt; retry paths only read the existing current state.
    """
    if type(before) is not RoleResources:
        raise ValueError('Explicit current resource profile required')
    caps=before.caps if current_caps is None else current_caps
    _scope(before,caps,rules)
    if type(cause) is not str or cause not in rules.resource_causes:
        raise ValueError('Unsupported resource value transition cause')
    a,b=before.caps.source,caps.source
    if ((caps.hp_max,caps.mp_max)!=(before.caps.hp_max,before.caps.mp_max)
            or (a.baseline_revision,a.growth_revision,a.attribute_policy,a.equipment_basis_revision,a.equipment_policy)!=
               (b.baseline_revision,b.growth_revision,b.attribute_policy,b.equipment_basis_revision,b.equipment_policy)
            or b.inventory_revision<a.inventory_revision):
        raise ValueError('Resource values cannot replace a growth or equipment cap transition')
    _native(hp);_native(mp)
    if hp>caps.hp_max or mp>caps.mp_max or before.hp==0 and hp!=0:
        raise ValueError('Resource result exceeds final caps or attempts unauthorized revival')
    return _transition(before,caps,hp,mp,cause)


def plan_resource_source(before,caps,cause,rules):
    """Settle an inventory-only provenance change, without touching resources.

    Actual after caps come from the caller's current final projection. This is
    for grants, bag moves or objective debits, not a substitute for growth or
    equipment cap changes. Complete-before CAS remains a storage requirement.
    """
    _scope(before,caps,rules)
    a,b=before.caps.source,caps.source
    if (type(cause) is not str or cause not in rules.source_causes
            or (caps.hp_max,caps.mp_max)!=(before.caps.hp_max,before.caps.mp_max)
            or (a.baseline_revision,a.growth_revision,a.attribute_policy,a.equipment_basis_revision,a.equipment_policy)!=
               (b.baseline_revision,b.growth_revision,b.attribute_policy,b.equipment_basis_revision,b.equipment_policy)
            or b.inventory_revision<a.inventory_revision):
        raise ValueError('Source-only transition requires unchanged final caps and naked growth')
    return _transition(before,caps,before.hp,before.mp,cause)


def plan_combat_resources(before,hp,mp,rules):
    """Current ordinary physical battle result: consume only, no revive/heal."""
    if type(before) is not RoleResources:
        raise ValueError('Explicit current combat resource profile required')
    _scope(before,before.caps,rules);_native(hp);_native(mp)
    if 'battle_terminal' not in rules.combat_causes or hp>before.hp or mp>before.mp:
        raise ValueError('Ordinary combat result cannot increase resources')
    return _transition(before,before.caps,hp,mp,'battle_terminal')
