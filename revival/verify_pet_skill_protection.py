"""Public certification learning/progress seam; real disposable storage."""
from pathlib import Path
from tempfile import TemporaryDirectory
from contextlib import closing
from dataclasses import FrozenInstanceError
import sqlite3
import struct
import hashlib
import json

from accounts import AccountStore
from inventory import Inventory,REFRESH_PET,PET_INFO,LEARN_SKILL_BOOK
from research_pet_skill_progress import native_progress
from research_pet_skills import native_record_skills
from research_pet_binding import native_column_bindings
from pet_protocol import SkillBookOptions
from pet_skill_progress import SkillProgress
from inspect_client import OUT,write_json


def refused(action):
    try:action()
    except ValueError:return
    raise AssertionError('Invalid certification or unknown expansion progress accepted')
from inventory_test_support import known_cash_context


def main():
    with TemporaryDirectory() as tmp:
        store=AccountStore(Path(tmp)/'state.sqlite3')
        role=store.create_role(1111,'认证拓格',12,1010101)
        config=Inventory.prepare(store)
        inv=Inventory(store,1111,role['id'],config,
            **known_cash_context(store,1111,role['id'],balances=(71,0,0,0)))
        pet=inv.grant_pet(500001)
        def state(pid):return next(p for p in inv.snapshot()['pets'] if p['id']==pid)
        def grant(template,n=1):
            inv.grant_item(template,n)
            return next(i['id'] for i in inv.snapshot()['items'] if i['template_id']==template)
        def use(pid,book,key,draws=(9999,0),basic=-1,advanced=-1,first=-1,second=-1):
            return inv.receive_pet_skill_book(struct.pack('>6i',pid,book,basic,advanced,first,second),inv.epoch,key,draws)
        current=next(p for p in inv.snapshot()['pets'] if p['id']==pet)
        progress=current.get('skill_progress')
        assert progress is not None and progress.points==0, 'New pet still has unknown expansion progress'
        inv.grant_item(31003,2);inv.grant_item(31254,2)
        items=inv.snapshot()['items']
        book=next(i['id'] for i in items if i['template_id']==31003)
        basic=next(i['id'] for i in items if i['template_id']==31254)
        inv.receive_pet_skill_book(struct.pack('>6i',pet,book,basic,-1,200091,-1),
                                   inv.epoch,'cert:basic',(9999,0))
        current=next(p for p in inv.snapshot()['pets'] if p['id']==pet)
        assert current['skills'].learned==(200091,200011)
        assert current['skill_progress'].points==2
        assert {i['template_id']:i['quantity'] for i in inv.snapshot()['items']}=={31003:1,31254:1}
        progress_reply=inv.receive(0xc0800,b'')
        assert len(progress_reply)==1 and progress_reply[0][0]==0xc0801
        assert native_progress(progress_reply[0][1],selected=pet,skill_count=2,threshold=20)['displayed_progress']==2
        before=inv.immutable_snapshot()
        replay=use(pet,book,'cert:basic',basic=basic,first=200091)
        assert inv.immutable_snapshot()==before
        assert native_record_skills(next(b for k,b in replay if k==REFRESH_PET))[0]==(200091,200011)
        try:inv.immutable_snapshot().pets[0].skill_progress.points=999
        except FrozenInstanceError:pass
        else:raise AssertionError('Mutable cross-owner expansion progress')
        # A known one-skill historical pet, protected by a basic certificate:
        # five failed attempts collect2 each, then the next is guaranteed.
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            protected_pet=db.execute('INSERT INTO inventory_pets(role_id,template_id,name) VALUES(?,?,?)',
                (role['id'],500001,'已核对单技能宠')).lastrowid
            inv.initialize_pet_care(db,protected_pet,1,100,6000)
            inv.initialize_pet_growth(db,protected_pet)
            inv.initialize_pet_skills(db,protected_pet,(200091,))
            inv.initialize_pet_flags(db,protected_pet,0)
            inv.initialize_pet_skill_progress(db,protected_pet,0)
            inv.initialize_pet_skill_expiry(db,protected_pet,())
        book2=grant(31013,6);basic2=grant(31254,5)
        for index,points in enumerate((2,4,6,8,10)):
            use(protected_pet,book2,'cert:all:'+str(index),basic=basic2,first=200091)
            current=state(protected_pet)
            assert current['skills'].learned==(200091,)
            assert current['skills'].version==index+1 and current['skill_progress'].points==points
        guaranteed=use(protected_pet,book2,'cert:guaranteed',basic=basic2,first=200091)
        assert state(protected_pet)['skills'].learned==(200091,200061)
        assert state(protected_pet)['skill_progress']==SkillProgress(6,0)
        assert not any(i['template_id'] in (31013,31254) for i in inv.snapshot()['items'])
        # The official table specifies100% with two skills and both certificates.
        expand_book=grant(31005);expand_basic=grant(31254);expand_advanced=grant(31255)
        use(protected_pet,expand_book,'cert:both-two-skills',basic=expand_basic,advanced=expand_advanced,
            first=200091,second=200061)
        assert state(protected_pet)['skills'].learned==(200091,200061,200021)
        assert state(protected_pet)['skill_progress']==SkillProgress(6,0)
        assert not any(i['template_id'] in (31005,31254,31255) for i in inv.snapshot()['items'])
        before=inv.immutable_snapshot()
        late=use(protected_pet,book2,'cert:all:0',basic=basic2,first=200091)
        assert inv.immutable_snapshot()==before
        assert native_record_skills(next(b for k,b in late if k==REFRESH_PET))[0]==(200091,200061,200021)
        assert native_progress(next(b for k,b in late if k==0xc0801),selected=protected_pet,skill_count=3,threshold=40)['displayed_progress']==0
        # A valid protected-all failed binding-book attempt does not bind. A
        # later actual learning action binds and refreshes the full column.
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            bound_pet=db.execute('INSERT INTO inventory_pets(role_id,template_id,name) VALUES(?,?,?)',
                (role['id'],500001,'已核对单技能绑定宠')).lastrowid
            inv.initialize_pet_care(db,bound_pet,1,100,6000)
            inv.initialize_pet_growth(db,bound_pet)
            inv.initialize_pet_skills(db,bound_pet,(200091,))
            inv.initialize_pet_flags(db,bound_pet,0)
            inv.initialize_pet_skill_progress(db,bound_pet,0)
            inv.initialize_pet_skill_expiry(db,bound_pet,())
        bound_book=grant(31956,2);bc=grant(31254,2)
        use(bound_pet,bound_book,'cert:bound-failure',basic=bc,first=200091)
        assert not state(bound_pet)['flags'].bound and state(bound_pet)['skill_progress'].points==2
        bound_reply=use(bound_pet,bound_book,'cert:bound-success',(0,0),bc,first=200091)
        assert state(bound_pet)['flags'].bound and state(bound_pet)['skill_progress'].points==0
        assert (bound_pet,2,True) in native_column_bindings(next(b for k,b in bound_reply if k==PET_INFO))
        failure_pet=inv.grant_pet(500001)
        failure_book=grant(31007,2);fc=grant(31254,3);fa=grant(31255,3);wrong=grant(31000)
        body=struct.pack('>6i',failure_pet,failure_book,fc,-1,200091,-1)
        before=inv.immutable_snapshot()
        for values in ((failure_pet,failure_book,0,-1,-1,-1),
            (failure_pet,failure_book,-1,fa,-1,200061),
            (failure_pet,failure_book,-1,-1,200091,-1),
            (failure_pet,failure_book,fc,fa,200091,200091),
            (failure_pet,failure_book,fc,-1,200012,-1),
            (failure_pet,failure_book,wrong,-1,200091,-1),
            (failure_pet,failure_book,fc,wrong,200091,200061),
            (failure_pet,failure_book,fc,fc,200091,200061),
            (failure_pet,failure_book,failure_book,-1,200091,-1)):
            refused(lambda values=values:inv.receive_pet_skill_book(struct.pack('>6i',*values),inv.epoch,'cert:invalid',(9999,0)))
            assert inv.immutable_snapshot()==before
        refused(lambda:inv.receive_pet_skill_book(body[:-1],inv.epoch,'cert:short',(9999,0)))
        refused(lambda:inv.receive(LEARN_SKILL_BOOK,body))
        refused(lambda:inv.receive(0xc0800,b'\0'))
        refused(lambda:inv.receive_pet_skill_progress(b'',inv.epoch+1))
        for table,action in (('inventory_pet_skill_progress','UPDATE'),('inventory_pet_skill_receipts','INSERT')):
            with closing(store.connect()) as db:
                db.execute(f"CREATE TRIGGER fail_certification BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT,'certification save failure'); END")
            try:inv.receive_pet_skill_book(body,inv.epoch,'cert:save-failure',(9999,0))
            except sqlite3.IntegrityError:pass
            else:raise AssertionError('Actual progress/receipt save failure did not execute')
            assert inv.immutable_snapshot()==before
            with closing(store.connect()) as db:db.execute('DROP TRIGGER fail_certification')
        unknown_wallet=Inventory(store,1111,role['id'],config,epoch=inv.epoch)
        refused(lambda:unknown_wallet.receive_pet_skill_book(body,inv.epoch,'cert:no-wallet',(9999,0)))
        assert inv.immutable_snapshot()==before
        try:
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                inv.learn_pet_skill(db,failure_book,failure_pet,inv.epoch,'cert:outer',0,(9999,0),
                                    options=SkillBookOptions(fc,-1,200091,-1))
                raise RuntimeError('downstream common receipt failure')
        except RuntimeError:pass
        assert inv.immutable_snapshot()==before
        inv.receive_pet_skill_book(body,inv.epoch,'cert:save-failure',(9999,0))
        assert state(failure_pet)['skills'].learned==(200091,200031)
        assert state(failure_pet)['skill_progress'].points==2
        before=inv.immutable_snapshot()
        refused(lambda:inv.receive_pet_skill_book(body,inv.epoch,'cert:save-failure',(9998,0)))
        assert inv.immutable_snapshot()==before
        # Two protections with a third replaceable skill leave both protected
        # IDs intact and select only the remaining position.
        replace_book=grant(31009)
        use(protected_pet,replace_book,'cert:two-protected-replacement',basic=fc,advanced=fa,first=200091,second=200061)
        assert state(protected_pet)['skills'].learned==(200091,200061,200041)
        assert state(protected_pet)['skill_progress'].points==5
        # Explicit legacy import of historical progress, never default0.
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            legacy=db.execute('INSERT INTO inventory_pets(role_id,template_id,name) VALUES(?,?,?)',
                (role['id'],500001,'进度未知旧宠')).lastrowid
            inv.initialize_pet_care(db,legacy,1,100,6000)
            inv.initialize_pet_growth(db,legacy)
            inv.initialize_pet_skills(db,legacy,(200091,200061))
            inv.initialize_pet_skill_expiry(db,legacy,())
            inv.initialize_pet_flags(db,legacy,0)
        assert state(legacy).get('skill_progress') is None
        before=inv.immutable_snapshot()
        refused(lambda:use(legacy,book,'cert:unknown-progress'))
        refused(lambda:inv.receive(0xc0800,b''))
        assert inv.immutable_snapshot()==before
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            inv.initialize_pet_skill_progress(db,legacy,19)
            refused(lambda:inv.initialize_pet_skill_progress(db,legacy,0))
        assert state(legacy)['skill_progress']==SkillProgress(0,19)
        assert native_progress(inv.receive(0xc0800,b'')[0][1],selected=legacy,skill_count=2,threshold=20)['displayed_progress']==19
        inv.free_pet(legacy)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            refused(lambda:inv.initialize_pet_skill_progress(db,legacy,0))
        # Explicit chance boundaries from the official table, through actual
        # item debit and persistence, including boost-only certification.
        chance_book=grant(31011,4);chance_basic=grant(31254,4);chance_advanced=grant(31255,2)
        for index,(draw,advanced,count,points) in enumerate(((1999,-1,3,0),(2000,-1,2,2),
                (1999,chance_advanced,4,0),(2000,chance_advanced,3,5))):
            chance_pet=inv.grant_pet(500001)
            if advanced!=-1:
                bootstrap=grant(31009)
                use(chance_pet,bootstrap,'cert:bootstrap:'+str(index),(0,0))
            use(chance_pet,chance_book,'cert:chance:'+str(index),(draw,0),chance_basic,advanced)
            assert len(state(chance_pet)['skills'].learned)==count
            assert state(chance_pet)['skill_progress'].points==points
            if index==0:
                cap_book=grant(31009)
                use(chance_pet,cap_book,'cert:reach-cap',(0,0))
                assert len(state(chance_pet)['skills'].learned)==4
                use(chance_pet,failure_book,'cert:already-capped',(0,0),chance_basic,first=200091)
                assert len(state(chance_pet)['skills'].learned)==4 and state(chance_pet)['skill_progress'].points==0
            inv.free_pet(chance_pet)
        # Protected in-place upgrade is invalid; protecting another skill keeps
        # the already-earned progress unchanged on the valid upgrade.
        upgrade=grant(31004);upcert=grant(31254)
        before=inv.immutable_snapshot()
        refused(lambda:use(pet,upgrade,'cert:protected-upgrade',basic=upcert,first=200011))
        assert inv.immutable_snapshot()==before
        use(pet,upgrade,'cert:upgrade',basic=upcert,first=200091)
        assert state(pet)['skills'].learned==(200091,200012) and state(pet)['skill_progress'].points==2
        # The smallest official probability is0.02%, requiring two successes
        # out of10000 server draws rather than rounding away in a1000 range.
        rare_book=grant(31019,2)
        for draw,count in ((1,12),(2,11)):
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                rare_pet=db.execute('INSERT INTO inventory_pets(role_id,template_id,name) VALUES(?,?,?)',
                    (role['id'],500001,'已核对11技能宠'+str(draw))).lastrowid
                inv.initialize_pet_care(db,rare_pet,6,100,6000)
                inv.initialize_pet_growth(db,rare_pet)
                inv.initialize_pet_skills(db,rare_pet,(200011,200021,200031,200041,200051,200061,
                                                       200071,200081,200101,200111,200121))
                inv.initialize_pet_flags(db,rare_pet,0)
                inv.initialize_pet_skill_progress(db,rare_pet,0)
                inv.initialize_pet_skill_expiry(db,rare_pet,())
            use(rare_pet,rare_book,'cert:rare:'+str(draw),(draw,0))
            assert len(state(rare_pet)['skills'].learned)==count
            assert state(rare_pet)['skill_progress'].points==(0 if count==12 else 1)
            if count==12:
                cap12_book=grant(31027)
                use(rare_pet,cap12_book,'cert:twelve-cap',(0,0))
                assert len(state(rare_pet)['skills'].learned)==12 and state(rare_pet)['skill_progress'].points==0
        before=inv.immutable_snapshot()
        refused(lambda:use(failure_pet,book,'cert:bad-range',(10000,0)))
        refused(lambda:use(failure_pet,book,'cert:bool-draw',(True,0)))
        assert inv.immutable_snapshot()==before
        # Historical v1 receipt shape/fingerprint is a fixture from the old
        # implementation. Replay must acknowledge it without resetting current
        # IDs or assigning retroactive expansion points.
        old_result={'settlement_id':'cert:legacy-ack','pet_id':pet,'item_key':book,'skill_id':200011,
            'replaced_skill_id':None,'before':{'version':0,'learned':[200091,200061]},
            'after':{'version':1,'learned':[200091,200061,200011]},'flags_before':None,'flags_after':None}
        old_fp=hashlib.sha256(json.dumps([pet,book,None,(0,0),'2026-10-23.pet-skills.1']).encode()).hexdigest()
        with closing(store.connect()) as db,db:
            db.execute('INSERT INTO inventory_pet_skill_receipts VALUES(?,?,?,?,?)',
                (role['id'],pet,'cert:legacy-ack',old_fp,json.dumps(old_result)))
        before=inv.immutable_snapshot()
        history=use(pet,book,'cert:legacy-ack',(0,0))
        assert inv.immutable_snapshot()==before
        assert native_record_skills(next(b for k,b in history if k==REFRESH_PET))[0]==(200091,200012)
        assert native_progress(next(b for k,b in history if k==0xc0801),selected=pet,skill_count=2,threshold=20)['displayed_progress']==2
        # Foreign certificate ownership and read-transaction requirements.
        foreign_role=store.create_role(1111,'别人的认证符',12,1010101)
        foreign_inv=Inventory(store,1111,foreign_role['id'],config)
        foreign_inv.grant_item(31254)
        foreign_cert=foreign_inv.snapshot()['items'][0]['id']
        refused(lambda:use(failure_pet,book,'cert:foreign-item',basic=foreign_cert,first=200091))
        with closing(store.connect()) as db:
            refused(lambda:inv.pet_skill_progress_messages(db,inv.epoch))
            db.execute('BEGIN')
            refused(lambda:inv.pet_skill_progress_messages(db,inv.epoch,(2**63,)))
        assert inv.immutable_snapshot()==before
        assert Inventory(AccountStore(store.path),1111,role['id'],config).snapshot()==inv.snapshot()
        # Actual fenced Adapter accepts the same opaque owner identity used by
        # other modules, and the replaced int lease cannot learn/query further.
        store.inventory_config=config;token='宠物技能所有者:00007'
        with closing(store.connect()) as db,db:
            db.execute('UPDATE role_leases SET epoch=? WHERE role_id=?',(token,role['id']))
        active=Inventory(store.leased(1111,role['id'],token),1111,role['id'],config,
                         epoch=token,currency_rules=inv.currency_rules)
        before=active.immutable_snapshot()
        refused(lambda:inv.receive_pet_skill_progress(b'',inv.epoch))
        assert active.immutable_snapshot()==before
        active.grant_item(31254)
        opaque_cert=next(i['id'] for i in active.snapshot()['items'] if i['template_id']==31254)
        active.receive_pet_skill_book(struct.pack('>6i',protected_pet,book,opaque_cert,-1,200091,-1),
                                      token,'cert:opaque-owner',(9999,1))
        assert native_progress(active.receive_pet_skill_progress(b'',token)[0][1],selected=protected_pet,
                               skill_count=3,threshold=40)['displayed_progress']==7
        assert Inventory(AccountStore(store.path),1111,role['id'],config).snapshot()==active.snapshot()
    report={'passed':['new pets have explicit frozen known0 progress; old unknowns require one-time historical import',
        'basic/advanced certification selects exact distinct learned IDs and debits one of each atomically',
        'one protected skill failures accumulate2; threshold10 forces next expansion and resets',
        'official count2 basic1999/2000 and count3 combined1999/2000 boundaries; count2 both100% verified',
        'official eleven-skill0.02% distinguishes draw1/2 exactly in10000 range; twelve-skill cap remains stable',
        'boost-only selection supported; protected upgrade refuses; other protection permits upgrade without progress change',
        'failed bound-book attempt does not bind; actual learning binds and stages original full-column reply',
        'old request replies current skills/progress without repeated book/cert debit',
        'real progress and receipt abort, outer exception and missing wallet roll back whole attempt',
        'bad item/type/pair/skill/duplicate/short/query/current-lease context refuses before consumption',
        'two protections exclude both from replacement; color cap does not accumulate expansion points',
        'old v1 receipt remains readable without retroactive progress; real opaque fenced learning and query succeed',
        'original progress codec/merge/lookup/bar consumes replies; reopen preserves all state'],
        'learning_algorithm':'pet-skill-learning-v3: guide_supported probabilities; designed guarantee/state machine; client_verified source values/layout',
        'shared_c07ff_route_connected':False,'native_gui_tested':False}
    write_json(OUT/'evidence/pet-skill-protection-verification.json',report)
    print('PASS:',', '.join(report['passed']))


if __name__=='__main__':main()
