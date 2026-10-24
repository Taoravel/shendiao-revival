"""Battle ownership, bounded admission and cross-owner progress checks."""
import asyncio
from dataclasses import replace, FrozenInstanceError
import json
from pathlib import Path
import struct
import unittest
from battle_owner import Participant, BattleOwner, BattleCommand
from training_battle import DEFAULT_RULES
import battle_protocol as p

PLAYER=Participant(123,7,9,11,'训练侠客',1010109,1)
ATTACK=struct.pack('>iiiBB',1,21,0,1,0)


def owner(**limits):
    options={'mailbox_capacity':4,'receipt_capacity':64,'playback_timeout_ms':90000,'now_ms':0}
    options.update(limits)
    return BattleOwner(PLAYER,DEFAULT_RULES,**options)


def command(o,sequence,kind=p.SEND_ACTION,body=ATTACK,request=None,deadline=100000):
    s=o.snapshot()
    return BattleCommand(o.id,PLAYER.role_id,PLAYER.login_epoch,PLAYER.connection_generation,
                         request or str(sequence),sequence,s.state_version,s.round_number,deadline,kind,body)


def send(o,c,now=0):
    assert o.submit(c,now)=='accepted'
    return o.process_one(now)


class OwnerChecks(unittest.TestCase):
    def test_four_round_victory_and_versioned_completion(self):
        o=owner();initial=o.initial()
        self.assertEqual(len(initial.delivery.packets),3)
        self.assertEqual(o.initial().rejection,'already_started_or_closed')
        for turn in range(1,5):
            attack=send(o,command(o,turn*2-1))
            self.assertEqual(attack.snapshot.phase,'playback')
            done=send(o,command(o,turn*2,p.CLIENT_PLAY_END,b'\0'))
        self.assertEqual(done.snapshot.phase,'ended')
        self.assertEqual(done.finished.login_epoch,7)
        self.assertEqual(done.finished.snapshot_version,11)
        self.assertEqual(done.finished.settlement_id,'training:'+o.id)
        self.assertTrue(done.finished.won)
        self.assertFalse(done.finished.task_event_eligible)
        self.assertEqual(o.terminal(),done)

    def test_stale_lease_is_rejected_before_queue(self):
        o=owner(mailbox_capacity=1);o.initial();c=command(o,1)
        for changed in (replace(c,battle_id='other'),replace(c,login_epoch=6),
                        replace(c,connection_generation=8),replace(c,role_id=456)):
            self.assertNotEqual(o.submit(changed,0),'accepted')
        self.assertEqual(o.submit(c,0),'accepted')
        self.assertEqual(o.submit(c,0),'backpressure')

    def test_queued_expiry_and_old_state_do_not_mutate(self):
        o=owner();o.initial();s=o.snapshot()
        c=command(o,1,deadline=5)
        self.assertEqual(o.submit(c,0),'accepted')
        self.assertEqual(o.process_one(5).rejection,'deadline')
        self.assertEqual(o.snapshot(),s)
        result=send(o,command(o,2),5)
        self.assertEqual(send(o,replace(c,request_id='late',sequence=3,deadline_ms=100),5).rejection,'stale_state')
        self.assertEqual(o.snapshot(),result.snapshot)

    def test_request_retry_and_collision(self):
        o=owner();o.initial();c=command(o,1)
        original=send(o,c)
        replay=send(o,replace(c,deadline_ms=200000))
        self.assertTrue(replay.replayed)
        self.assertEqual(replay.snapshot,original.snapshot)
        self.assertIsNone(replay.delivery)
        self.assertIsNone(replay.finished)
        collision=send(o,replace(c,body=struct.pack('>iiiBB',9,0,0,1,0)))
        self.assertEqual(collision.rejection,'request_id_conflict')
        self.assertEqual(o.snapshot(),original.snapshot)

    def test_state_and_sequence_fences_across_round(self):
        o=owner();o.initial();c=command(o,1);send(o,c)
        send(o,command(o,2,p.CLIENT_PLAY_END,b'\0'))
        self.assertEqual(send(o,replace(c,request_id='replayed-old',sequence=3)).rejection,'stale_state')
        oldseq=replace(command(o,3),sequence=1,request_id='old-seq')
        self.assertEqual(send(o,oldseq).rejection,'stale_sequence')
        self.assertEqual(o.snapshot().round_number,2)

    def test_receipt_capacity_rejects_without_eviction(self):
        o=owner(receipt_capacity=1);o.initial();c=command(o,1);send(o,c)
        result=send(o,command(o,2,p.CLIENT_PLAY_END,b'\0'))
        self.assertEqual(result.rejection,'receipt_backpressure')
        self.assertTrue(send(o,c).replayed)
        self.assertEqual(o.snapshot().phase,'playback')

    def test_timeout_and_abort_have_no_reward_or_false_win(self):
        o=owner(playback_timeout_ms=50);o.initial()
        self.assertIsNone(o.advance(29999))
        timed=o.advance(30000)
        self.assertEqual(timed.snapshot.phase,'playback')
        self.assertIsNone(o.advance(30049))
        expired=o.advance(30050)
        self.assertEqual(expired.aborted.reason,'playback_timeout')
        self.assertIsNone(expired.finished)
        self.assertEqual(expired.delivery.packets[0][0],p.BATTLE_END)
        self.assertIsNone(o.advance(30051))
        self.assertEqual(o.close('disconnect',30052),expired)

    def test_immutable_boundary_and_generation_target(self):
        o=owner();opening=o.initial()
        with self.assertRaises(FrozenInstanceError):opening.snapshot.phase='ended'
        with self.assertRaises(FrozenInstanceError):opening.snapshot.fighters[0].hp=0
        self.assertIsInstance(opening.delivery.packets,tuple)
        self.assertEqual((opening.delivery.role_id,opening.delivery.login_epoch,
                          opening.delivery.connection_generation),(123,7,9))

    def test_invalid_input_has_bounded_diagnostics_and_no_state_change(self):
        o=owner(receipt_capacity=128);o.initial();before=o.snapshot()
        for i in range(1,70):
            r=send(o,command(o,i,body=b''))
            self.assertEqual(r.rejection,'Invalid CSendAction length')
        self.assertEqual(o.snapshot(),before)
        self.assertEqual(o.submit(replace(command(o,71),body=bytes(258)),0),'invalid_protocol')
        with self.assertRaises(ValueError):o.advance(-1)


