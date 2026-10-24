"""Complete optional ordinary gem profile as the original world attribute map.

Validate and freeze these bytes before the owner transaction commits; delivery
belongs to the connection owner afterward. Reuses all root ordinary fields and
adds the six explicit original numeric identities, including signed raw values.
"""
import struct
from role_attribute_protocol import growth_refresh as core_refresh
from role_equipment import EquipmentRoleSnapshot
from role_equipment_gems import EXTRA_IDS
from role_equipment_gem_storage import GemEquipmentProfile
from wire import compact,read_compact


def growth_refresh(growth,profile):
    if (type(profile) is not GemEquipmentProfile or type(profile.core) is not EquipmentRoleSnapshot
            or profile.core.equipment_policy!='2026-10-24.role-equipment-gems.1'
            or type(profile.extras) is not tuple or len(profile.extras)!=len(EXTRA_IDS)
            or any(type(pair) is not tuple or len(pair)!=2 or type(pair[0]) is not int for pair in profile.extras)
            or tuple(pair[0] for pair in profile.extras)!=EXTRA_IDS):
        raise ValueError('Complete current gem equipment profile required')
    kind,body=core_refresh(growth,profile.core)
    count,offset=read_compact(body)
    if count!=21 or len(body)!=offset+8*count:
        raise ValueError('Complete ordinary core refresh required')
    fields={struct.unpack_from('>i',body,offset+8*i)[0]:body[offset+8*i:offset+8*i+8] for i in range(count)}
    for key,value in profile.extras:
        if type(value) is not int or not -0x80000000<=value<=0x7fffffff or key in fields:
            raise ValueError('Distinct signed32 native gem attribute required')
        encoded=struct.pack('>f',value)
        if struct.unpack('>f',encoded)[0]!=value:raise ValueError('Inexact native gem attribute')
        fields[key]=struct.pack('>i',key)+encoded
    return kind,compact(len(fields))+b''.join(fields[key] for key in sorted(fields))
