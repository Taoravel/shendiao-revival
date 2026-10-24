"""Stone use/clear through owned Inventory commands and original native consumers."""
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
import struct
import sqlite3
from unittest.mock import patch
from accounts import AccountStore
from inventory import Inventory,pet_record
from inventory_test_support import known_cash_context
from research_pet_stones_native import native_pet_stones,native_stone_attributes
from pet_protocol import SUPER_RETURN_SUBMIT
from research_pet_cake_protocol import native_notice
from inspect_client import OUT,write_json


def refused(action,errors=(ValueError,)):
    try:action()
    except errors:return
    raise AssertionError('Invalid stone command or injected fault committed')


def main():
    with TemporaryDirectory() as tmp:
        store=AccountStore(Path(tmp)/'stones.sqlite3')
        role=store.create_role(1111,'灵石事务',12,1010101)
        with closing(store.connect()) as db,db:db.execute('UPDATE roles SET level=20 WHERE id=?',(role['id'],))
        config=Inventory.prepare(store)
        inv=Inventory(store,1111,role['id'],config,**known_cash_context(store,1111,role['id']))
        pet=inv.grant_pet(500001)
        def current():return inv.immutable_snapshot().pets[0]
        before=current()
        assert before.progress.stones.count==0
        inv.fight_pet(pet)
        inv.grant_item(70052)
        key=next(i.id for i in inv.immutable_snapshot().items if i.template_id==70052)
        body=struct.pack('>iiQ',key,1,pet)
        messages=inv.receive_pet_consumable(body,inv.epoch,'stones:first',stone_draws=(0,)*50)
        assert native_notice(next(b for t,b in messages if t==0xc1775))==(150454,0,('50','0','0','0','0'))
        after=current()
        assert after.progress.stones.count==1
        assert after.progress.stones.added_aptitudes==(50,0,0,0,0)
        assert after.progress.profile.aptitudes==before.progress.profile.aptitudes
        assert after.progress.profile.growth_raw==1011
        assert after.progress.effective_profile.aptitudes==(1180,1235,960,657,1122)
        assert (after.progress.state.hp,after.progress.state.mp)==(before.progress.state.hp,before.progress.state.mp)
        expected=((1930,1),(1940,50),(1950,0),(1960,0),(1970,0),(1980,0))
        assert native_pet_stones(pet_record(vars(after)))==expected
        assert native_stone_attributes(next(b for t,b in messages if t==0xc32c9))==expected
        paid=inv.receive_pet_consumable(body,inv.epoch,'stones:first')
        assert current()==after and all(t!=0xc1775 for t,b in paid)
        inv.grant_item(70053)
        clear=next(i.id for i in inv.immutable_snapshot().items if i.template_id==70053)
        messages=inv.receive_pet_consumable(struct.pack('>iiQ',clear,1,pet),inv.epoch,'stones:clear')
        clean=current()
        assert clean.progress.stones.count==0 and clean.progress.stones.added_aptitudes==(0,)*5
        assert clean.progress.profile==before.progress.profile
        assert clean.progress.effective_profile==before.progress.effective_profile
        assert native_stone_attributes(next(b for t,b in messages if t==0xc32c9))==tuple((key,0) for key,_ in expected)
        assert current().fighting==1
        inv.fight_pet()
        # Cake operates on BASE without removing or multiplying a stone's extras.
        def item(template):return next(i.id for i in inv.immutable_snapshot().items if i.template_id==template)
        def eat(template,request,**kwargs):
            return inv.receive_pet_consumable(struct.pack('>iiQ',item(template),1,pet),inv.epoch,request,**kwargs)
        inv.grant_item(70052,2);eat(70052,'stones:again',stone_draws=(0,)*50)
        inv.grant_item(31268);eat(31268,'stones:cake')
        baked=current()
        assert baked.progress.profile.aptitudes==(1137,1235,960,657,1122)
        assert baked.progress.effective_profile.aptitudes==(1187,1235,960,657,1122)
        assert baked.cake.added_aptitudes==(7,0,0,0,0) and baked.progress.stones.count==1
        inv.grant_item(70053);eat(70053,'stones:clear-after-cake')
        assert current().progress.profile.aptitudes==(1137,1235,960,657,1122)
        assert current().progress.effective_profile.aptitudes==(1137,1235,960,657,1122)
        # Newly rolled natural growth retains the independent stone source once.
        eat(70052,'stones:before-return',stone_draws=(9999,)*50)
        inv.grant_item(31002)
        inv.receive_ordinary_return(struct.pack('>iiQ',item(31002),1,pet),inv.epoch,'stones:ordinary',(0,)*15)
        reborn=current()
        assert reborn.progress.profile.growth_raw==991
        assert reborn.progress.profile.aptitudes==(1040,1130,840,585,1025)
        assert reborn.progress.effective_profile.aptitudes==(1040,1130,840,585,1075)
        assert reborn.progress.stones.added_aptitudes==(0,0,0,0,50) and reborn.cake.count==0
        inv.grant_item(31576,2)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            preview=inv.super_return(db,pet,inv.epoch,'stones:super','preview',item_key=item(31576),draws=(9999,)*7).candidate
        assert preview.profile.growth_raw==1031 and preview.display_aptitudes==(1220,1340,1080,730,1270)
        inv.receive_super_return(SUPER_RETURN_SUBMIT,struct.pack('>i',pet),inv.epoch,'stones:save',expected_candidate='stones:super')
        assert current().progress.profile.growth_raw==1031 and current().progress.stones.count==1
        # Boundary draws allocate exactly ten to each dimension; blood acts on
        # BASE first, leaving stone extras independent of the existing ratio.
        inv.grant_item(70052,10)
        inv.grant_item(36117,3)
        for number in range(2):eat(36117,'stones:blood:'+str(number))
        blooded=current()
        assert blooded.progress.blood.level==2
        assert blooded.progress.effective_profile.aptitudes==(1226,1346,1085,733,1276)
        boundary=(0,1999,2000,3999,4000,5999,6000,7999,8000,9999)*5
        eat(70052,'stones:balanced',stone_draws=boundary)
        assert current().progress.stones.added_aptitudes==(10,10,10,10,60)
        assert current().progress.effective_profile.aptitudes==(1236,1356,1095,743,1286)
        balanced_stones=current().progress.stones
        # Later poison/cake changes belong to BASE; clearing must retain them.
        inv.grant_item(32004,quality=10)
        eat(32004,'stones:poison',draw=0)
        poisoned=current()
        assert poisoned.progress.profile.aptitudes==(1219,1339,1079,729,1219)
        assert poisoned.progress.stones==balanced_stones
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');p=inv.read_pet_state(db,pet)
            inv.change_pet_growth(db,pet,'stones:level20',p.progress.state.version,'experience',sum(inv.growth_rules.thresholds[i] for i in range(20)))
        inv.grant_item(31227,2)
        inv.receive_pet_evolution(struct.pack('>i',pet),inv.epoch,'stones:evolve')
        evolved=current()
        assert evolved.progress.profile.growth_raw==1041 and evolved.progress.stones.count==2
        inv.grant_item(70053,10);eat(70053,'stones:clear-later')
        cleaned=current()
        assert cleaned.progress.profile.growth_raw==1031
        assert cleaned.progress.profile.aptitudes==poisoned.progress.profile.aptitudes
        assert cleaned.progress.effective_profile.aptitudes==(1225,1345,1084,732,1225)
        assert cleaned.evolution==evolved.evolution and cleaned.progress.blood==evolved.progress.blood
        # Original cap5 and empty clear refusal debit neither assets nor IDs.
        for number in range(5):eat(70052,'stones:cap:'+str(number),stone_draws=(0,)*50)
        snapshot=inv.immutable_snapshot()
        def no_precommit(*a,**kw):raise AssertionError('No-effect stone reached mutation precommit')
        response=eat(70052,'stones:over',stone_draws=(0,)*50,precommit=no_precommit)
        assert native_notice(response[0][1])==(150453,0,()) and inv.immutable_snapshot()==snapshot
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');p=inv.read_pet_state(db,pet)
            inv.change_pet_growth(db,pet,'stones:full-resources',p.progress.state.version,'resources',
                (p.progress.attributes.max_hp,p.progress.attributes.max_mp))
        before_clear=current()
        eat(70053,'stones:clear-five');snapshot=inv.immutable_snapshot()
        assert current().progress.state.hp==current().progress.attributes.max_hp<=before_clear.progress.state.hp
        assert current().progress.state.mp==current().progress.attributes.max_mp<=before_clear.progress.state.mp
        response=eat(70053,'stones:empty',precommit=no_precommit)
        assert native_notice(response[0][1])==(150483,0,()) and inv.immutable_snapshot()==snapshot
        # A super candidate cannot survive an add/clear cycle that restores the
        # same physical profile: the independent source version changed.
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            inv.super_return(db,pet,inv.epoch,'stones:old-candidate','preview',item_key=item(31576),draws=(0,)*7)
        eat(70052,'stones:cycle-add',stone_draws=(0,)*50);eat(70053,'stones:cycle-clear')
        snapshot=inv.immutable_snapshot()
        refused(lambda:inv.receive_super_return(SUPER_RETURN_SUBMIT,struct.pack('>i',pet),inv.epoch,
            'stones:old-save',expected_candidate='stones:old-candidate'))
        assert inv.immutable_snapshot()==snapshot
        # Dead stays dead, and add/clear preserves absolute depleted MP.
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');p=inv.read_pet_state(db,pet)
            inv.change_pet_growth(db,pet,'stones:death',p.progress.state.version,'resources',(0,2))
        eat(70052,'stones:dead-add',stone_draws=(0,)*50);eat(70053,'stones:dead-clear')
        assert (current().progress.state.hp,current().progress.state.mp)==(0,2)
        # Every source/debit/receipt stage and late representation can fail;
        # retrying the same failed command then commits only once.
        inv.grant_item(70052,10)
        for table,operation in (('inventory_pet_growth','UPDATE'),('inventory_pet_stones','UPDATE'),
                ('inventory_items','UPDATE'),('inventory_pet_stone_receipts','INSERT'),('inventory_pet_consumable_commands','INSERT')):
            with closing(store.connect()) as db,db:
                db.execute(f"CREATE TRIGGER stone_fault BEFORE {operation} ON {table} BEGIN SELECT RAISE(ABORT,'stone persistence failed'); END")
            snapshot=inv.immutable_snapshot()
            refused(lambda:eat(70052,'stones:fault',stone_draws=boundary),(sqlite3.IntegrityError,))
            assert inv.immutable_snapshot()==snapshot
            with closing(store.connect()) as db,db:db.execute('DROP TRIGGER stone_fault')
        for target in ('inventory.pet_record','inventory.stone_attributes_message','inventory.stone_notice'):
            with patch(target,side_effect=RuntimeError('late stone representation')):
                refused(lambda:eat(70052,'stones:fault',stone_draws=boundary),(RuntimeError,))
            assert inv.immutable_snapshot()==snapshot
        def source_failed(*a,**kw):raise RuntimeError('source/common transaction failure')
        refused(lambda:eat(70052,'stones:fault',stone_draws=boundary,precommit=source_failed),(RuntimeError,))
        assert inv.immutable_snapshot()==snapshot
        eat(70052,'stones:fault',stone_draws=boundary);paid_state=inv.immutable_snapshot()
        refused(lambda:eat(70052,'stones:fault',stone_draws=(0,)*50))
        assert inv.immutable_snapshot()==paid_state
        paid=inv.receive_pet_consumable(body,inv.epoch,'stones:first')
        assert native_stone_attributes(next(b for t,b in paid if t==0xc32c9))==((1930,1),(1940,10),(1950,10),(1960,10),(1970,10),(1980,10))
        assert current().progress.state.hp==0 and inv.immutable_snapshot()==paid_state
        for draws in ([0]*50,(0,)*49,(0,)*49+(10000,),(True,)*50):
            refused(lambda:eat(70052,'stones:invalid-draws',stone_draws=draws))
            assert inv.immutable_snapshot()==paid_state
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            refused(lambda:inv.use_pet_stone(db,item(70052),pet,False,'stones:bad-epoch',boundary))
            refused(lambda:inv.use_pet_stone(db,item(70052),pet,inv.epoch,'stones:bad-version',boundary,0))
        assert inv.immutable_snapshot()==paid_state
        # Historical add replay does not require its deleted last item or a
        # live target, never rerolls, and is strictly SQL-readonly.
        with closing(store.connect()) as db,db:
            db.execute('BEGIN');db.set_authorizer(lambda a,*args:sqlite3.SQLITE_DENY if a in
                (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE) else sqlite3.SQLITE_OK)
            with patch.object(Path,'read_text',side_effect=AssertionError('hot stone configuration')):
                receipt=inv.use_pet_stone(db,key,pet,inv.epoch,'stones:first')
                assert receipt.replayed and receipt.after.stones.count==1
        # Unknown legacy source is never initialized on load or guessed zero.
        with closing(store.connect()) as db,db:db.execute('DELETE FROM inventory_pet_stones WHERE pet_id=?',(pet,))
        assert current().progress.stones is None
        snapshot=inv.immutable_snapshot()
        refused(lambda:eat(70052,'stones:unknown',stone_draws=(0,)*50))
        refused(lambda:eat(70053,'stones:unknown-clear'))
        inv.grant_item(31002)
        snapshot=inv.immutable_snapshot()
        refused(lambda:inv.receive_ordinary_return(struct.pack('>iiQ',item(31002),1,pet),inv.epoch,'stones:unknown-return',(0,)*15))
        assert inv.immutable_snapshot()==snapshot
        inv.free_pet(pet);released=inv.immutable_snapshot()
        response=inv.receive_pet_consumable(body,inv.epoch,'stones:first')
        assert (0xc07dd,struct.pack('>ii',1,pet)) in response and inv.immutable_snapshot()==released
        imported=inv.grant_pet(500001)
        with closing(store.connect()) as db,db:db.execute('DELETE FROM inventory_pet_stones WHERE pet_id=?',(imported,))
        assert current().progress.stones is None
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            inv.initialize_pet_stones(db,imported,0,(0,)*5)
            refused(lambda:inv.initialize_pet_stones(db,imported,0,(0,)*5))
        known=inv.immutable_snapshot()
        reopened=Inventory(AccountStore(store.path),1111,role['id'],config,epoch=inv.epoch,currency_rules=inv.currency_rules)
        assert reopened.immutable_snapshot()==known and known.pets[0].progress.stones.count==0
    write_json(OUT/'evidence/pet-stones-verification.json',{'passed':[
        'original initial Pet map and distinct absolute attr refresh including zero clearing; stable captured add and deterministic clear consume one item atomically',
        'BASE/cake/poison/blood/evolution and ordinary/super replacement retain independent stone sources; clear only removes own contribution; source version prevents stale super save after add/clear',
        'original5 cap and empty no-debit notices;50 boundary draws distribute10 per dimension; death0/depleted MP preserved',
        'five real persistence faults, late basic/attribute/notice failures and caller source failure roll back every asset; same failed ID retries once; changed captured draws reject',
        'historical receipt SQL-readonly/no hot config after item deletion; unknown old state staysNone; released historical target never resurrects'],
        'live_server_changed':False,'native_gui_verified':False})
    print('PASS atomic owned stone add/clear, source composition, native initial/absolute refresh and paid current replay')


if __name__=='__main__':main()
