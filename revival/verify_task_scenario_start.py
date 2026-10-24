"""Necessary type50 start-dialogue checks, using original NPC and temp DB."""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
import json
import struct
import tempfile
from accounts import AccountStore
from inventory import Inventory
from tasks import prepare_task_store
from task_domain import TaskDomain,TaskActor,TaskSnapshot,TaskEvidence,supports_npc_start_dialogue,supports_npc_finish_dialogue
from task_persistence import load_task_state,apply_task_plan
from task_conversation import TaskConversation
from task_session import TaskIntent,decode_task_intent
from task_protocol import C_COMMIT_SCENARIO_QUEST,C_QUEST_DIALOG_END,decode_scenario_state,decode_accept_scenario_quest
from task_workflow import complete_task_transaction,completion_messages
from task_rewards import prepare_reward_storage
from currency import load_currency_rules,prepare_wallet_storage,initialize_wallet,read_wallet
from progression import read_experience
from world_owner import MapAddress,Location
from world_npcs import load_placements,NpcScene
from world_catalog import maps
from inspect_client import OUT


def refuse(call):
    try:call()
    except ValueError:return
    raise AssertionError('Unsupported or stale scenario start action accepted')


class BrokenRefresh(Inventory):
    def equipment_bag_messages(self,db,epoch):
        raise ValueError('controlled start-dialogue reply failure')


