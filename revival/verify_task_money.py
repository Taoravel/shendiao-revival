"""Original type11 contracts and three actual static NPC domain transactions.

The explicit test payment recipe extends only the disposable CurrencyRules
snapshot. Production wallet permissions/policy are deliberately not modified.
"""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from types import MappingProxyType
import json
import struct
import tempfile
from accounts import AccountStore
from inventory import Inventory
from task_domain import TaskDomain,TaskActor,TaskSnapshot,TaskEvidence
from task_persistence import load_task_state,apply_task_plan
from task_conversation import TaskConversation
from task_money_protocol import TaskMoneySubmission,encode_task_money_submission,decode_task_money_submission
from task_money import load_task_money_resources,TaskMoneyPaymentRule,open_task_money_transaction,submit_task_money_transaction
from task_session import TaskIntent,decode_task_item_intent,decode_task_money_intent
from task_item_protocol import C_SUBMIT_2_NPC,NpcItemSubmission,encode_npc_item_submission
from task_protocol import C_COMMIT_SCENARIO_QUEST,C_QUEST_DIALOG_END,S_REFRESH_SCENARIO_QUEST_STATE
from task_chains import plan_task_chain
from world_owner import MapAddress,Location
from world_npcs import load_placements,NpcScene
from world_catalog import maps
from currency import read_wallet,initialize_wallet,CurrencyChange,apply_currency
from role_growth import initialize_growth
from role_attribute_storage import initialize_attribute_baseline
from role_equipment import EquipmentAttributeBasis,resource_caps_from_projection
from role_equipment_storage import initialize_equipment_attribute_basis,current_equipment_totals
from role_resource_plan import load_resource_rules
from role_resource_storage import migrate_role_resources,read_role_resources
from inspect_client import OUT
import runtime_storage


def refuse(call):
    try:call()
    except ValueError:return
    raise AssertionError('Unapproved or mismatched money task accepted')


class BrokenBag(Inventory):
    def equipment_bag_messages(self,db,epoch):
        raise ValueError('controlled late task money reply failure')


