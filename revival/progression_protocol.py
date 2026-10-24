"""Native level-up request framing; business mode is checked by growth policy.

Evidence: ROLE_PROGRESSION_RESEARCH.md, constructor d57d30 / marshal e411a0.
The one field remains opaque; it is not a level, target, count or EXP amount.
"""
import struct

C_REQ_LEVEL_UP = 0xc32cd


def decode_level_up_request(body):
    if len(body) != 4:
        raise ValueError('Level-up request requires one BE32 field')
    return struct.unpack('>I',body)[0]
