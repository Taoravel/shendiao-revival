"""Original simple talk task, real map NPC proof, one completion/reward commit."""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
import json
import struct
import tempfile
from accounts import AccountStore
from inventory import Inventory
from inspect_client import OUT
from tasks import prepare_task_store
from task_domain import TaskDomain
from task_persistence import load_task_state, apply_task_plan
from task_rewards import prepare_reward_storage
from task_conversation import TaskConversation
from task_session import decode_task_intent
from task_protocol import C_COMMIT_SCENARIO_QUEST, C_QUEST_DIALOG_END, decode_scenario_state, decode_quest_can_accept
from task_dialog_protocol import decode_user_experience, decode_visit_npc
from task_workflow import complete_task_transaction, completion_messages
from progression import credit_experience, read_experience
from world_catalog import maps
from world_npcs import load_placements, NpcScene
from world_owner import MapAddress, Location


def main():
    with tempfile.TemporaryDirectory() as directory:
        accounts = AccountStore(Path(directory)/'workflow.sqlite3')
        role = accounts.create_role(1111,'原版任务',11,1010109)
        resources = prepare_task_store(accounts)
        inventory = Inventory(accounts,1111,role['id'],Inventory.prepare(accounts))
        with closing(accounts.connect()) as db:
            prepare_reward_storage(db)
        epoch = accounts.acquire_lease(1111,role['id'])
        address = MapAddress(1006,1,0)
        placements = load_placements()[1006]
        npc = next(p for p in placements if p.npc_id == 10899)
        scene = NpcScene(address,placements,maps(),interaction_radius=32,binding_capacity=1)
        scene.bind(42,npc.placement_id)
        current = Location(role['id'],epoch,address,1,npc.x,npc.y)
        proof = scene.interact(struct.pack('>Q',42),current,current,
                               request_id='npc-event',deadline_ms=1000,now_ms=1)
        conversation = TaskConversation(resources,role['id'],epoch)
        domain = TaskDomain(resources)
        with closing(accounts.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            actor,state = load_task_state(db,1111,role['id'],epoch)
            apply_task_plan(db,actor,domain.plan(actor,state,'offer',100192),'offer')
            actor,state = load_task_state(db,1111,role['id'],epoch)
            menu = conversation.menu_messages(actor,state,proof,current,now_ms=1,deadline_ms=1000)
            assert decode_quest_can_accept(menu[0][1]) == [100192]
            assert decode_visit_npc(menu[1][1]) == (42,[],[100192])
            intent = decode_task_intent(C_COMMIT_SCENARIO_QUEST,struct.pack('>iQi',100192,42,0))
            acceptance = conversation.plan_accept(actor,state,intent,proof,current,now_ms=2,deadline_ms=1000)
            apply_task_plan(db,actor,acceptance,'accept')
        assert conversation.acceptance_messages(acceptance,42)[0][0] == 0xc4a45
        with closing(accounts.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            actor,state = load_task_state(db,1111,role['id'],epoch)
            dialogue = conversation.open(actor,state,100192,proof,current,now_ms=3,deadline_ms=1000)
            ready,menu = conversation.menu_messages(actor,state,proof,current,now_ms=3,deadline_ms=1000)
            assert decode_scenario_state(ready[1]) == (100192,3)
            assert decode_visit_npc(menu[1]) == (42,[],[100192])
            end = decode_task_intent(C_QUEST_DIALOG_END,struct.pack('>i',100192))
            try:
                conversation.plan_finish(actor,state,end,replace(current,version=2),now_ms=4)
                raise AssertionError('Moved NPC conversation completed')
            except ValueError:
                pass
            plan = conversation.plan_finish(actor,state,end,current,now_ms=4)
            result = complete_task_transaction(db,actor,plan,'finish',resources,inventory)
        conversation.acknowledge(plan)
        packets = completion_messages(result)
        assert decode_scenario_state(packets[0][1]) == (100192,1)
        assert decode_user_experience(packets[1][1]) == 150
        assert [(i['template_id'],i['quantity'],i['binding']) for i in inventory.snapshot()['items']] == [(43000,1,1)]
        # Replaying a completed operation after another reward must send the
        # present balance, not the original channel receipt's older 150 balance.
        with closing(accounts.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            credit_experience(db,1111,role['id'],123)  # isolated later-reward fixture
            replay = complete_task_transaction(db,actor,plan,'finish',resources,inventory)
        assert decode_user_experience(completion_messages(replay)[1][1]) == 273
        with closing(accounts.connect()) as db, db:
            db.execute('BEGIN')
            assert read_experience(db,1111,role['id']).experience == 273
            assert db.execute('SELECT COUNT(*) FROM task_effects').fetchone()[0] == 1
        report = {'passed':['original NPC proof and CCommit acceptance',
            'native ready state 3 then quest-ID NPC menu', 'moved conversation refused',
            'task completion + 150 EXP + original bound item committed together',
            'native completion and current-balance messages; replay has no duplicate reward'],
            'task_id':100192,'dialogue_lines':len(dialogue.lines),'live_client_tested':False}
    (OUT/'evidence/task-workflow-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__ == '__main__': main()
