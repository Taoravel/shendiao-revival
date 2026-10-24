"""Same role transaction: gem list, explicit score and condition color CAS."""
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from dataclasses import replace
import sqlite3
import json
from accounts import AccountStore
from inventory import Inventory
from inventory_test_support import known_cash_context
from equipment_detail import EquipmentDetail
from equipment_gems import GemRules,GemState,embed,remove,encode_detail
from equipment_gem_score import GemScoreRules,GemScoreBasis,project
import equipment_gem_storage as sockets
import equipment_gem_score_storage as scores
import equipment_gem_presentation as presentation
from research_equipment_gem_detail import NativeGemEquipmentDetail


def refused(fn,errors=(ValueError,)):
    try:fn()
    except errors:return
    raise AssertionError('Invalid gem presentation source or failure committed')


def main():
    with TemporaryDirectory(prefix='gem-score-color-cas-') as tmp:
        store=AccountStore(Path(tmp)/'state.sqlite3');role=store.create_role(1111,'宝石分色写入',12,1010101)
        inv=Inventory(store,1111,role['id'],**known_cash_context(store,1111,role['id']))
        gem_rules=GemRules.load();score_rules=GemScoreRules.load()
        with closing(store.connect()) as db,db:
            sockets.prepare(db);scores.prepare(db)
            db.execute('BEGIN IMMEDIATE')
            key=db.execute('INSERT INTO inventory_items(role_id,template_id,quantity,slot,binding) VALUES(?,40101,1,0,0)',(inv.role_id,)).lastrowid
            inv.initialize_equipment_condition(db,key,42,80,1)
            inv.initialize_equipment_detail(db,key,EquipmentDetail(1,1,1040,((81,80),(811,80),(1231,30))))
            sockets.initialize(db,inv,gem_rules,key,GemState(0,(),gem_rules.revision),0,'explicit_known_socket_profile')
            score_basis=GemScoreBasis(inv.role_id,key,score_rules.revision,1040,'known-level10-before-gems')
            scores.initialize(db,inv,score_rules,gem_rules,score_basis,'explicit_known_pre_gem_score')
        inv.grant_item(35001,2)
        with closing(store.connect()) as db:
            db.execute('BEGIN')
            before=sockets.read(db,inv,gem_rules,key)
            material=next(i for i in inv.immutable_snapshot_transaction(db).items if i.template_id==35001)
            plan=embed(gem_rules,before.item,before.state,material,0,flags=(0,0))
            wanted=project(score_rules,gem_rules,before.item,before.state,plan.after,score_basis)
        def current():
            with closing(store.connect()) as db:
                db.execute('BEGIN');return sockets.read(db,inv,gem_rules,key),inv.immutable_snapshot_transaction(db),scores.read(db,inv,score_rules,key)
        def perform(*,change=wanted,after_list=None,after_presentation=None):
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                saved=sockets.replace_state(db,inv,gem_rules,before,plan.after)
                if after_list is not None:after_list(db,saved)
                result=presentation.apply(db,inv,gem_rules,score_rules,before,saved,change)
                if after_presentation is not None:after_presentation(db,result)
                return result
        initial=current()
        # A second version update fault is specifically in presentation,
        # after the gem source's first version CAS has already succeeded.
        faults=(('inventory_equipment_details',''),('inventory_equipment_conditions',''),
            ('inventory_versions',f' WHEN OLD.revision={before.inventory_revision+1}'))
        for table,when in faults:
            with closing(store.connect()) as db,db:
                db.execute(f"CREATE TRIGGER gem_presentation_fault BEFORE UPDATE ON {table}{when} BEGIN SELECT RAISE(ABORT,'paired presentation failed'); END")
            refused(perform,(sqlite3.IntegrityError,))
            with closing(store.connect()) as db,db:db.execute('DROP TRIGGER gem_presentation_fault')
            assert current()==initial,table
        for bad in (replace(wanted,old_contribution=False),replace(wanted,new_contribution=51),
                replace(wanted,after=replace(wanted.after,detail=replace(wanted.after.detail,score=1091))),
                replace(wanted,after=replace(wanted.after,condition=replace(wanted.after.condition,maximum=81))),
                replace(wanted,after=replace(wanted.after,binding=False))):
            refused(lambda:perform(change=bad))
            assert current()==initial
        def raw_source_change(db,saved):
            db.execute('UPDATE inventory_equipment_details SET detail=? WHERE item_key=?',
                (json.dumps(json.loads(saved.detail_source[2]),indent=2),key))
        refused(lambda:perform(after_list=raw_source_change))
        assert current()==initial
        def score_source_change(db,saved):
            raw=db.execute('SELECT basis FROM inventory_equipment_gem_score_bases WHERE item_key=?',(key,)).fetchone()[0]
            changed=json.loads(raw);changed['source_ref']='later-different-known-score-source'
            db.execute('UPDATE inventory_equipment_gem_score_bases SET basis=? WHERE item_key=?',(json.dumps(changed),key))
        refused(lambda:perform(after_list=score_source_change))
        assert current()==initial
        native=NativeGemEquipmentDetail(40101)
        def late_native(db,result):
            parsed=native.parse(encode_detail(gem_rules,result.item,result.state,0))
            assert (parsed['score'],parsed['color'],parsed['gems'])==(1090,2,[35001])
            raise RuntimeError('late failure after actual native encoding')
        refused(lambda:perform(after_presentation=late_native),(RuntimeError,))
        assert current()==initial
        result=perform()
        assert result.state==plan.after and result.item.detail.score==1090
        assert result.inventory_revision==before.inventory_revision+2
        assert (result.item.condition.color_tier,result.item.condition.current,result.item.condition.maximum,result.item.condition.version)==(2,42,80,1)
        # This low-level writer deliberately does not charge material/cash.
        # The combined gameplay controller remains a separate unfinished step.
        assert next(i for i in current()[1].items if i.template_id==35001).quantity==2
        refused(perform)
        # Same-grade different family keeps score/color exactly unchanged.
        inv.grant_item(35000)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');old=sockets.read(db,inv,gem_rules,key)
            moon=next(i for i in inv.immutable_snapshot_transaction(db).items if i.template_id==35000)
            swap=embed(gem_rules,old.item,old.state,moon,0,flags=(0,0))
            score=project(score_rules,gem_rules,old.item,old.state,swap.after,score_basis)
            saved=sockets.replace_state(db,inv,gem_rules,old,swap.after)
            db.set_authorizer(lambda action,*_:sqlite3.SQLITE_DENY if action in
                (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE) else sqlite3.SQLITE_OK)
            swapped=presentation.apply(db,inv,gem_rules,score_rules,old,saved,score)
            assert swapped.inventory_revision==saved.inventory_revision and swapped.item==saved.item
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');old=sockets.read(db,inv,gem_rules,key)
            removal=remove(gem_rules,old.item,old.state,-1,0,flags=0)
            score=project(score_rules,gem_rules,old.item,old.state,removal.after,score_basis)
            saved=sockets.replace_state(db,inv,gem_rules,old,removal.after)
            cleared=presentation.apply(db,inv,gem_rules,score_rules,old,saved,score)
            assert (cleared.item.detail.score,cleared.item.condition.color_tier,cleared.item.condition.version)==(1040,1,2)
            parsed=native.parse(encode_detail(gem_rules,cleared.item,cleared.state,0))
            assert parsed['gems']==[] and parsed['gem_effects']==[] and parsed['score']==1040
        print('PASS paired score/color/gem CAS,3 actual write faults/late native rollback, immutable proof, readonly same-grade no-op and removal')


if __name__=='__main__':main()
