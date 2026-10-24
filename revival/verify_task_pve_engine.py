"""Dedicated quest battle through the public BattleOwner and original commands.

No listener, GUI, live database, synthetic victory or task state edits.
"""
from pathlib import Path
from dataclasses import replace
import struct
import unittest
from battle import Fighter
from battle_owner import Participant, BattleOwner, BattleCommand
from battle_loadout import OwnedBattlePet, PetTemplate
from research_battle_commands import native_action
from research_battle_damage import consumed_target_hp
from task_battle import TaskBattleDefinition
from task_pve import TaskPveBattle, load_task_pve_rules
import battle_protocol as p

ROOT = Path(__file__).parent
DEFINITION = TaskBattleDefinition(100107, 8001, 1501, 10908, 'a' * 64, {}, {})
PLAYER = Participant(123, 7, 9, 11, '梦境验证', 1010109, 2,
                     Fighter(1, 0, 100, 100, 40, 25, 5, 10, max_mp=40))


def owner(participant=PLAYER, *, rules=None):
    rules = rules or load_task_pve_rules(ROOT / 'design/task-pve-ai8001-v1.json')
    return BattleOwner(participant, rules, mailbox_capacity=64,
        receipt_capacity=1024, playback_timeout_ms=rules.playback_timeout_ms,
        now_ms=0, engine_factory=lambda actor, frozen, clock:
            TaskPveBattle(actor, frozen, DEFINITION, clock=clock))


def send(battle, sequence, kind, body, now_ms=0):
    state = battle.snapshot()
    actor = battle.participant
    command = BattleCommand(battle.id, actor.role_id, actor.login_epoch,
        actor.connection_generation, str(sequence), sequence, state.state_version,
        state.round_number, now_ms + 1000, kind, body)
    if battle.submit(command, now_ms) != 'accepted':
        raise AssertionError('Current trusted battle command was rejected')
    return battle.process_one(now_ms)


