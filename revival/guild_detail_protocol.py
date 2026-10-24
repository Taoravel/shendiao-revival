"""Original guild details codec; no state, admission, connection or send.

Scene IDs are supplied by the shared owner's authoritative residence binding.
They are not derived from a guild ID, map template, hash or incoming packet.
Raw groups name native offsets, not business meanings. Every field is required;
an unknown saved record must not be completed with made-up defaults.
"""
from dataclasses import dataclass
import struct
from faction_protocol import text
from wire import compact

DETAILED_GUILD=0xc5624
MAX_DETAIL_BODY=65535  # original SFactionDetailedData size policy at 0xf91d40
MAX_SKILL_ROWS=64      # local bounded output budget, not original gameplay cap
MAX_COURSE_ROWS=100
MAX_BULLETIN_ROWS=32


@dataclass(frozen=True)
class GuildSceneIDs:
    hall: int       # original slot0, map1393
    workshop: int   # original slot1, map1395
    practice: int   # original slot2, map1394


def scene_ids(scenes):
    if (not isinstance(scenes,GuildSceneIDs)
            or any(type(n) is not int or not 0<=n<2**63 for n in (scenes.hall,scenes.workshop,scenes.practice))):
        raise ValueError('invalid_guild_scene_identities')
    return struct.pack('>QQQ',scenes.hall,scenes.workshop,scenes.practice)


@dataclass(frozen=True,kw_only=True)
class GuildDetails:
    unbound_header: str
    bulletins: tuple
    courses: tuple
    raw_i32_at_3c: tuple       # native +3c/+40, two i32
    raw_u64_at_48: tuple   # +48/+50, two Q; meanings not assigned here
    raw_i32_at_58: tuple     # +58/+5c, two i32
    raw_u64_at_60: tuple  # +60/+68/+70, three Q
    raw_i32_at_78: tuple  # +78/+7c/+80/+84, four i32
    skills: tuple
    practices: tuple
    scenes: GuildSceneIDs
    raw_i32_at_c0: int         # native +c0


@dataclass(frozen=True)
class GuildSkill:
    skill_id: int
    unbound_values: tuple  # native +8/+c/+10/+14, four distinct i32


@dataclass(frozen=True)
class GuildPractice:
    skill_id: int
    status: int


@dataclass(frozen=True)
class GuildCourse:
    template_id: int
    parameters: tuple


@dataclass(frozen=True)
class GuildBulletin:
    unbound_first: str
    unbound_second: str


def _integers(values,count,low,high):
    if (type(values) is not tuple or len(values)!=count
            or any(type(value) is not int or not low<=value<high for value in values)):
        raise ValueError('invalid_guild_detail_scalar_group')
    return values


def _text(value):
    if type(value) is not str or len(value)>4096 or '\0' in value:raise ValueError('invalid_guild_detail_text')
    return text(value)


def _frozen_rows(rows,limit):
    if type(rows) is not tuple or len(rows)>limit:raise ValueError('bounded_frozen_guild_detail_rows_required')


def _skills(rows):
    _frozen_rows(rows,MAX_SKILL_ROWS);encoded=[];seen=set()
    for row in rows:
        if not isinstance(row,GuildSkill):raise ValueError('guild_skill_row_required')
        _integers((row.skill_id,),1,1,2**31)
        numbers=_integers(row.unbound_values,4,-2**31,2**31)
        if row.skill_id in seen:raise ValueError('duplicate_guild_skill')
        seen.add(row.skill_id);encoded.append(struct.pack('>5i',row.skill_id,*numbers))
    return compact(len(rows))+b''.join(encoded)


def _practices(rows):
    _frozen_rows(rows,MAX_SKILL_ROWS);encoded=[];seen=set()
    for row in rows:
        if not isinstance(row,GuildPractice):raise ValueError('guild_practice_row_required')
        _integers((row.skill_id,),1,1,2**31);_integers((row.status,),1,-2**31,2**31)
        if row.skill_id in seen:raise ValueError('duplicate_guild_practice')
        seen.add(row.skill_id);encoded.append(struct.pack('>ii',row.skill_id,row.status))
    return compact(len(rows))+b''.join(encoded)


def _courses(rows):
    _frozen_rows(rows,MAX_COURSE_ROWS);encoded=[]
    for row in rows:
        if (not isinstance(row,GuildCourse) or type(row.template_id) is not int or not 1<=row.template_id<=7
                or type(row.parameters) is not tuple
                or len(row.parameters)!=(1 if row.template_id==1 else 3 if row.template_id==7 else 2)
                or any(type(value) is not str or not 1<=len(value)<=128 for value in row.parameters)):
            raise ValueError('invalid_guild_course')
        encoded.append(struct.pack('>i',row.template_id)+compact(len(row.parameters))+b''.join(_text(value) for value in row.parameters))
    return compact(len(rows))+b''.join(encoded)


def _bulletins(rows):
    _frozen_rows(rows,MAX_BULLETIN_ROWS);encoded={}
    for row in rows:
        if type(row) is not tuple or len(row)!=2 or not isinstance(row[1],GuildBulletin):
            raise ValueError('guild_bulletin_map_row_required')
        key,value=row;_integers((key,),1,-2**31,2**31)
        if key in encoded:raise ValueError('duplicate_guild_bulletin_key')
        encoded[key]=struct.pack('>i',key)+_text(value.unbound_first)+_text(value.unbound_second)
    return compact(len(rows))+b''.join(encoded[key] for key in sorted(encoded))


def guild_details(view):
    if not isinstance(view,GuildDetails):raise ValueError('complete_guild_details_required')
    head=_integers(view.raw_i32_at_3c,2,-2**31,2**31)
    balances=_integers(view.raw_u64_at_48,2,0,2**64)
    middle=_integers(view.raw_i32_at_58,2,-2**31,2**31)
    resources=_integers(view.raw_u64_at_60,3,0,2**64)
    buildings=_integers(view.raw_i32_at_78,4,-2**31,2**31)
    tail=_integers((view.raw_i32_at_c0,),1,-2**31,2**31)
    body=(_text(view.unbound_header)+_bulletins(view.bulletins)+_courses(view.courses)
        +struct.pack('>iiQQiiQQQiiii',*head,*balances,*middle,*resources,*buildings)
        +_skills(view.skills)+_practices(view.practices)+scene_ids(view.scenes)+struct.pack('>i',*tail))
    if len(body)>MAX_DETAIL_BODY:raise ValueError('guild_detail_body_capacity')
    return body
