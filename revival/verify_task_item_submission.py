"""Offline native item-submit body and task/debit/reward transaction checks."""
from contextlib import closing
from dataclasses import replace
import json
from pathlib import Path
import struct
import tempfile
from accounts import AccountStore
from inventory import Inventory, ItemState
from inspect_client import OUT
from tasks import prepare_task_store
from task_domain import TaskDomain, supports_item_submission
from task_conversation import TaskConversation,TaskConversationTicket
from task_item_submission import plan_item_objective
from task_persistence import load_task_state,apply_task_plan
from task_session import TaskIntent
from task_protocol import C_COMMIT_SCENARIO_QUEST,decode_accept_scenario_quest,decode_scenario_state
from task_item_protocol import (NpcItemSubmission,encode_npc_item_submission,decode_npc_item_submission,
                                encode_npc_submission_prompt)
from task_rewards import prepare_reward_storage
from task_pet_experience import load_task_pet_experience_rules
from task_workflow import complete_task_transaction,replay_item_completion_transaction
from progression import read_experience
from world_owner import MapAddress,Location
from world_npcs import NpcScene,load_placements
from world_catalog import maps


def main():
    command=NpcItemSubmission(101101,0x1122334455667788,1,((12345,3),))
    assert encode_npc_item_submission(command).hex()=='00018aed112233445566778800000001010000303900000003'
    assert decode_npc_item_submission(encode_npc_item_submission(command))==command
    for body in (b'',encode_npc_item_submission(command)+b'\0',
                 struct.pack('>iQi',101101,1,1)+b'\x80',
                 struct.pack('>iQi',101101,1,1)+b'\x82\0'):
        try:
            decode_npc_item_submission(body)
            raise AssertionError('Malformed submission accepted')
        except ValueError:
            pass
    checks=['native CSubmit2Npc body matches original x86 marshal; bounded malformed/trailing/truncated vectors rejected']
    pet_rules=load_task_pet_experience_rules()
    with tempfile.TemporaryDirectory() as directory:
        accounts=AccountStore(Path(directory)/'task-items.sqlite3')
        resources=prepare_task_store(accounts)
        config=Inventory.prepare(accounts)
        role=accounts.create_role(1111,'原交物任务',11,1010109)
        epoch=accounts.acquire_lease(1111,role['id'])
        inv=Inventory(accounts,1111,role['id'],config)
        with closing(accounts.connect()) as db:
            prepare_reward_storage(db)
        address=MapAddress(1006,1,0)
        placements=load_placements()[1006]
        npc=next(x for x in placements if x.npc_id==10527)
        scene=NpcScene(address,placements,maps(),interaction_radius=32,binding_capacity=4)
        scene.bind(201,npc.placement_id)
        current=Location(role['id'],epoch,address,1,npc.x,npc.y)
        proof=scene.interact(struct.pack('>Q',201),current,current,request_id='item-npc-proof',deadline_ms=1000,now_ms=1)
        conversation=TaskConversation(resources,role['id'],epoch)

        # This temporary-DB Adapter supplies the same-transaction read required
        # from the inventory owner in production; no task code reads asset SQL.
        def rows(db):
            return tuple(ItemState(*x) for x in db.execute(
                'SELECT id,role_id,template_id,quantity,slot,equipment_slot,binding,quality FROM inventory_items WHERE role_id=?',
                (role['id'],)))

        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            actor,state=load_task_state(db,1111,role['id'],epoch)
            apply_task_plan(db,actor,TaskDomain(resources).plan(actor,state,'offer',101101),'trusted-offer')
            actor,state=load_task_state(db,1111,role['id'],epoch)
            intent=TaskIntent(C_COMMIT_SCENARIO_QUEST,101101,201,0)
            accept=conversation.plan_accept(actor,state,intent,proof,current,now_ms=2,deadline_ms=1000)
            apply_task_plan(db,actor,accept,'accept')
            actor,state=load_task_state(db,1111,role['id'],epoch)
            initial=conversation.menu_messages(actor,state,proof,current,now_ms=3,deadline_ms=1000,item_states=rows(db))
            assert decode_scenario_state(initial[0][1])==(101101,2) and conversation.ticket is None
            restored=conversation.resume_messages(actor,state)
            bean=decode_accept_scenario_quest(restored[0][1])
            assert (bean.quest_id,bean.state,bean.value1,bean.value2)==(101101,2,0,0)
        inv.grant_item(50062,1,binding=1)
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            actor,state=load_task_state(db,1111,role['id'],epoch)
            items=rows(db)
            key=items[0].id
            ready=conversation.menu_messages(actor,state,proof,current,now_ms=4,deadline_ms=1000,item_states=items)
            assert decode_scenario_state(ready[0][1])==(101101,3)
            assert conversation.item_prompt_messages()==((0xc233f,encode_npc_submission_prompt(101101,201,1,(),0)),)
            valid=NpcItemSubmission(101101,201,1,((key,1),))
            for bad in (replace(valid,submit_type=0),replace(valid,npc_key=202),replace(valid,units=()),
                        replace(valid,units=((key,2),)),replace(valid,units=((key,1),(key,1)))):
                try:
                    conversation.plan_item_submission(actor,state,bad,current,items,now_ms=5)
                    raise AssertionError('Invalid client selection accepted')
                except ValueError:
                    pass
            for wrong_items in ((replace(items[0],template_id=50067),),
                                (replace(items[0],role_id=role['id']+1),),
                                (replace(items[0],equipment_slot=0),),()):
                try:
                    conversation.plan_item_submission(actor,state,valid,current,wrong_items,now_ms=5)
                    raise AssertionError('Wrong inventory evidence accepted')
                except ValueError:
                    pass
            try:
                conversation.plan_item_submission(actor,state,valid,replace(current,version=2),items,now_ms=5)
                raise AssertionError('Moved item ticket accepted')
            except ValueError:
                pass
            try:
                conversation.plan_finish(actor,state,intent,current,now_ms=5)
                raise AssertionError('Plain CCommit completed an item quest')
            except ValueError:
                pass
            plan=conversation.plan_item_submission(actor,state,valid,current,items,now_ms=5)
            assert plan.objective_debits==((key,1),)
            result=complete_task_transaction(db,actor,plan,'submit',resources,inv,pet_experience_rules=pet_rules)
            assert result.consumed_items==((key,1),) and result.rewards.experience_balance==400
            assert not rows(db)
            effect=json.loads(db.execute('SELECT payload FROM task_effects WHERE role_id=? AND task_id=101101',(role['id'],)).fetchone()[0])
            assert effect['objective_debits']==[[key,1]]
        conversation.acknowledge(plan)
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            again=complete_task_transaction(db,actor,plan,'submit',resources,inv,pet_experience_rules=pet_rules)
            assert again.rewards.experience_balance==400 and not rows(db)
            assert read_experience(db,1111,role['id']).experience==400
        epoch=accounts.acquire_lease(1111,role['id'])
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            reconnect,_=load_task_state(db,1111,role['id'],epoch)
            replay=replay_item_completion_transaction(db,reconnect,valid,resources,inv,pet_experience_rules=pet_rules)
            assert replay.rewards.experience_balance==400 and not rows(db)
            try:
                replay_item_completion_transaction(db,reconnect,replace(valid,units=((key,2),)),resources,inv,pet_experience_rules=pet_rules)
                raise AssertionError('Changed completed selection acknowledged')
            except ValueError:
                pass
        checks.append('original101101 NPC10527/map1006: accept, ongoing without item, ready/selector with bound50062, consume once+400XP; reconnect restores bean and acknowledges exact paid selection without another debit')
        checks.append('empty/excess/duplicate/wrong NPC/type/role/template/equipped/moved selections and plain CCommit rejected')

        # Late failure after task/debit/XP must restore the selected item too.
        rollback_role=accounts.create_role(1111,'交物回滚',11,1010109)
        rollback_epoch=accounts.acquire_lease(1111,rollback_role['id'])
        rollback_inv=Inventory(accounts,1111,rollback_role['id'],config)
        rollback_inv.grant_item(50062,1,binding=1)
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            for action in ('offer','accept'):
                a,s=load_task_state(db,1111,rollback_role['id'],rollback_epoch)
                apply_task_plan(db,a,TaskDomain(resources).plan(a,s,action,101101),action)
            a,s=load_task_state(db,1111,rollback_role['id'],rollback_epoch)
            item=ItemState(*db.execute('SELECT id,role_id,template_id,quantity,slot,equipment_slot,binding,quality FROM inventory_items WHERE role_id=?',
                                      (a.role_id,)).fetchone())
            # Authoritative trusted evidence mirrors the already checked selector;
            # this fault test specifically crosses the common completion Interface.
            from task_domain import TaskEvidence
            evidence=TaskEvidence(101101,a.role_id,a.login_epoch,'npc_items_submitted','rollback-proof',1006,10527,50062,((item.id,1),))
            failed_plan=TaskDomain(resources).plan(a,s,'complete',101101,evidence=evidence)
        class FailingInventory(Inventory):
            def apply_settlement(self, db, change):
                receipt=super().apply_settlement(db,change)
                if change.settlement_id.endswith(':items'):
                    raise RuntimeError('controlled reward-item failure after objective debit')
                return receipt
        failing=FailingInventory(accounts,1111,a.role_id,config)
        try:
            with closing(accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                complete_task_transaction(db,a,failed_plan,'submit',resources,failing,pet_experience_rules=pet_rules)
            raise AssertionError('Partial objective debit committed')
        except RuntimeError:
            pass
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN')
            assert db.execute('SELECT quantity,binding FROM inventory_items WHERE id=?',(item.id,)).fetchone()==(1,1)
            assert db.execute('SELECT state FROM task_journal WHERE role_id=?',(a.role_id,)).fetchone()[0]=='active'
            assert read_experience(db,1111,a.role_id).experience==0
            assert db.execute('SELECT COUNT(*) FROM task_effects WHERE role_id=?',(a.role_id,)).fetchone()[0]==0
        checks.append('failure after objective debit and XP restores bound item, task, XP and receipts together')
        # Original102012 requires five 50014, not a hardcoded single item.
        # This controlled owner ticket isolates cross-stack quantity handling.
        quantity_role=accounts.create_role(1111,'交物原数量',11,1010109)
        quantity_epoch=accounts.acquire_lease(1111,quantity_role['id'])
        quantity_inv=Inventory(accounts,1111,quantity_role['id'],config)
        quantity_inv.grant_item(50014,6,binding=1)
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            for action in ('offer','accept'):
                qa,qs=load_task_state(db,1111,quantity_role['id'],quantity_epoch)
                apply_task_plan(db,qa,TaskDomain(resources).plan(qa,qs,action,102012),action)
            qa,qs=load_task_state(db,1111,quantity_role['id'],quantity_epoch)
            qi=tuple(ItemState(*x) for x in db.execute(
                'SELECT id,role_id,template_id,quantity,slot,equipment_slot,binding,quality FROM inventory_items WHERE role_id=? ORDER BY slot',
                (qa.role_id,)))
            assert tuple(x.quantity for x in qi)==(5,1)
            qaddress=MapAddress(1014,1,0)
            qlocation=Location(qa.role_id,qa.login_epoch,qaddress,1,0,0)
            qticket=TaskConversationTicket(102012,qa.role_id,qa.login_epoch,'controlled-quantity-proof',
                                           qaddress,1,10350,301,1000)
            selected=NpcItemSubmission(102012,301,1,((qi[0].id,4),(qi[1].id,1)))
            qp=plan_item_objective(qa,qs,selected,qticket,qlocation,qi,resources,now_ms=2)
            complete_task_transaction(db,qa,qp,'submit-five',resources,quantity_inv,pet_experience_rules=pet_rules)
            assert db.execute('SELECT quantity,binding FROM inventory_items WHERE id=?',(qi[0].id,)).fetchone()==(1,1)
            assert db.execute('SELECT 1 FROM inventory_items WHERE id=?',(qi[1].id,)).fetchone() is None
        checks.append('original102012 requires five50014: selected4+1 across two bound stacks; unselected remainder1 preserved')
        supported=tuple(q for q,t in resources.definitions.items() if supports_item_submission(t))
        assert not any(q in supported for q in (221112,221117,232003,812001))
        report=dict(passed=checks,supported_static_item_objectives=len(supported),
                    target12_total=236,unimplemented_special_or_extra_conditions=236-len(supported),
                    exact_quantity_policy='designed',native_wire='client_verified',
                    inventory_transaction_reader='required production integration; temporary-DB adapter checked',
                    live_runtime_tested=False,live_client_tested=False)
    (OUT/'evidence/task-item-submission-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':
    main()
