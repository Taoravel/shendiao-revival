"""Ordinary rebirth via the owned Inventory transaction and current native messages."""
from pathlib import Path
from tempfile import TemporaryDirectory
from contextlib import closing
from accounts import AccountStore
from inventory import Inventory,USE_ITEM,REFRESH_PET
import struct
from inventory_test_support import known_cash_context
from native_gameplay_probe import probe
from pet_skill_expiry import TimedSkillGrant
from inspect_client import OUT,write_json
from unittest.mock import patch
import sqlite3


def refused(action,errors=(ValueError,)):
    try:action()
    except errors:return
    raise AssertionError('Invalid or failing ordinary return accepted')


def main():
    with TemporaryDirectory() as tmp:
        store=AccountStore(Path(tmp)/'ordinary-return.sqlite3')
        role=store.create_role(1111,'普通还童',12,1010101)
        config=Inventory.prepare(store)
        inv=Inventory(store,1111,role['id'],config,**known_cash_context(store,1111,role['id']))
        pet=inv.grant_pet(500001);inv.grant_item(31002,3);inv.grant_item(36117)
        snapshot=inv.immutable_snapshot()
        key=next(i.id for i in snapshot.items if i.template_id==31002)
        essence=next(i.id for i in snapshot.items if i.template_id==36117)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            inv.use_pet_blood_essence(db,essence,pet,inv.epoch,'ordinary:blood',None)
            p=inv.read_pet_state(db,pet)
            inv.change_pet_growth(db,pet,'ordinary:XP',p.progress.state.version,'experience',1000)
            p=inv.read_pet_state(db,pet)
            inv.change_pet_growth(db,pet,'ordinary:allocate',p.progress.state.version,'allocate',(3,0,0,0,0))
        before=inv.immutable_snapshot().pets[0]
        def wash():
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                return inv.ordinary_return(db,pet,key,inv.epoch,'ordinary:A',(0,)*15)
        receipt=wash();snapshot=inv.immutable_snapshot();after=snapshot.pets[0]
        assert before.progress.state.level>0 and after.progress.state.level==0
        assert after.progress.state.experience==0 and after.progress.state.allocated==(0,)*5
        assert after.progress.profile.aptitudes==(1040,1130,840,585,1025) and after.progress.profile.growth_raw==986
        assert after.progress.blood==before.progress.blood and after.care.grade==before.care.grade
        assert after.progress.attributes.potential==10 and after.traits.origin==2
        assert (after.progress.state.hp,after.progress.state.mp)==(after.progress.attributes.max_hp,after.progress.attributes.max_mp)
        assert after.skills.learned==() and after.care.loyalty==100 and after.care.lifetime==6000
        assert next(i.quantity for i in snapshot.items if i.id==key)==2
        assert wash().replayed and inv.immutable_snapshot()==snapshot
        replies=inv.receive_ordinary_return(struct.pack('>iiQ',key,1,pet),inv.epoch,'ordinary:native',(9999,)*15)
        assert any(t==REFRESH_PET for t,b in replies)
        assert inv.immutable_snapshot().pets[0].skills.learned==(200061,200091)
        # Template threshold is independent of CURRENT pet and character levels.
        inv.grant_item(31002,100);inv.grant_item(31087,3);inv.grant_item(31576,4)
        with closing(store.connect()) as db,db:db.execute('UPDATE roles SET level=150 WHERE id=?',(role['id'],))
        def state(target):return next(p for p in inv.immutable_snapshot().pets if p.id==target)
        def item(template):return next(i.id for i in inv.immutable_snapshot().items if i.template_id==template)
        def wash_pet(target,request,draws=(0,)*15,pill=None,expected=None):
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                return inv.ordinary_return(db,target,key if pill is None else pill,inv.epoch,request,draws,expected)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');p=inv.read_pet_state(db,pet)
            inv.change_pet_growth(db,pet,'ordinary:level100',p.progress.state.version,'experience',
                sum(inv.growth_rules.thresholds[i] for i in range(100)))
        assert state(pet).progress.state.level==100
        before=inv.immutable_snapshot()
        refused(lambda:wash_pet(pet,'wrong-high-pill',pill=item(31087)))
        assert inv.immutable_snapshot()==before
        wash_pet(pet,'low-template-high-current')
        high=inv.grant_pet(500043)
        assert state(high).progress.state.level==0
        before=inv.immutable_snapshot();refused(lambda:wash_pet(high,'wrong-low-pill'))
        assert inv.immutable_snapshot()==before
        wash_pet(high,'high-template-current-zero',pill=item(31087))
        # Current native Pet and original raw scalar/skill/expiry decode are valid.
        high_body=struct.pack('>iiQ',item(31087),1,high)
        high_replies=inv.receive_ordinary_return(high_body,inv.epoch,'native:high',(9999,)*15)
        _,raw=probe(0xf9d7b0,0xf9d840,0xf9d880,payload=next(b for t,b in high_replies if t==REFRESH_PET))
        assert struct.unpack_from('<i',raw,8+0x28)[0]==0
        # Trusted fixtures model an old wild pet with all explicit subrecords.
        wild=inv.grant_pet(500001)
        pill=item(31576)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            inv.super_return(db,wild,inv.epoch,'super:wild-before','preview',item_key=pill,draws=(0,)*7)
            inv.super_return(db,pet,inv.epoch,'super:other-pet','preview',item_key=pill,draws=(0,)*7)
        def known_wild(target):
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                # Explicit legacy fixture: remove known baseline before complete import,
                # never a production mutation shortcut or automatic migration.
                for table in ('inventory_pet_traits','inventory_pet_care','inventory_pet_blood','inventory_pet_cakes',
                              'inventory_pet_flags','inventory_pet_skill_progress','inventory_pet_battle_care'):
                    db.execute(f'DELETE FROM {table} WHERE pet_id=?',(target,))
                inv.initialize_pet_traits(db,target,1,73)
                inv.initialize_pet_care(db,target,3,50,100)
                inv.initialize_pet_blood(db,target,2000)
                inv.initialize_pet_cakes(db,target,20,(5,2,1,0,0))
                inv.initialize_pet_flags(db,target,0x82)
                inv.initialize_pet_skill_progress(db,target,100)
                inv.initialize_pet_battle_care_counter(db,target,2)
                p=inv.read_pet_state(db,target)
                inv.grant_pet_timed_skill(db,TimedSkillGrant('ordinary:timed:'+str(target),target,200011,9999,
                    'known-rebirth-fixture',p.skills.version),inv.epoch,1000)
                db.execute('DELETE FROM inventory_pet_skill_expiry WHERE pet_id=?',(target,))
                inv.initialize_pet_skill_expiry(db,target,((200011,9999),(200091,9999)))
        known_wild(wild)
        old=state(wild)
        assert old.progress.blood.bonus_potential==40 and old.skill_expiry.entries==((200011,9999),(200091,9999))
        body=struct.pack('>iiQ',key,1,wild)
        replies=inv.receive_ordinary_return(body,inv.epoch,'ordinary:wild',(9999,)*15)
        reborn=state(wild)
        assert reborn.id==old.id and reborn.name==old.name and reborn.flags==old.flags and reborn.flags.bound
        assert reborn.traits.origin==2 and reborn.traits.insight==100
        assert reborn.care.grade==6 and reborn.care.loyalty==400 and reborn.care.lifetime==6000
        assert reborn.progress.blood.state.power==0 and reborn.progress.attributes.potential==0
        assert reborn.skill_expiry.entries==() and reborn.skill_progress.points==0 and reborn.cake.count==0
        assert 200011 not in reborn.skills.learned
        assert (reborn.progress.state.level,reborn.progress.state.experience)==(0,0)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN')
            assert inv.pet_battle_care_counter(db,wild).mod3==0
            assert inv.super_return_candidate(db,wild,inv.epoch) is None
            assert inv.super_return_candidate(db,pet,inv.epoch).candidate_id=='super:other-pet'
        # Original timed metadata is really cleared on the wire, not merely hidden.
        _,raw=probe(0xf9d7b0,0xf9d840,0xf9d880,payload=next(b for t,b in replies if t==REFRESH_PET))
        assert raw[8+0x111]==0 and struct.unpack_from('<i',raw,8+0xb4)[0]==2
        from research_pet_skill_expiry import native_timed_record
        learned,icons,clock=native_timed_record(next(b for t,b in replies if t==REFRESH_PET),10000)
        assert learned==reborn.skills.learned and 200011 not in learned
        assert tuple(args[1] for args in icons)==reborn.skills.learned and 200091 in learned
        assert next(b for t,b in replies if t==0xc0801)==b'\x01'+struct.pack('>ih',wild,0)
        # Baby colour retention must ignore a later wild-colour draw.
        wash_pet(wild,'ordinary:gold-baby')
        assert state(wild).care.grade==6
        # The thirteen source-proven fairy species retain required abilities even at count draw0.
        expected={500090:200472,500050:200542,500097:200552,500112:200582,500118:200612,
            500130:200642,500131:200652,500114:200662,500154:200692,500156:200702,
            500157:200712,500155:200722,500158:200732}
        for template,skill in expected.items():
            fairy=inv.grant_pet(template)
            wash_pet(fairy,'fairy:'+str(template))
            assert state(fairy).skills.learned==(skill,)
            inv.free_pet(fairy)
        # Kind2 ordinary eligibility is an explicit restoration design, not a super-only ban.
        god=inv.grant_pet(500069);wash_pet(god,'ordinary:known-kind2')
        assert state(god).progress.profile.growth_raw==1300
        inv.free_pet(god)
        # Late paid replay never resets later growth/wounds/progress or reintroduces a deleted skill.
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');p=inv.read_pet_state(db,pet)
            inv.change_pet_growth(db,pet,'ordinary:later-xp',p.progress.state.version,'experience',1000)
            p=inv.read_pet_state(db,pet)
            inv.change_pet_growth(db,pet,'ordinary:later-wound',p.progress.state.version,'resources',(0,3))
        before=inv.immutable_snapshot()
        assert wash().replayed and inv.immutable_snapshot()==before
        assert state(pet).progress.state.hp==0
        wash_pet(pet,'ordinary:revive-designed')
        assert state(pet).progress.state.hp==state(pet).progress.attributes.max_hp
        # The original nonfighting gate is real; a new valid command cannot wash selected pets.
        from inventory import FIGHT_PET,REST_PET
        inv.receive(FIGHT_PET,struct.pack('>i',pet))
        baseline=inv.immutable_snapshot();refused(lambda:wash_pet(pet,'ordinary:fighting'))
        assert inv.immutable_snapshot()==baseline
        inv.receive(REST_PET,b'')
        # A historical reset cannot erase a later timed skill or invent a clock.
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');p=inv.read_pet_state(db,pet)
            inv.grant_pet_timed_skill(db,TimedSkillGrant('ordinary:later-timed',pet,200011,19999,
                'known-later-fixture',p.skills.version),inv.epoch,1000)
        baseline=inv.immutable_snapshot();low_body=struct.pack('>iiQ',key,1,pet)
        refused(lambda:inv.receive_ordinary_return(low_body,inv.epoch,'ordinary:A'))
        inv.receive_ordinary_return(low_body,inv.epoch,'ordinary:A',now_ms=10000)
        assert inv.immutable_snapshot()==baseline and state(pet).skill_expiry.entries==((200011,19999),)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN')
            db.set_authorizer(lambda a,*args:sqlite3.SQLITE_DENY if a in
                (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE) else sqlite3.SQLITE_OK)
            with patch.object(Path,'read_text',side_effect=AssertionError('hot file read')),patch.object(store,'connect',side_effect=AssertionError('nested connection')):
                assert inv.ordinary_return(db,pet,key,inv.epoch,'ordinary:A').replayed
        # Real faults in every reset stage preserve the COMPLETE pet, pill, meter and pending candidate.
        target=inv.grant_pet(500001)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            inv.super_return(db,target,inv.epoch,'super:fault-pending','preview',item_key=pill,draws=(0,)*7)
        known_wild(target)
        def aux():
            with closing(store.connect()) as db,db:
                db.execute('BEGIN')
                return inv.pet_battle_care_counter(db,target),inv.super_return_candidate(db,target,inv.epoch)
        stages=[(table,'UPDATE') for table in ('inventory_pet_growth','inventory_pet_care','inventory_pet_traits',
            'inventory_pet_skills','inventory_pet_skill_expiry','inventory_pet_skill_progress','inventory_pet_cakes',
            'inventory_pet_blood','inventory_pet_battle_care','inventory_items')]
        stages += [('inventory_pet_return_candidates','DELETE'),('inventory_pet_ordinary_return_receipts','INSERT')]
        for table,operation in stages:
            with closing(store.connect()) as db,db:
                db.execute(f"CREATE TRIGGER ordinary_fail BEFORE {operation} ON {table} BEGIN SELECT RAISE(ABORT,'ordinary fault'); END")
            baseline=inv.immutable_snapshot();extra=aux()
            refused(lambda:wash_pet(target,'ordinary:fault'),(sqlite3.IntegrityError,))
            assert inv.immutable_snapshot()==baseline and aux()==extra
            with closing(store.connect()) as db,db:db.execute('DROP TRIGGER ordinary_fail')
        wash_pet(target,'ordinary:fault')
        assert state(target).traits.origin==2 and aux()[1] is None
        # A late encoder or caller failure rolls back the reset and payment.
        before=inv.immutable_snapshot()
        def late(*args,**kwargs):raise RuntimeError('late caller source failure')
        refused(lambda:inv.receive_ordinary_return(body,inv.epoch,'ordinary:late',(0,)*15,precommit=late),(RuntimeError,))
        with patch('inventory.pet_record',side_effect=RuntimeError('late wire failure')):
            refused(lambda:inv.receive_ordinary_return(body,inv.epoch,'ordinary:late',(0,)*15),(RuntimeError,))
        assert inv.immutable_snapshot()==before
        inv.receive_ordinary_return(body,inv.epoch,'ordinary:late',(0,)*15)
        # All original templates draw only known distinct candidates and respect current colour caps.
        for template,values in inv.ordinary_return_rules.templates.items():
            for grade in range(1,7):
                for draws in ((0,)*15,(5000,)*15,(9999,)*15):
                    result=inv.ordinary_return_rules.skills(template,grade,draws,inv.skill_rules)
                    assert len(set(result))==len(result)<=inv.skill_rules.caps[grade]
                    assert set(result)<=set(values[3])
                    if template in expected:assert expected[template] in result
        # Unknown legacy subrecords/foreign identity/invalid draw/version cannot spend.
        with closing(store.connect()) as db,db:db.execute('DELETE FROM inventory_pet_cakes WHERE pet_id=?',(target,))
        before=inv.immutable_snapshot();refused(lambda:wash_pet(target,'ordinary:unknown'))
        assert inv.immutable_snapshot()==before
        for draws in ([],(0,)*14,(True,)*15,(-1,)*15,(10000,)*15):
            refused(lambda:wash_pet(pet,'ordinary:invalid',draws))
        refused(lambda:wash_pet(pet,'ordinary:wrong-version',expected=999999))
        refused(lambda:wash_pet(pet,'ordinary:A',(1,)*15))
        refused(lambda:inv.receive(USE_ITEM,struct.pack('>iiQ',key,1,pet)))
        other_role=store.create_role(1111,'外部还童',12,1010101)
        other_inv=Inventory(store,1111,other_role['id'],config)
        foreign=other_inv.grant_pet(500001);other_inv.grant_item(31002)
        foreign_key=next(i.id for i in other_inv.immutable_snapshot().items if i.template_id==31002)
        refused(lambda:wash_pet(foreign,'ordinary:foreign'))
        refused(lambda:wash_pet(wild,'ordinary:foreign-item',pill=foreign_key))
        for invalid_body in (b'',b'\x00'*16,struct.pack('>iiQ',key,0,pet),struct.pack('>iiQ',key,1,2**32)):
            refused(lambda:inv.receive_ordinary_return(invalid_body,inv.epoch,'ordinary:bad-body',(0,)*15))
        # Opaque replacement owner and reopen retain the complete current state.
        old_epoch=inv.epoch;token='普通还童:00031'
        with closing(store.connect()) as db,db:db.execute('UPDATE role_leases SET epoch=? WHERE role_id=?',(token,role['id']))
        active=Inventory(store,1111,role['id'],config,epoch=token,currency_rules=inv.currency_rules)
        active.receive_ordinary_return(body,token,'ordinary:opaque',(0,)*15)
        before=active.immutable_snapshot()
        active.receive_ordinary_return(body,token,'ordinary:opaque')
        assert active.immutable_snapshot()==before
        refused(lambda:inv.receive_ordinary_return(body,old_epoch,'ordinary:late'))
        assert Inventory(AccountStore(store.path),1111,role['id'],config).immutable_snapshot()==before
        # Released-instance history is still audit; a fresh reset cannot recreate it.
        active.free_pet(high)
        gone=active.immutable_snapshot()
        removed=active.receive_ordinary_return(high_body,token,'native:high')
        from inventory import REMOVE_PET
        assert (REMOVE_PET,struct.pack('>ii',1,high)) in removed and active.immutable_snapshot()==gone
        probe(0xdc0f10,0xe540d0,0xdc0f40,payload=next(b for t,b in removed if t==REMOVE_PET),factory=True)
        refused(lambda:active.receive_ordinary_return(high_body,token,'native:released-new',(0,)*15))
    report={'passed':['baby level/XP/allocated/skills/care reset, blood retained once and10 potential returned unallocated',
        'original uselevel95 boundary ignores current level100/character150 and newborn95-template level0',
        'wild becomes baby, weighted grade6, blood/potential/expiry/expansion/cakes/mod3 reset; exact flags/binding/name/key retained',
        'only own super candidate invalidated; other pet pending survives; later gold baby retains colour',
        '13 source-proven fairy required skills survive lowest draw; original fixed-range kind2 restoration design supported',
        '158templates*6grades*3draw cases obey source candidates/caps/uniqueness and guaranteed skills',
        'paid history SQL-readonly/no hot IO preserves later XP/death/wounds/timed skill; explicit ordinary rebirth full resource policy and nonfighting gate',
        '12 real write-stage faults and late source/encoding failure roll whole reset/pill/receipt/pending/meter back',
        'unknown legacy/foreign/malformed/draw/intent/version/legacy route refuse; current opaque owner/retry/reopen and stale owner guards'],
        'shared_route_integrated':False,'live_server_changed':False,'native_gui_verified':False}
    write_json(OUT/'evidence/pet-ordinary-return-verification.json',report)
    print('PASS',', '.join(report['passed']))


if __name__=='__main__':main()
