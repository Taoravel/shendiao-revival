"""Disposable real task/world transaction for the original blood handprint.

Enrollment and NPC approach are explicit fixtures, not natural client travel.
Clock/coordinates consume the approved isolated policy; shared/live admission
and natural client travel remain outside this check.
"""
from contextlib import closing
from dataclasses import replace
import json
from pathlib import Path
import struct
import tempfile
from accounts import AccountStore
from inventory import Inventory
from task_domain import TaskDomain,TaskEvidence,PROLOGUE_TOUCH_IDS
from task_persistence import load_task_state,apply_task_plan
from task_workflow import complete_task_transaction
from task_conversation import TaskConversation
from task_session import TaskIntent
from task_newbie_chapter import read_newbie_chapter
from task_protocol import C_COMMIT_SCENARIO_QUEST,C_QUEST_DIALOG_END,decode_accept_scenario_quest
from task_prologue_touch import (load_touch_policy,load_touch_resources,prepare_touch_storage,
    open_touch_transaction,authorize_touch_transfer,complete_touch_transfer_transaction,
    reconcile_touch_successor_transaction,resume_touch_messages)
from world_catalog import maps,maze_grids
from world_owner import MapAddress,Location,MapOwner
from world_npcs import load_placements,NpcScene
from world_story_instances import (StoryInstanceIntent,load_story_instance_rules,prepare_story_instance_storage,
    allocate_story_instance_transaction,load_story_instance_transaction)
from research_task_existing_quest import assert_ready_before_visit
from inspect_client import OUT
import world_transfer_storage as handoffs
import runtime_storage


def refuse(call):
    try:call()
    except ValueError:return
    raise AssertionError('Invalid or premature touch accepted')


