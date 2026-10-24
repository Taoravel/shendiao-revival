"""Ordinary-world role growth display from a committed, versioned snapshot.

Native routing is independently traced in ROLE_GROWTH_UI_RESEARCH.md.
No battle-only initializer, storage access, sends or historical receipt reuse.
"""
import struct
from dataclasses import dataclass
from role_attribute_storage import RoleAttributeSnapshot
from role_growth import GrowthState
from role_equipment import EquipmentRoleSnapshot
from wire import compact

REFRESH_ROLE_DATA = 0xc32c8
_SUPPORTED = frozenset((10,20,30,40,50,60,70,80,100,110,120,130,140,150,490,500,640,810,820,1230,1240))
_COMBAT = ((80,'physical_attack'),(100,'physical_defense'),(110,'hit'),(120,'dodge'),
           (130,'speed'),(810,'magic_attack'),(820,'magic_defense'))


@dataclass(frozen=True)
class RoleDetailProfile:
    values: tuple
    five_stats: tuple
    potential: int


def _integer(value):
    if type(value) is not int or not 0 <= value <= 0x7fffffff:
        raise ValueError('Ordinary role attribute exceeds native nonnegative signed32')
    return value


def encode_role_attributes(values):
    """Encode known native attribute IDs; refuse float rounding before commit."""
    if type(values) is not tuple or not values or len(values)>len(_SUPPORTED):
        raise ValueError('Immutable ordinary attribute pairs required')
    data={}
    for pair in values:
        if type(pair) is not tuple or len(pair)!=2:
            raise ValueError('Invalid ordinary role attribute pair')
        key,value=pair
        if type(key) is not int or key not in _SUPPORTED or key in data:
            raise ValueError('Unknown or repeated ordinary role attribute')
        value=_integer(value)
        packed=struct.pack('>f',value)
        if struct.unpack('>f',packed)[0]!=value:
            raise ValueError('Ordinary role attribute is not exactly representable by native float')
        data[key]=packed
    return REFRESH_ROLE_DATA,compact(len(data))+b''.join(struct.pack('>i',key)+data[key] for key in sorted(data))


def _snapshot(role_id,snapshot):
    if not isinstance(snapshot,RoleAttributeSnapshot):
        raise ValueError('Explicit role attribute snapshot required')
    a,v=snapshot.attributes,snapshot.vitals
    if (type(role_id) is not int or not 0<role_id<2**63 or a.role_id!=role_id or v.target_id!=role_id
            or (v.max_hp,v.max_mp)!=(a.hp_max,a.mp_max)):
        raise ValueError('Role attribute/vital snapshot scope or maxima mismatch')
    return a,v


def _growth_snapshot(growth,snapshot):
    if not isinstance(growth,GrowthState):
        raise ValueError('Current role growth snapshot required')
    a,v=_snapshot(growth.role_id,snapshot)
    if ((a.level,a.growth_revision)!=(growth.level,growth.revision)
            or type(a.five_stats) is not tuple or len(a.five_stats)!=5):
        raise ValueError('Stale role growth display snapshot')
    for value in a.five_stats:
        if _integer(value)>32767:
            raise ValueError('Ordinary role five stats exceed native entry signed16 fields')
    _integer(growth.free_points)
    return a,v


def growth_refresh(growth,snapshot):
    """Validate/encode inside the owner transaction; send only after it commits.

    Level490 and potential500 are ordinary ROLE keys confirmed independently
    of pet messages. Wound limit640=maxHP is this explicit restoration profile's
    uninjured design; a future injury model must supply its own authoritative cap.
    """
    a,v=_growth_snapshot(growth,snapshot)
    pairs=((490,a.level),(500,growth.free_points),(60,v.hp),(70,v.mp),
           (140,a.hp_max),(150,a.mp_max),(640,a.hp_max))
    pairs+=tuple(zip((10,20,30,40,50),a.five_stats))
    pairs+=tuple((key,getattr(a,name)) for key,name in _COMBAT)
    if isinstance(snapshot,EquipmentRoleSnapshot):
        pairs+=((1230,snapshot.seal_strength),)
        if snapshot.seal_resistance is not None:pairs+=((1240,snapshot.seal_resistance),)
    return encode_role_attributes(pairs)


def role_detail_profile(growth,snapshot):
    """Known complete entry fields from the same current growth/display state.

    Original constructor zeros remain for unidentified32i slots. Five signed16
    stats are V/I/S/END/AGI (unlike the add-point request's last two fields).
    Unknown legacy profiles do not call this Interface. Potential is current,
    not a creation default or value recovered from a historical receipt.
    """
    a,v=_growth_snapshot(growth,snapshot)
    values=[0]*32
    values[:5]=role_detail_vitals(growth.role_id,snapshot)
    for index,name in ((7,'hit'),(8,'physical_attack'),(9,'physical_defense'),
                       (10,'speed'),(11,'dodge'),(12,'magic_attack'),(13,'magic_defense')):
        values[index]=_integer(getattr(a,name))
    if isinstance(snapshot,EquipmentRoleSnapshot):
        values[14]=_integer(snapshot.seal_strength)
        if snapshot.seal_resistance is not None:values[15]=_integer(snapshot.seal_resistance)
    return RoleDetailProfile(tuple(values),a.five_stats,_integer(growth.free_points))


def role_detail_vitals(role_id,snapshot):
    """Known first five RoleDetail int32 slots for an explicit uninjured profile.

    Order: current HP, wound limit, maximum HP, current MP, maximum MP.
    Unknown profiles must use the caller's separate compatibility path, never
    fabricate a profile here. Ordinary growth values are not equipment/buff sums.
    """
    a,v=_snapshot(role_id,snapshot)
    return tuple(_integer(x) for x in (v.hp,a.hp_max,a.hp_max,v.mp,a.mp_max))


def role_detail_equipment_fields(role_id,snapshot):
    """Known RoleDetail 32i indices, only from an explicit final projection.

    Unprojected legacy/growth snapshots supply no invented sealing baseline.
    Native consumers are documented in EQUIPMENT_ROLE_ATTRIBUTE_RESEARCH.
    """
    a,_=_snapshot(role_id,snapshot)
    if not isinstance(snapshot,EquipmentRoleSnapshot):
        return ()
    fields=((8,_integer(a.physical_attack)),(12,_integer(a.magic_attack)),
            (14,_integer(snapshot.seal_strength)))
    if snapshot.seal_resistance is not None:fields+=((15,_integer(snapshot.seal_resistance)),)
    return fields
