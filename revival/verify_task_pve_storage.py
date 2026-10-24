"""Task PVE loadout Interface with a disposable actual role profile."""
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from accounts import AccountStore
from inventory import Inventory, AssetChange
from verify_npc_equipped_repair_runtime import seed_profile
from task_pve import load_task_pve_rules
from task_pve_runtime_storage import read_combat_snapshot_transaction
from training_battle import DEFAULT_RULES
from currency import initialize_wallet
import runtime_storage


class TaskCombatStorageChecks(unittest.TestCase):
    def test_actual_profile_required_and_complete_asset_source_changes_snapshot(self):
        with TemporaryDirectory(prefix='task-pve-loadout-') as folder:
            store = AccountStore(Path(folder) / 'state.sqlite3')
            role = store.create_role(1111, '任务战斗存储', 11, 1010109)
            runtime_storage.prepare(store)
            epoch = store.acquire_lease(1111, role['id'])
            inv = Inventory(store.leased(1111, role['id'], epoch), 1111, role['id'])
            rules = load_task_pve_rules(Path(__file__).parent / 'design/task-pve-ai8001-v1.json',
                                       pet_templates=DEFAULT_RULES.pet_templates)
            with closing(store.connect()) as db, db:
                db.execute('BEGIN IMMEDIATE')
                with self.assertRaises(ValueError):
                    read_combat_snapshot_transaction(db, store, 1111, role['id'], epoch, 9, rules)
            seed_profile(store, inv)
            with closing(store.connect()) as db, db:
                db.execute('BEGIN IMMEDIATE')
                initialize_wallet(db, 1111, role['id'], epoch, (1000, 0, 0, 0),
                                  'explicit_migration', store.currency_rules)
                first = read_combat_snapshot_transaction(db, store, 1111, role['id'], epoch, 9, rules)
                self.assertEqual((first.participant.stats.hp, first.participant.stats.mp), (70, 40))
                self.assertEqual((first.participant.role_id, first.participant.connection_generation),
                                 (role['id'], 9))
                self.assertIsNone(first.resources)
                self.assertIsNone(first.skill_ledger)
                inv.apply_settlement(db, AssetChange('owned-bag-source-change', grants=((49009, 1, 1),)))
                later = read_combat_snapshot_transaction(db, store, 1111, role['id'], epoch, 9, rules)
                self.assertEqual(first.participant, later.participant)
                self.assertNotEqual(first.basis, later.basis)


if __name__ == '__main__':
    unittest.main(verbosity=2)
