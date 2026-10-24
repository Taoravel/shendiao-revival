"""Real adopted XP above naked caps, same original pet/root resource stores."""
from pathlib import Path
from tempfile import TemporaryDirectory
from contextlib import closing
from dataclasses import replace
from accounts import AccountStore
from inventory import Inventory
from currency import initialize_wallet
from item_effects import VitalState
from role_attributes import AttributeBaseline
from role_attribute_storage import initialize_attribute_baseline
from role_growth import initialize_growth
from role_equipment import EquipmentAttributeBasis,load_ordinary_equipment_attribute_rules,resource_caps_from_projection
from role_equipment_storage import initialize_equipment_attribute_basis,current_equipment_totals,synchronize_inventory_resource_source
from role_resource_storage import migrate_role_resources
from pet_souls import SoulProfile,SoulBean
from pet_soul_totals import PetSoulTotalsRules,PetSoulExtraBasis
from pet_soul_action_storage import SoulResourceRules
import pet_soul_storage as souls
import role_mingwen as mingwen
import pet_soul_totals_storage as totals
import pet_soul_growth as growth_actions
import runtime_storage


def main():
    with TemporaryDirectory(prefix='actual-adopted-growth-') as tmp:
        store=AccountStore(Path(tmp)/'state.sqlite3');runtime_storage.prepare(store)
        trules=PetSoulTotalsRules.load();arules=growth_actions.PetSoulGrowthRules.load();gear=load_ordinary_equipment_attribute_rules()
        role=store.create_role(1111,'最终属性真实成长',12,1010101);rid=role['id'];epoch=store.acquire_lease(1111,rid)
        inv=Inventory(store.leased(1111,rid,epoch),1111,rid);context=SoulResourceRules(store.resource_rules,gear)
        with closing(store.connect()) as db:souls.prepare(db);mingwen.prepare(db)
        def sync(db,inventory,snapshot,*,replayed,request_id):
            return synchronize_inventory_resource_source(db,1111,rid,inventory.epoch,snapshot,request_id,
                equipment_rules=gear,resource_rules=store.resource_rules,replayed=replayed)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');db.execute('UPDATE roles SET level=5 WHERE id=?',(rid,))
            db.execute('INSERT INTO role_progress VALUES(?,0)',(rid,))
            rg=initialize_growth(db,1111,rid,epoch,store.growth_rules,expected_level=5,free_points=0)
            old=initialize_attribute_baseline(db,1111,rid,epoch,AttributeBaseline(rid,5,0,(10,)*5,
                (100,100,20,10,50,10,10,20,10)),rg,store.attribute_rules,VitalState(rid,0,70,100,40,100)).vitals
            initialize_equipment_attribute_basis(db,1111,rid,epoch,EquipmentAttributeBasis(rid,1,0,gear.revision,0,
                'known-adopted-growth-role',seal_resistance=0),gear)
            rt=current_equipment_totals(db,1111,rid,epoch,inv.immutable_snapshot_transaction(db),gear)
            migrate_role_resources(db,1111,rid,epoch,old,resource_caps_from_projection(rt),origin='explicit_migration',
                migration_id='known-adopted-growth-role',rules=store.resource_rules,equipment_rules=gear)
            initialize_wallet(db,1111,rid,epoch,(1000,0,0,0),'explicit_migration',store.currency_rules)
        pet=inv.grant_pet(500001);inv.fight_pet(pet)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');inv.change_pet_growth(db,pet,'before-adoption-L1',0,'experience',50)
            inv.change_pet_growth(db,pet,'before-adoption-hurt',1,'resources',(80,30))
            souls.initialize(db,inv,trules.souls,SoulProfile(rid,pet,0,trules.souls.revision,'known-growth-solar',
                ((1,SoulBean(31286,0,0,0,0,0)),)),'explicit_known_pet_souls')
            mingwen.initialize(db,inv,trules.mingwen,mingwen.MingwenState(rid,0,trules.mingwen.revision,
                'known-growth-inscriptions',tuple(mingwen.MingwenEntry(i,0,0,0) for i in range(1,23))),'explicit_known_mingwen_ledger')
            extra=PetSoulExtraBasis(rid,pet,trules.revision,'known-growth-seven-extras',
                ((110,100,1),(120,80,1),(740,-1,10),(1550,1,100),(1560,0,1),(1580,0,1),(1590,0,1)))
            totals.initialize(db,inv,trules,extra,'explicit_known_pet_soul_extras')
        config=replace(store.inventory_config,growth_rules=replace(store.inventory_config.growth_rules,totals_rules=trules))
        inv=Inventory(store.leased(1111,rid,epoch),1111,rid,config)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');before=totals.read_profile(db,inv,trules,pet)
            before=totals.change_resources(db,inv,trules,before,'known-growth-medicine',(195,30),cause='medicine')
            sync(db,inv,inv.immutable_snapshot_transaction(db),replayed=False,request_id='known-growth-fixture')
            command=growth_actions.PetGrowthCommand('adopted-growth-200',arules.revision,before,'experience',200,1000)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            result=growth_actions.apply(db,inv,trules,arules,command,resource_context=context,clock_ms=lambda:100,precommit=sync)
            state=result.profile.progress.state;attrs=result.profile.progress.attributes
            assert (state.level,state.experience,state.hp,state.mp,attrs.max_hp,attrs.max_mp)==(2,0,207,34,214,71)
            assert not result.replayed and (result.resources.hp,result.resources.mp,result.resources.caps.hp_max)==(70,40,100)
            assert tuple(kind for kind,_ in result.messages)==(0xc07d5,0xc32c9)
        print('PASS actual adopted pet L1/cap202/195HP→original200XP L2/cap214/207HP/34MP; '
            'same original carrier, root70/40/100 and current native messages; no synthetic HP')


if __name__=='__main__':main()
