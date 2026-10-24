"""Original four-step talk sequence; stop before its unimplemented battle."""
from contextlib import closing
from pathlib import Path
import json
import struct
import tempfile
from accounts import AccountStore
from inventory import Inventory
from inspect_client import OUT
from tasks import prepare_task_store
from task_domain import TaskDomain
from task_persistence import load_task_state,apply_task_plan
from task_rewards import prepare_reward_storage
from task_conversation import TaskConversation
from task_session import decode_task_intent
from task_protocol import C_COMMIT_SCENARIO_QUEST,decode_accept_scenario_quest
from task_workflow import complete_task_transaction,completion_messages
from world_catalog import maps
from world_owner import MapAddress,Location
from world_npcs import NpcScene,load_placements


def main():
    with tempfile.TemporaryDirectory() as directory:
        accounts = AccountStore(Path(directory)/'chain.sqlite3')
        role = accounts.create_role(1111,'任务续接',11,1010109)
        resources = prepare_task_store(accounts)
        inv = Inventory(accounts,1111,role['id'],Inventory.prepare(accounts))
        epoch = accounts.acquire_lease(1111,role['id'])
        with closing(accounts.connect()) as db: prepare_reward_storage(db)
        domain = TaskDomain(resources)
        conversation = TaskConversation(resources,role['id'],epoch)
        address = MapAddress(1006,1,0)
        placements = load_placements()[1006]
        scene = NpcScene(address,placements,maps(),interaction_radius=32,binding_capacity=4)
        with closing(accounts.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            actor,state = load_task_state(db,1111,role['id'],epoch)
            apply_task_plan(db,actor,domain.plan(actor,state,'offer',100192),'initial-offer')
            actor,state = load_task_state(db,1111,role['id'],epoch)
            apply_task_plan(db,actor,domain.plan(actor,state,'accept',100192),'initial-accept')
        outcomes = []
        for version,ident in enumerate((100192,100193,100194,100195),1):
            definition = resources.definitions[ident]
            npc = next(p for p in placements if p.npc_id==definition['target']['npc_id'])
            scene.bind(100+version,npc.placement_id)
            location = Location(role['id'],epoch,address,version,npc.x,npc.y)
            proof = scene.interact(struct.pack('>Q',100+version),location,location,
                request_id=f'npc-{ident}',deadline_ms=1000,now_ms=1)
            with closing(accounts.connect()) as db, db:
                db.execute('BEGIN IMMEDIATE')
                actor,state = load_task_state(db,1111,role['id'],epoch)
                assert ident in state.active
                conversation.open(actor,state,ident,proof,location,now_ms=1,deadline_ms=1000)
                intent = decode_task_intent(C_COMMIT_SCENARIO_QUEST,struct.pack('>iQi',ident,100+version,0))
                plan = conversation.plan_finish(actor,state,intent,location,now_ms=2)
                result = complete_task_transaction(db,actor,plan,f'finish-{ident}',resources,inv)
            conversation.acknowledge(plan)
            outcomes.append((ident,result.started_tasks))
            if result.started_tasks:
                assert decode_accept_scenario_quest(completion_messages(result)[-1][1]).quest_id == result.started_tasks[0]
        assert outcomes==[(100192,(100193,)),(100193,(100194,)),(100194,(100195,)),(100195,())]
        with closing(accounts.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            _,state = load_task_state(db,1111,role['id'],epoch)
            assert state.completed==frozenset((100192,100193,100194,100195))
            assert 100113 not in state.active
            pending = json.loads(db.execute('SELECT payload FROM task_effects WHERE role_id=? AND task_id=100195',(role['id'],)).fetchone()[0])
            assert pending['chain_reason']=='successor_gameplay_unimplemented' and pending['next_ids']==[100113]
            replay = complete_task_transaction(db,actor,plan,'finish-100195',resources,inv)
            assert replay.started_tasks==()
            assert db.execute('SELECT experience FROM role_progress WHERE role_id=?',(role['id'],)).fetchone()[0]==1000
        report={'passed':['original dialogue sequence 100192->100193->100194->100195',
            'same-transaction successor activation and native accept notification',
            'battle 100113 held pending without skipping; original edge retained',
            'four completions credit 1000 EXP once; replay does not resurrect tasks'], 'live_client_tested':False}
    (OUT/'evidence/task-chain-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__ == '__main__': main()
