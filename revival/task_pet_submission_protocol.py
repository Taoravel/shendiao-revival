"""Original mode2 single-pet CSubmit2Npc intent, never removal authority.

The pet key is a positive native i32, independently of the u64 NPC instance.
Qualification, wild/baby category, lock/display state and retirement still
require public facts and a same-transaction contract from the pet owner.
"""
from dataclasses import dataclass
from task_item_protocol import NpcItemSubmission,encode_npc_item_submission,decode_npc_item_submission


@dataclass(frozen=True)
class TaskPetSubmission:
    task_id:int
    npc_key:int
    pet_key:int


def encode_task_pet_submission(command):
    if (type(command) is not TaskPetSubmission or type(command.task_id) is not int
            or not 1001<=command.task_id<=499999 or type(command.npc_key) is not int
            or not 0<command.npc_key<2**63 or type(command.pet_key) is not int
            or not 0<command.pet_key<=0x7fffffff):
        raise ValueError('Bounded original task pet submission required')
    return encode_npc_item_submission(NpcItemSubmission(command.task_id,command.npc_key,2,((command.pet_key,1),)))


def decode_task_pet_submission(body):
    command=decode_npc_item_submission(body)
    if command.submit_type!=2 or len(command.units)!=1 or command.units[0][1]!=1:
        raise ValueError('Task pet submission requires mode2 and one pet instance')
    result=TaskPetSubmission(command.task_id,command.npc_key,command.units[0][0])
    encode_task_pet_submission(result)
    return result
