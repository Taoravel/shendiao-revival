"""Map-owned ephemeral normal-walking declarations, never client state claims.

The map executor supplies its current Location on every call. ConnectionOwner
alone acknowledges the exact message after write/drain; no client ACK, timer,
wire flag or persisted default supplies movement state.
"""
from dataclasses import dataclass, replace
import json
from types import MappingProxyType
import uuid

from inspect_client import OUT
from world_protocol import ENTER_SCENE, scene_entry


SET_ROLE_LOCATION = 0xc0fa4
UNSUPPORTED_JUMPS = (0xc0fcd, 0xc0fcf)


class SupersededMovementDelivery(ValueError):
    """A once-valid send completed after this exact member revoked its state."""


def load_movement_policy():
    policy = json.loads((OUT / 'design/world-movement-state-v1.json').read_text(encoding='utf-8'))
    if (policy['supported_state'] != 0 or policy['native_mask'] != 1
            or policy['collision_points'] != 'native_current'
            or policy['location_packet_type'] != SET_ROLE_LOCATION
            or policy['location_packet_flag'] != 0
            or tuple(policy['unsupported_jump_types']) != UNSUPPORTED_JUMPS
            or type(policy['special_scene_normalization_enabled']) is not bool):
        raise ValueError('Unsupported movement declaration policy')
    # Freeze the only containers consumed at runtime; no mutable JSON escapes.
    return MappingProxyType(dict(revision=policy['revision'],
        scene_reasons=tuple(policy['scene_declaration_reasons']),
        skip_maps=tuple(policy['scene_skip_map_ids']),
        special_normalization=policy['special_scene_normalization_enabled'],
        resume_sources=tuple(policy['location_resume_sources'])))


@dataclass(frozen=True)
class MovementDeclaration:
    declaration_id: str
    location: object
    map_generation: str
    context_generation: int
    connection_generation: int
    scene_token: str
    kind: int
    body: bytes
    source: str


@dataclass(frozen=True)
class MovementContext:
    location: object
    declaration: MovementDeclaration
    state: int = 0


class MapMovement:
    """Owned solely by one map executor; bounded by its current membership."""
    def __init__(self, policy):
        self.policy = policy
        self.generation = uuid.uuid4().hex
        self._versions, self._pending, self._contexts = {}, {}, {}

    def invalidate(self, location):
        key = (location.role_id, location.login_epoch)
        self._versions[key] = self._versions.get(key, 0) + 1
        self._pending.pop(location.role_id, None)
        self._contexts.pop(location.role_id, None)

    def leave(self, location):
        self._versions.pop((location.role_id, location.login_epoch), None)
        self._pending.pop(location.role_id, None)
        self._contexts.pop(location.role_id, None)

    def declare(self, location, connection_generation, scene_token, kind, body, source):
        import struct
        if (type(connection_generation) is not int or not 0 < connection_generation < 2**63
                or type(scene_token) is not str or not scene_token or type(body) is not bytes):
            raise ValueError('Explicit movement declaration identity required')
        if source == 'normal_scene':
            if (kind != ENTER_SCENE or location.address.map_id in self.policy['skip_maps']
                    or not any(body == scene_entry(location.position, reason=reason)
                               for reason in self.policy['scene_reasons'])):
                raise ValueError('Scene does not establish ordinary movement state')
        elif source in self.policy['resume_sources']:
            if (source == 'special_scene_normalization' and not self.policy['special_normalization']):
                raise ValueError('Special scene normalization is not enabled')
            if kind != SET_ROLE_LOCATION or body != struct.pack('>QhhB', location.role_id, location.x, location.y, 0):
                raise ValueError('Exact current authoritative location command required')
        else:
            raise ValueError('Unauthorized movement declaration source')
        self.invalidate(location)
        declaration = MovementDeclaration(uuid.uuid4().hex, location, self.generation,
            self._versions[(location.role_id, location.login_epoch)], connection_generation,
            scene_token, kind, body, source)
        self._pending[location.role_id] = declaration
        return declaration

    def confirm(self, declaration, current, *, transferred=False):
        if type(declaration) is not MovementDeclaration:
            raise ValueError('Exact pending movement declaration required')
        expected = declaration.location
        if transferred:
            if expected.state != 'loading':
                raise ValueError('Transfer declaration must precede matching ready transition')
            expected = replace(expected, state='active', version=expected.version+1)
        generation=self._versions.get((current.role_id,current.login_epoch))
        if (current==expected and declaration.map_generation==self.generation
                and generation is not None and generation>declaration.context_generation):
            raise SupersededMovementDelivery('Movement delivery superseded by current lifecycle')
        if (self._pending.get(current.role_id) != declaration or current != expected
                or current.state != 'active' or declaration.map_generation != self.generation
                or self._versions.get((current.role_id,current.login_epoch)) != declaration.context_generation):
            raise ValueError('Stale movement declaration or membership')
        context = MovementContext(current, declaration)
        self._contexts[current.role_id] = context
        del self._pending[current.role_id]
        return context

    def pending_current(self, declaration, current):
        return (type(declaration) is MovementDeclaration
            and self._pending.get(current.role_id) == declaration
            and declaration.location == current and declaration.map_generation == self.generation
            and self._versions.get((current.role_id,current.login_epoch)) == declaration.context_generation)

    def current(self, location):
        context = self._contexts.get(location.role_id)
        if context is None or context.location != location:
            raise ValueError('Movement waits for exact normal-state delivery')
        return context

    def advance(self, before, after):
        context = self.current(before)
        self._contexts[after.role_id] = replace(context, location=after)
