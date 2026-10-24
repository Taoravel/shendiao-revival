"""Real inventory tip seam, original full parser, persistence and rollback."""
from contextlib import closing
from dataclasses import FrozenInstanceError
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import sqlite3
import struct

from accounts import AccountStore
from equipment_detail import EquipmentDetail
from inventory import Inventory, AssetChange, ITEM_TIPS, ITEM_TIPS_REPLY
from inventory_test_support import known_cash_context
from inspect_client import OUT, write_json
from native_gameplay_probe import probe
from research_equipment_detail_full import NativeEquipmentDetail
from wire import read_octets


def reject(action):
    try:
        action()
    except ValueError:
        return
    raise AssertionError('Invalid or unknown equipment details accepted')


def response(inv, key, column):
    replies = inv.receive(ITEM_TIPS, struct.pack('>ii', column, key))
    assert len(replies) == 1 and replies[0][0] == ITEM_TIPS_REPLY
    body = replies[0][1]
    assert struct.unpack_from('>ii', body) == (column, key)
    detail, end = read_octets(body, 8)
    assert end == len(body)
    # Original SItemTips constructor, encoder and decoder.
    probe(0xd9c110, 0xe4e5c0, 0xe0a240, payload=body)
    return detail


def main():
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / 'state.sqlite3'
        store = AccountStore(path)
        role = store.create_role(1111, '装备详情', 12, 1010101)
        config = Inventory.prepare(store)
        context = known_cash_context(store, 1111, role['id'], balances=(27,0,0,0))
        inv = Inventory(store, 1111, role['id'], config, **context)
        inv.grant_item(40200, binding=1, quality=99)
        item = inv.immutable_snapshot().items[0]
        assert item.detail == EquipmentDetail(1, 1, 0, ((81, 20), (811, 20), (1231, 6)))
        assert item.binding == 1 and item.quality == 99
        assert item.condition.color_tier == 1
        try:
            item.detail.score = 1
        except FrozenInstanceError:
            pass
        else:
            raise AssertionError('Mutable cross-owner equipment detail')
        native = NativeEquipmentDetail(40200)
        with patch.object(Path, 'read_text', side_effect=AssertionError('hot-path config read')):
            parsed = native.parse(response(inv, item.id, 1))
        assert parsed['properties'] == list(item.detail.base_properties)
        assert (parsed['identified'], parsed['prefix_quality'], parsed['score'], parsed['color'],
                parsed['current'], parsed['maximum']) == (1, 1, 0, 1, 100, 100)
        reject(lambda: response(inv, item.id, 4))
        inv.equip(item.id, 0)
        parsed = native.parse(response(inv, item.id, 4))
        assert parsed['current'] == 100
        reject(lambda: response(inv, item.id, 1))
        with closing(store.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            inv.wear_equipment(db, item.id, 'detail-wear', 0, 17)
        assert native.parse(response(inv, item.id, 4))['current'] == 83
        assert inv.equipment_attributes()[2] == item.detail.base_properties
        reopened = Inventory(AccountStore(path), 1111, role['id'], config, **context)
        assert reopened.immutable_snapshot() == inv.immutable_snapshot()
        assert native.parse(response(reopened, item.id, 4))['current'] == 83

        # Complete six-slot baseline payloads, each consumed by its original
        # native parser with the original per-template thresholds.
        selected = {}
        for template in config.detail_rules.templates:
            kind = int(config.items[template]['itemtypeid'])
            selected.setdefault((kind >> 4) & 15, template)
        native_examples = []
        for slot, template in sorted(selected.items()):
            inv.grant_item(template)
            state = next(x for x in inv.snapshot()['items'] if x['template_id'] == template and x['equipment_slot'] is None)
            emu = NativeEquipmentDetail(template)
            got = emu.parse(response(inv, state['id'], 1))
            assert got['properties'] == sorted(state['detail'].base_properties)
            native_examples.append({'slot': slot, 'template': template, 'bytes': got['bytes_consumed']})
            del emu
        assert set(selected) == set(range(6))

        before = inv.immutable_snapshot()
        with closing(store.connect()) as db:
            db.execute('''CREATE TRIGGER fail_detail BEFORE INSERT ON inventory_equipment_details
                WHEN (SELECT template_id FROM inventory_items WHERE id=NEW.item_key)=40200
                BEGIN SELECT RAISE(ABORT,'detail save failed'); END''')
        try:
            with closing(store.connect()) as db, db:
                db.execute('BEGIN IMMEDIATE')
                inv.apply_settlement(db, AssetChange('atomic-detail', grants=((32000, 1), (40200, 1))))
        except sqlite3.IntegrityError as exc:
            assert 'detail save failed' in str(exc)
        else:
            raise AssertionError('Failed detail generation committed')
        assert inv.immutable_snapshot() == before
        with closing(store.connect()) as db, db:
            assert not db.execute("SELECT 1 FROM inventory_settlements WHERE settlement_id='atomic-detail'").fetchone()
            db.execute('DROP TRIGGER fail_detail')
            db.execute('BEGIN IMMEDIATE')
            legacy = db.execute('INSERT INTO inventory_items(role_id,template_id,quantity,slot) VALUES(?,?,1,?)',
                                (role['id'], 40200, 35)).lastrowid
            inv.initialize_equipment_condition(db, legacy, 42, 80, 1)
        before = inv.immutable_snapshot()
        assert next(x for x in before.items if x.id == legacy).detail is None
        reject(lambda: response(inv, legacy, 1))
        assert inv.immutable_snapshot() == before
        known = EquipmentDetail(1, 1, 0, ((81, 13), (811, 7), (1231, 4)))
        with closing(store.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            with patch.object(store, 'connect', side_effect=AssertionError('nested detail connection')):
                inv.initialize_equipment_detail(db, legacy, known)
            reject(lambda: inv.initialize_equipment_detail(db, legacy, known))
        assert native.parse(response(inv, legacy, 1))['properties'] == list(known.base_properties)
        inv.equip(legacy, 0)
        assert inv.equipment_attributes()[2] == known.base_properties
        other = store.create_role(1111, '他人详情', 12, 1010101)
        other_inv = Inventory(store, 1111, other['id'], config)
        reject(lambda: response(other_inv, legacy, 4))
        with closing(store.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            reject(lambda: other_inv.initialize_equipment_detail(db, legacy, known))
        # A nonwhite condition cannot be disguised with a white detail profile.
        with closing(store.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            mismatch = db.execute('INSERT INTO inventory_items(role_id,template_id,quantity,slot) VALUES(?,?,1,?)',
                                  (role['id'], 40200, 36)).lastrowid
            inv.initialize_equipment_condition(db, mismatch, 50, 100, 2)
            reject(lambda: inv.initialize_equipment_detail(db, mismatch, known))
            assert not db.execute('SELECT 1 FROM inventory_equipment_details WHERE item_key=?', (mismatch,)).fetchone()
        for args in ((True, 1, 0, ()), (1, 6, 0, ()), (1, 1, -1, ()),
                     (1, 1, 0, ((81, 1), (81, 2))), (1, 1, 0, ((81, True),))):
            reject(lambda args=args: EquipmentDetail(*args))
        inv.grant_item(40123)  # Known original god-weapon ID, not ordinary detail.
        god = next(x for x in inv.snapshot()['items'] if x['template_id'] == 40123)
        assert god.get('detail') is None
        reject(lambda: response(inv, god['id'], 1))
    result = {'passed': ['real ITEM_TIPS seam and original SItemTips codec',
        'original full EquipObject constructor/parser and property-map replacement',
        'six ordinary equipment slots with original per-template data',
        'identified/prefix/score/color/current/max remain independent',
        'food quality and binding do not become equipment prefix or score',
        'carried/equipped ownership and column checks',
        'current wear survives reopen and later tip refresh',
        'frozen known details and raw modifier attribute snapshot',
        'detail save failure rolls reward/items/condition/revision/receipt back',
        'old unknown instances stay unknown until explicit same-transaction initialization',
        'foreign/reset/color-conflict/malformed details rejected',
        'god-weapon branch withheld', 'no hot config reads or nested initialization connection'],
        'native_examples': native_examples, 'native_ui_tested': False,
        'advanced_equipment_features_restored': False, 'live_server_changed': False}
    write_json(OUT / 'evidence/equipment-details-verification.json', result)
    print('PASS:', ', '.join(result['passed']))


if __name__ == '__main__':
    main()
