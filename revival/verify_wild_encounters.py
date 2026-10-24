"""Offline public-interface checks; no live role, listener or database changes."""
from dataclasses import replace
import json
from pathlib import Path
import random
import struct
import unittest
from battle import Fighter
from battle_owner import Participant
from training_battle import DEFAULT_RULES
from world_owner import MapOwner, MapAddress, Location, MoveCommand, MoveResult, TransferOffer
from world_catalog import maps
from world_movement import CHECK_MOVE, ROLE_MOVE
from wild_encounters import WildEncounters, load_wild_rules
from wild_battle import WildBattle
import battle_protocol as p

ROOT = Path(__file__).parent
RULES = load_wild_rules()


class ScriptRandom:
    def __init__(self, *values): self.values = iter(values); self.calls = 0
    def randrange(self, n):
        self.calls += 1
        value = next(self.values)
        assert 0 <= value < n
        return value


class EncounterChecks(unittest.TestCase):
    def setUp(self):
        self.location = Location(17, 101, MapAddress(1014,1,0), 1, 896, 3776)
        self.random = ScriptRandom(0,0)
        self.owner = WildEncounters(self.location,RULES,now_ms=0,rng=self.random)

    def move(self, *, dx=64, now=5000, eligible=True, owner=None):
        owner = owner or self.owner
        old = owner.location
        new = replace(old, version=old.version+1, x=old.x+dx)
        return owner.accepted_move(old,MoveResult(new,new),now_ms=now,eligible=eligible)

    def ticket(self):
        ticket = self.move()
        self.assertIsNotNone(ticket)
        return ticket

    def test_original_scene_specific_distribution_and_town_exclusion(self):
        self.assertNotIn(1007,RULES.maps)
        self.assertEqual({m.name for m in RULES.maps[1002].monsters},{'野猪','流浪者'})
        self.assertIn('小灰狗',{m.name for m in RULES.maps[1014].monsters})
        self.assertEqual(len(RULES.maps),46)

    def test_tower_visible_maps_do_not_also_roll_hidden_encounters(self):
        for mid in range(1200,1207):
            old=replace(self.location,address=MapAddress(mid,1,0),x=512,y=512)
            owner=WildEncounters(old,RULES,now_ms=0,rng=ScriptRandom())
            self.assertEqual(RULES.maps[mid].encounter_mode,'visible')
            self.assertIsNone(self.move(owner=owner))

    def test_actual_map_owner_checkpoint_triggers_original_monster(self):
        domain = MapOwner(self.location.address,maps(),capacity=2,transfer_capacity=2,mailbox_capacity=2)
        domain.join(self.location)
        body = struct.pack('>hhB Q',960,3776,0,1)
        result = domain.move(MoveCommand(self.location,'move-1',6000,CHECK_MOVE,body),5000)
        self.assertFalse(result.rejection)
        ticket = self.owner.accepted_move(self.location,result,now_ms=5000,eligible=True)
        self.assertEqual((ticket.monster.name,ticket.monster.shape_id),('小灰狗',6013))
        self.assertEqual((ticket.enemy.hp,ticket.enemy.attack,ticket.level),(60,13,5))

    def test_grace_stationary_and_intention_never_roll(self):
        self.assertIsNone(self.move(now=4999))
        self.assertIsNone(self.move(dx=0))
        old = self.owner.location
        self.assertIsNone(self.owner.accepted_move(old,MoveResult(location=old),now_ms=5000,eligible=True))
        self.assertEqual(self.random.calls,0)

    def test_distance_accumulation_and_chance_threshold(self):
        self.assertIsNone(self.move(dx=32))
        self.assertIsNotNone(self.move(dx=32))
        lose = WildEncounters(self.location,RULES,now_ms=0,rng=ScriptRandom(2000))
        self.assertIsNone(self.move(owner=lose))
        win = WildEncounters(self.location,RULES,now_ms=0,rng=ScriptRandom(1999,0))
        self.assertIsNotNone(self.move(owner=win))

    def test_stationary_and_same_cell_do_not_accumulate(self):
        for _ in range(10): self.assertIsNone(self.move(dx=1))
        self.assertEqual(self.random.calls,0)

    def test_stale_lease_position_and_failed_movement_rejected(self):
        old = self.owner.location
        self.move(dx=32)
        with self.assertRaises(ValueError):
            self.owner.accepted_move(old,MoveResult(old,old),now_ms=5000,eligible=True)
        current = self.owner.location
        for bad in (MoveResult(rejection='blocked'),
                    MoveResult(replace(current,login_epoch=102),replace(current,login_epoch=102))):
            with self.assertRaises(ValueError):
                self.owner.accepted_move(current,bad,now_ms=5000,eligible=True)

    def test_portal_loading_ineligible_and_safe_map(self):
        old = self.owner.location; new = replace(old,version=2,x=960)
        offer = TransferOffer('transfer',new,(1007,1,1),6000)
        self.assertIsNone(self.owner.accepted_move(old,MoveResult(new,new,offer),now_ms=5000,eligible=True))
        self.assertIsNone(self.move(eligible=False))
        self.assertEqual(self.random.calls,0)
        safe = WildEncounters(replace(old,address=MapAddress(1007,1,0)),RULES,now_ms=0,rng=ScriptRandom())
        self.assertIsNone(self.move(owner=safe))
        loading = replace(self.owner.location,state='loading')
        with self.assertRaises(ValueError):
            self.owner.accepted_move(self.owner.location,MoveResult(loading,loading),now_ms=5000,eligible=True)

    def test_one_pending_and_exact_battle_terminal_then_cooldown(self):
        ticket = self.ticket()
        self.assertIsNone(self.move())
        self.owner.accepted(ticket,'battle-1')
        with self.assertRaises(ValueError): self.owner.rejected(ticket,now_ms=5000)
        with self.assertRaises(ValueError): self.owner.finished(ticket,'battle-other',now_ms=5000)
        self.owner.finished(ticket,'battle-1',now_ms=5000)
        with self.assertRaises(ValueError): self.owner.finished(ticket,'battle-1',now_ms=5000)
        self.assertIsNone(self.move(now=14999))
        self.owner.rng = ScriptRandom(0,0)
        self.assertIsNotNone(self.move(now=15000))

    def test_admission_rejection_releases_with_cooldown(self):
        ticket = self.ticket()
        self.owner.rejected(ticket,now_ms=5000)
        self.assertIsNone(self.owner.pending)
        with self.assertRaises(ValueError): self.owner.accepted(ticket,'late')
        self.assertIsNone(self.move(now=5001))

    def test_independent_roles_and_long_report_one_attempt_only(self):
        other = WildEncounters(replace(self.location,role_id=18),RULES,now_ms=0,rng=random.Random(0))
        self.move(dx=4096)
        self.assertEqual(self.random.calls,2)
        self.assertIsNone(other.pending)
        self.assertEqual(other.location.role_id,18)

    def battle(self, stats=None):
        ticket = self.ticket()
        participant = Participant(17,101,1,7,'侠客',1010109,5,
            stats or Fighter(1,0,hp=100,max_hp=100,mp=100,attack=100,defense=10,speed=20))
        return WildBattle(participant,ticket,DEFAULT_RULES,clock=lambda:0)

    def test_native_roster_and_victory_result_no_training_identity_or_rewards(self):
        battle = self.battle()
        opening = battle.opening()
        roster = dict(opening)[p.ADD_FIGHTERS]
        self.assertEqual(struct.unpack('>8i2b',dict(opening)[p.BATTLE_START])[5],RULES.maps[1014].background)
        self.assertIn('小灰狗'.encode('utf-16le'),roster)
        self.assertNotIn('训练小灰狗'.encode('utf-16le'),roster)
        self.assertEqual(battle.opening(),[])
        battle.receive(p.SEND_ACTION,struct.pack('>iiiBB',p.ATTACK,21,0,1,0))
        self.assertIsNone(battle.finished())
        battle.receive(p.CLIENT_PLAY_END,b'\0')
        result = battle.finished()
        self.assertTrue(result.won)
        self.assertEqual(result.scope,'wild_encounter_v1')
        self.assertEqual(result.settlement_id,'wild:'+battle.id)
        self.assertEqual(result.snapshot_version,7)
        self.assertEqual((result.currency_reward,result.item_rewards,result.task_event_eligible),(0,(),False))
        self.assertEqual(battle.finished(),result)

    def test_all_recovered_monster_rosters_through_original_decoder(self):
        from research_battle import NativeBattleDecoder
        from wild_encounters import EncounterTicket
        from world_monsters import load_shape_ids
        shapes = load_shape_ids()
        checked = 0
        for area in RULES.maps.values():
            for monster in area.monsters:
                self.assertIn(monster.shape_id,shapes)
                location = replace(self.location,address=MapAddress(area.map_id,1,0))
                ticket = EncounterTicket('codec-fixture',location,monster,area.level,area.background,
                    Fighter(21,1,hp=60,max_hp=60),RULES.revision)
                participant = Participant(17,101,1,7,'侠客',1010109,5,Fighter(1,0,hp=40,max_hp=100))
                battle = WildBattle(participant,ticket,DEFAULT_RULES,clock=lambda:0)
                packets = dict(battle.opening())
                native = NativeBattleDecoder().decode('SSendAddFighters',packets[p.ADD_FIGHTERS])
                actor,enemy = native.list_items(native.obj+8)
                self.assertEqual(native.read(enemy+0x64),monster.shape_id)
                self.assertEqual(native.read(enemy+0x10),area.level)
                self.assertEqual(native.read(enemy+8),monster.template_id)
                self.assertEqual([native.read(actor+x) for x in (0x54,0x58,0x5c)],[100,100,40])
                native = NativeBattleDecoder().decode('SSendBattleStart',packets[p.BATTLE_START])
                self.assertEqual(native.read(native.obj+0x1c),area.background)
                checked += 1
        self.assertEqual(checked,107)

    def test_defeat_escape_close_and_missing_snapshot(self):
        battle = self.battle(Fighter(1,0,hp=1,max_hp=100,mp=100,attack=1,defense=0,speed=0))
        battle.opening()
        battle.receive(p.SEND_ACTION,struct.pack('>iiiBB',p.ATTACK,21,0,1,0))
        battle.receive(p.CLIENT_PLAY_END,b'\0')
        self.assertEqual(battle.finished().outcome,'defeat')
        self.setUp(); battle = self.battle(); battle.opening()
        battle.receive(p.SEND_ACTION,struct.pack('>iiiBB',p.ESCAPE,0,0,1,0))
        battle.receive(p.CLIENT_PLAY_END,b'\0')
        self.assertEqual(battle.finished().outcome,'escape')
        self.setUp(); battle = self.battle(); battle.close()
        self.assertIsNone(battle.finished())
        self.assertEqual(battle.opening(),[])
        with self.assertRaises(ValueError):
            WildBattle(replace(battle.participant,stats=None),battle.ticket,DEFAULT_RULES,clock=lambda:0)


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(EncounterChecks)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    (ROOT/'evidence/wild-encounters-verification.json').write_text(json.dumps(dict(
        tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),
        runtime_integrated=False, live_client_verified=False, asset_settlement_integrated=False),indent=2),encoding='utf-8')
    raise SystemExit(not result.wasSuccessful())
