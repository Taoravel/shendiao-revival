"""Role-owned wild encounter decisions from accepted map-owner snapshots.

The host serializes this module on the role's bounded mailbox. No file I/O,
network, database, map mutation or global queue occurs on the decision path.
Do not feed wire coordinates here: the map owner must accept movement first.
"""
from dataclasses import dataclass
from math import isqrt
from pathlib import Path
import json
from types import MappingProxyType
from uuid import uuid4
from battle import Fighter
from world_owner import Location, MoveResult

ROOT = Path(__file__).parent


@dataclass(frozen=True)
class WildMonster:
    template_id: int
    name: str
    shape_id: int
    catchable: bool


@dataclass(frozen=True)
class WildMap:
    map_id: int
    level: int
    background: int
    monsters: tuple[WildMonster, ...]
    encounter_mode: str = 'hidden'


@dataclass(frozen=True)
class EncounterRules:
    revision: str
    distance: int
    chance: int
    grace_ms: int
    cooldown_ms: int
    enemy_parameters: tuple
    maps: object


def load_wild_rules(root=ROOT):
    """Startup-only read; distribute this immutable snapshot to role owners."""
    root = Path(root)
    policy = json.loads((root/'design/wild-encounters-v1.json').read_text(encoding='utf-8'))
    rows = json.loads((root/'catalogs/wild-encounters.json').read_text(encoding='utf-8'))
    if (policy['revision'] != rows['revision'] or policy['enemy_count'] != 1
            or policy['cell_pixels'] != 16 or policy['maximum_attempts_per_report'] != 1
            or policy['selection'] != 'uniform_over_client_display_distribution'
            or policy['reward_policy'] != 'no_asset_rewards_until_role_owner_atomic_settlement_is_integrated'
            or policy['displacement_per_attempt_pixels'] < 1
            or not 0 <= policy['chance_basis_points'] <= 10000
            or min(policy['spawn_grace_ms'], policy['post_battle_cooldown_ms']) < 0):
        raise ValueError('Unsupported wild encounter policy')
    parameters = policy['enemy']
    if (any(type(v) is not int or v < 0 for v in parameters.values())
            or min(parameters['defense_level_divisor'], parameters['speed_level_divisor']) < 1
            or parameters['hp_base'] < 1):
        raise ValueError('Invalid enemy numeric policy')
    maps = {}
    for row in rows['maps']:
        monsters = tuple(WildMonster(m['template_id'], m['name'], m['shape_id'], m['catchable'])
                         for m in row['monsters'])
        if (not monsters or row['level'] < 1 or row['map_id'] in maps
                or len({m.template_id for m in monsters}) != len(monsters)
                or any(min(m.template_id, m.shape_id) < 1 or not m.name for m in monsters)):
            raise ValueError('Invalid wild map configuration')
        mode=row.get('encounter_mode','hidden')
        if mode not in ('hidden','visible'): raise ValueError('Unknown encounter mode')
        maps[row['map_id']] = WildMap(row['map_id'], row['level'], row['background'], monsters,mode)
    return EncounterRules(policy['revision'], policy['displacement_per_attempt_pixels'],
        policy['chance_basis_points'], policy['spawn_grace_ms'], policy['post_battle_cooldown_ms'],
        tuple(parameters.items()), MappingProxyType(maps))


@dataclass(frozen=True)
class EncounterTicket:
    encounter_id: str
    location: Location
    monster: WildMonster
    level: int
    background: int
    enemy: Fighter
    revision: str


