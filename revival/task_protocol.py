"""Original ScenarioQuest wire layouts; no task rules or reward policy.

See evidence/TASK_PROTOCOL.md. Encoders return bodies, not framed packets.
Opaque value fields deliberately retain their original uncertainty.
"""
from dataclasses import dataclass
import struct

from wire import compact, read_compact

C_COMMIT_SCENARIO_QUEST = 0xC4A44
S_ACCEPT_SCENARIO_QUEST = 0xC4A45
S_REFRESH_SCENARIO_QUEST_STATE = 0xC4A47
S_REFRESH_SCENARIO_QUEST_VALUE = 0xC4A49
C_TRACK_QUEST = 0xC4A4A
S_TRACK_QUEST = 0xC4A4B
C_REQUEST_QUEST_CAN_ACCEPT = 0xC4A50
S_REQUEST_QUEST_CAN_ACCEPT = 0xC4A51
C_QUEST_DIALOG_END = 0xC4A52
C_QUEST_REACH_SCENE = 0xC4A54
S_TRACKED_QUESTS = 0xC4A55
C_REQUEST_REWARD = 0xC4A87
C_VISIT_NPC = 0xC2329
C_NPC_SERVICE = 0xC232B

# Original tracker 0x160daa0: state 2 selects the explicit failure row.
SCENARIO_ACTIVE = 0
SCENARIO_REMOVE = 1
SCENARIO_FAILED = 2
SCENARIO_READY = 3


@dataclass(frozen=True)
class ScenarioQuestInfo:
    quest_id: int
    state: int
    value1: int
    value2: int
    npc_key: int


def _unpack(fmt, body):
    if len(body) != struct.calcsize(fmt):
        raise ValueError('Unexpected task protocol body length')
    return struct.unpack(fmt, body)


def decode_empty_request(body):
    _unpack('>', body)


def encode_quest_can_accept(quest_ids):
    """SRequestQuestCanAccept: compact count followed by signed BE i32 IDs."""
    ids = tuple(quest_ids)
    return compact(len(ids)) + b''.join(struct.pack('>i', q) for q in ids)


def decode_quest_can_accept(body):
    count, offset = read_compact(body)
    if len(body) - offset != count * 4:
        raise ValueError('Unexpected can-accept list length')
    return [entry[0] for entry in struct.iter_unpack('>i', body[offset:])]


def encode_accept_scenario_quest(info):
    """24 bytes; state/value1/value2 must come from known task state."""
    if info.quest_id < 0 or info.state < 0 or not 0 <= info.npc_key < 2**63:
        raise ValueError('ScenarioQuestInfo violates original scalar constraints')
    return struct.pack('>iiiiQ', info.quest_id, info.state, info.value1,
                       info.value2, info.npc_key)


def decode_accept_scenario_quest(body):
    return ScenarioQuestInfo(*_unpack('>iiiiQ', body))


def encode_scenario_state(quest_id, state):
    if not 1001 <= quest_id <= 499999:
        raise ValueError('Quest ID outside original state-protocol range')
    return struct.pack('>ii', quest_id, state)


def decode_scenario_state(body):
    return _unpack('>ii', body)


def encode_scenario_values(quest_id, value1, value2):
    if not 1001 <= quest_id <= 499999:
        raise ValueError('Quest ID outside original value-protocol range')
    return struct.pack('>iii', quest_id, value1, value2)


def decode_scenario_values(body):
    return _unpack('>iii', body)


def decode_commit_scenario_quest(body):
    """Returns quest_id, npc_key, final opaque i32 (often zero in client UI)."""
    return _unpack('>iQi', body)


def decode_quest_dialog_end(body):
    return _unpack('>i', body)[0]


def decode_request_reward(body):
    return _unpack('>i', body)[0]


def decode_track_quest(body):
    quest_id, tracked = _unpack('>ii', body)
    if tracked not in (0, 1):
        raise ValueError('Original track flag permits only 0 or 1')
    return quest_id, tracked


def encode_track_quest(quest_id, tracked):
    if tracked not in (0, 1):
        raise ValueError('Original track flag permits only 0 or 1')
    return struct.pack('>ii', quest_id, tracked)


def encode_tracked_quests(quests):
    """Map of quest ID to original opaque u64 TrackedQuest field."""
    entries = sorted(quests.items())
    return compact(len(entries)) + b''.join(struct.pack('>iQ', q, value)
                                             for q, value in entries)


def decode_tracked_quests(body):
    count, offset = read_compact(body)
    if len(body) - offset != count * 12:
        raise ValueError('Unexpected tracked-quests map length')
    entries = list(struct.iter_unpack('>iQ', body[offset:]))
    result = dict(entries)
    if len(result) != count:
        raise ValueError('Duplicate tracked quest IDs')
    return result


def decode_visit_npc(body):
    return _unpack('>Q', body)[0]


def decode_npc_service(body):
    return _unpack('>Qi', body)
