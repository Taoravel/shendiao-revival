"""Known pre-gem score is durable and cannot be silently inferred or reset."""
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from dataclasses import replace
import sqlite3
from accounts import AccountStore
from inventory import Inventory
from inventory_test_support import known_cash_context
from equipment_detail import EquipmentDetail
from equipment_gems import GemRules,GemState
from equipment_gem_score import GemScoreRules,GemScoreBasis
import equipment_gem_storage as sockets
import equipment_gem_score_storage as scores


def refused(fn,errors=(ValueError,)):
    try:fn()
    except errors:return
    raise AssertionError('Unknown, reset or stale pre-gem score accepted')


def main():
    with TemporaryDirectory(prefix='known-gem-score-') as tmp:
        store=AccountStore(Path(tmp)/'state.sqlite3');role=store.create_role(1111,'宝石评分来源',12,1010101)
        config=Inventory.prepare(store);store.inventory_config=config
        inv=Inventory(store,1111,role['id'],config,**known_cash_context(store,1111,role['id']))
        gems=GemRules.load();rules=GemScoreRules.load()
        with closing(store.connect()) as db,db:
            sockets.prepare(db);scores.prepare(db)
            db.execute('BEGIN IMMEDIATE')
            key=db.execute('INSERT INTO inventory_items(role_id,template_id,quantity,slot,binding) VALUES(?,40100,1,0,0)',(inv.role_id,)).lastrowid
            inv.initialize_equipment_condition(db,key,42,80,1)
            inv.initialize_equipment_detail(db,key,EquipmentDetail(1,1,250,((81,20),(811,20),(1231,6))))
            assert scores.read(db,inv,rules,key) is None
            sockets.initialize(db,inv,gems,key,GemState(0,(),gems.revision),0,'explicit_known_socket_profile')
            basis=GemScoreBasis(inv.role_id,key,rules.revision,250,'explicit-known-before-first-gem')
        before=inv.immutable_snapshot()
        def perform(fail_after=False):
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                value=scores.initialize(db,inv,rules,gems,basis,'explicit_known_pre_gem_score')
                if fail_after:raise RuntimeError('outer equipment transaction failed')
                return value
        with closing(store.connect()) as db,db:
            db.execute("CREATE TRIGGER gem_score_fault BEFORE INSERT ON inventory_equipment_gem_score_bases BEGIN SELECT RAISE(ABORT,'known baseline save failed'); END")
        refused(perform,(sqlite3.IntegrityError,))
        with closing(store.connect()) as db,db:db.execute('DROP TRIGGER gem_score_fault')
        refused(lambda:perform(True),(RuntimeError,))
        with closing(store.connect()) as db:
            db.execute('BEGIN');assert scores.read(db,inv,rules,key) is None
            refused(lambda:scores.initialize(db,inv,rules,gems,replace(basis,plain_score=249),'explicit_known_pre_gem_score'))
            refused(lambda:scores.initialize(db,inv,rules,gems,basis,'implicit_zero'))
            db.rollback()
        assert perform()==basis
        assert inv.immutable_snapshot()==before
        with closing(store.connect()) as db:
            db.execute('BEGIN');assert scores.read(db,inv,rules,key)==basis
            refused(lambda:scores.initialize(db,inv,rules,gems,replace(basis,plain_score=251),'explicit_known_pre_gem_score'))
            refused(lambda:scores.initialize(db,inv,rules,gems,replace(basis,source_ref='different-source'),'explicit_known_pre_gem_score'))
            db.set_authorizer(lambda action,*_:sqlite3.SQLITE_DENY if action in
                (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE) else sqlite3.SQLITE_OK)
            assert scores.read(db,inv,rules,key)==basis
            assert scores.initialize(db,inv,rules,gems,basis,'explicit_known_pre_gem_score')==basis
        old=inv;epoch=store.acquire_lease(1111,role['id'])
        inv=Inventory(store.leased(1111,role['id'],epoch),1111,role['id'],config,epoch=epoch,currency_rules=old.currency_rules)
        with closing(store.connect()) as db:
            db.execute('BEGIN');assert scores.read(db,inv,rules,key)==basis
            refused(lambda:scores.read(db,old,rules,key))
        print('PASS known score baseline failure/outer rollback, immutable no-reset, readonly reopen and current lease guards')


if __name__=='__main__':main()