class RuntimeChecks(unittest.IsolatedAsyncioTestCase):
    async def test_paused_battle_does_not_stop_other_battle(self):
        from runtime_core import SerialOwner
        a,b=owner(),owner();a.initial();b.initial()
        entered,release=asyncio.Event(),asyncio.Event()
        async def slow(c):
            entered.set();await release.wait()
            a.submit(c.args[0],0)
            return a.process_one(0)
        async def fast(c):
            b.submit(c.args[0],0)
            return b.process_one(0)
        ra,rb=SerialOwner('battle:'+a.id,slow,capacity=2),SerialOwner('battle:'+b.id,fast,capacity=2)
        pending=asyncio.create_task(ra.call('input',command(a,1)))
        try:
            await asyncio.wait_for(entered.wait(),1)
            other=await asyncio.wait_for(rb.call('input',command(b,1)),1)
            self.assertEqual(other.snapshot.phase,'playback')
            self.assertFalse(pending.done())
        finally:
            release.set();await pending
            await ra.close();await rb.close()


if __name__=='__main__':
    suite=unittest.TestSuite((unittest.defaultTestLoader.loadTestsFromTestCase(OwnerChecks),
                              unittest.defaultTestLoader.loadTestsFromTestCase(RuntimeChecks)))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():raise SystemExit(1)
    report={'checks_passed':result.testsRun,'controlled_other_battle_progress':True,
            'runtime_gateway_integrated':False,'live_client_verified':False,
            'scope':'battle owner, bounded mailbox and shared SerialOwner harness; not server capacity'}
    (Path(__file__).parent/'evidence/battle-owner-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
