"""Public pet binding state, atomic bound books and original native flags."""
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from dataclasses import FrozenInstanceError
import sqlite3
import struct

from accounts import AccountStore
from inventory import Inventory, PET_INFO, REFRESH_PET, QUERY_PETS, pet_record
from inventory_test_support import known_cash_context
from pet_flags import PetFlags
from inspect_client import OUT, write_json
from research_pet_binding import native_record_binding,native_column_bindings


def refused(action):
    try:action()
    except ValueError:return
    raise AssertionError('Invalid or unknown pet flag operation accepted')


def main():
    with TemporaryDirectory() as tmp:
        store=AccountStore(Path(tmp)/'state.sqlite3')
        role=store.create_role(1111,'绑定学习',12,1010101)
        config=Inventory.prepare(store)
        inv=Inventory(store,1111,role['id'],config,
            **known_cash_context(store,1111,role['id'],balances=(77,0,0,0)))
        pet=inv.grant_pet(500001)
        def current():return next(p for p in inv.snapshot()['pets'] if p['id']==pet)
        flags=current().get('flags')
        assert flags is not None and flags.raw==0 and not flags.bound, 'New pet binding state is still unknown'
        inv.grant_item(31956,2)
        book=next(i['id'] for i in inv.snapshot()['items'] if i['template_id']==31956)
        replies=inv.receive_pet_skill_book(struct.pack('>6i',pet,book,-1,-1,-1,-1),inv.epoch,'binding:first',(0,0))
        assert current()['flags'].raw==2 and current()['flags'].bound
        assert current()['skills'].learned==(200091,200061,200011)
        assert next(i['quantity'] for i in inv.snapshot()['items'] if i['id']==book)==1
        assert any(kind==PET_INFO for kind,body in replies), 'Binding change did not rebuild native pet-column cache'
        assert native_record_binding(pet_record(current()))==(2,True)
        assert native_column_bindings(next(body for kind,body in replies if kind==PET_INFO))==((pet,2,True),)
        before=inv.immutable_snapshot()
        refused(lambda:inv.receive_pet_skill_book(struct.pack('>6i',pet,book,-1,-1,-1,-1),inv.epoch,'binding:duplicate',(0,0)))
        assert inv.immutable_snapshot()==before
        inv.grant_item(31005)
        other=next(i['id'] for i in inv.snapshot()['items'] if i['template_id']==31005)
        inv.receive_pet_skill_book(struct.pack('>6i',pet,other,-1,-1,-1,-1),inv.epoch,'binding:ordinary',(0,0))
        before=inv.immutable_snapshot()
        replay=inv.receive_pet_skill_book(struct.pack('>6i',pet,book,-1,-1,-1,-1),inv.epoch,'binding:first',(0,0))
        assert inv.immutable_snapshot()==before
        assert native_column_bindings(next(body for kind,body in replay if kind==PET_INFO))==((pet,2,True),)
        from research_pet_skills import native_record_skills
        assert native_record_skills(next(b for k,b in replay if k==REFRESH_PET))[0]==(200091,200061,200011,200021)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            receipt=inv.learn_pet_skill(db,book,pet,inv.epoch,'binding:first',None,(0,0))
            assert receipt.flags_before==PetFlags(0,0) and receipt.flags_after==PetFlags(1,2)
            refused(lambda:inv.require_pet_transferable(db,pet))
        try:inv.immutable_snapshot().pets[0].flags.raw=0
        except FrozenInstanceError:pass
        else:raise AssertionError('Mutable pet binding in cross-owner snapshot')
        # An already-bound pet accepts a real upgrade without rebinding/version churn.
        inv.grant_item(31957)
        upgrade=next(i['id'] for i in inv.snapshot()['items'] if i['template_id']==31957)
        inv.receive_pet_skill_book(struct.pack('>6i',pet,upgrade,-1,-1,-1,-1),inv.epoch,'binding:upgrade',(999,999))
        assert current()['flags']==PetFlags(1,2)
        assert current()['skills'].learned==(200091,200061,200012,200021)
        # Original Pet decoding must preserve high flags even with Unicode name
        # and a variable-length learned list before the flag byte.
        inv.rename_pet(pet,'绑定宠甲')
        assert native_record_binding(pet_record(current()))==(2,True)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            legacy=db.execute('INSERT INTO inventory_pets(role_id,template_id,name) VALUES(?,?,?)',
                              (role['id'],500001,'已知非绑定位')).lastrowid
            inv.initialize_pet_flags(db,legacy,128)
            refused(lambda:inv.require_pet_transferable(db,legacy))
            refused(lambda:inv.initialize_pet_flags(db,legacy,0))
            inv.initialize_pet_care(db,legacy,1,100,6000)
            inv.initialize_pet_growth(db,legacy)
            inv.initialize_pet_skills(db,legacy,(200061,))
            inv.initialize_pet_skill_progress(db,legacy,0)
            inv.initialize_pet_skill_expiry(db,legacy,())
        # Binding preserves the whole original raw byte, not just bit1.
        inv.receive_pet_skill_book(struct.pack('>6i',legacy,book,-1,-1,-1,-1),inv.epoch,'binding:opaque',(0,0))
        opaque=next(p for p in inv.snapshot()['pets'] if p['id']==legacy)
        assert opaque['flags']==PetFlags(1,130)
        assert native_record_binding(pet_record(opaque))==(130,True)
        failure_pet=inv.grant_pet(500001)
        inv.grant_item(31956,2)
        failure_book=next(i['id'] for i in inv.snapshot()['items'] if i['template_id']==31956)
        body=struct.pack('>6i',failure_pet,failure_book,-1,-1,-1,-1)
        before=inv.immutable_snapshot()
        for table,action in (('inventory_pet_flags','UPDATE'),('inventory_pet_skill_receipts','INSERT')):
            with closing(store.connect()) as db:
                db.execute(f"CREATE TRIGGER fail_binding BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT,'binding save failure'); END")
            try:inv.receive_pet_skill_book(body,inv.epoch,'binding:save-failure',(0,0))
            except sqlite3.IntegrityError:pass
            else:raise AssertionError('Actual binding/receipt storage failure did not execute')
            assert inv.immutable_snapshot()==before
            with closing(store.connect()) as db:db.execute('DROP TRIGGER fail_binding')
        unknown_wallet=Inventory(store,1111,role['id'],config,epoch=inv.epoch)
        refused(lambda:unknown_wallet.receive_pet_skill_book(body,inv.epoch,'binding:no-wallet',(0,0)))
        assert inv.immutable_snapshot()==before
        try:
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                inv.learn_pet_skill(db,failure_book,failure_pet,inv.epoch,'binding:outer',0,(0,0))
                raise RuntimeError('outer common receipt failure')
        except RuntimeError:pass
        assert inv.immutable_snapshot()==before
        refused(lambda:inv.receive_pet_skill_book(body,inv.epoch+1,'binding:stale-lease',(0,0)))
        assert inv.immutable_snapshot()==before
        inv.receive_pet_skill_book(body,inv.epoch,'binding:save-failure',(0,0))
        assert next(p for p in inv.snapshot()['pets'] if p['id']==failure_pet)['flags']==PetFlags(1,2)
        # Legacy unknown flags are neither inferred nor silently bound.
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            unknown=db.execute('INSERT INTO inventory_pets(role_id,template_id,name) VALUES(?,?,?)',
                (role['id'],500001,'未知绑定旧宠')).lastrowid
            inv.initialize_pet_care(db,unknown,1,100,6000)
            inv.initialize_pet_growth(db,unknown)
            inv.initialize_pet_skills(db,unknown,())
            inv.initialize_pet_skill_progress(db,unknown,0)
            inv.initialize_pet_skill_expiry(db,unknown,())
        assert next(p for p in inv.snapshot()['pets'] if p['id']==unknown).get('flags') is None
        before=inv.immutable_snapshot()
        refused(lambda:inv.receive_pet_skill_book(struct.pack('>6i',unknown,failure_book,-1,-1,-1,-1),inv.epoch,'binding:unknown',(0,0)))
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            refused(lambda:inv.require_pet_transferable(db,unknown))
        assert inv.immutable_snapshot()==before
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            inv.initialize_pet_flags(db,unknown,0)
            assert inv.require_pet_transferable(db,unknown)==PetFlags(0,0)
        inv.fight_pet(unknown)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            refused(lambda:inv.require_pet_transferable(db,unknown))
        inv.fight_pet()
        inv.free_pet(unknown)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            refused(lambda:inv.initialize_pet_flags(db,unknown,0))
            refused(lambda:inv.require_pet_transferable(db,unknown))
            refused(lambda:inv.initialize_pet_flags(db,True,0))
        foreign_role=store.create_role(1111,'别人的绑定宠',12,1010101)
        foreign_inv=Inventory(store,1111,foreign_role['id'],config)
        foreign_pet=foreign_inv.grant_pet(500001)
        before=inv.immutable_snapshot()
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            refused(lambda:inv.initialize_pet_flags(db,foreign_pet,0))
            refused(lambda:inv.require_pet_transferable(db,foreign_pet))
        assert inv.immutable_snapshot()==before
        assert Inventory(AccountStore(store.path),1111,role['id'],config).snapshot()==inv.snapshot()
        queried=inv.receive(QUERY_PETS,struct.pack('>iQ',1,role['id']))
        assert native_column_bindings(next(b for k,b in queried if k==PET_INFO))==((pet,2,True),(legacy,130,True),(failure_pet,2,True))
    report={'passed':['new pet known unbound state and immutable flags',
        'binding book consumes exactly one and atomically learns/binds',
        'original full-column decoder, flag converter and binding getter consume current replies',
        'variable skill list and Unicode names preserve correct flag byte',
        'duplicate rejection, upgrade without flag churn, full original raw byte preserved',
        'replay sends latest skills and binding without repeat debit',
        'actual flag save and receipt abort, outer exception and missing wallet roll back all changes',
        'stale lease refused; unknown legacy explicit import only; no reset',
        'bound/unknown/other flags/fighting/released transfer gate; reopen retains state'],
        'shared_route_connected':False,'native_gui_tested':False,'cross_role_trade_implemented':False}
    write_json(OUT/'evidence/pet-binding-verification.json',report)
    print('PASS:',', '.join(report['passed']))


if __name__=='__main__':main()
