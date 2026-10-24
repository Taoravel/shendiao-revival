"""Gem assets, stamina, sole root resource source and native encoding atomicity."""
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
import sqlite3
import struct
from accounts import AccountStore
from inventory import Inventory,AssetChange
from verify_resource_owner_runtime import fixture
from role_resource_storage import read_role_resources
from role_equipment_storage import current_resource_profile
from currency import read_wallet
import equipment_gem_composition as gems
import role_stamina
import role_vigor
import runtime_storage


def main():
    with TemporaryDirectory(prefix='gem-atomic-') as tmp:
        store=AccountStore(Path(tmp)/'state.sqlite3');role=store.create_role(1111,'合成事务',11,1010109)
        runtime_storage.prepare(store)
        npc=next(p for rows in store.npc_resources[0].values() for p in rows if p.npc_id==10004)
        fixture(store,role,npc)
        with closing(store.connect()) as db:
            epoch=db.execute('SELECT epoch FROM role_leases WHERE role_id=?',(role['id'],)).fetchone()[0]
        inv=Inventory(store.leased(1111,role['id'],epoch),1111,role['id'])
        with closing(store.connect()) as db,db:
            rules=gems.prepare(db);stamina=role_stamina.prepare(db)
            db.execute('BEGIN IMMEDIATE')
            db.execute('CREATE TABLE gem_test_study(role INTEGER PRIMARY KEY,version INTEGER,level INTEGER)')
            db.execute('INSERT INTO gem_test_study VALUES(?,0,0)',(inv.role_id,))
            inv.apply_settlement(db,AssetChange('known-gems',grants=((35001,4,0),)))
            key=next(i.id for i in inv.immutable_snapshot_transaction(db).items if i.template_id==35001)
            role_stamina.initialize(db,inv,stamina,100,100,'explicit_known_stamina')
            gems.initialize_material(db,inv,rules,key,0,'explicit_known_gem_instance')
            runtime_storage._synchronize_source(db,store,inv,'gem:fixture-source',replayed=False)
        def study(db,inventory):
            version,level=db.execute('SELECT version,level FROM gem_test_study WHERE role=?',(inventory.role_id,)).fetchone()
            return gems.CompositionStudy(inventory.role_id,inventory.epoch,'explicit-complete-test-study',version,level)
        with closing(inv.accounts.connect()) as db:
            db.execute('BEGIN')
            command=gems.admit(db,inv,rules,stamina,'retry-after-all-faults',struct.pack('>ii',key,key),9999,study)
        def current():
            with closing(inv.accounts.connect()) as db:
                db.execute('BEGIN');assets=inv.immutable_snapshot_transaction(db)
                projection=current_resource_profile(db,1111,role['id'],epoch,assets,
                    equipment_rules=store.equipment_attribute_rules,resource_rules=store.resource_rules)
                assert (projection.vitals.hp,projection.vitals.mp,projection.vitals.version)==(10,20,0)
                return (assets,role_stamina.read(db,inv,stamina),read_role_resources(db,1111,role['id'],epoch,store.resource_rules),
                    read_wallet(db,1111,role['id'],epoch,store.currency_rules),role_vigor.read(db,inv,store.vigor_rules))
        def hook(db,inventory,assets,*,replayed):
            result=runtime_storage._synchronize_source(db,store,inventory,'gem:root-source',replayed=replayed)
            assert result.caps.source.inventory_revision==assets.inventory_revision
        def perform(callback=hook):
            with closing(inv.accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                return gems.apply(db,inv,rules,stamina,command,study_source=study,precommit=callback)
        before=current()
        async def accidental_async(*args,**kwargs):pass
        try:perform(accidental_async)
        except ValueError:pass
        else:raise AssertionError('Unawaited source synchronization was accepted')
        assert current()==before
        faults=(('inventory_items','UPDATE'),('inventory_items','INSERT'),('inventory_versions','UPDATE'),
            ('inventory_settlements','INSERT'),('role_stamina_profiles','UPDATE'),
            ('inventory_gem_materials','DELETE'),('inventory_gem_materials','INSERT'),
            ('equipment_gem_composition_receipts','INSERT'),('role_resource_receipts','INSERT'))
        for table,action in faults:
            with closing(store.connect()) as db,db:
                db.execute(f"CREATE TRIGGER gem_actual_fault BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT,'gem persistence failed'); END")
            try:perform()
            except sqlite3.IntegrityError:pass
            else:raise AssertionError((table,action,'did not fail'))
            with closing(store.connect()) as db,db:db.execute('DROP TRIGGER gem_actual_fault')
            assert current()==before,(table,action)
        def after_source(db,inventory,assets,*,replayed):
            hook(db,inventory,assets,replayed=replayed)
            raise RuntimeError('root source updated, later callback failed')
        try:perform(after_source)
        except RuntimeError:pass
        else:raise AssertionError('Post-source failure committed')
        assert current()==before
        # Real reply encoding reaches the authoritative wallet. Corrupting its
        # policy inside the same transaction makes late encoding fail, after
        # source/asset/receipt writes; the corruption must also roll back.
        def late_encoding(db,inventory,assets,*,replayed):
            hook(db,inventory,assets,replayed=replayed)
            db.execute("UPDATE role_wallet_profiles SET policy='unknown-gem-test-policy' WHERE role_id=?",(inv.role_id,))
        try:perform(late_encoding)
        except ValueError as exc:assert str(exc)=='Wallet policy migration required'
        else:raise AssertionError('Unknown-wallet late encoding committed')
        assert current()==before
        result=perform();after=current()
        assert not result.replayed and result.stamina.value==65
        assert [(i.template_id,i.quantity) for i in after[0].items if i.template_id in (35001,35014)]==[(35001,2),(35014,1)]
        assert after[2].hp==10 and after[2].mp==20 and after[2].version==before[2].version
        assert after[2].caps.hp_max==before[2].caps.hp_max and after[2].caps.mp_max==before[2].caps.mp_max
        assert after[2].caps.source!=before[2].caps.source and after[3:]==before[3:]
        with closing(store.connect()) as db:
            db.execute('BEGIN');db.set_authorizer(lambda a,*_:sqlite3.SQLITE_DENY if a in
                (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE) else sqlite3.SQLITE_OK)
            paid=gems.apply(db,inv,rules,stamina,command,study_source=None,precommit=hook)
            assert paid.replayed and paid.stamina.value==65
        assert current()==after
    print('PASS nine actual SQL faults + source/encoding failures roll back; retry once; root HP/MP/cash/vigor preserved; paid readonly')


if __name__=='__main__':main()
