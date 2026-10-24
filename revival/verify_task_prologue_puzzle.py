"""Isolated puzzle admission, actual reward channels and caller rollback.

The default policy is the published central policy. --fixture retains the
earlier explicitly UNAPPROVED clock fixture separately. Creation/intro is
natural; later story enrollment, position and completed dialogue are trusted
fixtures. No paused battle, live client, live database or shared route is used.
"""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
import json
import struct
import tempfile
from accounts import AccountStore
from inventory import FIGHT_PET
from inspect_client import OUT,write_json
from task_domain import TaskDomain,TaskEvidence,PROLOGUE_PUZZLE_IDS
from task_persistence import load_task_state,apply_task_plan
from task_newbie_chapter import read_newbie_chapter
from task_workflow import complete_task_transaction
from task_chains import plan_task_chain
from task_conversation import TaskConversation
from task_session import decode_task_intent
from task_protocol import C_COMMIT_SCENARIO_QUEST,C_QUEST_DIALOG_END,S_REFRESH_SCENARIO_QUEST_STATE
from task_protocol import decode_accept_scenario_quest
from task_prologue_puzzle import (PuzzlePolicy,load_puzzle_resources,prepare_puzzle_storage,
    reconcile_puzzle_successor_transaction,open_puzzle_menu_transaction,complete_puzzle_transaction,
    resume_puzzle_messages,load_puzzle_policy)
from world_npcs import load_placements,NpcScene
from world_owner import Location,MapAddress,MapOwner
from world_story_instances import (StoryInstanceIntent,load_story_instance_rules,prepare_story_instance_storage,
    allocate_story_instance_transaction)
from world_transfer_storage import bind_map_instance_transaction
from research_prologue_puzzle_close import native_puzzle_close
from role_growth import read_growth
import runtime_storage


def refuse(fn):
    try:fn()
    except ValueError:return
    raise AssertionError('Untrusted or stale portrait claim accepted')


def snapshot(store):
    with closing(store.connect()) as db:
        tables=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        return {t:tuple(sorted(map(repr,db.execute('SELECT * FROM "'+t+'"')))) for t in tables}


