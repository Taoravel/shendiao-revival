"""Expanded rewards through real admission/settlement/inventory interfaces."""
from contextlib import closing
from dataclasses import replace
import json
from pathlib import Path
import tempfile
from types import MappingProxyType
import unittest
from accounts import AccountStore
from inventory import Inventory,AssetChange,pet_record
from battle import Fighter
from battle_owner import Participant
from battle_loadout import selected_pet,CombatResources
from training_battle import BattleFinished,DEFAULT_RULES
from world_owner import Location,MapAddress
from wild_encounters import EncounterTicket,load_wild_rules
from wild_rewards import load_wild_reward_rules,prepare_wild_reward_storage,register_wild_reward,settle_wild_reward,wild_pet_refresh
from currency import load_currency_rules,prepare_wallet_storage,initialize_wallet,read_wallet
from progression import read_experience
from wild_battle import WildBattle
import battle_protocol as p

ROOT = Path(__file__).parent


class ExpandedChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rules,cls.reward,cls.money = load_wild_rules(),load_wild_reward_rules(),load_currency_rules()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='wild-v2-')
        self.addCleanup(self.temp.cleanup)
        self.store = AccountStore(Path(self.temp.name)/'state.sqlite3')
        self.role = self.store.create_role(1111,'野外奖励',11,1010109)
        self.config = Inventory.prepare(self.store)
        self.inv = Inventory(self.store,1111,self.role['id'],self.config)
        self.epoch = self.store.acquire_lease(1111,self.role['id'])
        with closing(self.store.connect()) as db:
            prepare_wallet_storage(db); prepare_wild_reward_storage(db); db.commit()
        self.tx(lambda db:initialize_wallet(db,1111,self.role['id'],self.epoch,(0,0,0,0),'new_restoration_role',self.money))
        self.tx(lambda db:db.execute('UPDATE roles SET level=5 WHERE id=?',(self.role['id'],)))
        area = self.rules.maps[1014]
        self.participant = Participant(self.role['id'],self.epoch,1,7,'野外奖励',1010109,5,Fighter(1,0))
        self.ticket = EncounterTicket('reward-v2-fixture',Location(self.role['id'],self.epoch,
            MapAddress(1014,1,0),1,896,3776),area.monsters[0],5,area.background,
            Fighter(21,1,hp=60,max_hp=60),self.rules.revision)

    def tx(self,call):
        with closing(self.store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            return call(db)

    def admission(self,index,participant=None,ticket=None):
        participant,ticket = participant or self.participant,ticket or self.ticket
        ident = 'v2-'+str(index)
        self.tx(lambda db:register_wild_reward(db,1111,participant,ticket,ident,self.inv,self.reward))
        return BattleFinished(ident,'wild:'+ident,self.role['id'],0,True,1,ticket.revision,
            self.epoch,participant.attribute_version,scope='wild_encounter_v1',outcome='victory')

    def settle(self,result,inventory=None):
        return self.tx(lambda db:settle_wild_reward(db,1111,self.role['id'],self.epoch,result,
            inventory or self.inv,self.money))

    def balances(self):
        return self.tx(lambda db:(read_experience(db,1111,self.role['id']),
            read_wallet(db,1111,self.role['id'],self.epoch,self.money)))

    def add_pet(self):
        key = self.inv.grant_pet(500001)
        self.tx(lambda db:self.inv.change_pet_growth(db,key,'fixture:level1',0,'experience',50))
        self.inv.fight_pet(key)
        snapshot = self.tx(lambda db:self.inv.immutable_snapshot_transaction(db,epoch=self.epoch))
        pet = selected_pet(snapshot,role_id=self.role['id'],role_level=5,templates=DEFAULT_RULES.pet_templates,
                           growth_revision=self.inv.growth_rules.revision)
        self.participant = replace(self.participant,pet=pet)
        return pet

    def terminal_pet(self,result,pet,hp=None):
        return replace(result,combat_resources=(CombatResources('pet',pet.key,pet.position,pet.growth_version,
            pet.stats.hp if hp is None else hp,pet.stats.max_hp,pet.stats.mp,pet.max_mp,False,
            pet.inventory_revision,pet.growth_revision),))

    def test_three_independent_drop_groups_and_real_equipment_details(self):
        result = self.admission(1206)
        receipt = self.settle(result)
        # Worked deterministic fixture: 杜仲, 破损瓷器 and level-one equipment.
        grants = receipt['items_awarded']
        self.assertEqual(grants[:2],[[33013,1,1],[50015,1,1]])
        self.assertEqual(len(grants),3)
        self.assertEqual((receipt['cash_awarded'],receipt['silver_awarded']),(10,10))
        items = self.inv.snapshot()['items']
        equipment = next(i for i in items if i['template_id'] == grants[2][0])
        self.assertIsNotNone(equipment['condition'])
        self.assertIsNotNone(equipment['detail'])
        self.assertEqual(equipment['condition'].current,equipment['condition'].maximum)
        self.assertEqual(equipment['detail'].prefix_quality,1)
        before = self.inv.snapshot()
        self.assertTrue(self.settle(result)['replayed'])
        self.assertEqual(self.inv.snapshot(),before)

    def test_porcelain_three_forms_and_gap_boundaries(self):
        for index,item in ((3,50002),(5,50015),(15,50001)):
            receipt = self.settle(self.admission(index))
            self.assertIn([item,1,1],receipt['items_awarded'])
        # +5 still allows porcelain; +6 excludes it while retaining base XP.
        at5 = self.settle(self.admission('edge5',replace(self.participant,level=10)))
        # Use the identical deterministic seed in fresh role-owned databases.
        self.assertGreater(at5['experience_awarded'],0)
        for level,allowed in ((10,True),(11,False),(1,True)):
            self.setUp()
            receipt = self.settle(self.admission(5,replace(self.participant,level=level)))
            self.assertEqual([50015,1,1] in receipt['items_awarded'],allowed)

    def test_equipment_tier_selection_and_all_153_templates_generate(self):
        pools = self.reward.content['pools']['equipment']
        self.assertEqual(sum(map(len,pools.values())),153)
        for level,rows in pools.items():
            for row in rows:
                # Public inventory grant exercised in a rollback-only transaction.
                with closing(self.store.connect()) as db:
                    db.execute('BEGIN IMMEDIATE')
                    self.inv.apply_settlement(db,AssetChange('codec:'+str(row['item_id']),((row['item_id'],1,1),)))
                    snapshot = self.inv.immutable_snapshot_transaction(db,epoch=self.epoch)
                    item = next(i for i in snapshot.items if i.template_id == row['item_id'])
                    self.assertIsNotNone(item.detail)
                    self.assertIsNotNone(item.condition)
                    db.rollback()
        # The same known equipment roll selects the scene-appropriate tier.
        for scene,expected in ((10,10),(25,20),(50,50),(85,80),(125,80)):
            self.setUp()
            receipt = self.settle(self.admission(3,replace(self.participant,level=scene),replace(self.ticket,level=scene)))
            equipment = [g[0] for g in receipt['items_awarded'] if g[0] in self.inv.detail_rules.templates]
            self.assertEqual(len(equipment),1)
            self.assertEqual(int(self.inv.items[equipment[0]]['level']),expected)

    def test_pet_experience_and_terminal_resources_are_atomic_and_once(self):
        pet = self.add_pet()
        result = self.terminal_pet(self.admission(0),pet,hp=1)
        old = self.tx(lambda db:self.inv.read_pet_state(db,pet.key))
        receipt = self.settle(result)
        self.assertEqual(receipt['pet_experience']['recipient'],pet.key)
        self.assertEqual(receipt['pet_experience']['awarded'],receipt['experience_awarded']*2)
        current = self.tx(lambda db:self.inv.read_pet_state(db,pet.key))
        self.assertEqual(current.progress.state.experience,old.progress.state.experience+receipt['experience_awarded']*2)
        self.assertEqual(current.progress.state.hp,1)
        self.assertTrue(self.settle(result)['replayed'])
        # Repeated admission after completion uses its original snapshot, not new pet growth.
        self.admission(0)
        self.assertEqual(self.tx(lambda db:self.inv.read_pet_state(db,pet.key)),current)
        self.assertTrue(pet_record(current.__dict__))
        # Historical receipt refreshes later current XP for the same pet key.
        self.tx(lambda db:self.inv.change_pet_growth(db,pet.key,'later:exp',current.progress.state.version,'experience',1))
        packets = self.tx(lambda db:wild_pet_refresh(db,1111,self.role['id'],self.epoch,receipt,self.inv))
        import struct
        self.assertEqual(struct.unpack('>iQ',packets[1][1]),(pet.key,current.progress.state.experience+1))

    def test_dead_pet_gets_no_experience_and_wrong_recipient_rejected(self):
        pet = self.add_pet()
        result = self.terminal_pet(self.admission(0),pet,hp=0)
        receipt = self.settle(result)
        self.assertEqual(receipt['pet_experience']['awarded'],0)
        self.assertEqual(self.tx(lambda db:self.inv.read_pet_state(db,pet.key)).progress.state.hp,0)
        self.setUp(); pet = self.add_pet()
        result = self.terminal_pet(self.admission(0),pet)
        wrong = replace(result,combat_resources=(replace(result.combat_resources[0],entity_id=pet.key+1),))
        with self.assertRaises(ValueError): self.settle(wrong)
        with self.assertRaises(ValueError): self.settle(replace(result,combat_resources=()))

    def test_pet_level_cap_uses_entry_role_and_keeps_excess_experience(self):
        for pet_level,awarded in ((9,True),(10,True),(11,False)):
            self.setUp(); pet = self.add_pet()
            amount = sum(self.inv.growth_rules.thresholds[n] for n in range(1,pet_level))
            self.tx(lambda db:self.inv.change_pet_growth(db,pet.key,'fixture:raise',pet.growth_version,'experience',amount))
            snapshot = self.tx(lambda db:self.inv.immutable_snapshot_transaction(db,epoch=self.epoch))
            pet = selected_pet(snapshot,role_id=self.role['id'],role_level=5,templates=DEFAULT_RULES.pet_templates,
                               growth_revision=self.inv.growth_rules.revision)
            self.participant = replace(self.participant,pet=pet)
            result = self.terminal_pet(self.admission(0,ticket=replace(self.ticket,level=125)),pet)
            receipt = self.settle(result)
            after = self.tx(lambda db:self.inv.read_pet_state(db,pet.key))
            self.assertEqual(receipt['pet_experience']['status']=='awarded',awarded)
            self.assertEqual(after.progress.state.level,10 if awarded else 11)
            if awarded: self.assertGreater(after.progress.state.experience,0)

    def test_switch_pet_does_not_redirect_and_changed_growth_rejected(self):
        pet = self.add_pet(); result = self.terminal_pet(self.admission(0),pet)
        other = self.inv.grant_pet(500001)
        self.inv.fight_pet(other)
        receipt = self.settle(result)
        self.assertEqual(receipt['pet_experience']['recipient'],pet.key)
        self.assertEqual(self.tx(lambda db:self.inv.read_pet_state(db,other)).progress.state.experience,0)
        self.setUp(); pet = self.add_pet(); result = self.terminal_pet(self.admission(0),pet)
        self.tx(lambda db:self.inv.change_pet_growth(db,pet.key,'other:award',pet.growth_version,'experience',1))
        before = self.balances()
        with self.assertRaises(ValueError): self.settle(result)
        self.assertEqual(self.balances(),before)

    def test_bag_failure_rolls_back_pet_money_experience_and_all_drop_groups(self):
        pet = self.add_pet(); result = self.terminal_pet(self.admission(1206),pet,hp=1)
        before,balances = self.inv.snapshot(),self.balances()
        tiny = Inventory(self.store,1111,self.role['id'],replace(self.config,
            policy=MappingProxyType({**self.config.policy,'bag_capacity':0})))
        with self.assertRaises(ValueError): self.settle(result,tiny)
        self.assertEqual(self.inv.snapshot(),before)
        self.assertEqual(self.balances(),balances)
        receipt = self.settle(result)
        self.assertEqual(len(receipt['items_awarded']),3)
        self.assertGreater(receipt['pet_experience']['awarded'],0)

    def test_native_battle_finish_feeds_actual_reward_transaction(self):
        pet = self.add_pet()
        actor = replace(self.participant,stats=Fighter(1,0,hp=100,max_hp=100,attack=999,speed=999))
        battle = WildBattle(actor,self.ticket,DEFAULT_RULES,clock=lambda:0)
        self.tx(lambda db:register_wild_reward(db,1111,actor,self.ticket,battle.id,self.inv,self.reward))
        battle.opening()
        battle.receive(p.SEND_ACTION,__import__('struct').pack('>iiiBB',p.ATTACK,21,0,1,0))
        battle.receive(p.SEND_ACTION,__import__('struct').pack('>iiiBB',p.ATTACK,21,0,0,0))
        battle.receive(p.CLIENT_PLAY_END,b'\0')
        result = battle.finished()
        self.assertIsNotNone(result)
        receipt = self.settle(result)
        self.assertGreater(receipt['pet_experience']['awarded'],0)


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ExpandedChecks))
    (ROOT/'evidence/wild-rewards-v2-verification.json').write_text(json.dumps(dict(tests=result.testsRun,
        errors=len(result.errors),failures=len(result.failures),runtime_integrated=False,
        live_client_verified=False),indent=2),encoding='utf-8')
    raise SystemExit(not result.wasSuccessful())
