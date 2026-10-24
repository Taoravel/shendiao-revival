"""Public pet skill state, original learned-icon consumer and atomic books."""
from contextlib import closing
from dataclasses import FrozenInstanceError
from pathlib import Path
from tempfile import TemporaryDirectory
import sqlite3
import struct

from accounts import AccountStore
from inventory import Inventory, pet_record, REFRESH_PET, USE_ITEM
from inventory_test_support import known_cash_context
from inspect_client import OUT, write_json
from research_pet_skills import native_record_skills
from pet_skills import PetSkills


def refused(action):
    try:action()
    except ValueError:return
    raise AssertionError('Invalid or unknown pet skill action accepted')


def main():
    with TemporaryDirectory() as tmp:
        store=AccountStore(Path(tmp)/'state.sqlite3')
        role=store.create_role(1111,'宠物学技能',12,1010101)
        config=Inventory.prepare(store)
        inv=Inventory(store,1111,role['id'],config,
            **known_cash_context(store,1111,role['id'],balances=(77,0,0,0)))
        pet=inv.grant_pet(500001)
        def current():return next(p for p in inv.snapshot()['pets'] if p['id']==pet)
        assert current().get('skills')==PetSkills(0,(200091,200061)), 'Known new pet still has no authoritative learned skills'
        assert inv.skill_rules.learn(current()['skills'],1,200011,(999,0))[0].learned==(200091,200061,200011)
        assert inv.skill_rules.learn(current()['skills'],1,200011,(1000,0))[0].learned==(200011,200061)
        assert native_record_skills(pet_record(current()))[0]==(200091,200061)
        try:inv.immutable_snapshot().pets[0].skills.learned=()
        except FrozenInstanceError:pass
        else:raise AssertionError('Mutable pet skills in cross-owner snapshot')
        inv.grant_item(31003,3)
        basic=next(i['id'] for i in inv.snapshot()['items'] if i['template_id']==31003)
        def learn(item,key,version,draws=(0,0),owner_epoch=None):
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                return inv.learn_pet_skill(db,item,pet,inv.epoch if owner_epoch is None else owner_epoch,key,version,draws)
        first=learn(basic,'skill:first',0)
        assert first.after==PetSkills(1,(200091,200061,200011)) and first.replaced_skill_id is None
        assert learn(basic,'skill:first',0)==first
        before=inv.immutable_snapshot()
        refused(lambda:learn(basic,'skill:first',0,(1,0)))
        refused(lambda:learn(basic,'skill:stale',0))
        refused(lambda:learn(basic,'skill:duplicate',1))
        refused(lambda:learn(basic,'skill:old-lease',1,owner_epoch=inv.epoch+1))
        assert inv.immutable_snapshot()==before
        inv.grant_item(31004)
        advanced=next(i['id'] for i in inv.snapshot()['items'] if i['template_id']==31004)
        upgraded=learn(advanced,'skill:upgrade',1,(999,999))
        assert upgraded.replaced_skill_id==200011 and upgraded.after.learned==(200091,200061,200012)
        before=inv.immutable_snapshot()
        refused(lambda:learn(basic,'skill:downgrade',2))
        assert inv.immutable_snapshot()==before
        inv.grant_item(31005,2)
        other=next(i['id'] for i in inv.snapshot()['items'] if i['template_id']==31005)
        body=struct.pack('>6i',pet,other,-1,-1,-1,-1)
        replies=inv.receive_pet_skill_book(body,inv.epoch,'skill:adapter',(0,0))
        decoded=native_record_skills(next(b for k,b in replies if k==REFRESH_PET))[0]
        assert decoded==(200091,200061,200012,200021)
        inv.grant_item(31007)
        third=next(i['id'] for i in inv.snapshot()['items'] if i['template_id']==31007)
        replaced=learn(third,'skill:full',3,(999,1))
        assert replaced.replaced_skill_id==200061 and replaced.after.learned==(200091,200031,200012,200021)
        replay=inv.receive_pet_skill_book(body,inv.epoch,'skill:adapter',(0,0))
        assert native_record_skills(next(b for k,b in replay if k==REFRESH_PET))[0]==replaced.after.learned
        # The second31005 is still owned; duplicate learning remains a no-op.
        before=inv.immutable_snapshot()
        refused(lambda:inv.receive_pet_skill_book(body,inv.epoch,'skill:duplicate2',(0,0)))
        refused(lambda:inv.receive_pet_skill_book(body[:-1],inv.epoch,'skill:short',(0,0)))
        refused(lambda:inv.receive_pet_skill_book(struct.pack('>6i',pet,other,0,-1,-1,-1),inv.epoch,'skill:protected',(0,0)))
        assert inv.immutable_snapshot()==before
        inv.grant_item(31956)
        bound=next(i['id'] for i in inv.snapshot()['items'] if i['template_id']==31956)
        before=inv.immutable_snapshot()
        # This bound book teaches lower-rank200011 while pet knows200012;
        # reject the weaker learning intent, not all binding books.
        refused(lambda:learn(bound,'skill:binding',4))
        assert inv.immutable_snapshot()==before
        inv.grant_item(31009,2)
        failure=next(i['id'] for i in inv.snapshot()['items'] if i['template_id']==31009)
        before=inv.immutable_snapshot()
        with closing(store.connect()) as db:
            db.execute("CREATE TRIGGER fail_pet_skills BEFORE UPDATE ON inventory_pet_skills BEGIN SELECT RAISE(ABORT,'skill failure'); END")
        try:learn(failure,'skill:db-abort',4)
        except sqlite3.IntegrityError:pass
        else:raise AssertionError('Actual skill-state failure did not execute')
        assert inv.immutable_snapshot()==before
        with closing(store.connect()) as db:db.execute('DROP TRIGGER fail_pet_skills')
        try:
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                inv.learn_pet_skill(db,failure,pet,inv.epoch,'skill:outer',4,(0,0))
                raise RuntimeError('common receipt failed')
        except RuntimeError:pass
        assert inv.immutable_snapshot()==before
        # Unknown wallet prevents a native success reply and rolls learning back.
        unknown=Inventory(store,1111,role['id'],config,epoch=inv.epoch)
        refused(lambda:unknown.receive_pet_skill_book(struct.pack('>6i',pet,failure,-1,-1,-1,-1),inv.epoch,'skill:no-cash',(0,0)))
        assert inv.immutable_snapshot()==before
        # All complete refreshes preserve the learned list after care changes.
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            inv.change_pet_care(db,pet,'skill:care',0,'defeat',1)
        inv.grant_item(31000)
        food=next(i['id'] for i in inv.snapshot()['items'] if i['template_id']==31000)
        feed=inv.receive(USE_ITEM,struct.pack('>iiQ',food,1,pet))
        assert native_record_skills(next(b for k,b in feed if k==REFRESH_PET))[0]==replaced.after.learned
        assert Inventory(AccountStore(store.path),1111,role['id'],config).snapshot()==inv.snapshot()
        # No implicit legacy template skills; explicitly known complete list only.
        with closing(store.connect()) as db,db:
            legacy=db.execute('INSERT INTO inventory_pets(role_id,template_id,name) VALUES(?,?,?)',
                              (role['id'],500001,'既有技能')).lastrowid
            db.execute('BEGIN IMMEDIATE') if not db.in_transaction else None
            inv.initialize_pet_care(db,legacy,1,100,6000)
            inv.initialize_pet_growth(db,legacy)
        old=next(p for p in inv.snapshot()['pets'] if p['id']==legacy)
        assert old.get('skills') is None
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            inv.initialize_pet_skills(db,legacy,(200021,))
            refused(lambda:inv.initialize_pet_skills(db,legacy,(200011,)))
        assert next(p for p in inv.snapshot()['pets'] if p['id']==legacy)['skills']==PetSkills(0,(200021,))
        inv.free_pet(legacy)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            refused(lambda:inv.initialize_pet_skills(db,legacy,()))
            refused(lambda:inv.learn_pet_skill(db,failure,legacy,inv.epoch,'skill:released',0,(0,0)))
        foreign_role=store.create_role(1111,'别人宠技能',12,1010101)
        foreign_inv=Inventory(store,1111,foreign_role['id'],config)
        foreign_pet=foreign_inv.grant_pet(500001)
        before=inv.immutable_snapshot()
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            refused(lambda:inv.learn_pet_skill(db,failure,foreign_pet,inv.epoch,'skill:foreign',0,(0,0)))
        assert inv.immutable_snapshot()==before
    report={'passed':['new explicit deterministic skills persist and reach original native learned-icon consumer',
        'frozen learned IDs survive feeding, refresh and reopen',
        'book append, same-family upgrade, full-grid replacement and no-op duplicate/weaker rejection',
        'expected version/current lease/intent fingerprint protect state and one-book debit',
        'historical receipt never overwrites later skill state; native retry sends current IDs',
        'actual DB abort, outer failure and missing wallet roll learning and debit back',
        'protected options, weaker bound book and truncated requests refuse before spending',
        'old unknown skills stay unknown; explicit known import cannot reroll; released pet refuses'],
        'native_ui_tested':False,'runtime_route_connected':False,'battle_effects_implemented':False}
    write_json(OUT/'evidence/pet-skills-verification.json',report)
    print('PASS:',', '.join(report['passed']))


if __name__=='__main__':main()
