"""Per-instance binding: reward settlement, stack compatibility and transfers."""
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from accounts import AccountStore
from inventory import Inventory, AssetChange
from inspect_client import OUT, write_json


def main():
    with TemporaryDirectory() as tmp:
        store = AccountStore(Path(tmp)/'state.sqlite3')
        role = store.create_role(1111,'绑定资产',12,1010101)
        store.inventory_config = Inventory.prepare(store)
        inv = Inventory(store,1111,role['id'])
        inv.grant_item(31000,2)
        change = AssetChange('bound-reward',grants=((31000,5,1),))
        with closing(store.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            inv.apply_settlement(db,change)
        first = inv.snapshot()
        assert [(x['quantity'],x['binding']) for x in first['items']] == [(2,0),(5,1)]
        free, bound = first['items']
        inv.move_item(bound['id'],3,2)
        assert inv.snapshot()['items'][-1]['binding'] == 1
        before = inv.snapshot()
        try:
            inv.move_item(bound['id'],free['slot'],1)
        except ValueError:
            pass
        else:
            raise AssertionError('Incompatible partial merge accepted')
        assert inv.snapshot() == before
        with closing(store.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            inv.require_transferable(db,free['id'])
            try:
                inv.require_transferable(db,bound['id'])
            except ValueError:
                pass
            else:
                raise AssertionError('Bound transfer allowed')
            inv.apply_settlement(db,change)
        assert inv.snapshot() == before
        other = Inventory(AccountStore(store.path),1111,role['id'],store.inventory_config)
        assert other.snapshot() == before
        assert sum(x['quantity'] for x in before['items'] if x['binding']) == 5
        assert sum(x['quantity'] for x in before['items'] if not x['binding']) == 2
        try:
            AssetChange('bad-binding',grants=((31000,1,7),))
        except ValueError:
            pass
        else:
            raise AssertionError('Unknown binding mode accepted')
    result = {'passed':['bound/unbound grants keep separate stacks', 'split inherits binding',
                        'partial merge with different binding rejected atomically',
                        'bound transfer gate rejects', 'bound reward replay and reopen preserve status',
                        'unknown binding mode rejected'],
              'supported_binding_modes':[0,1], 'native_binding_flag_verified':True,
              'native_binding_evidence':'item-position-binding-verification.json',
              'task_reward_producer_tested_by_this_script':False}
    write_json(OUT/'evidence/inventory-binding-verification.json',result)
    print('PASS:', ', '.join(result['passed']))


if __name__ == '__main__':
    main()
