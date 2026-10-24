"""Five cakes through owned inventory transactions and original confirmed CUseItem."""
from pathlib import Path
from tempfile import TemporaryDirectory
from contextlib import closing
import struct
from accounts import AccountStore
from inventory import Inventory,REFRESH_PET
from inventory_test_support import known_cash_context
from pet_protocol import CAKE_NOTICE,SUPER_RETURN_SUBMIT,game_time_message
from pet_cake_effects import CakeUnavailable
from research_pet_cake_protocol import native_notice
from research_pet_cake import native_count
from inspect_client import OUT,write_json
from unittest.mock import patch
import sqlite3


def refused(action,errors=(ValueError,)):
    try:action()
    except errors:return
    raise AssertionError('Invalid cake command or fault committed')


def main():
    with TemporaryDirectory() as tmp:
        store=AccountStore(Path(tmp)/'cakes.sqlite3')
        role=store.create_role(1111,'年糕事务',12,1010101)
        config=Inventory.prepare(store)
        inv=Inventory(store,1111,role['id'],config,**known_cash_context(store,1111,role['id']))
        pet=inv.grant_pet(500001);inv.grant_item(31268,3)
        snapshot=inv.immutable_snapshot();before=snapshot.pets[0]
        key=next(i.id for i in snapshot.items if i.template_id==31268)
        body=struct.pack('>iiQ',key,1,pet)
        replies=inv.receive_pet_consumable(body,inv.epoch,'cake:A')
        current=inv.immutable_snapshot();after=current.pets[0]
        assert after.progress.profile.aptitudes==(1137,1235,960,657,1122),'原客户端中档攻资年糕应增加7基础资质'
        assert after.cake.count==1 and after.cake.added_aptitudes==(7,0,0,0,0)
        assert after.progress.state.hp==before.progress.state.hp and after.progress.state.mp==before.progress.state.mp
        assert after.progress.blood==before.progress.blood and after.skills==before.skills
        assert next(i.quantity for i in current.items if i.id==key)==2
        inv.receive_pet_consumable(body,inv.epoch,'cake:A')
        assert inv.immutable_snapshot()==current
        assert any(t==REFRESH_PET for t,b in replies)
        assert any(t==0xc1775 for t,b in replies),'服用后缺少原年糕实际增长/剩余次数消息'
        assert native_notice(next(b for t,b in replies if t==CAKE_NOTICE))==(145135,0,('外功','7','19'))
        paid=inv.receive_pet_consumable(body,inv.epoch,'cake:A')
        assert all(t!=CAKE_NOTICE for t,b in paid)
        def state(target):return next(p for p in inv.immutable_snapshot().pets if p.id==target)
        def item(template):return next(i.id for i in inv.immutable_snapshot().items if i.template_id==template)
        def eat(target,template,request,**kwargs):
            return inv.receive_pet_consumable(struct.pack('>iiQ',item(template),1,target),inv.epoch,request,**kwargs)
        inv.grant_item(31268,10)
        for template in range(31269,31273):inv.grant_item(template,10)
        for template in range(31269,31273):eat(pet,template,'cake:kind:'+str(template))
        five=state(pet)
        assert five.progress.profile.aptitudes==(1137,1243,969,663,1130)
        assert five.cake.count==5 and five.cake.added_aptitudes==(7,8,9,6,8)
        assert five.skills==before.skills and five.traits==before.traits and five.care==before.care
        # A cake changes the BASE/history source of an existing super candidate.
        inv.grant_item(31576,3);pill=item(31576)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            inv.super_return(db,pet,inv.epoch,'cake:old-super','preview',item_key=pill,draws=(0,)*7)
        eat(pet,31268,'cake:after-super')
        snapshot=inv.immutable_snapshot()
        refused(lambda:inv.receive_super_return(SUPER_RETURN_SUBMIT,struct.pack('>i',pet),inv.epoch,
            'cake:save-stale',expected_candidate='cake:old-super'))
        assert inv.immutable_snapshot()==snapshot
        # All five kinds share one count. Each real successful item advances it once.
        for number in range(6,20):eat(pet,31268+number%5,'cake:fill:'+str(number))
        capped=state(pet);assert capped.cake.count==20
        assert native_count(next(b for t,b in inv.receive_pet_consumable(body,inv.epoch,'cake:A') if t==REFRESH_PET))['count']==20
        snapshot=inv.immutable_snapshot()
        def must_not_commit(*args,**kwargs):raise AssertionError('Rejected cake reached mutation precommit')
        rejected=eat(pet,31271,'cake:over-cap',precommit=must_not_commit)
        assert len(rejected)==1 and native_notice(rejected[0][1])==(145133,0,())
        assert inv.immutable_snapshot()==snapshot
        # Super save really removes the old BASE effects and resets all twenty slots.
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            inv.super_return(db,pet,inv.epoch,'cake:new-super','preview',item_key=pill,draws=(0,)*7)
        inv.receive_super_return(SUPER_RETURN_SUBMIT,struct.pack('>i',pet),inv.epoch,'cake:save-new',expected_candidate='cake:new-super')
        assert state(pet).cake.count==0 and state(pet).cake.added_aptitudes==(0,)*5
        eat(pet,31268,'cake:after-reset')
        assert state(pet).progress.profile.aptitudes[0]==1056 and state(pet).cake.added_aptitudes==(16,0,0,0,0)
        # Native already-max and near-max zero gain are both free rejections.
        inv.grant_item(31002,2)
        inv.receive_ordinary_return(struct.pack('>iiQ',item(31002),1,pet),inv.epoch,'cake:max-roll',(9999,)*15)
        snapshot=inv.immutable_snapshot()
        assert native_notice(eat(pet,31268,'cake:max')[0][1])==(145137,0,())
        assert inv.immutable_snapshot()==snapshot
        inv.grant_item(32004,1,quality=100)
        inv.receive_pet_consumable(struct.pack('>iiQ',item(32004),1,pet),inv.epoch,'cake:poison',draw=0)
        snapshot=inv.immutable_snapshot()
        assert native_notice(eat(pet,31268,'cake:near-max')[0][1])==(145136,0,('栗子年糕',))
        assert inv.immutable_snapshot()==snapshot
        # The original kind2 gate is specific; fairy/wild identities are not blanket-banned.
        god=inv.grant_pet(500069);snapshot=inv.immutable_snapshot()
        assert native_notice(eat(god,31268,'cake:god')[0][1])==(145139,0,())
        assert inv.immutable_snapshot()==snapshot
        inv.free_pet(god)
        fairy=inv.grant_pet(500118);snapshot=inv.immutable_snapshot()
        assert native_notice(eat(fairy,31270,'cake:fixed-fairy')[0][1])==(145137,0,())
        assert inv.immutable_snapshot()==snapshot
        eat(fairy,31268,'cake:fairy')
        assert state(fairy).cake.count==1
        wild=inv.grant_pet(500001)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');db.execute('DELETE FROM inventory_pet_traits WHERE pet_id=?',(wild,))
            inv.initialize_pet_traits(db,wild,1,73)
        eat(wild,31269,'cake:wild')
        assert state(wild).traits.origin==1 and state(wild).traits.insight==73
        # Actual retained blood is not multiplied into stored BASE; one known
        # native floating boundary predicts8 while rational effective delta is9.
        with closing(store.connect()) as db,db:db.execute('UPDATE roles SET level=150 WHERE id=?',(role['id'],))
        boundary=inv.grant_pet(500004);inv.grant_item(36117,2);essence=item(36117)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            inv.use_pet_blood_essence(db,essence,boundary,inv.epoch,'cake:blood:1',None)
            inv.use_pet_blood_essence(db,essence,boundary,inv.epoch,'cake:blood:2',None)
            p=inv.read_pet_state(db,boundary)
            receipt=inv.use_pet_cake(db,item(31272),boundary,inv.epoch,'cake:rounding')
            assert (receipt.prediction.client_gain,receipt.prediction.base_gain,receipt.actual_gain)==(8,8,9)
        actual=state(boundary)
        assert actual.progress.profile.aptitudes[4]==1200 and actual.cake.added_aptitudes[4]==8
        assert actual.progress.effective_profile.aptitudes[4]==1206
        # A low-level-only historical acknowledgement does not manufacture a
        # wrapper receipt, repeat the effect, or send a fresh success notice.
        snapshot=inv.immutable_snapshot()
        replay=inv.receive_pet_consumable(struct.pack('>iiQ',item(31272),1,boundary),inv.epoch,'cake:rounding')
        assert all(t!=CAKE_NOTICE for t,b in replay) and inv.immutable_snapshot()==snapshot
        # Selected does not mean currently in battle; the original named cake
        # permits the selected pet and must not copy rebirth's fighting gate.
        from inventory import FIGHT_PET,REST_PET
        inv.receive(FIGHT_PET,struct.pack('>i',boundary))
        eat(boundary,31268,'cake:selected')
        inv.receive(REST_PET,b'')
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');p=inv.read_pet_state(db,boundary)
            inv.change_pet_growth(db,boundary,'cake:XP',p.progress.state.version,'experience',1000)
            p=inv.read_pet_state(db,boundary)
            inv.change_pet_growth(db,boundary,'cake:allocation',p.progress.state.version,'allocate',(1,0,0,0,0))
            p=inv.read_pet_state(db,boundary)
            inv.change_pet_growth(db,boundary,'cake:death',p.progress.state.version,'resources',(0,2))
        p=state(boundary);eat(boundary,31270,'cake:dead-no-heal');q=state(boundary)
        assert q.progress.state.hp==0 and q.progress.state.mp==2
        assert q.progress.attributes.max_hp>=p.progress.attributes.max_hp
        assert (q.progress.state.level,q.progress.state.experience,q.progress.state.allocated)==(
            p.progress.state.level,p.progress.state.experience,p.progress.state.allocated)
        assert q.progress.blood==p.progress.blood and q.skills==p.skills and q.flags==p.flags
        # Real DB failures, caller failure and late native encoding all roll
        # back BASE/cake/count/item/revisions/both command receipts together.
        fault=inv.grant_pet(500001)
        stages=(('inventory_pet_growth','UPDATE'),('inventory_pet_cakes','UPDATE'),('inventory_items','UPDATE'),
                ('inventory_pet_cake_receipts','INSERT'),('inventory_pet_consumable_commands','INSERT'))
        for table,operation in stages:
            with closing(store.connect()) as db,db:
                db.execute(f"CREATE TRIGGER cake_fail BEFORE {operation} ON {table} BEGIN SELECT RAISE(ABORT,'cake write failed'); END")
            snapshot=inv.immutable_snapshot()
            refused(lambda:eat(fault,31269,'cake:fault'),(sqlite3.IntegrityError,))
            assert inv.immutable_snapshot()==snapshot
            with closing(store.connect()) as db,db:db.execute('DROP TRIGGER cake_fail')
        snapshot=inv.immutable_snapshot()
        def late(*args,**kwargs):raise RuntimeError('late caller failure')
        refused(lambda:eat(fault,31269,'cake:fault',precommit=late),(RuntimeError,))
        with patch('inventory.pet_record',side_effect=RuntimeError('late wire failure')):
            refused(lambda:eat(fault,31269,'cake:fault'),(RuntimeError,))
        with patch('inventory.cake_notice',side_effect=RuntimeError('late success notice failure')):
            refused(lambda:eat(fault,31269,'cake:fault'),(RuntimeError,))
        assert inv.immutable_snapshot()==snapshot
        # A distinct bound one-item pile is deleted, its paid retry still works,
        # and a cake's binding does not change the pet's binding flags.
        inv.grant_item(31268,1,binding=1)
        one=next(i.id for i in inv.immutable_snapshot().items if i.template_id==31268 and i.binding==1)
        flags=state(boundary).flags
        one_body=struct.pack('>iiQ',one,1,boundary)
        inv.receive_pet_consumable(one_body,inv.epoch,'cake:one-bound')
        assert all(i.id!=one for i in inv.immutable_snapshot().items) and state(boundary).flags==flags
        snapshot=inv.immutable_snapshot();inv.receive_pet_consumable(one_body,inv.epoch,'cake:one-bound')
        assert inv.immutable_snapshot()==snapshot
        eat(fault,31269,'cake:fault')
        assert state(fault).cake.count==1
        # Paid lower Interface is SQL-readonly and has no hot config/nested connection.
        snapshot=inv.immutable_snapshot()
        with closing(store.connect()) as db,db:
            db.execute('BEGIN')
            db.set_authorizer(lambda a,*args:sqlite3.SQLITE_DENY if a in
                (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE) else sqlite3.SQLITE_OK)
            with patch.object(Path,'read_text',side_effect=AssertionError('hot config')),patch.object(store,'connect',side_effect=AssertionError('nested connection')):
                assert inv.use_pet_cake(db,next(i.id for i in snapshot.items if i.template_id==31269),
                    fault,inv.epoch,'cake:fault').replayed
        assert inv.immutable_snapshot()==snapshot
        # Unknown old count is not guessed0, wrong key/template/version/owner
        # and generic legacy use reject before any spending.
        with closing(store.connect()) as db,db:db.execute('DELETE FROM inventory_pet_cakes WHERE pet_id=?',(fault,))
        snapshot=inv.immutable_snapshot();refused(lambda:eat(fault,31268,'cake:unknown'))
        assert inv.immutable_snapshot()==snapshot
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            refused(lambda:inv.use_pet_cake(db,item(31269),wild,inv.epoch,'cake:wrong-version',999999))
        from inventory import USE_ITEM
        refused(lambda:inv.receive(USE_ITEM,struct.pack('>iiQ',item(31269),1,wild)))
        inv.grant_item(31275,1);snapshot=inv.immutable_snapshot()
        refused(lambda:eat(boundary,31275,'cake:not-a-named-cake'))
        assert inv.immutable_snapshot()==snapshot
        other_role=store.create_role(1111,'未知年糕钱包',12,1010101)
        other_epoch=store.acquire_lease(1111,other_role['id'])
        other=Inventory(store,1111,other_role['id'],config,epoch=other_epoch)
        foreign=other.grant_pet(500001);other.grant_item(31268)
        other_key=next(i.id for i in other.immutable_snapshot().items if i.template_id==31268)
        snapshot=other.immutable_snapshot()
        refused(lambda:other.receive_pet_consumable(struct.pack('>iiQ',other_key,1,foreign),other_epoch,'cake:unknown-wallet'))
        assert other.immutable_snapshot()==snapshot
        snapshot=inv.immutable_snapshot()
        refused(lambda:inv.receive_pet_consumable(struct.pack('>iiQ',item(31269),1,foreign),inv.epoch,'cake:foreign-pet'))
        refused(lambda:inv.receive_pet_consumable(struct.pack('>iiQ',other_key,1,boundary),inv.epoch,'cake:foreign-item'))
        assert inv.immutable_snapshot()==snapshot
        # Historical released pet receives a current removal, never a revived BASE.
        inv.free_pet(wild);snapshot=inv.immutable_snapshot()
        replay=inv.receive_pet_consumable(struct.pack('>iiQ',item(31269),1,wild),inv.epoch,'cake:wild')
        from inventory import REMOVE_PET
        assert (REMOVE_PET,struct.pack('>ii',1,wild)) in replay and inv.immutable_snapshot()==snapshot
        from native_gameplay_probe import probe
        probe(0xdc0f10,0xe540d0,0xdc0f40,payload=next(b for t,b in replay if t==REMOVE_PET),factory=True)
        # Reopen a real historical four-column audit schema. Startup indexes
        # identities from complete receipts even when the spent item is gone.
        with closing(store.connect()) as db,db:
            historical=db.execute('SELECT role_id,request_id,fingerprint,result FROM inventory_pet_cake_receipts ORDER BY role_id,request_id').fetchall()
            db.execute('CREATE TABLE cake_old_audit(role_id INTEGER NOT NULL,request_id TEXT NOT NULL,fingerprint TEXT NOT NULL,result TEXT NOT NULL,PRIMARY KEY(role_id,request_id))')
            db.executemany('INSERT INTO cake_old_audit VALUES(?,?,?,?)',historical)
            db.execute('DROP TABLE inventory_pet_cake_receipts')
            db.execute('ALTER TABLE cake_old_audit RENAME TO inventory_pet_cake_receipts')
        snapshot=inv.immutable_snapshot()
        Inventory.prepare(store)
        assert inv.immutable_snapshot()==snapshot
        with closing(store.connect()) as db:
            assert db.execute('SELECT role_id,request_id,fingerprint,result FROM inventory_pet_cake_receipts ORDER BY role_id,request_id').fetchall()==historical
            assert db.execute('SELECT pet_id,item_key FROM inventory_pet_cake_receipts WHERE role_id=? AND request_id=?',(inv.role_id,'cake:one-bound')).fetchone()==(boundary,one)
        inv.receive_pet_consumable(one_body,inv.epoch,'cake:one-bound')
        assert inv.immutable_snapshot()==snapshot
        # Current opaque owner and reopen work; obsolete paid requests are fenced.
        old_epoch=inv.epoch;token='年糕:00041'
        with closing(store.connect()) as db,db:db.execute('UPDATE role_leases SET epoch=? WHERE role_id=?',(token,role['id']))
        active=Inventory(store,1111,role['id'],config,epoch=token,currency_rules=inv.currency_rules)
        active.receive_pet_consumable(struct.pack('>iiQ',item(31269),1,boundary),token,'cake:opaque')
        snapshot=active.immutable_snapshot()
        active.receive_pet_consumable(struct.pack('>iiQ',item(31269),1,boundary),token,'cake:opaque')
        assert active.immutable_snapshot()==snapshot
        refused(lambda:inv.receive_pet_consumable(body,old_epoch,'cake:A'))
        assert Inventory(AccountStore(store.path),1111,role['id'],config).immutable_snapshot()==snapshot
    report={'passed':['all5 named cakes original native predicted base increments/count/history/native success params and stable single debit',
        'shared total20 cap/no-effect/max/kind2 refusals without spending; fairy and wild supported according to native gates',
        'cake invalidates super BASE source; save resets actual cake effects and reopens count20; no double blood buff or healing/revival',
        'actual native rounding8 vs rational9 boundary audited, BASE+8/effective+9; current XP/allocation/skills/binding preserved',
        '5 actual write faults plus caller/native encoding failure roll all state/receipts back; same failed key retries once',
        'low-level-only paid and wrapper history strictly readonly/no new success; no hot IO; unknown old history/versions/legacy route rejected',
        'released paid current removal; current opaque owner/replay/reopen and stale owner fencing'],
        'live_server_changed':False,'native_gui_verified':False,
        'shared_route_evidence':'pet-cake-shared-gate.json and pet-cake-runtime-verification.json'}
    write_json(OUT/'evidence/pet-cake-consumables-verification.json',report)
    print('PASS',', '.join(report['passed']))


if __name__=='__main__':main()
