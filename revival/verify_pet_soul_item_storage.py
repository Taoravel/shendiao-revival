"""Known orb data and retained raw6 survive real Inventory source CAS."""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import sqlite3
from accounts import AccountStore
from inventory import Inventory
from pet_soul_item_data import OrbTips
from pet_soul_item_storage import OrbRules,OrbSource
import pet_soul_item_storage as orbs
import runtime_storage


def main():
    with TemporaryDirectory(prefix='soul-orb-source-') as tmp:
        store=AccountStore(Path(tmp)/'state.sqlite3');runtime_storage.prepare(store);rules=OrbRules.load()
        with closing(store.connect()) as db:orbs.prepare(db)
        role=store.create_role(1111,'元魂珠实例',12,1010101);rid=role['id'];epoch=store.acquire_lease(1111,rid)
        inv=Inventory(store.leased(1111,rid,epoch),1111,rid);inv.grant_item(31276);inv.grant_item(31277)
        key=next(i.id for i in inv.immutable_snapshot().items if i.template_id==31276)
        other=next(i.id for i in inv.immutable_snapshot().items if i.template_id==31277)
        source=OrbSource(rid,key,31276,0,rules.revision,'known-full-orb-import',OrbTips(61,10001,-205,204),160,-2)
        def refused(action):
            try:action()
            except ValueError:return
            raise AssertionError('Unknown, reset or stale orb source accepted')
        def state():
            with closing(store.connect()) as db:
                db.execute('BEGIN');return inv.immutable_snapshot_transaction(db),orbs.read(db,inv,rules,key)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');before=inv.immutable_snapshot_transaction(db)
            assert orbs.read(db,inv,rules,key) is None
            refused(lambda:orbs.tip_message(db,inv,rules,key))
            saved=orbs.initialize(db,inv,rules,source,'explicit_known_orb_instance')
            assert saved.source==source and saved.inventory_revision==before.inventory_revision+1
            kind,body=orbs.tip_message(db,inv,rules,key)
            assert kind==0xc03fe and body[9:].hex()=='0000003d00002711ffffff33000000cc'
            assert saved.source.retained_raw6==-2 and saved.source.nonbinding_flags==160
            empty_history=OrbSource(rid,other,31277,0,rules.revision,'known-never-worn-orb',OrbTips(0,0,0,0),0,None)
            assert orbs.initialize(db,inv,rules,empty_history,'explicit_known_orb_instance').source.retained_raw6 is None
        saved_state=state();saved=saved_state[1]
        next_source=replace(source,version=1,tips=OrbTips(140,10002,-205,204))
        refused(lambda:replace(saved,inventory_revision=True))
        refused(lambda:replace(saved,item=replace(saved.item,binding=False)))
        with closing(store.connect()) as db:
            db.execute('BEGIN')
            db.set_authorizer(lambda action,*args:sqlite3.SQLITE_DENY if action in
                (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE) else sqlite3.SQLITE_OK)
            assert orbs.initialize(db,inv,rules,source,'explicit_known_orb_instance')==saved
            refused(lambda:orbs.initialize(db,inv,rules,replace(source,retained_raw6=1),'explicit_known_orb_instance'))
        for table in ('inventory_pet_soul_items','inventory_versions'):
            with closing(store.connect()) as db:
                db.execute(f"CREATE TRIGGER orb_fault BEFORE UPDATE ON {table} BEGIN SELECT RAISE(ABORT,'orb-fault'); END");db.commit()
            try:
                with closing(store.connect()) as db,db:
                    db.execute('BEGIN IMMEDIATE');orbs.replace_source(db,inv,rules,saved,next_source)
            except sqlite3.IntegrityError as error:assert 'orb-fault' in str(error)
            else:raise AssertionError('Expected actual orb write fault')
            finally:
                with closing(store.connect()) as db:db.execute('DROP TRIGGER orb_fault');db.commit()
            assert state()==saved_state
        try:
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE');orbs.replace_source(db,inv,rules,saved,next_source)
                assert orbs.tip_message(db,inv,rules,key)[1][9:].hex()=='0000008c00002712ffffff33000000cc'
                raise ValueError('caller fails after orb encoding')
        except ValueError as error:assert str(error)=='caller fails after orb encoding'
        assert state()==saved_state
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            refused(lambda:orbs.replace_source(db,inv,rules,saved,replace(next_source,retained_raw6=0)))
            current=orbs.replace_source(db,inv,rules,saved,next_source)
            assert current.source.retained_raw6==-2 and current.source.nonbinding_flags==160
            assert orbs.initialize(db,inv,rules,source,'explicit_known_orb_instance')==current
            refused(lambda:orbs.replace_source(db,inv,rules,saved,next_source))
        assert state()[1]==current
        # Explicit fault-model fixture: a generic binding change and reversal
        # must not launder old flags/history back into a known current source.
        with closing(store.connect()) as db,db:
            db.execute('UPDATE inventory_items SET binding=1 WHERE id=?',(key,))
            db.execute('UPDATE inventory_items SET binding=0 WHERE id=?',(key,))
        with closing(store.connect()) as db:
            db.execute('BEGIN');assert orbs.read(db,inv,rules,key) is None
            refused(lambda:orbs.tip_message(db,inv,rules,key))
        new_epoch=store.acquire_lease(1111,rid)
        with closing(store.connect()) as db:
            db.execute('BEGIN');refused(lambda:orbs.read(db,inv,rules,other))
            active=Inventory(store.leased(1111,rid,new_epoch),1111,rid)
            assert orbs.read(db,active,rules,other).source==empty_history
        print('PASS real orb4 persistence/tips/current CAS, explicit flags and exact negative raw6 retained, '
            'unknown!=zero, readonly no-reset import,2 SQL+encoded caller rollbacks, binding ABA invalidation and stale lease')


if __name__=='__main__':main()
