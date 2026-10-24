"""Original fixed lifetime food uses the same admitted pet-item transaction."""
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
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
    raise AssertionError('Invalid lifetime food command accepted')


def main():
    with TemporaryDirectory() as tmp:
        store=AccountStore(Path(tmp)/'lifetime.sqlite3')
        role=store.create_role(1111,'宠物延寿',12,1010101)
        config=Inventory.prepare(store)
        inv=Inventory(store,1111,role['id'],config,**known_cash_context(store,1111,role['id']))
        pet=inv.grant_pet(500001);inv.grant_item(32036,2)
        before=inv.immutable_snapshot();key=before.items[0].id
        body=struct.pack('>iiQ',key,1,pet)
        replies=inv.receive_pet_consumable(body,inv.epoch,'lifetime:fixed')
        after=inv.immutable_snapshot()
        assert after.pets[0].care.lifetime==7000 and after.items[0].quantity==1
        assert after.pets[0].care.loyalty==100 and after.pets[0].care.grade==1
        assert after.pets[0].progress==before.pets[0].progress
        _,raw=probe(0xf9d7b0,0xf9d840,0xf9d880,payload=next(b for k,b in replies if k==REFRESH_PET))
        assert struct.unpack_from('<i',raw,8+0xb0)[0]==7000
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            care=inv.read_pet_state(db,pet).care
            inv.change_pet_care(db,pet,'lifetime:later-defeat',care.version,'defeat',1)
        before=inv.immutable_snapshot();flags=[]
        def hook(db,inventory,snapshot,*,replayed):flags.append(replayed)
        inv.receive_pet_consumable(body,inv.epoch,'lifetime:fixed',None,hook)
        assert inv.immutable_snapshot()==before and flags==[True]
        assert before.pets[0].care.lifetime==6950
        inv.receive_pet_consumable(body,inv.epoch,'lifetime:new',None,hook)
        assert flags==[True,False] and inv.immutable_snapshot().pets[0].care.lifetime==7950
        assert not inv.immutable_snapshot().items
        before=inv.immutable_snapshot()
        inv.receive_pet_consumable(body,inv.epoch,'lifetime:fixed')
        assert inv.immutable_snapshot()==before
        # Real writes fail at each stage; the same admitted ID stays unspent.
        inv.grant_item(32036,6);key=inv.immutable_snapshot().items[0].id
        body=struct.pack('>iiQ',key,1,pet)
        for table,operation in (('inventory_pet_care','UPDATE'),('inventory_items','UPDATE'),
                ('inventory_pet_care_receipts','INSERT'),('inventory_pet_consumable_commands','INSERT')):
            before=inv.immutable_snapshot()
            with closing(store.connect()) as db,db:
                db.execute(f"CREATE TRIGGER fail_lifetime BEFORE {operation} ON {table} BEGIN SELECT RAISE(ABORT,'lifetime failure'); END")
            refused(lambda:inv.receive_pet_consumable(body,inv.epoch,'lifetime:failed'),(sqlite3.IntegrityError,))
            assert inv.immutable_snapshot()==before
            with closing(store.connect()) as db,db:db.execute('DROP TRIGGER fail_lifetime')
        inv.receive_pet_consumable(body,inv.epoch,'lifetime:failed')
        assert inv.immutable_snapshot().pets[0].care.lifetime==8950
        before=inv.immutable_snapshot()
        def fail_hook(db,inventory,snapshot,*,replayed):raise ValueError('outer callback failure')
        refused(lambda:inv.receive_pet_consumable(body,inv.epoch,'lifetime:callback',None,fail_hook))
        assert inv.immutable_snapshot()==before
        inv.grant_item(32000,1)
        bad=next(x.id for x in inv.immutable_snapshot().items if x.template_id==32000)
        with closing(store.connect()) as db,db:db.execute('UPDATE inventory_items SET quantity=? WHERE id=?',(2**31,bad))
        before=inv.immutable_snapshot()
        refused(lambda:inv.receive_pet_consumable(body,inv.epoch,'lifetime:bag'),(struct.error,))
        assert inv.immutable_snapshot()==before
        with closing(store.connect()) as db,db:db.execute('UPDATE inventory_items SET quantity=1 WHERE id=?',(bad,))
        inv.receive_pet_consumable(body,inv.epoch,'lifetime:bag')
        assert inv.immutable_snapshot().pets[0].care.lifetime==9950
        # One explicit known ordinary import at lifetime0 and another near the
        # representation ceiling exercise real item effects without resetting.
        legacy=[]
        for name,lifetime in (('原寿命零',0),('原寿命将满',2**31-501)):
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                old=db.execute('INSERT INTO inventory_pets(role_id,template_id,name) VALUES(?,?,?)',
                    (role['id'],500001,name)).lastrowid
                inv.initialize_pet_care(db,old,1,100,lifetime)
            legacy.append(old)
        zero,limit=legacy
        before=inv.immutable_snapshot()
        refused(lambda:inv.receive_pet_consumable(struct.pack('>iiQ',key,1,limit),inv.epoch,'lifetime:overflow'))
        assert inv.immutable_snapshot()==before
        with patch.object(Path,'read_text',side_effect=AssertionError('Lifetime hot file read')):
            inv.receive_pet_consumable(struct.pack('>iiQ',key,1,zero),inv.epoch,'lifetime:zero')
        assert next(p.care.lifetime for p in inv.immutable_snapshot().pets if p.id==zero)==1000
        # Exhausted lifetime recovery does not resurrect HP0 or reroll growth.
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');progress=inv.pet_progress(db,pet)
            inv.change_pet_growth(db,pet,'lifetime:dead',progress.state.version,'resources',(0,0))
        before=inv.immutable_snapshot()
        inv.receive_pet_consumable(body,inv.epoch,'lifetime:dead-food')
        current=inv.immutable_snapshot()
        assert current.pets[0].progress==before.pets[0].progress and current.pets[0].progress.state.hp==0
        assert current.pets[0].care.lifetime==10950
        other=store.create_role(1111,'未知钱包',12,1010101)
        epoch=store.acquire_lease(1111,other['id'])
        unknown=Inventory(store,1111,other['id'],config,epoch=epoch,currency_rules=inv.currency_rules)
        other_pet=unknown.grant_pet(500001);unknown.grant_item(32036,2)
        other_key=unknown.immutable_snapshot().items[0].id;before_other=unknown.immutable_snapshot()
        refused(lambda:unknown.receive_pet_consumable(struct.pack('>iiQ',other_key,1,other_pet),epoch,'lifetime:no-wallet'))
        assert unknown.immutable_snapshot()==before_other
        before=inv.immutable_snapshot()
        refused(lambda:inv.receive_pet_consumable(struct.pack('>iiQ',key,1,other_pet),inv.epoch,'lifetime:foreign'))
        refused(lambda:inv.receive_pet_consumable(body,inv.epoch+1,'lifetime:stale'))
        refused(lambda:inv.receive_pet_consumable(body[:-1],inv.epoch,'lifetime:bad'))
        assert inv.immutable_snapshot()==before
        token='寿命道具:00007';store.inventory_config=config
        with closing(store.connect()) as db,db:db.execute('UPDATE role_leases SET epoch=? WHERE role_id=?',(token,role['id']))
        active=Inventory(store.leased(1111,role['id'],token),1111,role['id'],config,epoch=token,currency_rules=inv.currency_rules)
        active.receive_pet_consumable(body,token,'lifetime:dead-food')
        assert active.immutable_snapshot()==before
        assert Inventory(AccountStore(store.path),1111,role['id'],config).immutable_snapshot()==before
    report={'passed':['actual32036 consumes one and adds1000 lifetime beyond original starting6000',
        'original full pet decoder reads7000; growth/resources/blood/loyalty unchanged',
        'later defeat leaves6950 on old paid replay; identical fresh command adds1000; deleted instance still replays current',
        'actual care/item/two receipt aborts, callback failure, late native bag overflow and missing wallet roll back together',
        'same failed key later commits once; known zero recovers1000; signed32 overflow consumes nothing',
        'dead HP remains0; no hot files; foreign/stale/malformed refuse; actual opaque lease and reopen retain state'],
        'database':'disposable','live_server_changed':False,'native_gui_verified':False}
    write_json(OUT/'evidence/pet-lifetime-items-verification.json',report)
    print('PASS',', '.join(report['passed']))


if __name__=='__main__':main()
