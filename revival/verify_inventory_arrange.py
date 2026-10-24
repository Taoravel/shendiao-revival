"""Native bag arrangement retains binding and total item quantities."""
from pathlib import Path
from tempfile import TemporaryDirectory
import struct
from accounts import AccountStore
from inventory import Inventory
from native_gameplay_probe import probe
from inventory_test_support import known_cash_context


def main():
    with TemporaryDirectory() as tmp:
        store=AccountStore(Path(tmp)/'state.sqlite3')
        role=store.create_role(1111,'整理背包',12,1010101)
        inv=Inventory(store,1111,role['id'],Inventory.prepare(store),**known_cash_context(store,1111,role['id']))
        inv.grant_item(31000,9)
        key=inv.snapshot()['items'][0]['id']
        inv.move_item(key,7,4)
        inv.grant_item(31000,3,binding=1)
        body=struct.pack('>iQ',1,role['id'])
        native,_=probe(0x8184f0,0xe4b780,0xd8d2e0,{8:struct.pack('<i',1),0x10:struct.pack('<Q',role['id'])})
        assert body == native
        result=inv.receive(0xc03f4,body)
        assert result[0][0] == 0xc03f3
        items=inv.snapshot()['items']
        assert [(x['slot'],x['quantity'],x['binding']) for x in items] == [(0,9,0),(1,3,1)]
        assert items[0]['id'] == key
        assert Inventory(store,1111,role['id'],Inventory.prepare(store)).snapshot()['items'] == items
    print('PASS native arrange request, merge count conservation, binding and stable keys')


if __name__=='__main__':main()
