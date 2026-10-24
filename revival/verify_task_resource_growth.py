"""Task objective/pet/character/item phases against one actual resource record."""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
import json
import tempfile
from unittest.mock import patch
from accounts import AccountStore
from inventory import Inventory,AssetChange
from task_domain import TaskDomain,TaskEvidence
from task_persistence import load_task_state,apply_task_plan
from task_workflow import complete_task_transaction,replay_completed_task_transaction,completion_messages
from task_pet_experience import TaskPetExperienceResult
from task_growth_resources import synchronize_task_inventory_source
from role_growth import initialize_growth,read_growth
from role_attribute_storage import initialize_attribute_baseline
from role_equipment import EquipmentAttributeBasis,resource_caps_from_projection
from role_equipment_storage import initialize_equipment_attribute_basis,current_equipment_totals,current_resource_profile
from role_resource_plan import load_resource_rules,plan_resource_values
from role_resource_storage import migrate_role_resources,read_role_resources,apply_resource_transition
from role_attribute_protocol import role_detail_profile
from currency import initialize_wallet
from inspect_client import OUT
import runtime_storage


class BrokenRefresh(Inventory):
    def equipment_bag_messages(self,db,epoch):raise ValueError('controlled migrated task reply failure')


def refuse(call):
    try:call()
    except ValueError:return
    raise AssertionError('Unsafe resource task completion accepted')