def check_role(store,puzzles,role_config,school,q):
    resources=store.task_resources
    role=store.create_role(1111,'画卷'+str(role_config),school,1010100+role_config)
    rid=role['id'];epoch=store.acquire_lease(1111,rid)
    inv,_,spawn,version=runtime_storage.load_role(store,1111,rid,epoch,resources)
    route=store.newbie_rules.routes[(role_config,school)]
    intro=Location(rid,epoch,MapAddress(spawn[0],spawn[0],0),version,*spawn[1:])
    playback=runtime_storage.newbie_playback(store,1111,rid,epoch,intro,1,'puzzle-intro',1)
    runtime_storage.newbie_finish(store,1111,rid,epoch,struct.pack('>i',route.intro_movie_id),intro,1,2,playback.ticket,inv)
    pet=inv.grant_pet(500138)
    inv.receive(FIGHT_PET,struct.pack('>i',pet))
    task=resources.definitions[q];previous=task['incoming_ids'][0];successor=task['next_ids'][0]
    reward_rules=dict(growth_rules=store.growth_rules,attribute_rules=store.attribute_rules,
        currency_rules=store.currency_rules,pet_experience_rules=store.task_pet_experience_rules)
    with closing(store.leased(1111,rid,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        chapter=read_newbie_chapter(db,1111,rid,epoch,store.newbie_rules);origin=chapter.origin
        canonical=StoryInstanceIntent(origin.chapter_id,origin.creation_id,origin.policy,origin.route_fingerprint,
            puzzles.story_rules.source_tasks[(role_config,school)])
        allocated=allocate_story_instance_transaction(db,1111,rid,epoch,canonical,puzzles.story_rules)
        current=Location(rid,epoch,allocated.address,1,5870,1541)
        # Explicit story/approach fixtures, not a claimed natural battle chain.
        assert tuple(r[0] for r in db.execute("SELECT task_id FROM task_journal WHERE role_id=? AND state='active'",(rid,)))==(
            route.successor_task_id,)
        # Historical first-master journal is part of this late-story fixture,
        # so the public chapter reconciler can retain its selected successor.
        # No card, weapon, reward, formal battle or win is fabricated/executed.
        db.execute("UPDATE task_journal SET state='completed' WHERE role_id=? AND task_id=?",(rid,route.successor_task_id))
        db.execute('UPDATE role_positions SET map_id=?,x=?,y=? WHERE role_id=?',(*current.position,rid))
        db.execute('UPDATE position_versions SET version=1 WHERE role_id=?',(rid,))
        bind_map_instance_transaction(db,1111,rid,epoch,current)
        for action in ('offer','accept'):
            actor,state=load_task_state(db,1111,rid,epoch)
            apply_task_plan(db,actor,TaskDomain(resources).plan(actor,state,action,previous),'fixture:'+action)
        actor,state=load_task_state(db,1111,rid,epoch)
        proof=TaskEvidence(previous,rid,epoch,'npc_dialogue_completed','trusted-Cheng-Ying-fixture',1501,10139)
        done=complete_task_transaction(db,actor,TaskDomain(resources).plan(actor,state,'complete',previous,evidence=proof),
            'fixture:ChengYing',resources,inv,**reward_rules)
        assert done.started_tasks==(), 'Generic TaskChain silently enabled the new puzzle family'
        assert reconcile_puzzle_successor_transaction(db,1111,rid,epoch,resources,puzzles,previous)==(q,)
        assert reconcile_puzzle_successor_transaction(db,1111,rid,epoch,resources,puzzles,previous)==()
        actor,state=load_task_state(db,1111,rid,epoch)
        assert len(TaskConversation(resources,rid,epoch).resume_messages(actor,state))==1
    placements=load_placements();key=(1501<<32)|16
    from world_catalog import maps
    scene=NpcScene(current.address,placements[1501],maps(),interaction_radius=32,binding_capacity=1)
    scene.bind(key,16)
    owner=MapOwner(current.address,maps(),capacity=1,transfer_capacity=8,mailbox_capacity=8)
    owner.join(current)
    map_generation=owner.inspect_lifecycle(0).owner_generation
    proof=scene.interact(struct.pack('>q',key),current,current,request_id='puzzle-menu',now_ms=99,deadline_ms=999999)
    with closing(store.leased(1111,rid,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        opened=open_puzzle_menu_transaction(db,1111,rid,epoch,resources,puzzles,q,proof,current,
            generation=1,map_generation=map_generation,now_ms=100)
        ticket=opened.ticket
        expected=struct.pack('>q',key)+b'\x01'+struct.pack('>i',553)+b'\x00'
        assert opened.messages[-1]==(0xc232a,expected)
        refuse(lambda:open_puzzle_menu_transaction(db,1111,rid,epoch,resources,puzzles,q,
            replace(proof,npc_id=10139),current,generation=1,map_generation=map_generation,now_ms=100))
    kind,body=native_puzzle_close(q,3)[0]
    command=decode_task_intent(kind,body)
    accepted_ms=ticket.earliest_ms
    fresh=scene.interact(struct.pack('>q',key),current,current,request_id='puzzle-submit',now_ms=accepted_ms,deadline_ms=999999)

    def complete(db,**overrides):
        kwargs=dict(proof=fresh,location=current,generation=1,map_generation=map_generation,now_ms=accepted_ms,**reward_rules)
        kwargs.update(overrides)
        return complete_puzzle_transaction(db,1111,rid,epoch,resources,puzzles,ticket,
            kwargs.pop('command',command),inv,**kwargs)

    with closing(store.leased(1111,rid,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE');before=db.execute('SELECT total_changes()').fetchone()
        refuse(lambda:complete(db,now_ms=ticket.earliest_ms-1))
        refuse(lambda:complete(db,now_ms=ticket.deadline_ms))
        refuse(lambda:complete(db,generation=2))
        refuse(lambda:complete(db,map_generation=map_generation+'-replaced'))
        refuse(lambda:complete(db,command=replace(command,npc_key=key)))
        refuse(lambda:complete(db,command=replace(command,opaque=1)))
        refuse(lambda:complete(db,command=replace(command,kind=C_QUEST_DIALOG_END)))
        refuse(lambda:complete(db,proof=replace(fresh,placement_id=15)))
        moved=replace(current,version=2,x=current.x+1)
        refuse(lambda:complete(db,proof=replace(fresh,position_version=2),location=moved))
        assert db.execute('SELECT total_changes()').fetchone()==before
    before=snapshot(store)
    try:
        with closing(store.leased(1111,rid,epoch).connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');complete(db)
            raise RuntimeError('controlled exception at caller final-encoding seam before commit')
    except RuntimeError as exc:
        assert str(exc)=='controlled exception at caller final-encoding seam before commit'
    assert snapshot(store)==before, 'Puzzle assets/task/recipient/receipt failed to roll back together'
    # An expired menu can be renewed without penalty; it does not complete by timeout.
    expired=ticket
    renewed=scene.interact(struct.pack('>q',key),current,current,request_id='puzzle-renew',
        now_ms=expired.deadline_ms,deadline_ms=expired.deadline_ms+1000)
    with closing(store.leased(1111,rid,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        ticket=open_puzzle_menu_transaction(db,1111,rid,epoch,resources,puzzles,q,renewed,current,
            generation=1,map_generation=map_generation,now_ms=expired.deadline_ms).ticket
        assert ticket.operation_id!=expired.operation_id
        assert db.execute('SELECT COUNT(*) FROM task_prologue_puzzles WHERE role_id=?',(rid,)).fetchone()==(0,)
    # An uncommitted ticket never survives lease replacement. The real public
    # role loader preserves current task/instance; a new NPC menu is required.
    prior=ticket;owner.leave(current);epoch=store.acquire_lease(1111,rid)
    inv,_,_,_=runtime_storage.load_role(store,1111,rid,epoch,resources)
    current=replace(current,login_epoch=epoch)
    owner.join(current)
    renewed=scene.interact(struct.pack('>q',key),current,current,request_id='puzzle-new-lease',
        now_ms=prior.opened_ms+1,deadline_ms=prior.deadline_ms)
    with closing(store.leased(1111,rid,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        refuse(lambda:complete_puzzle_transaction(db,1111,rid,epoch,resources,puzzles,prior,command,inv,
            proof=renewed,location=current,generation=1,map_generation=map_generation,
            now_ms=prior.opened_ms+1,**reward_rules))
        beans=resume_puzzle_messages(db,1111,rid,epoch,resources,puzzles)
        assert tuple(decode_accept_scenario_quest(body).quest_id for _,body in beans)==(q,)
        ticket=open_puzzle_menu_transaction(db,1111,rid,epoch,resources,puzzles,q,renewed,current,
            generation=1,map_generation=map_generation,now_ms=prior.opened_ms+1).ticket
        assert ticket.operation_id!=prior.operation_id and ticket.source.login_epoch==epoch
    accepted_ms=ticket.deadline_ms-1
    fresh=scene.interact(struct.pack('>q',key),current,current,request_id='puzzle-last-valid',
        now_ms=accepted_ms,deadline_ms=ticket.deadline_ms)
    with closing(store.leased(1111,rid,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        refuse(lambda:complete(db,now_ms=ticket.deadline_ms))
        result=complete(db)
        assert result.completion.rewards.experience_awarded==360
        pet_result=result.completion.rewards.pet_experience
        assert (pet_result.status,pet_result.amount,pet_result.recipient_id)==(
            'awarded',task['display_rewards']['PetExpReward'],pet)
        assert result.completion.started_tasks==(successor,)
        state=load_task_state(db,1111,rid,epoch)[1]
        assert q in state.completed and successor in state.active
        evidence=json.loads(db.execute('SELECT payload FROM task_effects WHERE role_id=? AND task_id=?',(rid,q)).fetchone()[0])
        assert evidence['portrait_claim']['server_verified_board'] is False
    with closing(store.leased(1111,rid,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        old_growth=read_growth(db,1111,rid)
        old_assets=inv.immutable_snapshot_transaction(db,epoch=epoch)
        replay=complete(db,proof=None,location=None,map_generation=None,now_ms=ticket.deadline_ms+1)
        assert replay.replayed and replay.completion.rewards.experience_awarded==360
        assert not any(kind==S_REFRESH_SCENARIO_QUEST_STATE for kind,_ in replay.messages)
        assert read_growth(db,1111,rid)==old_growth
        assert inv.immutable_snapshot_transaction(db,epoch=epoch)==old_assets
        assert db.execute('SELECT COUNT(*) FROM task_prologue_puzzles WHERE role_id=?',(rid,)).fetchone()==(1,)
    epoch2=store.acquire_lease(1111,rid)
    with closing(store.leased(1111,rid,epoch2).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        _,state=load_task_state(db,1111,rid,epoch2)
        assert q in state.completed and successor in state.active
        beans=resume_puzzle_messages(db,1111,rid,epoch2,resources,puzzles)
        assert tuple((decode_accept_scenario_quest(body).quest_id,decode_accept_scenario_quest(body).state)
            for _,body in beans)==((successor,0),)
        assert resume_puzzle_messages(db,1111,rid,epoch2,resources,puzzles,already_projected=(successor,))==()
        refuse(lambda:complete_puzzle_transaction(db,1111,rid,epoch2,resources,puzzles,ticket,command,inv,
            proof=None,location=None,generation=1,map_generation=None,now_ms=accepted_ms,**reward_rules))
    return dict(task_id=q,pet_experience=task['display_rewards']['PetExpReward'],pet_key=pet)


def main(use_fixture=False):
    with tempfile.TemporaryDirectory(prefix='task-portrait-puzzle-') as directory:
        store=AccountStore(Path(directory)/'state.sqlite3');runtime_storage.prepare(store)
        resources=store.task_resources
        policy=(PuzzlePolicy('isolated-unapproved-puzzle-fixture',1000,300000) if use_fixture
            else load_puzzle_policy())
        if not use_fixture:
            assert (policy.minimum_elapsed_ms,policy.timeout_ms)==(0,300000)
            assert len(policy.source_fingerprint)==64
            central=json.loads((OUT/'design/newbie-puzzle-v1.json').read_text(encoding='utf-8'))
            for field,value in [('minimum_elapsed_ms',True),('minimum_elapsed_ms',1000),('timeout_ms',300001),
                    ('service_id',552),('server_verified_board',True),('tasks',[100120]*10)]:
                altered=Path(directory)/'invalid-policy.json'
                altered.write_text(json.dumps(dict(central,**{field:value})),encoding='utf-8')
                refuse(lambda:load_puzzle_policy(altered))
        story=load_story_instance_rules(resources,store.newbie_rules)
        puzzles=load_puzzle_resources(resources,store.newbie_rules,story,load_placements(),policy=policy)
        assert set(puzzles.definitions)==PROLOGUE_PUZZLE_IDS and len(puzzles.route_tasks)==43
        with closing(store.connect()) as db,db:
            prepare_puzzle_storage(db);prepare_story_instance_storage(db)
        rows=[check_role(store,puzzles,9,11,100120),check_role(store,puzzles,6,17,100719)]
    report=dict(passed=['43 original routes map to exactly10 portrait tasks; generic TaskChain remains pending',
        'Current private directory/NPC11106 placement16 opens original service553 menu',
        'Actual original close packet passes dedicated zero-NPC claim; wrong NPC/key/epoch/position/clock refuse',
        'Controlled exception at caller final-encoding seam before commit rolls back every table',
        f'Configured minimum{policy.minimum_elapsed_ms} admits at earliest; deadline-1 admits, deadline refuses; expiry/new lease require renewed NPC menu',
        'Actual public pet/character reward channels retain 360/360 and360/350 cases; original successor active0',
        'Paid claim does not repeat EXP or state1/Finish; new lease restores only original successor bean0 and rejects old ticket'],
        roles=rows,policy=policy.revision,production_policy_approved=not use_fixture,
        minimum_elapsed_ms=policy.minimum_elapsed_ms,timeout_ms=policy.timeout_ms,
        policy_fingerprint=policy.source_fingerprint,shared_runtime_wired=False,
        natural_story_travel=False,server_verified_board=False,live_server_changed=False,native_gui_verified=False,
        battle_executed=False)
    target='task-prologue-puzzle-fixture-check.json' if use_fixture else 'task-prologue-puzzle-check.json'
    write_json(OUT/'evidence'/target,report);print(report)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--fixture',action='store_true')
    main(parser.parse_args().fixture)