class TaskPveChecks(unittest.TestCase):
    def test_actual_two_round_victory_requires_original_playback_ack(self):
        battle = owner()
        opening = battle.initial()
        self.assertIn(p.ADD_FIGHTERS, dict(opening.delivery.packets))
        for turn, expected_damage in ((1, -22), (2, -18)):
            hit = send(battle, turn * 2 - 1, p.SEND_ACTION, native_action(p.ATTACK, 21))
            self.assertEqual(hit.snapshot.phase, 'playback')
            self.assertIsNone(hit.finished)
            script = dict(hit.delivery.packets)[p.ROUND_SCRIPT]
            self.assertEqual(consumed_target_hp(script), expected_damage)
            done = send(battle, turn * 2, p.CLIENT_PLAY_END, b'\0')
        self.assertEqual(done.snapshot.phase, 'ended')
        result = done.finished
        self.assertTrue(result.won)
        self.assertEqual((result.scope, result.task_event_eligible), ('task_quest_v1', True))
        self.assertEqual(result.settlement_id, 'task-battle:' + battle.id)
        self.assertEqual((result.role_id, result.login_epoch, result.snapshot_version), (123, 7, 11))
        self.assertEqual((result.currency_reward, result.item_rewards), (0, ()))
        resources = result.combat_resources[0]
        self.assertEqual((resources.kind, resources.hp, resources.mp), ('role', 96, 40))

    def test_defend_reduces_real_enemy_damage_and_escape_never_wins(self):
        battle = owner()
        battle.initial()
        hit = send(battle, 1, p.SEND_ACTION, native_action(p.DEFEND, 0))
        self.assertEqual(next(f.hp for f in hit.snapshot.fighters if f.id == 1), 98)
        self.assertEqual(consumed_target_hp(dict(hit.delivery.packets)[p.ROUND_SCRIPT],
                                          item_index=1), -2)
        send(battle, 2, p.CLIENT_PLAY_END, b'\0')
        send(battle, 3, p.SEND_ACTION, native_action(p.ESCAPE, 0))
        done = send(battle, 4, p.CLIENT_PLAY_END, b'\0')
        self.assertEqual((done.finished.outcome, done.finished.won), ('escape', False))
        self.assertTrue(done.finished.combat_resources[0].escaped)

    def test_real_defeat_preserves_raw_zero_and_timeout_never_awards_win(self):
        weak = replace(PLAYER, stats=replace(PLAYER.stats, hp=1, attack=1, speed=1))
        battle = owner(weak)
        battle.initial()
        send(battle, 1, p.SEND_ACTION, native_action(p.ATTACK, 21))
        done = send(battle, 2, p.CLIENT_PLAY_END, b'\0')
        self.assertEqual((done.finished.outcome, done.finished.combat_resources[0].hp), ('defeat', 0))
        self.assertFalse(done.finished.won)
        battle = owner()
        battle.initial()
        hit = battle.advance(30000)
        self.assertEqual(hit.snapshot.phase, 'playback')
        self.assertIsNone(hit.finished)
        expired = battle.advance(60000)
        self.assertEqual((expired.finished.outcome, expired.finished.won), ('draw', False))
        self.assertEqual(expired.finished.combat_resources[0].hp, 96)

    def test_learned_ledger_never_becomes_training_authorization_or_ui_overwrite(self):
        actor = replace(PLAYER, authorized_skills=(999999,))
        battle = owner(actor)
        initial = battle.initial()
        self.assertNotIn(p.OTHER_SKILLS, dict(initial.delivery.packets))
        before = battle.snapshot()
        rejected = send(battle, 1, p.SEND_ACTION, native_action(p.SKILL, 21, 999999))
        self.assertTrue(rejected.rejection)
        self.assertEqual(rejected.snapshot.fighters, before.fighters)
        self.assertEqual(rejected.snapshot.pending, before.pending)
        self.assertEqual(battle.participant.authorized_skills, (999999,))

    def test_malformed_or_early_end_does_not_create_terminal(self):
        battle = owner()
        battle.initial()
        early = send(battle, 1, p.CLIENT_PLAY_END, b'\0')
        self.assertIsNone(early.finished)
        for sequence, body in enumerate((b'', native_action(p.ATTACK, 1),
                native_action(p.DEFEND, 21), struct.pack('>iiiBB', 1, 21, 0, 2, 0)), start=2):
            result = send(battle, sequence, p.SEND_ACTION, body)
            self.assertTrue(result.rejection)
            self.assertEqual(result.snapshot.phase, 'commands')
            self.assertIsNone(result.finished)

    def test_owned_pet_joins_real_commands_and_leaves_with_escaping_owner(self):
        pet = OwnedBattlePet(123, 17, 500001, 4, 3, 'pet-policy-v1', '小灰狗', 2, 6,
            6013, Fighter(6, 0, 35, 40, 10, 10, 3, 4, max_mp=20), 20)
        rules = load_task_pve_rules(ROOT / 'design/task-pve-ai8001-v1.json',
                                   pet_templates=(PetTemplate(500001, 6013, 1, 1),))
        battle = owner(replace(PLAYER, pet=pet), rules=rules)
        initial = battle.initial()
        self.assertEqual(len(initial.snapshot.fighters), 3)
        role_command = send(battle, 1, p.SEND_ACTION, native_action(p.ESCAPE, 0))
        self.assertEqual(role_command.snapshot.phase, 'commands')
        hit = send(battle, 2, p.SEND_ACTION, native_action(p.ATTACK, 21, is_role=False))
        self.assertEqual(hit.snapshot.phase, 'playback')
        done = send(battle, 3, p.CLIENT_PLAY_END, b'\0')
        self.assertEqual(done.finished.outcome, 'escape')
        own_pet = done.finished.combat_resources[1]
        self.assertEqual((own_pet.kind, own_pet.entity_id, own_pet.hp, own_pet.mp), ('pet', 17, 35, 10))
        self.assertEqual((own_pet.inventory_revision, own_pet.source_version), (4, 3))
        self.assertTrue(own_pet.escaped)
        with self.assertRaises(ValueError):
            owner(replace(PLAYER, pet=replace(pet, role_id=456)), rules=rules)

    def test_full_two_hundred_rounds_finish_as_draw_without_receipt_exhaustion(self):
        actor = replace(PLAYER, stats=replace(PLAYER.stats, hp=2000, max_hp=2000, defense=999))
        pet = OwnedBattlePet(123, 17, 500001, 4, 3, 'pet-policy-v1', '小灰狗', 2, 6,
            6013, Fighter(6, 0, 35, 40, 10, 10, 3, 4, max_mp=20), 20)
        rules = load_task_pve_rules(ROOT / 'design/task-pve-ai8001-v1.json',
                                   pet_templates=(PetTemplate(500001, 6013, 1, 1),))
        battle = owner(replace(actor, pet=pet), rules=rules)
        battle.initial()
        defend = native_action(p.DEFEND, 0)
        pet_defend = native_action(p.DEFEND, 0, is_role=False)
        for turn in range(1, 201):
            pending = send(battle, turn * 3 - 2, p.SEND_ACTION, defend)
            self.assertEqual(pending.snapshot.phase, 'commands')
            self.assertFalse(pending.rejection)
            hit = send(battle, turn * 3 - 1, p.SEND_ACTION, pet_defend)
            self.assertEqual(hit.snapshot.phase, 'playback')
            self.assertFalse(hit.rejection)
            done = send(battle, turn * 3, p.CLIENT_PLAY_END, b'\0')
        self.assertEqual((done.finished.outcome, done.finished.rounds), ('draw', 200))
        self.assertFalse(done.finished.won)

    def test_receipt_budget_refuses_locally_without_evicting_retry_evidence(self):
        battle = owner()
        battle.initial()
        state = battle.snapshot()
        actor = battle.participant
        first = None
        for sequence in range(1, 1025):
            command = BattleCommand(battle.id, actor.role_id, actor.login_epoch,
                actor.connection_generation, str(sequence), sequence, state.state_version,
                state.round_number, 1000, p.SEND_ACTION, b'')
            first = first or command
            self.assertEqual(battle.submit(command, 0), 'accepted')
            self.assertTrue(battle.process_one(0).rejection)
        full = send(battle, 1025, p.SEND_ACTION, native_action(p.ATTACK, 21))
        self.assertEqual(full.rejection, 'receipt_backpressure')
        self.assertEqual(battle.snapshot(), state)
        self.assertEqual(battle.submit(first, 0), 'accepted')
        self.assertTrue(battle.process_one(0).replayed)
        another = owner()
        another.initial()
        self.assertEqual(send(another, 1, p.SEND_ACTION,
                              native_action(p.ATTACK, 21)).snapshot.phase, 'playback')

    def test_recipe_drift_and_non_enabled_original_ai_are_rejected(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory(prefix='task-pve-policy-') as folder:
            changed = Path(folder) / 'recipe.json'
            changed.write_bytes((ROOT / 'design/task-pve-ai8001-v1.json').read_bytes() + b' ')
            with self.assertRaises(ValueError):
                load_task_pve_rules(changed)
        rules = load_task_pve_rules(ROOT / 'design/task-pve-ai8001-v1.json')
        for definition in (replace(DEFINITION, task_id=101003), replace(DEFINITION, ai_id=8002),
                           replace(DEFINITION, npc_id=10909)):
            with self.assertRaises(ValueError):
                TaskPveBattle(PLAYER, rules, definition, clock=lambda: 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
