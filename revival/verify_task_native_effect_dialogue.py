"""Original10 local60001 effect quests; temporary NPC/role transactions only."""
from contextlib import closing
from pathlib import Path
import json
import struct
import tempfile
from accounts import AccountStore
from inventory import Inventory
from tasks import prepare_task_store
from task_domain import (TaskDomain,NATIVE_EFFECT_DIALOGUE_IDS,supports_plain_dialogue,
                         supports_native_effect_dialogue)
from task_persistence import load_task_state,apply_task_plan
from task_rewards import prepare_reward_storage
from task_conversation import TaskConversation
from task_session import TaskIntent
from task_protocol import (C_COMMIT_SCENARIO_QUEST,C_QUEST_DIALOG_END,S_REFRESH_SCENARIO_QUEST_STATE,
                           decode_accept_scenario_quest)
from task_workflow import complete_task_transaction,replay_completed_task_transaction,completion_messages
from progression import read_experience
from world_owner import MapAddress,Location
from world_npcs import NpcScene,load_placements
from world_catalog import maps
from inspect_client import OUT


def main():
    with tempfile.TemporaryDirectory() as directory:
        accounts=AccountStore(Path(directory)/'native-effect.sqlite3')
        resources=prepare_task_store(accounts)
        config=Inventory.prepare(accounts)
        with closing(accounts.connect()) as db:prepare_reward_storage(db)
        supported={q for q,t in resources.definitions.items() if supports_native_effect_dialogue(t)}
        assert supported==NATIVE_EFFECT_DIALOGUE_IDS
        assert all(not supports_plain_dialogue(resources.definitions[q]) for q in supported)
        assert not supports_native_effect_dialogue(resources.definitions[100186])
        placements=load_placements()[1006]
        address=MapAddress(1006,1,0)
        for index,task_id in enumerate(sorted(supported)):
            # Direct trusted-offer fixture isolates these original objectives;
            # this is not a natural intro/master/cart or world-travel check.
            with closing(accounts.connect()) as db,db:
                role_id=db.execute('INSERT INTO roles(account_id,name,school,shape) VALUES(1111,?,11,1010109)',
                    (f'原标题{index}',)).lastrowid
            epoch=accounts.acquire_lease(1111,role_id)
            inv=Inventory(accounts,1111,role_id,config)
            task=resources.definitions[task_id]
            npc=next(p for p in placements if p.npc_id==task['target']['npc_id'])
            location=Location(role_id,epoch,address,1,npc.x,npc.y)
            scene=NpcScene(address,placements,maps(),interaction_radius=32,binding_capacity=1)
            scene.bind(200+index,npc.placement_id)
            proof=scene.interact(struct.pack('>Q',200+index),location,location,
                request_id=f'native-effect-npc:{index}',deadline_ms=1000,now_ms=1)
            local=TaskConversation(resources,role_id,epoch)
            with closing(accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                for action in ('offer','accept'):
                    actor,state=load_task_state(db,1111,role_id,epoch)
                    apply_task_plan(db,actor,TaskDomain(resources).plan(actor,state,action,task_id),f'{task_id}:{action}')
                actor,state=load_task_state(db,1111,role_id,epoch)
                assert decode_accept_scenario_quest(local.resume_messages(actor,state)[0][1]).state==0
                dialogue=local.open(actor,state,task_id,proof,location,now_ms=2,deadline_ms=1000)
                assert len(dialogue.lines)==3
                try:
                    local.plan_finish(actor,state,TaskIntent(C_QUEST_DIALOG_END,task_id),location,now_ms=3)
                    raise AssertionError('Animation end finished local-effect task')
                except ValueError:pass
                intent=TaskIntent(C_COMMIT_SCENARIO_QUEST,task_id,proof.entity_key,0)
                plan=local.plan_finish(actor,state,intent,location,now_ms=3)
                assert plan.completion_effect_id==60001
            if index==0:
                try:
                    with closing(accounts.connect()) as db,db:
                        db.execute('BEGIN IMMEDIATE')
                        complete_task_transaction(db,actor,plan,'finish-native-effect',resources,inv)
                        raise RuntimeError('after effect/XP/next/receipt')
                except RuntimeError:pass
                with closing(accounts.connect()) as db,db:
                    db.execute('BEGIN')
                    assert task_id in load_task_state(db,1111,role_id,epoch)[1].active
                    assert read_experience(db,1111,role_id).experience==0
                    assert not db.execute('SELECT 1 FROM task_effects WHERE role_id=?',(role_id,)).fetchone()
            with closing(accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                complete=complete_task_transaction(db,actor,plan,'finish-native-effect',resources,inv)
                assert complete.rewards.experience_awarded==120 and complete.rewards.experience_balance==120
                assert complete.started_tasks==tuple(task['next_ids'])
                assert completion_messages(complete)[0][0]==S_REFRESH_SCENARIO_QUEST_STATE
                effect=json.loads(db.execute('SELECT payload FROM task_effects WHERE role_id=? AND task_id=?',(role_id,task_id)).fetchone()[0])
                assert effect['continuation_fields']['ScenarioInfoAnimationID']=='60001'
                assert effect['continuation_resolved_fields']==['ScenarioInfoAnimationID']
                assert effect['native_completion_effect']['status']=='delegated_to_original_client'
                assert effect['native_completion_effect']['gui_confirmed'] is False
            with closing(accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                again=complete_task_transaction(db,actor,plan,'finish-native-effect',resources,inv)
                assert again.replayed and again.native_completion_effect_id==60001
                assert not any(k==S_REFRESH_SCENARIO_QUEST_STATE for k,_ in completion_messages(again))
                assert again.rewards.experience_balance==120
            epoch=accounts.acquire_lease(1111,role_id)
            with closing(accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                actor,_=load_task_state(db,1111,role_id,epoch)
                again=replay_completed_task_transaction(db,actor,task_id,resources,inv)
                assert again.replayed and not any(k==S_REFRESH_SCENARIO_QUEST_STATE for k,_ in completion_messages(again))
        report=dict(passed=['exact original10 type10/60001 capability; plain dialogue remains narrow; 200xx card excluded',
            'actual NPC entity/distance proof, original three lines and ordinary CCommit; no dialog/CG-end prerequisite',
            'original120XP/unique next/effect delegation/receipt share caller transaction; late failure rolls back',
            'same-plan and reconnect acknowledgement keep current120XP and omit repeated state1 to avoid native title replay'],
            source='TASK_JIAXING_SCENARIO_RESEARCH.md',tested_scope='direct trusted-offer NPC objectives in temporary DB',
            runtime_tested=False,native_gui_tested=False)
    (OUT/'evidence/task-native-effect-dialogue-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':main()
