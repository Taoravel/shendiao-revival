"""Isolated already-active dream return: original dialogue and raw commit only.

Reuses an explicitly late-story puzzle fixture; it executes no formal combat
and does not claim naturally completed earlier story or native GUI movement.
"""
from contextlib import closing
from dataclasses import replace
import json
from pathlib import Path
import struct
import tempfile

from accounts import AccountStore
from inspect_client import OUT,write_json
from task_prologue_puzzle import load_puzzle_policy,load_puzzle_resources,prepare_puzzle_storage
from task_prologue_return_dialogue import (load_return_dialogue_resources,open_return_dialogue_transaction,
    inspect_return_commit_transaction,resume_return_messages,RETURN_IDS,FIRST_RETURN_IDS,SECOND_RETURN_IDS)
from task_protocol import (C_COMMIT_SCENARIO_QUEST,C_QUEST_DIALOG_END,S_REFRESH_SCENARIO_QUEST_STATE,
    decode_accept_scenario_quest)
from task_session import decode_task_intent
from verify_task_prologue_puzzle import check_role,snapshot
from world_catalog import maps
from world_npcs import load_placements,NpcScene
from world_owner import Location,MapOwner
from world_story_instances import load_story_instance_rules,prepare_story_instance_storage
from world_transfer_storage import load_map_instance_transaction,bind_map_instance_transaction
import runtime_storage


def refuse(fn):
    try:fn()
    except ValueError:return
    raise AssertionError('Wrong or stale dream-return intent accepted')


