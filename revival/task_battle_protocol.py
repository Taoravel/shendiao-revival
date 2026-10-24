"""Original CActiveScenarioQuestAIBattle body; no combat or reward authority."""
from dataclasses import dataclass
import struct

C_ACTIVE_SCENARIO_QUEST_AI_BATTLE=0xC4A4C


@dataclass(frozen=True)
class TaskBattleRequest:
    task_id:int
    npc_key:int


def encode_task_battle_request(command):
    if (not isinstance(command,TaskBattleRequest) or type(command.task_id) is not int
            or not 1001<=command.task_id<=499999 or type(command.npc_key) is not int
            or not 0<=command.npc_key<2**64):
        raise ValueError('Invalid original task battle request scalars')
    return struct.pack('>iQ',command.task_id,command.npc_key)


def decode_task_battle_request(body):
    # Native scalar decoder checks quest range only. Key ownership/sign and
    # trailing bytes belong to the receiver, so enforce exact framing here.
    if type(body) is not bytes or len(body)!=12:
        raise ValueError('Task battle request requires exactly12 bytes')
    command=TaskBattleRequest(*struct.unpack('>iQ',body))
    encode_task_battle_request(command)
    return command
