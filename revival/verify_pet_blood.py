"""Ordinary blood advancement at the public Inventory state/transaction seams."""
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from dataclasses import FrozenInstanceError,asdict
import json
import hashlib

from accounts import AccountStore
from inventory import Inventory,pet_record
from inventory_test_support import known_cash_context
from research_pet_blood import native_blood_record
from inspect_client import OUT,write_json


def refused(action):
    try:action()
    except ValueError:return
    raise AssertionError('Unknown or reset ordinary blood state accepted')


def main():
    with TemporaryDirectory() as directory:
        store=AccountStore(Path(directory)/'state.sqlite3')
        role=store.create_role(1111,'宠物血脉',12,1010101)
        config=Inventory.prepare(store)
        inv=Inventory(store,1111,role['id'],config,**known_cash_context(store,1111,role['id']))
        pet=inv.grant_pet(500001)
        def current(pid):return next(p for p in inv.snapshot()['pets'] if p['id']==pid)
        born=current(pet)['progress']
        assert born.blood is not None and born.blood.state.power==0,'New pet blood remains unknown'
        assert (born.blood.level,born.blood.maximum_level,born.blood.maximum_power)==(0,3,1139)
        observed=native_blood_record(pet_record(current(pet)))
        assert (observed['power'],observed['maximum_power'],observed['level'])==(0,1139,0)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            old=db.execute('INSERT INTO inventory_pets(role_id,template_id,name) VALUES(?,?,?)',
                (role['id'],500001,'已知历史血脉')).lastrowid
            inv.initialize_pet_care(db,old,1,100,6000)
            inv.initialize_pet_growth(db,old)
            original=inv.pet_progress(db,old)
            assert original.blood is None
            inv.initialize_pet_blood(db,old,200)
            refused(lambda:inv.initialize_pet_blood(db,old,0))
            refused(lambda:inv.initialize_pet_blood(db,old,True))
            refused(lambda:inv.initialize_pet_blood(db,old,1140))
        known=current(old)['progress']
        assert known.profile.aptitudes==(1130,1235,960,657,1122)
        assert known.effective_profile.aptitudes==(1132,1237,961,658,1124)
        assert known.blood.level==1 and known.attributes.potential==10
        assert known.state.hp==born.state.hp and known.state.mp==born.state.mp
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            allocated=inv.change_pet_growth(db,old,'blood:allocate',known.state.version,'allocate',(5,0,0,0,0))
            assert allocated.attributes.potential==5 and allocated.state.allocated==(5,0,0,0,0)
            assert allocated.blood.state.power==200
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            assert inv.change_pet_growth(db,old,'blood:allocate',known.state.version,'allocate',(5,0,0,0,0))==allocated
            advanced=inv.change_pet_growth(db,old,'blood:xp',allocated.state.version,'experience',200)
            assert advanced.state.level==1 and advanced.state.experience==150 and advanced.attributes.potential==10
            assert advanced.blood.state.power==200 and advanced.profile==known.profile
        try:known.blood.state.power=0
        except FrozenInstanceError:pass
        else:raise AssertionError('Mutable blood snapshot crossed the owner seam')
        before=inv.immutable_snapshot()
        # A captured pre-blood ordinary receipt remains historical; it cannot
        # retroactively claim blood bonuses or replace the current projected pet.
        with closing(store.connect()) as db,db:
            fingerprint=hashlib.sha256(json.dumps(['experience',0],separators=(',',':')).encode()).hexdigest()
            db.execute('INSERT INTO inventory_pet_growth_receipts VALUES(?,?,?,?,?)',
                (role['id'],old,'blood:old-receipt',fingerprint,json.dumps([asdict(original.profile),asdict(original.state)])))
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            historical=inv.change_pet_growth(db,old,'blood:old-receipt',0,'experience',0)
            assert historical.blood is None and historical.attributes.potential==0
        assert inv.immutable_snapshot()==before
        assert Inventory(AccountStore(store.path),1111,role['id'],config).immutable_snapshot()==inv.immutable_snapshot()
    report={'passed':['new explicit ordinary power0 and original blood power/cap/level consumers',
        'old unknown remains None; one-time known power200 base-profile import preserves current resources',
        'base/effective aptitude split and real10 potential; allocate5 then200XP to L1/150XP retains correct budget',
        'immutable blood state; reset/bool/colour overflow refuse; original two-part historical receipt stays historical',
        'reopen preserves the same effective snapshot without repeated multiplication'],
        'scope':'ordinary metadata/effective growth only; essence transaction pending','native_gui_tested':False,'live_server_changed':False}
    write_json(OUT/'evidence/pet-blood-baseline-verification.json',report)
    print('PASS',', '.join(report['passed']))


if __name__=='__main__':main()
