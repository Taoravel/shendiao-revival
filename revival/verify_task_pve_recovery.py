"""Retired actual combat checkpoint -> dedicated no-award recovery terminal."""
from dataclasses import replace
from pathlib import Path
import unittest
from verify_task_pve_engine import owner, send
from task_pve import load_task_pve_rules
from research_battle_commands import native_action
from task_pve_recovery import abort_checkpoint_terminal
import battle_protocol as p


class TaskPveRecoveryChecks(unittest.TestCase):
    def test_lost_owner_retains_real_damage_without_creating_a_victory(self):
        battle = owner()
        battle.initial()
        outcome = send(battle, 1, p.SEND_ACTION, native_action(p.ATTACK, 21))
        snapshot, participant = outcome.snapshot, battle.participant
        battle.close('disconnected', 1)
        rules = load_task_pve_rules(Path(__file__).parent / 'design/task-pve-ai8001-v1.json')
        event = abort_checkpoint_terminal(participant, snapshot, rules, current_epoch=8)
        self.assertFalse(event.won)
        self.assertEqual((event.outcome, event.winner_side), ('draw', -1))
        self.assertEqual((event.login_epoch, event.battle_id), (7, snapshot.battle_id))
        self.assertEqual(event.combat_resources[0].hp, 96)
        self.assertEqual(event.scope, 'task_quest_v1')
        with self.assertRaises(ValueError):
            abort_checkpoint_terminal(participant, snapshot,
                rules, current_epoch=participant.login_epoch)
        with self.assertRaises(ValueError):
            abort_checkpoint_terminal(participant, snapshot,
                rules, current_epoch=str(participant.login_epoch))
        with self.assertRaises(ValueError):
            abort_checkpoint_terminal(participant,
                replace(snapshot, fighters=tuple(replace(f, hp=f.max_hp+1) for f in snapshot.fighters)),
                rules, current_epoch=8)


if __name__ == '__main__':
    unittest.main(verbosity=2)
