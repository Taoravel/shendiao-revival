"""Original11 selected-state objectives and actual public pet selection hook.

The quest/pets/position are trusted disposable fixtures, not the paused story
battle chain or a restored source of the originally gifted pet.
"""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
import json
import struct
import tempfile
from accounts import AccountStore
from inventory import Inventory,FIGHT_PET,REST_PET
from task_domain import TaskDomain,TaskActor,TaskSnapshot,TaskEvidence,FIGHTING_PET_TASK_IDS
from task_persistence import load_task_state,apply_task_plan
from task_chains import plan_task_chain
from task_conversation import TaskConversation
from task_fighting_pet import load_fighting_pet_task_resources,reconcile_fighting_pet_task
from task_protocol import S_ACCEPT_SCENARIO_QUEST,S_REFRESH_SCENARIO_QUEST_STATE
from world_owner import Location,MapAddress
from currency import initialize_wallet
from role_growth import initialize_growth,read_growth
from role_attribute_storage import initialize_attribute_baseline
from role_equipment import EquipmentAttributeBasis,resource_caps_from_projection
from role_equipment_storage import initialize_equipment_attribute_basis,current_equipment_totals,synchronize_inventory_resource_source
from role_resource_plan import load_resource_rules
from role_resource_storage import migrate_role_resources,read_role_resources
from inspect_client import OUT
import runtime_storage


def refuse(call):
    try:call()
    except ValueError:return
    raise AssertionError('Untrusted selected-pet objective accepted')


class BrokenBag(Inventory):
    def equipment_bag_messages(self,db,epoch):
        raise ValueError('controlled selected-pet late native encoding failure')


