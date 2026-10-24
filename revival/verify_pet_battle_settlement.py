"""Trusted battle care counts, level exemption and atomic owned settlement."""
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from dataclasses import replace
import sqlite3
import struct
from unittest.mock import patch
from accounts import AccountStore
from inventory import Inventory,pet_record
from inventory_test_support import known_cash_context
from pet_battle_care import BattleCareEvent
from inspect_client import OUT,write_json
from native_gameplay_probe import probe


def refused(action,errors=(ValueError,)):
    try:action()
    except errors:return
    raise AssertionError('Invalid battle care settlement accepted')


def main():
    with TemporaryDirectory() as tmp:
        store=AccountStore(Path(tmp)/'pet-battle.sqlite3')
        role=store.create_role(1111,'战斗养护',12,1010101)
        config=Inventory.prepare(store)
        inv=Inventory(store,1111,role['id'],config,**known_cash_context(store,1111,role['id']))
        pet=inv.grant_pet(500001)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            p=inv.pet_progress(db,pet)
            inv.change_pet_growth(db,pet,'battle-care:train',p.state.version,'experience',
                sum(inv.growth_rules.thresholds[i] for i in range(31)))
        for index in range(3):
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                p=inv.read_pet_state(db,pet);meter=inv.pet_battle_care_counter(db,pet)
                event=BattleCareEvent(f'battle-care:{index}',pet,p.template_id,p.care.version,
                                      p.progress.state.version,meter.version)
                receipt=inv.settle_pet_battle_care(db,event,inv.epoch)
        current=inv.immutable_snapshot().pets[0]
        assert (current.care.loyalty,current.care.lifetime)==(99,5997)
        assert (receipt.counter_after.version,receipt.counter_after.mod3)==(3,0)
        def capture(target,identity,**options):
            with closing(store.connect()) as db,db:
                db.execute('BEGIN')
                p=inv.read_pet_state(db,target);meter=inv.pet_battle_care_counter(db,target)
                return BattleCareEvent(identity,target,p.template_id,p.care.version,
                                       p.progress.state.version,meter.version,**options)
        def settle(event,inventory=inv):
            with closing(inventory.accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                return inventory.settle_pet_battle_care(db,event,inventory.epoch)
        # Death replaces the ordinary count, preserves the prior mod2, and is
        # followed by the next surviving battle's one loyalty debit.
        settle(capture(pet,'battle-care:4'));settle(capture(pet,'battle-care:5'))
        death=capture(pet,'battle-care:death',death_count=1)
        result=settle(death)
        assert (result.care_after.loyalty,result.care_after.lifetime)==(79,5945)
        assert result.counter_after==result.counter_before and result.counter_after.mod3==2
        result=settle(capture(pet,'battle-care:6'))
        assert (result.care_after.loyalty,result.care_after.lifetime,result.counter_after.mod3)==(78,5944,0)
        # Sparring and not actually participating are no-ops with durable IDs.
        before=inv.immutable_snapshot()
        spar=settle(capture(pet,'battle-care:spar',mode='sparring',death_count=1))
        absent=settle(capture(pet,'battle-care:absent',participated=False))
        assert spar.care_before==spar.care_after and spar.counter_before==spar.counter_after
        assert absent.care_before==absent.care_after and inv.immutable_snapshot()==before
        # Below and exactly30 loyalty is exempt, including death. Lifetime is
        # still charged, but no hidden young-level battle count accumulates.
        young=inv.grant_pet(500001)
        y=settle(capture(young,'battle-care:young0',death_count=1))
        assert (y.level,y.care_after.loyalty,y.care_after.lifetime,y.counter_after.mod3)==(0,100,5950,0)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');p=inv.pet_progress(db,young)
            inv.change_pet_growth(db,young,'battle-care:young-xp',p.state.version,'experience',
                sum(inv.growth_rules.thresholds[i] for i in range(30)))
        for i in range(3):y=settle(capture(young,f'battle-care:young30:{i}'))
        assert (y.level,y.care_after.loyalty,y.care_after.lifetime,y.counter_after.mod3)==(30,100,5947,0)
        y=settle(capture(young,'battle-care:young30:death',death_count=1))
        assert (y.care_after.loyalty,y.care_after.lifetime)==(100,5897)
        immortal=inv.grant_pet(500070)
        before=inv.immutable_snapshot()
        for i in range(4):
            god=settle(capture(immortal,f'battle-care:god:{i}',death_count=int(i==3)))
            assert god.care_before==god.care_after and god.counter_before==god.counter_after
        assert inv.immutable_snapshot()==before
        # Paid events are historical acknowledgements, never current refreshes.
        # Use the captured event unchanged even after later wounds and food.
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');p=inv.read_pet_state(db,pet)
            inv.change_pet_growth(db,pet,'battle-care:later-hp',p.progress.state.version,'resources',(7,3))
            inv.change_pet_care(db,pet,'battle-care:later-food',p.care.version,'feed',31001)
        before=inv.immutable_snapshot()
        with closing(store.connect()) as db,db:
            db.execute('BEGIN')
            def authorizer(op,*args):
                return sqlite3.SQLITE_DENY if op in (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE) else sqlite3.SQLITE_OK
            db.set_authorizer(authorizer)
            replay=inv.settle_pet_battle_care(db,death,inv.epoch)
            assert replay.replayed and replay.care_after.loyalty==79
            current=inv.read_pet_state(db,pet)
            assert (current.care.loyalty,current.care.lifetime,current.progress.state.hp)==(98,5944,7)
        assert inv.immutable_snapshot()==before
        _,raw=probe(0xf89ba0,0xf5df70,0xf5f1f0,payload=pet_record({
            'id':pet,'template_id':current.template_id,'name':'','care':current.care,'progress':current.progress}))
        assert struct.unpack_from('<i',raw,0x90)[0]==98 and struct.unpack_from('<i',raw,0xb0)[0]==5944
        assert struct.unpack_from('<i',raw,0x40)[0]==7
        for bad in (replace(death,death_count=0),replace(capture(pet,'battle-care:bad-template'),template_id=500002),
                    replace(capture(pet,'battle-care:bad-care'),expected_care_version=0),
                    replace(capture(pet,'battle-care:bad-growth'),expected_growth_version=0),
                    replace(capture(pet,'battle-care:bad-count'),expected_counter_version=0)):
            refused(lambda:settle(bad))
            assert inv.immutable_snapshot()==before
        refused(lambda:replace(death,expected_care_version=True))
        refused(lambda:replace(death,death_count=True))
        refused(lambda:replace(death,participated=False))
        refused(lambda:replace(death,mode='pk'))
        # Each concrete persistence stage aborts the whole role transaction;
        # retrying the same frozen outcome then commits exactly once.
        for table,action in (('inventory_pet_care','UPDATE'),('inventory_pet_care_receipts','INSERT'),
                             ('inventory_pet_battle_care','UPDATE'),('inventory_pet_battle_care_receipts','INSERT')):
            event=capture(pet,f'battle-care:abort:{table}');before=inv.immutable_snapshot()
            with closing(store.connect()) as db,db:
                db.executescript(f"CREATE TRIGGER fail_battle_care BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT,'battle care failed'); END")
            refused(lambda:settle(event),(sqlite3.IntegrityError,))
            assert inv.immutable_snapshot()==before
            with closing(store.connect()) as db,db:db.execute('DROP TRIGGER fail_battle_care')
            done=settle(event);after=inv.immutable_snapshot()
            assert done.care_after.lifetime==before.pets[0].care.lifetime-1
            assert settle(event).replayed and inv.immutable_snapshot()==after
        event=capture(pet,'battle-care:outer');before=inv.immutable_snapshot()
        try:
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE');inv.settle_pet_battle_care(db,event,inv.epoch)
                raise RuntimeError('later resource/reward failed')
        except RuntimeError:pass
        assert inv.immutable_snapshot()==before
        assert not settle(event).replayed
        # Unknown old modulo is never fabricated; an explicit complete import
        # restores the gate and cannot be rerolled later.
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            legacy=db.execute('INSERT INTO inventory_pets(role_id,template_id,name) VALUES(?,?,?)',
                              (role['id'],500001,'旧计数未知')).lastrowid
            inv.initialize_pet_growth(db,legacy);inv.initialize_pet_care(db,legacy,1,100,6000)
            refused(lambda:inv.pet_battle_care_counter(db,legacy))
            unknown=BattleCareEvent('battle-care:unknown-counter',legacy,500001,0,0,0)
            refused(lambda:inv.settle_pet_battle_care(db,unknown,inv.epoch))
            inv.initialize_pet_battle_care_counter(db,legacy,2)
            refused(lambda:inv.initialize_pet_battle_care_counter(db,legacy,0))
        old_event=capture(legacy,'battle-care:legacy')
        assert settle(old_event).counter_after.mod3==2  # level0 exemption keeps the imported remainder.
        double=capture(pet,'battle-care:two-deaths',death_count=2)
        result=settle(double)
        assert result.care_before.lifetime-result.care_after.lifetime==100
        assert result.care_before.loyalty-result.care_after.loyalty==40
        assert result.counter_after==result.counter_before
        # The new path accepts an existing transaction without any nested
        # connection or hot-path policy read.
        hot=capture(pet,'battle-care:no-hot-io')
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            with (patch.object(store,'connect',side_effect=AssertionError('nested connection')),
                  patch.object(Path,'read_text',side_effect=AssertionError('hot-path file read'))):
                assert not inv.settle_pet_battle_care(db,hot,inv.epoch).replayed
        # Admission at49, dead HP, foreign ID, or an obsolete lease refuses.
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            low=db.execute('INSERT INTO inventory_pets(role_id,template_id,name) VALUES(?,?,?)',
                           (role['id'],500001,'寿命49')).lastrowid
            inv.initialize_pet_growth(db,low);inv.initialize_pet_care(db,low,1,100,49)
            inv.initialize_pet_battle_care_counter(db,low,0)
        before=inv.immutable_snapshot()
        refused(lambda:settle(capture(low,'battle-care:life49-refuse')))
        assert inv.immutable_snapshot()==before
        foreign_role=store.create_role(1111,'其他养护',12,1010101)
        other=Inventory(store,1111,foreign_role['id'],config,
                        **known_cash_context(store,1111,foreign_role['id']))
        foreign_pet=other.grant_pet(500001)
        refused(lambda:settle(BattleCareEvent('battle-care:foreign',foreign_pet,500001,0,0,0)))
        assert inv.immutable_snapshot()==before
        inv.free_pet(legacy)
        before=inv.immutable_snapshot()
        with closing(store.connect()) as db,db:
            db.execute('BEGIN');db.set_authorizer(authorizer)
            assert inv.settle_pet_battle_care(db,old_event,inv.epoch).replayed
            assert inv.read_pet_state(db,legacy) is None
        refused(lambda:settle(replace(old_event,settlement_id='battle-care:released-fresh')))
        assert inv.immutable_snapshot()==before
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');p=inv.pet_progress(db,young)
            inv.change_pet_growth(db,young,'battle-care:dead-admission',p.state.version,'resources',(0,0))
        before=inv.immutable_snapshot()
        refused(lambda:settle(capture(young,'battle-care:dead-refuse')))
        assert inv.immutable_snapshot()==before
        final_event=capture(pet,'battle-care:opaque');token='战斗养护:0009';old_epoch=inv.epoch
        store.inventory_config=config
        with closing(store.connect()) as db,db:
            db.execute('UPDATE role_leases SET epoch=? WHERE role_id=?',(token,role['id']))
        active=Inventory(store.leased(1111,role['id'],token),1111,role['id'],config,
                         epoch=token,currency_rules=inv.currency_rules)
        refused(lambda:settle(final_event))
        assert not settle(final_event,active).replayed
        assert settle(final_event,active).replayed
        before=active.immutable_snapshot()
        assert Inventory(AccountStore(store.path),1111,role['id'],config).immutable_snapshot()==before
    report={'passed':['three level31 ordinary survived battles spend3 life/1 loyalty; persistent modulo wraps',
        'death spends50 not51 and20 loyalty; preserves prior mod2 then next survivor spends1 loyalty',
        'level0/30 preserve loyalty and counters including death; lifetime remains charged',
        'sparring/nonparticipation/god pets no-op with durable IDs and no inventory revision churn',
        'late paid event is SQL read-only and preserves later98 loyalty/5944 life/7HP; native decoder sees current',
        'four actual persistence faults and outer resource/reward failure roll back care/meter/receipts; same event retries once',
        'two recorded deaths cost100 life/40 loyalty without ordinary count; no hot files or nested connection',
        'actual lifetime49, dead HP and foreign pet admission refuse without mutation',
        'released recipient historical acknowledgement remains read-only; fresh released settlement refuses without resurrection',
        'unknown old counter needs authoritative import and cannot reroll; dead admission/version/template/intent/bool/mode reject',
        'fenced opaque replacement succeeds; old lease rejects; reopen preserves'],
        'native_gui_verified':False,'actual_pet_battle_integrated':False,'live_server_changed':False,
        'source_status':'original amounts/level30; official death/sparring; modulo preservation designed'}
    write_json(OUT/'evidence/pet-battle-settlement-verification.json',report)
    print('PASS',', '.join(report['passed']))


if __name__=='__main__':main()
