"""Original use-item codec plus atomic pet heal/item consumption."""
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
import sqlite3
import struct
from accounts import AccountStore
from inventory import Inventory, USE_ITEM, REFRESH_PET, BAG_INFO
from native_gameplay_probe import probe
from native_inspect import u32
from inspect_client import OUT, write_json
from inventory_test_support import known_cash_context


def main():
    with TemporaryDirectory() as tmp:
        store=AccountStore(Path(tmp)/'state.sqlite3')
        role=store.create_role(1111,'宠物用药',12,1010101)
        store.inventory_config=Inventory.prepare(store)
        inv=Inventory(store,1111,role['id'],**known_cash_context(store,1111,role['id']))
        pet=inv.grant_pet(500001)
        inv.grant_item(32000,2)
        key=inv.snapshot()['items'][0]['id']
        body=struct.pack('>iiQ',key,1,pet)
        native,_=probe(0x8184f0,0xe4d740,0xd987a0,
                       {8:struct.pack('<iiQ',key,1,pet)})
        assert native == body
        def rejects(call):
            before=inv.snapshot()
            try:call()
            except ValueError:pass
            else:raise AssertionError('Invalid use accepted')
            assert inv.snapshot() == before
        rejects(lambda:inv.receive(USE_ITEM,body))  # Full HP never consumes.
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            inv.change_pet_growth(db,pet,'damage:1',0,'resources',(1,20))
        replies=inv.receive(USE_ITEM,body)
        assert [x[0] for x in replies] == [REFRESH_PET,BAG_INFO]
        _,decoded=probe(0xf9d7b0,0xf9d840,0xf9d880,payload=replies[0][1])
        assert struct.unpack_from('<i',decoded,8+0x40)[0] == 146
        probe(0xef6220,u32(0x2284234),u32(0x2284238),payload=replies[1][1])
        assert inv.snapshot()['items'][0]['quantity'] == 1
        rejects(lambda:inv.receive(USE_ITEM,body))
        other=store.create_role(1111,'他人宠物',12,1010101)
        other_inv=Inventory(store,1111,other['id'])
        foreign=other_inv.grant_pet(500001)
        rejects(lambda:inv.receive(USE_ITEM,struct.pack('>iiQ',key,1,foreign)))
        # Real DB failure after the resource write must undo resource and receipt.
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            inv.change_pet_growth(db,pet,'damage:2',2,'resources',(1,20))
        before=inv.snapshot()
        with closing(store.connect()) as db,db:
            db.executescript("CREATE TRIGGER fail_item_delete BEFORE DELETE ON inventory_items BEGIN SELECT RAISE(ABORT,'injected failure'); END;")
        try:inv.receive(USE_ITEM,body)
        except sqlite3.IntegrityError:pass
        else:raise AssertionError('Injected persistence failure did not run')
        assert inv.snapshot() == before
        with closing(store.connect()) as db,db:
            db.execute('DROP TRIGGER fail_item_delete')
        inv.receive(USE_ITEM,body)
        assert inv.snapshot()['items'] == []
        # Quality-bearing medicine must use persisted server metadata. At this
        # level max MP >201, so quality10 (600) differs observably from quality0.
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            old=inv.pet_progress(db,pet)
            xp=sum(inv.growth_rules.thresholds[x] for x in range(100))
            advanced=inv.change_pet_growth(db,pet,'level:100',old.state.version,'experience',xp)
            assert advanced.attributes.max_mp > 201
            inv.change_pet_growth(db,pet,'mp:drained',advanced.state.version,'resources',(advanced.state.hp,1))
        inv.grant_item(32001,1,quality=10)
        medicine=inv.snapshot()['items'][0]['id']
        inv.receive(USE_ITEM,struct.pack('>iiQ',medicine,1,pet))
        with closing(store.connect()) as db,db:
            db.execute('BEGIN')
            after=inv.pet_progress(db,pet)
            assert after.state.mp == after.attributes.max_mp
        reopened=Inventory(AccountStore(store.path),1111,role['id'],store.inventory_config)
        assert reopened.snapshot() == inv.snapshot()
    result={'passed':['native CUseItem request','native pet-resource and bag refresh decoders',
                      'resource restore and item deduction commit together','full HP does not consume',
                      'foreign pet rejected','real database abort rolls back resources and receipts',
                      'persisted quality drives formula instead of packet fields',
                      'reopen preserves healed resources and consumed stack'],
            'role_resource_handler_implemented':False,'native_ui_tested':False}
    write_json(OUT/'evidence/pet-consumable-verification.json',result)
    print('PASS:',', '.join(result['passed']))


if __name__=='__main__':main()
