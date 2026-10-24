"""Known original consumable examples and resource limits."""
from item_effects import Consumables, VitalState
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from accounts import AccountStore
from inventory import Inventory


def main():
    rules = Consumables.load()
    target = VitalState(1, 7, 10, 500, 5, 200)
    result = rules.apply(32000, target)
    assert (result.hp, result.mp, result.version) == (210, 5, 8)
    # Original ai=40 / bi=200, quality10 gives 600 recovery, capped at max MP.
    result = rules.apply(32001, target, quality=10)
    assert result.mp == 200 and result.hp == 10
    assert target == VitalState(1,7,10,500,5,200)
    for call in (lambda: rules.apply(32001, target),
                 lambda: rules.apply(32000, VitalState(1,0,0,100,0,100)),
                 lambda: rules.apply(32000, VitalState(1,0,100,100,0,100)),
                 lambda: rules.apply(999999, target)):
        try:
            call()
        except ValueError:
            continue
        raise AssertionError('Invalid consumable effect accepted')
    with TemporaryDirectory() as tmp:
        store = AccountStore(Path(tmp) / 'state.sqlite3')
        role = store.create_role(1111,'药品事务',12,1010101)
        inv = Inventory(store,1111,role['id'],Inventory.prepare(store))
        inv.grant_item(32000,2)
        key = inv.snapshot()['items'][0]['id']
        state = VitalState(role['id'],0,1,500,0,100)
        before = inv.snapshot()
        try:
            with closing(store.connect()) as db, db:
                db.execute('BEGIN IMMEDIATE')
                inv.use_consumable(db,key,state)
                raise ValueError('Injected vitality save failure')
        except ValueError:
            pass
        assert inv.snapshot() == before
        with closing(store.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            healed = inv.use_consumable(db,key,state)
            assert db.in_transaction
        assert healed.hp == 201
        assert inv.snapshot()['items'][0]['quantity'] == 1
        before = inv.snapshot()
        try:
            with closing(store.connect()) as db, db:
                db.execute('BEGIN IMMEDIATE')
                inv.use_consumable(db,key,VitalState(role['id'],1,500,500,0,100))
        except ValueError:
            pass
        else:
            raise AssertionError('No-op effect consumed item')
        assert inv.snapshot() == before
        # A role consumable must use its own persisted quality, just as the pet
        # path does. The Interface must not depend on a caller supplying quality.
        inv.grant_item(32001,quality=10)
        quality_key=next(x['id'] for x in inv.snapshot()['items'] if x['template_id']==32001)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            quality_result=inv.use_consumable(db,quality_key,VitalState(role['id'],0,1,500,1,1000))
        assert quality_result.mp==601
        inv.grant_item(32001,quality=0)
        zero_key=next(x['id'] for x in inv.snapshot()['items'] if x['template_id']==32001)
        before=inv.snapshot()
        try:
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                inv.use_consumable(db,zero_key,VitalState(role['id'],0,1,500,1,1000),quality=10)
        except ValueError:pass
        else:raise AssertionError('External quality overrode owned instance metadata')
        assert inv.snapshot()==before
    print('PASS fixed/formula recovery, limits, immutable snapshots and rejection')


if __name__ == '__main__':
    main()
