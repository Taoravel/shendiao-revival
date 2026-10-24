"""Offline explicit training skill/pet snapshots and native wire validation."""
from dataclasses import replace
import json
from pathlib import Path
import struct
import unittest
from battle import Battle,Fighter,Skill,Command
from training_battle import TrainingBattle,TrainingPet,DEFAULT_RULES
from battle_owner import BattleOwner,Participant,BattleCommand
from research_battle import NativeBattleDecoder
from research_battle_commands import native_action
import battle_protocol as p

ROLE={'id':123,'name':'训练侠客','level':5,'shape':1010109}
PET=TrainingPet(123,7,500001,3,'小灰狗',5,6,True,True)


def native_map(n, container, value_format):
    head=n.read(container+4)
    root=n.read(head+4)
    result={}
    def visit(node):
        if node==head:return
        assert len(result)<64
        visit(n.read(node))
        key=n.read(node+0xc)
        result[key]=struct.unpack(value_format,n.u.mem_read(node+0x10,4))[0]
        visit(n.read(node+8))
    visit(root)
    return result


class LoadoutChecks(unittest.TestCase):
    def test_multitarget_command_charges_once_and_orders_primary_first(self):
        skill=Skill(100008,10,6,max_targets=2)
        b=Battle((Fighter(1,0,attack=20,skills=(100008,)),Fighter(21,1,defense=4),Fighter(22,1,defense=4)),(skill,))
        b.submit(1,Command(1,'skill',22,100008))
        b.submit(1,Command(21,'defend'));b.submit(1,Command(22,'defend'))
        events=b.resolve()
        spell=next(e for e in events if e.kind=='skill')
        self.assertEqual([(h.target,h.hp_change) for h in spell.impacts],[(22,-11),(21,-11)])
        self.assertEqual(b.fighters[0].mp,90)
        self.assertEqual(spell.mp_change,-10)

    def test_explicit_skill_native_sender_and_mp_presentation(self):
        t=TrainingBattle(ROLE,authorized_skills=(100008,))
        opening=t.opening()
        # Baseline .3 forbids temporary learned-menu injection until restore
        # semantics and the original complete skill snapshot are available.
        self.assertNotIn(p.OTHER_SKILLS,[kind for kind,body in opening])
        packets=t.receive(p.SEND_ACTION,native_action(2,21,100008))
        self.assertEqual([k for k,b in packets],[p.ROUND_SCRIPT,p.ROLE_INIT_ATTRS])
        n=NativeBattleDecoder().decode('SSendRoundScript',packets[0][1])
        item=n.list_items(n.obj+8)[0]
        self.assertEqual([n.read(item+x) for x in (8,0x10,0x18,0x1c)],[1,10,2,100008])
        targets=n.list_items(item+0x38)
        self.assertEqual(len(targets),1) # target count never duplicates a sole enemy
        self.assertEqual(t.battle.fighters[1].hp,38)
        n=NativeBattleDecoder().decode('SSendRoleInitAttrs',packets[1][1])
        self.assertEqual(native_map(n,n.obj+8,'<f')[70],90)

    def test_unauthorized_or_insufficient_mp_leaves_state(self):
        for t in (TrainingBattle(ROLE),TrainingBattle(ROLE,actor_stats={'mp':9},authorized_skills=(100008,))):
            before=t.battle.fighters
            self.assertEqual(t.receive(p.SEND_ACTION,native_action(2,21,100008)),[])
            self.assertEqual(t.battle.fighters,before)
            self.assertEqual(t.battle.pending,(1,21))

    def test_pet_command_is_independent_and_uses_original_pet_flag(self):
        t=TrainingBattle(ROLE,pet=PET)
        added=next(body for kind,body in t.opening() if kind==p.ADD_FIGHTERS)
        n=NativeBattleDecoder().decode('SSendAddFighters',added)
        pet=n.list_items(n.obj+8)[2]
        self.assertEqual([n.read(pet+x) for x in (4,8,0x10,0x4c,0x64)],[2,7,5,6,6013])
        self.assertEqual(t.receive(p.SEND_ACTION,native_action(1,21)),[])
        self.assertEqual(t.battle.pending,(6,21))
        self.assertEqual(t.receive(p.SEND_ACTION,native_action(1,21)),[])
        self.assertEqual(t.battle.pending,(6,21))
        packets=t.receive(p.SEND_ACTION,native_action(1,21,is_role=False))
        self.assertEqual([k for k,b in packets],[p.ROUND_SCRIPT,p.ROLE_INIT_ATTRS,p.PET_INIT_ATTRS])
        self.assertEqual([f.hp for f in t.battle.fighters],[93,80,33])
        for name,(_,body) in zip(('SSendRoundScript','SSendRoleInitAttrs','SSendPetInitAttrs'),packets):
            NativeBattleDecoder().decode(name,body)

    def test_pet_requires_eligibility_ownership_selection_and_fixture_authorization(self):
        for pet in (replace(PET,role_id=999),replace(PET,selected=False),replace(PET,fixture_authorized=False),
                    replace(PET,level=1),replace(PET,position=1),replace(PET,inventory_revision=0)):
            with self.assertRaises(ValueError):TrainingBattle(ROLE,pet=pet)
        with self.assertRaises(ValueError):TrainingBattle(dict(ROLE,level=1),pet=PET)
        t=TrainingBattle(ROLE)
        self.assertEqual(t.receive(p.SEND_ACTION,native_action(1,21,is_role=False)),[])

    def test_pet_timeout_fills_only_the_missing_command(self):
        clock=[0]
        t=TrainingBattle(ROLE,pet=PET,clock=lambda:clock[0])
        t.receive(p.SEND_ACTION,native_action(4,0))
        clock[0]=30
        self.assertTrue(t.tick())
        self.assertEqual([f.hp for f in t.battle.fighters],[97,80,49])
        self.assertEqual(t.tick(),[])

    def test_owner_snapshot_versions_include_partially_submitted_round(self):
        participant=Participant(123,7,9,11,ROLE['name'],ROLE['shape'],5,authorized_skills=(100008,),pet=PET)
        o=BattleOwner(participant,DEFAULT_RULES,mailbox_capacity=4,receipt_capacity=64,playback_timeout_ms=90000,now_ms=0)
        o.initial();before=o.snapshot()
        c=BattleCommand(o.id,123,7,9,'role',1,before.state_version,1,100,p.SEND_ACTION,native_action(2,21,100008))
        self.assertEqual(o.submit(c,0),'accepted')
        result=o.process_one(0)
        self.assertIsNone(result.delivery)
        self.assertGreater(result.snapshot.state_version,before.state_version)
        self.assertEqual(result.snapshot.pending,(6,21))
        after=result.snapshot
        pet=replace(c,request_id='pet',sequence=2,state_version=after.state_version,body=native_action(4,0,is_role=False))
        self.assertEqual(o.submit(pet,0),'accepted')
        result=o.process_one(0)
        self.assertEqual(result.snapshot.phase,'playback')
        self.assertEqual(result.delivery.connection_generation,9)


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(LoadoutChecks))
    if not result.wasSuccessful():raise SystemExit(1)
    report={'checks_passed':result.testsRun,'rules_revision':DEFAULT_RULES.revision,
            'scope':'explicit ephemeral training snapshots, original role/pet sender fields and native decoders',
            'existing_assets_changed':False,'live_runtime_activated':False,'live_gui_verified':False}
    (Path(__file__).parent/'evidence/battle-loadout-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
