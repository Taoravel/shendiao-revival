"""Original NPC-only type50 handoffs, with minimal disposable storage checks."""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
import json
import struct
import tempfile
from accounts import AccountStore
from inventory import Inventory
from tasks import prepare_task_store
from task_domain import (TaskDomain,TaskActor,TaskSnapshot,TaskEvidence,
    supports_npc_empty_scenario,supports_npc_start_dialogue,supports_npc_finish_dialogue)
from task_persistence import load_task_state,apply_task_plan
from task_conversation import TaskConversation
from task_session import TaskIntent
from task_protocol import C_COMMIT_SCENARIO_QUEST,C_QUEST_DIALOG_END,decode_scenario_state,decode_accept_scenario_quest
from task_workflow import complete_task_transaction,completion_messages
from task_rewards import prepare_reward_storage
from currency import load_currency_rules,prepare_wallet_storage,initialize_wallet
from world_owner import MapAddress,Location
from world_npcs import load_placements,NpcScene
from world_catalog import maps
from inspect_client import OUT


def refuse(call):
    try:call()
    except ValueError:return
    raise AssertionError('Unsupported NPC scenario handoff accepted')


def main():
    with tempfile.TemporaryDirectory() as directory:
        accounts=AccountStore(Path(directory)/'empty-scenario.sqlite3')
        resources=prepare_task_store(accounts);config=Inventory.prepare(accounts);cash=load_currency_rules()
        with closing(accounts.connect()) as db:prepare_reward_storage(db);prepare_wallet_storage(db)
        supported={q for q,t in resources.definitions.items() if supports_npc_empty_scenario(t)}
        assert supported=={203601,205701,233701}
        assert sum(supports_npc_finish_dialogue(t) for t in resources.definitions.values())==122
        assert sum(supports_npc_start_dialogue(t) for t in resources.definitions.values())==2
        for q in supported:
            task=resources.definitions[q];actor=TaskActor(1111,1,123,task['level']['min'],1010109)
            state=TaskSnapshot(1,active=frozenset((q,)))
            evidence=TaskEvidence(q,1,123,'npc_empty_scenario_committed','offline-npc',
                map_id=task['target']['map_id'],npc_id=task['target']['npc_id'])
            plan=TaskDomain(resources).plan(actor,state,'complete',q,evidence=evidence)
            assert dict(plan.reward_scalars)==dict(task['display_rewards']) and plan.next_ids==task['next_ids']
            assert not plan.completion_finish_dialogue and not plan.completion_effect_id
            for invalid in ('npc_dialogue_completed','npc_start_dialogue_completed','npc_finish_dialogue_completed'):
                refuse(lambda:TaskDomain(resources).plan(actor,state,'complete',q,evidence=replace(evidence,kind=invalid)))
        for q in (102101,203201,221201,231001,319901,102622):
            assert not supports_npc_empty_scenario(resources.definitions[q])
        role_id=accounts.create_role(1111,'原NPC空交接',11,1010109)['id'];epoch=accounts.acquire_lease(1111,role_id)
        inv=Inventory(accounts,1111,role_id,config,epoch=epoch,currency_rules=cash)
        q=203601;task=resources.definitions[q]
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');db.execute('UPDATE roles SET level=29 WHERE id=?',(role_id,))
            initialize_wallet(db,1111,role_id,epoch,(31,0,0,0),'explicit_migration',cash)
            actor,state=load_task_state(db,1111,role_id,epoch)
        placements=load_placements()[1007];npc=next(p for p in placements if p.npc_id==10958)
        address=MapAddress(1007,1,0);location=Location(role_id,epoch,address,1,npc.x,npc.y)
        scene=NpcScene(address,placements,maps(),interaction_radius=32,binding_capacity=1);scene.bind(401,npc.placement_id)
        proof=scene.interact(struct.pack('>Q',401),location,location,request_id='real-empty-npc',deadline_ms=1000,now_ms=1)
        local=TaskConversation(resources,role_id,epoch);command=TaskIntent(C_COMMIT_SCENARIO_QUEST,q,401,0)
        refuse(lambda:local.plan_accept(actor,state,command,proof,location,now_ms=2,deadline_ms=1000))
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            apply_task_plan(db,actor,TaskDomain(resources).plan(actor,state,'offer',q),'trusted-offer')
            actor,state=load_task_state(db,1111,role_id,epoch)
            apply_task_plan(db,actor,local.plan_accept(actor,state,command,proof,location,now_ms=2,deadline_ms=1000),'accept')
            actor,state=load_task_state(db,1111,role_id,epoch)
        assert decode_accept_scenario_quest(local.resume_messages(actor,state)[0][1]).state==0
        assert local.open(actor,state,q,proof,location,now_ms=3,deadline_ms=1000).lines==()
        assert decode_scenario_state(local.opening_messages()[0][1])==(q,3)
        refuse(lambda:local.plan_finish(actor,state,TaskIntent(C_QUEST_DIALOG_END,q),location,now_ms=4))
        refuse(lambda:local.plan_finish(actor,state,replace(command,npc_key=402),location,now_ms=4))
        refuse(lambda:local.plan_finish(actor,state,command,replace(location,version=2),now_ms=4))
        plan=local.plan_finish(actor,state,command,location,now_ms=4)
        def complete(db):
            result=complete_task_transaction(db,actor,plan,'empty-original-commit',resources,inv,currency_rules=cash)
            return result,inv.equipment_bag_messages(db,epoch)+completion_messages(result)
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');result,messages=complete(db)
            assert result.started_tasks==(203690,) and result.rewards.experience_awarded==0
            assert len(messages)>=2 and not result.suppress_replayed_state
        local.acknowledge(plan)
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');again,_=complete(db)
            assert again.replayed and not again.started_tasks and again.rewards.experience_awarded==0
        new_epoch=accounts.acquire_lease(1111,role_id)
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');refuse(lambda:complete(db))
            restored=load_task_state(db,1111,role_id,new_epoch)[1]
            assert q in restored.completed and 203690 in restored.active
        report=dict(supported_npc_empty_tasks=sorted(supported),static_npc_type50_total=127,
            passed=['three original NPC-only empty scenario plans; automatic/no-NPC/Note/movie nodes excluded',
                'real NPC10958 and explicit trusted offer required; active0/ready3 menu and CCommit only, wrong key/moved location/DialogEnd refuse',
                'original zero reward and unique203690 successor commit together; paid retry does not reactivate it; new lease reload and old lease fence'],
            native_source='TASK_SCENARIO_TRIGGER_RESEARCH.md',
            scope='three pure plans and original203601/NPC10958 caller transaction in disposable SQLite; trusted offer/position fixture',
            shared_runtime_tested=False,client_tested=False)
    (OUT/'evidence/task-scenario-empty-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':main()
