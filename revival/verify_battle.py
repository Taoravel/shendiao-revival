"""Battle behavior and native codec checks; no live accounts/processes modified."""
import json
import struct
import unittest
from pathlib import Path
from battle import Battle, Fighter, Skill, Command
from training_battle import TrainingBattle,DEFAULT_RULES
import battle_protocol as p

ROLE={'id':123,'name':'训练侠客','shape':1010109,'level':1}


class BattleChecks(unittest.TestCase):
    def test_training_victory_and_playback_barrier(self):
        t=TrainingBattle(ROLE)
        for turn in range(1,5):
            replies=t.receive(p.SEND_ACTION,struct.pack('>iiiBB',1,21,0,1,0))
            self.assertEqual([x[0] for x in replies],[p.ROUND_SCRIPT])
            snapshot=t.battle.fighters
            self.assertEqual(t.receive(p.SEND_ACTION,struct.pack('>iiiBB',1,21,0,1,0)),[])
            self.assertEqual(t.battle.fighters,snapshot)
            with self.assertRaises(ValueError):t.battle.resolve()
            replies=t.receive(p.CLIENT_PLAY_END,b'\0')
            self.assertEqual([x[0] for x in replies],
                [p.BATTLE_END] if turn==4 else [p.SERVER_PLAY_END,p.ROUND_START])
            self.assertEqual(t.receive(p.CLIENT_PLAY_END,b'\0'),[])
        self.assertEqual([f.hp for f in t.battle.fighters],[79,0])
        self.assertTrue(t.result['won'])
        self.assertEqual(t.result['currency_reward'],0)
        self.assertFalse(t.result['task_event_eligible'])

    def test_guard_and_timeout(self):
        t=TrainingBattle(ROLE)
        t.receive(p.SEND_ACTION,struct.pack('>iiiBB',4,0,0,1,0))
        self.assertEqual([f.hp for f in t.battle.fighters],[97,60])
        clock=[0]
        t=TrainingBattle(ROLE,clock=lambda:clock[0])
        clock[0]=29
        self.assertEqual(t.tick(),[])
        clock[0]=30
        self.assertEqual(t.tick()[0][0],p.ROUND_SCRIPT)
        self.assertEqual(t.tick(),[])
        self.assertEqual([f.hp for f in t.battle.fighters],[93,44])

    def test_invalid_target_and_unsupported_commands_leave_turn_open(self):
        t=TrainingBattle(ROLE)
        for body in (b'',struct.pack('>iiiBB',1,1,0,1,0),struct.pack('>iiiBB',99,0,21,1,0),
                     struct.pack('>iiiBB',1,21,0,0,0)):
            self.assertEqual(t.receive(p.SEND_ACTION,body),[])
            self.assertEqual(t.battle.pending,(1,21))
        self.assertEqual(t.receive(p.CLIENT_PLAY_END,b'\xff'),[])

    def test_escape_and_disconnect(self):
        t=TrainingBattle(ROLE)
        t.receive(p.SEND_ACTION,struct.pack('>iiiBB',9,0,0,1,0))
        t.receive(p.CLIENT_PLAY_END,b'\0')
        self.assertFalse(t.result['won'])
        t=TrainingBattle(ROLE);t.close()
        self.assertEqual(t.battle.phase,'ended')
        self.assertIsNone(t.result)

    def test_dead_actor_cannot_attack_and_tie_uses_position(self):
        b=Battle((Fighter(21,1,hp=10,attack=100,speed=10),Fighter(1,0,attack=100,speed=10)))
        b.submit(1,Command(21,'attack',1));b.submit(1,Command(1,'attack',21))
        events=b.resolve()
        self.assertEqual(len(events),1)
        self.assertEqual(events[0].actor,1)
        self.assertEqual(b.fighters[0].hp,100)
        self.assertEqual(b.winner,0)

    def test_skill_validation_self_heal_and_mp(self):
        b=Battle((Fighter(1,0,hp=40,mp=10,skills=(1001,)),Fighter(21,1,attack=5)),
                 skills=(Skill(1001,6,30,True),))
        with self.assertRaises(ValueError): b.submit(1,Command(1,'skill',21,1001))
        b.submit(1,Command(1,'skill',1,1001));b.submit(1,Command(21,'defend'))
        b.resolve();b.acknowledge(1)
        self.assertEqual((b.fighters[0].hp,b.fighters[0].mp),(70,4))
        with self.assertRaises(ValueError):b.submit(2,Command(1,'skill',1,1001))
        self.assertIn(1,b.pending)

    def test_round_cap_and_late_command(self):
        b=Battle((Fighter(1,0),Fighter(21,1)),max_rounds=1)
        b.submit(1,Command(1,'defend'));b.submit(1,Command(21,'defend'))
        b.resolve();b.acknowledge(1)
        self.assertEqual((b.phase,b.winner),('ended',-1))
        with self.assertRaises(ValueError): b.submit(1,Command(1,'defend'))

    def test_gateway_dispatch_and_world_lock(self):
        from gateway import Session
        from wire import frame, FrameReader
        s=Session(None)
        with self.assertRaises(ValueError):s.start_training()
        s.state='world';s.role=dict(ROLE)
        self.assertEqual([k for k,b in FrameReader().feed(b''.join(s.start_training()))],
                         [p.BATTLE_START,p.ADD_FIGHTERS,p.ROUND_START])
        from world_movement import ROLE_MOVE
        self.assertEqual(s.feed(frame(ROLE_MOVE,b'')),[])
        self.assertEqual(s.events[-1]['reason'],'in_battle')
        for turn in range(4):
            packets=s.feed(frame(p.SEND_ACTION,struct.pack('>iiiBB',1,21,0,1,0)))
            self.assertEqual(FrameReader().feed(b''.join(packets))[0][0],p.ROUND_SCRIPT)
            s.feed(frame(p.CLIENT_PLAY_END,b'\0'))
        self.assertIsNone(s.training)
        self.assertEqual(sum(e['event']=='training_battle_finished' for e in s.events),1)
        s.feed(frame(p.CLIENT_PLAY_END,b'\0'))
        self.assertEqual(sum(e['event']=='training_battle_finished' for e in s.events),1)


