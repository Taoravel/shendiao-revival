"""Monster templates and instance-owned visible entities, without invented stats.

Render via the native NpcBasic shape override on an explicitly supplied valid
NPC carrier. The carrier choice is a restoration policy, not original spawn data.
"""
from dataclasses import dataclass, replace
import json
from types import MappingProxyType
from uuid import uuid4
from inspect_client import OUT
from world_catalog import valid_position
from world_entity_protocol import NpcBasic, npc_screen, remove_npc_screen, ADD_USER_SCREEN, REMOVE_USER_SCREEN


@dataclass(frozen=True)
class MonsterTemplate:
    template_id: int
    name: str
    shape_id: int
    catchable: bool
    attributes: tuple


@dataclass(frozen=True)
class MonsterEntity:
    entity_key: int
    template_id: int
    carrier_npc_id: int
    address: object
    x: int
    y: int
    revision: int = 1
    state: str = 'visible'
    battle_id: str = ''
    claimant_role_id: int = 0
    claimant_epoch: int | str = ''
    owner_generation: str = ''


def load_monster_templates():
    rows = json.loads((OUT/'catalogs/knight.gsp.npc.cmonsterconfig.json').read_text(encoding='utf-8'))
    return MappingProxyType({int(a['id']): MonsterTemplate(int(a['id']), a.get('name', ''),
        int(a['modelID']), a['becatch'] == '1', tuple(sorted(a.items())))
        for a in (r['attributes'] for r in rows)})


def load_shape_ids():
    return frozenset(int(r['attributes']['id']) for r in json.loads(
        (OUT/'catalogs/knight.gsp.npc.cnpcshape.json').read_text(encoding='utf-8')))


class MonsterScene:
    def __init__(self, address, catalog, templates, npc_definitions, shape_ids, *, capacity):
        if capacity < 1: raise ValueError('Explicit monster capacity required')
        self.address, self.catalog, self.templates = address, catalog, templates
        self.npc_definitions, self.shape_ids, self.capacity = npc_definitions, shape_ids, capacity
        self._entities = {}
        self._revision = 0
        self._generation = uuid4().hex

    def snapshot(self, key):
        return self._entities.get(key)

    def spawn(self, key, template_id, x, y, *, carrier_npc_id):
        if key in self._entities or not 0 <= key <= 0x7fffffffffffffff:
            raise ValueError('Invalid or occupied monster key')
        if len(self._entities) >= self.capacity: raise ValueError('Monster capacity')
        template = self.templates.get(template_id)
        if template is None or template.shape_id not in self.shape_ids:
            raise ValueError('Monster template or original shape unavailable')
        if carrier_npc_id not in self.npc_definitions:
            raise ValueError('Explicit valid NPC render carrier required')
        if not valid_position((self.address.map_id, x, y), self.catalog):
            raise ValueError('Monster outside available map')
        # +0x4c is a native-verified model override. Monster IDs are never passed
        # as NPC config IDs; battle/drop tables are not fabricated here.
        packet = (ADD_USER_SCREEN, npc_screen((NpcBasic(key, carrier_npc_id, template.name,
                                                     x, y, field_4c=template.shape_id),)))
        self._revision += 1
        entity = MonsterEntity(key, template_id, carrier_npc_id, self.address, x, y,
                               revision=self._revision, owner_generation=self._generation)
        self._entities[key] = entity
        return entity, (packet,)

    def remove(self, expected):
        if (self.snapshot(expected.entity_key) != expected or expected.address != self.address
                or expected.state != 'visible'):
            raise ValueError('Stale monster removal')
        packet = (REMOVE_USER_SCREEN, remove_npc_screen((expected.entity_key,)))
        del self._entities[expected.entity_key]
        return packet

    def encounter(self, expected, role, *, interaction_radius, battle_id):
        """Reserve a visible monster; battle owner supplies its actual stats.

        Input role is an authoritative map snapshot. The caller routes a battle
        request, not a victory/reward. No task completion is emitted here.
        """
        if (self.snapshot(expected.entity_key) != expected or expected.state != 'visible'
                or role.address != self.address or role.state != 'active'
                or not valid_position(role.position, self.catalog)
                or interaction_radius <= 0 or not battle_id or len(battle_id) > 128):
            raise ValueError('Invalid monster encounter scope')
        if (role.x-expected.x)**2+(role.y-expected.y)**2 > interaction_radius**2:
            raise ValueError('Monster outside encounter range')
        self._revision += 1
        reserved = replace(expected, revision=self._revision, state='reserved', battle_id=battle_id,
                           claimant_role_id=role.role_id, claimant_epoch=role.login_epoch)
        self._entities[expected.entity_key] = reserved
        return reserved

    def cancel_encounter(self, expected):
        """Release a reservation after the battle owner explicitly rejects it.

        A timeout alone is not rejection. Callers must resolve the battle's
        authoritative acceptance state before issuing this map-owner command.
        A stale rejection cannot release a later reservation of the same key.
        """
        if self.snapshot(expected.entity_key) != expected or expected.state != 'reserved':
            raise ValueError('Stale or active monster encounter cancellation')
        self._revision += 1
        restored = replace(expected, revision=self._revision, state='visible',
                           battle_id='', claimant_role_id=0, claimant_epoch='')
        self._entities[expected.entity_key] = restored
        return restored

    def confirm_encounter(self, expected):
        """Record explicit acceptance from the battle owner of this reservation."""
        if self.snapshot(expected.entity_key) != expected or expected.state != 'reserved':
            raise ValueError('Stale monster battle acceptance')
        self._revision += 1
        active = replace(expected, revision=self._revision, state='in_battle')
        self._entities[expected.entity_key] = active
        return active

    def end_encounter(self, expected, *, despawn):
        """Apply a trusted terminal battle result with an explicit disposition.

        The caller validates the battle result and chooses the source-backed
        world policy. This method never infers victory, issues rewards, changes
        role/task data, or chooses a respawn delay. Timeout is not a result.
        """
        if (self.snapshot(expected.entity_key) != expected or expected.state != 'in_battle'
                or type(despawn) is not bool):
            raise ValueError('Stale or incomplete monster battle result')
        if despawn:
            packet = (REMOVE_USER_SCREEN, remove_npc_screen((expected.entity_key,)))
            del self._entities[expected.entity_key]
            return None, (packet,)
        self._revision += 1
        restored = replace(expected, revision=self._revision, state='visible',
                           battle_id='', claimant_role_id=0, claimant_epoch='')
        self._entities[expected.entity_key] = restored
        return restored, ()
