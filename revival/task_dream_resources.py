"""Pure, narrowly scoped authority for the approved first-dream recovery.

The Task PVE host creates this immutable message only after checking its durable
admission and genuine engine terminal. It is never decoded from client input.
Resource storage checks it again; ordinary medicine/growth rules stay unchanged.
"""
from dataclasses import dataclass
from battle_loadout import CombatResources
from role_resource_plan import RoleResources, ResourceTransition

POLICY_SHA256 = '2cbbe2cafe3151e49f21a4ec35dab0dd9d4aa9dca82b4b28016dfcb3c13a3c56'
POLICY_REVISION = '2026-10-24.task-pve-ai8001.1'
TASK_IDS = frozenset((100107,100205,100305,100405,100505,100605,100705,100805,100905,103207))


@dataclass(frozen=True)
class TaskDreamRevivePermit:
    role_id: int
    login_epoch: object
    task_id: int
    battle_id: str
    settlement_id: str
    recipe_revision: str
    recipe_sha256: str
    terminal_fingerprint: str
    raw_role: CombatResources
    raw_carrier_version: int


def _validate_raw(role_id, version, hp, mp, hp_max, mp_max, permit):
    if type(permit) is not TaskDreamRevivePermit:
        raise ValueError('Trusted dream terminal permit required')
    raw = permit.raw_role
    if (permit.recipe_sha256 != POLICY_SHA256 or permit.recipe_revision != POLICY_REVISION
            or type(permit.task_id) is not int or permit.task_id not in TASK_IDS
            or type(permit.role_id) is not int or permit.role_id != role_id
            or not ((type(permit.login_epoch) is int and permit.login_epoch > 0)
                or (type(permit.login_epoch) is str and 1 <= len(permit.login_epoch) <= 128))
            or type(permit.battle_id) is not str or not 1 <= len(permit.battle_id) <= 128
            or permit.settlement_id != 'task-battle:' + permit.battle_id
            or type(permit.terminal_fingerprint) is not str
            or len(permit.terminal_fingerprint) != 64
            or any(value not in '0123456789abcdef' for value in permit.terminal_fingerprint)
            or type(permit.raw_carrier_version) is not int or permit.raw_carrier_version != version
            or type(raw) is not CombatResources or raw.kind != 'role'
            or any(type(value) is not int for value in
                (raw.entity_id, raw.position, raw.source_version, raw.hp, raw.max_hp, raw.mp, raw.max_mp))
            or raw.entity_id != permit.role_id or raw.position != 1 or raw.source_version < 1
            or raw.escaped is not False or raw.inventory_revision is not None or raw.growth_revision
            or (raw.hp, raw.mp, raw.max_hp, raw.max_mp)
                != (hp, mp, hp_max, mp_max)
            or raw.hp != 0):
        raise ValueError('Dream recovery is not bound to this raw-dead current resource snapshot')


def plan_task_dream_revival(before, permit):
    """Recover only a known raw-dead role; preserve full caps and provenance."""
    if type(before) is not RoleResources:
        raise ValueError('Known current resource profile required')
    _validate_raw(before.caps.source.role_id, before.version, before.hp, before.mp,
                  before.caps.hp_max, before.caps.mp_max, permit)
    after = RoleResources(before.version + 1, before.caps.hp_max, before.caps.mp_max,
                          before.caps, before.policy)
    return ResourceTransition(before, after, 'task_dream_revive')


def plan_legacy_task_dream_revival(before, permit):
    """Known legacy carrier only; caller uses its existing full-CAS writer."""
    from item_effects import VitalState
    if type(before) is not VitalState:
        raise ValueError('Known legacy vital snapshot required; no inferred migration')
    _validate_raw(before.target_id, before.version, before.hp, before.mp,
                  before.max_hp, before.max_mp, permit)
    return VitalState(before.target_id, before.version + 1, before.max_hp,
                      before.max_hp, before.max_mp, before.max_mp)