def main():
    with tempfile.TemporaryDirectory(prefix='dream-return-dialogue-') as directory:
        store=AccountStore(Path(directory)/'isolated.sqlite3');runtime_storage.prepare(store)
        resources=store.task_resources;placements=load_placements()
        story=load_story_instance_rules(resources,store.newbie_rules)
        returns=load_return_dialogue_resources(resources,store.newbie_rules,story,placements)
        assert set(returns.definitions)==RETURN_IDS and len(returns.route_tasks)==43
        assert all(pair[0] in FIRST_RETURN_IDS and pair[1] in SECOND_RETURN_IDS for pair in returns.route_tasks.values())
        puzzles=load_puzzle_resources(resources,store.newbie_rules,story,placements,policy=load_puzzle_policy())
        with closing(store.connect()) as db,db:
            prepare_puzzle_storage(db);prepare_story_instance_storage(db)
        # Genuine public puzzle completion on the established explicit story
        # fixture activates100121. No type40 journal/win is inserted or run.
        check_role(store,puzzles,9,11,100120)
        rid=store.roles(1111)[0]['id'];epoch=store.acquire_lease(1111,rid)
        runtime_storage.load_role(store,1111,rid,epoch,resources)
        version=store.position_version(rid)+1
        assert store.save_checkpoint(1111,rid,epoch,(1501,5464,1993),version)
        with closing(store.leased(1111,rid,epoch).connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            old=load_map_instance_transaction(db,1111,rid,epoch)
            current=Location(rid,epoch,old.address,version,5464,1993)
            bind_map_instance_transaction(db,1111,rid,epoch,current)
        # Exact NPC-position checkpoint is an approach fixture, not navigation.
        owner=MapOwner(current.address,maps(),capacity=1,transfer_capacity=8,mailbox_capacity=8)
        owner.join(current);map_generation=owner.inspect_lifecycle(0).owner_generation
        scene=NpcScene(current.address,placements[1501],maps(),interaction_radius=32,binding_capacity=1)
        key=(1501<<32)|6;scene.bind(key,6)
        proof=scene.interact(struct.pack('>q',key),current,current,request_id='return-menu',now_ms=100,deadline_ms=5000)
        before=snapshot(store)
        with closing(store.leased(1111,rid,epoch).connect()) as db,db:
            db.execute('BEGIN')
            opened=open_return_dialogue_transaction(db,1111,rid,epoch,resources,returns,100121,proof,current,
                generation=1,map_generation=map_generation,now_ms=100,deadline_ms=5000)
            ticket=opened.ticket
            assert opened.messages[1]==(S_REFRESH_SCENARIO_QUEST_STATE,struct.pack('>ii',100121,3))
            assert opened.messages[-1]==(0xc232a,struct.pack('>q',key)+b'\x00\x01'+struct.pack('>i',100121))
            bean=resume_return_messages(db,1111,rid,epoch,resources,returns)
            assert tuple((decode_accept_scenario_quest(body).quest_id,decode_accept_scenario_quest(body).state)
                for _,body in bean)==((100121,0),)
            assert resume_return_messages(db,1111,rid,epoch,resources,returns,already_projected=(100121,))==()
            refuse(lambda:open_return_dialogue_transaction(db,1111,rid,epoch,resources,returns,100111,proof,current,
                generation=1,map_generation=map_generation,now_ms=100,deadline_ms=5000))
            refuse(lambda:open_return_dialogue_transaction(db,1111,rid,epoch,resources,returns,100121,
                replace(proof,placement_id=2),current,generation=1,map_generation=map_generation,now_ms=100,deadline_ms=5000))
        fresh=scene.interact(struct.pack('>q',key),current,current,request_id='return-commit',now_ms=101,deadline_ms=5000)
        command=decode_task_intent(C_COMMIT_SCENARIO_QUEST,struct.pack('>iQi',100121,key,0))
        with closing(store.leased(1111,rid,epoch).connect()) as db,db:
            db.execute('BEGIN')
            def inspect(**overrides):
                opts=dict(generation=1,map_generation=map_generation,now_ms=101)
                opts.update(overrides)
                return inspect_return_commit_transaction(db,1111,rid,epoch,resources,returns,
                    opts.pop('ticket',ticket),opts.pop('command',command),fresh,current,**opts)
            accepted=inspect()
            assert accepted.original_jump==(3,1006,335,144) and accepted.successor_id==100122
            assert accepted.coordinate_space=='original_reward_fields_unresolved' and not accepted.settlement_authorized
            assert inspect()==accepted, 'Same current ticket changed raw request identity'
            for change in (dict(now_ms=99),dict(now_ms=5000),dict(generation=2),dict(map_generation=map_generation+'-old'),
                    dict(command=replace(command,npc_key=0)),dict(command=replace(command,opaque=1)),
                    dict(command=replace(command,kind=C_QUEST_DIALOG_END)),dict(ticket=replace(ticket,task_revision=-1))):
                refuse(lambda change=change:inspect(**change))
        assert snapshot(store)==before, 'Read-only dialogue/intent/resume wrote task, assets, receipts or world state'
        owner.leave(current);epoch2=store.acquire_lease(1111,rid)
        current2=replace(current,login_epoch=epoch2);owner.join(current2)
        proof2=scene.interact(struct.pack('>q',key),current2,current2,request_id='return-new-lease',now_ms=102,deadline_ms=5000)
        with closing(store.leased(1111,rid,epoch2).connect()) as db,db:
            db.execute('BEGIN')
            refuse(lambda:inspect_return_commit_transaction(db,1111,rid,epoch2,resources,returns,ticket,command,
                proof2,current2,generation=1,map_generation=map_generation,now_ms=102))
        owner.leave(current2)
    report=dict(passed=['43 original routes freeze exact20 return definitions and actual NPC placements',
        'Actual current private NPC10140 opens native Start menu with explicit ready refresh',
        'Original real-key commit gives only raw Jump3/1006/335/144 intent; no coordinate adoption or settlement',
        'Wrong key/option/End/placement/revision/clock/generation/lease refuse; all tables unchanged',
        'Only existing current-route active0 resumes; combined inactive/missing-predecessor first-family context refuses'],
        shared_runtime_wired=False,settlement_implemented=False,transfer_policy_approved=False,
        native_gui_verified=False,live_server_changed=False,battle_executed=False,
        fixtures=['Inherited puzzle test uses explicit late-story enrollment and completed master historical journal',
            'Exact private NPC-position approach and32px Scene are explicit fixtures, not v2 or natural GUI'],
        limits=['First-family valid post-AI8002 and isolated combat-predecessor negative cases remain unverified; no fake win inserted',
            'This report validates dialogue/raw intent only; no dream-return completion or reward is enabled'])
    write_json(OUT/'evidence/task-prologue-return-dialogue-verification.json',report)
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':main()
