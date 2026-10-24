"""Confirmed ordinary-world resource refresh for item effects.

Only current HP/MP are sent. Maximum HP, wound cap and other attributes are not
inferred from a consumable. Caller supplies the latest authoritative snapshot.
"""
import struct
from item_effects import VitalState
from wire import compact

REFRESH_ROLE_DATA = 0xc32c8


def role_resource_refresh(vitals):
    if not isinstance(vitals,VitalState):
        raise ValueError('Authoritative role vital snapshot required')
    pairs=((60,vitals.hp),(70,vitals.mp))
    encoded=[]
    for key,value in pairs:
        if type(value) is not int or not 0<=value<=0x7fffffff:
            raise ValueError('Role resources exceed original signed integer consumer')
        packed=struct.pack('>f',value)
        if struct.unpack('>f',packed)[0]!=value:
            raise ValueError('Role resource is not exactly representable by original float field')
        encoded.append(struct.pack('>i',key)+packed)
    return REFRESH_ROLE_DATA,compact(len(pairs))+b''.join(encoded)