def main():
    with tempfile.TemporaryDirectory(prefix='task-fighting-pet-') as directory:
        store=AccountStore(Path(directory)/'state.sqlite3');runtime_storage.prepare(store)
        resources=store.task_resources;fighting=load_fighting_pet_task_resources(resources)
        assert set(fighting.definitions)==FIGHTING_PET_TASK_IDS and len(fighting.definitions)==11
        actor=TaskActor(1111,1,1,1,1010109)
        for q in fighting.definitions:
            task=resources.definitions[q];state=TaskSnapshot(1,active=frozenset((q,)))
            e=TaskEvidence(q,1,1,'pet_set_fighting','actual-current-selected',1006,reference_id=7)
            p=TaskDomain(resources).plan(actor,state,'complete',q,evidence=e)
            assert dict(p.reward_scalars)==dict(task['display_rewards']) and dict(p.reward_scalars)['ExpReward']==200
            assert p.next_ids==tuple(task['next_ids']) and p.reward_items==()
            refuse(lambda:TaskDomain(resources).plan(actor,state,'complete',q,evidence=replace(e,reference_id=0)))
            refuse(lambda:TaskDomain(resources).plan(actor,state,'complete',q,evidence=replace(e,map_id=1007)))
            refuse(lambda:TaskDomain(resources).plan(actor,state,'complete',q,evidence=replace(e,kind='npc_dialogue_completed')))
            source=task['incoming_ids'][0]
            decision=plan_task_chain(actor,TaskSnapshot(1,completed=frozenset((source,))),source,resources)
            assert (decision.status,decision.target_id,decision.reason)==('activate',q,'unique_supported_fighting_pet_task')
        role_id=store.create_role(1111,'宠参战任务',11,1010109)['id'];epoch=store.acquire_lease(1111,role_id)
        inv=Inventory(store.leased(1111,role_id,epoch),1111,role_id)
        # Explicit fixtures use original500138(uselevel1). The original story's
        # gifted template is unknown; do not bypass the real CSetFightPet gate
        # by using low-level fight_pet with500001(uselevel5) at role level1.
        first=inv.grant_pet(500138);second=inv.grant_pet(500138)
        q=100189;rules=load_resource_rules();gear=store.equipment_attribute_rules
        location=Location(role_id,epoch,MapAddress(1006,1,0),1,348,2244)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            initialize_wallet(db,1111,role_id,epoch,(31,0,0,0),'explicit_migration',store.currency_rules)
            growth=initialize_growth(db,1111,role_id,epoch,store.growth_rules,expected_level=1,free_points=0)
            p=store.attribute_rules.initial_profile
            old=initialize_attribute_baseline(db,1111,role_id,epoch,p.baseline(role_id),growth,
                store.attribute_rules,replace(p.vitals(role_id),hp=70,mp=40))
            initialize_equipment_attribute_basis(db,1111,role_id,epoch,
                EquipmentAttributeBasis(role_id,9,0,gear.revision,0,'explicit-selected-pet-fixture'),gear)
            caps=resource_caps_from_projection(current_equipment_totals(db,1111,role_id,epoch,inv.immutable_snapshot_transaction(db),gear))
            migrate_role_resources(db,1111,role_id,epoch,old.vitals,caps,origin='explicit_migration',
                migration_id='known-selected-pet-profile',rules=rules,equipment_rules=gear)
            for action in ('offer','accept'):
                actor,state=load_task_state(db,1111,role_id,epoch)
                apply_task_plan(db,actor,TaskDomain(resources).plan(actor,state,action,q),f'fixture:{action}')
        def reconcile(db,inventory=inv,where=location,**overrides):
            kwargs=dict(growth_rules=store.growth_rules,attribute_rules=store.attribute_rules,currency_rules=store.currency_rules,
                pet_experience_rules=store.task_pet_experience_rules,resource_rules=rules,equipment_rules=gear)
            kwargs.update(overrides)
            return reconcile_fighting_pet_task(db,1111,role_id,epoch,q,resources,fighting,inventory,where,'selected-pet-complete',**kwargs)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');changes=db.total_changes
            assert reconcile(db).outcome=='waiting' and db.total_changes==changes
            refuse(lambda:reconcile(db,where=replace(location,address=MapAddress(1007,1,0))))
            actor,state=load_task_state(db,1111,role_id,epoch)
            beans=TaskConversation(resources,role_id,epoch).resume_messages(actor,state)
            assert len(beans)==1 and beans[0][0]==S_ACCEPT_SCENARIO_QUEST
        def hook(db,inventory,snapshot,*,replayed):
            synchronize_inventory_resource_source(db,1111,role_id,epoch,snapshot,'actual-set-fighting-pet',
                resource_rules=rules,equipment_rules=gear,replayed=replayed)
            return reconcile(db,inventory)
        with closing(store.connect()) as db:
            before=tuple(db.iterdump())
        try:
            # No implicit source repair in TaskWorkflow/reconcile. Omitting the
            # caller's real inventory stage must roll back the selection too.
            inv.receive(FIGHT_PET,struct.pack('>i',first),precommit=lambda db,i,s,replayed:reconcile(db,i))
            raise AssertionError('Unstaged resource source accepted')
        except ValueError:pass
        with closing(store.connect()) as db:
            assert tuple(db.iterdump())==before
        broken=BrokenBag(store.leased(1111,role_id,epoch),1111,role_id)
        try:
            broken.receive(FIGHT_PET,struct.pack('>i',first),precommit=hook)
            raise AssertionError('Controlled selected-pet failure did not fire')
        except ValueError as error:
            assert 'controlled selected-pet' in str(error)
        with closing(store.connect()) as db:
            assert tuple(db.iterdump())==before
        pending=[]
        def accepted_hook(db,i,s,*,replayed):
            result=hook(db,i,s,replayed=replayed);pending.append(result)
        reply=inv.receive(FIGHT_PET,struct.pack('>i',first),precommit=accepted_hook)
        assert reply==[(0xc07d9,struct.pack('>i',first))] and len(pending)==1
        result=pending.pop()
        assert result.outcome=='completed' and not result.replayed
        assert result.completion.rewards.experience_awarded==200
        assert result.completion.started_tasks==()
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            g=read_growth(db,1111,role_id);r=read_role_resources(db,1111,role_id,epoch,rules)
            assert (g.level,g.experience,g.free_points)==(2,111,5)
            assert (r.hp,r.caps.hp_max,r.mp,r.caps.mp_max,r.version)==(80,110,46,106,1)
            e=json.loads(db.execute('SELECT payload FROM task_effects WHERE role_id=? AND task_id=?',(role_id,q)).fetchone()[0])
            assert e['fighting_pet_objective']['pet_key']==first
            assert e['chain_status']=='pending' and e['chain_reason']=='successor_gameplay_unimplemented'
            refuse(lambda:reconcile(db,equipment_rules=None))
        def source_only(identity):
            def stage(db,i,s,*,replayed):
                synchronize_inventory_resource_source(db,1111,role_id,epoch,s,identity,
                    resource_rules=rules,equipment_rules=gear,replayed=replayed)
            return stage
        inv.receive(FIGHT_PET,struct.pack('>i',second),precommit=source_only('later-different-selected-pet'))
        inv.receive(REST_PET,b'',precommit=source_only('later-rest-pet'))
        old_epoch=epoch;epoch=store.acquire_lease(1111,role_id)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');before=read_role_resources(db,1111,role_id,epoch,rules)
            current_pet=inv.selected_fighting_pet(db);assert current_pet is None
            replay=reconcile(db,where=None)
            assert replay.replayed and replay.completion.rewards.experience_balance==111
            assert not any(kind==S_REFRESH_SCENARIO_QUEST_STATE for kind,_ in replay.messages)
            assert inv.selected_fighting_pet(db) is None and read_role_resources(db,1111,role_id,epoch,rules)==before
            assert read_growth(db,1111,role_id).experience==111
            refuse(lambda:reconcile_fighting_pet_task(db,1111,role_id,old_epoch,q,resources,fighting,inv,None,'old-callback',
                currency_rules=store.currency_rules,resource_rules=rules,equipment_rules=gear))
        report=dict(original_objectives=11,actual_task=q,passed=[
            'eleven original200XP/no-item/no-petXP objectives and exact original predecessor/successor retained; other type59 mechanisms remain excluded',
            'actual public Inventory.receive CSetFightPet0xc07d8 and synchronous same-transaction hook; current owned selected state is objective proof',
            'not selected waits without writes; wrong map, omitted source stage, half rules and stale lease reject; active0 resume provided',
            'late native bag failure rolls back entire DB including real pet selection/source/task/growth; identical retry succeeds once',
            'explicit migrated70/40 plus original200XP yieldsL2/111/free5 and80/110HP46/106MP/version1 without altering pet XP',
            'paused actual battle successor stays pending; later changing pet/rest/new lease paid ack does not reselect or pay again'],
            completion_policy='designed current selected owned nonreleased pet state under already-authorized active task; no original gifted-pet identity inferred',
            scope='pure original11 and trusted task/pet/position fixtures with actual public inventory/currency/resource modules in disposable DB',
            shared_runtime_tested=False,client_tested=False,live_server_changed=False,battle_executed=False)
    (OUT/'evidence/task-fighting-pet-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':main()
