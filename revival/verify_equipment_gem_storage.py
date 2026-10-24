"""Explicit current equipment gem source and same-transaction full-source CAS."""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import sqlite3
import json
from accounts import AccountStore
from inventory import Inventory
from inventory_test_support import known_cash_context
from equipment_gems import GemRules,GemState,SocketRequest,embed
import equipment_gem_storage as sockets


def refused(fn,errors=(ValueError,)):
    try:fn()
    except errors:return
    raise AssertionError('Unknown, mutable or stale equipment gem source accepted')


def main():
    with TemporaryDirectory(prefix='gem-profile-') as tmp:
        store=AccountStore(Path(tmp)/'state.sqlite3');role=store.create_role(1111,'宝石存档',12,1010101)
        config=Inventory.prepare(store);store.inventory_config=config
        inv=Inventory(store,1111,role['id'],config,**known_cash_context(store,1111,role['id']))
        rules=GemRules.load()
        with closing(store.connect()) as db:sockets.prepare(db)
        inv.grant_item(40104);inv.grant_item(35001,2)
        equipment,material=inv.immutable_snapshot().items
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            assert sockets.read(db,inv,rules,equipment.id) is None
            sockets.initialize(db,inv,rules,equipment.id,GemState(0,(),rules.revision),0,'explicit_known_socket_profile')
            basis=sockets.read(db,inv,rules,equipment.id)
            assert sockets.request_basis(db,inv,rules,SocketRequest('embed',equipment.id,1,material.id))==basis
            refused(lambda:sockets.request_basis(db,inv,rules,SocketRequest('embed',equipment.id,4,material.id)))
            result=embed(rules,basis.item,basis.state,material,basis.equipment_skill,flags=(0,0))
        before=inv.immutable_snapshot()
        # Explicit disposable current-container fixture, not a wearing action
        # or evidence that the role satisfies this equipment's wear eligibility.
        with closing(store.connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('UPDATE inventory_items SET equipment_slot=0,slot=-1 WHERE id=?',(equipment.id,))
            assert sockets.request_basis(db,inv,rules,SocketRequest('remove',equipment.id,4,selection=-1)).item.equipment_slot==0
            refused(lambda:sockets.request_basis(db,inv,rules,SocketRequest('remove',equipment.id,1,selection=-1)))
            db.rollback()
        def perform(hook=None):
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                changed=sockets.replace_state(db,inv,rules,basis,result.after)
                if hook is not None:hook(db,inv,changed)
                return changed
        # Full persistent sources are part of the basis, even when changed
        # whitespace decodes to an identical object and no item field changed.
        mutations=(('inventory_equipment_gems','state'),('inventory_equipment_details','detail'),
            ('inventory_equipment_conditions','state'))
        for table,column in mutations:
            with closing(store.connect()) as db:
                db.execute('BEGIN IMMEDIATE')
                raw=db.execute(f'SELECT {column} FROM {table} WHERE item_key=?',(equipment.id,)).fetchone()[0]
                db.execute(f'UPDATE {table} SET {column}=? WHERE item_key=?',(json.dumps(json.loads(raw),indent=2),equipment.id))
                refused(lambda:sockets.replace_state(db,inv,rules,basis,result.after))
                db.rollback()
        with closing(store.connect()) as db:
            db.execute('BEGIN')
            refused(lambda:replace(basis,item=replace(basis.item,binding=True)))
            refused(lambda:sockets.replace_state(db,inv,rules,basis,replace(result.after,version=2)))
        for table in ('inventory_equipment_gems','inventory_versions'):
            with closing(store.connect()) as db,db:
                db.execute(f"CREATE TRIGGER socket_save_failure BEFORE UPDATE ON {table} BEGIN SELECT RAISE(ABORT,'socket save failed'); END")
            refused(perform,(sqlite3.IntegrityError,))
            with closing(store.connect()) as db,db:db.execute('DROP TRIGGER socket_save_failure')
            assert inv.immutable_snapshot()==before
            with closing(store.connect()) as db:
                db.execute('BEGIN');assert sockets.read(db,inv,rules,equipment.id)==basis
        def late_failure(db,inventory,current):
            from equipment_gems import encode_detail
            encoded=encode_detail(rules,current.item,current.state,current.equipment_skill)
            assert len(encoded)>len(__import__('equipment_detail').encode(current.item.template_id,current.item.detail,current.item.condition,rules.detail_rules))
            raise RuntimeError('native output built but outer save failed')
        refused(lambda:perform(late_failure),(RuntimeError,))
        assert inv.immutable_snapshot()==before
        saved=perform()
        assert saved.state.templates==(35001,) and saved.state.version==1
        assert saved.inventory_revision==basis.inventory_revision+1
        with closing(store.connect()) as db:
            db.execute('BEGIN')
            refused(lambda:sockets.replace_state(db,inv,rules,basis,result.after))
        with closing(store.connect()) as db:
            db.execute('BEGIN');current=sockets.read(db,inv,rules,equipment.id)
            assert current.state.templates==(35001,) and current.state.version==1
            assert current.item.detail==equipment.detail
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            assert sockets.initialize(db,inv,rules,equipment.id,GemState(0,(),rules.revision),0,'explicit_known_socket_profile')==current
            refused(lambda:sockets.initialize(db,inv,rules,equipment.id,GemState(0,(35014,),rules.revision),0,'explicit_known_socket_profile'))
        inv.move_item(equipment.id,4);inv.move_item(equipment.id,0)
        with closing(store.connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            refused(lambda:sockets.replace_state(db,inv,rules,current,replace(current.state,version=2,templates=())))
            db.rollback()
        with closing(store.connect()) as db:
            db.execute('BEGIN');db.set_authorizer(lambda action,*_:sqlite3.SQLITE_DENY if action in
                (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE) else sqlite3.SQLITE_OK)
            current=sockets.read(db,inv,rules,equipment.id)
            assert current.state.templates==(35001,)
        old_inv=inv;epoch=store.acquire_lease(1111,role['id'])
        inv=Inventory(store.leased(1111,role['id'],epoch),1111,role['id'],config,epoch=epoch,currency_rules=old_inv.currency_rules)
        with closing(store.connect()) as db:
            db.execute('BEGIN');assert sockets.read(db,inv,rules,equipment.id).state.templates==(35001,)
            refused(lambda:sockets.read(db,old_inv,rules,equipment.id))
        print('PASS source CAS/reopen, old epoch/version/JSON guards, real SQL/late native rollback; current readonly and no reset')


if __name__=='__main__':main()