def main():
    with tempfile.TemporaryDirectory(prefix='task-money-') as directory:
        store=AccountStore(Path(directory)/'state.sqlite3');runtime_storage.prepare(store)
        resources=store.task_resources;money=load_task_money_resources(resources)
        expected={205707:500000,230307:2000000,233307:100000,233309:50000,233906:1}
        assert {q:d.amount for q,d in money.definitions.items()}==expected and not money.exclusions
        # This proposed recipe is explicit test input, not an edit or default
        # approval of the shared production currency policy.
        production_cash=store.currency_rules
        purposes=dict(production_cash.spend_purposes)
        purposes['cash']=purposes['cash']|{'task_money_submission'}
        cash=replace(production_cash,spend_purposes=MappingProxyType(purposes))
        payment=TaskMoneyPaymentRule('test-explicit-task-money-recipe.1','cash','task_money_submission')
        rules=load_resource_rules();gear=store.equipment_attribute_rules
        for q,amount in expected.items():
            task=resources.definitions[q]
            actor=TaskActor(1111,1,1,1,1010109);state=TaskSnapshot(1,active=frozenset((q,)))
            evidence=TaskEvidence(q,1,1,'npc_money_submitted','pure-original-money',task['target']['map_id'],task['target']['npc_id'],amount)
            plan=TaskDomain(resources).plan(actor,state,'complete',q,evidence=evidence)
            assert plan.completion_finish_dialogue and dict(plan.reward_scalars)==dict(task['display_rewards'])
            assert plan.next_ids==tuple(task['next_ids'])
            refuse(lambda:TaskDomain(resources).plan(actor,state,'complete',q,evidence=replace(evidence,reference_id=amount+1)))
            command=TaskMoneySubmission(q,0x112233445566778,amount)
            body=encode_task_money_submission(command)
            assert len(body)==25 and body==struct.pack('>iQiBii',q,command.npc_key,3,1,amount,amount)
            assert decode_task_money_submission(body)==command and decode_task_money_intent(C_SUBMIT_2_NPC,body)==command
            refuse(lambda:decode_task_item_intent(C_SUBMIT_2_NPC,body))
            refuse(lambda:decode_task_money_submission(body[:-1]))
            refuse(lambda:decode_task_money_submission(encode_npc_item_submission(
                NpcItemSubmission(q,command.npc_key,1,((amount,amount),)))))
            refuse(lambda:decode_task_money_submission(encode_npc_item_submission(
                NpcItemSubmission(q,command.npc_key,3,()))))
            refuse(lambda:decode_task_money_submission(encode_npc_item_submission(
                NpcItemSubmission(q,command.npc_key,3,((amount,amount+1),)))))
        # Original unambiguous predecessor edges may now activate only this
        # supported objective. Enrollment and activity qualification stay owned
        # by their trusted trigger; no test activates the holiday NPCs.
        for source,q in ((205706,205707),(230306,230307),(233905,233906)):
            decision=plan_task_chain(actor,TaskSnapshot(1,completed=frozenset((source,))),source,resources)
            assert (decision.status,decision.target_id,decision.reason)==('activate',q,'unique_supported_money_submission')
        placements=load_placements();completed=[]
        for q in (205707,230307,233906):
            amount=expected[q];task=resources.definitions[q]
            role_id=store.create_role(1111,f'交钱{q}',11,1010109)['id'];epoch=store.acquire_lease(1111,role_id)
            inv=Inventory(store.leased(1111,role_id,epoch),1111,role_id)
            address=MapAddress(task['target']['map_id'],1,0)
            npc=next(p for p in placements[address.map_id] if p.npc_id==task['target']['npc_id'])
            scene=NpcScene(address,placements[address.map_id],maps(),interaction_radius=32,binding_capacity=1)
            key=0x100000000+q;scene.bind(key,npc.placement_id)
            location=Location(role_id,epoch,address,1,npc.x,npc.y)
            proof=scene.interact(struct.pack('>Q',key),location,location,request_id=f'money-proof:{q}',deadline_ms=1000,now_ms=1)
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                initialize_wallet(db,1111,role_id,epoch,(amount-1 if q==205707 else amount+9,7000000,0,0),'explicit_migration',cash)
                for action in ('offer','accept'):
                    actor,state=load_task_state(db,1111,role_id,epoch)
                    apply_task_plan(db,actor,TaskDomain(resources).plan(actor,state,action,q),f'money:{q}:{action}')
                if q==230307:
                    growth=initialize_growth(db,1111,role_id,epoch,store.growth_rules,expected_level=1,free_points=0)
                    p=store.attribute_rules.initial_profile
                    legacy=initialize_attribute_baseline(db,1111,role_id,epoch,p.baseline(role_id),growth,
                        store.attribute_rules,replace(p.vitals(role_id),hp=70,mp=40))
                    initialize_equipment_attribute_basis(db,1111,role_id,epoch,
                        EquipmentAttributeBasis(role_id,9,0,gear.revision,0,'explicit-money-resource-fixture'),gear)
                    caps=resource_caps_from_projection(current_equipment_totals(db,1111,role_id,epoch,inv.immutable_snapshot_transaction(db),gear))
                    migrate_role_resources(db,1111,role_id,epoch,legacy.vitals,caps,origin='explicit_migration',
                        migration_id='known-money-profile',rules=rules,equipment_rules=gear)
                refuse(lambda:open_task_money_transaction(db,1111,role_id,epoch,resources,money,inv,q,proof,location,
                    generation=1,now_ms=2,deadline_ms=1000,currency_rules=production_cash,payment_rule=payment))
                opening=open_task_money_transaction(db,1111,role_id,epoch,resources,money,inv,q,proof,location,
                    generation=1,now_ms=2,deadline_ms=1000,currency_rules=cash,payment_rule=payment)
                local=TaskConversation(resources,role_id,epoch);local.ticket=opening.permit.ticket
                actor,state=load_task_state(db,1111,role_id,epoch)
                for kind in (C_COMMIT_SCENARIO_QUEST,C_QUEST_DIALOG_END):
                    refuse(lambda:local.plan_finish(actor,state,TaskIntent(kind,q,key,0),location,now_ms=3))
                generic=local.menu_messages(actor,state,proof,location,now_ms=3,deadline_ms=1000)
                assert local.ticket is None and not any(kind==S_REFRESH_SCENARIO_QUEST_STATE for kind,_ in generic)
            command=TaskMoneySubmission(q,key,amount)
            def submit(db,inventory=inv,**overrides):
                kwargs=dict(generation=1,now_ms=3,currency_rules=cash,payment_rule=payment,
                    growth_rules=store.growth_rules,attribute_rules=store.attribute_rules,pet_experience_rules=store.task_pet_experience_rules,
                    resource_rules=rules,equipment_rules=gear)
                kwargs.update(overrides)
                return submit_task_money_transaction(db,1111,role_id,epoch,resources,money,inventory,command,
                    opening.permit,location,f'money-submit:{q}',**kwargs)
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE');changes=db.total_changes
                refuse(lambda:submit(db,generation=2));refuse(lambda:submit(db,now_ms=1000))
                refuse(lambda:submit_task_money_transaction(db,1111,role_id,epoch,resources,money,inv,
                    replace(command,npc_key=key+1),opening.permit,location,'wrong-npc',generation=1,now_ms=3,
                    currency_rules=cash,payment_rule=payment))
                refuse(lambda:submit_task_money_transaction(db,1111,role_id,epoch,resources,money,inv,
                    command,opening.permit,replace(location,version=2),'moved',generation=1,now_ms=3,
                    currency_rules=cash,payment_rule=payment))
                refuse(lambda:submit_task_money_transaction(db,1111,role_id,epoch,resources,money,inv,
                    command,replace(opening.permit,task_revision=opening.permit.task_revision+1),location,'stale-task',generation=1,now_ms=3,
                    currency_rules=cash,payment_rule=payment))
                refuse(lambda:submit_task_money_transaction(db,1111,role_id,epoch,resources,money,inv,
                    replace(command,amount=amount+1),opening.permit,location,'wrong-amount',generation=1,now_ms=3,
                    currency_rules=cash,payment_rule=payment))
                assert db.total_changes==changes
            if q==205707:
                with closing(store.connect()) as db:
                    before=tuple(db.iterdump())
                try:
                    with closing(store.connect()) as db,db:
                        db.execute('BEGIN IMMEDIATE');submit(db)
                    raise AssertionError('Insufficient cash accepted bound silver')
                except ValueError as error:
                    assert 'Insufficient' in str(error)
                with closing(store.connect()) as db,db:
                    assert tuple(db.iterdump())==before
                    db.execute('BEGIN IMMEDIATE')
                    apply_currency(db,1111,role_id,epoch,CurrencyChange('known-fixture-cash','test_fixture','explicit-known-cash',(('cash',10),)),cash)
            with closing(store.connect()) as db:
                before=tuple(db.iterdump())
            try:
                with closing(store.connect()) as db,db:
                    db.execute('BEGIN IMMEDIATE')
                    submit(db,BrokenBag(store.leased(1111,role_id,epoch),1111,role_id))
                raise AssertionError('Controlled late money failure did not fire')
            except ValueError as error:
                assert 'controlled late task money' in str(error)
            with closing(store.connect()) as db,db:
                assert tuple(db.iterdump())==before
                db.execute('BEGIN IMMEDIATE');result=submit(db)
                wallet=read_wallet(db,1111,role_id,epoch,cash)
                assert tuple(row.balance for row in wallet)==(9,7000000,0,0)
                items=inv.immutable_snapshot_transaction(db).items
                assert tuple((x.template_id,x.quantity,x.binding) for x in items)==tuple(
                    (x['id'],x['count'],x['bind']) for x in task['display_items'])
                assert result.completion.rewards.experience_awarded==0
                effect=json.loads(db.execute('SELECT payload FROM task_effects WHERE role_id=? AND task_id=?',(role_id,q)).fetchone()[0])
                assert effect['native_finish_dialogue']['status']=='delegated_to_original_client'
                if q==230307:
                    current=read_role_resources(db,1111,role_id,epoch,rules)
                    assert (current.hp,current.mp,current.version)==(70,40,0)
                    assert current.caps.source.inventory_revision==inv.immutable_snapshot_transaction(db).inventory_revision
                apply_currency(db,1111,role_id,epoch,CurrencyChange('later-known-cash','test_fixture','later-current-balance',(('cash',7),)),cash)
            old_epoch=epoch;epoch=store.acquire_lease(1111,role_id)
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                replay=submit_task_money_transaction(db,1111,role_id,epoch,resources,money,inv,command,None,None,'current-paid-ack',
                    generation=2,now_ms=1001,currency_rules=cash,payment_rule=payment,growth_rules=store.growth_rules,
                    attribute_rules=store.attribute_rules,pet_experience_rules=store.task_pet_experience_rules,
                    resource_rules=rules,equipment_rules=gear)
                assert replay.replayed and replay.completion.rewards.wallet[0].balance==16
                assert not any(kind==S_REFRESH_SCENARIO_QUEST_STATE for kind,_ in replay.messages)
                changes=db.total_changes
                refuse(lambda:submit_task_money_transaction(db,1111,role_id,epoch,resources,money,inv,
                    replace(command,npc_key=key+1),None,None,'changed-paid-npc',generation=2,now_ms=1001,
                    currency_rules=cash,payment_rule=payment))
                refuse(lambda:submit_task_money_transaction(db,1111,role_id,epoch,resources,money,inv,
                    command,None,None,'changed-paid-policy',generation=2,now_ms=1001,currency_rules=cash,
                    payment_rule=replace(payment,revision='test-another-recipe')))
                assert db.total_changes==changes
                refuse(lambda:submit_task_money_transaction(db,1111,role_id,old_epoch,resources,money,inv,command,None,None,'old-lease',
                    generation=1,now_ms=1001,currency_rules=cash,payment_rule=payment))
                assert read_wallet(db,1111,role_id,epoch,cash)[0].balance==16
            completed.append(q)
        report=dict(original_static_money_tasks=5,actual_static_npc_transactions=completed,passed=[
            'original mode3 one equal amount pair,25-byte body,full64-bit NPC key; malformed/type1/unequal amount cannot cross item route',
            'all five original amounts/rewards/Finish/next retained; three unique original predecessor edges activate only supported money objective',
            'currency-owner recipe gate, exact current permit/task/generation/deadline and original amount; ordinary CCommit/DialogEnd refuse',
            'insufficient cash cannot spend bound silver; late reply failure rolls back full DB; exact retry debits once and grants original bound50397/50417',
            'migrated resource profile preserves70/40/version0 and follows actual reward inventory source',
            'new-lease paid acknowledgement reads later16cash without another debit or repeated Finish/state1; old lease refuses'],
            payment_policy_scope='explicit disposable CurrencyRules extension and test recipe only; production task_money_submission expense permission not enabled',
            holiday_npc_scope='233307/233309 pure original plans only; NPC13874 absent from static1011 placements, no activity enrollment or spawn',
            scope='trusted task offer/known wallet/position fixtures and actual public NpcScene/Inventory/currency/resource Interfaces in disposable DB',
            shared_runtime_tested=False,client_tested=False,live_server_changed=False,battle_executed=False)
    (OUT/'evidence/task-money-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':main()
