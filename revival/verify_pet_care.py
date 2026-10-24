"""Native pet food request, versioned care and atomic consume/rollback."""
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
import sqlite3
import struct
from accounts import AccountStore
from inventory import Inventory, USE_ITEM, REFRESH_PET, BAG_INFO
from native_gameplay_probe import probe
from inspect_client import OUT, write_json
from inventory_test_support import known_cash_context


def main():
    with TemporaryDirectory() as tmp:
        store=AccountStore(Path(tmp)/'state.sqlite3')
        role=store.create_role(1111,'宠物喂养',12,1010101)
        config=Inventory.prepare(store)
        inv=Inventory(store,1111,role['id'],config,**known_cash_context(store,1111,role['id']))
        pet=inv.grant_pet(500001)
        inv.grant_item(31000,6)
        key=inv.snapshot()['items'][0]['id']
        def state(): return next(p for p in inv.snapshot()['pets'] if p['id']==pet)['care']
        initial=state()
        assert (initial.grade,initial.loyalty,initial.lifetime)==(1,100,6000)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            damaged=inv.change_pet_care(db,pet,'battle:1:death',0,'defeat',1)
            assert (damaged.loyalty,damaged.lifetime)==(80,5950)
            assert inv.change_pet_care(db,pet,'battle:1:death',0,'defeat',1)==damaged
        body=struct.pack('>iiQ',key,1,pet)
        replies=inv.receive(USE_ITEM,body)
        assert [x[0] for x in replies]==[REFRESH_PET,BAG_INFO]
        assert (state().loyalty,state().lifetime)==(85,5950)
        # Full production pet record, including growth and care, is accepted by
        # the original decoder; fields are also inspected at the known offsets.
        _,raw=probe(0xf9d7b0,0xf9d840,0xf9d880,payload=replies[0][1])
        assert struct.unpack_from('<i',raw,8+0x90)[0]==85
        assert struct.unpack_from('<i',raw,8+0xb0)[0]==5950
        before=inv.snapshot()
        with closing(store.connect()) as db,db:
            db.executescript("CREATE TRIGGER fail_feed BEFORE UPDATE OF quantity ON inventory_items BEGIN SELECT RAISE(ABORT,'feed failure'); END;")
        try:inv.receive(USE_ITEM,body)
        except sqlite3.IntegrityError:pass
        else:raise AssertionError('Injected food deduction failure did not execute')
        assert inv.snapshot()==before
        with closing(store.connect()) as db,db:db.execute('DROP TRIGGER fail_feed')
        for _ in range(3):inv.receive(USE_ITEM,body)
        assert state().loyalty==100
        before=inv.snapshot()
        try:inv.receive(USE_ITEM,body)
        except ValueError:pass
        else:raise AssertionError('Food consumed at full loyalty')
        assert inv.snapshot()==before
        # Exact native codec comparison independently checks care-only record.
        from inventory import pet_record
        wire=pet_record({'id':pet,'template_id':500001,'name':'','care':state()})
        expected,_=probe(0xf89ba0,0xf5df70,0xf5f1f0,
            {4:struct.pack('<i',500001),8:struct.pack('<i',pet),
             0x3c:struct.pack('<i',1),0x90:struct.pack('<i',100),0xb0:struct.pack('<i',5950)})
        assert wire==expected
        # Explicit legacy import covers all six original caps. A plain old pet
        # is read without silently fabricating grade, loyalty or lifetime.
        legacy_role=store.create_role(1111,'既有宠物',12,1010101)
        legacy_inv=Inventory(store,1111,legacy_role['id'],config,**known_cash_context(store,1111,legacy_role['id']))
        legacy_inv.grant_item(31001,6)
        food=legacy_inv.snapshot()['items'][0]['id']
        for grade,cap in ((1,100),(2,100),(3,125),(4,200),(5,300),(6,400)):
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                other=db.execute('INSERT INTO inventory_pets(role_id,template_id,name) VALUES(?,?,?)',
                    (legacy_role['id'],500001,'既有宠')).lastrowid
            old=next(p for p in legacy_inv.snapshot()['pets'] if p['id']==other)
            assert 'care' not in old
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                legacy_inv.initialize_pet_care(db,other,grade,cap-3,6000)
                try:legacy_inv.initialize_pet_care(db,other,grade,cap,6000)
                except ValueError:pass
                else:raise AssertionError('Care reroll allowed')
            result=legacy_inv.receive(USE_ITEM,struct.pack('>iiQ',food,1,other))
            _,raw=probe(0xf9d7b0,0xf9d840,0xf9d880,payload=result[0][1])
            assert struct.unpack_from('<i',raw,8+0x90)[0]==cap
            assert next(p for p in legacy_inv.snapshot()['pets'] if p['id']==other)['care'].loyalty==cap
        assert legacy_inv.snapshot()['items']==[]
        before=inv.snapshot()
        for operation in ('foreign','stale','conflict'):
            try:
                with closing(store.connect()) as db,db:
                    db.execute('BEGIN IMMEDIATE')
                    if operation=='foreign':
                        inv.change_pet_care(db,other,'foreign',0,'defeat',1)
                    elif operation=='stale':
                        inv.change_pet_care(db,pet,'stale',0,'defeat',1)
                    else:
                        inv.change_pet_care(db,pet,'battle:1:death',0,'feed',31000)
            except ValueError:pass
            else:raise AssertionError(f'Invalid {operation} care settlement accepted')
            assert inv.snapshot()==before
        reopened=Inventory(AccountStore(store.path),1111,role['id'],config)
        assert reopened.snapshot()==inv.snapshot()
        # Defeat floors at zero, and cannot affect another role's pet.
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            current=state()
            for i in range(120):
                current=inv.change_pet_care(db,pet,f'battle:floor:{i}',current.version,'defeat',1)
            lost=current
            assert (lost.loyalty,lost.lifetime)==(0,0)
        before=inv.snapshot()
        try:inv.fight_pet(pet)
        except ValueError:pass
        else:raise AssertionError('Exhausted pet selected to fight')
        assert inv.snapshot()==before
    result={'passed':['food raises loyalty and consumes atomically','full loyalty refuses without consumption',
        'original six-grade caps loaded','original care field bytes and refresh decoder',
        'real DB abort rolls back care item receipt and revision','care replay does not repeat defeat loss',
        'explicit legacy imports clamp food at each of six original caps',
        'legacy read leaves unknown care untouched','foreign stale and conflicting settlements rejected',
        'care initialization cannot reroll instances','reopen preserves care',
        'defeat floors at zero and exhausted pet cannot fight'],
        'native_ui_tested':False,'battle_defeat_event_integrated':False,
        'initial_grade_provenance':'designed','death_loss_provenance':'guide_supported_historical'}
    write_json(OUT/'evidence/pet-care-verification.json',result)
    print('PASS:',', '.join(result['passed']))


if __name__=='__main__':main()