def main():
    with tempfile.TemporaryDirectory() as directory:
        accounts=AccountStore(Path(directory)/'scenario-start.sqlite3')
        resources=prepare_task_store(accounts);config=Inventory.prepare(accounts);cash=load_currency_rules()
        with closing(accounts.connect()) as db:prepare_reward_storage(db);prepare_wallet_storage(db)
        supported={q for q,t in resources.definitions.items() if supports_npc_start_dialogue(t)}
        assert supported=={201201,230401}
        assert len([t for t in resources.definitions.values() if supports_npc_finish_dialogue(t)])==122
        for q in supported:
            task=resources.definitions[q];actor=TaskActor(1111,1,123,task['level']['min'],1010109)
            state=TaskSnapshot(1,active=frozenset((q,)))
            evidence=TaskEvidence(q,1,123,'npc_start_dialogue_completed','offline-npc',
                map_id=task['target']['map_id'],npc_id=task['target']['npc_id'])
            plan=TaskDomain(resources).plan(actor,state,'complete',q,evidence=evidence)
            assert not plan.completion_finish_dialogue and not plan.completion_effect_id
            assert dict(plan.reward_scalars)==dict(task['display_rewards'])
            assert plan.next_ids==task['next_ids']
            for invalid in ('npc_dialogue_completed','npc_finish_dialogue_completed'):
                refuse(lambda:TaskDomain(resources).plan(actor,state,'complete',q,evidence=replace(evidence,kind=invalid)))
        for q in (101001,230701,323001,323101,323201,323301,101109,103309):
            assert not supports_npc_start_dialogue(resources.definitions[q])

        q=201201;task=resources.definitions[q]
        role_id=accounts.create_role(1111,'原开始对白NPC',11,1010109)['id'];epoch=accounts.acquire_lease(1111,role_id)
        inv=Inventory(accounts,1111,role_id,config,epoch=epoch,currency_rules=cash)
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');db.execute('UPDATE roles SET level=22 WHERE id=?',(role_id,))
            initialize_wallet(db,1111,role_id,epoch,(31,0,0,0),'explicit_migration',cash)
            actor,state=load_task_state(db,1111,role_id,epoch)
        address=MapAddress(1002,1,0);placements=load_placements()[1002]
        npc=next(p for p in placements if p.npc_id==10903)
        location=Location(role_id,epoch,address,1,npc.x,npc.y)
        scene=NpcScene(address,placements,maps(),interaction_radius=32,binding_capacity=1);scene.bind(301,npc.placement_id)
        proof=scene.interact(struct.pack('>Q',301),location,location,request_id='original-start-npc',deadline_ms=1000,now_ms=1)
        local=TaskConversation(resources,role_id,epoch)
        command=decode_task_intent(C_COMMIT_SCENARIO_QUEST,struct.pack('>iQi',q,301,0))
        # Test an explicit trusted offer fixture, not natural prerequisite proof.
        refuse(lambda:local.plan_accept(actor,state,command,proof,location,now_ms=2,deadline_ms=1000))
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            apply_task_plan(db,actor,TaskDomain(resources).plan(actor,state,'offer',q),'trusted-offer')
            actor,state=load_task_state(db,1111,role_id,epoch)
            accept=local.plan_accept(actor,state,command,proof,location,now_ms=2,deadline_ms=1000)
            apply_task_plan(db,actor,accept,'accept');actor,state=load_task_state(db,1111,role_id,epoch)
        assert decode_accept_scenario_quest(local.resume_messages(actor,state)[0][1]).state==0
        dialogue=local.open(actor,state,q,proof,location,now_ms=3,deadline_ms=1000)
        assert dialogue.lines==tuple((x['speaker'],x['text']) for x in task['dialogue']['start']) and len(dialogue.lines)==2
        assert decode_scenario_state(local.opening_messages()[0][1])==(q,3)
        refuse(lambda:local.plan_finish(actor,state,TaskIntent(C_QUEST_DIALOG_END,q),location,now_ms=4))
        refuse(lambda:local.plan_finish(actor,state,replace(command,npc_key=302),location,now_ms=4))
        refuse(lambda:local.plan_finish(actor,state,command,replace(location,version=2),now_ms=4))
        refuse(lambda:local.plan_finish(actor,state,command,location,now_ms=1000))
        plan=local.plan_finish(actor,state,command,location,now_ms=4)
        def complete(db,inventory=inv):
            result=complete_task_transaction(db,actor,plan,'original-start-commit',resources,inventory,currency_rules=cash)
            return result,inventory.equipment_bag_messages(db,epoch)+completion_messages(result)
        broken=BrokenRefresh(accounts,1111,role_id,config,epoch=epoch,currency_rules=cash)
        try:
            with closing(accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE');complete(db,broken)
            raise AssertionError('Late reply failure committed')
        except ValueError as error:assert str(error)=='controlled start-dialogue reply failure'
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            assert load_task_state(db,1111,role_id,epoch)[1].active==frozenset((q,))
            assert not db.execute('SELECT 1 FROM task_effects WHERE role_id=?',(role_id,)).fetchone()
            result,messages=complete(db)
            assert not result.started_tasks and not result.suppress_replayed_state
            effect=json.loads(db.execute('SELECT payload FROM task_effects WHERE role_id=? AND task_id=?',
                (role_id,q)).fetchone()[0])
            assert effect['next_ids']==[201202] and effect['chain_status']=='pending'
            assert effect['chain_reason']=='successor_gameplay_unimplemented'
            # cacceptabletask advertises aggregate20000XP/10000silver; this
            # individual cmainmissioninfo node explicitly awards zero.
            assert result.rewards.experience_awarded==0 and read_experience(db,1111,role_id).experience==0
            assert not result.rewards.currency_awarded
            assert {x.currency:x.balance for x in read_wallet(db,1111,role_id,epoch,cash)}['bound_silver']==0
        local.acknowledge(plan)
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');again,_=complete(db)
            assert again.replayed and not again.started_tasks and again.rewards.experience_awarded==0
        new_epoch=accounts.acquire_lease(1111,role_id)
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');refuse(lambda:complete(db))
            restored=load_task_state(db,1111,role_id,new_epoch)[1]
            assert q in restored.completed and 201202 not in restored.active
        report=dict(supported_npc_start_tasks=sorted(supported),existing_npc_finish_tasks=122,
            passed=['two original noncyclic start-only plans; no-NPC/placeholder/transfer/round families excluded',
                'explicit server offer required; real NPC10903 start lines/active0/ready3 and exact CCommit; dialog-end/stale position/key/deadline refused',
                'original201201 keeps zeroXP/zeroSilver despite different aggregate offer display; battle201202 remains pending, without skipping or dummy battle',
                'late reply failure rolls back task/next/effect; identical retry awards once and new lease restores; old lease refuses'],
            native_source='TASK_SCENARIO_START_RESEARCH.md',
            scope='two pure plans and one original NPC/caller transaction in disposable SQLite; trusted offer and position fixtures',
            activity_eligibility_verified=False,shared_runtime_tested=False,client_tested=False)
    (OUT/'evidence/task-scenario-start-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':main()
