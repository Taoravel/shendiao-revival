"""Confirmed organization request codecs; preserve unconfirmed choice semantics.

NPC context, camp and raw choice values must be resolved by the integration
owner. A decoded packet is not an authorized OrganizationCommand.
"""
import struct
from dataclasses import dataclass,replace,field
from types import MappingProxyType
from social_protocol import text,read_text,end
from social_protocol import chat_message
from wire import compact,read_compact
from faction_types import JOIN_FAMILY,FAMILY_REVIEW,EXPEL_MEMBER,LEAVE_FAMILY,FAMILY_POSITION,FAMILY_NATIVE_TYPES
from faction_types import REQUEST_FACTION,FACTION_POSITION,RESIGN_FACTION_OFFICE,GUILD_NATIVE_TYPES

FAMILY_CHANNEL, GUILD_CHANNEL = 10,4


def organization_chat(kind,role,content):
    if kind not in ('family','guild'): raise ValueError('Invalid organization kind')
    return chat_message(role,FAMILY_CHANNEL if kind=='family' else GUILD_CHANNEL,content)

CREATE_FAMILY=0xc55f1
JOIN_FACTION=0xc5612
CREATE_FACTION_RESPONSE=0xc5614
LEAVE_FACTION=0xc5615
FACTION_REVIEW=0xc561e
SET_DEPUTY_AUTHORITY=0xc5639
DEPUTY_AUTHORITY=0xc5638
REQUEST_FAMILY=0xc5657
FACTION_TYPES=frozenset((CREATE_FAMILY,JOIN_FAMILY,FAMILY_REVIEW,EXPEL_MEMBER,LEAVE_FAMILY,FAMILY_POSITION,
    REQUEST_FACTION,JOIN_FACTION,CREATE_FACTION_RESPONSE,LEAVE_FACTION,FACTION_REVIEW,FACTION_POSITION,REQUEST_FAMILY,
    RESIGN_FACTION_OFFICE,SET_DEPUTY_AUTHORITY))
UPDATE_FAMILY=0xc55f3
ADD_FAMILY_MEMBERS=0xc55f9
UPDATE_FAMILY_MEMBER=0xc55fa
REMOVE_FAMILY_MEMBER=0xc55fc
LEFT_FAMILY=0xc5602
LEFT_FACTION=0xc560c
EXPELLED_FAMILY_MEMBER=0xc564d
ADD_FAMILY_APPLICATIONS=0xc55fb
REMOVE_FAMILY_APPLICATIONS=0xc55fd
FAMILY_POSITIONS=MappingProxyType({'member':0,'deputy':1,'leader':2})
GUILD_POSITIONS=MappingProxyType({'member':0,'patrol':1,'family_leader':2,'left_elder':3,'right_elder':4,'deputy':5,'leader':6})


def deputy_authority(mask):
    if type(mask) is not int or not 0<=mask<512:raise ValueError('Invalid deputy authority mask')
    return struct.pack('>i',mask)


@dataclass(frozen=True)
class FamilyMemberWire:
    role_id: int
    name: str
    unbound_metadata: int  # Original +2c is copied but not read by roster renderer.
    prestige_values: tuple  # +30/+34 shown as first/second; spending meaning unbound.
    level: int
    position: str
    last_offline_text: str  # Empty means online in the original client.


def family_member(member):
    """Verified native layout; caller must supply all as-yet unbound fields."""
    if (not isinstance(member,FamilyMemberWire) or type(member.prestige_values) is not tuple
        or len(member.prestige_values)!=2 or member.position not in FAMILY_POSITIONS):
        raise ValueError('Complete native family member fields required')
    numbers=(member.unbound_metadata,*member.prestige_values,member.level)
    if (type(member.role_id) is not int or not 0<member.role_id<2**63
        or any(type(v) is not int or not -2**31<=v<2**31 for v in numbers)):
        raise ValueError('Invalid native family member fields')
    return (struct.pack('>Q',member.role_id)+text(member.name)
        +struct.pack('>iiiii',*numbers,FAMILY_POSITIONS[member.position])+text(member.last_offline_text))


def family_members(members):
    if type(members) is not tuple:raise ValueError('Frozen family roster required')
    return compact(len(members))+b''.join(family_member(m) for m in members)


def removed_family_member(role_id):return struct.pack('>Q',role_id)


@dataclass(frozen=True)
class FamilyApplication:
    role_id: int
    name: str
    level: int
    school: int
    recommender: str = ''


def family_application(row):
    return struct.pack('>Q',row.role_id)+text(row.name)+struct.pack('>ii',row.level,row.school)+text(row.recommender)


def family_applications(rows):return compact(len(rows))+b''.join(family_application(r) for r in rows)


def removed_family_applications(ids):return compact(len(ids))+b''.join(struct.pack('>Q',rid) for rid in ids)


def family_join_request(ids,mode=0):return compact(len(ids))+b''.join(struct.pack('>i',i) for i in ids)+struct.pack('>i',mode)


MAX_FAMILY_COURSES=100  # local bounded panel budget, not an original retention claim


@dataclass(frozen=True)
class FamilyCourse:
    template_id: int
    parameters: tuple


