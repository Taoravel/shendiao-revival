"""Public caller-transaction composition: real SQLite assets and stamina."""
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from dataclasses import replace
import sqlite3
import struct
from accounts import AccountStore
from inventory import Inventory
from inventory_test_support import known_cash_context
import equipment_gem_composition as gems
import role_stamina


def refused(fn,errors=(ValueError,)):
    try:fn()
    except errors:return
    raise AssertionError('Invalid gem transaction committed')


def readonly(db):
    db.set_authorizer(lambda action,*_: sqlite3.SQLITE_DENY if action in
        (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE) else sqlite3.SQLITE_OK)


def main():
    with TemporaryDirectory(prefix='gem-composition-') as tmp:
        store=AccountStore(Path(tmp)/'state.sqlite3');role=store.create_role(1111,'宝石合成',12,1010101)
        config=Inventory.prepare(store);store.inventory_config=config
        inv=Inventory(store,1111,role['id'],config,**known_cash_context(store,1111,role['id']))
        with closing(store.connect()) as db,db:
            rules=gems.prepare(db);stamina=role_stamina.prepare(db)
            # Test-only explicit complete skill source; production must supply
            # the role skill owner's current reader, never assume absent==0.
            db.execute('CREATE TABLE known_test_study(role INTEGER PRIMARY KEY,version INTEGER,level INTEGER)')
            db.execute('INSERT INTO known_test_study VALUES(?,0,0)',(inv.role_id,))
        def study(db,inventory):
            version,level=db.execute('SELECT version,level FROM known_test_study WHERE role=?',(inventory.role_id,)).fetchone()
            return gems.CompositionStudy(inventory.role_id,inventory.epoch,'explicit-test-complete-skill',version,level)
        inv.grant_item(35001,2)
        key=inv.immutable_snapshot().items[0].id
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            role_stamina.initialize(db,inv,stamina,100,100,'explicit_known_stamina')
            gems.initialize_material(db,inv,rules,key,0,'explicit_known_gem_instance')
            command=gems.admit(db,inv,rules,stamina,'ordinary-same-stack',struct.pack('>ii',key,key),9999,study)
            result=gems.apply(db,inv,rules,stamina,command,study_source=study)
            assert result.success and not result.replayed and result.stamina.value==65
            assert [(i.template_id,i.quantity,i.binding) for i in result.snapshot.items]==[(35014,1,0)]
            assert result.messages[-1]==role_stamina.refresh(result.stamina)
        assert [(i.template_id,i.quantity) for i in inv.immutable_snapshot().items]==[(35014,1)]
        with closing(store.connect()) as db,db:
            db.execute('BEGIN')
            readonly(db)
            paid=gems.apply(db,inv,rules,stamina,command,study_source=lambda *_: (_ for _ in ()).throw(AssertionError('Paid must not reread old skill')))
            assert paid.replayed and paid.success and paid.stamina.value==65
            assert paid.snapshot==result.snapshot and paid.messages==result.messages
            refused(lambda:gems.apply(db,inv,rules,stamina,replace(command,draw=0),study_source=study))
        # Later growth/quantity/skill changes are current authority, never
        # rewound by the old paid receipt. No receipt is repaired on replay.
        inv.grant_item(35014,1)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');role_stamina.consume(db,inv,stamina,1)
            db.execute('UPDATE known_test_study SET version=1,level=6')
        with closing(store.connect()) as db:
            db.execute('BEGIN');readonly(db)
            paid=gems.apply(db,inv,rules,stamina,command,study_source=None)
            assert paid.replayed and paid.stamina.value==64 and paid.snapshot.items[0].quantity==2
        # A generic reward merge invalidates the old material source; unknown
        # incoming raw flags are not silently laundered as clean gems.
        merged=inv.immutable_snapshot().items[0]
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            refused(lambda:gems.admit(db,inv,rules,stamina,'must-not-launder',struct.pack('>ii',merged.id,merged.id),0,study))
        # Reconnect permits current paid reads, but cannot execute the admitted
        # old-epoch fresh operation or let the old inventory object write.
        old_inv=inv;epoch=store.acquire_lease(1111,role['id'])
        inv=Inventory(store.leased(1111,role['id'],epoch),1111,role['id'],config,epoch=epoch,currency_rules=old_inv.currency_rules)
        with closing(store.connect()) as db:
            db.execute('BEGIN');readonly(db)
            assert gems.apply(db,inv,rules,stamina,command,study_source=None).stamina.value==64
            refused(lambda:gems.apply(db,old_inv,rules,stamina,command,study_source=None))
        # Missing companion receipt is corruption, not authorization to charge
        # or to reconstruct history. Paid branch remains strict read-only.
        with closing(store.connect()) as db,db:
            db.execute('DELETE FROM inventory_settlements WHERE role_id=? AND settlement_id=?',
                (inv.role_id,'gem-compose:'+command.request_id))
        with closing(store.connect()) as db:
            db.execute('BEGIN');readonly(db)
            refused(lambda:gems.apply(db,inv,rules,stamina,command,study_source=None))
    print('PASS original wire -> persistent gems/stamina; strict current paid, reentry, stale epoch and incomplete receipts')


if __name__=='__main__':main()
