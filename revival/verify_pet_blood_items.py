"""Actual blood essence through admitted pet CUseItem and caller transactions."""
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
import struct
import sqlite3

from accounts import AccountStore
from inventory import Inventory,REFRESH_PET
from inventory_test_support import known_cash_context
from research_pet_blood import native_blood_record
from pet_skill_expiry import TimedSkillGrant
from research_pet_skill_expiry import native_timed_record
from inspect_client import OUT,write_json
from native_gameplay_probe import probe


def refused(action):
    try:action()
    except ValueError:return
    raise AssertionError('Invalid pet item or capped blood consumed an asset')


def main():
    with TemporaryDirectory() as directory:
        store=AccountStore(Path(directory)/'state.sqlite3')
        role=store.create_role(1111,'血脉精华使用',12,1010101)
        config=Inventory.prepare(store)
        inv=Inventory(store,1111,role['id'],config,**known_cash_context(store,1111,role['id'],balances=(71,0,0,0)))
        pet=inv.grant_pet(500001);inv.grant_item(36117,7)
        key=next(i.id for i in inv.immutable_snapshot().items if i.template_id==36117)
        body=struct.pack('>iiQ',key,1,pet)
        reply=inv.receive_pet_consumable(body,inv.epoch,'blood:first')
        current=inv.immutable_snapshot().pets[0].progress
        assert current.blood.state.power==200 and current.blood.state.version==1
        assert current.attributes.potential==10 and current.state.version==1
        assert current.profile.aptitudes==(1130,1235,960,657,1122)
        assert current.effective_profile.aptitudes==(1132,1237,961,658,1124)
        assert next(i.quantity for i in inv.immutable_snapshot().items if i.id==key)==6
        native=native_blood_record(next(b for k,b in reply if k==REFRESH_PET))
        assert (native['power'],native['maximum_power'],native['level'],native['displayed_blood_potential'])==(200,1139,1,10)
        before=inv.immutable_snapshot()
        inv.receive_pet_consumable(body,inv.epoch,'blood:first')
        assert inv.immutable_snapshot()==before
        for index,power,level,potential,aptitudes in (
            (2,400,2,20,(1135,1241,964,660,1127)),
            (3,600,3,30,(1140,1246,968,662,1132)),
            (4,800,3,30,(1140,1246,968,662,1132)),
            (5,1000,3,30,(1140,1246,968,662,1132)),
            (6,1139,3,30,(1140,1246,968,662,1132))):
            reply=inv.receive_pet_consumable(body,inv.epoch,'blood:'+str(index))
            current=inv.immutable_snapshot().pets[0].progress
            assert (current.blood.state.power,current.blood.level,current.attributes.potential)==(power,level,potential)
            assert current.effective_profile.aptitudes==aptitudes
            native=native_blood_record(next(b for k,b in reply if k==REFRESH_PET))
            assert (native['power'],native['level'],native['displayed_blood_potential'])==(power,level,potential)
        assert next(i.quantity for i in inv.immutable_snapshot().items if i.id==key)==1
        before=inv.immutable_snapshot()
        refused(lambda:inv.receive_pet_consumable(body,inv.epoch,'blood:capped'))
        assert inv.immutable_snapshot()==before
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            current=inv.pet_progress(db,pet)
            allocated=inv.change_pet_growth(db,pet,'blood:allocate',current.state.version,'allocate',(30,0,0,0,0))
            assert allocated.attributes.potential==0
            refused(lambda:inv.change_pet_growth(db,pet,'blood:over-allocate',allocated.state.version,'allocate',(1,0,0,0,0)))
        before=inv.immutable_snapshot()
        late=inv.receive_pet_consumable(body,inv.epoch,'blood:first')
        assert inv.immutable_snapshot()==before
        assert native_blood_record(next(b for k,b in late if k==REFRESH_PET))['power']==1139
        assert Inventory(AccountStore(store.path),1111,role['id'],config).immutable_snapshot()==before
        fresh=inv.grant_pet(500001);inv.grant_item(36117,8)
        body=struct.pack('>iiQ',key,1,fresh)
        before=inv.immutable_snapshot()
        # Every actual storage phase is part of the same admitted use transaction.
        for table,action in (('inventory_pet_blood','UPDATE'),('inventory_pet_growth','UPDATE'),
                ('inventory_pet_blood_receipts','INSERT'),('inventory_pet_consumable_commands','INSERT')):
            with closing(store.connect()) as db:
                db.execute(f"CREATE TRIGGER fail_blood_item BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT,'blood item failed'); END")
            try:inv.receive_pet_consumable(body,inv.epoch,'blood:abort')
            except sqlite3.IntegrityError:pass
            else:raise AssertionError('Real blood/growth/receipt storage fault did not execute')
            assert inv.immutable_snapshot()==before
            with closing(store.connect()) as db:db.execute('DROP TRIGGER fail_blood_item')
        try:
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                inv.use_pet_blood_essence(db,key,fresh,inv.epoch,'blood:outer',0)
                raise RuntimeError('outer common settlement failed')
        except RuntimeError:pass
        assert inv.immutable_snapshot()==before
        no_wallet=Inventory(AccountStore(store.path),1111,role['id'],config,epoch=inv.epoch)
        refused(lambda:no_wallet.receive_pet_consumable(body,inv.epoch,'blood:abort'))
        assert inv.immutable_snapshot()==before
        inv.grant_item(32001,quality=10)
        other=next(i.id for i in inv.immutable_snapshot().items if i.template_id==32001)
        with closing(store.connect()) as db,db:
            assert db.execute('UPDATE inventory_items SET quantity=? WHERE id=?',(2**31,other)).rowcount==1
        bad=inv.immutable_snapshot()
        try:inv.receive_pet_consumable(body,inv.epoch,'blood:abort')
        except struct.error:pass
        else:raise AssertionError('Late real bag encoding overflow did not execute')
        assert inv.immutable_snapshot()==bad
        with closing(store.connect()) as db,db:db.execute('UPDATE inventory_items SET quantity=1 WHERE id=?',(other,))
        before=inv.immutable_snapshot()
        inv.receive_pet_consumable(body,inv.epoch,'blood:abort')
        current=next(p.progress for p in inv.immutable_snapshot().pets if p.id==fresh)
        assert current.blood.state.power==200
        assert next(i.quantity for i in inv.immutable_snapshot().items if i.id==key)==next(i.quantity for i in before.items if i.id==key)-1
        before=inv.immutable_snapshot()
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            refused(lambda:inv.use_pet_blood_essence(db,key,fresh,inv.epoch,'blood:stale',0))
            refused(lambda:inv.use_pet_blood_essence(db,key,fresh,inv.epoch,'blood:bool',False))
        assert inv.immutable_snapshot()==before
        # The low-level paid receipt can be read through the native Adapter even
        # with no wrapper receipt; the root hook gets a VERIFIED True and no DB
        # writes occur. This prevents an old payment from repairing later source.
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            receipt=inv.use_pet_blood_essence(db,key,fresh,inv.epoch,'blood:low-level',None)
            assert not receipt.replayed and receipt.after.blood.state.power==400
        before=inv.immutable_snapshot();seen=[]
        def paid_read(db,inventory,snapshot,*,replayed):seen.append(replayed)
        inv.receive_pet_consumable(body,inv.epoch,'blood:low-level',None,paid_read)
        assert seen==[True] and inv.immutable_snapshot()==before
        class ReadOnlyConnections:
            """Real storage Adapter with SQL writes denied for the paid path."""
            def __getattr__(self,name):return getattr(store,name)
            def connect(self):
                db=store.connect()
                db.set_authorizer(lambda action,*args:sqlite3.SQLITE_DENY if action in
                    (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE) else sqlite3.SQLITE_OK)
                return db
        read_inv=Inventory(ReadOnlyConnections(),1111,role['id'],config,epoch=inv.epoch,currency_rules=inv.currency_rules)
        read_inv.receive_pet_consumable(body,inv.epoch,'blood:low-level',None,paid_read)
        assert inv.immutable_snapshot()==before
        # Old unknown blood refuses a real valid item until a trusted full import.
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            unknown=db.execute('INSERT INTO inventory_pets(role_id,template_id,name) VALUES(?,?,?)',
                (role['id'],500001,'旧血脉未知')).lastrowid
            inv.initialize_pet_care(db,unknown,1,100,6000);inv.initialize_pet_growth(db,unknown)
            inv.initialize_pet_skills(db,unknown,(200091,200061));inv.initialize_pet_flags(db,unknown,0)
            inv.initialize_pet_skill_progress(db,unknown,0);inv.initialize_pet_skill_expiry(db,unknown,())
        unknown_body=struct.pack('>iiQ',key,1,unknown);before=inv.immutable_snapshot()
        refused(lambda:inv.receive_pet_consumable(unknown_body,inv.epoch,'blood:unknown'))
        assert inv.immutable_snapshot()==before and next(p.progress.blood for p in before.pets if p.id==unknown) is None
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');inv.initialize_pet_blood(db,unknown,0)
        inv.receive_pet_consumable(unknown_body,inv.epoch,'blood:unknown')
        assert next(p.progress.blood.state.power for p in inv.immutable_snapshot().pets if p.id==unknown)==200
        dead=inv.grant_pet(500001)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            p=inv.pet_progress(db,dead)
            inv.change_pet_growth(db,dead,'blood:dead-fixture',p.state.version,'resources',(0,0))
        inv.receive_pet_consumable(struct.pack('>iiQ',key,1,dead),inv.epoch,'blood:dead')
        assert next(p.progress.state.hp for p in inv.immutable_snapshot().pets if p.id==dead)==0
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            p=inv.read_pet_state(db,fresh)
            inv.grant_pet_timed_skill(db,TimedSkillGrant('blood:clock-fixture',fresh,200484,1000,'fixture:known-source',p.skills.version),inv.epoch,100)
        before=inv.immutable_snapshot()
        refused(lambda:inv.receive_pet_consumable(body,inv.epoch,'blood:timed'))
        assert inv.immutable_snapshot()==before
        timed=inv.receive_pet_consumable(body,inv.epoch,'blood:timed',1001)
        assert timed[0]==(0xc0007,struct.pack('>q',1001))
        _,icons,_=native_timed_record(next(b for k,b in timed if k==REFRESH_PET),1001)
        assert icons[-1][1]==200534
        # The same admitted kind1 Adapter also guards ordinary medicines/food;
        # later wounds or loyalty loss cannot make an old payment run again.
        inv.grant_item(32000,2)
        medicine_key=next(i.id for i in inv.immutable_snapshot().items if i.template_id==32000)
        medicine_body=struct.pack('>iiQ',medicine_key,1,fresh)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');p=inv.pet_progress(db,fresh)
            inv.change_pet_growth(db,fresh,'ordinary:wound',p.state.version,'resources',(1,1))
        flags=[]
        def ordinary_hook(db,inventory,snapshot,*,replayed):flags.append(replayed)
        inv.receive_pet_consumable(medicine_body,inv.epoch,'ordinary:medicine',1002,ordinary_hook)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');p=inv.pet_progress(db,fresh)
            inv.change_pet_growth(db,fresh,'ordinary:later-wound',p.state.version,'resources',(7,1))
        before=inv.immutable_snapshot()
        replay=inv.receive_pet_consumable(medicine_body,inv.epoch,'ordinary:medicine',1003,ordinary_hook)
        assert flags==[False,True] and inv.immutable_snapshot()==before
        _,decoded=probe(0xf9d7b0,0xf9d840,0xf9d880,
            payload=next(b for k,b in replay if k==REFRESH_PET))
        assert struct.unpack_from('<i',decoded,0x48)[0]==7
        inv.grant_item(31000,2)
        food_key=next(i.id for i in inv.immutable_snapshot().items if i.template_id==31000)
        food_body=struct.pack('>iiQ',food_key,1,fresh)
        for request in ('ordinary:defeat','ordinary:later-defeat'):
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE');care=inv.read_pet_state(db,fresh).care
                inv.change_pet_care(db,fresh,request,care.version,'defeat',1)
            if request=='ordinary:defeat':inv.receive_pet_consumable(food_body,inv.epoch,'ordinary:food',1004)
        before=inv.immutable_snapshot()
        inv.receive_pet_consumable(food_body,inv.epoch,'ordinary:food',1005)
        assert inv.immutable_snapshot()==before
        foreign=store.create_role(1111,'他人血脉宠',12,1010101)
        other_inv=Inventory(store,1111,foreign['id'],config)
        foreign_pet=other_inv.grant_pet(500001)
        before=inv.immutable_snapshot()
        refused(lambda:inv.receive_pet_consumable(struct.pack('>iiQ',key,1,foreign_pet),inv.epoch,'blood:foreign',1006))
        before=inv.immutable_snapshot()
        refused(lambda:inv.receive_pet_consumable(body[:-1],inv.epoch,'blood:invalid'))
        refused(lambda:inv.receive_pet_consumable(body,inv.epoch+1,'blood:invalid'))
        refused(lambda:inv.receive_pet_consumable(struct.pack('>iiQ',key,0,role['id']),inv.epoch,'blood:invalid'))
        refused(lambda:inv.receive_pet_consumable(struct.pack('>iiQ',key,1,dead),inv.epoch,'blood:first',1002))
        assert inv.immutable_snapshot()==before
        token='血脉命令:00007';old_epoch=inv.epoch;store.inventory_config=config
        with closing(store.connect()) as db,db:db.execute('UPDATE role_leases SET epoch=? WHERE role_id=?',(token,role['id']))
        active=Inventory(store.leased(1111,role['id'],token),1111,role['id'],config,
            epoch=token,currency_rules=inv.currency_rules)
        refused(lambda:inv.receive_pet_consumable(body,old_epoch,'blood:abort',1007))
        active.receive_pet_consumable(body,token,'blood:abort',1007)
        assert active.immutable_snapshot()==before
        active.receive_pet_consumable(body,token,'blood:opaque-new',1008)
        p=next(p.progress for p in active.immutable_snapshot().pets if p.id==fresh)
        assert (p.blood.state.power,p.state.hp)==(800,7)
        # At naturalL10 the third blood level increases actual caps262/105 to
        #263/106. A wounded20/10 becomes21/11, rather than being filled.
        trained=active.grant_pet(500001);active.grant_item(36117,5)
        with closing(active.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');p=active.pet_progress(db,trained)
            amount=sum(active.growth_rules.thresholds[i] for i in range(10))
            p=active.change_pet_growth(db,trained,'blood:trained-xp',p.state.version,'experience',amount)
            assert (p.state.level,p.attributes.max_hp,p.attributes.max_mp)==(10,262,105)
            active.change_pet_growth(db,trained,'blood:trained-wound',p.state.version,'resources',(20,10))
        trained_body=struct.pack('>iiQ',key,1,trained)
        for index in (1,2,3):trained_reply=active.receive_pet_consumable(trained_body,token,'blood:trained:'+str(index),1010+index)
        p=next(p.progress for p in active.immutable_snapshot().pets if p.id==trained)
        assert (p.attributes.max_hp,p.attributes.max_mp,p.state.hp,p.state.mp,p.attributes.potential)==(263,106,21,11,80)
        _,decoded=probe(0xf9d7b0,0xf9d840,0xf9d880,payload=next(b for k,b in trained_reply if k==REFRESH_PET))
        assert struct.unpack_from('<4i',decoded,0x48)==(21,263,11,106)
        assert struct.unpack_from('<h',decoded,0x80)[0]==80
        with closing(active.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');p=active.pet_progress(db,dead)
            p=active.change_pet_growth(db,dead,'blood:dead-trained-xp',p.state.version,'experience',amount)
            active.change_pet_growth(db,dead,'blood:dead-trained-resources',p.state.version,'resources',(0,0))
        for index in (2,3):active.receive_pet_consumable(struct.pack('>iiQ',key,1,dead),token,'blood:dead-trained:'+str(index),1020+index)
        p=next(p.progress for p in active.immutable_snapshot().pets if p.id==dead)
        assert (p.attributes.max_hp,p.state.hp,p.blood.level)==(263,0,3)
    report={'passed':['real original36117 consumes one and advances200; native blood/level/potential consumers accept replies',
        'white colour fills1139; level3 energy-only steps add no extra potential; capped attempt consumes nothing',
        'real blood potential allocated30; late first request replies CURRENT capped/allocated state without repeat debit',
        'actual blood/growth/blood-receipt/common-command faults, outer failure, missing wallet and late native bag overflow roll back together',
        'same failed key later commits once; version/bool guards; low-level historical replay True succeeds with SQL writes forbidden',
        'old unknown blood refuses valid essence then explicit known import succeeds; dead pet advances without reviving',
        'naturalL10 blood3 raises caps262/105 to263/106; wounds20/10 become21/11 and original decoder sees80 potential; actual cap increase never revives',
        'ordinary medicine/food stable commands never reapply after later wounds or loyalty loss',
        'timed pet requires server clock and preserves original expiry/empty icon; foreign/malformed/context/intent mismatch refuses',
        'actual opaque LeasedAccounts supports current replay/new essence and rejects the obsolete lease'],
        'source_status':'original values/layout client_verified; rounding/cap/resources/level-conflict decisions designed',
        'live_server_changed':False,'native_gui_tested':False,'shared_route_changed_by_this_window':False}
    write_json(OUT/'evidence/pet-blood-items-verification.json',report)
    print('PASS',', '.join(report['passed']))


if __name__=='__main__':main()
