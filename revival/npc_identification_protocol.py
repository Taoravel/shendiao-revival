"""Original identification wire shapes, without service or asset authority.

The query has an ordered vector, not a set. NPC identity uses all 64 wire bits;
map ownership decides whether an identity is admissible. Explicit item budgets
belong to the caller. Mode values are wire data, not permission to identify.
"""
from dataclasses import dataclass
import struct
from wire import compact,read_compact,NeedMoreData

QUERY_IDENTIFICATION = 0xc04cc
IDENTIFICATION_STATES = 0xc04cd
IDENTIFY_EQUIPMENT = 0xc4276


@dataclass(frozen=True)
class IdentificationQuery:
    item_keys: tuple
    npc_key: int
    mode: int


@dataclass(frozen=True)
class IdentificationRequest:
    item_key: int
    auxiliary_argument: int
    mode: int


def decode_identification_query(body,*,max_items):
    if type(body) is not bytes or type(max_items) is not int or not 0<max_items<=0xffffffff:
        raise ValueError('Identification query requires bytes and an explicit item budget')
    try:count,offset=read_compact(body)
    except NeedMoreData:raise ValueError('Truncated identification query') from None
    if count>max_items or len(body)!=offset+count*4+12:
        raise ValueError('Identification query size or item budget exceeded')
    keys=tuple(struct.unpack_from('>i',body,offset+i*4)[0] for i in range(count))
    npc_key,mode=struct.unpack_from('>Qi',body,offset+count*4)
    return IdentificationQuery(keys,npc_key,mode)


def encode_identification_states(npc_key,states,mode,*,max_items):
    if (type(npc_key) is not int or not 0<=npc_key<2**64
            or type(mode) is not int or not -2**31<=mode<2**31
            or type(max_items) is not int or not 0<max_items<=0xffffffff
            or type(states) is not tuple or len(states)>max_items
            or any(type(row) is not tuple or len(row)!=2
                or any(type(value) is not int for value in row)
                or not 0<row[0]<2**31 or not -2**31<=row[1]<2**31 for row in states)):
        raise ValueError('Invalid or over-budget original identification states')
    return (struct.pack('>Q',npc_key)+compact(len(states))
        +b''.join(struct.pack('>ii',*row) for row in states)+struct.pack('>i',mode))


def decode_identification_request(body):
    """NPC confirmation sends (item_key, 0, 1); other modes need own authority.

    The second field is preserved without assigning a currency, column or NPC
    identity meaning. The original codec accepts every signed32 field value.
    """
    if type(body) is not bytes or len(body)!=12:
        raise ValueError('Identification confirmation must contain three signed integers')
    return IdentificationRequest(*struct.unpack('>iii',body))
