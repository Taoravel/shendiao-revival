"""Confirmed native pet commands, progress and presentation projections."""
import struct
from dataclasses import dataclass
from wire import compact,octets

LEARN_SKILL_BOOK=0xc07ff
QUERY_SKILL_PROGRESS=0xc0800
SKILL_PROGRESS_REPLY=0xc0801
SUPER_RETURN_PREVIEW=0xc0810
SUPER_RETURN_SUBMIT=0xc0811
SUPER_RETURN_QUERY=0xc0812
SUPER_RETURN_CLEAR=0xc0813
CAKE_NOTICE=0xc1775
PET_EVOLVE=0xc07fc


def decode_pet_evolution_request(body):
    """Original CReqPetEvolve carries exactly one positive signed BE32 key."""
    if type(body) is not bytes or len(body)!=4:raise ValueError('Invalid original evolution request')
    pet=struct.unpack('>i',body)[0]
    if pet<=0:raise ValueError('Original owned evolution pet key required')
    return pet


def pet_removal_message(pet_id):
    """Original SRemovePetFromCol: carried column1, positive BE32 pet key."""
    if type(pet_id) is not int or not 0<pet_id<=0x7fffffff:raise ValueError('Original pet removal key required')
    return 0xc07dd,struct.pack('>ii',1,pet_id)


def _pet_notice(message_id,parameters,counts):
    if (type(message_id) is not int or message_id not in counts or type(parameters) is not tuple
            or len(parameters)!=counts[message_id] or any(type(s) is not str or len(s.encode('utf-16le'))>256 for s in parameters)):
        raise ValueError('Known original pet notice and exact UTF16 parameters required')
    return CAKE_NOTICE,struct.pack('>ii',message_id,0)+compact(len(parameters))+b''.join(octets(s.encode('utf-16le')) for s in parameters)


def cake_notice(message_id,parameters=()):
    """Original SSendMsgNotify default extra0, exact cake parameter counts."""
    return _pet_notice(message_id,parameters,{145133:0,145135:3,145136:1,145137:0,145139:0})


def evolution_notice(message_id,parameters=()):
    """Original ordinary stage success(name,label) or post-cap success()."""
    return _pet_notice(message_id,parameters,{143571:2,148963:0})


def stone_notice(message_id,parameters=()):
    return _pet_notice(message_id,parameters,{150453:0,150454:5,150456:0,150483:0})


def stone_attribute_map(stones):
    from pet_stones import PetStones
    if type(stones) is not PetStones:raise ValueError('Known complete stone state required for native attributes')
    return compact(6)+b''.join(struct.pack('>if',key,float(value)) for key,value in
        zip((1930,1940,1950,1960,1970,1980),(stones.count,*stones.added_aptitudes)))


def stone_attributes_message(pet_id,stones):
    if type(pet_id) is not int or not 0<pet_id<=0x7fffffff:raise ValueError('Original positive owned pet key required')
    return 0xc32c9,struct.pack('>ii',1,pet_id)+stone_attribute_map(stones)


def decode_super_return_pet_request(body):
    """Original query/submit/clear use one signed BE32 pet instance key."""
    if type(body) is not bytes or len(body)!=4:raise ValueError('Invalid super-return pet request')
    pet=struct.unpack('>i',body)[0]
    if pet<=0:raise ValueError('Positive owned pet instance key required')
    return pet


def super_return_preview_message(pet_id,aptitudes,insight,growth_raw,score):
    """Encode an explicitly known pending result; never fabricate unknown score."""
    if type(aptitudes) is not tuple or len(aptitudes)!=5:
        raise ValueError('Known five preview aptitudes required')
    values=(pet_id,*aptitudes,insight,growth_raw,score)
    if (any(type(v) is not int or not 0<=v<=0x7fffffff for v in values) or pet_id==0):
        raise ValueError('Representable complete super-return preview required')
    return SUPER_RETURN_PREVIEW,struct.pack('>9i',*values)


@dataclass(frozen=True)
class SkillBookOptions:
    basic_key: int = -1
    advanced_key: int = -1
    protected_skill: int = -1
    second_protected_skill: int = -1

    def __post_init__(self):
        values=(self.basic_key,self.advanced_key,self.protected_skill,self.second_protected_skill)
        if (any(type(v) is not int or v!=-1 and not 0<v<=0x7fffffff for v in values)
                or self.advanced_key!=-1 and self.basic_key==-1
                or self.protected_skill!=-1 and self.basic_key==-1
                or self.second_protected_skill!=-1 and self.advanced_key==-1
                or self.basic_key!=-1 and self.basic_key==self.advanced_key
                or self.protected_skill!=-1 and self.protected_skill==self.second_protected_skill):
            raise ValueError('Invalid certification item or protected skill selection')

    @property
    def protected_ids(self):
        return tuple(v for v in (self.protected_skill,self.second_protected_skill) if v!=-1)

    @property
    def wire_values(self):
        return self.basic_key,self.advanced_key,self.protected_skill,self.second_protected_skill


@dataclass(frozen=True)
class SkillBookRequest:
    pet_id: int
    item_key: int
    options: SkillBookOptions


def decode_skill_book_request(body):
    if type(body) is not bytes or len(body)!=24:
        raise ValueError('Invalid native pet skill-book request')
    pet,key,*values=struct.unpack('>6i',body)
    options=SkillBookOptions(*values)
    if pet<=0 or key<=0 or key in (options.basic_key,options.advanced_key):
        raise ValueError('Invalid owned pet, book or distinct certification key')
    return SkillBookRequest(pet,key,options)


def decode_skill_book(body):
    request=decode_skill_book_request(body)
    if request.options!=SkillBookOptions():
        raise ValueError('Use the full skill-book request decoder for certification options')
    return request.pet_id,request.item_key


def skill_progress_message(rows):
    if (type(rows) is not tuple or len(rows)>128
            or any(type(row) is not tuple or len(row)!=2 or type(row[0]) is not int
                or not 0<row[0]<=0x7fffffff or type(row[1]) is not int or not 0<=row[1]<=32767 for row in rows)
            or len({key for key,value in rows})!=len(rows)):
        raise ValueError('Known owned progress rows must fit original signed16 UI')
    return SKILL_PROGRESS_REPLY,compact(len(rows))+b''.join(struct.pack('>ih',key,value) for key,value in sorted(rows))


def game_time_message(now_ms):
    from pet_skill_expiry import require_time
    return 0xc0007,struct.pack('>q',require_time(now_ms))


def growth_wire_float(raw):
    """Project stored original integer into the native growth display float.

    The original UI multiplies its stored float32 by1000 then truncates. Choose
    the least float32 >= raw/1000 so a nearest-rounded value such as996 would
    not display995. Storage and point-growth arithmetic retain the exact raw
    integer; this deterministic wire choice is a restoration projection.
    """
    if type(raw) is not int or not 500<=raw<=0x7fffffff:
        raise ValueError('Known original positive pet growth integer required')
    bits=struct.unpack('>I',struct.pack('>f',raw/1000))[0]
    value=struct.unpack('>f',struct.pack('>I',bits))[0]
    if value*1000<raw:
        bits+=1
        value=struct.unpack('>f',struct.pack('>I',bits))[0]
    if int(value*1000)!=raw:
        raise ValueError('Pet growth cannot be preserved by the original native display')
    return value
