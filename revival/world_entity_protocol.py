"""Pure scene-entity wire codecs verified against the original 1.6.1 image.

Unknown NpcBasic fields retain their object-offset names. Static activity NPCs
use config IDs and positions, not dynamic entity keys or monster template IDs.
"""
from dataclasses import dataclass
import struct
from wire import compact as compact_uint, octets

ADD_ACTIVITY_NPC = 0xc0fbf
REMOVE_ACTIVITY_NPC = 0xc0fc0
VISIT_NPC = 0xc2329
NPC_SERVICE = 0xc232b
VISIT_NPC_REPLY = 0xc232a
ADD_USER_SCREEN = 0xc0fa5
REMOVE_USER_SCREEN = 0xc0fa6


def remove_npc_screen(keys):
    keys = tuple(keys)
    if len(keys) > 4096:
        raise ValueError('scene entity batch exceeds local bound')
    return b'\0' + compact_uint(len(keys)) + b''.join(struct.pack('>q', k) for k in keys)


def npc_screen(npcs):
    """SAddUserScreen with an empty role list and bounded NpcBasic list."""
    npcs = tuple(npcs)
    if len(npcs) > 4096 or len({n.key for n in npcs}) != len(npcs):
        raise ValueError('invalid NPC screen batch')
    return b'\0' + compact_uint(len(npcs)) + b''.join(npc_basic(n) for n in npcs)


def read_visit_npc(payload):
    if len(payload) != 8:
        raise ValueError('CVisitNpc requires exactly 8 bytes')
    key, = struct.unpack('>q', payload)
    if key < 0:
        raise ValueError('native CVisitNpc rejects negative keys')
    return key


def read_npc_service(payload):
    if len(payload) != 12:
        raise ValueError('CNpcService requires exactly 12 bytes')
    return struct.unpack('>qi', payload)


def visit_npc_reply(key, vector_10=(), vector_20=()):
    """SVisitNpc; two i32 vectors whose menu semantics remain unverified."""
    first, second = tuple(vector_10), tuple(vector_20)
    if key < 0 or max(len(first), len(second)) > 4096:
        raise ValueError('invalid NPC visit reply')
    return (struct.pack('>q', key) + compact_uint(len(first))
            + b''.join(struct.pack('>i', v) for v in first)
            + compact_uint(len(second)) + b''.join(struct.pack('>i', v) for v in second))


def activity_npcs(placements):
    """Encode aligned (config_id, x, y) collections; positions are logical pixels."""
    placements = tuple(placements)
    if len(placements) > 4096:
        raise ValueError('scene entity batch exceeds local bound')
    count = compact_uint(len(placements))
    return (count + b''.join(struct.pack('>i', p[0]) for p in placements)
            + count + b''.join(struct.pack('>hh', p[1], p[2]) for p in placements))


def remove_activity_npcs(config_ids):
    ids = tuple(config_ids)
    if len(ids) > 4096:
        raise ValueError('scene entity batch exceeds local bound')
    return compact_uint(len(ids)) + b''.join(struct.pack('>i', i) for i in ids)


@dataclass(frozen=True)
class NpcBasic:
    key: int
    config_id: int
    name: str
    x: int
    y: int
    field_38: int = 0
    field_40: int = 0
    field_42: int = 0
    field_44: int = 0
    field_48: int = 0
    field_4c: int = 0
    field_50: int = 0
    properties: tuple = ()


def npc_basic(npc):
    """Encode dynamic NpcBasic; field semantics beyond key/config/name/pos unproven."""
    properties = tuple(npc.properties)
    if not 0 <= npc.key <= 0x7fffffffffffffff:
        raise ValueError('NPC key outside nonnegative signed int64')
    if len(properties) > 256 or len({k for k, v in properties}) != len(properties):
        raise ValueError('invalid NPC property map')
    return (struct.pack('>Qi', npc.key, npc.config_id)
            + octets(npc.name.encode('utf-16-le'))
            + struct.pack('>hhBhh4i', npc.x, npc.y, npc.field_38,
                          npc.field_40, npc.field_42, npc.field_44,
                          npc.field_48, npc.field_4c, npc.field_50)
            + compact_uint(len(properties))
            + b''.join(struct.pack('>Bi', k, v) for k, v in sorted(properties)))
