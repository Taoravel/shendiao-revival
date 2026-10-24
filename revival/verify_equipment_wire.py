"""Wear/remove native messages and durable container snapshots."""
from pathlib import Path
from tempfile import TemporaryDirectory
import struct
from accounts import AccountStore
from inventory import Inventory
from native_gameplay_probe import probe
from native_inspect import u32
from inspect_client import OUT, write_json
from inventory_test_support import known_cash_context


def main():
    with TemporaryDirectory() as tmp:
        store = AccountStore(Path(tmp) / 'state.sqlite3')
        role = store.create_role(1111, '装备恢复', 12, 1010101)
        store.inventory_config = Inventory.prepare(store)
        inv = Inventory(store, 1111, role['id'],**known_cash_context(store,1111,role['id']))
        inv.grant_item(40200)
        key = inv.snapshot()['items'][0]['id']
        replies = inv.receive(0xc03f5, struct.pack('>ii', key, 0))
        assert [struct.unpack_from('>i', b)[0] for k,b in replies] == [1,4]
        for k,b in replies:
            assert k == 0xc03f3
            probe(0xef6220, u32(0x2284234), u32(0x2284238), payload=b)
        assert inv.snapshot()['items'][0]['equipment_slot'] == 0
        assert Inventory(store,1111,role['id']).snapshot() == inv.snapshot()
        inv.receive(0xc03f6,struct.pack('>ii',key,3))
        assert inv.snapshot()['items'][0]['slot'] == 3
        inv.grant_item(40200)
        keys = [x['id'] for x in inv.snapshot()['items']]
        inv.equip(keys[0],0)
        inv.equip(keys[1],0)
        assert sum(x['equipment_slot'] == 0 for x in inv.snapshot()['items']) == 1
        assert sum(x['quantity'] for x in inv.snapshot()['items']) == 2
        attributes = inv.equipment_attributes()
        assert attributes[2] == ((81, 20), (811, 20), (1231, 6))
        inv.grant_item(40100)
        incompatible = next(x['id'] for x in inv.snapshot()['items'] if x['template_id'] == 40100)
        before = inv.snapshot()
        try:
            inv.equip(incompatible, 0)
        except ValueError as error:
            assert 'character' in str(error)
        else:
            raise AssertionError('Character-incompatible weapon accepted')
        assert inv.snapshot() == before
    result = {'passed': ['equipment request handler', 'native carried/equipment bag reply decoders',
                         'wear/remove persistence', 'replacement preserves item count',
                         'character-incompatible weapon rejected without mutation',
                         'original baseEffect attribute IDs and values snapshot'],
              'bag_type_evidence': 'native CGetBagInfo callsite 0x1103dff uses 4',
              'native_ui_verified': False,
              'eligibility_verification': 'equipment-eligibility-verification.json',
              'pending': ['character stat refresh and live deployment acceptance',
                          'enhancement and gem attributes', 'client display acceptance']}
    write_json(OUT / 'evidence/equipment-wire-verification.json', result)
    print('PASS:', ', '.join(result['passed']))


if __name__ == '__main__':
    main()
