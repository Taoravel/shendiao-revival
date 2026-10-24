"""Explicit correction of v1 experimental quality/color ambiguity."""
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib
import json
from accounts import AccountStore
from inventory import Inventory
from inspect_client import OUT,write_json


def main():
    with TemporaryDirectory() as tmp:
        store=AccountStore(Path(tmp)/'state.sqlite3')
        role=store.create_role(1111,'颜色核对',12,1010101)
        config=Inventory.prepare(store);inv=Inventory(store,1111,role['id'],config)
        inv.grant_item(40200,binding=1);key=inv.snapshot()['items'][0]['id']
        original={'version':3,'current':17,'maximum':90,'quality_tier':5}
        old_json=json.dumps(original)
        with closing(store.connect()) as db,db:
            db.execute('UPDATE inventory_equipment_conditions SET revision=?,state=? WHERE item_key=?',
                       ('2026-10-23.equipment-condition.1',old_json,key))
            # The v1 receipt did not fingerprint its policy. Preserve it and
            # refuse blind replay under corrected v2 semantics.
            fingerprint=hashlib.sha256(json.dumps(['wear',key,2,1],separators=(',',':')).encode()).hexdigest()
            db.execute('INSERT INTO inventory_equipment_receipts VALUES(?,?,?,?)',
                       (role['id'],'old:wear',fingerprint,old_json))
        try:inv.snapshot()
        except ValueError:pass
        else:raise AssertionError('Old quality field silently reinterpreted as color')
        try:
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                inv.reconcile_equipment_color(db,key,3,2)
                raise RuntimeError('outer failure after migration')
        except RuntimeError:pass
        with closing(store.connect()) as db:
            assert db.execute('SELECT revision,state FROM inventory_equipment_conditions WHERE item_key=?',(key,)).fetchone()==(
                '2026-10-23.equipment-condition.1',old_json)
            assert db.execute('SELECT COUNT(*) FROM inventory_equipment_color_migrations').fetchone()[0]==0
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            corrected=inv.reconcile_equipment_color(db,key,3,2)
            assert (corrected.version,corrected.current,corrected.maximum,corrected.color_tier)==(4,17,90,2)
            assert inv.reconcile_equipment_color(db,key,3,2)==corrected
            try:inv.reconcile_equipment_color(db,key,3,3)
            except ValueError:pass
            else:raise AssertionError('Reconciliation key changed known color')
            newer=inv.wear_equipment(db,key,'new:wear',4,1)
            assert inv.reconcile_equipment_color(db,key,3,2)==corrected
            assert inv.equipment_condition(db,key)==newer
            try:inv.wear_equipment(db,key,'old:wear',2,1)
            except ValueError:pass
            else:raise AssertionError('Ambiguous v1 receipt replayed under v2 policy')
            audit=db.execute('SELECT before_state FROM inventory_equipment_color_migrations WHERE item_key=?',(key,)).fetchone()[0]
            assert audit==old_json
        item=inv.snapshot()['items'][0]
        assert item['binding']==1 and item['condition']==newer
        assert Inventory(AccountStore(store.path),1111,role['id'],config).snapshot()==inv.snapshot()
    report={'passed':['v1 ambiguous field requires explicit color; no automatic reinterpretation',
        'actual color2 independent of old quality5','current maximum binding and identity preserved',
        'original state JSON retained in migration audit','repeat reconciliation is idempotent',
        'conflicting color refused','old reconciliation cannot overwrite newer wear',
        'policy-scoped commands refuse ambiguous v1 receipts','outer failure rolls back migration and audit',
        'reopen keeps corrected state'],
        'production_data_migrated':False,'actual_color_source':'trusted explicit caller'}
    write_json(OUT/'evidence/equipment-color-reconciliation-verification.json',report)
    print('PASS:',', '.join(report['passed']))


if __name__=='__main__':main()
