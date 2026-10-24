"""Original fixed-NPC quiz answer, distinct from ordinary CCommit."""
from dataclasses import dataclass
import struct

C_ANSWER_QUESTION=0xC4A48


@dataclass(frozen=True)
class TaskQuizAnswer:
    task_id:int
    npc_key:int
    answer_code:int


def decode_task_quiz_answer(body):
    if not isinstance(body,bytes) or len(body)!=16:
        raise ValueError('CAnswerQuestion requires exactly16 bytes')
    task,key,code=struct.unpack('>iQi',body)
    if not 1001<=task<=499999 or not 0<=key<2**63 or not 0<=code<=5:
        raise ValueError('Invalid original quiz ID/code or unsupported server NPC key')
    return TaskQuizAnswer(task,key,code)
