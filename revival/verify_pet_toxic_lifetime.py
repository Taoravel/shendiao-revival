"""Quality lifetime food, trusted chance and permanent aptitude effects."""
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
from pet_growth import Profile
from pet_growth_store import initialize_pet
from pet_skill_expiry import TimedSkillGrant
from research_pet_skill_expiry import native_timed_record


def refused(action,errors=(ValueError,)):
    try:action()
    except errors:return
    raise AssertionError('Invalid toxic-food attempt committed')


def main():
    with TemporaryDirectory() as tmp:
        store=AccountStore(Path(tmp)/'toxic-food.sqlite3')
        role=store.create_role(1111,'寿命食品',12,1010101)
        config=Inventory.prepare(store)
        inv=Inventory(store,1111,role['id'],config,**known_cash_context(store,1111,role['id']))
        pet=inv.grant_pet(500001);inv.grant_item(32004,1,quality=100)
        before=inv.immutable_snapshot();key=before.items[0].id
        body=struct.pack('>iiQ',key,1,pet)
        replies=inv.receive_pet_consumable(body,inv.epoch,'toxic:safe',None,None,9999)
        after=inv.immutable_snapshot()
        assert after.pets[0].care.lifetime==6300 and not after.items
        assert after.pets[0].progress==before.pets[0].progress
        _,raw=probe(0xf9d7b0,0xf9d840,0xf9d880,payload=next(b for k,b in replies if k==REFRESH_PET))
        assert struct.unpack_from('<i',raw,8+0xb0)[0]==6300
        inv.grant_item(32009,1,quality=100)
        key=inv.immutable_snapshot().items[0].id;body=struct.pack('>iiQ',key,1,pet)
        before=inv.immutable_snapshot()
        replies=inv.receive_pet_consumable(body,inv.epoch,'toxic:poison',None,None,299)
        after=inv.immutable_snapshot();p=after.pets[0].progress
        assert after.pets[0].care.lifetime==6550 and not after.items
        assert p.profile.aptitudes==(1129,1234,959,656,1121)
        assert p.profile.growth_raw==before.pets[0].progress.profile.growth_raw
        assert p.blood==before.pets[0].progress.blood
        assert (p.state.version,p.state.hp,p.attributes.max_hp)==(1,145,145)
        _,raw=probe(0xf9d7b0,0xf9d840,0xf9d880,payload=next(b for k,b in replies if k==REFRESH_PET))
        assert struct.unpack_from('<5i',raw,8+0x94)==(1129,1234,959,656,1121)
        assert struct.unpack_from('<4i',raw,0x48)==(145,145,62,62)
        # Expired admitted commands remain current even after unrelated later
        # growth/resources/care changes; deleted food keys do not reroll.
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');p=inv.pet_progress(db,pet)
            inv.change_pet_growth(db,pet,'toxic:later-wound',p.state.version,'resources',(7,3))
            care=inv.read_pet_state(db,pet).care
            inv.change_pet_care(db,pet,'toxic:later-death',care.version,'defeat',1)
        before=inv.immutable_snapshot();seen=[]
        def observe(db,inventory,snapshot,*,replayed):seen.append(replayed)
        inv.receive_pet_consumable(body,inv.epoch,'toxic:poison',None,observe)
        assert seen==[True] and inv.immutable_snapshot()==before
        refused(lambda:inv.receive_pet_consumable(body,inv.epoch,'toxic:poison',None,observe,300))
        assert inv.immutable_snapshot()==before
        class ReadOnlyConnections:
            def __getattr__(self,name):return getattr(store,name)
            def connect(self):
                db=store.connect()
                db.set_authorizer(lambda action,*args:sqlite3.SQLITE_DENY if action in
                    (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE) else sqlite3.SQLITE_OK)
                return db
        readonly=Inventory(ReadOnlyConnections(),1111,role['id'],config,epoch=inv.epoch,currency_rules=inv.currency_rules)
        readonly.receive_pet_consumable(body,inv.epoch,'toxic:poison')
        assert inv.immutable_snapshot()==before
        inv.grant_item(32009,1,quality=0)
        key=inv.immutable_snapshot().items[0].id;safe_body=struct.pack('>iiQ',key,1,pet)
        inv.receive_pet_consumable(safe_body,inv.epoch,'toxic:boundary300',None,None,300)
        p=inv.immutable_snapshot().pets[0]
        assert p.care.lifetime==6550 and p.progress==before.pets[0].progress
        # Low-level receipt already paid without a wrapper: native adaptation
        # validates that receipt, reports True, and remains a strict SQL read.
        inv.grant_item(32004,1,quality=100)
        key=inv.immutable_snapshot().items[0].id;low_body=struct.pack('>iiQ',key,1,pet)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            paid=inv.use_pet_toxic_food(db,key,pet,inv.epoch,'toxic:low',0,None)
            assert paid.poisoned and not paid.replayed
            assert paid.growth_after.profile.aptitudes==(1128,1233,958,655,1120)
        before=inv.immutable_snapshot();seen.clear()
        readonly.receive_pet_consumable(low_body,inv.epoch,'toxic:low',None,observe)
        assert seen==[True] and inv.immutable_snapshot()==before
        # Actual saved profile, care, debit and both receipts roll back as one.
        inv.grant_item(32004,1,quality=100)
        key=inv.immutable_snapshot().items[0].id;fresh_body=struct.pack('>iiQ',key,1,pet)
        for table,action in (('inventory_pet_growth','UPDATE'),('inventory_pet_care','UPDATE'),
                ('inventory_items','DELETE'),('inventory_pet_care_receipts','INSERT'),
                ('inventory_pet_toxic_food_receipts','INSERT'),('inventory_pet_consumable_commands','INSERT')):
            before=inv.immutable_snapshot()
            with closing(store.connect()) as db,db:
                db.execute(f"CREATE TRIGGER fail_toxic BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT,'toxic-food failure'); END")
            refused(lambda:inv.receive_pet_consumable(fresh_body,inv.epoch,'toxic:failed',None,None,0),(sqlite3.IntegrityError,))
            assert inv.immutable_snapshot()==before
            with closing(store.connect()) as db,db:db.execute('DROP TRIGGER fail_toxic')
        with patch.object(Path,'read_text',side_effect=AssertionError('Toxic food hot file read')):
            inv.receive_pet_consumable(fresh_body,inv.epoch,'toxic:failed',None,None,0)
        assert inv.immutable_snapshot().pets[0].progress.profile.aptitudes==(1127,1232,957,654,1119)
        inv.grant_item(32009,1,quality=100)
        key=inv.immutable_snapshot().items[0].id;fresh_body=struct.pack('>iiQ',key,1,pet)
        before=inv.immutable_snapshot()
        for bad in (None,False,-1,10000,1.5):
            refused(lambda:inv.receive_pet_consumable(fresh_body,inv.epoch,'toxic:bad-draw',None,None,bad))
            assert inv.immutable_snapshot()==before
        refused(lambda:inv.receive(0xc03ff,fresh_body))
        assert inv.immutable_snapshot()==before
        # Original ordinary blood projection follows the damaged base, without
        # modifying current blood power or awarding a second potential budget.
        inv.grant_item(36117)
        blood_key=next(x.id for x in inv.immutable_snapshot().items if x.template_id==36117)
        inv.receive_pet_consumable(struct.pack('>iiQ',blood_key,1,pet),inv.epoch,'toxic:blood')
        p=inv.immutable_snapshot().pets[0].progress
        assert p.effective_profile.aptitudes==(1129,1234,958,655,1121) and p.attributes.potential==10
        before=inv.immutable_snapshot()
        inv.receive_pet_consumable(fresh_body,inv.epoch,'toxic:with-blood',None,None,0)
        p=inv.immutable_snapshot().pets[0].progress
        assert p.profile.aptitudes==(1126,1231,956,653,1118)
        assert p.effective_profile.aptitudes==(1128,1233,957,654,1120)
        assert p.blood==before.pets[0].progress.blood and p.attributes.potential==10
        assert p.state.hp==7 and p.state.mp==3
        final=inv.immutable_snapshot()
        inv.receive_pet_consumable(struct.pack('>iiQ',blood_key,1,pet),inv.epoch,'toxic:blood')
        assert inv.immutable_snapshot()==final
        for quality in (None,0):
            inv.grant_item(32004,1,quality=quality)
            bad=next(x.id for x in inv.immutable_snapshot().items if x.template_id==32004 and x.quality==quality)
            before=inv.immutable_snapshot()
            refused(lambda:inv.receive_pet_consumable(struct.pack('>iiQ',bad,1,pet),inv.epoch,'toxic:bad-quality:'+str(quality),None,None,0))
            assert inv.immutable_snapshot()==before
        inv.grant_item(32009,1,quality=100)
        key=next(x.id for x in inv.immutable_snapshot().items if x.template_id==32009)
        late_body=struct.pack('>iiQ',key,1,pet)
        inv.grant_item(32000)
        bad=next(x.id for x in inv.immutable_snapshot().items if x.template_id==32000)
        with closing(store.connect()) as db,db:db.execute('UPDATE inventory_items SET quantity=? WHERE id=?',(2**31,bad))
        before=inv.immutable_snapshot()
        refused(lambda:inv.receive_pet_consumable(late_body,inv.epoch,'toxic:late-bag',None,None,0),(struct.error,))
        assert inv.immutable_snapshot()==before
        with closing(store.connect()) as db,db:db.execute('UPDATE inventory_items SET quantity=1 WHERE id=?',(bad,))
        inv.receive_pet_consumable(late_body,inv.epoch,'toxic:late-bag',None,None,0)
        assert inv.immutable_snapshot().pets[0].progress.profile.aptitudes==(1125,1230,955,652,1117)
        inv.grant_item(32009,1,quality=100)
        key=next(x.id for x in inv.immutable_snapshot().items if x.template_id==32009)
        fresh_body=struct.pack('>iiQ',key,1,pet);before=inv.immutable_snapshot()
        try:
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE');progress=inv.pet_progress(db,pet)
                inv.use_pet_toxic_food(db,key,pet,inv.epoch,'toxic:outer',0,progress.state.version)
                raise ValueError('Controlled caller failure')
        except ValueError:pass
        assert inv.immutable_snapshot()==before
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            refused(lambda:inv.use_pet_toxic_food(db,key,pet,inv.epoch,'toxic:stale',0,0))
            refused(lambda:inv.use_pet_toxic_food(db,key,pet,inv.epoch,'toxic:bool',0,False))
        assert inv.immutable_snapshot()==before
        # Full known historical base imports exercise the aptitude zero floor,
        # death preservation and lifetime overflow without resetting any pet.
        special=[]
        for name,lifetime,blood in (('基础将零',6000,True),('寿命将满',2**31-11,True),('旧血脉未知',6000,False)):
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                old=db.execute('INSERT INTO inventory_pets(role_id,template_id,name) VALUES(?,?,?)',
                    (role['id'],500001,name)).lastrowid
                inv.initialize_pet_care(db,old,1,100,lifetime)
                initialize_pet(db,1111,role['id'],old,Profile(500001,1006,(0,1,0,1,0)),inv.growth_rules)
                if blood:inv.initialize_pet_blood(db,old,0)
            special.append(old)
        floor,limit,unknown=special
        before=inv.immutable_snapshot()
        refused(lambda:inv.receive_pet_consumable(struct.pack('>iiQ',key,1,limit),inv.epoch,'toxic:overflow',None,None,0))
        refused(lambda:inv.receive_pet_consumable(struct.pack('>iiQ',key,1,unknown),inv.epoch,'toxic:unknown',None,None,0))
        assert inv.immutable_snapshot()==before
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');progress=inv.pet_progress(db,floor)
            inv.change_pet_growth(db,floor,'toxic:floor-dead',progress.state.version,'resources',(0,0))
        inv.receive_pet_consumable(struct.pack('>iiQ',key,1,floor),inv.epoch,'toxic:floor',None,None,0)
        floored=next(p.progress for p in inv.immutable_snapshot().pets if p.id==floor)
        assert floored.profile.aptitudes==(0,0,0,0,0) and (floored.state.version,floored.state.hp)==(2,0)
        inv.grant_item(32009,1,quality=100)
        key=next(x.id for x in inv.immutable_snapshot().items if x.template_id==32009)
        floor_body=struct.pack('>iiQ',key,1,floor)
        inv.receive_pet_consumable(floor_body,inv.epoch,'toxic:floor-again',None,None,0)
        assert next(p.progress for p in inv.immutable_snapshot().pets if p.id==floor)==floored
        # Missing actual cash forces rollback AFTER aptitude/lifetime writes.
        other=store.create_role(1111,'未知食物钱包',12,1010101)
        epoch=store.acquire_lease(1111,other['id'])
        no_cash=Inventory(store,1111,other['id'],config,epoch=epoch,currency_rules=inv.currency_rules)
        other_pet=no_cash.grant_pet(500001);no_cash.grant_item(32009,quality=100)
        other_key=no_cash.immutable_snapshot().items[0].id;before_other=no_cash.immutable_snapshot()
        refused(lambda:no_cash.receive_pet_consumable(struct.pack('>iiQ',other_key,1,other_pet),epoch,'toxic:no-wallet',None,None,0))
        assert no_cash.immutable_snapshot()==before_other
        # Paid confirmation with a real replacement opaque lease still reads
        # current state. It may not revive or rewrite any historical profile.
        token='中毒食物:00007';store.inventory_config=config
        with closing(store.connect()) as db,db:db.execute('UPDATE role_leases SET epoch=? WHERE role_id=?',(token,role['id']))
        active=Inventory(store.leased(1111,role['id'],token),1111,role['id'],config,epoch=token,currency_rules=inv.currency_rules)
        final=active.immutable_snapshot()
        active.receive_pet_consumable(floor_body,token,'toxic:floor-again')
        refused(lambda:inv.receive_pet_consumable(floor_body,inv.epoch,'toxic:floor-again'))
        assert active.immutable_snapshot()==final
        active.grant_item(32004,quality=1)
        fresh_key=next(x.id for x in active.immutable_snapshot().items if x.template_id==32004 and x.quality==1)
        actual_body=struct.pack('>iiQ',fresh_key,1,pet)
        before=active.immutable_snapshot()
        refused(lambda:active.receive_pet_consumable(struct.pack('>iiQ',fresh_key,1,other_pet),token,'toxic:foreign',None,None,0))
        refused(lambda:active.receive_pet_consumable(actual_body[:-1],token,'toxic:truncated',None,None,0))
        assert active.immutable_snapshot()==before
        active.receive_pet_consumable(actual_body,token,'toxic:opaque-new',None,None,0)
        assert active.immutable_snapshot().pets[0].progress.profile.aptitudes==(1124,1229,954,651,1116)
        active.grant_item(32009,quality=0)
        long_key=next(x.id for x in active.immutable_snapshot().items if x.template_id==32009 and x.quality==0)
        long_body=struct.pack('>iiQ',long_key,1,pet);long_id='食'*160
        active.receive_pet_consumable(long_body,token,long_id,None,None,9999)
        before=active.immutable_snapshot()
        active.receive_pet_consumable(long_body,token,long_id)
        assert active.immutable_snapshot()==before
        active.grant_item(32009,quality=100)
        timed_key=next(x.id for x in active.immutable_snapshot().items if x.template_id==32009 and x.quality==100)
        timed_body=struct.pack('>iiQ',timed_key,1,pet)
        before=active.immutable_snapshot()
        refused(lambda:active.receive_pet_consumable(timed_body,token,'食'*161,None,None,0))
        assert active.immutable_snapshot()==before
        with closing(active.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');current=active.read_pet_state(db,pet)
            active.grant_pet_timed_skill(db,TimedSkillGrant('toxic:clock-skill',pet,200484,1000,
                'known-absolute-fixture',current.skills.version),token,100)
        before=active.immutable_snapshot()
        refused(lambda:active.receive_pet_consumable(timed_body,token,'toxic:clock',None,None,0))
        assert active.immutable_snapshot()==before
        timed=active.receive_pet_consumable(timed_body,token,'toxic:clock',1011,None,0)
        assert timed[0]==(0xc0007,struct.pack('>q',1011))
        _,icons,_=native_timed_record(next(b for k,b in timed if k==REFRESH_PET),1011)
        assert icons[-1][1]==200534
        assert active.immutable_snapshot().pets[0].skill_expiry==before.pets[0].skill_expiry
        final=inv.immutable_snapshot()
        assert Inventory(AccountStore(store.path),1111,role['id'],config).immutable_snapshot()==final
    report={'passed':['actual32004 quality100 draw9999 adds300 without aptitude change',
        'actual32009 quality100 draw299 adds250 and loses1 each base aptitude; original native decoder sees new five aptitudes and clipped145HP',
        'draw300 safe boundary and original32009 quality0 adds50; later wounds/care survive deleted-key paid replay',
        'paid and low-level-only replay pass SQL no-write authorizer; changed captured draw refuses without source repair',
        'real growth/care/debit/care-receipt/food-receipt/wrapper faults all roll back; same failed command later commits once',
        'missing/bool/range draws and legacy context-free route refuse; no hot files',
        'current damaged base is projected before unchanged blood and10 potential; old blood receipt never restores pre-poison base',
        'unknown/zero quality, unknown blood and lifetime overflow refuse; aptitude floor0 preserves HP0 and avoids fake growth churn',
        'actual late bag overflow, missing wallet and outer caller failure roll all poisoned effects back; stale/bool versions refuse',
        'real replacement opaque lease reads paid state and executes fresh poison; foreign/truncated/old owner refuse; reopen retains damaged profiles',
        '160-character command ID commits/replays;161 refuses; missing clock rolls poison back and trusted clock preserves expired raw skill map'],
        'database':'disposable','live_server_changed':False,'native_gui_verified':False}
    write_json(OUT/'evidence/pet-toxic-lifetime-verification.json',report)
    print('PASS',', '.join(report['passed']))


if __name__=='__main__':main()
