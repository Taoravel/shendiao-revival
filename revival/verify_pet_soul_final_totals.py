"""Actual shared growth read/native/battle sees settled soul totals, one HPMP."""
from pathlib import Path
from tempfile import TemporaryDirectory
from contextlib import closing
from dataclasses import replace
import struct
from accounts import AccountStore
from inventory import Inventory,pet_record
from pet_souls import SoulProfile,SoulBean,SoulRules
from pet_soul_actions import SoulActionRules
import pet_soul_action_storage as actions
import pet_soul_storage as souls
import role_mingwen as mingwen
import pet_soul_totals_storage as totals
import pet_soul_totals_protocol as protocol
from pet_soul_totals import PetSoulTotalsRules,PetSoulExtraBasis
from native_gameplay_probe import probe
from battle_loadout import selected_pet,PetTemplate
import runtime_storage


def main():
    with TemporaryDirectory(prefix='actual-pet-soul-totals-') as tmp:
        store=AccountStore(Path(tmp)/'state.sqlite3');runtime_storage.prepare(store)
        role=store.create_role(1111,'宠物元魂真属性',12,1010101);rid=role['id'];epoch=store.acquire_lease(1111,rid)
        inv=Inventory(store.leased(1111,rid,epoch),1111,rid);pet=inv.grant_pet(500001);inv.fight_pet(pet)
        rules=PetSoulTotalsRules.load();sr=rules.souls;mr=rules.mingwen
        action_rules=SoulActionRules.load()
        with closing(store.connect()) as db:
            souls.prepare(db);mingwen.prepare(db);totals.prepare(db)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            inv.change_pet_growth(db,pet,'known-pet-level1',0,'experience',50)
            inv.change_pet_growth(db,pet,'known-hurt-pet',1,'resources',(80,30))
            db.execute('UPDATE roles SET level=5 WHERE id=?',(rid,))
            souls.initialize(db,inv,sr,SoulProfile(rid,pet,0,sr.revision,'known-empty-totals-souls',()),'explicit_known_pet_souls')
            mingwen.initialize(db,inv,mr,mingwen.MingwenState(rid,0,mr.revision,'known-totals-mingwen',
                tuple(mingwen.MingwenEntry(i,0,0,0) for i in range(1,23))),'explicit_known_mingwen_ledger')
            extra=PetSoulExtraBasis(rid,pet,rules.revision,'known-seven-pet-extras',
                ((110,100,1),(120,80,1),(740,-1,10),(1550,1,100),(1560,0,1),(1580,0,1),(1590,0,1)))
            totals.initialize(db,inv,rules,extra,'explicit_known_pet_soul_extras')
        selected=replace(store.inventory_config,growth_rules=replace(store.inventory_config.growth_rules,totals_rules=rules))
        current_inv=Inventory(store.leased(1111,rid,epoch),1111,rid,selected)
        with closing(store.connect()) as db:
            db.execute('BEGIN');before=totals.read_profile(db,current_inv,rules,pet)
            assert (before.progress.state.hp,before.progress.state.mp,before.progress.attributes.max_hp)==(80,30,157)
            try:current_inv.change_pet_growth(db,pet,'known-pet-level1',0,'experience',50)
            except ValueError:pass
            else:raise AssertionError('Legacy paid growth result bypassed selected final policy')
        try:inv.immutable_snapshot()
        except ValueError:pass
        else:raise AssertionError('Old bare growth reader silently ignored adopted soul policy')
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');basis=souls.read(db,current_inv,sr,pet)
            souls.replace_profile(db,current_inv,sr,basis,replace(basis.profile,version=1,
                entries=((1,SoulBean(31286,0,0,0,0,0)),)))
            pending=current_inv.immutable_snapshot_transaction(db)
            def forbidden_authority(*args):raise AssertionError('Pending pet reached operation permission lookup')
            try:actions.admit(db,current_inv,action_rules,'pending-native-remove',0xc0805,struct.pack('>ii',pet,1),
                deadline_ms=1000,clock_ms=lambda:100,authority_reader=forbidden_authority)
            except ValueError as error:assert 'settled' in str(error)
            else:raise AssertionError('Soul admission froze pending pet resources')
            try:totals.change_resources(db,current_inv,rules,before,'forbidden-pending-heal',(81,30),cause='medicine')
            except ValueError:pass
            else:raise AssertionError('Medicine silently repaired a pending source')
            try:pet_record(vars(pending.pets[0]))
            except ValueError:pass
            else:raise AssertionError('Native consumer emitted unsettled pet caps')
            changed=totals.settle_source(db,current_inv,rules,before,'known-solar-source')
            assert (changed.progress.state.hp,changed.progress.state.mp,changed.progress.attributes.max_hp)==(80,30,202)
            snapshot=current_inv.immutable_snapshot_transaction(db)
            record=pet_record(vars(snapshot.pets[0]));probe(0xf89ba0,0xf5df70,0xf5f1f0,payload=record)
            native=protocol.current_messages(db,current_inv,rules,pet)
            assert native.ratio_display_pending==(740,1550,1560,1580,1590)
            assert tuple(kind for kind,_ in native.messages)==(0xc07d5,0xc32c9)
            assert native.messages[1][1]==struct.pack('>iiBifif',1,pet,2,110,100.0,120,80.0)
            probe(0xf9d7b0,0xf9d840,0xf9d880,payload=native.messages[0][1])
            probe(0xec30c0,0xec3250,0xec32f0,payload=native.messages[1][1])
            battle=selected_pet(snapshot,role_id=rid,role_level=5,templates=(PetTemplate(500001,16013,0,5),),
                growth_revision=current_inv.growth_rules.revision)
            assert (battle.stats.hp,battle.stats.max_hp)==(80,202)
        second=current_inv.grant_pet(500001)
        before_large=current_inv.immutable_snapshot()
        try:
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                souls.initialize(db,current_inv,sr,SoulProfile(rid,second,0,sr.revision,'known-second-empty',()),'explicit_known_pet_souls')
                large=PetSoulExtraBasis(rid,second,rules.revision,'known-nonfloat32-hit',
                    ((110,16777217,1),(120,80,1),(740,0,1),(1550,0,1),(1560,0,1),(1580,0,1),(1590,0,1)))
                totals.initialize(db,current_inv,rules,large,'explicit_known_pet_soul_extras')
                protocol.current_messages(db,current_inv,rules,second)
        except ValueError as error:assert 'exactly representable' in str(error)
        else:raise AssertionError('Native float32 silently changed the final integer hit value')
        assert current_inv.immutable_snapshot()==before_large
        print('PASS actual selected growth reader/soul source settle→202 cap with80HP30MP; old reader/pending native rejected; '
            'original Pet+integer-map codecs and actual battle core snapshot use totals; unrepresentable hit adoption rolls back; sole original HPMP state')


if __name__=='__main__':main()
