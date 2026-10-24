"""Nonempty inventory protocol through domain receive and original native codecs."""
from pathlib import Path
from tempfile import TemporaryDirectory
import struct
from accounts import AccountStore
from inventory import Inventory, QUERY_BAG, BAG_INFO, MOVE_ITEM
from native_gameplay_probe import probe
from native_inspect import u32
from inspect_client import OUT, write_json
from inventory_test_support import known_cash_context


def main():
    with TemporaryDirectory() as tmp:
        store = AccountStore(Path(tmp) / 'state.sqlite3')
        role = store.create_role(1111, '物品同步', 12, 1010101)
        inv = Inventory(store, 1111, role['id'], Inventory.prepare(store),
                        **known_cash_context(store,1111,role['id']))
        inv.grant_item(31000, 7)
        key = inv.snapshot()['items'][0]['id']
        # Native offsets: +4 template, +8 flags, +c instance key,
        # +10 position, +18 time, +20 quantity. Consumer regression separately
        # verifies nonzero positions and binding, not just the zero-slot case.
        native, decoded = probe(0x8184f0, 0x822040, 0x81a590, {
            4: struct.pack('<i', 31000), 8: struct.pack('<i', 0),
            12: struct.pack('<i', key), 0x20: struct.pack('<i', 7)})
        assert struct.unpack_from('<i', decoded, 12)[0] == key
        assert struct.unpack_from('<i', decoded, 0x20)[0] == 7
        response = inv.receive(QUERY_BAG, struct.pack('>iQ', 1, role['id']))
        expected = struct.pack('>iQi', 1, 0, 40) + b'\1' + native + b'\0'
        assert response == [(BAG_INFO, expected)]
        probe(0xef6220, u32(0x2284234), u32(0x2284238), payload=expected)
        def request(source, source_slot, target_slot, count):
            result = inv.receive(MOVE_ITEM, struct.pack('>6iq', 1, source, source_slot, 1, target_slot, count, -1))
            assert result[0][0] == BAG_INFO
            probe(0xef6220, u32(0x2284234), u32(0x2284238), payload=result[0][1])
        request(key, 0, 5, 3)
        state = inv.snapshot()
        assert [(x['slot'], x['quantity']) for x in state['items']] == [(0, 4), (5, 3)]
        split = state['items'][1]['id']
        request(split, 5, 0, 0)
        assert [(x['slot'], x['quantity']) for x in inv.snapshot()['items']] == [(0, 7)]
        request(key, 0, 9, 0)
        assert inv.snapshot()['items'][0]['slot'] == 9
        inv.grant_item(40100)
        weapon = next(x for x in inv.snapshot()['items'] if x['template_id'] == 40100)
        request(key, 9, weapon['slot'], 0)
        assert next(x for x in inv.snapshot()['items'] if x['id'] == weapon['id'])['slot'] == 9
        before = inv.snapshot()
        try:
            inv.move_item(key, 4, 99)
        except ValueError:
            pass
        else:
            raise AssertionError('Overdraw move accepted')
        assert inv.snapshot() == before
        other = store.create_role(1111, '另个背包', 12, 1010101)
        foreign = Inventory(store, 1111, other['id'], store.inventory_config if hasattr(store, 'inventory_config') else Inventory.prepare(store))
        try:
            foreign.move_item(key, 0)
        except ValueError:
            pass
        else:
            raise AssertionError('Cross-role move accepted')
        assert inv.snapshot() == before
        reopened = Inventory(store, 1111, role['id'], Inventory.prepare(store))
        assert reopened.snapshot() == before
    result = {'passed': ['nonempty production bag matches original item serializer',
                         'original full bag decoder accepts nonempty and multi-item replies',
                         'split conserves quantity', 'merge conserves quantity', 'whole-stack move',
                         'different-template swap', 'overdraw rollback', 'cross-role refusal',
                         'reopen keeps positions and instance keys'],
              'item_field_semantics': 'template/key plus position and binding confirmed through native consumers; quantity layout verified, UI pending',
              'move_business_rules': 'local restoration semantics; count zero means whole stack',
              'native_ui_tested': False, 'live_gateway_restarted': False}
    write_json(OUT / 'evidence/inventory-wire-verification.json', result)
    print('PASS:', ', '.join(result['passed']))


if __name__ == '__main__':
    main()
