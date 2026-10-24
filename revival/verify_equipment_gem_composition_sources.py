"""Fresh source CAS, mixed-binding failure and unknown legacy refusals."""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import struct
from accounts import AccountStore
from inventory import Inventory,AssetChange
from inventory_test_support import known_cash_context
import equipment_gem_composition as gems
import role_stamina


def refused(fn):
    try:fn()
    except ValueError:return
    raise AssertionError('Unknown/stale material, skill or stamina source accepted')


def main():
    with TemporaryDirectory(prefix='gem-sources-') as tmp:
        store=AccountStore(Path(tmp)/'state.sqlite3');role=store.create_role(1111,'宝石来源',12,1010101)
        inv=Inventory(store,1111,role['id'],**known_cash_context(store,1111,role['id']))
        with closing(store.connect()) as db,db:
            rules=gems.prepare(db);stamina=role_stamina.prepare(db)
            db.execute('CREATE TABLE gem_source_test_study(version INTEGER,level INTEGER)')
            db.execute('INSERT INTO gem_source_test_study VALUES(0,0)')
        inv.grant_item(35118,3,0);inv.grant_item(35118,2,1)
        first,second=inv.immutable_snapshot().items
        payload=struct.pack('>ii',first.id,second.id)
        def study(db,inventory):
            version,level=db.execute('SELECT version,level FROM gem_source_test_study').fetchone()
            return gems.CompositionStudy(inventory.role_id,inventory.epoch,'complete-zaxue-test',version,level)
        def admit(db,name='mixed-failure',draw=5500,reader=study):
            return gems.admit(db,inv,rules,stamina,name,payload,draw,reader)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            refused(lambda:admit(db))
            gems.initialize_material(db,inv,rules,first.id,0,'explicit_known_gem_instance')
            gems.initialize_material(db,inv,rules,second.id,0,'explicit_known_gem_instance')
            refused(lambda:admit(db)) # stamina unknown, not implicitly100
            role_stamina.initialize(db,inv,stamina,100,100,'explicit_known_stamina')
            refused(lambda:admit(db,reader=None))
            refused(lambda:admit(db,reader=lambda *_:None))
            refused(lambda:gems.CompositionStudy(inv.role_id,inv.epoch,'other-skills',0,0,skill_id=100008))
            command=admit(db)
        before=inv.immutable_snapshot()
        # Returning to the same quantity cannot prove unchanged provenance:
        # the generic incoming grant carries no complete raw-flag authority.
        with closing(store.connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            inv.apply_settlement(db,AssetChange('outside-consume',debits=((first.id,1),)))
            inv.apply_settlement(db,AssetChange('outside-refill',grants=((35118,1,0),)))
            assert inv.immutable_snapshot_transaction(db).items==before.items
            refused(lambda:admit(db,'same-quantity-unknown-source'))
            db.rollback()
        # Changes are made inside disposable rolled-back transactions. Public
        # apply must refuse without requiring any repair or fresh receipt.
        changes=(
            ("UPDATE gem_source_test_study SET version=1,level=3",()),
            ("UPDATE role_stamina_profiles SET value=99,version=1 WHERE role_id=?",(inv.role_id,)),
            ("UPDATE inventory_gem_materials SET flags=160 WHERE item_key=?",(first.id,)),
            ("UPDATE inventory_gem_materials SET origin='unknown' WHERE item_key=?",(first.id,)),
            ("UPDATE inventory_gem_materials SET policy='future' WHERE item_key=?",(first.id,)),
            ("UPDATE inventory_items SET quantity=4 WHERE id=?",(first.id,)),
            ("UPDATE inventory_items SET binding=1 WHERE id=?",(first.id,)),
            ("UPDATE inventory_items SET quality=0 WHERE id=?",(first.id,)))
        for sql,args in changes:
            with closing(store.connect()) as db:
                db.execute('BEGIN IMMEDIATE');db.execute(sql,args)
                refused(lambda:gems.apply(db,inv,rules,stamina,command,study_source=study))
                db.rollback()
            assert inv.immutable_snapshot()==before
        # Slot-away-and-back retains the same full material fields, but the
        # admission revision is stale and must not charge.
        inv.move_item(first.id,5);inv.move_item(first.id,0)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            refused(lambda:gems.apply(db,inv,rules,stamina,command,study_source=study))
            command=admit(db,'mixed-failure-current')
        with closing(store.connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('UPDATE role_stamina_profiles SET value=79 WHERE role_id=?',(inv.role_id,))
            refused(lambda:admit(db)) # level10 costs80
            db.rollback()
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            failed=gems.apply(db,inv,rules,stamina,command,study_source=study)
            assert failed.success is False and failed.stamina.value==20
            assert [(i.id,i.template_id,i.quantity,i.binding) for i in failed.snapshot.items]==[
                (first.id,35118,3,0),(second.id,35118,1,1)]
        # Failure did not erase the survivor's known source. A new attempt is
        # rejected solely for insufficient20 stamina, without consuming gems.
        with closing(store.connect()) as db:
            db.execute('BEGIN');refused(lambda:admit(db,'next-attempt',draw=0))
        after_failure=inv.immutable_snapshot()
        with closing(store.connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('UPDATE role_stamina_profiles SET value=100,version=2 WHERE role_id=?',(inv.role_id,))
            used={i.slot for i in inv.immutable_snapshot_transaction(db).items}
            for slot in range(inv.policy['bag_capacity']):
                if slot not in used:
                    db.execute('INSERT INTO inventory_items(role_id,template_id,quantity,slot,binding) VALUES(?,32000,1,?,0)',(inv.role_id,slot))
            full=gems.admit(db,inv,rules,stamina,'full-bag-same-stack',struct.pack('>ii',first.id,first.id),0,study)
            try:gems.apply(db,inv,rules,stamina,full,study_source=study)
            except ValueError as exc:assert str(exc)=='Bag full'
            else:raise AssertionError('Full bag manufactured output without space')
            db.rollback()
        assert inv.immutable_snapshot()==after_failure
        # Success output cannot merge into a stack with unknown raw flags.
        with closing(store.connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('UPDATE role_stamina_profiles SET value=100,version=2 WHERE role_id=?',(inv.role_id,))
            inv.apply_settlement(db,AssetChange('test-unknown-output',grants=((35131,1,1),)))
            success=admit(db,'output-unknown',draw=0)
            refused(lambda:gems.apply(db,inv,rules,stamina,success,study_source=study))
            db.rollback()
        # A complete known output stack can merge, retaining bound output and
        # a usable new source stamp. This uses actual public settlement logic.
        with closing(store.connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('UPDATE role_stamina_profiles SET value=100,version=2 WHERE role_id=?',(inv.role_id,))
            inv.apply_settlement(db,AssetChange('test-known-output',grants=((35131,1,1),)))
            target=next(i for i in inv.immutable_snapshot_transaction(db).items if i.template_id==35131)
            gems.initialize_material(db,inv,rules,target.id,0,'explicit_known_gem_instance')
            success=admit(db,'output-known',draw=0)
            applied=gems.apply(db,inv,rules,stamina,success,study_source=study)
            assert [(i.template_id,i.quantity,i.binding) for i in applied.snapshot.items]==[(35118,2,0),(35131,2,1)]
            db.execute('UPDATE role_stamina_profiles SET value=100,version=4 WHERE role_id=?',(inv.role_id,))
            next_command=gems.admit(db,inv,rules,stamina,'known-merged-stack',struct.pack('>ii',target.id,target.id),0,study)
            assert next_command.first.quantity==2 and next_command.first.binding==1
            db.rollback()
        print('PASS mixed failure retains first/binding, loses one second, costs80; unknown/stale sources and unsafe merges refuse')


if __name__=='__main__':main()
