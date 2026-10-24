"""Original type56 geometry and actual temporary caller-transaction checks.

Direct trusted activation/position fixtures, not real navigation or live play.
"""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
import json
import tempfile
from accounts import AccountStore
from inventory import Inventory
from tasks import prepare_task_store
from task_domain import TaskDomain,TaskActor,TaskSnapshot,TaskEvidence,supports_static_region
from task_persistence import load_task_state,apply_task_plan
from task_region import (RegionCommand,load_region_resources,prepare_region_storage,
    plan_region_completion,complete_region_transaction,acknowledge_region_transaction)
from task_conversation import TaskConversation
from task_chains import plan_task_chain
from task_session import TaskIntent,decode_task_intent
from task_protocol import (C_COMMIT_SCENARIO_QUEST,C_QUEST_REACH_SCENE,S_REFRESH_SCENARIO_QUEST_STATE,
    decode_accept_scenario_quest)
from world_owner import Location,MapAddress,MapOwner
from world_catalog import maps,maze_grids,valid_position
from world_collision import maze_clear
from currency import load_currency_rules,prepare_wallet_storage,initialize_wallet
from task_rewards import prepare_reward_storage
from task_pet_experience import load_task_pet_experience_rules
from progression import read_experience,credit_experience
from inspect_client import OUT
import struct


class BrokenRefresh(Inventory):
    def equipment_bag_messages(self,db,epoch):
        raise ValueError('controlled region reply failure')


def refuse(call):
    try:call()
    except ValueError:return
    raise AssertionError('Invalid region objective was accepted')


def command_for(actor,state,task_id,location,regions,request_id='region-command'):
    intent=decode_task_intent(C_COMMIT_SCENARIO_QUEST,struct.pack('>iQi',task_id,0,0))
    return RegionCommand(intent,location,1,state.revision,request_id,'world-observation:'+request_id,
        1000,regions.definitions[task_id].fingerprint)


