"""Explicit vigor baseline, online-only accrual and lease-safe rest spending."""
from contextlib import closing
from pathlib import Path
import tempfile
from accounts import AccountStore
from inventory import Inventory
import runtime_storage
import role_vigor
from inspect_client import OUT,write_json


def main():
    with tempfile.TemporaryDirectory() as temp:
        store=AccountStore(Path(temp)/'vigor.sqlite3');role=store.create_role(1111,'活力检查',11,1010109)
        runtime_storage.prepare(store);epoch=store.acquire_lease(1111,role['id'])
        inv=Inventory(store.leased(1111,role['id'],epoch),1111,role['id']);rules=store.vigor_rules
        def tx(fn,*args):
            with closing(inv.accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE');return fn(db,inv,rules,*args)
        assert tx(role_vigor.read) is None
        tx(role_vigor.initialize,100,100,'explicit_migration')
        tx(role_vigor.bind,1000)
        assert tx(role_vigor.consume,15).value==85
        assert tx(role_vigor.advance,151000).value==85
        tx(role_vigor.suspend,151000)
        next_epoch=store.acquire_lease(1111,role['id'])
        inv=Inventory(store.leased(1111,role['id'],next_epoch),1111,role['id'])
        tx(role_vigor.bind,1000000) # Offline time is deliberately excluded.
        assert tx(role_vigor.advance,1149999).value==85
        assert tx(role_vigor.advance,1150000).value==90
        assert tx(role_vigor.advance,2050000).value==100
        assert tx(role_vigor.consume,15).value==85
        assert tx(role_vigor.advance,2050001).value==85 # No banked time at cap.
        before=tx(role_vigor.read)
        try:tx(role_vigor.consume,1000)
        except ValueError:pass
        else:raise AssertionError('Insufficient vigor spent')
        assert tx(role_vigor.read)==before
        try:tx(role_vigor.initialize,0,100,'explicit_migration')
        except ValueError:pass
        else:raise AssertionError('Existing vigor reset')
        old_inv=inv
        store.acquire_lease(1111,role['id'])
        with closing(old_inv.accounts.connect()) as db:
            try:
                db.execute('BEGIN IMMEDIATE');role_vigor.consume(db,old_inv,rules,1)
            except ValueError:pass
            else:raise AssertionError('Stale vigor lease accepted')
    report={'passed':['legacy profile remains unknown','explicit baseline100 and rest debit15',
        'five points per300000 online ms; fractions retained across reconnect',
        'offline time excluded and time at cap cannot be banked','insufficient/reset/old lease rejected'],
        'regeneration_amount_and_baseline':'designed recovery profile','live_database_modified':False}
    write_json(OUT/'evidence/role-vigor-verification.json',report);print(report)


if __name__=='__main__':main()
