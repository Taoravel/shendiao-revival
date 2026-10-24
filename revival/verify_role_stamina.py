"""Stamina450 is an independent explicit authority, never vigor440."""
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from accounts import AccountStore
from inventory import Inventory
from inventory_test_support import known_cash_context
import role_stamina
from native_gameplay_probe import probe
from verify_role_resource_protocol import native_assignment


def refused(fn):
    try:fn()
    except ValueError:return
    raise AssertionError('Unknown, insufficient or stale stamina accepted')


def main():
    with TemporaryDirectory(prefix='stamina-') as tmp:
        store=AccountStore(Path(tmp)/'state.sqlite3');role=store.create_role(1111,'体力检查',12,1010101)
        inv=Inventory(store,1111,role['id'],**known_cash_context(store,1111,role['id']))
        with closing(store.connect()) as db,db:
            rules=role_stamina.prepare(db)
            db.execute('BEGIN IMMEDIATE')
            assert role_stamina.read(db,inv,rules) is None
            initial=role_stamina.initialize(db,inv,rules,100,100,'explicit_known_stamina')
            after=role_stamina.consume(db,inv,rules,35)
            assert (initial.value,initial.version,after.value,after.version)==(100,0,65,1)
            assert role_stamina.refresh(after)[1].hex()=='02000001c2428200000000027642c80000'
            assert role_stamina.initialize(db,inv,rules,100,100,'explicit_known_stamina')==after
            refused(lambda:role_stamina.initialize(db,inv,rules,100,101,'explicit_known_stamina'))
            refused(lambda:role_stamina.initialize(db,inv,rules,100,100,'new_restoration_role'))
            for amount in (66,0,-1,True,1.5):refused(lambda:role_stamina.consume(db,inv,rules,amount))
            assert role_stamina.read(db,inv,rules)==after
        payload=role_stamina.refresh(after)[1]
        native,raw=probe(0xec3590,0xec36b0,0xec3730,payload=payload)
        assert native==payload
        for key,value in ((450,65),(450,0),(630,100),(630,16777216)):
            assert native_assignment(key,value)==value
        for value,maximum in ((True,100),(0,0),(101,100),(0,16777217)):
            refused(lambda:role_stamina.StaminaState(inv.role_id,0,value,maximum))
        with closing(store.connect()) as db:
            refused(lambda:role_stamina.read(db,inv,rules))
            db.execute('BEGIN IMMEDIATE')
            db.execute("UPDATE role_stamina_profiles SET policy='future'")
            refused(lambda:role_stamina.read(db,inv,rules))
            db.rollback()
        store.acquire_lease(1111,role['id'])
        with closing(store.connect()) as db:
            db.execute('BEGIN');refused(lambda:role_stamina.read(db,inv,rules))
    print('PASS independent stamina, native450/630 codec and consumer, no reset, precision/unknown/epoch guards')


if __name__=='__main__':main()