def main():
    with tempfile.TemporaryDirectory() as directory:
        accounts=AccountStore(Path(directory)/'regions.sqlite3')
        resources=prepare_task_store(accounts);regions=load_region_resources(resources)
        config=Inventory.prepare(accounts);cash=load_currency_rules();pet=load_task_pet_experience_rules()
        with closing(accounts.connect()) as db:
            prepare_reward_storage(db);prepare_wallet_storage(db);prepare_region_storage(db)
        catalog=json.loads((OUT/'evidence/task-region-catalog.json').read_text(encoding='utf-8'))
        expected={r['task_id']:r for r in catalog['tasks'] if r['metadata_static_candidate']}
        assert set(regions.definitions)==set(expected) and len(expected)==158
        assert len(regions.exclusions)==25 and 102626 in regions.exclusions
        world=maps();grids=maze_grids()
        for task_id,row in expected.items():
            task=resources.definitions[task_id]
            actor=TaskActor(1111,1,123,max(1,task['level']['min']),1010109)
            state=TaskSnapshot(1,3,active=frozenset((task_id,)))
            witnesses=row['coverage']['witnesses'];mask=1 if '1' in witnesses else 8
            position=witnesses[str(mask)]
            assert valid_position(position,world) and maze_clear(grids[position[0]],*position[1:],mask=mask)
            location=Location(1,123,MapAddress(position[0],1,0),2,*position[1:])
            command=command_for(actor,state,task_id,location,regions)
            plan=plan_region_completion(actor,state,command,location,resources,regions,generation=1,now_ms=2)
            assert plan.task_id==task_id and task_id in plan.after.completed
            assert dict(plan.reward_scalars)==dict(task['display_rewards'])
            assert plan.next_ids==tuple(task['next_ids'])
            if task['attributes'].get('NoteInfo'):
                assert dict(plan.continuation_fields)['NoteInfo']==task['attributes']['NoteInfo']
            assert len(dict(plan.continuation_fields).get('ScenarioInfoFinishConversationList',()))==row['finish_dialogue_count']
        # Original102391: pure edges use exactly the native half-open rectangle.
        actor=TaskActor(1111,1,123,50,1010109)
        state=TaskSnapshot(1,3,active=frozenset((102391,)))
        left,top,right,bottom=regions.definitions[102391].rectangle
        def at(x,y):
            location=Location(1,123,MapAddress(1220,1,0),2,x,y)
            command=command_for(actor,state,102391,location,regions)
            return plan_region_completion(actor,state,command,location,resources,regions,generation=1,now_ms=2)
        for x,y in ((left,top),(right-1,top),(left,bottom-1)):
            assert 102391 in at(x,y).after.completed
        for x,y in ((left-1,top),(right,top),(left,top-1),(left,bottom)):
            refuse(lambda x=x,y=y:at(x,y))
        refuse(lambda:TaskDomain(resources).plan(actor,state,'complete',102391,evidence=
            TaskEvidence(102391,1,123,'region_reached','unversioned',map_id=1220)))
        source=102342
        decision=plan_task_chain(actor,TaskSnapshot(1,completed=frozenset((source,))),source,resources)
        assert decision.status=='activate' and decision.target_id==102391
        assert decision.reason=='unique_supported_static_region'

        task_id=102391;task=resources.definitions[task_id]
        role=accounts.create_role(1111,'原到区事务',11,1010109);role_id=role['id']
        epoch=accounts.acquire_lease(1111,role_id)
        inv=Inventory(accounts,1111,role_id,config,epoch=epoch,currency_rules=cash)
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('UPDATE roles SET level=? WHERE id=?',(max(1,task['level']['min']),role_id))
            initialize_wallet(db,1111,role_id,epoch,(31,0,0,0),'explicit_migration',cash)
            for action in ('offer','accept'):
                actor,state=load_task_state(db,1111,role_id,epoch)
                apply_task_plan(db,actor,TaskDomain(resources).plan(actor,state,action,task_id),action)
            actor,state=load_task_state(db,1111,role_id,epoch)
        p=expected[task_id]['coverage']['witnesses']['1']
        location=Location(role_id,epoch,MapAddress(p[0],1,0),1,*p[1:])
        owner=MapOwner(location.address,world,capacity=2,transfer_capacity=2,mailbox_capacity=2,maze=grids[p[0]])
        owner.join(location)
        current=owner.location(role_id)
        command=command_for(actor,state,task_id,current,regions)
        assert decode_accept_scenario_quest(TaskConversation(resources,role_id,epoch).resume_messages(actor,state)[0][1]).state==0
        def submit(db,cmd=command,pos=current,inventory=inv,**changes):
            options=dict(generation=1,now_ms=3,currency_rules=cash,pet_experience_rules=pet);options.update(changes)
            return complete_region_transaction(db,1111,role_id,epoch,cmd,pos,resources,regions,inventory,**options)
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            for bad in (replace(command,intent=TaskIntent(C_QUEST_REACH_SCENE)),
                    replace(command,intent=replace(command.intent,npc_key=99)),
                    replace(command,intent=replace(command.intent,opaque=1)),
                    replace(command,task_revision=state.revision+1),
                    replace(command,definition_fingerprint='changed')):
                refuse(lambda bad=bad:submit(db,bad))
            refuse(lambda:submit(db,generation=2))
            refuse(lambda:submit(db,now_ms=1000))
            for bad in (replace(current,version=2),replace(current,state='loading'),
                    replace(current,address=MapAddress(p[0],2,0)),
                    replace(current,address=MapAddress(1221,1,0))):
                refuse(lambda bad=bad:submit(db,pos=bad))
        broken=BrokenRefresh(accounts,1111,role_id,config,epoch=epoch,currency_rules=cash)
        try:
            with closing(accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                submit(db,inventory=broken)
            raise AssertionError('Region reply failure committed')
        except ValueError as error:
            assert str(error)=='controlled region reply failure'
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            assert task_id in load_task_state(db,1111,role_id,epoch)[1].active
            assert read_experience(db,1111,role_id).experience==0
            assert not db.execute('SELECT 1 FROM task_region_receipts WHERE role_id=?',(role_id,)).fetchone()
            assert not db.execute('SELECT 1 FROM task_effects WHERE role_id=?',(role_id,)).fetchone()
            result=submit(db)
            assert not result.replayed and result.completion.rewards.experience_awarded==7500
            assert result.completion.rewards.experience_balance==7500
            assert any(k==S_REFRESH_SCENARIO_QUEST_STATE for k,_ in result.messages)
            evidence=json.loads(db.execute('SELECT evidence FROM task_region_receipts WHERE role_id=?',(role_id,)).fetchone()[0])
            assert evidence['location']==json.loads(json.dumps(current,default=lambda x:x.__dict__))
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            again=submit(db,pos=None,now_ms=1001)
            assert again.replayed and again.completion.rewards.experience_balance==7500
            assert not any(k==S_REFRESH_SCENARIO_QUEST_STATE for k,_ in again.messages)
            refuse(lambda:submit(db,replace(command,source_id='changed-intent'),now_ms=1001))
            fresh=replace(command,request_id='new-identical-wire',source_id='new-world-observation')
            assert submit(db,fresh,pos=None).replayed
        new_epoch=accounts.acquire_lease(1111,role_id)
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            refuse(lambda:submit(db))
            refuse(lambda:complete_region_transaction(db,1111,role_id,new_epoch,command,None,
                resources,regions,inv,generation=2,now_ms=5,currency_rules=cash,pet_experience_rules=pet))
            credit_experience(db,1111,role_id,7)
            ack=acknowledge_region_transaction(db,1111,role_id,new_epoch,command.intent,resources,regions,inv,
                currency_rules=cash,pet_experience_rules=pet)
            assert ack.replayed and ack.completion.rewards.experience_balance==7507
            assert not any(k==S_REFRESH_SCENARIO_QUEST_STATE for k,_ in ack.messages)
            refuse(lambda:acknowledge_region_transaction(db,1111,role_id,new_epoch,
                TaskIntent(C_COMMIT_SCENARIO_QUEST,102131),resources,regions,inv,currency_rules=cash))
        # The two original overlapping objectives are not both completed by one
        # packet. This pure Interface selects only its requested task ID.
        actor=TaskActor(1111,1,123,90,1010109)
        state=TaskSnapshot(1,3,active=frozenset((222609,232803)))
        location=Location(1,123,MapAddress(1225,1,0),1,624,64)
        plan=plan_region_completion(actor,state,command_for(actor,state,222609,location,regions),
            location,resources,regions,generation=1,now_ms=2)
        assert plan.after.active==frozenset((232803,))
        report=dict(supported_static_regions=len(regions.definitions),excluded_regions=len(regions.exclusions),
            passed=['158 original objectives match catalog; real maze witnesses with explicit mask; rewards/next/finish/note preserved',
                'native half-open edges, CCommit key0/option0, current Location/instance/version/state, task revision/generation/deadline',
                'actual original102391 with public MapOwner Location and Inventory in temporary caller transaction; original7500XP',
                'late reply failure rolls back objective/rewards/effects/region receipt; paid duplicate after deadline acknowledges once',
                'changed retry identity refuses; old epoch/generation refuses; new owner ack returns current7507XP without repeated state1',
                'original102342 unique successor102391 activates through existing chain policy; original active resume state0',
                'overlapping222609/232803 only requested task completes'],
            scope='direct trusted activation/position fixtures; no actual role navigation, lightgong permission, animation or live process',
            runtime_integrated=False,client_tested=False)
    (OUT/'evidence/task-region-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':main()
