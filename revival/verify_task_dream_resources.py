"""Public caller-transaction dream recovery, isolated known resource fixture."""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from accounts import AccountStore
from inventory import Inventory
from role_growth import initialize_growth
from role_attribute_storage import initialize_attribute_baseline
from role_equipment import EquipmentAttributeBasis, resource_caps_from_projection
from role_equipment_storage import initialize_equipment_attribute_basis, current_equipment_totals
from role_resource_plan import plan_combat_resources, plan_resource_values
from role_resource_storage import (migrate_role_resources, read_role_resources,
    apply_resource_transition, revive_task_dream_resources)
from task_dream_resources import TaskDreamRevivePermit, POLICY_SHA256
from battle_loadout import CombatResources
import runtime_storage


class DreamResourceChecks(unittest.TestCase):
    def test_death_recovery_is_once_with_same_carrier_and_late_failure_rolls_back(self):
        with TemporaryDirectory(prefix='task-dream-resource-') as folder:
            store = AccountStore(Path(folder) / 'state.sqlite3')
            role = store.create_role(1111, '梦境资源验证', 11, 1010109)
            runtime_storage.prepare(store)
            epoch = store.acquire_lease(1111, role['id'])
            rid = role['id']
            rules, gear = store.resource_rules, store.equipment_attribute_rules
            inv = Inventory(store.leased(1111, rid, epoch), 1111, rid)
            with closing(store.connect()) as db, db:
                db.execute('BEGIN IMMEDIATE')
                growth = initialize_growth(db, 1111, rid, epoch, store.growth_rules,
                                           expected_level=1, free_points=0)
                initial = store.attribute_rules.initial_profile
                legacy = initialize_attribute_baseline(db, 1111, rid, epoch,
                    initial.baseline(rid), growth, store.attribute_rules,
                    replace(initial.vitals(rid), hp=70, mp=40))
                initialize_equipment_attribute_basis(db, 1111, rid, epoch,
                    EquipmentAttributeBasis(rid, 9, 0, gear.revision, 0, 'known-dream-fixture'), gear)
                totals = current_equipment_totals(db, 1111, rid, epoch,
                    inv.immutable_snapshot_transaction(db), gear)
                known = migrate_role_resources(db, 1111, rid, epoch, legacy.vitals,
                    resource_caps_from_projection(totals), origin='explicit_migration',
                    migration_id='dream-resource-known', rules=rules, equipment_rules=gear)
            dead = plan_combat_resources(known, 0, 35, rules)
            permit = TaskDreamRevivePermit(rid, epoch, 100107, 'real-owner-terminal',
                'task-battle:real-owner-terminal', '2026-10-24.task-pve-ai8001.1', POLICY_SHA256,
                'a' * 64, CombatResources('role', rid, 1, 1, 0, known.caps.hp_max,
                    35, known.caps.mp_max, False), dead.after.version)
            def settle(db):
                apply_resource_transition(db, 1111, rid, epoch, dead, 'dream-consume',
                                          rules=rules, equipment_rules=gear)
                return revive_task_dream_resources(db, 1111, rid, epoch, dead.after,
                                                   permit, rules=rules, equipment_rules=gear)
            with self.assertRaisesRegex(RuntimeError, 'after final encode'):
                with closing(store.connect()) as db, db:
                    db.execute('BEGIN IMMEDIATE')
                    settle(db)
                    raise RuntimeError('after final encode')
            with closing(store.connect()) as db, db:
                db.execute('BEGIN IMMEDIATE')
                self.assertEqual(read_role_resources(db, 1111, rid, epoch, rules), known)
                result = settle(db)
                self.assertFalse(result.replayed)
                self.assertEqual((result.resources.hp, result.resources.mp),
                                 (known.caps.hp_max, known.caps.mp_max))
                later = plan_combat_resources(result.resources, 61, 30, rules)
                apply_resource_transition(db, 1111, rid, epoch, later, 'later-real-damage',
                                          rules=rules, equipment_rules=gear)
                paid = revive_task_dream_resources(db, 1111, rid, epoch, dead.after, permit,
                                                  rules=rules, equipment_rules=gear)
                self.assertTrue(paid.replayed)
                self.assertEqual((paid.resources.hp, paid.resources.mp), (61, 30))
                with self.assertRaises(ValueError):
                    plan_resource_values(dead.after, 1, 35, 'medicine', rules)
                with self.assertRaises(ValueError):
                    revive_task_dream_resources(db, 1111, rid, epoch, dead.after,
                        replace(permit, task_id=101003), rules=rules, equipment_rules=gear)


if __name__ == '__main__':
    unittest.main(verbosity=2)
