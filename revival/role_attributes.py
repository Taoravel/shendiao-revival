"""Pure versioned role attributes; caller supplies an explicit growth baseline.

No database, Session, packets, caches, locks or mutation of live characters.
Known client coefficients compose designed deltas; physical attack is designed.
"""
from dataclasses import dataclass, replace
import json
from pathlib import Path
from types import MappingProxyType
from inspect_client import OUT

NAMES = ('hp_max', 'mp_max', 'physical_attack', 'physical_defense',
         'hit', 'dodge', 'speed', 'magic_attack', 'magic_defense')
LIMIT = 2**31 - 1


def _integer(value, minimum=0):
    if type(value) is not int or not minimum <= value <= LIMIT:
        raise ValueError('Invalid or overflowing role attribute integer')
    return value


def _points(values):
    if type(values) is not tuple or len(values) != 5:
        raise ValueError('Exactly five immutable role points required')
    for value in values:
        _integer(value)
    return values


def _role_id(value):
    if type(value) is not int or not 1 <= value < 2**63:
        raise ValueError('Invalid role identity')


@dataclass(frozen=True)
class AttributeRules:
    revision: str
    growth_policy: str
    denominator: int
    coefficients: object
    per_level: object
    initial_profile: object = None


@dataclass(frozen=True)
class AttributeBaseline:
    role_id: int
    level: int
    revision: int
    five_stats: tuple
    values: tuple  # NAMES order; captured explicitly, never inferred from a level.

    def __post_init__(self):
        _role_id(self.role_id)
        _integer(self.level, 1)
        _integer(self.revision)
        _points(self.five_stats)
        if type(self.values) is not tuple or len(self.values) != len(NAMES):
            raise ValueError('Immutable baseline attribute values required')
        for name, value in zip(NAMES, self.values):
            _integer(value, 1 if name in ('hp_max', 'speed') else 0)


@dataclass(frozen=True)
class InitialRoleProfile:
    """Designed creation template, not permission to initialize an existing role."""
    level: int
    free_points: int
    five_stats: tuple
    values: tuple

    def __post_init__(self):
        _integer(self.level,1)
        _integer(self.free_points)
        _points(self.five_stats)
        if type(self.values) is not tuple or len(self.values)!=len(NAMES):
            raise ValueError('Immutable creation attribute values required')
        for name,value in zip(NAMES,self.values):
            _integer(value,1 if name in ('hp_max','speed') else 0)

    def baseline(self,role_id):
        return AttributeBaseline(role_id,self.level,0,self.five_stats,self.values)

    def vitals(self,role_id):
        from item_effects import VitalState
        _role_id(role_id)
        return VitalState(role_id,0,self.values[0],self.values[0],self.values[1],self.values[1])


@dataclass(frozen=True)
class RoleAttributes:
    role_id: int
    level: int
    baseline_revision: int
    growth_revision: int
    policy_revision: str
    five_stats: tuple
    hp_max: int
    mp_max: int
    physical_attack: int
    physical_defense: int
    hit: int
    dodge: int
    speed: int
    magic_attack: int
    magic_defense: int


def load_attribute_rules(path=None):
    """Startup-only read. Inject this immutable result into role owners."""
    path = Path(path) if path is not None else OUT/'design/role-attributes-v1.json'
    policy = json.loads(path.read_text(encoding='utf-8'))
    denominator = _integer(policy['coefficient_denominator'], 1)
    coefficients = {name: _points(tuple(policy['increment_coefficients'][name])) for name in NAMES}
    levels = {name: _integer(policy['extra_per_level'].get(name, 0)) for name in NAMES}
    initial=policy['new_role_designed_baseline']
    initial_profile=InitialRoleProfile(initial['level'],initial['free_points'],tuple(initial['five_stats']),
                                       tuple(initial[name] for name in NAMES))
    return AttributeRules(policy['revision'], policy['growth_policy'], denominator,
                          MappingProxyType(coefficients), MappingProxyType(levels),initial_profile)


def derive_attributes(baseline, growth, rules):
    """Use role_growth.GrowthState increments, not a fabricated initial profile."""
    if (not isinstance(baseline, AttributeBaseline) or not isinstance(rules, AttributeRules)
            or growth.role_id != baseline.role_id or growth.baseline_level != baseline.level
            or growth.policy != rules.growth_policy or growth.level < baseline.level):
        raise ValueError('Growth and attribute baseline scope mismatch')
    _integer(growth.level, 1)
    _role_id(growth.role_id)
    _integer(growth.revision)
    automatic, allocated = _points(growth.automatic_points), _points(growth.allocated_points)
    delta = tuple(_integer(a+b) for a, b in zip(automatic, allocated))
    stats = tuple(_integer(a+b) for a, b in zip(baseline.five_stats, delta))
    values = []
    for name, before in zip(NAMES, baseline.values):
        increase = sum(p*c for p, c in zip(delta, rules.coefficients[name])) // rules.denominator
        increase += rules.per_level[name] * (growth.level-baseline.level)
        values.append(_integer(before+increase, 1 if name in ('hp_max', 'speed') else 0))
    return RoleAttributes(baseline.role_id, growth.level, baseline.revision, growth.revision,
                          rules.revision, stats, *values)


def growth_vitals(before, attributes):
    """Return item_effects.VitalState; caller persists alongside growth/revision."""
    from item_effects import VitalState
    if (not isinstance(before, VitalState) or not isinstance(attributes, RoleAttributes)
            or before.target_id != attributes.role_id):
        raise ValueError('Vital snapshot role mismatch')
    _integer(attributes.hp_max, 1)
    _integer(attributes.mp_max)
    hp = 0 if before.hp == 0 else max(1, min(attributes.hp_max, before.hp+attributes.hp_max-before.max_hp))
    mp = max(0, min(attributes.mp_max, before.mp+attributes.mp_max-before.max_mp))
    return replace(before, version=before.version+1, hp=hp, max_hp=attributes.hp_max,
                   mp=mp, max_mp=attributes.mp_max)
