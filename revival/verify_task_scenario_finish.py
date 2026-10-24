"""Type50 NPC commit/finish presentation, with necessary offline transactions."""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
import json
import struct
import tempfile
from accounts import AccountStore
from inventory import Inventory
from tasks import prepare_task_store
from task_domain import TaskDomain,TaskActor,TaskSnapshot,TaskEvidence,supports_npc_finish_dialogue,supports_plain_dialogue
from task_persistence import load_task_state,apply_task_plan
from task_conversation import TaskConversation
from task_session import TaskIntent,decode_task_intent
from task_protocol import C_COMMIT_SCENARIO_QUEST,C_QUEST_DIALOG_END,S_REFRESH_SCENARIO_QUEST_STATE,decode_scenario_state,decode_accept_scenario_quest
from task_workflow import complete_task_transaction,replay_completed_task_transaction,completion_messages
from task_chains import plan_task_chain
from task_rewards import prepare_reward_storage
from task_pet_experience import load_task_pet_experience_rules
from currency import load_currency_rules,prepare_wallet_storage,initialize_wallet,read_wallet
from progression import read_experience,credit_experience
from world_owner import MapAddress,Location
from world_npcs import load_placements,NpcScene
from world_catalog import maps
from inspect_client import OUT


class BrokenRefresh(Inventory):
    def equipment_bag_messages(self,db,epoch):
        raise ValueError('controlled scenario completion encoding failure')


def refuse(call):
    try:call()
    except ValueError:return
    raise AssertionError('Invalid native scenario NPC action accepted')


