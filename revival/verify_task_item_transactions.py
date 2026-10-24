"""One ordinary original submission through actual public Inventory Interfaces."""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
import tempfile
import json
import struct
from accounts import AccountStore
from inventory import Inventory,AssetChange
from tasks import prepare_task_store
from task_domain import TaskDomain
from task_persistence import load_task_state,apply_task_plan
from task_rewards import prepare_reward_storage
from task_pet_experience import load_task_pet_experience_rules
from task_item_protocol import NpcItemSubmission
from task_item_transactions import open_item_task_transaction,submit_item_task_transaction
from world_owner import Location,MapAddress
from world_npcs import NpcScene,load_placements
from world_catalog import maps
from currency import prepare_wallet_storage,initialize_wallet,load_currency_rules
from progression import read_experience
from inspect_client import OUT


class BrokenRefresh(Inventory):
    def equipment_bag_messages(self,db,epoch):
        raise ValueError('controlled native reply failure')


def refuse(call):
    try:call()
    except ValueError:return
    raise AssertionError('Invalid selected-item transaction accepted')


def main():
    with tempfile.TemporaryDirectory() as directory:
        accounts=AccountStore(Path(directory)/'items.sqlite3')
        resources=prepare_task_store(accounts)
        config=Inventory.prepare(accounts)
        cash=load_currency_rules()
        pet=load_task_pet_experience_rules()
        role=accounts.create_role(1111,'原交物真实接口',11,1010109)
        role_id=role['id']
        epoch=accounts.acquire_lease(1111,role_id)
        with closing(accounts.connect()) as db:
            prepare_reward_storage(db);prepare_wallet_storage(db)
        inv=Inventory(accounts,1111,role_id,config,epoch=epoch,currency_rules=cash)
        address=MapAddress(1006,1,0)
        npc=next(p for p in load_placements()[1006] if p.npc_id==10527)
        scene=NpcScene(address,load_placements()[1006],maps(),interaction_radius=32,binding_capacity=2)
        scene.bind(201,npc.placement_id)
        location=Location(role_id,epoch,address,1,npc.x,npc.y)
        proof=scene.interact(struct.pack('>Q',201),location,location,request_id='item-proof',deadline_ms=1000,now_ms=1)
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            initialize_wallet(db,1111,role_id,epoch,(31,0,0,0),'explicit_migration',cash)
            for action in ('offer','accept'):
                actor,state=load_task_state(db,1111,role_id,epoch)
                apply_task_plan(db,actor,TaskDomain(resources).plan(actor,state,action,101101),action)
            inv.apply_settlement(db,AssetChange('original-task-items',grants=((50062,1,1),)))
            key=inv.immutable_snapshot_transaction(db,epoch=epoch).items[0].id
            opening=open_item_task_transaction(db,1111,role_id,epoch,resources,inv,101101,proof,location,
                generation=1,now_ms=2,deadline_ms=1000)
        command=NpcItemSubmission(101101,201,1,((key,1),))
        def submit(db,inventory=inv,**changes):
            options=dict(generation=1,now_ms=3,currency_rules=cash,pet_experience_rules=pet);options.update(changes)
            return submit_item_task_transaction(db,1111,role_id,epoch,resources,inventory,command,opening.permit,
                location,'submit-original',**options)
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            refuse(lambda:submit(db,generation=2))
            refuse(lambda:submit(db,now_ms=1000))
        try:
            broken=BrokenRefresh(accounts,1111,role_id,config,epoch=epoch,currency_rules=cash)
            with closing(accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                submit(db,broken)
            raise AssertionError('Controlled reply failure committed')
        except ValueError as error:
            assert str(error)=='controlled native reply failure'
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            assert inv.immutable_snapshot_transaction(db,epoch=epoch).items[0].id==key
            assert read_experience(db,1111,role_id).experience==0
            _,state=load_task_state(db,1111,role_id,epoch)
            assert 101101 in state.active
            result=submit(db)
            assert not result.replayed and result.completion.consumed_items==((key,1),)
            assert not inv.immutable_snapshot_transaction(db,epoch=epoch).items
            assert read_experience(db,1111,role_id).experience==400
        new_epoch=accounts.acquire_lease(1111,role_id)
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            replay=submit_item_task_transaction(db,1111,role_id,new_epoch,resources,inv,command,None,None,'reconnect-ack',
                generation=2,now_ms=5,currency_rules=cash,pet_experience_rules=pet)
            assert replay.replayed and replay.completion.rewards.experience_balance==400
            refuse(lambda:submit_item_task_transaction(db,1111,role_id,new_epoch,resources,inv,
                replace(command,units=((key,2),)),None,None,'bad-ack',generation=2,now_ms=5,currency_rules=cash,pet_experience_rules=pet))
        report=dict(passed=['actual public same-transaction inventory reader and debit/reward/native bag refresh',
            'frozen permit only across owners; wrong generation/expired refuses',
            'late native refresh failure rolls back item/task/XP/receipts; retry consumes selected bound50062 once and grants original400XP',
            'new lease acknowledges identical paid manifest without old ticket/location; changed manifest rejects'],
            test_scope='temporary SQLite, actual original101101/NPC10527/map1006; actual AccountStore.acquire_lease identities',
            shared_runtime_tested=False,client_tested=False)
    (OUT/'evidence/task-item-transactions-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':main()