def family_course(course):
    if (not isinstance(course,FamilyCourse) or type(course.template_id) is not int
            or not 1<=course.template_id<=7 or type(course.parameters) is not tuple
            or len(course.parameters)!=(1 if course.template_id==1 else 2)
            or any(type(value) is not str or not 1<=len(value)<=128 or '\0' in value for value in course.parameters)):
        raise ValueError('invalid_family_course')
    return struct.pack('>i',course.template_id)+compact(len(course.parameters))+b''.join(text(value) for value in course.parameters)


@dataclass(frozen=True)
class FamilyView:
    identity: int
    name: str
    aim: str
    founder_name: str
    level: int
    funds: int  # Required authoritative balance, never copied from leader cash.
    popularity: int = 0
    popularity_max: int = 0
    construction: int = 0
    construction_max: int = 0
    unbound_identity: int = 0
    history: tuple = field(default=(),kw_only=True)

    @property
    def family_scene_identity(self):
        """Original +78 Q; old constructor name is retained for compatibility."""
        return self.unbound_identity


def family_scene_view(view,client_scene_identity):
    """Pure projection of a root-supplied family scene identity, not admission.

    The shared owner binds the family/generation to its actual map instance and
    original client scene identity. This helper does not derive that identity
    from a family ID, map template, address hash or client packet.
    """
    if (not isinstance(view,FamilyView) or type(client_scene_identity) is not int
            or not 0<=client_scene_identity<2**63):raise ValueError('invalid_family_scene_identity')
    return replace(view,unbound_identity=client_scene_identity)


def family_data(view):
    """Native FamilyData verified against UI consumers, not a complete panel.

    Family scene identity stays at constructor zero unless the shared owner
    supplies its actual binding. History defaults empty for legacy callers.
    Popularity/construction pairs are supplied by the organization read model.
    Caller must supply known family funds; there is no implicit wallet baseline.
    """
    if not isinstance(view,FamilyView) or type(view.funds) is not int or not 0<=view.funds<2**63:
        raise ValueError('Authoritative family balance required')
    if type(view.family_scene_identity) is not int or not 0<=view.family_scene_identity<2**63:
        raise ValueError('invalid_family_scene_identity')
    if type(view.history) is not tuple or len(view.history)>MAX_FAMILY_COURSES:
        raise ValueError('bounded_frozen_family_history_required')
    # Original Family/FamilyFrame/FamilyName displays +24, not the first string.
    # First string is FamilyCreater, +40 is purpose; current leader is rendered
    # separately from the member roster. +78 is the family client scene identity.
    return (struct.pack('>i',view.identity)+text(view.founder_name)+text(view.name)+text(view.aim)
        +struct.pack('>iQiiiiQ',view.level,view.funds,view.popularity,view.popularity_max,
                     view.construction,view.construction_max,view.unbound_identity)
        +compact(len(view.history))+b''.join(family_course(course) for course in view.history))


def family_update(view):return family_data(view)


def create_request(context,mode,name,aim,camp):
    return struct.pack('>Qi',context,mode)+text(name)+text(aim)+struct.pack('>i',camp)


def decode(kind,body):
    if kind==JOIN_FAMILY:
        count,pos=read_compact(body)
        if not 1<=count<=100 or len(body)-pos!=count*4+4:raise ValueError('Invalid family application list')
        ids=struct.unpack_from('>'+'i'*count,body,pos)
        if len(set(ids))!=count or any(i<=0 for i in ids):raise ValueError('Invalid family ids')
        return ids,struct.unpack_from('>i',body,pos+count*4)[0]
    if kind==CREATE_FAMILY:
        if len(body)<12: raise ValueError('Truncated create context')
        context,mode=struct.unpack_from('>Qi',body)
        name,pos=read_text(body,12,64)
        aim,pos=read_text(body,pos,256)
        if len(body)-pos!=4: raise ValueError('Invalid create tail')
        return context,mode,name,aim,struct.unpack_from('>i',body,pos)[0]
    if kind in (FAMILY_REVIEW,FAMILY_POSITION,FACTION_POSITION):
        if len(body)!=12: raise ValueError('Invalid role choice')
        return struct.unpack('>Qi',body)
    if kind==SET_DEPUTY_AUTHORITY:
        if len(body)!=16:raise ValueError('Invalid deputy authority choice')
        # Native UI sends one selected bit mask, not a zero-based bit index.
        # The organization Interface accepts an index; its eventual native
        # Adapter must validate one-hot and convert rather than forwarding it.
        return struct.unpack('>Qii',body)
    if kind==FACTION_REVIEW:
        if len(body)!=8: raise ValueError('Invalid family choice')
        return struct.unpack('>ii',body)
    if kind==EXPEL_MEMBER:
        if len(body)!=8: raise ValueError('Invalid target')
        return struct.unpack('>Q',body)
    if kind in (REQUEST_FAMILY,JOIN_FACTION,CREATE_FACTION_RESPONSE):
        if len(body)!=4: raise ValueError('Invalid int request')
        return struct.unpack('>i',body)
    if kind in (LEAVE_FAMILY,LEAVE_FACTION,REQUEST_FACTION,RESIGN_FACTION_OFFICE):
        if body: raise ValueError('Expected empty organization request')
        return ()
    raise ValueError('Unconfirmed organization codec')
