"""Super-return transactions through the owned inventory Interface, real SQLite."""
from tempfile import TemporaryDirectory
from pathlib import Path
from contextlib import closing
from accounts import AccountStore
from inventory import Inventory
from inventory_test_support import known_cash_context
from inventory import pet_record,USE_ITEM,REFRESH_PET
from pet_protocol import SUPER_RETURN_QUERY,SUPER_RETURN_SUBMIT,SUPER_RETURN_CLEAR,SUPER_RETURN_PREVIEW
from native_gameplay_probe import probe
from inspect_client import OUT,write_json
import struct
import sqlite3
from unittest.mock import patch


def refused(action,errors=(ValueError,)):
    try:action()
    except errors:return
    raise AssertionError('Invalid or stale return accepted')


def main():
    with TemporaryDirectory() as tmp:
        store=AccountStore(Path(tmp)/'return.sqlite3')
        role=store.create_role(1111,'超级还童',12,1010101)
        config=Inventory.prepare(store)
        inv=Inventory(store,1111,role['id'],config,**known_cash_context(store,1111,role['id']))
        pet=inv.grant_pet(500001);inv.grant_item(31576,3)
        before=inv.immutable_snapshot()
        key=next(i.id for i in before.items if i.template_id==31576)
        refused(lambda:inv.receive(USE_ITEM,struct.pack('>iiQ',key,1,pet)))
        assert inv.immutable_snapshot()==before
        def preview():
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                return inv.super_return(db,pet,inv.epoch,'preview:A','preview',item_key=key,draws=(0,)*7)
        receipt=preview();after=inv.immutable_snapshot()
        assert after.pets==before.pets,'预览覆盖了当前宠物'
        assert next(i.quantity for i in after.items if i.id==key)==2
        assert preview().replayed and inv.immutable_snapshot()==after
        with closing(store.connect()) as db,db:
            db.execute('BEGIN')
            candidate=inv.super_return_candidate(db,pet,inv.epoch)
        assert candidate==receipt.candidate
        assert candidate.profile.aptitudes==(1040,1130,840,585,1025)
        assert candidate.profile.growth_raw==986 and candidate.insight==0
        def command(request,action,expected):
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                return inv.super_return(db,pet,inv.epoch,request,action,expected_candidate=expected)
        saved=command('save:A','save','preview:A')
        saved_pet=inv.immutable_snapshot().pets[0]
        assert saved_pet.progress.profile==candidate.profile
        assert saved_pet.progress.state.level==before.pets[0].progress.state.level
        assert saved_pet.skills==before.pets[0].skills and saved_pet.care==before.pets[0].care
        assert saved_pet.traits.insight==0 and saved_pet.traits.origin==2 and saved_pet.cake.count==0
        assert command('save:A','save','preview:A').replayed
        assert inv.immutable_snapshot().pets[0]==saved_pet
        # A paid preview is historical acknowledgement, never pending restoration.
        assert preview().replayed
        with closing(store.connect()) as db,db:
            db.execute('BEGIN')
            assert inv.super_return_candidate(db,pet,inv.epoch) is None
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            b=inv.super_return(db,pet,inv.epoch,'preview:B','preview',item_key=key,draws=(9999,)*7)
        assert b.candidate.profile.aptitudes==(1220,1340,1080,730,1220)
        assert b.candidate.profile.growth_raw==1026 and b.candidate.insight==100
        command('clear:B','clear','preview:B')
        assert inv.immutable_snapshot().pets[0]==saved_pet
        assert command('clear:B','clear','preview:B').replayed
        # Old paid A/save/clear cannot modify a newer preview C, even after reopen.
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            c=inv.super_return(db,pet,inv.epoch,'preview:C','preview',item_key=key,draws=(5000,)*7)
        snapshot=inv.immutable_snapshot()
        assert preview().replayed and command('save:A','save','preview:A').replayed
        assert command('clear:B','clear','preview:B').replayed
        assert inv.immutable_snapshot()==snapshot
        with closing(store.connect()) as db,db:
            db.execute('BEGIN')
            assert inv.super_return_candidate(db,pet,inv.epoch)==c.candidate
        refused(lambda:command('late:save:B','save','preview:B'))
        assert inv.immutable_snapshot()==snapshot
        # Current injuries/XP/allocation are preserved, never stale preview resources.
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            inv.change_pet_growth(db,pet,'return:XP',saved_pet.progress.state.version,'experience',1000)
            current=inv.read_pet_state(db,pet)
            inv.change_pet_growth(db,pet,'return:points',current.progress.state.version,'allocate',(1,0,0,0,0))
            current=inv.read_pet_state(db,pet)
            inv.change_pet_growth(db,pet,'return:wound',current.progress.state.version,'resources',(0,7))
        before_save=inv.immutable_snapshot().pets[0]
        command('save:C','save','preview:C')
        after_save=inv.immutable_snapshot().pets[0]
        assert after_save.progress.profile==c.candidate.profile
        assert (after_save.progress.state.level,after_save.progress.state.experience,after_save.progress.state.allocated)==(
            before_save.progress.state.level,before_save.progress.state.experience,before_save.progress.state.allocated)
        assert (after_save.progress.state.hp,after_save.progress.state.mp)==(0,7)
        assert (after_save.skills,after_save.flags,after_save.skill_progress,after_save.skill_expiry,after_save.care)==(
            before_save.skills,before_save.flags,before_save.skill_progress,before_save.skill_expiry,before_save.care)
        # Explicit old ledger import keeps BASE authoritative; no double application.
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM inventory_pet_cakes WHERE pet_id=?',(pet,)) # fixture: legacy ledger absent
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            assert inv.read_pet_state(db,pet).cake is None
            inv.initialize_pet_cakes(db,pet,20,(20,10,3,0,7))
        history=inv.immutable_snapshot().pets[0]
        assert history.progress.profile==after_save.progress.profile
        record=pet_record(vars(history))
        _,raw=probe(0xf89ba0,0xf5df70,0xf5f1f0,payload=record)
        assert raw[0x111]==20
        from research_pet_cake import native_count
        assert native_count(record)=={'attribute':1540,'count':20,'twenty_rejected':True}
        inv.grant_item(31576,6)
        key=next(i.id for i in inv.immutable_snapshot().items if i.template_id==31576)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            d=inv.super_return(db,pet,inv.epoch,'preview:D','preview',item_key=key,draws=(0,)*7)
        command('save:D','save','preview:D')
        reset=inv.immutable_snapshot().pets[0]
        assert reset.cake.count==0 and reset.cake.added_aptitudes==(0,)*5 and reset.cake.version==history.cake.version+1
        assert reset.progress.profile==d.candidate.profile
        _,raw=probe(0xf89ba0,0xf5df70,0xf5f1f0,payload=pet_record(vars(reset)))
        assert raw[0x111]==0
        # Original adapters produce current candidate; a late paid preview cannot send old A.
        body=struct.pack('>iiQ',key,1,pet)
        response=inv.receive_super_return(USE_ITEM,body,inv.epoch,'native:E',draws=(9999,)*7)
        preview_body=next(b for t,b in response if t==SUPER_RETURN_PREVIEW)
        assert struct.unpack('>9i',preview_body)[1:6]==(1220,1340,1080,730,1220)
        _,native_preview=probe(0xdc15a0,0xe54300,0xdc15e0,payload=preview_body,factory=True)
        assert struct.unpack_from('<9i',native_preview,8)==struct.unpack('>9i',preview_body)
        native=inv.receive_super_return(SUPER_RETURN_QUERY,struct.pack('>i',pet),inv.epoch)
        assert native==[(SUPER_RETURN_PREVIEW,preview_body)]
        late=inv.receive_super_return(USE_ITEM,body,inv.epoch,'native:E')
        assert next(b for t,b in late if t==SUPER_RETURN_PREVIEW)==preview_body
        inv.receive_super_return(SUPER_RETURN_SUBMIT,struct.pack('>i',pet),inv.epoch,'native:save:E',expected_candidate='native:E')
        assert inv.receive_super_return(SUPER_RETURN_QUERY,struct.pack('>i',pet),inv.epoch)==[]
        late=inv.receive_super_return(USE_ITEM,body,inv.epoch,'native:E')
        assert all(t!=SUPER_RETURN_PREVIEW for t,b in late)
        # Late encoding and late caller source failures roll payment/candidate/receipts back.
        baseline=inv.immutable_snapshot()
        with patch('inventory.pet_record',side_effect=RuntimeError('late encoding')):
            refused(lambda:inv.receive_super_return(USE_ITEM,body,inv.epoch,'native:rollback',draws=(0,)*7),(RuntimeError,))
        assert inv.immutable_snapshot()==baseline
        def fail_source(db,inventory,snapshot,*,replayed):raise RuntimeError('source failure')
        refused(lambda:inv.receive_super_return(USE_ITEM,body,inv.epoch,'native:rollback',draws=(0,)*7,precommit=fail_source),(RuntimeError,))
        assert inv.immutable_snapshot()==baseline
        response=inv.receive_super_return(USE_ITEM,body,inv.epoch,'native:rollback',draws=(0,)*7)
        # Paid path is SQL read-only and cannot load files or open nested connections.
        with closing(store.connect()) as db,db:
            db.execute('BEGIN')
            def readonly(action,*args):
                return sqlite3.SQLITE_DENY if action in (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE) else sqlite3.SQLITE_OK
            db.set_authorizer(readonly)
            with patch.object(Path,'read_text',side_effect=AssertionError('hot file read')),patch.object(store,'connect',side_effect=AssertionError('nested connection')):
                assert inv.super_return(db,pet,inv.epoch,'native:rollback','preview',item_key=key).replayed
        before=inv.immutable_snapshot()
        assert Inventory(AccountStore(store.path),1111,role['id'],config).immutable_snapshot()==before
        # Another pet owns an independent pending preview.
        other=inv.grant_pet(500001)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM inventory_pet_cakes WHERE pet_id=?',(other,))
            inv.initialize_pet_cakes(db,other,1,(1,0,0,0,0))
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            inv.super_return(db,other,inv.epoch,'preview:other','preview',item_key=key,draws=(0,)*7)
            assert inv.super_return_candidate(db,pet,inv.epoch).candidate_id=='native:rollback'
            assert inv.super_return_candidate(db,other,inv.epoch).candidate_id=='preview:other'
        # Guard source mutation and obsolete candidate; pending is retained for explicit clear.
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            from pet_growth_store import damage_base_aptitudes
            p=inv.read_pet_state(db,pet)
            damage_base_aptitudes(db,inv.account_id,inv.role_id,pet,inv.growth_rules,inv.blood_rules,p.care.grade,p.progress,1)
        before=inv.immutable_snapshot()
        refused(lambda:command('save:stale','save','native:rollback'))
        assert inv.immutable_snapshot()==before
        command('clear:stale','clear','native:rollback')
        # Every real write stage can fail without partial saved state or lost candidate.
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            pending=inv.super_return_candidate(db,other,inv.epoch)
        for table,operation in (('inventory_pet_growth','UPDATE'),('inventory_pet_traits','UPDATE'),('inventory_pet_cakes','UPDATE'),
                ('inventory_pet_return_candidates','DELETE'),('inventory_pet_return_receipts','INSERT')):
            with closing(store.connect()) as db,db:
                db.execute(f"CREATE TRIGGER return_fail BEFORE {operation} ON {table} BEGIN SELECT RAISE(ABORT,'save failure'); END")
            baseline=inv.immutable_snapshot()
            def fail_save():
                with closing(store.connect()) as db,db:
                    db.execute('BEGIN IMMEDIATE')
                    inv.super_return(db,other,inv.epoch,'save:other','save',expected_candidate='preview:other')
            refused(fail_save,(sqlite3.IntegrityError,))
            assert inv.immutable_snapshot()==baseline
            with closing(store.connect()) as db,db:
                db.execute('DROP TRIGGER return_fail')
                db.execute('BEGIN')
                assert inv.super_return_candidate(db,other,inv.epoch)==pending
        fail_save()
        # Unknown old cake history and wild identity never become eligible by guess.
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM inventory_pet_cakes WHERE pet_id=?',(other,))
        def invalid_preview(**kwargs):
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                return inv.super_return(db,other,inv.epoch,'invalid:new','preview',item_key=key,draws=kwargs.get('draws',(0,)*7))
        baseline=inv.immutable_snapshot();refused(invalid_preview);assert inv.immutable_snapshot()==baseline
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            inv.initialize_pet_cakes(db,other,0,(0,)*5)
            db.execute('DELETE FROM inventory_pet_traits WHERE pet_id=?',(other,))
            inv.initialize_pet_traits(db,other,1,73)
        baseline=inv.immutable_snapshot();refused(invalid_preview);assert inv.immutable_snapshot()==baseline
        for bad_draws in ([],(0,)*6,(True,)*7,(-1,)*7,(10000,)*7):
            refused(lambda:invalid_preview(draws=bad_draws))
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            refused(lambda:inv.super_return(db,pet,inv.epoch,'native:rollback','preview',item_key=key,draws=(1,)*7))
        # A clear captured with no pending candidate is a durable no-op; cannot clear later work.
        inv.receive_super_return(SUPER_RETURN_CLEAR,struct.pack('>i',pet),inv.epoch,'clear:absent')
        baseline=inv.immutable_snapshot()
        inv.receive_super_return(USE_ITEM,body,inv.epoch,'native:after-empty-clear',draws=(0,)*7)
        inv.receive_super_return(SUPER_RETURN_CLEAR,struct.pack('>i',pet),inv.epoch,'clear:absent')
        with closing(store.connect()) as db,db:
            db.execute('BEGIN')
            assert inv.super_return_candidate(db,pet,inv.epoch).candidate_id=='native:after-empty-clear'
        # Current opaque leases work; both old queries and historical paid writes are fenced.
        old_epoch=inv.epoch;token='超级还童:00021'
        with closing(store.connect()) as db,db:db.execute('UPDATE role_leases SET epoch=? WHERE role_id=?',(token,role['id']))
        active=Inventory(store,1111,role['id'],config,epoch=token,currency_rules=inv.currency_rules)
        assert active.receive_super_return(SUPER_RETURN_QUERY,struct.pack('>i',pet),token)
        refused(lambda:inv.receive_super_return(SUPER_RETURN_QUERY,struct.pack('>i',pet),old_epoch))
        refused(lambda:inv.receive_super_return(USE_ITEM,body,old_epoch,'native:rollback'))
        active.receive_super_return(SUPER_RETURN_CLEAR,struct.pack('>i',pet),token,'opaque:clear',
            expected_candidate='native:after-empty-clear')
        opaque=active.immutable_snapshot()
        active.receive_super_return(SUPER_RETURN_CLEAR,struct.pack('>i',pet),token,'opaque:clear',
            expected_candidate='native:after-empty-clear')
        assert active.immutable_snapshot()==opaque
    report={'passed':['preview debit once/current pet unchanged/reopen/read-only paid/no hot IO',
        'all original min/max aptitude and growth endpoints; designed insight endpoints',
        'save/clear/replaced candidate and late paid preview/save/clear never resurrect historical state',
        'save retains current XP/level/allocation/skills/care/metadata, death0 and absolute resources',
        'explicit known cake20 import does not double-buff BASE; save resets count/history/native bean111',
        'native request adapters query current pending; late encoding and caller precommit failure roll back',
        'per-pet independent candidates, BASE source conflict rejected, five real write-stage save rollback',
        'old unknown cake/wild identity/draw guards; empty clear cannot clear later work; current opaque lease and stale paid/query fencing'],
        'shared_route_integrated':False,'live_server_changed':False,'native_gui_verified':False}
    write_json(OUT/'evidence/pet-super-return-verification.json',report)
    print('PASS',', '.join(report['passed']))


if __name__=='__main__':main()
