"""Ordinary evolution through the owned Inventory transaction interface."""
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from accounts import AccountStore
from inventory import Inventory
from inventory_test_support import known_cash_context
import struct
from research_pet_evolution import native_stage
from inventory import pet_record
from pet_protocol import SUPER_RETURN_SUBMIT
from unittest.mock import patch
import sqlite3
from inspect_client import OUT,write_json


def refused(fn,errors=(ValueError,)):
    try:fn()
    except errors:return
    raise AssertionError('Invalid evolution/fault committed')


def main():
    with TemporaryDirectory() as tmp:
        store=AccountStore(Path(tmp)/'evolution.sqlite3')
        role=store.create_role(1111,'进化事务',12,1010101)
        config=Inventory.prepare(store)
        inv=Inventory(store,1111,role['id'],config,**known_cash_context(store,1111,role['id']))
        pet=inv.grant_pet(500001);inv.grant_item(31227,2)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');p=inv.read_pet_state(db,pet)
            inv.change_pet_growth(db,pet,'evolve:known20',p.progress.state.version,'experience',sum(inv.growth_rules.thresholds[i] for i in range(20)))
        before=inv.immutable_snapshot();p=before.pets[0]
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            receipt=inv.evolve_pet(db,pet,inv.epoch,'evolve:first',p.progress.state.version)
        after=inv.immutable_snapshot();q=after.pets[0]
        assert q.evolution.stage==1 and q.progress.profile.growth_raw==1011
        assert all(i.template_id!=31227 for i in after.items)
        assert (q.progress.state.hp,q.progress.state.mp)==(p.progress.state.hp,p.progress.state.mp)
        assert (q.skills,q.cake,q.care,q.traits,q.flags)==(p.skills,p.cake,p.care,p.traits,p.flags)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            assert inv.evolve_pet(db,pet,inv.epoch,'evolve:first',p.progress.state.version).replayed
        assert inv.immutable_snapshot()==after
        assert native_stage(pet_record(vars(q)))==1
        # Original after-cap first row costs8 advanced and1 final for growth+1.
        inv.grant_item(31228,5);inv.grant_item(31228,3,binding=1);inv.grant_item(31229,1)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            receipt=inv.evolve_pet(db,pet,inv.epoch,'evolve:final1')
        q=inv.immutable_snapshot().pets[0]
        assert (q.evolution.stage,q.progress.profile.growth_raw)==(2,1012)
        assert tuple(row[2] for row in receipt.debits)==(1,0,0)
        assert native_stage(pet_record(vars(q)))==2
        # A new roll replaces the natural growth but preserves evolution+6.
        inv.grant_item(31002)
        pill=next(i.id for i in inv.immutable_snapshot().items if i.template_id==31002)
        inv.receive_ordinary_return(struct.pack('>iiQ',pill,1,pet),inv.epoch,'evolve:rebirth',(0,)*15)
        q=inv.immutable_snapshot().pets[0]
        assert (q.evolution.stage,q.progress.profile.growth_raw)==(2,992),'Ordinary rebirth dropped the retained evolution growth source'
        inv.grant_item(31576)
        super_pill=next(i.id for i in inv.immutable_snapshot().items if i.template_id==31576)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            candidate=inv.super_return(db,pet,inv.epoch,'evolve:super','preview',item_key=super_pill,draws=(0,)*7).candidate
        assert candidate.profile.growth_raw==992
        inv.receive_super_return(SUPER_RETURN_SUBMIT,struct.pack('>i',pet),inv.epoch,'evolve:save',expected_candidate='evolve:super')
        assert inv.immutable_snapshot().pets[0].progress.profile.growth_raw==992
        # Exact sparse original path:0->1->2->6, never nonexistent3/4/5.
        with closing(store.connect()) as db,db:db.execute('UPDATE roles SET level=150 WHERE id=?',(role['id'],))
        sparse=inv.grant_pet(500050);inv.grant_item(31227,48);inv.grant_item(31229,1)
        def state(key):return next(p for p in inv.immutable_snapshot().pets if p.id==key)
        def level(key,target):
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE');p=inv.read_pet_state(db,key)
                inv.change_pet_growth(db,key,'evolve:level:'+str(key),p.progress.state.version,'experience',sum(inv.growth_rules.thresholds[i] for i in range(target)))
        level(sparse,30);natural=state(sparse).progress.profile.growth_raw
        for stage in (1,2,6):
            inv.receive_pet_evolution(struct.pack('>i',sparse),inv.epoch,'evolve:sparse:'+str(stage))
            assert state(sparse).evolution.stage==stage
        assert state(sparse).progress.profile.growth_raw==natural+15
        assert native_stage(pet_record(vars(state(sparse))))==6
        # All50 post-cap original cost rows, then a no-debit ceiling refusal.
        inv.grant_item(31228,6000);inv.grant_item(31229,500)
        for number in range(2,51):
            inv.receive_pet_evolution(struct.pack('>i',pet),inv.epoch,'evolve:final:'+str(number))
        assert (state(pet).evolution.stage,state(pet).progress.profile.growth_raw)==(51,1041)
        snapshot=inv.immutable_snapshot()
        refused(lambda:inv.receive_pet_evolution(struct.pack('>i',pet),inv.epoch,'evolve:full'))
        assert inv.immutable_snapshot()==snapshot
        # A paid command remains SQL-readonly and does not require its old item.
        with closing(store.connect()) as db,db:
            db.execute('BEGIN');db.set_authorizer(lambda a,*args:sqlite3.SQLITE_DENY if a in
                (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE) else sqlite3.SQLITE_OK)
            with patch.object(Path,'read_text',side_effect=AssertionError('hot evolution config')):
                assert inv.evolve_pet(db,pet,inv.epoch,'evolve:first',p.progress.state.version).replayed
        assert inv.immutable_snapshot()==snapshot
        # Independent write failures and late representation errors undo every asset.
        fault=inv.grant_pet(500001);level(fault,20);inv.grant_item(31227,5)
        for table,operation in (('inventory_pet_growth','UPDATE'),('inventory_pet_evolution','UPDATE'),
                ('inventory_items','UPDATE'),('inventory_pet_evolution_receipts','INSERT')):
            with closing(store.connect()) as db,db:
                db.execute(f"CREATE TRIGGER evolve_fault BEFORE {operation} ON {table} BEGIN SELECT RAISE(ABORT,'evolution persistence failed'); END")
            before=inv.immutable_snapshot()
            refused(lambda:inv.receive_pet_evolution(struct.pack('>i',fault),inv.epoch,'evolve:fault'),(sqlite3.IntegrityError,))
            assert inv.immutable_snapshot()==before
            with closing(store.connect()) as db,db:db.execute('DROP TRIGGER evolve_fault')
        before=inv.immutable_snapshot()
        with patch('inventory.pet_record',side_effect=RuntimeError('late evolution encoding')):
            refused(lambda:inv.receive_pet_evolution(struct.pack('>i',fault),inv.epoch,'evolve:fault'),(RuntimeError,))
        with patch('inventory.evolution_notice',side_effect=RuntimeError('late evolution notice encoding')):
            refused(lambda:inv.receive_pet_evolution(struct.pack('>i',fault),inv.epoch,'evolve:fault'),(RuntimeError,))
        assert inv.immutable_snapshot()==before
        inv.receive_pet_evolution(struct.pack('>i',fault),inv.epoch,'evolve:fault')
        assert state(fault).evolution.stage==1
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');p=inv.read_pet_state(db,fault)
            inv.change_pet_growth(db,fault,'evolve:later-death',p.progress.state.version,'resources',(0,2))
        inv.receive_pet_evolution(struct.pack('>i',fault),inv.epoch,'evolve:dead')
        assert (state(fault).progress.state.hp,state(fault).progress.state.mp)==(0,2)
        # Unknown old metadata is not made stage0 on load or by rebirth.
        unknown=inv.grant_pet(500001)
        with closing(store.connect()) as db,db:db.execute('DELETE FROM inventory_pet_evolution WHERE pet_id=?',(unknown,))
        before=inv.immutable_snapshot();assert state(unknown).evolution is None
        refused(lambda:inv.receive_pet_evolution(struct.pack('>i',unknown),inv.epoch,'evolve:unknown'))
        inv.grant_item(31002)
        pill=next(i.id for i in inv.immutable_snapshot().items if i.template_id==31002)
        before=inv.immutable_snapshot()
        refused(lambda:inv.receive_ordinary_return(struct.pack('>iiQ',pill,1,unknown),inv.epoch,'evolve:unknown-return',(0,)*15))
        assert inv.immutable_snapshot()==before
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');inv.initialize_pet_evolution(db,unknown,0)
            refused(lambda:inv.initialize_pet_evolution(db,unknown,0))
        # Historical released target returns native removal without restoring it.
        inv.free_pet(fault);before=inv.immutable_snapshot()
        replies=inv.receive_pet_evolution(struct.pack('>i',fault),inv.epoch,'evolve:fault')
        assert (0xc07dd,struct.pack('>ii',1,fault)) in replies
        assert inv.immutable_snapshot()==before
    write_json(OUT/'evidence/pet-evolution-verification.json',{'passed':[
        'original first two-dan step growth+5 and exact last-item debit; nonhealing HP/MP, actual death0 and all unrelated pet metadata retained',
        'original post-cap row1 dual8/1 cost growth+1; bound-first deterministic material plan',
        'ordinary and super replacement rolls preserve evolution+6 without double addition; original native stage reads persisted values',
        'sparse500050 path0/1/2/6 adds15 growth; all50 post-cap advances then no-debit ceiling refusal',
        'SQL-readonly historical use with hot config forbidden; four real write faults and late native encoding roll all assets back, failed ID retries once',
        'unknown legacy evolution staysNone and fresh evolution/rebirth reject; explicit complete one-time import only; released historical target stays removed'],
        'live_server_changed':False,'native_gui_verified':False})
    print('PASS first/sparse/final50 evolution, rebirth preservation, rollback, read-only replay and unknown-state guards')


if __name__=='__main__':main()
