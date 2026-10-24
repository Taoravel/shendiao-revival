"""Pure task command codecs plus the legacy synchronous session Adapter.

New routing uses decode_task_request -> role owner -> encode_task_reply. Only the
connection owner frames/encrypts returned logical messages. The legacy receive
path still does blocking SQLite work and must be replaced by integration.
"""
from dataclasses import dataclass
from task_protocol import (C_REQUEST_QUEST_CAN_ACCEPT, S_REQUEST_QUEST_CAN_ACCEPT,
                           C_TRACK_QUEST, decode_empty_request, decode_track_quest,
                           encode_quest_can_accept, S_TRACK_QUEST, encode_track_quest,
                           C_COMMIT_SCENARIO_QUEST, C_QUEST_DIALOG_END, C_QUEST_REACH_SCENE,
                           C_REQUEST_REWARD, decode_commit_scenario_quest,
                           decode_quest_dialog_end, decode_request_reward)
from tasks import TaskStore
from task_item_protocol import C_SUBMIT_2_NPC, decode_npc_item_submission
from task_money_protocol import decode_task_money_submission
from task_pet_submission_protocol import decode_task_pet_submission

TASK_TYPES = (C_REQUEST_QUEST_CAN_ACCEPT, C_TRACK_QUEST)
TASK_INTENT_TYPES = (C_COMMIT_SCENARIO_QUEST, C_QUEST_DIALOG_END,
                     C_QUEST_REACH_SCENE, C_REQUEST_REWARD)
TASK_ITEM_INTENT_TYPES = (C_SUBMIT_2_NPC,)  # task route must additionally require submit_type==1
TASK_MONEY_INTENT_TYPES = (C_SUBMIT_2_NPC,)  # money route separately requires submit_type==3
TASK_PET_SUBMISSION_INTENT_TYPES = (C_SUBMIT_2_NPC,)  # pet route separately requires submit_type==2


def decode_task_item_intent(kind, body):
    """Separate native item intent; it requires current inventory and NPC proof."""
    if kind!=C_SUBMIT_2_NPC:
        raise ValueError('Unsupported task item intent')
    command=decode_npc_item_submission(body)
    if command.submit_type!=1:
        raise ValueError('NPC submission belongs to another gameplay module')
    return command


def decode_task_money_intent(kind,body):
    if kind!=C_SUBMIT_2_NPC:
        raise ValueError('Unsupported task money intent')
    return decode_task_money_submission(body)


def decode_task_pet_submission_intent(kind,body):
    if kind!=C_SUBMIT_2_NPC:
        raise ValueError('Unsupported task pet submission intent')
    return decode_task_pet_submission(body)


@dataclass(frozen=True)
class TaskIntent:
    """Untrusted client request; never passed as TaskEvidence or a reward grant."""
    kind: int
    task_id: int = 0
    npc_key: int = 0
    opaque: int = 0


def decode_task_intent(kind, body):
    """Pure codec for integration to route to authoritative gameplay owners.

    Commit's last i32 remains opaque, not a verified dialogue option. Dialog-end
    and reach-scene alone establish neither a valid objective nor eligibility.
    Kept outside legacy TASK_TYPES until map/scenario validation is connected.
    """
    if kind == C_COMMIT_SCENARIO_QUEST:
        quest_id, npc_key, opaque = decode_commit_scenario_quest(body)
        return TaskIntent(kind, quest_id, npc_key, opaque)
    if kind == C_QUEST_DIALOG_END:
        return TaskIntent(kind, decode_quest_dialog_end(body))
    if kind == C_REQUEST_REWARD:
        return TaskIntent(kind, decode_request_reward(body))
    if kind == C_QUEST_REACH_SCENE:
        decode_empty_request(body)
        return TaskIntent(kind)
    raise ValueError('Unsupported task intent protocol')


@dataclass(frozen=True)
class TaskCommand:
    kind: int
    task_id: int = 0
    tracked: int = 0


def decode_task_request(kind, body):
    """Pure native codec; routing envelope supplies role/epoch/request/deadline."""
    if kind == C_REQUEST_QUEST_CAN_ACCEPT:
        decode_empty_request(body)
        return TaskCommand(kind)
    if kind == C_TRACK_QUEST:
        ident, tracked = decode_track_quest(body)
        return TaskCommand(kind, ident, tracked)
    raise ValueError('Unsupported task protocol')


def execute_task_command(store, account_id, role_id, command):
    """Synchronous compatibility storage path, for the bounded storage worker.

    The role owner must serialize its commands and fence stale login epochs.
    Returns immutable result data; never receives or calls any Session/writer.
    """
    if command.kind == C_REQUEST_QUEST_CAN_ACCEPT:
        return tuple(store.available(account_id, role_id))
    if command.kind == C_TRACK_QUEST:
        store.track(account_id, role_id, command.task_id, command.tracked)
        return ()
    raise ValueError('Unsupported task command')


def encode_task_reply(command, result):
    """Pure codec returning immutable logical messages, with no RC4/MPPC access."""
    if command.kind == C_REQUEST_QUEST_CAN_ACCEPT:
        return ((S_REQUEST_QUEST_CAN_ACCEPT, encode_quest_can_accept(result)),)
    if command.kind == C_TRACK_QUEST:
        return ((S_TRACK_QUEST, encode_track_quest(command.task_id, command.tracked)),)
    raise ValueError('Unsupported task command')


class TaskSession:
    def __init__(self, accounts, account_id, role_id, *, store=None):
        self.store = store if store is not None else TaskStore(accounts)
        self.account_id, self.role_id = account_id, role_id

    def receive(self, kind, body):
        command = decode_task_request(kind, body)
        result = execute_task_command(self.store, self.account_id, self.role_id, command)
        return list(encode_task_reply(command, result))
