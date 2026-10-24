"""Original fixed quizzes: minimal native intent and caller-transaction checks."""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
import json
import struct
import tempfile
from accounts import AccountStore
from inventory import Inventory
from tasks import prepare_task_store
from task_domain import TaskDomain,TaskActor,TaskSnapshot,TaskEvidence,supports_fixed_npc_quiz
from task_conversation import TaskConversation
from task_persistence import load_task_state,apply_task_plan
from task_session import TaskIntent
from task_protocol import C_COMMIT_SCENARIO_QUEST,C_QUEST_DIALOG_END,S_REFRESH_SCENARIO_QUEST_STATE,decode_scenario_state
from task_quiz_protocol import TaskQuizAnswer,decode_task_quiz_answer
from task_quiz import load_task_quiz_resources,open_task_quiz_transaction,answer_task_quiz_transaction
from task_rewards import prepare_reward_storage
from task_chains import plan_task_chain
from currency import prepare_wallet_storage,initialize_wallet,load_currency_rules
from progression import credit_experience
from world_npcs import load_placements,NpcScene
from world_owner import MapAddress,Location
from world_catalog import maps
from inspect_client import OUT


def refuse(call):
    try:call()
    except ValueError:return
    raise AssertionError('Invalid fixed quiz operation accepted')


class BrokenRefresh(Inventory):
    def equipment_bag_messages(self,db,epoch):raise ValueError('controlled quiz reply failure')