def main():
    rules=load_resource_rules()
    with tempfile.TemporaryDirectory(prefix='task-resource-growth-') as directory:
        store=AccountStore(Path(directory)/'state.sqlite3')
        role_id=store.create_role(1111,'分阶段资源任务',11,1010109)['id']
        runtime_storage.prepare(store);epoch=store.acquire_lease(1111,role_id)
        inv=Inventory(store.leased(1111,role_id,epoch),1111,role_id)
        pet=inv.grant_pet(500001);inv.fight_pet(pet)
        gear=store.equipment_attribute_rules;resources=store.task_resources;q=102108
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');db.execute('UPDATE roles SET level=20 WHERE id=?',(role_id,))
            growth=initialize_growth(db,1111,role_id,epoch,store.growth_rules,expected_level=20,free_points=0)
            p=store.attribute_rules.initial_profile
            legacy=initialize_attribute_baseline(db,1111,role_id,epoch,replace(p.baseline(role_id),level=20),growth,
                store.attribute_rules,replace(p.vitals(role_id),hp=70,mp=40))
            initialize_wallet(db,1111,role_id,epoch,(31,0,0,0),'explicit_migration',store.currency_rules)
            initialize_equipment_attribute_basis(db,1111,role_id,epoch,
                EquipmentAttributeBasis(role_id,9,0,gear.revision,0,'explicit-task-resource-fixture'),gear)
            inv.apply_settlement(db,AssetChange('resource-task-fixture',grants=((49009,1,1),(50056,1,1))))
            items=inv.immutable_snapshot_transaction(db).items
            weapon=next(x.id for x in items if x.template_id==49009);objective=next(x.id for x in items if x.template_id==50056)
            inv.equip_transaction(db,weapon,0,epoch,'resource-task-equip')
            pet_state=inv.pet_progress(db,pet).state
            amount=sum(inv.growth_rules.thresholds[x] for x in range(pet_state.level,25))
            inv.change_pet_growth(db,pet,'fixture-pet25',pet_state.version,'experience',amount)
            for action in ('offer','accept'):
                actor,state=load_task_state(db,1111,role_id,epoch)
                apply_task_plan(db,actor,TaskDomain(resources).plan(actor,state,action,q),action)
            caps=resource_caps_from_projection(current_equipment_totals(db,1111,role_id,epoch,inv.immutable_snapshot_transaction(db),gear))
            migrate_role_resources(db,1111,role_id,epoch,legacy.vitals,caps,origin='explicit_migration',
                migration_id='known-task-resource-origin',rules=rules,equipment_rules=gear)
            actor,state=load_task_state(db,1111,role_id,epoch)
            target=resources.definitions[q]['target']
            evidence=TaskEvidence(q,role_id,epoch,'npc_items_submitted','controlled-original102108',
                target['map_id'],target['npc_id'],50056,((objective,1),))
            plan=TaskDomain(resources).plan(actor,state,'complete',q,evidence=evidence)
            baseline=tuple(db.iterdump())
        def finish(db,inventory=inv,**changes):
            kwargs=dict(growth_rules=store.growth_rules,attribute_rules=store.attribute_rules,
                currency_rules=store.currency_rules,pet_experience_rules=store.task_pet_experience_rules,
                resource_rules=rules,equipment_rules=gear);kwargs.update(changes)
            result=complete_task_transaction(db,actor,plan,'original-resource-task',resources,inventory,**kwargs)
            messages=inventory.equipment_bag_messages(db,epoch)+completion_messages(result)
            return result,messages
        broken=BrokenRefresh(store.leased(1111,role_id,epoch),1111,role_id)
        try:
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE');finish(db,broken)
            raise AssertionError('Late migrated task encoding failure committed')
        except ValueError as error:assert str(error)=='controlled migrated task reply failure'
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');assert tuple(db.iterdump())==baseline
            # Half-injected or omitted rules cannot bypass the migrated fence.
            refuse(lambda:finish(db,equipment_rules=None))
        # The legacy default path can write before a fence rejects; always roll
        # back the WHOLE caller transaction instead of catching and committing.
        try:
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE');finish(db,resource_rules=None,equipment_rules=None)
            raise AssertionError('Legacy task path bypassed migrated resource fence')
        except ValueError:pass
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');assert tuple(db.iterdump())==baseline
            result,messages=finish(db)
            assert result.consumed_items==((objective,1),) and result.rewards.pet_experience.status=='awarded'
            assert result.rewards.experience_awarded==10000 and result.rewards.experience_balance==10000
            assert result.rewards.items_awarded==((50057,3,1),)
            assert (result.attributes.vitals.hp,result.attributes.vitals.mp)==(70,40)
            assert result.attributes.vitals.version==0
            current=current_resource_profile(db,1111,role_id,epoch,inv.immutable_snapshot_transaction(db),
                equipment_rules=gear,resource_rules=rules)
            assert current==result.attributes
            assert (inv.pet_progress(db,pet).state.level,inv.pet_progress(db,pet).state.experience)==(25,5000)
            assert len([1 for kind,_ in messages if kind==0xc32c8])==1
            assert role_detail_profile(read_growth(db,1111,role_id),current).values[:5]==(70,100,100,40,100)
            phases=tuple(db.execute("SELECT request_id,cause FROM role_resource_receipts WHERE role_id=? AND cause='inventory_change'",(role_id,)))
            assert len(phases)==2 and any('before-exp' in key for key,_ in phases) and any('after-items' in key for key,_ in phases)
            before_damage=read_role_resources(db,1111,role_id,epoch,rules)
            damage=plan_resource_values(before_damage,60,30,'medicine',rules)
            apply_resource_transition(db,1111,role_id,epoch,damage,'later-task-damage',rules=rules,equipment_rules=gear)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');before_replay=tuple(db.iterdump())
            replay,_=finish(db)
            assert (replay.attributes.vitals.hp,replay.attributes.vitals.mp)==(60,30)
            assert replay.rewards.experience_balance==10000 and not replay.started_tasks
            assert tuple(db.iterdump())==before_replay
        # A deliberately held pet channel can be paid after character_exp and
        # items already settled. No private receipt/decision SQL is fabricated.
        later_q=102313
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            inv.apply_settlement(db,AssetChange('pending-pet-objective',grants=((50064,1,1),)))
            later_key=next(x.id for x in inv.immutable_snapshot_transaction(db).items if x.template_id==50064)
            synchronize_task_inventory_source(db,1111,role_id,epoch,later_q,inv,rules,gear,phase='before-exp')
            for action in ('offer','accept'):
                later_actor,later_state=load_task_state(db,1111,role_id,epoch)
                apply_task_plan(db,later_actor,TaskDomain(resources).plan(later_actor,later_state,action,later_q),'pending-'+action)
            later_actor,later_state=load_task_state(db,1111,role_id,epoch)
            target=resources.definitions[later_q]['target']
            later_plan=TaskDomain(resources).plan(later_actor,later_state,'complete',later_q,
                evidence=TaskEvidence(later_q,role_id,epoch,'npc_items_submitted','controlled-pending-pet',
                    target['map_id'],target['npc_id'],50064,((later_key,1),)))
            with patch('task_rewards.settle_pet_experience',return_value=TaskPetExperienceResult('pending','controlled-channel-hold',7000,pet)):
                held=complete_task_transaction(db,later_actor,later_plan,'pending-channel-task',resources,inv,
                    store.growth_rules,store.attribute_rules,store.currency_rules,store.task_pet_experience_rules,
                    resource_rules=rules,equipment_rules=gear)
            assert held.rewards.pet_experience.status=='pending' and held.rewards.experience_balance==20500
            paid_growth=read_growth(db,1111,role_id)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            later_actor,_=load_task_state(db,1111,role_id,epoch)
            delayed=replay_completed_task_transaction(db,later_actor,later_q,resources,inv,
                store.growth_rules,store.attribute_rules,store.currency_rules,store.task_pet_experience_rules,
                resource_rules=rules,equipment_rules=gear)
            assert delayed.rewards.pet_experience.status=='awarded' and delayed.rewards.experience_balance==20500
            assert read_growth(db,1111,role_id)==paid_growth
            assert (inv.pet_progress(db,pet).state.level,inv.pet_progress(db,pet).state.experience)==(25,12000)
            assert (delayed.attributes.vitals.hp,delayed.attributes.vitals.mp)==(60,30)
        new_epoch=store.acquire_lease(1111,role_id)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');refuse(lambda:finish(db))
            fresh,_=load_task_state(db,1111,role_id,new_epoch)
            replay=replay_completed_task_transaction(db,fresh,q,resources,inv,store.growth_rules,store.attribute_rules,
                store.currency_rules,store.task_pet_experience_rules,resource_rules=rules,equipment_rules=gear)
            assert (replay.attributes.vitals.hp,replay.attributes.vitals.mp)==(60,30)
        report=dict(passed=['original102108 objective50056 debit, actual selected pet5000XP, character10000XP, original three bound50057 items share one migrated-resource transaction',
            'pre-EXP objective+pet revisions and post-items revision synchronize separately; final source matches actual inventory/growth and HP70/MP40 do not heal',
            'single current final growth map/RoleDetail encoded in inner workflow; no preliminary naked encoding',
            'late bag failure rolls back full DB; omitted/half rules and old epoch reject; paid/reconnect replay keeps later60/30 without source/asset/resource mutation',
            'controlled pending pet channel paid after character EXP/items: original pet receives7000 once, source converges without repeating20500XP or growth'],
            database='disposable',shared_runtime_tested=False,native_gui_verified=False,live_server_changed=False,battle_executed=False)
    (OUT/'evidence/task-resource-growth-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':main()
