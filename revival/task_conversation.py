"""One bounded NPC task conversation per role owner, without I/O or networking.

Map ownership validates instance/version/distance before emitting NpcInteraction.
Opening a conversation is not completion; a matching client intent is planned
against a fresh role snapshot, and its ticket is consumed only after DB commit.
"""
from dataclasses import dataclass
from task_domain import (TaskDomain, TaskEvidence, supports_item_submission, supports_level_gate,
                         supports_native_effect_dialogue,supports_static_region,supports_npc_finish_dialogue,
                         supports_npc_start_dialogue,supports_npc_empty_scenario,supports_fixed_npc_quiz,
                         supports_money_submission,supports_fighting_pet_task,supports_prologue_touch,
                         supports_prologue_puzzle)
from task_quiz_protocol import TaskQuizAnswer
from task_money_protocol import TaskMoneySubmission
from task_protocol import (C_COMMIT_SCENARIO_QUEST, C_QUEST_DIALOG_END,
                           S_REFRESH_SCENARIO_QUEST_STATE, encode_scenario_state,
                           S_ACCEPT_SCENARIO_QUEST, ScenarioQuestInfo, encode_accept_scenario_quest,
                           S_REQUEST_QUEST_CAN_ACCEPT, encode_quest_can_accept)
from task_dialog_protocol import S_VISIT_NPC, encode_visit_npc
from task_session import TaskIntent
from world_npcs import NpcInteraction
from task_item_submission import item_objective_available, plan_item_objective
from task_item_protocol import S_SUBMIT_2_NPC, encode_npc_submission_prompt
from task_protocol import SCENARIO_ACTIVE, SCENARIO_READY


@dataclass(frozen=True)
class TaskConversationTicket:
    task_id: int
    role_id: int
    login_epoch: int | str
    source_id: str
    address: object
    position_version: int
    npc_id: int
    entity_key: int
    deadline_ms: int


@dataclass(frozen=True)
class TaskDialogue:
    ticket: TaskConversationTicket
    lines: tuple  # ((speaker_config_id, original rich text), ...)


