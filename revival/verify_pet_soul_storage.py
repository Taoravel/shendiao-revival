"""Explicit complete soul provenance, caller transaction CAS and rollback."""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import sqlite3
from accounts import AccountStore
from inventory import Inventory
from pet_souls import SoulBean,SoulProfile,SoulRules
from pet_soul_protocol import full_refresh
import pet_soul_storage as souls
import runtime_storage


def main():
    with TemporaryDirectory(prefix='pet-soul-source-') as tmp:
        store=AccountStore(Path(tmp)/'state.sqlite3');runtime_storage.prepare(store)
        rules=SoulRules.load()
        with closing(store.connect()) as db:souls.prepare(db)
        role=store.create_role(1111,'元魂完整来源',12,1010101);rid=role['id'];epoch=store.acquire_lease(1111,rid)
        inv=Inventory(store.leased(1111,rid,epoch),1111,rid);pet=inv.grant_pet(500001)
        initial=SoulProfile(rid,pet,0,rules.revision,'explicit-known-import',
            ((1,SoulBean(31276,61,10001,104,-105,106)),(5,SoulBean(31299,120,10002,-204,205,-206))))
        def refused(action):
            try:action()
            except ValueError:return
            raise AssertionError('Unknown, stale or partial pet soul source accepted')
        def state():
            with closing(store.connect()) as db:
                db.execute('BEGIN')
                return inv.immutable_snapshot_transaction(db),souls.read(db,inv,rules,pet)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');assert souls.read(db,inv,rules,pet) is None
            before=inv.immutable_snapshot_transaction(db)
            saved=souls.initialize(db,inv,rules,initial,'explicit_known_pet_souls')
            assert saved.profile==initial and saved.inventory_revision==before.inventory_revision+1
            assert full_refresh(saved.profile)[0]==0xc0803
        saved_state=state()
        refused(lambda:replace(saved_state[1],inventory_revision=True))
        with closing(store.connect()) as db:
            db.execute('BEGIN')
            def readonly(action,*args):
                return sqlite3.SQLITE_DENY if action in (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE) else sqlite3.SQLITE_OK
            db.set_authorizer(readonly)
            assert souls.initialize(db,inv,rules,initial,'explicit_known_pet_souls')==saved_state[1]
            refused(lambda:souls.initialize(db,inv,rules,replace(initial,source_ref='guessed'), 'explicit_known_pet_souls'))
        next_profile=replace(initial,version=1,entries=(initial.entries[0],))
        for table in ('inventory_pet_souls','inventory_versions'):
            with closing(store.connect()) as db:
                db.execute(f"CREATE TRIGGER soul_fault BEFORE UPDATE ON {table} BEGIN SELECT RAISE(ABORT,'soul-fault'); END");db.commit()
            try:
                with closing(store.connect()) as db,db:
                    db.execute('BEGIN IMMEDIATE');souls.replace_profile(db,inv,rules,saved_state[1],next_profile)
            except sqlite3.IntegrityError as error:assert 'soul-fault' in str(error)
            else:raise AssertionError('Expected actual soul SQL fault')
            finally:
                with closing(store.connect()) as db:db.execute('DROP TRIGGER soul_fault');db.commit()
            assert state()==saved_state
        try:
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                current=souls.replace_profile(db,inv,rules,saved_state[1],next_profile)
                assert full_refresh(current.profile)[0]==0xc0803
                raise ValueError('caller fails after soul encoding')
        except ValueError as error:assert str(error)=='caller fails after soul encoding'
        assert state()==saved_state
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');current=souls.replace_profile(db,inv,rules,saved_state[1],next_profile)
            assert current.profile.entries[0][1].raw5==-105
            refused(lambda:souls.replace_profile(db,inv,rules,saved_state[1],next_profile))
            # Repeating the original import returns current, never resets slot5.
            assert souls.initialize(db,inv,rules,initial,'explicit_known_pet_souls')==current
        assert state()[1]==current
        second=inv.grant_pet(500001)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN');assert souls.read(db,inv,rules,second) is None
            refused(lambda:souls.read(db,inv,rules,pet+99999))
            empty=souls.initialize(db,inv,rules,SoulProfile(rid,second,0,rules.revision,
                'explicit-known-empty-second-pet',()),'explicit_known_pet_souls')
            assert empty.profile.entries==() and souls.read(db,inv,rules,second)==empty
        new_epoch=store.acquire_lease(1111,rid)
        with closing(store.connect()) as db:
            db.execute('BEGIN');refused(lambda:souls.read(db,inv,rules,pet))
            new_inv=Inventory(store.leased(1111,rid,new_epoch),1111,rid)
            assert souls.read(db,new_inv,rules,pet).profile==current.profile
        print('PASS explicit complete pet soul map persistence/current CAS, unknown!=empty, readonly import retry/no reset, '
            '2 SQL faults and encoded caller rollback, stale before/lease refusal; no paid asset action claim')


if __name__=='__main__':main()
