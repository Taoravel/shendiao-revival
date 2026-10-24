"""Instance-owned NPC activation and interaction checks; no I/O in commands."""
from collections import Counter
from dataclasses import dataclass
import json
from types import MappingProxyType
from inspect_client import OUT
from world_entity_protocol import ADD_ACTIVITY_NPC, ADD_USER_SCREEN, VISIT_NPC_REPLY, NpcBasic, npc_screen, activity_npcs, read_visit_npc, visit_npc_reply
from world_catalog import valid_position
from npc_interaction import resolve_interaction_radius


@dataclass(frozen=True)
class NpcPlacement:
    placement_id: int
    npc_id: int
    map_id: int
    x: int
    y: int
    direction: int

    def __post_init__(self):
        if type(self.direction) is not int or not 0<=self.direction<=7:
            raise ValueError('Original NPC placement direction must be an integer0..7')


@dataclass(frozen=True)
class NpcInteraction:
    source_id: str
    role_id: int
    login_epoch: int | str
    address: object
    position_version: int
    entity_key: int
    npc_id: int
    placement_id: int
    kind: str = 'npc_interacted'
    position_validation: str = 'bounds_version_distance'


def load_placements(path=OUT/'catalogs/world.json'):
    """Startup-only snapshot. Repeated NPC IDs keep distinct placement IDs."""
    result = {}
    for row in json.loads(path.read_text(encoding='utf-8')):
        mid = int(row['attributes']['id'])
        result[mid] = tuple(NpcPlacement(i+1, int(p['id']), mid, int(p['posx']), int(p['posy']), int(p.get('dir', 0)))
                            for i, p in enumerate(row['npc_placements']))
    return MappingProxyType(result)


def load_npc_definitions(path=OUT/'catalogs/knight.gsp.npc.cnpcconfig.json'):
    return MappingProxyType({int(row['attributes']['id']): MappingProxyType(row['attributes'])
                             for row in json.loads(path.read_text(encoding='utf-8'))})


class NpcScene:
    def __init__(self, address, placements, catalog, *, interaction_radius=None, binding_capacity,
                 interaction_rules=None):
        interaction_radius=resolve_interaction_radius(interaction_rules,interaction_radius)
        if (interaction_radius is None and interaction_rules is None
                or interaction_radius is not None and interaction_radius<=0 or binding_capacity<1):
            raise ValueError('Explicit NPC radius and capacity required')
        self.address, self.catalog = address, catalog
        self.placements = MappingProxyType({p.placement_id: p for p in placements if p.map_id == address.map_id})
        self.radius, self.binding_capacity = interaction_radius, binding_capacity
        self.interaction_rules=interaction_rules
        self._bindings = {}

    def spawn(self, bindings, definitions, *, batch_size):
        """Real model path: independently keyed NpcBasic in SAddUserScreen.

        bindings is a server-issued tuple of (entity_key, placement_id). Encode
        the complete request before changing bindings, so invalid batches leave
        no partially registered entities. Delivery/AOI remains runtime-owned.
        """
        bindings = tuple(bindings)
        if not 1 <= batch_size <= 4096 or len({key for key, _ in bindings}) != len(bindings):
            raise ValueError('Invalid NPC spawn batch')
        if len(set(self._bindings) | {key for key, _ in bindings}) > self.binding_capacity:
            raise ValueError('NPC binding capacity')
        records = []
        for key, placement_id in bindings:
            npc = self.placements.get(placement_id)
            if (npc is None or npc.npc_id not in definitions or not 0 <= key <= 0x7fffffffffffffff
                    or not valid_position((npc.map_id, npc.x, npc.y), self.catalog)):
                raise ValueError('Invalid NPC spawn placement')
            if key in self._bindings and self._bindings[key] != placement_id:
                raise ValueError('NPC key conflict')
            records.append(NpcBasic(key, npc.npc_id, definitions[npc.npc_id].get('name', ''),
                npc.x, npc.y, field_48=npc.direction))
        packets = tuple((ADD_USER_SCREEN, npc_screen(records[i:i+batch_size]))
                        for i in range(0, len(records), batch_size))
        self._bindings.update(bindings)
        return packets

    def activation(self, batch_size):
        """Native activity IDs are unique. Withhold duplicates; never alias them.

        Normal static NPCs may already be loaded by the original scene loader.
        This only provides a codec-verified explicit activation candidate.
        """
        if not 1 <= batch_size <= 4096:
            raise ValueError('Invalid NPC batch size')
        counts = Counter(p.npc_id for p in self.placements.values())
        visible = tuple(p for p in self.placements.values() if counts[p.npc_id] == 1
                        and valid_position((p.map_id, p.x, p.y), self.catalog))
        return tuple((ADD_ACTIVITY_NPC, activity_npcs(tuple((p.npc_id, p.x, p.y) for p in visible[i:i+batch_size])))
                     for i in range(0, len(visible), batch_size))

    def bind(self, entity_key, placement_id):
        """Only a native-verified/server-owned entity-key assignment may call this.

        The visit packet cannot register or choose its own static NPC mapping.
        """
        if not 0 <= entity_key <= 0x7fffffffffffffff or placement_id not in self.placements:
            raise ValueError('Invalid NPC binding')
        existing = self._bindings.get(entity_key)
        if existing is not None:
            if existing != placement_id:
                raise ValueError('NPC key conflict')
            return
        if len(self._bindings) >= self.binding_capacity:
            raise ValueError('NPC binding capacity')
        self._bindings[entity_key] = placement_id

    def interact(self, body, expected, current, *, request_id, deadline_ms, now_ms):
        if not request_id or len(request_id) > 128 or now_ms >= deadline_ms:
            raise ValueError('Invalid or expired NPC command')
        if current != expected or current.address != self.address or current.state != 'active':
            raise ValueError('Stale NPC interaction scope')
        if not valid_position(current.position, self.catalog):
            raise ValueError('Invalid role position')
        key = read_visit_npc(body)
        placement_id = self._bindings.get(key)
        if placement_id is None:
            raise ValueError('Unknown NPC entity key')
        npc = self.placements[placement_id]
        if not valid_position((npc.map_id, npc.x, npc.y), self.catalog):
            raise ValueError('NPC outside available map')
        nearby=((current.x-npc.x)**2+(current.y-npc.y)**2<=self.radius**2 if self.interaction_rules is None
            else self.interaction_rules.allows(npc,current.position))
        if not nearby:
            raise ValueError('NPC out of interaction range')
        return NpcInteraction(request_id, current.role_id, current.login_epoch, self.address,
                              current.version, key, npc.npc_id, npc.placement_id)

    def visit(self, body, expected, current, *, request_id, deadline_ms, now_ms):
        event = self.interact(body, expected, current, request_id=request_id,
                              deadline_ms=deadline_ms, now_ms=now_ms)
        # Empty native menu is a display probe, not quest/service completion.
        return event, ((VISIT_NPC_REPLY, visit_npc_reply(event.entity_key)),)