def native_checks():
    from research_battle import NativeBattleDecoder
    cases=[('SSendBattleStart',p.battle_start(background=6,music=2)),
        ('SSendAddFighters',p.add_fighters([p.fighter(1,123,1010109,'训练侠客长名字测试',1,100),
                                         p.fighter(21,20001,6013,'小灰狗',3,60)])),
        ('SSendRoundStart',p.round_start(7)),
        ('CSendAction',struct.pack('>iiiBB',1,21,0,1,0)),
        ('CSendRoundPlayEnd',b'\1'+struct.pack('>i',123)),
        ('SSendRoundScript',p.round_script([((1,0,0,0,1,0,0,0,0),[p.TargetResult(21,((p.HP_CHANGE,-16),))])])),
        ('SSendBattleEnd',p.battle_end({1:2})),
        ('SSendRoundPlayEnd',struct.pack('>i',7))]
    results=[]
    for name,payload in cases:
        n=NativeBattleDecoder().decode(name,payload)
        if name=='SSendBattleStart':
            assert n.read(n.obj+0x1c)==6 and n.read(n.obj+0x20)==2
        elif name=='SSendAddFighters':
            fighters=n.list_items(n.obj+8)
            assert len(fighters)==2
            for addr,pos,kind,hp in zip(fighters,(1,21),(1,3),(100,60)):
                # Native SSendAddFighters debug consumers 0x118e223/0x118e1d2
                # read type at +4 and battle position at +0x4c respectively.
                assert n.read(addr+4)==kind, 'Fighter type/position were swapped'
                assert n.read(addr+0x4c)==pos, 'Fighter position does not match script target'
                assert n.read(addr+0x10)==1, 'Fighter level was populated with model ID'
                assert n.read(addr+0x64)==(1010109 if kind==1 else 6013), 'Native model field is empty'
                assert [n.read(addr+x) for x in (0x54,0x58,0x5c)]==[hp]*3
            text=fighters[0]+0x14
            data=n.read(text+4) if n.read(text+24)>=8 else text+4
            assert bytes(n.u.mem_read(data,n.read(text+20)*2)).decode('utf-16-le')=='训练侠客长名字测试'
        elif name=='CSendAction':
            assert [n.read(n.obj+x) for x in (0xc,0x10,0x14)]==[1,21,0]
        elif name=='SSendRoundScript':
            items=n.list_items(n.obj+8)
            assert len(items)==1 and n.read(items[0]+8)==1 # attacker
            targets=n.list_items(items[0]+0x38)
            assert len(targets)==1 and n.read(targets[0]+4)==21
            attrs=n.list_items(targets[0]+0x14)
            assert len(attrs)==0, 'HP must not be placed in the DemoAttr collection'
            from research_battle_damage import consumed_target_hp
            assert consumed_target_hp(payload)==-16
        results.append({'class':name,'bytes':len(payload),'native_consumed':len(payload)})
    # Follow the actual snapshot -> training opening -> native decoder seam.
    damaged=TrainingBattle(ROLE,actor_stats={'hp':40,'max_hp':100})
    payload=next(body for kind,body in damaged.opening() if kind==p.ADD_FIGHTERS)
    n=NativeBattleDecoder().decode('SSendAddFighters',payload)
    actor=n.list_items(n.obj+8)[0]
    assert [n.read(actor+x) for x in (0x54,0x58,0x5c)]==[100,100,40], 'Damaged snapshot lost max HP in native fighter'
    from research_battle_commands import native_action, button_arguments
    defend=button_arguments(0x11bb230)[1]
    escape=button_arguments(0x11bb644)[1]
    for operation,target in ((1,21),(defend,0),(escape,0)):
        t=TrainingBattle(ROLE)
        assert t.receive(p.SEND_ACTION,native_action(operation,target)), 'Original client command rejected by training adapter'
        assert t.battle.phase=='playback'
    t=TrainingBattle(ROLE)
    wait=next(body for kind,body in t.opening() if kind==p.ROUND_START)
    assert struct.unpack_from('>i',wait)[0]==30, 'Client command timer must receive seconds, not round index'
    return results


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(BattleChecks))
    if not result.wasSuccessful():raise SystemExit(1)
    native=native_checks()
    report={'behavior_tests_passed':result.testsRun,'native_codecs':native,
            'native_commands_accepted':['attack','defend','escape'],
            'damaged_snapshot_max_hp_verified':True,'native_command_timer_seconds':30,
            'training_rules_revision':DEFAULT_RULES.revision,'live_client_battle_verified':False,
            'scope':'offline state transitions, native decoders/sender commands, gateway world fixture; live presentation pending'}
    (Path(__file__).parent/'evidence/battle-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))
