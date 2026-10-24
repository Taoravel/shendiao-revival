"""Confirmed original task/NPC display wire bodies, without business effects.

The character owner supplies committed balances. These functions do not grant
rewards, complete tasks, start dialogue, or send packets themselves.
See evidence/TASK_DIALOG_PROTOCOL.md for native addresses and limitations.
"""
import struct

from wire import compact, read_compact

S_REFRESH_USER_EXP = 0xC000D
S_VISIT_NPC = 0xC232A


def encode_user_experience(balance):
    """Absolute current experience balance, not gained experience (8 BE bytes)."""
    if not isinstance(balance, int) or not 0 <= balance < 2**63:
        raise ValueError('Experience balance must fit a nonnegative signed int64')
    return struct.pack('>Q', balance)


def decode_user_experience(body):
    if len(body) != 8:
        raise ValueError('SRefreshUserExp body must contain exactly 8 bytes')
    return struct.unpack('>Q', body)[0]


def _encode_ids(values):
    values = tuple(values)
    return compact(len(values)) + b''.join(struct.pack('>i', value) for value in values)


def encode_visit_npc(npc_key, first_ids=(), second_ids=()):
    """SVisitNpc: npc key, service IDs (first), task IDs (second).

    Empty lists do not invent NPC services or assume that any task is complete.
    The caller must provide a real scene NPC key and authorized menu entries.
    Task dialogue text is read from the original local task configuration.
    """
    if not 0 <= npc_key < 2**63:
        raise ValueError('NPC key must fit a nonnegative signed int64')
    return struct.pack('>Q', npc_key) + _encode_ids(first_ids) + _encode_ids(second_ids)


def decode_visit_npc(body):
    if len(body) < 10:
        raise ValueError('Truncated SVisitNpc body')
    npc_key = struct.unpack_from('>Q', body)[0]
    offset = 8
    vectors = []
    for _ in range(2):
        count, offset = read_compact(body, offset)
        end = offset + count * 4
        if end > len(body):
            raise ValueError('Truncated NPC ID vector')
        vectors.append([v[0] for v in struct.iter_unpack('>i', body[offset:end])])
        offset = end
    if offset != len(body):
        raise ValueError('Unexpected bytes after SVisitNpc body')
    return npc_key, vectors[0], vectors[1]
