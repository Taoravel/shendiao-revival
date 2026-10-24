"""Native NPC item submission bodies, independent of task authorization.

See TASK_ITEM_SUBMISSION_RESEARCH.md. submit_type=1 belongs to ordinary type12;
other submit types remain available to their owning gameplay modules, not tasks.
"""
from dataclasses import dataclass
import struct
from wire import compact, read_compact, NeedMoreData

C_SUBMIT_2_NPC = 0xC2340
S_SUBMIT_2_NPC = 0xC233F
MAX_SUBMIT_UNITS = 256  # local bounded command policy, not a recovered UI limit


@dataclass(frozen=True)
class NpcItemSubmission:
    task_id: int
    npc_key: int
    submit_type: int
    units: tuple  # ((owned item instance key, selected quantity), ...)


def _header(task_id, npc_key, submit_type):
    if (any(type(x) is not int or not 0 <= x <= 0x7fffffff for x in (task_id,submit_type))
            or type(npc_key) is not int or not 0 <= npc_key < 2**63):
        raise ValueError('NPC submission header outside native scalar range')
    return struct.pack('>iQi',task_id,npc_key,submit_type)


def encode_npc_item_submission(command):
    if not isinstance(command,NpcItemSubmission) or type(command.units) is not tuple or len(command.units)>MAX_SUBMIT_UNITS:
        raise ValueError('Bounded immutable NPC submission units required')
    if any(type(x) is not tuple or len(x)!=2 or any(type(v) is not int or not 0<v<=0x7fffffff for v in x)
           for x in command.units):
        raise ValueError('Invalid native item submission scalar')
    return _header(command.task_id,command.npc_key,command.submit_type)+compact(len(command.units))+b''.join(
        struct.pack('>ii',*unit) for unit in command.units)


def decode_npc_item_submission(body):
    if len(body)<17:
        raise ValueError('Truncated NPC item submission')
    task_id,npc_key,submit_type=struct.unpack('>iQi',body[:16])
    _header(task_id,npc_key,submit_type)
    try:
        count,offset=read_compact(body,16)
    except NeedMoreData:
        raise ValueError('Truncated NPC submission count') from None
    if count>MAX_SUBMIT_UNITS or len(body)-offset!=count*8:
        raise ValueError('NPC submission unit count or body length mismatch')
    command=NpcItemSubmission(task_id,npc_key,submit_type,tuple(struct.iter_unpack('>ii',body[offset:])))
    # Reuse scalar checks, retaining original order rather than silently merging.
    encode_npc_item_submission(command)
    return command


def encode_npc_submission_prompt(task_id,npc_key,submit_type,target_ids,opaque):
    """SSubmit2Npc: empty target_ids invokes the client's original task config.

    The last i32 stays opaque. Task callers may only use a separately verified
    value; this generic codec does not assign it a business meaning.
    """
    if (type(target_ids) is not tuple or len(target_ids)>MAX_SUBMIT_UNITS
            or any(type(x) is not int or not 0<=x<=0x7fffffff for x in target_ids)
            or type(opaque) is not int or not -2**31<=opaque<2**31):
        raise ValueError('Invalid NPC submission prompt fields')
    return _header(task_id,npc_key,submit_type)+compact(len(target_ids))+b''.join(
        struct.pack('>i',x) for x in target_ids)+struct.pack('>i',opaque)
