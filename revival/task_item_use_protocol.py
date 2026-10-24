"""Original task-item use intent: the ordinary inventory CUseItem body.

This role-target decoder carries no quest ID, quantity, position or timer proof.
The inventory owner still decides which gameplay path receives the request.
"""
from dataclasses import dataclass
import struct

USE_ITEM=0xC03FF
S_USE_TASK_ITEM_FAIL=0xC4A53


@dataclass(frozen=True)
class TaskItemUseRequest:
    item_key:int
    target_kind:int
    target_id:int


def decode_task_item_use(body):
    if not isinstance(body,bytes) or len(body)!=16:
        raise ValueError('Task item use requires the original16-byte CUseItem')
    key,kind,target=struct.unpack('>iiQ',body)
    if key<=0 or kind!=0 or not 0<target<2**63:
        raise ValueError('Task item requires an owned key and role target0')
    return TaskItemUseRequest(key,kind,target)


def task_item_use_failure_message():
    """Original empty failure body; it cannot carry a task or reason code."""
    return S_USE_TASK_ITEM_FAIL,b''
