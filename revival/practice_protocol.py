"""Native personal practice shapes; NPC proof is required above this codec."""
import struct
from role_practice import PracticeState
from wire import compact

PRACTISE_SKILL=0xc36cc
UPDATE_ASSIST_SKILL=0xc36b7
FACTION_PRACTICE=0xc5654


def request(body):
    if type(body) is not bytes or len(body)!=13:raise ValueError('invalid_practice_packet')
    npc,skill,mode=struct.unpack('>QiB',body)
    if not 0<npc<2**63 or skill<=0 or mode>4:raise ValueError('invalid_practice_packet')
    return npc,skill,mode


def update(state):
    if (not isinstance(state,PracticeState) or state.skill<=0 or any(type(n) is not int or not 0<=n<2**31
        for n in (state.skill,state.level,state.experience))):raise ValueError('invalid_practice_update')
    return struct.pack('>iii',state.skill,state.level,state.experience)


def open_types(opened):
    """Current seven-type map, including explicit closed entries."""
    if (type(opened) is not tuple or len(opened)>7 or len(set(opened))!=len(opened)
        or any(type(s) is not int or not 360001<=s<=360007 for s in opened)):
        raise ValueError('invalid_open_practice_types')
    return compact(7)+b''.join(struct.pack('>ii',s,int(s in opened)) for s in range(360001,360008))