def main():
    with tempfile.TemporaryDirectory() as directory:
        accounts=AccountStore(Path(directory)/'scenario-finish.sqlite3')
        resources=prepare_task_store(accounts);config=Inventory.prepare(accounts)
        cash=load_currency_rules();pet=load_task_pet_experience_rules()
        with closing(accounts.connect()) as db:prepare_reward_storage(db);prepare_wallet_storage(db)
        supported={q for q,t in resources.definitions.items() if supports_npc_finish_dialogue(t)}
        assert len(supported)==122
        assert all(not supports_plain_dialogue(resources.definitions[q]) for q in supported)
        assert not supported&{102317,102392,102490,203501,230801,230901,226701,226901,100101,102622,206103,101001}
        for q in supported:
            task=resources.definitions[q]
            actor=TaskActor(1111,1,123,max(1,task['level']['min']),1010109)
            state=TaskSnapshot(1,active=frozenset((q,)))
            evidence=TaskEvidence(q,1,123,'npc_finish_dialogue_completed','offline-source',
                map_id=task['target']['map_id'],npc_id=task['target']['npc_id'])
            plan=TaskDomain(resources).plan(actor,state,'complete',q,evidence=evidence)
            assert plan.completion_finish_dialogue and plan.after.completed==frozenset((q,))
            assert dict(plan.reward_scalars)==dict(task['display_rewards'])
            assert dict(plan.continuation_fields)['ScenarioInfoFinishConversationList']==tuple(task['lists']['ScenarioInfoFinishConversationList'])
            refuse(lambda:TaskDomain(resources).plan(actor,state,'complete',q,
                evidence=replace(evidence,kind='npc_dialogue_completed')))
        # Existing unique-edge policy accepts this family without relaxing its
        # separate unknown-prerequisite check.
        actor=TaskActor(1111,1,123,100,1010109)
        source=next(t['id'] for t in resources.definitions.values() if t['next_ids']==(200104,))
        decision=plan_task_chain(actor,TaskSnapshot(1,completed=frozenset((source,))),source,resources)
        assert decision.status=='activate' and decision.reason=='unique_supported_npc_finish_dialogue'

        q=200104;task=resources.definitions[q]
        role=accounts.create_role(1111,'完成对白原NPC',11,1010109);role_id=role['id']
        epoch=accounts.acquire_lease(1111,role_id)
        inv=Inventory(accounts,1111,role_id,config,epoch=epoch,currency_rules=cash)
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('UPDATE roles SET level=? WHERE id=?',(max(1,task['level']['min']),role_id))
            initialize_wallet(db,1111,role_id,epoch,(31,0,0,0),'explicit_migration',cash)
            for action in ('offer','accept'):
                actor,state=load_task_state(db,1111,role_id,epoch)
                apply_task_plan(db,actor,TaskDomain(resources).plan(actor,state,action,q),action)
            actor,state=load_task_state(db,1111,role_id,epoch)
        address=MapAddress(1007,1,0);placements=load_placements()[1007]
        npc=next(p for p in placements if p.npc_id==10530)
        location=Location(role_id,epoch,address,1,npc.x,npc.y)
        scene=NpcScene(address,placements,maps(),interaction_radius=32,binding_capacity=1)
        scene.bind(201,npc.placement_id)
        proof=scene.interact(struct.pack('>Q',201),location,location,request_id='real-scenario-npc',deadline_ms=1000,now_ms=1)
        local=TaskConversation(resources,role_id,epoch)
        assert decode_accept_scenario_quest(local.resume_messages(actor,state)[0][1]).state==0
        dialogue=local.open(actor,state,q,proof,location,now_ms=2,deadline_ms=1000)
        assert dialogue.lines==() and len(task['dialogue']['finish'])==4
        assert decode_scenario_state(local.opening_messages()[0][1])==(q,3)
        end=TaskIntent(C_QUEST_DIALOG_END,q)
        refuse(lambda:local.plan_finish(actor,state,end,location,now_ms=3))
        command=decode_task_intent(C_COMMIT_SCENARIO_QUEST,struct.pack('>iQi',q,201,0))
        refuse(lambda:local.plan_finish(actor,state,replace(command,npc_key=202),location,now_ms=3))
        refuse(lambda:local.plan_finish(actor,state,command,replace(location,version=2),now_ms=3))
        refuse(lambda:local.plan_finish(actor,state,command,location,now_ms=1000))
        plan=local.plan_finish(actor,state,command,location,now_ms=3)
        def complete(db,inventory=inv):
            completion=complete_task_transaction(db,actor,plan,'finish-original-scenario',resources,inventory,
                currency_rules=cash,pet_experience_rules=pet)
            messages=inventory.equipment_bag_messages(db,epoch)+completion_messages(completion)
            return completion,messages
        broken=BrokenRefresh(accounts,1111,role_id,config,epoch=epoch,currency_rules=cash)
        try:
            with closing(accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE');complete(db,broken)
            raise AssertionError('Late scenario reply failure committed')
        except ValueError as error:assert str(error)=='controlled scenario completion encoding failure'
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            assert q in load_task_state(db,1111,role_id,epoch)[1].active
            assert read_experience(db,1111,role_id).experience==0
            assert not db.execute('SELECT 1 FROM task_effects WHERE role_id=?',(role_id,)).fetchone()
            assert {x.currency:x.balance for x in read_wallet(db,1111,role_id,epoch,cash)}['bound_silver']==0
            completion,messages=complete(db)
            assert completion.suppress_replayed_state and not completion.replayed
            assert completion.rewards.experience_awarded==11000 and completion.rewards.experience_balance==11000
            assert completion.rewards.currency_awarded==(('SMoney','bound_silver',2275),)
            assert sum(k==S_REFRESH_SCENARIO_QUEST_STATE for k,_ in messages)==1
            effect=json.loads(db.execute('SELECT payload FROM task_effects WHERE role_id=? AND task_id=?',(role_id,q)).fetchone()[0])
            assert effect['native_finish_dialogue']==dict(handler='original_state1',status='delegated_to_original_client',gui_confirmed=False)
            assert len(effect['continuation_fields']['ScenarioInfoFinishConversationList'])==4
            assert {'ScenarioInfoFinishConversationList','ScenarioInfoFinishNpcID'}<=set(effect['continuation_resolved_fields'])
        local.acknowledge(plan)
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            current_actor,current_state=load_task_state(db,1111,role_id,epoch)
            refuse(lambda:local.plan_finish(current_actor,current_state,end,location,now_ms=4))
            again,messages=complete(db)
            assert again.replayed and not any(k==S_REFRESH_SCENARIO_QUEST_STATE for k,_ in messages)
            assert again.rewards.experience_balance==11000
            assert {x.currency:x.balance for x in read_wallet(db,1111,role_id,epoch,cash)}['bound_silver']==2275
        new_epoch=accounts.acquire_lease(1111,role_id)
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            refuse(lambda:complete(db))
            credit_experience(db,1111,role_id,7)
            fresh_actor,fresh_state=load_task_state(db,1111,role_id,new_epoch)
            replay=replay_completed_task_transaction(db,fresh_actor,q,resources,inv,currency_rules=cash,pet_experience_rules=pet)
            assert replay.replayed and replay.rewards.experience_balance==11007
            assert not any(k==S_REFRESH_SCENARIO_QUEST_STATE for k,_ in completion_messages(replay))
        report=dict(supported_npc_finish_tasks=len(supported),passed=[
            '122 original type50 finish-only NPC plans; ordinary type10 evidence remains invalid; NPC-less/999999/movie/transfer/branch excluded',
            'ready3 and empty start require original CCommit key/option; CQuestDialogEnd cannot first complete; active resume state0',
            'actual original200104/NPC10530 caller transaction: original11000XP/2275 bound silver and four finish lines; no live navigation',
            'late native bag error rolls back task/reward/finish delegation/receipts; retry commits exactly once',
            'paid/reconnect replay keeps current11007XP and silver2275 with no repeated state1; old lease refuses',
            'original unique supported NPC-finish successor activates through existing chain policy'],
            native_source='TASK_SCENARIO_OBJECTIVES_RESEARCH.md',
            scope='122 pure original plans; one full actual NPC/storage/inventory transaction in disposable SQLite; no GUI or server process',
            shared_runtime_tested=False,client_tested=False)
    (OUT/'evidence/task-scenario-finish-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':main()
