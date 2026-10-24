"""Pure original player screen/movement codecs; no AOI or authority mutation.

Unknown metadata remains named by its original object offset. RoleBasicOctets
is nested inside RoleBasic, which is the first SAddUserScreen collection.
"""
from dataclasses import dataclass
import struct
from wire import compact, octets

S_ADD_USER_SCREEN = 0xC0FA5
S_REMOVE_USER_SCREEN = 0xC0FA6
S_ROLE_MOVE = 0xC0FA2
S_ROLE_STOP = 0xC0FAB  # This image's Process is a no-op; not a movement guarantee.


@dataclass(frozen=True)
class RoleBasic:
    role_id: int
    name: str
    shape: int
    x: int
    y: int
    packed_2c: int
    field_4c: int = 0
    screen_flag: int = 0
    properties: tuple = ()
    octets_properties: tuple = ()
    path: tuple = ()


def _role_id(value):
    if type(value) is not int or not 0 < value < 2**63:
        raise ValueError('Role ID requires a positive signed int64')
    return value


def _points(points):
    points=tuple(points)
    if len(points)>4096:raise ValueError('Role path exceeds local bound')
    return compact(len(points))+b''.join(struct.pack('>hh',x,y) for x,y in points)


def _byte_map(entries, encode):
    entries=tuple(entries)
    if (len(entries)>256 or len({k for k,v in entries})!=len(entries)
            or any(type(k) is not int or not 0<=k<=255 for k,v in entries)):
        raise ValueError('Invalid original byte-key map')
    ordered=sorted(entries,key=lambda p:p[0] if p[0]<128 else p[0]-256)
    return compact(len(ordered))+b''.join(bytes([k])+encode(v) for k,v in ordered)


def role_basic_octets(role):
    _role_id(role.role_id)
    encoded=role.name.encode('utf-16le')
    if len(encoded)>512:raise ValueError('Role name exceeds local bound')
    return (struct.pack('>q',role.role_id)+octets(encoded)
            +struct.pack('>Bi',role.packed_2c,role.shape)
            +_byte_map(role.properties,lambda v:struct.pack('>i',v))
            +_byte_map(role.octets_properties,octets)+struct.pack('>B',role.field_4c))


def role_basic(role):
    return (octets(role_basic_octets(role))+struct.pack('>hhB',role.x,role.y,role.screen_flag)
            +_points(role.path))


def role_screen(roles):
    """SAddUserScreen body, original player collection plus empty NPC collection."""
    roles=tuple(roles)
    if len(roles)>4096 or len({r.role_id for r in roles})!=len(roles):
        raise ValueError('Invalid role screen batch')
    return compact(len(roles))+b''.join(role_basic(r) for r in roles)+b'\0'


def remove_role_screen(role_ids):
    role_ids=tuple(role_ids)
    if len(role_ids)>4096 or len(set(role_ids))!=len(role_ids):
        raise ValueError('Invalid role removal batch')
    return compact(len(role_ids))+b''.join(struct.pack('>q',_role_id(r)) for r in role_ids)+b'\0'


def role_move(role_id,x,y):
    return struct.pack('>qhh',_role_id(role_id),x,y)


def role_stop(role_id,x,y):
    """Original body only; the original SRoleStop handler does nothing."""
    return role_move(role_id,x,y)
