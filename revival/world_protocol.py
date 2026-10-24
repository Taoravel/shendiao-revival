"""Initial world snapshot and scene notification from original native codecs.

Vitals and test spawn are explicit local restoration settings, not original rules.
"""
import struct
from wire import octets
from world_catalog import maps, valid_position
from role_attribute_protocol import role_detail_vitals,role_detail_equipment_fields,role_detail_profile

ENTER_WORLD = 0xc0006
ENTER_SCENE = 0xc0fa9
AFTER_ENTER_WORLD = 0xc003d


def world_snapshot(role,attribute_snapshot=None,*,intro_discriminator=0,growth_snapshot=None):
    """Encode current state; intro 0/1 is the explicit local chapter projection.

    Only the role owner with durable chapter provenance supplies this value.
    Default zero preserves the original constructor/legacy compatibility path;
    XP, level and task-free input never infer a completed chapter. See the
    designed policy in design/newbie-opening-v1.json, not a guessed native name.
    Explicit current growth/profile together supply the identified combat,
    signed16 five-stat and current potential fields. Legacy callers preserve
    their existing compatibility projection; no growth baseline is inferred.
    """
    # RoleDetail's original constructor supplies empty nested containers and zero
    # unknown scalar fields. Only positively identified fields are populated.
    attributes = [0] * 32
    five_stats,potential=(0,0,0,0,0),0
    if growth_snapshot is not None:
        if attribute_snapshot is None:
            raise ValueError('Explicit attributes required with current growth snapshot')
        profile=role_detail_profile(growth_snapshot,attribute_snapshot)
        if ((growth_snapshot.role_id,growth_snapshot.level,growth_snapshot.experience)
                !=(role['id'],role['level'],role.get('experience',0))):
            raise ValueError('Entry role and current growth snapshot disagree')
        attributes=list(profile.values)
        five_stats,potential=profile.five_stats,profile.potential
    elif attribute_snapshot is None:
        # Explicit compatibility path only, not an invented persisted baseline.
        attributes[:5] = [100, 100, 100, 100, 100]
    else:
        attributes[:5] = role_detail_vitals(role['id'],attribute_snapshot)
        for index,value in role_detail_equipment_fields(role['id'],attribute_snapshot):
            attributes[index] = value
    experience = role.get('experience', 0)
    if type(experience) is not int or not 0 <= experience < 2**63:
        raise ValueError('Invalid committed experience balance')
    if type(intro_discriminator) is not int or intro_discriminator not in (0,1):
        raise ValueError('Intro projection must be an explicit policy value 0 or 1')
    return (struct.pack('>Q', role['id']) + octets(role['name'].encode('utf-16-le'))
            # The first q64 is independent of current EXP (+f8 below).
            + struct.pack('>4iQ', role['level'], role['school'], role['shape'], 0, intro_discriminator)
            + struct.pack('>32i', *attributes)
            + struct.pack('>5h', *five_stats)
            + struct.pack('>6i',potential,0,0,0,0,0)
            + struct.pack('>Q', experience) + bytes(16)  # native packet+f8, then two u64
            + bytes(12)  # three i32
            + bytes(4)   # four empty collection counts
            + bytes(8) + b'\0' + bytes(8) + bytes(8)
            + bytes(3) + bytes(2) + b'\0')


def scene_entry(position=(1007, 8480, 6976), reason=516015):
    # Local test location: original portal destination into Lin'an from Taihu.
    # Portal cells (530,436) -> logical pixels (8480,6976); native renderer scales X.
    map_id, x, y = position
    if not valid_position(position):
        raise ValueError('Unavailable scene or out-of-bounds position')
    return (octets(maps()[map_id]['name'].encode('utf-16-le'))
            + struct.pack('>hhBiQB', x, y, 0, reason, map_id, 0) + octets(b''))