def main():
    decoded=decode_task_quiz_answer(struct.pack('>iQi',230407,0x1122334455667788,3))
    assert decoded==TaskQuizAnswer(230407,0x1122334455667788,3)
    for body in (b'',b'\0'*15,struct.pack('>iQi',500000,1,0),struct.pack('>iQi',230407,1,6)):
        refuse(lambda:decode_task_quiz_answer(body))
    with tempfile.TemporaryDirectory() as directory:
        accounts=AccountStore(Path(directory)/'quiz.sqlite3');resources=prepare_task_store(accounts)
        config=Inventory.prepare(accounts);cash=load_currency_rules();quiz=load_task_quiz_resources(resources)
        assert set(quiz.definitions)=={229103,229110,229112,230407,232503} and len(quiz.exclusions)==7
        assert quiz.definitions[230407].answers[0]==(0,'2')
        with closing(accounts.connect()) as db:prepare_reward_storage(db);prepare_wallet_storage(db)
        for q in quiz.definitions:
            task=resources.definitions[q];actor=TaskActor(1111,1,123,100,1010109)
            state=TaskSnapshot(1,active=frozenset((q,)))
            evidence=TaskEvidence(q,1,123,'npc_quiz_correct_answer','offline-quiz',
                map_id=task['target']['map_id'],npc_id=task['target']['npc_id'])
            plan=TaskDomain(resources).plan(actor,state,'complete',q,evidence=evidence)
            assert plan.next_ids==task['next_ids'] and dict(plan.reward_scalars)==dict(task['display_rewards'])
            assert plan.completion_finish_dialogue==bool(task['dialogue']['finish'])
            refuse(lambda:TaskDomain(resources).plan(actor,state,'complete',q,evidence=replace(evidence,reference_id=1)))
            if q in (229103,229110,229112):
                decision=plan_task_chain(actor,plan.after,q,resources)
                assert decision.status=='pending' and decision.reason=='branch_selection_unconfirmed'
        q=230407;role_id=accounts.create_role(1111,'原NPC答题',11,1010109)['id'];epoch=accounts.acquire_lease(1111,role_id)
        inv=Inventory(accounts,1111,role_id,config,epoch=epoch,currency_rules=cash)
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');initialize_wallet(db,1111,role_id,epoch,(31,0,0,0),'explicit_migration',cash)
            for action in ('offer','accept'):
                actor,state=load_task_state(db,1111,role_id,epoch)
                apply_task_plan(db,actor,TaskDomain(resources).plan(actor,state,action,q),action)
            actor,state=load_task_state(db,1111,role_id,epoch)
        placements=load_placements()[1007];npc=next(p for p in placements if p.npc_id==10215)
        address=MapAddress(1007,1,0);location=Location(role_id,epoch,address,1,npc.x,npc.y)
        scene=NpcScene(address,placements,maps(),interaction_radius=32,binding_capacity=1);scene.bind(501,npc.placement_id)
        proof=scene.interact(struct.pack('>Q',501),location,location,request_id='original-quiz-npc',deadline_ms=1000,now_ms=1)
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            opening=open_task_quiz_transaction(db,1111,role_id,epoch,resources,quiz,inv,q,proof,location,generation=1,now_ms=2,deadline_ms=1000)
        assert decode_scenario_state(opening.messages[0][1])==(q,3)
        local=TaskConversation(resources,role_id,epoch);local.ticket=opening.permit.ticket
        for kind in (C_COMMIT_SCENARIO_QUEST,C_QUEST_DIALOG_END):
            refuse(lambda:local.plan_finish(actor,state,TaskIntent(kind,q,501,0),location,now_ms=3))
        answer=decode_task_quiz_answer(struct.pack('>iQi',q,501,0))
        def finish(db,command=answer,permit=opening.permit,current=location,inventory=inv,**changes):
            args=dict(generation=1,now_ms=3,currency_rules=cash);args.update(changes)
            return answer_task_quiz_transaction(db,1111,role_id,epoch,resources,quiz,inventory,command,permit,current,'original-answer',**args)
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');before=tuple(db.iterdump())
            wrong=finish(db,replace(answer,answer_code=1));assert wrong.outcome=='incorrect' and not wrong.messages
            assert tuple(db.iterdump())==before and q in load_task_state(db,1111,role_id,epoch)[1].active
            refuse(lambda:finish(db,replace(answer,answer_code=4)))
            refuse(lambda:finish(db,permit=None))
            refuse(lambda:finish(db,replace(answer,npc_key=502)))
            refuse(lambda:finish(db,current=replace(location,version=2)))
            refuse(lambda:finish(db,generation=2))
            refuse(lambda:finish(db,now_ms=1000))
        # Owner discards its wrong-answer permit and reopens at a fresh visit.
        proof=scene.interact(struct.pack('>Q',501),location,location,request_id='quiz-retry-visit',deadline_ms=1000,now_ms=4)
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            opening=open_task_quiz_transaction(db,1111,role_id,epoch,resources,quiz,inv,q,proof,location,generation=1,now_ms=5,deadline_ms=1000)
        broken=BrokenRefresh(accounts,1111,role_id,config,epoch=epoch,currency_rules=cash)
        try:
            with closing(accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE');finish(db,permit=opening.permit,inventory=broken,now_ms=6)
            raise AssertionError('Late quiz encoding failure committed')
        except ValueError as error:assert str(error)=='controlled quiz reply failure'
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            assert q in load_task_state(db,1111,role_id,epoch)[1].active
            assert not db.execute('SELECT 1 FROM task_effects WHERE role_id=?',(role_id,)).fetchone()
            result=finish(db,permit=opening.permit,now_ms=6)
            assert result.outcome=='correct' and result.completion.rewards.experience_awarded==0
            assert result.completion.started_tasks==(230408,)
            effect=json.loads(db.execute('SELECT payload FROM task_effects WHERE role_id=? AND task_id=?',(role_id,q)).fetchone()[0])
            assert effect['quiz_answer']['answer_code']==0 and 'native_finish_dialogue' in effect
        new_epoch=accounts.acquire_lease(1111,role_id)
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');refuse(lambda:finish(db))
            credit_experience(db,1111,role_id,7)
            replay=answer_task_quiz_transaction(db,1111,role_id,new_epoch,resources,quiz,inv,answer,None,None,'quiz-paid-ack',
                generation=2,now_ms=1001,currency_rules=cash)
            assert replay.replayed and replay.completion.rewards.experience_balance==7
            assert not any(k==S_REFRESH_SCENARIO_QUEST_STATE for k,_ in replay.messages)
        report=dict(fixed_npc_quiz_tasks=5,dynamic_or_round_excluded=7,passed=[
            'original CAnswerQuestion16-byte answer layout and full64-bit NPC key; task1001..499999 and code0..5 constraints',
            'five original fixed questions preserve source codes/text;230407 correct label2 is code0; seven dynamic/round questions excluded',
            'ordinary CCommit/DialogEnd cannot complete quiz; realNPC10215 ready3, exact answer key/range/position/generation/deadline required',
            'wrong answer leaves active without writes; fresh visit can retry; three ambiguous original branches remain pending',
            'late bag error rolls back completion/rewards/next/evidence; correct retry commits original zero reward and unique230408 once',
            'paid current-lease replay reads later7XP with no repeated state1/Finish; old lease refuses'],
            scope='five pure original questions and actual230407/NpcScene10215 caller transaction in disposable DB; trusted offer/position fixtures',
            wrong_answer_behavior='designed retain-active and require fresh visit; original event failure behavior unconfirmed',
            shared_runtime_tested=False,client_tested=False)
    (OUT/'evidence/task-quiz-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':main()
