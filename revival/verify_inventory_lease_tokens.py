"""Opaque current role leases cross the actual inventory transaction seam."""
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import struct

from accounts import AccountStore
from inventory import Inventory
from inventory_test_support import known_cash_context
from inspect_client import OUT, write_json
from role_growth import prepare_growth_storage, initialize_growth, load_growth_rules
from role_attributes import AttributeBaseline, load_attribute_rules
from role_attribute_storage import prepare_attribute_storage, initialize_attribute_baseline, read_attribute_snapshot
from item_effects import VitalState


def refused(action):
    try:
        action()
    except ValueError:
        return
    raise AssertionError('Invalid or obsolete inventory lease accepted')


def main():
    token = 'role-owner:会话:0007'
    replacement = '00007'
    with TemporaryDirectory() as tmp:
        store = AccountStore(Path(tmp) / 'state.sqlite3')
        role = store.create_role(1111, '字符串租约', 12, 1010101)
        config = Inventory.prepare(store)
        store.inventory_config = config
        store.acquire_lease(1111, role['id'])
        with closing(store.connect()) as db, db:
            db.execute('UPDATE role_leases SET epoch=? WHERE role_id=?', (token, role['id']))
        context = known_cash_context(store, 1111, role['id'], epoch=token, balances=(41,0,0,0))
        inv = Inventory(store.leased(1111, role['id'], token), 1111, role['id'], config, **context)
        inv.grant_item(40200)
        key = inv.immutable_snapshot().items[0].id
        with closing(inv.accounts.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            with patch.object(inv.accounts, 'connect', side_effect=AssertionError('Nested lease connection')):
                initial = inv.immutable_snapshot_transaction(db)
                fact = inv.equip_transaction(db, key, 0, token, 'opaque:equip')
                current = inv.immutable_snapshot_transaction(db)
                inv.equipment_bag_messages(db, token)
            assert initial.items[0].equipment_slot is None and current.items[0].equipment_slot == 0
            assert fact.login_epoch == token and current.inventory_revision == fact.inventory_revision
        with closing(inv.accounts.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            replay = inv.equip_transaction(db, key, 0, token, 'opaque:equip')
            assert replay.replayed and replay.login_epoch == token
            for bad in (True, False, None, '', 'x'*129, 0, -1, 2**63, 1.0, b'token', 'wrong'):
                refused(lambda bad=bad: inv.equip_transaction(db, key, 0, bad, 'bad'))
                if bad is not None:  # None means the trusted Inventory default.
                    refused(lambda bad=bad: inv.immutable_snapshot_transaction(db, epoch=bad))
        with closing(store.connect()) as db:
            prepare_growth_storage(db)
            prepare_attribute_storage(db)
        growth_rules, attribute_rules = load_growth_rules(), load_attribute_rules()
        with closing(inv.accounts.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            growth = initialize_growth(db, 1111, role['id'], token, growth_rules, expected_level=1, free_points=0)
            initialize_attribute_baseline(db, 1111, role['id'], token,
                AttributeBaseline(role['id'], 1, 0, (10,10,10,10,10), (500,1000,20,5,40,20,10,20,5)),
                growth, attribute_rules, VitalState(role['id'],0,1,500,1,1000))
        inv.grant_item(32000)
        medicine = next(i.id for i in inv.immutable_snapshot().items if i.template_id == 32000)
        request = struct.pack('>iiQ', medicine, 0, role['id'])
        inv.receive_role_consumable(request, token, 'opaque:medicine')
        inv.receive_role_consumable(request, token, 'opaque:medicine')
        with closing(inv.accounts.connect()) as db:
            db.execute('BEGIN')
            vitals = read_attribute_snapshot(db,1111,role['id'],token).vitals
            assert (vitals.hp,vitals.version) == (201,1)
        current = inv.immutable_snapshot()
        with closing(store.connect()) as db, db:
            db.execute('UPDATE role_leases SET epoch=? WHERE role_id=?', (replacement, role['id']))
        current_inv = Inventory(store.leased(1111, role['id'], replacement), 1111, role['id'], config,
                                epoch=replacement, currency_rules=context['currency_rules'])
        with closing(current_inv.accounts.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            refused(lambda: inv.immutable_snapshot_transaction(db))
            refused(lambda: inv.equip_transaction(db, key, 0, token, 'opaque:equip'))
            assert current_inv.immutable_snapshot_transaction(db) == current
            for lookalike in ('7', 7):
                refused(lambda lookalike=lookalike: current_inv.immutable_snapshot_transaction(db, epoch=lookalike))
                refused(lambda lookalike=lookalike: current_inv.equip_transaction(db,key,0,lookalike,'lookalike'))
            historical = current_inv.equip_transaction(db, key, 0, replacement, 'opaque:equip')
            assert historical.replayed and historical.login_epoch == token
        store.release_lease(role['id'], replacement)
        with closing(store.connect()) as db:
            db.execute('BEGIN')
            refused(lambda: current_inv.immutable_snapshot_transaction(db))
    report = {'passed': ['opaque Unicode lease preserved exactly in equip event and snapshot',
        'actual LeasedAccounts fenced transaction and wallet replies work without nested connection',
        'same-token replay is historical and does not re-equip',
        'role medicine uses same opaque token and replay consumes once',
        'padded opaque00007 differs from string7 and integer7',
        'bool/empty/oversized/foreign/obsolete/inactive lease rejected',
        'new current token acknowledges old fact with original token retained'],
        'live_client_tested': False, 'live_server_changed': False}
    write_json(OUT / 'evidence/inventory-lease-tokens-verification.json', report)
    print('PASS:', ', '.join(report['passed']))


if __name__ == '__main__':
    main()
