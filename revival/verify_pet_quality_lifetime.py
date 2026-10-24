"""Quality comes from the owned instance, never from the native request."""
from pathlib import Path
from tempfile import TemporaryDirectory
from contextlib import closing
import struct
import sqlite3
from unittest.mock import patch

from accounts import AccountStore
from inventory import Inventory,REFRESH_PET
from inventory_test_support import known_cash_context
from native_gameplay_probe import probe
from inspect_client import OUT,write_json


def refused(action,errors=(ValueError,)):
    try:action()
    except errors:return
    raise AssertionError('Invalid quality lifetime meal accepted')


def main():
    with TemporaryDirectory() as tmp:
        store=AccountStore(Path(tmp)/'quality-lifetime.sqlite3')
        role=store.create_role(1111,'荷叶延寿',12,1010101)
        config=Inventory.prepare(store)
        inv=Inventory(store,1111,role['id'],config,**known_cash_context(store,1111,role['id']))
        pet=inv.grant_pet(500001);inv.grant_item(32007,2,quality=95)
        before=inv.immutable_snapshot();key=before.items[0].id
        assert len(before.items)==2 and all(x.quantity==1 for x in before.items)
        body=struct.pack('>iiQ',key,1,pet)
        paid_body=body
        replies=inv.receive_pet_consumable(body,inv.epoch,'quality-lifetime:95')
        after=inv.immutable_snapshot()
        assert after.pets[0].care.lifetime==6047 and after.items[0].quantity==1
        assert after.pets[0].progress==before.pets[0].progress
        assert after.pets[0].care.loyalty==100
        _,raw=probe(0xf9d7b0,0xf9d840,0xf9d880,payload=next(b for k,b in replies if k==REFRESH_PET))
        assert struct.unpack_from('<i',raw,8+0xb0)[0]==6047
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');care=inv.read_pet_state(db,pet).care
            inv.change_pet_care(db,pet,'quality-lifetime:defeat',care.version,'defeat',1)
        before=inv.immutable_snapshot();seen=[]
        def hook(db,inventory,snapshot,*,replayed):seen.append(replayed)
        inv.receive_pet_consumable(body,inv.epoch,'quality-lifetime:95',None,hook)
        assert seen==[True] and inv.immutable_snapshot()==before
        assert before.pets[0].care.lifetime==5997
        key=inv.immutable_snapshot().items[0].id;body=struct.pack('>iiQ',key,1,pet)
        inv.receive_pet_consumable(body,inv.epoch,'quality-lifetime:95-new',None,hook)
        assert seen==[True,False] and inv.immutable_snapshot().pets[0].care.lifetime==6044
        before=inv.immutable_snapshot()
        inv.receive_pet_consumable(paid_body,inv.epoch,'quality-lifetime:95')
        assert inv.immutable_snapshot()==before and not before.items
        inv.grant_item(32007,6,quality=96)
        key=inv.immutable_snapshot().items[0].id;body=struct.pack('>iiQ',key,1,pet)
        with patch.object(Path,'read_text',side_effect=AssertionError('Quality food hot file read')):
            inv.receive_pet_consumable(body,inv.epoch,'quality-lifetime:96')
        assert inv.immutable_snapshot().pets[0].care.lifetime==6092
        key=next(x.id for x in inv.immutable_snapshot().items if x.quality==96)
        body=struct.pack('>iiQ',key,1,pet)
        for quality in (None,0,1):
            inv.grant_item(32007,1,quality=quality)
            bad=next(x.id for x in inv.immutable_snapshot().items if x.quality==quality)
            before=inv.immutable_snapshot()
            refused(lambda:inv.receive_pet_consumable(struct.pack('>iiQ',bad,1,pet),inv.epoch,'quality-lifetime:bad:'+str(quality)))
            assert inv.immutable_snapshot()==before
        before=inv.immutable_snapshot()
        for invalid in ((32007,True),(32007,-1),(32007,2**31),(32007,None),[32007,95],(32004,95)):
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE');care=inv.read_pet_state(db,pet).care
                refused(lambda:inv.change_pet_care(db,pet,'quality-lifetime:invalid',care.version,'feed_lifetime_quality',invalid))
            assert inv.immutable_snapshot()==before
        with closing(store.connect()) as db,db:
            db.execute("CREATE TRIGGER fail_quality_meal BEFORE INSERT ON inventory_pet_care_receipts BEGIN SELECT RAISE(ABORT,'quality receipt failure'); END")
        refused(lambda:inv.receive_pet_consumable(body,inv.epoch,'quality-lifetime:failed'),(sqlite3.IntegrityError,))
        assert inv.immutable_snapshot()==before
        with closing(store.connect()) as db,db:db.execute('DROP TRIGGER fail_quality_meal')
        inv.receive_pet_consumable(body,inv.epoch,'quality-lifetime:failed')
        assert inv.immutable_snapshot().pets[0].care.lifetime==6140
        key=next(x.id for x in inv.immutable_snapshot().items if x.quality==96)
        body=struct.pack('>iiQ',key,1,pet)
        inv.grant_item(32000)
        bad=next(x.id for x in inv.immutable_snapshot().items if x.template_id==32000)
        with closing(store.connect()) as db,db:db.execute('UPDATE inventory_items SET quantity=? WHERE id=?',(2**31,bad))
        before=inv.immutable_snapshot()
        refused(lambda:inv.receive_pet_consumable(body,inv.epoch,'quality-lifetime:bag'),(struct.error,))
        assert inv.immutable_snapshot()==before
        with closing(store.connect()) as db,db:db.execute('UPDATE inventory_items SET quantity=1 WHERE id=?',(bad,))
        inv.receive_pet_consumable(body,inv.epoch,'quality-lifetime:bag')
        assert inv.immutable_snapshot().pets[0].care.lifetime==6188
        key=next(x.id for x in inv.immutable_snapshot().items if x.quality==96)
        body=struct.pack('>iiQ',key,1,pet)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');p=inv.pet_progress(db,pet)
            inv.change_pet_growth(db,pet,'quality-lifetime:dead',p.state.version,'resources',(0,0))
            limit=db.execute('INSERT INTO inventory_pets(role_id,template_id,name) VALUES(?,?,?)',
                (role['id'],500001,'寿命近界')).lastrowid
            inv.initialize_pet_care(db,limit,1,100,2**31-21)
        before=inv.immutable_snapshot()
        refused(lambda:inv.receive_pet_consumable(struct.pack('>iiQ',key,1,limit),inv.epoch,'quality-lifetime:overflow'))
        assert inv.immutable_snapshot()==before
        inv.receive_pet_consumable(body,inv.epoch,'quality-lifetime:dead-food')
        current=inv.immutable_snapshot()
        assert current.pets[0].care.lifetime==6236 and current.pets[0].progress==before.pets[0].progress
        before=current
        refused(lambda:inv.receive_pet_consumable(body+struct.pack('>i',999),inv.epoch,'quality-lifetime:client-quality'))
        refused(lambda:inv.receive_pet_consumable(body,inv.epoch+1,'quality-lifetime:stale'))
        assert inv.immutable_snapshot()==before
        token='品质延寿:00007';store.inventory_config=config
        with closing(store.connect()) as db,db:db.execute('UPDATE role_leases SET epoch=? WHERE role_id=?',(token,role['id']))
        active=Inventory(store.leased(1111,role['id'],token),1111,role['id'],config,epoch=token,currency_rules=inv.currency_rules)
        active.receive_pet_consumable(body,token,'quality-lifetime:dead-food')
        assert active.immutable_snapshot()==before
        assert Inventory(AccountStore(store.path),1111,role['id'],config).immutable_snapshot()==before
    report={'passed':['owned32007 quality95 adds47 lifetime and consumes one; original native decoder reads6047',
        'original maxNum1 preserves separate instances; later defeat remains5997 on paid retry; a fresh other instance adds47; deleted key still replays current',
        'quality96 adds48 from owned instance; unknown/0/1 quality has no spend; bool/negative/overflow/list/unsafe template rejects',
        'real care receipt abort and late native bag overflow roll back care/item/command; same failed ID later succeeds',
        'signed32 lifetime overflow refuses; HP0 remains0; hot file reads forbidden; native extra quality and old lease reject',
        'actual opaque LeasedAccounts current replay and reopen preserve exact snapshot'],
        'source_status':'original0.5 quality coefficient client_verified; service truncation designed',
        'database':'disposable','live_server_changed':False,'native_gui_verified':False}
    write_json(OUT/'evidence/pet-quality-lifetime-verification.json',report)
    print('PASS',', '.join(report['passed']))


if __name__=='__main__':main()
