"""Gameplay regression through the same Session.feed interface as the gateway."""
from pathlib import Path
from tempfile import TemporaryDirectory
import struct
from accounts import AccountStore
from gateway import Session
from wire import frame, FrameReader
from inventory import Inventory, pet_record
from native_gameplay_probe import probe
from native_inspect import u32
from inspect_client import OUT, write_json
from inventory_test_support import known_cash_context


def main():
    with TemporaryDirectory() as tmp:
        accounts = AccountStore(Path(tmp) / 'accounts.sqlite3')
        role = accounts.create_role(1111, '行囊测试', 12, 1010101)
        session = Session(accounts)
        session.account_id = 1111
        session.state = 'roles'
        session.feed(frame(0xc0005, struct.pack('>Q', role['id']) + b'\0\0'))
        # The native bag reply also replaces cash. This legacy Session fixture
        # needs the same explicit wallet authority as the production role owner.
        session.inventory=Inventory(accounts,1111,role['id'],Inventory.prepare(accounts),
            **known_cash_context(accounts,1111,role['id']))
        def request(kind, body):
            return FrameReader().feed(b''.join(session.feed(frame(kind, body))))
        assert request(0xc03f2, struct.pack('>iQ', 1, role['id'])) == [
            (0xc03f3, bytes.fromhex('000000010000000000000000000000280000'))], 'Bag query ignored'
        assert request(0xc07de, struct.pack('>iQ', 1, role['id'])) == [
            (0xc07df, bytes.fromhex('00000001000000000600'))], 'Pet column query ignored'
        inv = session.inventory
        inv.grant_item(31000, 100)
        assert [x['quantity'] for x in inv.snapshot()['items']] == [99, 1]
        key = inv.snapshot()['items'][0]['id']
        inv.consume_item(key, 98)
        assert inv.snapshot()['items'][0]['quantity'] == 1
        def rejects(call):
            try:
                call()
            except ValueError:
                return
            raise AssertionError('Invalid operation accepted')
        rejects(lambda: inv.consume_item(key, -1))
        rejects(lambda: Inventory(accounts, 2222, role['id']))
        before = inv.snapshot()
        rejects(lambda: inv.grant_item(31000, 99 * 41))
        assert inv.snapshot() == before, 'Full bag grant must roll back all stack changes'
        other = accounts.create_role(1111, '其他角色', 12, 1010101)
        other_inventory = Inventory(accounts, 1111, other['id'])
        assert other_inventory.snapshot()['items'] == []
        rejects(lambda: other_inventory.consume_item(key))
        other_inventory.grant_item(40200)
        weapon = other_inventory.snapshot()['items'][0]['id']
        rejects(lambda: other_inventory.equip(weapon, 2))
        other_inventory.equip(weapon, 0)
        assert other_inventory.snapshot()['items'][0]['equipment_slot'] == 0
        rejects(lambda: other_inventory.consume_item(weapon))
        other_inventory.unequip(weapon)
        assert other_inventory.snapshot()['items'][0]['equipment_slot'] is None
        other_inventory.grant_item(37001)
        paper = next(x['id'] for x in other_inventory.snapshot()['items'] if x['template_id'] == 37001)
        rejects(lambda: other_inventory.equip(paper, 0))
        pet = inv.grant_pet(500001)
        rename = struct.pack('>i', pet) + b'\6' + '灰小狗'.encode('utf-16le')
        reply = request(0xc07e2, rename)
        assert reply == [(0xc07e3, struct.pack('>Qi', role['id'], pet) + rename[4:])]
        probe(0xdbf7f0, 0xe53d10, 0xf77860, payload=reply[0][1])
        rejects(lambda: inv.receive(0xc07d8, struct.pack('>i', pet)))  # original uselevel=5
        assert request(0xc07d8, struct.pack('>i', pet)) == []
        assert session.events[-1]['event'] == 'inventory_request_rejected'
        inv.fight_pet(pet)
        assert inv.snapshot()['pets'][0]['fighting'] == 1
        assert request(0xc07da, b'') == [(0xc07db, b'')]
        reopened = Inventory(AccountStore(accounts.path), 1111, role['id'])
        assert reopened.snapshot() == inv.snapshot()
        response = request(0xc07de, struct.pack('>iQ', 1, role['id']))[0][1]
        probe(0xf20220, u32(0x2284dc4), u32(0x2284dc8), payload=response)
        rejects(lambda: inv.receive(0xc07de, struct.pack('>iQ', 1, other['id'])))
        rejects(lambda: inv.receive(0xc07e2, rename + b'\0'))
        assert request(0xc03f2, struct.pack('>iQ', 1, role['id']))[0][0] == 0xc03f3
        assert request(0xc03f2, struct.pack('>iQ', 2, role['id'])) == []
        assert session.events[-1]['event'] == 'inventory_protocol_pending'
        # Independent original codecs verify both confirmed container envelopes.
        bag, _ = probe(0xef6220, u32(0x2284234), u32(0x2284238),
                       {8: struct.pack('<i', 1), 0x20: struct.pack('<i', 40)})
        assert bag == bytes.fromhex('000000010000000000000000000000280000')
        sample = pet_record({'id': 7, 'template_id': 500001, 'name': '召唤测试'})
        _, native = probe(0xf89ba0, 0xf5df70, 0xf5f1f0, payload=sample)
        assert struct.unpack_from('<ii', native, 4) == (500001, 7)
        rejects(lambda: probe(0xf89ba0, 0xf5df70, 0xf5f1f0, payload=sample[:-1]))
    result = {'passed': ['session bag query regression', 'session pet query',
               'original native empty bag serializer comparison', 'native nonempty pet column decoder',
               'native pet rename decoder', 'stack limits', 'partial consume',
               'failed grant transaction rollback', 'cross-role isolation',
               'reopen persistence', 'pet rename persistence', 'pet fight/rest persistence',
               'equipment storage wear/remove', 'equipment slot check', 'equipment paper rejection',
               'original pet uselevel restriction', 'malformed payload rejection'],
              'native_client_ui_tested': False, 'live_gateway_restarted': False,
              'pending': ['native UI confirmation of item position/quantity semantics', 'equipment client protocol integration',
                          'item effects', 'pet growth attributes and battle integration', 'unified reward transaction']}
    write_json(OUT / 'evidence/inventory-verification.json', result)
    print('PASS:', ', '.join(result['passed']))


if __name__ == '__main__':
    main()