def snapshot(store):
    with closing(store.connect()) as db:
        tables=[row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        return {t:tuple(sorted(map(repr,db.execute('SELECT * FROM "'+t+'"')))) for t in tables}


def main():
    with tempfile.TemporaryDirectory(prefix='task-touch-') as folder:
        store=AccountStore(Path(folder)/'state.sqlite3');runtime_storage.prepare(store)
        resources=store.task_resources;catalog=maps();grids=maze_grids()
        # Approved isolated policy. Clock/coordinate choices remain designed;
        # loading this policy does not enable a shared runtime or live service.
        policy=load_touch_policy()
        assert (policy.minimum_duration_ms,policy.timeout_ms)==(3000,15000)
        story_rules=load_story_instance_rules(resources,store.newbie_rules)
        touch=load_touch_resources(resources,policy,catalog,grids,chapter_rules=store.newbie_rules,story_rules=story_rules)
        assert set(touch.definitions)==PROLOGUE_TOUCH_IDS
        assert len(touch.definitions)==10 and 101002 not in touch.definitions
        assert len(touch.route_tasks)==43 and touch.route_tasks[(9,11)]==100106
        refuse(lambda:load_touch_resources(resources,replace(policy,target_position=(1501,63,79)),catalog,grids,
            chapter_rules=store.newbie_rules,story_rules=story_rules))
        with closing(store.connect()) as db:
            prepare_touch_storage(db)
            prepare_story_instance_storage(db)
        role=store.create_role(1111,'血手印检查',11,1010109);rid=role['id'];epoch=store.acquire_lease(1111,rid)
        inv,_,spawn,spawn_version=runtime_storage.load_role(store,1111,rid,epoch,resources)
        origin_route=store.newbie_rules.routes[(9,11)]
        intro_location=Location(rid,epoch,MapAddress(spawn[0],spawn[0],0),spawn_version,*spawn[1:])
        playback=runtime_storage.newbie_playback(store,1111,rid,epoch,intro_location,1,'touch-fixture-intro',1)
        runtime_storage.newbie_finish(store,1111,rid,epoch,struct.pack('>i',origin_route.intro_movie_id),
            intro_location,1,2,playback.ticket,inv)
        npc=next(p for p in load_placements()[1006] if p.npc_id==10498)
        source=Location(rid,epoch,MapAddress(1006,1006,0),1,npc.x,npc.y)
        target_address=MapAddress(1501,(1<<62)|rid,0)  # Unallocated address: must not authorize entry.
        with closing(store.leased(1111,rid,epoch).connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            # Trusted enrollment/position fixtures, never used on the live DB.
            db.execute('UPDATE role_positions SET map_id=?,x=?,y=? WHERE role_id=?',(*source.position,rid))
            db.execute('UPDATE position_versions SET version=1 WHERE role_id=?',(rid,))
            for action in ('offer','accept'):
                actor,state=load_task_state(db,1111,rid,epoch)
                apply_task_plan(db,actor,TaskDomain(resources).plan(actor,state,action,100160),'touch-fixture:'+action)
            actor,state=load_task_state(db,1111,rid,epoch)
            evidence=TaskEvidence(100160,rid,epoch,'npc_dialogue_completed','trusted-story-dialogue-fixture',1006,10083)
            preceding=complete_task_transaction(db,actor,TaskDomain(resources).plan(actor,state,'complete',100160,evidence=evidence),
                'touch-fixture:predecessor',resources,inv,currency_rules=store.currency_rules,
                growth_rules=store.growth_rules,attribute_rules=store.attribute_rules,
                pet_experience_rules=store.task_pet_experience_rules)
            assert preceding.started_tasks==(), 'Unapproved generic path activated timed travel'
            assert reconcile_touch_successor_transaction(db,1111,rid,epoch,resources,touch,100160)==(100106,)
            assert reconcile_touch_successor_transaction(db,1111,rid,epoch,resources,touch,100160)==()
        scene=NpcScene(source.address,load_placements()[1006],catalog,interaction_radius=32,binding_capacity=1)
        key=(1006<<32)|npc.placement_id;scene.bind(key,npc.placement_id)
        proof=scene.interact(struct.pack('>q',key),source,source,request_id='actual-touch-npc',deadline_ms=10000,now_ms=100)
        commit_proof=scene.interact(struct.pack('>q',key),source,source,
            request_id='actual-touch-submit-npc',deadline_ms=15100,now_ms=3100)
        command=TaskIntent(C_COMMIT_SCENARIO_QUEST,100106,key,0)
        with closing(store.leased(1111,rid,epoch).connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            refuse(lambda:open_touch_transaction(db,1111,rid,epoch,resources,touch,100106,proof,source,
                target_address=target_address,generation=1,now_ms=100))
            handoffs.bind_map_instance_transaction(db,1111,rid,epoch,source)
            refuse(lambda:open_touch_transaction(db,1111,rid,epoch,resources,touch,100106,proof,source,
                target_address=MapAddress(1501,1501,0),generation=1,now_ms=100))
            refuse(lambda:open_touch_transaction(db,1111,rid,epoch,resources,touch,100106,proof,source,
                target_address=target_address,generation=1,now_ms=100))
            origin=read_newbie_chapter(db,1111,rid,epoch,store.newbie_rules).origin
            story_intent=StoryInstanceIntent(origin.chapter_id,origin.creation_id,origin.policy,origin.route_fingerprint,100106)
            allocated=allocate_story_instance_transaction(db,1111,rid,epoch,story_intent,story_rules)
            target_address=allocated.address
            assert allocate_story_instance_transaction(db,1111,rid,epoch,story_intent,story_rules)==allocated
            opening=open_touch_transaction(db,1111,rid,epoch,resources,touch,100106,proof,source,
                target_address=target_address,generation=1,now_ms=100)
            native=assert_ready_before_visit(opening.messages,100106)
            actor,state=load_task_state(db,1111,rid,epoch)
            restored=TaskConversation(resources,rid,epoch).resume_messages(actor,state)
            assert any(struct.unpack_from('>i',body)[0]==100106 for _,body in restored)
            def authorize(cmd=command,location=source,now_ms=3100):
                return authorize_touch_transfer(db,1111,rid,epoch,resources,touch,opening.intent,cmd,location,
                    proof=commit_proof,generation=1,now_ms=now_ms)
            refuse(lambda:authorize(now_ms=3099))
            refuse(lambda:authorize(now_ms=15100))
            refuse(lambda:authorize(replace(command,kind=C_QUEST_DIALOG_END)))
            refuse(lambda:authorize(replace(command,npc_key=key+1)))
            refuse(lambda:authorize(location=replace(source,version=2)))
            intent=authorize()
            chapter=read_newbie_chapter(db,1111,rid,epoch,store.newbie_rules)
            assert intent.chapter_id==chapter.origin.chapter_id
            refuse(lambda:authorize_touch_transfer(db,1111,rid,epoch,resources,touch,
                replace(intent,chapter_id='other-chapter'),command,source,proof=commit_proof,generation=1,now_ms=3100))
            refuse(lambda:authorize_touch_transfer(db,1111,rid,epoch,resources,touch,intent,command,source,
                proof=replace(commit_proof,npc_id=10083),generation=1,now_ms=3100))
            refuse(lambda:authorize_touch_transfer(db,1111,rid,epoch,resources,touch,
                replace(intent,directory_intent=replace(intent.directory_intent,creation_id='other-creation')),
                command,source,proof=commit_proof,generation=1,now_ms=3100))
        source_owner=MapOwner(source.address,catalog,capacity=2,transfer_capacity=2,mailbox_capacity=2,maze=grids[1006])
        source_owner.join(source)
        target_owner=MapOwner(target_address,catalog,capacity=2,transfer_capacity=2,mailbox_capacity=2,maze=grids[1501])
        offer=source_owner.prepare_transfer(source,intent.target_position,request_id=intent.request_id,deadline_ms=intent.deadline_ms,now_ms=3100)
        reservation=target_owner.reserve(offer,3101);frozen=source_owner.freeze(reservation,3102)
        receipt=target_owner.activate(frozen,3103)
        handoffs.begin(store,1111,rid,epoch,offer)
        def complete(db,*,now_ms=3104,result=receipt,movement_state=0):
            return complete_touch_transfer_transaction(db,1111,rid,epoch,resources,touch,intent,result,inv,
                generation=1,now_ms=now_ms,movement_state=movement_state,currency_rules=store.currency_rules,
                growth_rules=store.growth_rules,attribute_rules=store.attribute_rules,
                pet_experience_rules=store.task_pet_experience_rules)
        with closing(store.leased(1111,rid,epoch).connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            refuse(lambda:complete(db,now_ms=3099));refuse(lambda:complete(db,movement_state=1))
            refuse(lambda:complete(db,result=replace(receipt,location=replace(receipt.location,x=0))))
            other=replace(receipt,location=replace(receipt.location,address=replace(target_address,instance_id=target_address.instance_id+1)))
            refuse(lambda:complete(db,result=other))
        before=snapshot(store)
        try:
            with closing(store.leased(1111,rid,epoch).connect()) as db,db:
                db.execute('BEGIN IMMEDIATE');complete(db)
                raise RuntimeError('controlled late scene encoding failure')
        except RuntimeError as exc:assert str(exc)=='controlled late scene encoding failure'
        assert snapshot(store)==before,'Late scene encoding leaked task/world/resource state'
        with closing(store.leased(1111,rid,epoch).connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');result=complete(db)
            assert not result.replayed and result.target==receipt.location
            state=load_task_state(db,1111,rid,epoch)[1]
            assert 100106 in state.completed and 100107 in state.active and 100107 not in state.completed
            effect=json.loads(db.execute('SELECT payload FROM task_effects WHERE role_id=? AND task_id=100106',(rid,)).fetchone()[0])
            assert effect['chain_target']==100107 and effect['chain_status']=='activated'
            projected=resume_touch_messages(db,1111,rid,epoch,resources,touch)
            assert len(projected)==1
            bean=decode_accept_scenario_quest(projected[0][1])
            assert (bean.quest_id,bean.state)==(100107,0)
            assert set(effect['continuation_resolved_fields'])>={'RewardMapJumpType','RewardMapID','RewardMapXPos','RewardMapYPos'}
            assert db.execute('SELECT map_id,x,y FROM role_positions WHERE role_id=?',(rid,)).fetchone()==policy.target_position
            stored=handoffs.load_map_instance_transaction(db,1111,rid,epoch)
            assert stored.address==target_address and stored.position==policy.target_position
        before_replay=snapshot(store)
        with closing(store.leased(1111,rid,epoch).connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');replay=complete(db,now_ms=70000)
            assert replay.replayed and not any(kind==0xc4a47 for kind,_ in replay.messages)
        assert snapshot(store)==before_replay,'Paid retry wrote historical task/world state'
        old_epoch=epoch;epoch=store.acquire_lease(1111,rid)
        with closing(store.leased(1111,rid,old_epoch).connect()) as stale:
            refuse(lambda:stale.execute('BEGIN IMMEDIATE'))
        with closing(store.leased(1111,rid,epoch).connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');assert 100106 in load_task_state(db,1111,rid,epoch)[1].completed
            assert handoffs.load_map_instance_transaction(db,1111,rid,epoch).address==target_address
            assert load_story_instance_transaction(db,1111,rid,epoch,intent.directory_intent,
                story_rules,expected_address=target_address).address==target_address
    result=dict(passed=['10 current-route original touch definitions retain exact fields/edges; legacy101002 remains excluded',
        'all43 original chapter routes resolve by raw edges; actual completed intro identity is frozen and foreign chapter refuses',
        'explicit policy recovery of100160 activates100106 once; generic path stays pending without it',
        'actual map-owned blood-handprint proof opens native ready3 and local progress path',
        'server earliest3000ms fence refuses premature, expired, moved, wrong NPC and dialog-end requests',
        'unknown source instance refuses; explicit source adoption and private target address commit with the task',
        'real world directory allocates once per original chapter; unallocated private address and changed creation identity refuse',
        'late target-scene encoding failure rolls every table back; exact paid retry writes no table',
        'new lease retains the exact target instance and completion; original battle successor is active0 without entering AI8001'],
        native_existing_quest=native,policy=policy.revision,private_directory_policy=policy.directory_revision,
        database='disposable',natural_travel_verified=False,shared_runtime_wired=False,native_gui_verified=False,
        live_server_changed=False,battle_executed=False)
    (OUT/'evidence/task-prologue-touch-check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(result)


if __name__=='__main__':main()
