"""Explicit baselines and growth/attribute/vital rollback, temporary accounts."""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
import json
import tempfile
from accounts import AccountStore
from inspect_client import OUT
from item_effects import VitalState
from progression import credit_experience
from role_growth import (load_growth_rules,prepare_growth_storage,initialize_growth,
    read_growth,plan_potential_allocation,apply_growth_plan)
from role_attributes import load_attribute_rules,AttributeBaseline
from role_attribute_storage import (prepare_attribute_storage,initialize_attribute_baseline,read_attribute_snapshot,update_role_vitals)


def main():
    growth_rules,attribute_rules=load_growth_rules(),load_attribute_rules()
    with tempfile.TemporaryDirectory() as directory:
        accounts=AccountStore(Path(directory)/'attributes.sqlite3')
        with closing(accounts.connect()) as db:
            prepare_growth_storage(db);prepare_attribute_storage(db)
        def initialize(name,dead=False,maximum=100):
            role=accounts.create_role(1111,name,11,1010109)
            epoch=accounts.acquire_lease(1111,role['id'])
            baseline=AttributeBaseline(role['id'],1,0,(10,10,10,10,10),
                (maximum,100,20,5,40,20,10,20,5))
            with closing(accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                state=initialize_growth(db,1111,role['id'],epoch,growth_rules,expected_level=1,free_points=0)
                snapshot=initialize_attribute_baseline(db,1111,role['id'],epoch,baseline,state,attribute_rules,
                    VitalState(role['id'],0,0 if dead else maximum-10,maximum,80,100))
            return role,epoch,snapshot
        role,epoch,initial=initialize('属性成长')
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            credit_experience(db,1111,role['id'],150,growth_rules,attribute_rules,epoch)
            state=read_growth(db,1111,role['id'])
            plan=plan_potential_allocation(state,(0,0,5,0,0),state.revision,growth_rules)
            apply_growth_plan(db,1111,role['id'],epoch,plan,'strength-five',growth_rules,attribute_rules)
            result=read_attribute_snapshot(db,1111,role['id'],epoch)
            a,v=result.attributes,result.vitals
            assert (a.level,a.hp_max,a.mp_max,a.physical_attack,a.hit,a.speed)==(2,110,106,34,64,11)
            assert (v.hp,v.max_hp,v.mp,v.max_mp,v.version)==(100,110,86,106,1)
            apply_growth_plan(db,1111,role['id'],epoch,plan,'strength-five',growth_rules,attribute_rules)
            assert read_attribute_snapshot(db,1111,role['id'],epoch)==result
            wounded=replace(v,version=v.version+1,hp=90,mp=81)
            update_role_vitals(db,1111,role['id'],epoch,v,wounded)
            credit_experience(db,1111,role['id'],195,growth_rules,attribute_rules,epoch)
            latest=read_attribute_snapshot(db,1111,role['id'],epoch)
            assert (latest.vitals.hp,latest.vitals.max_hp,latest.vitals.mp,latest.vitals.max_mp)==(100,120,87,112)
            try: update_role_vitals(db,1111,role['id'],epoch,v,wounded)
            except ValueError: pass
            else: raise AssertionError('Old damage result replaced newer growth vitals')
        dead,dead_epoch,_=initialize('倒地成长',True)
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            credit_experience(db,1111,dead['id'],150,growth_rules,attribute_rules,dead_epoch)
            assert read_attribute_snapshot(db,1111,dead['id'],dead_epoch).vitals.hp==0
        overflow,overflow_epoch,before=initialize('溢出回滚',maximum=2**31-1)
        try:
            with closing(accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                credit_experience(db,1111,overflow['id'],150,growth_rules,attribute_rules,overflow_epoch)
            raise AssertionError('Overflowing attributes accepted')
        except ValueError:
            pass
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN')
            current=read_growth(db,1111,overflow['id'])
            assert (current.level,current.experience,current.free_points,current.revision)==(1,0,0,0)
            assert read_attribute_snapshot(db,1111,overflow['id'],overflow_epoch)==before
        report={'passed':['explicit baseline, original coefficient composition and designed physical attack',
            'L2 + strength5 gives HP110/MP106/attack34/hit64/speed11',
            'missing HP/MP preserved; no duplicate vital refresh on allocation replay',
            'growth preserves latest stored wounds; old vital results rejected',
            'dead character stays dead; attribute overflow rolls back level/XP/points/vitals'],
            'native_attribute_refresh_tested':False,'live_characters_changed':False}
    (OUT/'evidence/role-attribute-storage-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':main()
