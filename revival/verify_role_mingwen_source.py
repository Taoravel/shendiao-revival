"""Actual complete known Mingwen ledger, source CAS and lease fencing."""
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
import sqlite3
from dataclasses import replace
from accounts import AccountStore
from inventory import Inventory
import runtime_storage
import role_mingwen as mingwen


def main():
    with TemporaryDirectory(prefix='known-mingwen-source-') as tmp:
        store=AccountStore(Path(tmp)/'state.sqlite3');runtime_storage.prepare(store)
        role=store.create_role(1111,'铭文明确来源',12,1010101);rid=role['id'];epoch=store.acquire_lease(1111,rid)
        inv=Inventory(store.leased(1111,rid,epoch),1111,rid);rules=mingwen.MingwenRules.load()
        with closing(store.connect()) as db:mingwen.prepare(db)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');assert mingwen.read(db,inv,rules) is None
            entries=tuple(mingwen.MingwenEntry(i,0,0,1 if i==22 else 0) for i in range(1,23))
            state=mingwen.MingwenState(rid,0,rules.revision,'explicit-known-role-mingwen',entries)
            before=inv.immutable_snapshot_transaction(db)
            saved=mingwen.initialize(db,inv,rules,state,'explicit_known_mingwen_ledger')
            assert saved.inventory_revision==before.inventory_revision+1
            assert saved.state==state and saved.state.soul_cap_increment==1
        with closing(store.connect()) as db:
            db.execute('BEGIN');db.set_authorizer(lambda action,*args:sqlite3.SQLITE_DENY if action in
                (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE) else sqlite3.SQLITE_OK)
            assert mingwen.read(db,inv,rules)==saved
            assert mingwen.initialize(db,inv,rules,state,'explicit_known_mingwen_ledger')==saved
        entries2=entries[:-1]+(mingwen.MingwenEntry(22,-7,12345,2),)
        after=replace(state,version=1,entries=entries2)
        assert after.soul_cap_increment==0
        def current():
            with closing(store.connect()) as db:
                db.execute('BEGIN');return mingwen.read(db,inv,rules),inv.immutable_snapshot_transaction(db)
        before_faults=current()
        for table in ('role_mingwen_profiles','inventory_versions'):
            with closing(store.connect()) as db,db:
                db.execute(f"CREATE TRIGGER mingwen_fault BEFORE UPDATE ON {table} BEGIN SELECT RAISE(ABORT,'mingwen-write-fault'); END")
            try:
                with closing(store.connect()) as db,db:
                    db.execute('BEGIN IMMEDIATE');mingwen.replace_state(db,inv,rules,saved,after)
            except sqlite3.IntegrityError as error:assert 'mingwen-write-fault' in str(error)
            else:raise AssertionError('Real Mingwen write fault did not execute')
            finally:
                with closing(store.connect()) as db,db:db.execute('DROP TRIGGER mingwen_fault')
            assert current()==before_faults
        try:
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE');changed=mingwen.replace_state(db,inv,rules,saved,after)
                assert changed.state.soul_cap_increment==0
                raise RuntimeError('late Mingwen caller failure')
        except RuntimeError as error:assert str(error)=='late Mingwen caller failure'
        assert current()==before_faults
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');changed=mingwen.replace_state(db,inv,rules,saved,after)
            assert changed.state.entries[21]==mingwen.MingwenEntry(22,-7,12345,2)
        with closing(store.connect()) as db:
            db.execute('BEGIN');db.set_authorizer(lambda action,*args:sqlite3.SQLITE_DENY if action in
                (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE) else sqlite3.SQLITE_OK)
            assert mingwen.initialize(db,inv,rules,state,'explicit_known_mingwen_ledger')==changed
            for action in (lambda:mingwen.replace_state(db,inv,rules,saved,after),
                    lambda:mingwen.initialize(db,inv,rules,replace(state,source_ref='different-history'),'explicit_known_mingwen_ledger')):
                try:action()
                except ValueError:pass
                else:raise AssertionError('Historical Mingwen source was overwritten')
        # A real unrelated inventory change makes the previously captured full
        # source basis stale, even though inscription22 itself is unchanged.
        inv.grant_item(38045)
        with closing(store.connect()) as db:
            db.execute('BEGIN')
            try:mingwen.replace_state(db,inv,rules,changed,replace(after,version=2))
            except ValueError:pass
            else:raise AssertionError('Stale inventory basis changed current Mingwen source')
        other=store.create_role(1111,'别人的铭文',12,1010101);other_epoch=store.acquire_lease(1111,other['id'])
        other_inv=Inventory(store.leased(1111,other['id'],other_epoch),1111,other['id'])
        with closing(store.connect()) as db:
            db.execute('BEGIN');assert mingwen.read(db,other_inv,rules) is None
            try:mingwen.initialize(db,other_inv,rules,state,'explicit_known_mingwen_ledger')
            except ValueError:pass
            else:raise AssertionError('Foreign Mingwen ledger imported')
        epoch2=store.acquire_lease(1111,rid)
        with closing(store.connect()) as db:
            db.execute('BEGIN')
            try:mingwen.read(db,inv,rules)
            except ValueError:pass
            else:raise AssertionError('Old lease read current inscription authority')
        inv=Inventory(store.leased(1111,rid,epoch2),1111,rid)
        with closing(store.connect()) as db:
            db.execute('BEGIN');assert mingwen.read(db,inv,rules).state==after
        for bad in (lambda:replace(state,entries=entries[:-1]),lambda:replace(state,entries=entries[::-1]),
                lambda:replace(entries[21],raw_active=True),lambda:replace(state,version=2**63-1)):
            try:bad()
            except ValueError:pass
            else:raise AssertionError('Partial/unrepresentable Mingwen state accepted')
        print('PASS real complete Mingwen source/current CAS and known!=missing; active==1 not2; exact signed fields; '
            'readonly original import returns current/no reset;2 SQL faults+caller failure rollback; stale inventory/foreign/old lease refuses')


if __name__=='__main__':main()
