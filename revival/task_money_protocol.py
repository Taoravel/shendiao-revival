"""Original type11 CSubmit2Npc money body, separate from item-key semantics.

Native mode3 writes its amount twice into one SubmitUnit. Equality and exact
configured amount are server constraints, not the generic native validator.
"""
from dataclasses import dataclass
from task_item_protocol import C_SUBMIT_2_NPC,NpcItemSubmission,decode_npc_item_submission,encode_npc_item_submission


@dataclass(frozen=True)
class TaskMoneySubmission:
    task_id:int
    npc_key:int
    amount:int


def encode_task_money_submission(command):
    if (type(command) is not TaskMoneySubmission or type(command.task_id) is not int
            or not 1001<=command.task_id<=499999 or type(command.npc_key) is not int
            or not 0<command.npc_key<2**63 or type(command.amount) is not int
            or not 0<command.amount<=0x7fffffff):
        raise ValueError('Bounded original task money request required')
    return encode_npc_item_submission(NpcItemSubmission(command.task_id,command.npc_key,3,
        ((command.amount,command.amount),)))


def decode_task_money_submission(body):
    command=decode_npc_item_submission(body)
    if (command.submit_type!=3 or len(command.units)!=1
            or command.units[0][0]!=command.units[0][1]):
        raise ValueError('Task money requires mode3 and one equal amount pair')
    result=TaskMoneySubmission(command.task_id,command.npc_key,command.units[0][0])
    encode_task_money_submission(result)
    return result