class WildEncounters:
    """One role/login lifetime; one unresolved reservation at a time.

    accepted_move consumes exactly the last authoritative location and its
    accepted MoveResult. Host eligibility excludes team/dead/special modes.
    The host freezes gameplay before admitting ticket to a battle owner, then
    calls accepted or rejected on explicit acknowledgement. Timeout leaves the
    ticket pending until the authoritative battle admission is resolved.
    """
    def __init__(self, location, rules, *, now_ms, rng):
        if (not isinstance(location, Location) or location.state != 'active'
                or location.role_id < 1 or location.version < 1 or not location.login_epoch
                or type(now_ms) is not int or now_ms < 0):
            raise ValueError('Active authoritative role location required')
        self.location, self.rules, self.rng = location, rules, rng
        self._time = now_ms
        self._ready = now_ms + rules.grace_ms
        self._distance = 0
        self._pending = None
        self._battle_id = ''

    @property
    def pending(self): return self._pending

    def _clock(self, now_ms):
        if type(now_ms) is not int or now_ms < self._time:
            raise ValueError('Monotonic encounter clock required')
        self._time = now_ms

    def accepted_move(self, previous, result, *, now_ms, eligible):
        self._clock(now_ms)
        if type(eligible) is not bool or previous != self.location:
            raise ValueError('Stale encounter position or eligibility')
        if not isinstance(result, MoveResult) or result.rejection:
            raise ValueError('Accepted map result required')
        current = result.location
        if (not isinstance(current, Location) or current.role_id != previous.role_id
                or current.login_epoch != previous.login_epoch or current.address != previous.address
                or current.state != 'active' or previous.state != 'active'):
            raise ValueError('Encounter move changed lease/map/state')
        if result.checkpoint is None:
            if current != previous: raise ValueError('Intention changed authoritative position')
            return None
        if result.checkpoint != current or current.version != previous.version + 1:
            raise ValueError('Encounter position version mismatch')
        # Consume blocked/cooldown updates too; none may be replayed later.
        self.location = current
        area = self.rules.maps.get(current.address.map_id)
        if (not eligible or area is None or area.encounter_mode!='hidden' or result.offer is not None
                or self._pending is not None or now_ms < self._ready):
            self._distance = 0
            return None
        if (current.x//16, current.y//16) == (previous.x//16, previous.y//16):
            return None
        distance = isqrt((current.x-previous.x)**2 + (current.y-previous.y)**2)
        self._distance += min(distance, self.rules.distance)
        if self._distance < self.rules.distance: return None
        self._distance = 0
        if self.rng.randrange(10000) >= self.rules.chance: return None
        monster = area.monsters[self.rng.randrange(len(area.monsters))]
        p = dict(self.rules.enemy_parameters); level = area.level
        hp = p['hp_base'] + p['hp_per_level']*level
        enemy = Fighter(21, 1, hp=hp, max_hp=hp, mp=p['mp'],
            attack=p['attack_base'] + p['attack_per_level']*level,
            defense=p['defense_base'] + level//p['defense_level_divisor'],
            speed=p['speed_base'] + level//p['speed_level_divisor'])
        self._pending = EncounterTicket(uuid4().hex, current, monster, level, area.background, enemy, self.rules.revision)
        return self._pending

    def accepted(self, ticket, battle_id):
        if (ticket != self._pending or not ticket or self._battle_id
                or not isinstance(battle_id, str) or not 1 <= len(battle_id) <= 128):
            raise ValueError('Stale encounter admission')
        self._battle_id = battle_id

    def rejected(self, ticket, *, now_ms):
        self._clock(now_ms)
        if not ticket or ticket != self._pending or self._battle_id:
            raise ValueError('Only explicit pending admission rejection may release encounter')
        self._pending = None
        self._ready = now_ms + self.rules.cooldown_ms

    def finished(self, ticket, battle_id, *, now_ms):
        """Trusted battle-owner terminal acknowledgement, never a client end packet.

        The role owner must first handle resource settlement/abort resolution;
        this is only the encounter gate and never applies assets or rewards.
        """
        self._clock(now_ms)
        if not ticket or ticket != self._pending or not self._battle_id or battle_id != self._battle_id:
            raise ValueError('Stale encounter terminal event')
        self._pending, self._battle_id = None, ''
        self._distance = 0
        self._ready = now_ms + self.rules.cooldown_ms
