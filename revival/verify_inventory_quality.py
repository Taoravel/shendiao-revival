"""Instance quality survives old-schema startup and all carried-stack operations."""
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from accounts import AccountStore
from inventory import AssetChange, Inventory
from inspect_client import OUT, write_json


def rejected(inv, operation):
    before = inv.snapshot()
    try:
        operation()
    except ValueError:
        pass
    else:
        raise AssertionError('Invalid quality operation accepted')
    assert inv.snapshot() == before


def main():
    with TemporaryDirectory() as tmp:
        store = AccountStore(Path(tmp)/'state.sqlite3')
        role = store.create_role(1111, '品质存档', 12, 1010101)
        # Reproduce the actual pre-binding/quality schema, rather than creating
        # the new schema then pretending the migration ran.
        with closing(store.connect()) as db, db:
            db.execute('''CREATE TABLE inventory_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT, role_id INTEGER NOT NULL REFERENCES roles(id),
                template_id INTEGER NOT NULL, quantity INTEGER NOT NULL CHECK(quantity>0),
                slot INTEGER NOT NULL, equipment_slot INTEGER,
                UNIQUE(role_id,slot), UNIQUE(role_id,equipment_slot))''')
            db.execute('INSERT INTO inventory_items(role_id,template_id,quantity,slot) VALUES(?,?,?,?)',
                       (role['id'],31000,3,0))
        config = Inventory.prepare(store)
        inv = Inventory(store,1111,role['id'],config)
        legacy = inv.snapshot()['items'][0]
        assert legacy['binding'] == 0 and legacy['quality'] is None
        # None is unknown, distinct from the confirmed quality value zero.
        inv.grant_item(31000,8,quality=0)
        inv.grant_item(31000,9,binding=1,quality=10)
        inv.grant_item(31000,4,quality=10)
        initial = inv.snapshot()['items']
        assert [(x['quantity'],x['binding'],x['quality']) for x in initial] == [
            (3,0,None),(8,0,0),(9,1,10),(4,0,10)]
        quality_item = initial[2]
        inv.move_item(quality_item['id'],9,4)
        split = inv.snapshot()['items'][-1]
        assert (split['binding'],split['quality'],split['quantity']) == (1,10,4)
        rejected(inv,lambda:inv.move_item(split['id'],initial[3]['slot'],1))
        rejected(inv,lambda:inv.move_item(initial[1]['id'],legacy['slot'],1))
        inv.arrange_bag()
        state = inv.snapshot()
        assert {(x['binding'],x['quality']):x['quantity'] for x in state['items']} == {
            (0,None):3,(0,0):8,(0,10):4,(1,10):9}
        assert split['id'] not in {x['id'] for x in state['items']}
        # Stable arrangement must not bump the asset version.
        inv.arrange_bag()
        assert inv.snapshot() == state
        command = AssetChange('quality-reward',grants=((31000,2,1,25),))
        with closing(store.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            inv.apply_settlement(db,command)
        expected = inv.snapshot()
        with closing(store.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            inv.apply_settlement(db,command)
        assert inv.snapshot() == expected
        def conflicting():
            with closing(store.connect()) as db, db:
                db.execute('BEGIN IMMEDIATE')
                inv.apply_settlement(db,AssetChange('quality-reward',grants=((31000,2,1,26),)))
        rejected(inv,conflicting)
        for value in (-1,2**31,True,1.5):
            rejected(inv,lambda value=value:inv.grant_item(31000,quality=value))
        reopened = AccountStore(store.path)
        assert Inventory(reopened,1111,role['id'],Inventory.prepare(reopened)).snapshot() == expected
        # A late outer failure undoes the quality-bearing reward and receipt.
        try:
            with closing(store.connect()) as db, db:
                db.execute('BEGIN IMMEDIATE')
                inv.apply_settlement(db,AssetChange('quality-rollback',grants=((31000,2,1,26),)))
                raise RuntimeError('failure after inventory write')
        except RuntimeError:
            pass
        assert inv.snapshot() == expected
    result = {'passed':['old pre-binding/quality schema migrates without inventing quality',
        'unknown quality and quality zero never stack together',
        'split inherits quality and binding', 'partial incompatible merges reject atomically',
        'arrangement preserves per-quality quantities and stable surviving keys',
        'repeated arrangement does not bump revision',
        'quality-bearing reward replay and conflict detection',
        'outer rollback undoes quality reward and receipt',
        'quality bounds reject bool float negative and overflow',
        'reopen and repeat startup preserve metadata'], 'native_ui_tested':False}
    write_json(OUT/'evidence/inventory-quality-verification.json',result)
    print('PASS:',', '.join(result['passed']))


if __name__ == '__main__':
    main()
