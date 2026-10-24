"""Owned primitive sources can be read without recursively projecting a pet."""
from pathlib import Path
from tempfile import TemporaryDirectory
from contextlib import closing
import sqlite3
from accounts import AccountStore
from inventory import Inventory
from pet_souls import SoulProfile,SoulRules
import role_mingwen as mingwen
import pet_soul_storage as souls
import runtime_storage


def main():
    with TemporaryDirectory(prefix='pet-projection-sources-') as tmp:
        store=AccountStore(Path(tmp)/'state.sqlite3');runtime_storage.prepare(store)
        role=store.create_role(1111,'宠物投影来源',12,1010101);rid=role['id'];epoch=store.acquire_lease(1111,rid)
        inv=Inventory(store.leased(1111,rid,epoch),1111,rid);pet=inv.grant_pet(500001)
        sr=SoulRules.load();mr=mingwen.MingwenRules.load()
        with closing(store.connect()) as db:souls.prepare(db);mingwen.prepare(db)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            souls.initialize(db,inv,sr,SoulProfile(rid,pet,0,sr.revision,'projection-known-empty',()),'explicit_known_pet_souls')
            mingwen.initialize(db,inv,mr,mingwen.MingwenState(rid,0,mr.revision,'projection-known-mingwen',
                tuple(mingwen.MingwenEntry(i,0,0,0) for i in range(1,23))),'explicit_known_mingwen_ledger')
            source=souls.read(db,inv,sr,pet);inscription=mingwen.read(db,inv,mr)
        with closing(store.connect()) as db:
            db.execute('BEGIN');db.set_authorizer(lambda action,*args:sqlite3.SQLITE_DENY if action in
                (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE) else sqlite3.SQLITE_OK)
            raw=souls.read_profile_source(db,1111,rid,pet,sr)
            state=mingwen.read_state_source(db,1111,rid,mr)
            assert (raw.profile,raw.origin,raw.raw_profile,raw.baseline_source)==(
                source.profile,source.origin,source.raw_profile,source.baseline_source)
            assert (state.state,state.origin,state.raw_state,state.baseline_source)==(
                inscription.state,inscription.origin,inscription.raw_state,inscription.baseline_source)
            for call in (lambda:souls.read_profile_source(db,1112,rid,pet,sr),
                    lambda:mingwen.read_state_source(db,1112,rid,mr)):
                try:call()
                except ValueError:pass
                else:raise AssertionError('Primitive projection source ownership bypass')
        print('PASS actual same-source primitive reads without Inventory recursion, exact shared validation and SQL readonly/foreign refusal')


if __name__=='__main__':main()
