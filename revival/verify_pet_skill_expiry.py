"""Timed pet skills through the Inventory transaction/snapshot/native seams."""
from pathlib import Path
from tempfile import TemporaryDirectory
from contextlib import closing
from dataclasses import FrozenInstanceError
import struct
import sqlite3
import hashlib
import json

from accounts import AccountStore
from inventory import Inventory,pet_record,REFRESH_PET,PET_INFO,USE_ITEM
from inventory_test_support import known_cash_context
from research_pet_skill_expiry import native_timed_record
from research_pet_binding import native_column_bindings
from pet_skill_expiry import TimedSkillGrant
from pet_protocol import SkillBookOptions
from inspect_client import OUT,write_json


def refused(action):
    try:action()
    except ValueError:return
    raise AssertionError('Unknown or invalid pet expiry accepted')


def main():
    with TemporaryDirectory() as tmp:
        store=AccountStore(Path(tmp)/'state.sqlite3')
        role=store.create_role(1111,'限时技能',12,1010101)
        config=Inventory.prepare(store)
        inv=Inventory(store,1111,role['id'],config,
            **known_cash_context(store,1111,role['id'],balances=(71,0,0,0)))
        pet=inv.grant_pet(500001)
        state=next(p for p in inv.snapshot()['pets'] if p['id']==pet)
        assert state.get('skill_expiry') is not None,'New pet expiry metadata is still unknown'
        assert state['skill_expiry'].entries==()
        # A full explicit historical map, never guessed from a missing row.
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            old=db.execute('INSERT INTO inventory_pets(role_id,template_id,name) VALUES(?,?,?)',
                (role['id'],500001,'原技能到期宠')).lastrowid
            inv.initialize_pet_care(db,old,1,100,6000)
            inv.initialize_pet_growth(db,old)
            inv.initialize_pet_skills(db,old,(200484,200061))
            inv.initialize_pet_flags(db,old,0)
            inv.initialize_pet_skill_progress(db,old,7)
            refused(lambda:inv.pet_skill_view(db,old,inv.epoch,1000))
            inv.initialize_pet_skill_expiry(db,old,((200484,1000),))
            refused(lambda:inv.initialize_pet_skill_expiry(db,old,()))
        for now,active,slots,expired,next_change in (
            (999,(200484,200061),(200484,200061),(),1001),
            (1000,(200484,200061),(200484,200061),(),1001),
            (1001,(200061,),(200534,200061),(200484,),None)):
            before=inv.immutable_snapshot()
            with closing(store.connect()) as db:
                db.execute('BEGIN')
                view=inv.pet_skill_view(db,old,inv.epoch,now)
                assert (view.active_ids,view.slot_ids,view.expired_ids,view.next_change_ms)==(active,slots,expired,next_change)
                refused(lambda:inv.pet_skill_view(db,old,inv.epoch+1,now))
                refused(lambda:inv.pet_skill_view(db,old,inv.epoch,True))
            assert inv.immutable_snapshot()==before
            raw=next(p for p in inv.snapshot()['pets'] if p['id']==old)
            assert raw['skills'].learned==(200484,200061) and raw['skill_expiry'].entries==((200484,1000),)
            copied,icons,clock=native_timed_record(pet_record(raw),now)
            assert copied==(200484,200061) and tuple(v[1] for v in icons)==slots
            assert clock['server_ms']==now
        try:view.active_ids=()
        except FrozenInstanceError:pass
        else:raise AssertionError('Mutable timed battle view')
        inv.grant_item(31003,2)
        book=next(i['id'] for i in inv.snapshot()['items'] if i['template_id']==31003)
        body=struct.pack('>6i',old,book,-1,-1,-1,-1)
        before=inv.immutable_snapshot()
        refused(lambda:inv.receive_pet_skill_book(body,inv.epoch,'expiry:no-time',(9999,0)))
        assert inv.immutable_snapshot()==before
        inv.grant_item(31254)
        cert=next(i['id'] for i in inv.snapshot()['items'] if i['template_id']==31254)
        before=inv.immutable_snapshot()
        refused(lambda:inv.receive_pet_skill_book(struct.pack('>6i',old,book,cert,-1,200484,-1),
            inv.epoch,'expiry:protect-dead',(9999,0),1001))
        assert inv.immutable_snapshot()==before
        # Real storage aborts, outer rollback and pre-commit encoding failure.
        for table in ('inventory_pet_skill_expiry','inventory_pet_skill_receipts'):
            action='UPDATE' if table.endswith('expiry') else 'INSERT'
            with closing(store.connect()) as db:
                db.execute(f"CREATE TRIGGER fail_expiry BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT,'expiry save failed'); END")
            try:inv.receive_pet_skill_book(body,inv.epoch,'expiry:reuse',(9999,0),1001)
            except sqlite3.IntegrityError:pass
            else:raise AssertionError('Actual expiry/receipt abort did not execute')
            assert inv.immutable_snapshot()==before
            with closing(store.connect()) as db:db.execute('DROP TRIGGER fail_expiry')
        no_wallet=Inventory(store,1111,role['id'],config,epoch=inv.epoch)
        refused(lambda:no_wallet.receive_pet_skill_book(body,inv.epoch,'expiry:reuse',(9999,0),1001))
        assert inv.immutable_snapshot()==before
        try:
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                inv.learn_pet_skill(db,book,old,inv.epoch,'expiry:outer',0,(9999,0),now_ms=1001)
                raise RuntimeError('outer settlement failed')
        except RuntimeError:pass
        assert inv.immutable_snapshot()==before
        replies=inv.receive_pet_skill_book(body,inv.epoch,'expiry:reuse',(9999,0),1001)
        assert replies[0]==(0xc0007,struct.pack('>q',1001))
        raw=next(p for p in inv.snapshot()['pets'] if p['id']==old)
        assert raw['skills'].learned==(200011,200061)
        assert raw['skill_progress'].points==7 and raw['skill_expiry'].entries==()
        assert raw['skill_expiry'].version==1
        copied,icons,_=native_timed_record(next(b for k,b in replies if k==REFRESH_PET),1001)
        assert copied==(200011,200061) and tuple(v[1] for v in icons)==(200011,200061)
        before=inv.immutable_snapshot()
        late=inv.receive_pet_skill_book(body,inv.epoch,'expiry:reuse',(9999,0),2000)
        assert inv.immutable_snapshot()==before and late[0]==(0xc0007,struct.pack('>q',2000))
        # A pre-expiry v3 receipt remains an acknowledgement after migration.
        with closing(store.connect()) as db,db:
            fp,result=db.execute('SELECT fingerprint,result FROM inventory_pet_skill_receipts WHERE settlement_id=?',('expiry:reuse',)).fetchone()
            value=json.loads(result)
            for key in ('expiry_before','expiry_after','applied_at_ms','expiry_revision'):value.pop(key)
            previous=hashlib.sha256(json.dumps([old,book,None,(9999,0),inv.skill_rules.revision,
                inv.skill_rules.learning_rules.revision,SkillBookOptions().wire_values]).encode()).hexdigest()
            db.execute('UPDATE inventory_pet_skill_receipts SET fingerprint=?,result=? WHERE settlement_id=?',
                (previous,json.dumps(value),'expiry:reuse'))
        assert inv.receive_pet_skill_book(body,inv.epoch,'expiry:reuse',(9999,0),3000)[0]==(0xc0007,struct.pack('>q',3000))
        assert inv.immutable_snapshot()==before
        command=TimedSkillGrant('expiry:reward',pet,200484,5000,'verified:event:1',0)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            granted=inv.grant_pet_timed_skill(db,command,inv.epoch,2000)
            messages=inv.pet_skill_time_messages(db,inv.epoch,2000,(pet,))
            assert granted.after.learned==(200091,200061,200484)
            assert granted.expiry_after.entries==((200484,5000),)
            assert messages[0]==(0xc0007,struct.pack('>q',2000))
        before=inv.immutable_snapshot()
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            assert inv.grant_pet_timed_skill(db,command,inv.epoch,6000)==granted
            assert inv.pet_skill_view(db,pet,inv.epoch,6000).active_ids==(200091,200061)
        assert inv.immutable_snapshot()==before
        renewed=TimedSkillGrant('expiry:renew',pet,200484,9000,'verified:event:2',1)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            receipt=inv.grant_pet_timed_skill(db,renewed,inv.epoch,6000)
            assert receipt.after.learned==(200091,200061,200484)
            assert receipt.expiry_after.entries==((200484,9000),)
        query=inv.receive_pet_query(struct.pack('>iQ',1,role['id']),inv.epoch,6000)
        assert query[0]==(0xc0007,struct.pack('>q',6000))
        assert native_column_bindings(next(b for k,b in query if k==PET_INFO))==((pet,0,False),(old,0,False))
        # Other gameplay writes preserve absolute expiry, not time remaining.
        inv.rename_pet(pet,'限时宠改名')
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            p=inv.pet_progress(db,pet)
            inv.change_pet_growth(db,pet,'expiry:experience',p.state.version,'experience',1)
            inv.change_pet_care(db,pet,'expiry:defeat',0,'defeat',1)
        inv.grant_item(31000)
        food=next(i['id'] for i in inv.snapshot()['items'] if i['template_id']==31000)
        fed=inv.receive(USE_ITEM,struct.pack('>iiQ',food,1,pet))
        raw=next(p for p in inv.snapshot()['pets'] if p['id']==pet)
        assert raw['skill_expiry'].entries==((200484,9000),) and raw['skills'].version==2
        assert native_timed_record(next(b for k,b in fed if k==REFRESH_PET),9001)[1][-1][1]==200534
        inv.grant_item(31094)
        cosmetic=next(i['id'] for i in inv.snapshot()['items'] if i['template_id']==31094)
        inv.receive_pet_skill_book(struct.pack('>6i',pet,cosmetic,-1,-1,-1,-1),
            inv.epoch,'expiry:same-id-permanent',(9999,0),10000)
        raw=next(p for p in inv.snapshot()['pets'] if p['id']==pet)
        assert raw['skills'].learned==(200091,200061,200484) and raw['skill_expiry'].entries==()
        # Multiple actual empty markers are reusable slots, never abilities.
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            empty=db.execute('INSERT INTO inventory_pets(role_id,template_id,name) VALUES(?,?,?)',
                (role['id'],500001,'空技能格')).lastrowid
            inv.initialize_pet_care(db,empty,1,100,6000)
            inv.initialize_pet_growth(db,empty)
            inv.initialize_pet_skills(db,empty,(200534,200061,200534))
            inv.initialize_pet_skill_progress(db,empty,9)
            inv.initialize_pet_flags(db,empty,0)
            inv.initialize_pet_skill_expiry(db,empty,())
            assert inv.pet_skill_view(db,empty,inv.epoch,10000).active_ids==(200061,)
        inv.receive_pet_skill_book(struct.pack('>6i',empty,book,-1,-1,-1,-1),
            inv.epoch,'expiry:empty-first',(9999,0),10000)
        inv.grant_item(31005);inv.grant_item(31099)
        items=inv.snapshot()['items']
        second=next(i['id'] for i in items if i['template_id']==31005)
        placeholder=next(i['id'] for i in items if i['template_id']==31099)
        inv.receive_pet_skill_book(struct.pack('>6i',empty,second,-1,-1,-1,-1),
            inv.epoch,'expiry:empty-second',(9999,0),10000)
        raw=next(p for p in inv.snapshot()['pets'] if p['id']==empty)
        assert raw['skills'].learned==(200011,200061,200021) and raw['skill_progress'].points==9
        before=inv.immutable_snapshot()
        refused(lambda:inv.receive_pet_skill_book(struct.pack('>6i',empty,placeholder,-1,-1,-1,-1),
            inv.epoch,'expiry:placeholder-book',(9999,0),10000))
        assert inv.immutable_snapshot()==before
        # Failed trusted grants leave no metadata, skill change or receipt.
        fresh=inv.grant_pet(500001)
        fail_command=TimedSkillGrant('expiry:grant-abort',fresh,200484,20000,'verified:event:3',0)
        before=inv.immutable_snapshot()
        for table,action in (('inventory_pet_skill_expiry','UPDATE'),('inventory_pet_timed_skill_receipts','INSERT')):
            with closing(store.connect()) as db:
                db.execute(f"CREATE TRIGGER fail_expiry BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT,'timed grant failed'); END")
            try:
                with closing(store.connect()) as db,db:
                    db.execute('BEGIN IMMEDIATE')
                    inv.grant_pet_timed_skill(db,fail_command,inv.epoch,10000)
            except sqlite3.IntegrityError:pass
            else:raise AssertionError('Actual timed grant abort did not execute')
            assert inv.immutable_snapshot()==before
            with closing(store.connect()) as db:db.execute('DROP TRIGGER fail_expiry')
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            refused(lambda:inv.grant_pet_timed_skill(db,fail_command,inv.epoch+1,10000))
            refused(lambda:inv.grant_pet_timed_skill(db,fail_command,inv.epoch,20000))
            refused(lambda:inv.pet_skill_time_messages(db,inv.epoch,10000,(fresh,fresh)))
            refused(lambda:inv.pet_skill_time_messages(db,inv.epoch,True,()))
            for entries in (((200011,1000),(200011,2000)),((200011,True),),((200534,1000),),((200484,1000),)):
                refused(lambda entries=entries:inv.initialize_pet_skill_expiry(db,empty,entries))
        assert inv.immutable_snapshot()==before
        inv.grant_item(31007)
        legacy_book=next(i['id'] for i in inv.snapshot()['items'] if i['template_id']==31007)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            unknown=db.execute('INSERT INTO inventory_pets(role_id,template_id,name) VALUES(?,?,?)',
                (role['id'],500001,'未知到期旧宠')).lastrowid
            inv.initialize_pet_care(db,unknown,1,100,6000)
            inv.initialize_pet_growth(db,unknown)
            inv.initialize_pet_skills(db,unknown,(200091,200061))
            inv.initialize_pet_flags(db,unknown,0)
            inv.initialize_pet_skill_progress(db,unknown,0)
        before=inv.immutable_snapshot()
        unknown_body=struct.pack('>6i',unknown,legacy_book,-1,-1,-1,-1)
        refused(lambda:inv.receive_pet_skill_book(unknown_body,inv.epoch,'expiry:unknown',(0,0),10000))
        assert inv.immutable_snapshot()==before and next(p for p in before.pets if p.id==unknown).skill_expiry is None
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            inv.initialize_pet_skill_expiry(db,unknown,())
        inv.receive_pet_skill_book(unknown_body,inv.epoch,'expiry:unknown',(0,0),10000)
        assert next(p for p in inv.immutable_snapshot().pets if p.id==unknown).skills.learned==(200091,200061,200031)
        reopened=Inventory(store,1111,role['id'],config,epoch=inv.epoch)
        assert reopened.immutable_snapshot()==inv.immutable_snapshot()
        store.inventory_config=config;token='限时技能:00007'
        with closing(store.connect()) as db,db:
            db.execute('UPDATE role_leases SET epoch=? WHERE role_id=?',(token,role['id']))
        active=Inventory(store.leased(1111,role['id'],token),1111,role['id'],config,
            epoch=token,currency_rules=inv.currency_rules)
        refused(lambda:inv.receive_pet_query(struct.pack('>iQ',1,role['id']),inv.epoch,10000))
        with closing(active.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            committed=active.grant_pet_timed_skill(db,fail_command,token,10000)
            assert committed.after.learned==(200091,200061,200484)
            assert active.pet_skill_view(db,fresh,token,20001).active_ids==(200091,200061)
        assert active.receive_pet_query(struct.pack('>iQ',1,0),token,20001)[0]==(0xc0007,struct.pack('>q',20001))
    report={'passed':['new known empty map; historical complete one-time import; missing expiry never inferred',
        'original clock and Pet codec display equality active and strictly past empty while retaining raw IDs',
        'immutable effective IDs contain neither expired abilities nor empty markers',
        'expired-slot reuse holds expansion points; same expired ID renews without duplicate; multiple empty slots reusable',
        'expired protection and internal empty-skill book refuse without spending',
        'trusted timed grant/extension/replay stages current clock and keeps raw audit',
        'learning and grant actual expiry/receipt abort, outer rollback and missing wallet preserve whole snapshot',
        'v3 pre-expiry receipt compatibility; timed replay refreshes current time without repeat consumption',
        'rename/XP/food preserve deadlines; timed full-column query and original converter remain valid',
        'strict time/lease/map/context guards; actual opaque LeasedAccounts query/grant/view; reopen persists exact frozen metadata'],
        'source_status':'client_verified wire/time/empty icon; designed persistence/grant/slot reuse',
        'shared_route_connected':False,'native_gui_tested':False,'battle_effects_tested':False}
    write_json(OUT/'evidence/pet-skill-expiry-verification.json',report)
    print('PASS',', '.join(report['passed']))


if __name__=='__main__':main()
