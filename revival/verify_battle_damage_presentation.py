"""Disposable domain output -> original decoder and HP-result consumer.

No game executable, listener, live battle, live account or database is accessed.
"""
from dataclasses import replace
import hashlib
import json
import sys
from pathlib import Path
import unittest
from battle import Fighter
from battle_owner import Participant
from training_battle import TrainingBattle,TrainingPet,DEFAULT_RULES
from wild_battle import WildBattle
from wild_encounters import WildEncounters,load_wild_rules
from world_owner import Location,MapAddress,MoveResult
from research_battle import NativeBattleDecoder
from research_battle_commands import native_action
from research_battle_damage import consumed_target_hp
import battle_protocol as p

ROOT=Path(__file__).parent
ROLE=dict(id=123,name='离线伤害探针',shape=1010109,level=5)
# Captured from the unchanged npc-role-healing-20261023T125539Z serializer.
# Its original decoder succeeds but the original HP-result consumer reads0.
LEGACY_PACKET=bytes.fromhex('01000000010000000000000000000000000000000100000000000000000000000000000000000100000015000100000001fffffff00000000000000000000000')


class DamageChecks(unittest.TestCase):
    def assert_consumed_damage(self,battle,before,packets):
        body=next(body for kind,body in packets if kind==p.ROUND_SCRIPT)
        n=NativeBattleDecoder().decode('SSendRoundScript',body)
        seen={f.id:0 for f in battle.battle.fighters}
        for item_index,item in enumerate(n.list_items(n.obj+8)):
            for target_index,target in enumerate(n.list_items(item+0x38)):
                self.assertEqual(n.list_items(target+0x14),[], 'HP was put in the unrelated DemoAttr list')
                seen[n.read(target+4)]+=consumed_target_hp(body,item_index=item_index,target_index=target_index)
        expected={f.id:f.hp-before[f.id] for f in battle.battle.fighters}
        self.assertEqual(seen,expected, 'Native HP-result consumer differs from authoritative battle damage')
        return body

    @staticmethod
    def before(battle):return {f.id:f.hp for f in battle.battle.fighters}

    def test_old_packet_is_decodable_but_damage_is_ignored(self):
        self.assertEqual(len(LEGACY_PACKET),64)
        self.assertEqual(consumed_target_hp(LEGACY_PACKET),0)

    def test_real_attack_output_reaches_native_hp_consumer(self):
        battle=TrainingBattle(ROLE)
        before=self.before(battle)
        packets=battle.receive(p.SEND_ACTION,native_action(p.ATTACK,21))
        body=self.assert_consumed_damage(battle,before,packets)
        self.assertEqual(consumed_target_hp(body),-16)

    def test_defend_keeps_reduced_damage_and_no_fake_target(self):
        battle=TrainingBattle(ROLE);before=self.before(battle)
        packets=battle.receive(p.SEND_ACTION,native_action(p.DEFEND,0))
        body=self.assert_consumed_damage(battle,before,packets)
        n=NativeBattleDecoder().decode('SSendRoundScript',body)
        self.assertEqual(n.list_items(n.list_items(n.obj+8)[0]+0x38),[])
        self.assertEqual(consumed_target_hp(body,item_index=1),-3)

    def test_lethal_hit_is_clamped_without_fabricating_extra_damage(self):
        battle=TrainingBattle(ROLE,actor_stats={'attack':100});before=self.before(battle)
        packets=battle.receive(p.SEND_ACTION,native_action(p.ATTACK,21))
        body=self.assert_consumed_damage(battle,before,packets)
        self.assertEqual(consumed_target_hp(body),-before[21])

    def test_skill_keeps_one_mp_cost_and_native_target_damage(self):
        battle=TrainingBattle(ROLE,authorized_skills=(100008,));before=self.before(battle)
        packets=battle.receive(p.SEND_ACTION,native_action(p.SKILL,21,100008))
        body=self.assert_consumed_damage(battle,before,packets)
        self.assertEqual(consumed_target_hp(body),-22)
        n=NativeBattleDecoder().decode('SSendRoundScript',body)
        self.assertEqual(n.read(n.list_items(n.obj+8)[0]+0x10),10)

    def test_role_pet_and_enemy_hits_each_have_their_own_result_map(self):
        pet=TrainingPet(123,7,500001,3,'离线小灰狗',5,6,True,True)
        battle=TrainingBattle(ROLE,pet=pet);before=self.before(battle)
        self.assertEqual(battle.receive(p.SEND_ACTION,native_action(p.ATTACK,21)),[])
        packets=battle.receive(p.SEND_ACTION,native_action(p.ATTACK,21,is_role=False))
        self.assert_consumed_damage(battle,before,packets)

    def test_multi_target_codec_keeps_separate_native_results(self):
        body=p.round_script([((1,0,10,0,p.SKILL,100008,0,0,0),
            [p.TargetResult(22,((p.HP_CHANGE,-11),)),p.TargetResult(21,((p.HP_CHANGE,-7),))])])
        self.assertEqual(consumed_target_hp(body,target_index=0),-11)
        self.assertEqual(consumed_target_hp(body,target_index=1),-7)

    def test_original_taihu_cat_wild_adapter_two_rounds(self):
        rules=load_wild_rules();area=rules.maps[1014]
        cat=next(i for i,m in enumerate(area.monsters) if m.template_id==21102 and m.name=='小花猫')
        values=iter((0,cat))
        class RandomFixture:
            def randrange(self,_):return next(values)
        old=Location(123,7,MapAddress(1014,1,0),1,127*16,56*16)
        current=replace(old,version=2,x=old.x+rules.distance)
        encounters=WildEncounters(old,rules,now_ms=0,rng=RandomFixture())
        ticket=encounters.accepted_move(old,MoveResult(current,current),now_ms=rules.grace_ms,eligible=True)
        self.assertIsNotNone(ticket)
        participant=Participant(123,7,9,11,ROLE['name'],ROLE['shape'],2,
            Fighter(1,0,hp=100,max_hp=100,mp=100,attack=20,defense=5,speed=20))
        battle=WildBattle(participant,ticket,DEFAULT_RULES,clock=lambda:0)
        battle.opening()
        for round_number in (1,2):
            self.assertEqual(battle.battle.round,round_number)
            before=self.before(battle)
            packets=battle.receive(p.SEND_ACTION,native_action(p.ATTACK,21))
            self.assert_consumed_damage(battle,before,packets)
            battle.receive(p.CLIENT_PLAY_END,b'\0')


def main():
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(DamageChecks))
    if not result.wasSuccessful():raise SystemExit(1)
    report=dict(checks_passed=result.testsRun,legacy_native_hp_change=consumed_target_hp(LEGACY_PACKET),
        original_consumer_range=['0x11910df','0x1191821'],
        scope='original decoded target-result map dispatch and actual training/wild output; no rendering',
        production_files={name:hashlib.sha256(Path(sys.modules[name[:-3]].__file__).read_bytes()).hexdigest()
                          for name in ('battle_protocol.py','training_battle.py')},
        live_client_opened=False,live_battle_executed=False,live_service_changed=False,
        rendered_animation_verified=False)
    report_path=ROOT/'evidence/battle-damage-presentation-verification.json'
    report_path.parent.mkdir(parents=True,exist_ok=True)
    report_path.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
