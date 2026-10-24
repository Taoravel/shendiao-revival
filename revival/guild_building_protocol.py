"""Original construction codec; no NPC authorization or state mutation."""
import struct
from guild_buildings import Building,BuildingSnapshot,requirements
from wire import compact
from faction_types import QUERY_GUILD_BUILDINGS as QUERY_BUILDINGS

BUILDING_DATA=0xc5628
CHOOSE_BUILDING=0xc5631


def decode_query(body):
    if type(body) is not bytes or body:raise ValueError('invalid_guild_building_query')
    return ()


def decode_choice(body):
    if type(body) is not bytes or len(body)!=12:raise ValueError('invalid_guild_building_choice_packet')
    context,target=struct.unpack('>Qi',body)
    if target not in (0,1,2):raise ValueError('invalid_building_choice')
    return context,target


def building_data(state):
    if (not isinstance(state,BuildingSnapshot) or type(state.selected) is not int
            or state.selected not in (-1,0,1,2) or type(state.buildings) is not tuple
            or any(not isinstance(b,Building) for b in state.buildings)
            or tuple(b.building_type for b in state.buildings)!=(0,1,2)):
        raise ValueError('complete_guild_buildings_required')
    rows=[]
    for b in state.buildings:
        needed=requirements(b).construction
        if (type(b.construction) is not int or b.construction<0
                or (needed and b.construction>=needed) or (not needed and b.construction)):
            raise ValueError('invalid_guild_building_progress')
        rows.append(struct.pack('>iii',b.building_type,b.level,b.construction))
    return struct.pack('>i',state.selected)+compact(3)+b''.join(rows)
