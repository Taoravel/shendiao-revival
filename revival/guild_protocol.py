"""Native guild basic data and members; explicit unknown fields, no state I/O."""
import struct
from dataclasses import dataclass
from faction_protocol import text,FAMILY_POSITIONS,GUILD_POSITIONS
from wire import compact

UPDATE_GUILD=0xc5616
ADD_GUILD_MEMBERS=0xc5618
UPDATE_GUILD_MEMBER=0xc5619
REMOVE_GUILD_MEMBER=0xc561a


@dataclass(frozen=True)
class GuildView:
    identity: int
    name: str
    aim: str
    level: int
    reserved: int  # Native +44, still unbound. Caller supplies provenance.


@dataclass(frozen=True)
class GuildMemberWire:
    role_id: int
    name: str
    level: int
    school: int
    family: int
    family_name: str
    family_position: str
    guild_position: str
    metadata: tuple  # Native +10/+14/+18, not assigned invented meanings.
    prestige: tuple  # Current guild prestige and native displayed upper value.
    weekly_dues: int
    historical_dues: int
    offline_text: str


def guild_data(view):
    if (not isinstance(view,GuildView) or type(view.identity) is not int or not 0<view.identity<2**31
        or type(view.level) is not int or not 0<view.level<2**31
        or type(view.reserved) is not int or not -2**31<=view.reserved<2**31):
        raise ValueError('Complete native guild data required')
    return struct.pack('>i',view.identity)+text(view.name)+text(view.aim)+struct.pack('>ii',view.level,view.reserved)


def guild_member(m):
    if (not isinstance(m,GuildMemberWire) or type(m.metadata) is not tuple or len(m.metadata)!=3
        or type(m.prestige) is not tuple or len(m.prestige)!=2
        or m.family_position not in FAMILY_POSITIONS or m.guild_position not in GUILD_POSITIONS):
        raise ValueError('Complete native guild member fields required')
    numbers=(*m.metadata,m.level,m.school,*m.prestige,m.family)
    if (type(m.role_id) is not int or not 0<m.role_id<2**63
        or any(type(n) is not int or not -2**31<=n<2**31 for n in numbers)
        or any(type(n) is not int or not 0<=n<2**63 for n in (m.weekly_dues,m.historical_dues))):
        raise ValueError('Invalid native guild member fields')
    return (struct.pack('>Qiiii',m.role_id,*m.metadata,m.level)+text(m.name)
        +struct.pack('>iiiQQii',m.school,*m.prestige,m.weekly_dues,m.historical_dues,
                     FAMILY_POSITIONS[m.family_position],GUILD_POSITIONS[m.guild_position])
        +text(m.family_name)+struct.pack('>i',m.family)+text(m.offline_text))


def guild_members(rows):
    if type(rows) is not tuple:raise ValueError('Frozen guild roster required')
    return compact(len(rows))+b''.join(guild_member(m) for m in rows)


def removed_guild_member(role_id):return struct.pack('>Q',role_id)