class TaskConversation:
    def __init__(self, resources, role_id, login_epoch):
        self.resources = resources
        self.domain = TaskDomain(resources)
        self.role_id, self.login_epoch = role_id, login_epoch
        self.ticket = None

    def _scope(self, actor, snapshot):
        if (actor.role_id != self.role_id or actor.login_epoch != self.login_epoch
                or snapshot.role_id != self.role_id):
            raise ValueError('Task conversation owner mismatch')

    def _dialogue_evidence(self,task_id,source_id,map_id,npc_id):
        native=supports_native_effect_dialogue(self.resources.definitions[task_id])
        finish=supports_npc_finish_dialogue(self.resources.definitions[task_id])
        start=supports_npc_start_dialogue(self.resources.definitions[task_id])
        empty=supports_npc_empty_scenario(self.resources.definitions[task_id])
        quiz=supports_fixed_npc_quiz(self.resources.definitions[task_id])
        money=supports_money_submission(self.resources.definitions[task_id])
        return TaskEvidence(task_id,self.role_id,self.login_epoch,
            'npc_native_effect_dialogue_completed' if native else
            'npc_finish_dialogue_completed' if finish else
            'npc_start_dialogue_completed' if start else
            'npc_empty_scenario_committed' if empty else
            'npc_quiz_correct_answer' if quiz else
            'npc_money_submitted' if money else 'npc_dialogue_completed',
            source_id,map_id,npc_id,60001 if native else
            int(self.resources.definitions[task_id]['attributes']['ActiveInfoGiveBackMoney']) if money else 0)

    @staticmethod
    def _interaction(proof, current):
        if (not isinstance(proof, NpcInteraction) or proof.kind != 'npc_interacted'
                or proof.position_validation != 'bounds_version_distance'
                or current.role_id != proof.role_id or current.login_epoch != proof.login_epoch
                or current.address != proof.address or current.version != proof.position_version
                or current.state != 'active'):
            raise ValueError('Stale task NPC interaction')

    def open(self, actor, snapshot, task_id, proof, current, *, now_ms, deadline_ms):
        self._scope(actor, snapshot)
        self._interaction(proof, current)
        task = self.resources.definitions.get(task_id)
        if (task is None or task_id not in snapshot.active or proof.role_id != self.role_id
                or proof.login_epoch != self.login_epoch or now_ms >= deadline_ms
                or not proof.source_id or len(proof.source_id) > 160):
            raise ValueError('Task conversation is unavailable')
        target = task['target']
        if proof.npc_id != target['npc_id'] or proof.address.map_id != target['map_id']:
            raise ValueError('Task NPC target mismatch')
        # Validate the ordinary or verified local-effect objective before exposing
        # the client's ready-to-submit branch. No plan is persisted here.
        self.domain.plan(actor, snapshot, 'complete', task_id,evidence=self._dialogue_evidence(
            task_id,proof.source_id,proof.address.map_id,proof.npc_id))
        # Only one ticket is retained; opening another NPC invalidates the old one.
        self.ticket = TaskConversationTicket(task_id, self.role_id, self.login_epoch,
            proof.source_id, proof.address, proof.position_version, proof.npc_id,
            proof.entity_key, deadline_ms)
        return TaskDialogue(self.ticket, tuple((line['speaker'], line['text']) for line in task['dialogue']['start']))

    def plan_accept(self, actor, snapshot, intent, proof, current, *, now_ms, deadline_ms):
        """CCommit is also native acceptance; validate it against a real NPC."""
        self._scope(actor, snapshot)
        self._interaction(proof, current)
        if (proof.role_id != self.role_id or proof.login_epoch != self.login_epoch
                or now_ms >= deadline_ms or intent.kind != C_COMMIT_SCENARIO_QUEST
                or intent.npc_key != proof.entity_key or intent.opaque != 0):
            raise ValueError('Invalid task acceptance interaction')
        task = self.resources.definitions.get(intent.task_id)
        if (task is None or proof.npc_id != task['target']['npc_id']
                or proof.address.map_id != task['target']['map_id']):
            raise ValueError('Task acceptance NPC mismatch')
        plan = self.domain.plan(actor, snapshot, 'accept', intent.task_id)
        # Static type12 may be accepted without owning the items yet. Completion
        # goes through its native selected-item request, never plain CCommit.
        if not supports_item_submission(task):
            self.domain.plan(actor, plan.after, 'complete', intent.task_id,evidence=self._dialogue_evidence(
                intent.task_id,proof.source_id,proof.address.map_id,proof.npc_id))
        return plan

    def menu_messages(self, actor, snapshot, proof, current, *, now_ms, deadline_ms, item_states=None):
        """Expose one supported quest per NPC visit, keeping storage bounded.

        Active dialogue is prioritized, then an already authorized offer. Other
        quests remain available on a later visit; this is local recovery policy.
        """
        self._scope(actor, snapshot)
        self._interaction(proof, current)
        if proof.role_id != self.role_id or proof.login_epoch != self.login_epoch or now_ms >= deadline_ms:
            raise ValueError('Invalid task menu scope')
        self.cancel()
        for ident in sorted(snapshot.active):
            task = self.resources.definitions.get(ident)
            if task is None or (task['target']['npc_id'], task['target']['map_id']) != (proof.npc_id, proof.address.map_id):
                continue
            if supports_money_submission(task):
                # The dedicated opener checks the currency owner's payment
                # recipe before exposing a payable mode3 conversation.
                continue
            if supports_item_submission(task):
                if item_states is None:
                    continue  # integration has not supplied a transaction-consistent inventory read
                if not item_objective_available(actor,task,item_states):
                    return ((S_REFRESH_SCENARIO_QUEST_STATE,encode_scenario_state(ident,SCENARIO_ACTIVE)),
                            (S_VISIT_NPC,encode_visit_npc(proof.entity_key,(),(ident,))))
                self.open_items(actor,snapshot,ident,proof,current,item_states,now_ms=now_ms,deadline_ms=deadline_ms)
                return self.opening_messages()
            try:
                self.open(actor, snapshot, ident, proof, current, now_ms=now_ms, deadline_ms=deadline_ms)
            except ValueError:
                continue
            return self.opening_messages()
        offered = self.domain.available(actor, snapshot)
        for ident in offered:
            intent = TaskIntent(C_COMMIT_SCENARIO_QUEST, ident, proof.entity_key, 0)
            try:
                self.plan_accept(actor, snapshot, intent, proof, current, now_ms=now_ms, deadline_ms=deadline_ms)
            except ValueError:
                continue
            return ((S_REQUEST_QUEST_CAN_ACCEPT, encode_quest_can_accept(offered)),
                    (S_VISIT_NPC, encode_visit_npc(proof.entity_key, (), (ident,))))
        return ((S_VISIT_NPC, encode_visit_npc(proof.entity_key)),)

    def open_items(self, actor, snapshot, task_id, proof, current, item_states, *, now_ms, deadline_ms):
        """Use the same one-ticket role owner for plain talk and item selection."""
        self._scope(actor,snapshot)
        self._interaction(proof,current)
        task=self.resources.definitions.get(task_id)
        if (task is None or task_id not in snapshot.active or now_ms>=deadline_ms
                or (proof.role_id,proof.login_epoch)!=(self.role_id,self.login_epoch)
                or not proof.source_id or len(proof.source_id)>160
                or (task['target']['npc_id'],task['target']['map_id'])!=(proof.npc_id,proof.address.map_id)
                or not item_objective_available(actor,task,item_states)):
            raise ValueError('Task item conversation is unavailable')
        self.ticket=TaskConversationTicket(task_id,self.role_id,self.login_epoch,proof.source_id,
            proof.address,proof.position_version,proof.npc_id,proof.entity_key,deadline_ms)
        return TaskDialogue(self.ticket,tuple((line['speaker'],line['text']) for line in task['dialogue']['start']))

    def item_prompt_messages(self):
        """Verified alternate SSubmit2Npc path: original config, default opaque0.

        opening_messages preserves the local dialogue/menu path. This direct
        prompt is available only after open_items validated current ownership.
        """
        ticket=self.ticket
        if ticket is None or not supports_item_submission(self.resources.definitions[ticket.task_id]):
            raise ValueError('No validated task item conversation')
        return ((S_SUBMIT_2_NPC,encode_npc_submission_prompt(ticket.task_id,ticket.entity_key,1,(),0)),)

    def plan_item_submission(self, actor, snapshot, command, current, item_states, *, now_ms):
        self._scope(actor,snapshot)
        return plan_item_objective(actor,snapshot,command,self.ticket,current,item_states,self.resources,now_ms=now_ms)

    def acceptance_messages(self, plan, npc_key):
        if (plan.action != 'accept' or plan.role_id != self.role_id
                or plan.login_epoch != self.login_epoch):
            raise ValueError('Task acceptance acknowledgement mismatch')
        return ((S_ACCEPT_SCENARIO_QUEST, encode_accept_scenario_quest(
            ScenarioQuestInfo(plan.task_id, SCENARIO_ACTIVE, 0, 0, npc_key))),)

    def opening_messages(self):
        """For an already synchronized active quest: ready state then NPC menu.

        Native menu vector 2 is quest IDs. Its state-3 branch reads original
        dialogue locally; no generic confirmation dialog is substituted.
        """
        if self.ticket is None:
            raise ValueError('No validated task conversation')
        return ((S_REFRESH_SCENARIO_QUEST_STATE, encode_scenario_state(self.ticket.task_id, SCENARIO_READY)),
                (S_VISIT_NPC, encode_visit_npc(self.ticket.entity_key, (), (self.ticket.task_id,))))

    def resume_messages(self, actor, snapshot):
        """Restore supported ordinary objective beans; other types stay pending.

        Static type12's ordinary selector reads config and actual bag, not these
        two bean values. Full tracker-counter meaning remains unverified.
        """
        self._scope(actor, snapshot)
        result = []
        for ident in sorted(snapshot.active):
            task = self.resources.definitions.get(ident)
            if task is None:
                continue
            if supports_level_gate(task):
                result.append((S_ACCEPT_SCENARIO_QUEST,encode_accept_scenario_quest(
                    ScenarioQuestInfo(ident,SCENARIO_ACTIVE,actor.level,0,0))))
                continue
            if supports_static_region(task):
                result.append((S_ACCEPT_SCENARIO_QUEST,encode_accept_scenario_quest(
                    ScenarioQuestInfo(ident,SCENARIO_ACTIVE,0,0,0))))
                continue
            if (supports_npc_finish_dialogue(task) or supports_npc_start_dialogue(task)
                    or supports_npc_empty_scenario(task) or supports_fixed_npc_quiz(task)
                    or supports_money_submission(task) or supports_fighting_pet_task(task)
                    or supports_prologue_touch(task) or supports_prologue_puzzle(task)):
                result.append((S_ACCEPT_SCENARIO_QUEST,encode_accept_scenario_quest(
                    ScenarioQuestInfo(ident,SCENARIO_ACTIVE,0,0,0))))
                continue
            if task['type'] not in (10,12):
                continue
            target = task['target']
            if task['type']==12:
                if not supports_item_submission(task):
                    continue
            else:
                try:
                    self.domain.plan(actor, snapshot, 'complete', ident,evidence=self._dialogue_evidence(
                        ident,'resume-capability-check',target['map_id'],target['npc_id']))
                except ValueError:
                    continue
            result.append((S_ACCEPT_SCENARIO_QUEST, encode_accept_scenario_quest(
                ScenarioQuestInfo(ident, SCENARIO_ACTIVE, 0, 0, 0))))
        return tuple(result)

    def _current_ticket(self,actor,snapshot,current,now_ms):
        self._scope(actor, snapshot)
        ticket = self.ticket
        if (ticket is None or now_ms >= ticket.deadline_ms
                or (ticket.role_id,ticket.login_epoch)!=(self.role_id,self.login_epoch)
                or current.role_id != self.role_id or current.login_epoch != self.login_epoch
                or current.address != ticket.address or current.version != ticket.position_version
                or current.state != 'active'):
            raise ValueError('Expired or moved task conversation')
        return ticket

    def plan_finish(self, actor, snapshot, intent, current, *, now_ms):
        ticket=self._current_ticket(actor,snapshot,current,now_ms)
        if supports_fixed_npc_quiz(self.resources.definitions[ticket.task_id]):
            raise ValueError('Quiz requires its original CAnswerQuestion, not a dialogue completion')
        if supports_money_submission(self.resources.definitions[ticket.task_id]):
            raise ValueError('Task money requires its original money confirmation and wallet settlement')
        if intent.kind not in (C_COMMIT_SCENARIO_QUEST, C_QUEST_DIALOG_END) or intent.task_id != ticket.task_id:
            raise ValueError('Task submission does not match conversation')
        if intent.kind == C_COMMIT_SCENARIO_QUEST and (intent.npc_key != ticket.entity_key or intent.opaque != 0):
            raise ValueError('Task submission NPC or option is unconfirmed')
        task=self.resources.definitions[ticket.task_id]
        if (supports_native_effect_dialogue(task) or supports_npc_finish_dialogue(task)
                or supports_npc_start_dialogue(task) or supports_npc_empty_scenario(task)) and intent.kind!=C_COMMIT_SCENARIO_QUEST:
            raise ValueError('Native NPC dialogue requires ordinary NPC commit')
        # Domain rejects animation, battle, delivery and timed-task shortcuts.
        evidence=self._dialogue_evidence(ticket.task_id,ticket.source_id,ticket.address.map_id,ticket.npc_id)
        return self.domain.plan(actor, snapshot, 'complete', ticket.task_id, evidence=evidence)

    def plan_quiz_answer(self,actor,snapshot,answer,current,*,now_ms):
        """Correct code0 plans completion; a legal wrong answer has no plan.

        Codes are source identities, not shuffled display-row indexes. The
        bounded local recovery behavior for wrong answers is to retain active;
        event-specific failure/branch policy remains a separate integration.
        """
        ticket=self._current_ticket(actor,snapshot,current,now_ms)
        task=self.resources.definitions[ticket.task_id]
        if (not isinstance(answer,TaskQuizAnswer) or not supports_fixed_npc_quiz(task)
                or ticket.task_id not in snapshot.active or answer.task_id!=ticket.task_id
                or type(answer.npc_key) is not int or answer.npc_key!=ticket.entity_key
                or type(answer.answer_code) is not int
                or not 0<=answer.answer_code<=len(task['lists']['QuestionInfoWrongAnswerList'])):
            raise ValueError('Quiz answer differs from the current original NPC question')
        if answer.answer_code:return None
        return self.domain.plan(actor,snapshot,'complete',ticket.task_id,evidence=self._dialogue_evidence(
            ticket.task_id,ticket.source_id,ticket.address.map_id,ticket.npc_id))

    def plan_money_submission(self,actor,snapshot,command,current,*,now_ms):
        """Validate the native exact amount; caller joins its wallet debit.

        This pure plan is not a paid receipt. The dedicated transaction applies
        the currency-owner-approved recipe and completion atomically.
        """
        ticket=self._current_ticket(actor,snapshot,current,now_ms)
        task=self.resources.definitions[ticket.task_id]
        if (type(command) is not TaskMoneySubmission or not supports_money_submission(task)
                or ticket.task_id not in snapshot.active or command.task_id!=ticket.task_id
                or type(command.npc_key) is not int or command.npc_key!=ticket.entity_key
                or type(command.amount) is not int or command.amount!=int(task['attributes']['ActiveInfoGiveBackMoney'])
                or ticket.npc_id!=task['target']['npc_id'] or ticket.address.map_id!=task['target']['map_id']):
            raise ValueError('Task money differs from the current original NPC amount')
        return self.domain.plan(actor,snapshot,'complete',ticket.task_id,evidence=self._dialogue_evidence(
            ticket.task_id,ticket.source_id,ticket.address.map_id,ticket.npc_id))

    def acknowledge(self, plan):
        """Role owner calls this only after its transaction commits successfully."""
        ticket = self.ticket
        if (ticket is None or plan.role_id != self.role_id or plan.login_epoch != self.login_epoch
                or plan.task_id != ticket.task_id or plan.source_event != ticket.source_id
                or plan.action != 'complete'):
            raise ValueError('Task completion acknowledgement mismatch')
        self.ticket = None

    def cancel(self):
        self.ticket = None
