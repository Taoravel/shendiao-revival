"""Confirmed ordinary-role growth requests; preserve opaque native fields."""
import struct

C_REQ_LEVEL_UP = 0xc32cd
C_ADD_POINT_TO_ATTR = 0xc000c
GROWTH_TYPES = frozenset((C_REQ_LEVEL_UP,C_ADD_POINT_TO_ATTR))


def decode_level_request(body):
    """Original body is one signed BE32; its business meaning is unconfirmed.

    The domain's designed ordinary mode accepts zero only. This decoder must
    not interpret the field as a client-authorized target level or XP amount.
    """
    if type(body) is not bytes or len(body)!=4:
        raise ValueError('Invalid native level request body')
    return struct.unpack('>i',body)[0]


def decode_allocation_request(body):
    """Return increments in internal V/I/S/END/AGI order.

    Native role UI sends V/I/S/AGI/END: the final two fields are exchanged.
    The request supplies no role identity, version or retry token. Eligibility,
    available points and the current revision belong to the role transaction.
    """
    if type(body) is not bytes or len(body)!=20:
        raise ValueError('Invalid native role allocation request body')
    values=struct.unpack('>5i',body)
    if min(values)<0:
        raise ValueError('Native role allocation increments must be nonnegative')
    return values[:3]+(values[4],values[3])
