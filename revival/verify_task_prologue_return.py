"""Approved return settlement in a disposable store; no formal battle or GUI.

Second-family fixture completes the real public portrait-claim path. The
earlier story/master journal and approach remain explicit inherited fixtures.
First-family uses explicit task-settlement contract inputs, never a real AI
victory. Production battle capabilities remain empty.
"""
from contextlib import closing
from dataclasses import replace
import json
import hashlib
import importlib
from pathlib import Path
import struct
import tempfile

from accounts import AccountStore
from inspect_client import OUT,write_json
from inventory import FIGHT_PET,REFRESH_PET,REFRESH_PET_EXP,pet_record
from progression import read_experience,credit_experience
from role_growth import read_growth
from role_attribute_storage import attribute_snapshot_if_initialized
from role_equipment import resource_caps_from_projection
from role_equipment_storage import current_equipment_totals,current_resource_profile
from role_resource_storage import migrate_role_resources,read_role_resources,apply_resource_transition
from role_resource_plan import plan_resource_values
from role_attribute_protocol import growth_refresh
from task_dialog_protocol import S_REFRESH_USER_EXP,encode_user_experience
from task_battle import load_task_battle_resources,prepare_task_battle_storage
from task_battle import (open_task_battle_dialogue,admit_task_battle_transaction,
    settle_task_battle_transaction,read_completed_task_battle_proof,TASK_BATTLE_SCOPE,SETTLEMENT_PREFIX)
from task_battle_protocol import TaskBattleRequest
from task_domain import TaskDomain
from task_persistence import apply_task_plan
from task_newbie_chapter import read_newbie_chapter
from battle_owner import Participant
from battle import Fighter
from training_battle import BattleFinished
from task_prologue_puzzle import load_puzzle_policy,load_puzzle_resources,prepare_puzzle_storage
from task_prologue_return_dialogue import inspect_return_commit_transaction
from task_prologue_return import (load_dream_return_rules,prepare_dream_return_storage,
    open_dream_return_transaction,resolve_dream_return_transaction,complete_dream_return_transaction)
from task_prologue_return import reconcile_dream_return_successor_transaction
from task_persistence import load_task_state
from task_protocol import C_COMMIT_SCENARIO_QUEST,encode_scenario_state
from task_session import decode_task_intent
from verify_task_prologue_puzzle import check_role,snapshot
from world_catalog import maps,maze_grids
from world_npcs import load_placements,NpcScene
from world_owner import Location,MapOwner,MoveCommand
from world_story_instances import load_story_instance_rules,prepare_story_instance_storage
from world_story_instances import StoryInstanceIntent,allocate_story_instance_transaction,load_story_instance_transaction
from world_transfer_storage import load_map_instance_transaction,bind_map_instance_transaction
import world_transfer_storage as world_storage
import runtime_storage
from verify_world_committed_transfer_read import readonly


def refuse(fn):
    try:fn()
    except ValueError:return
    raise AssertionError('Invalid dream-return authorization accepted')


def source_hashes():
    names=('task_domain','task_battle','task_prologue_puzzle','task_prologue_return','task_prologue_return_dialogue',
        'world_transfer_storage','world_owner','world_story_instances','inventory','runtime_storage',
        'role_growth','role_equipment_storage','role_resource_storage','role_attribute_storage',
        'task_workflow','task_chains','task_rewards','task_pet_experience','verify_world_committed_transfer_read',
        'verify_task_prologue_puzzle','verify_task_prologue_return')
    result={name:hashlib.sha256(Path(importlib.import_module(name).__file__).read_bytes()).hexdigest() for name in names}
    for name in ('newbie-dream-return-v1.json','newbie-puzzle-v1.json','story-instance-v1.json'):
        result['design/'+name]=hashlib.sha256((OUT/'design'/name).read_bytes()).hexdigest()
    return result


def check_first_family_contract(store,rules,placements,catalog):
    """Planner-approved temporary task contract, NOT an AI8002 battle/win.

    Creation/intro and task admission/settlement run their public Interfaces.
    The late story, approach, numeric Participant and terminal input are explicit
    fixtures. Never construct or launch a BattleOwner or production capability.
    """
    resources=store.task_resources
    role=store.create_role(1111,'梦醒契约9',11,1010109)
    rid=role['id'];epoch=store.acquire_lease(1111,rid)
    inv,_,spawn,version=runtime_storage.load_role(store,1111,rid,epoch,resources)
    route=store.newbie_rules.routes[(9,11)]
    from world_owner import MapAddress
    intro=Location(rid,epoch,MapAddress(spawn[0],spawn[0],0),version,*spawn[1:])
    playback=runtime_storage.newbie_playback(store,1111,rid,epoch,intro,1,'first-return-contract-intro',1)
    runtime_storage.newbie_finish(store,1111,rid,epoch,struct.pack('>i',route.intro_movie_id),intro,1,2,playback.ticket,inv)
    # Explicit owned pet confirms the return's original pet0 changes no pet.
    pet=inv.grant_pet(500138);inv.receive(FIGHT_PET,struct.pack('>i',pet))
    # Only this disposable admission registry accepts the artificial contract.
    # rules.battles remains the default disabled metadata registry throughout.
    fixture=load_task_battle_resources(resources,enabled_task_ids=frozenset({100110}),
        engine_revision='isolated-first-return-task-contract-v1')
    definition=fixture.definitions[100110]
    npc=next(p for p in placements[1501] if p.npc_id==definition.npc_id)
    with closing(store.leased(1111,rid,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        origin=read_newbie_chapter(db,1111,rid,epoch,store.newbie_rules).origin
        canonical=StoryInstanceIntent(origin.chapter_id,origin.creation_id,origin.policy,origin.route_fingerprint,
            rules.dialogue.story_rules.source_tasks[(9,11)])
        allocation=allocate_story_instance_transaction(db,1111,rid,epoch,canonical,rules.dialogue.story_rules)
        current=Location(rid,epoch,allocation.address,1,npc.x,npc.y)
        # Explicit historical master/enrollment/approach fixture, no battle
        # journal completion or victory receipt is written by this fixture.
        db.execute("UPDATE task_journal SET state='completed' WHERE role_id=? AND task_id=?",(rid,route.successor_task_id))
        db.execute('UPDATE role_positions SET map_id=?,x=?,y=? WHERE role_id=?',(*current.position,rid))
        db.execute('UPDATE position_versions SET version=1 WHERE role_id=?',(rid,))
        bind_map_instance_transaction(db,1111,rid,epoch,current)
        for action in ('offer','accept'):
            actor,state=load_task_state(db,1111,rid,epoch)
            apply_task_plan(db,actor,TaskDomain(resources).plan(actor,state,action,100110),'first-contract:'+action)
        legacy=attribute_snapshot_if_initialized(db,1111,rid,epoch)
        caps=resource_caps_from_projection(current_equipment_totals(db,1111,rid,epoch,
            inv.immutable_snapshot_transaction(db,epoch=epoch),store.equipment_attribute_rules))
        migrate_role_resources(db,1111,rid,epoch,legacy.vitals,caps,origin='explicit_migration',
            migration_id='first-contract-resource-fixture',rules=store.resource_rules,
            equipment_rules=store.equipment_attribute_rules)
    source=MapOwner(current.address,catalog,capacity=1,transfer_capacity=8,mailbox_capacity=8)
    target=MapOwner(rules.target_address,catalog,capacity=4,transfer_capacity=8,mailbox_capacity=8,maze=maze_grids()[1006])
    source.join(current);generation=source.inspect_lifecycle(0).owner_generation
    scene=NpcScene(current.address,placements[1501],catalog,interaction_radius=32,binding_capacity=1)
    key=(1501<<32)|npc.placement_id;scene.bind(key,npc.placement_id)
    def proof(at,request):
        return scene.interact(struct.pack('>q',key),current,current,request_id=request,now_ms=at,deadline_ms=999999)
    participant=Participant(rid,epoch,1,7,role['name'],role['shape'],role['level'],
        Fighter(1,0,hp=100,max_hp=100,mp=50,max_mp=50,attack=25,defense=5,speed=10))
    with closing(store.leased(1111,rid,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        ticket=open_task_battle_dialogue(db,1111,rid,epoch,resources,fixture,100110,proof(10,'contract-npc'),current,
            generation=1,now_ms=11,deadline_ms=500).ticket
        admission=admit_task_battle_transaction(db,1111,rid,epoch,resources,fixture,ticket,
            TaskBattleRequest(100110,key),current,participant,'first-return-contract',generation=1,now_ms=12)
        assert admission.plan['ai_id']==8002
    terminal=BattleFinished('first-return-contract',SETTLEMENT_PREFIX+'first-return-contract',rid,0,True,2,
        fixture.engine_revision,epoch,7,scope=TASK_BATTLE_SCOPE,task_event_eligible=True,outcome='victory')
    rewards=dict(growth_rules=store.growth_rules,attribute_rules=store.attribute_rules,
        currency_rules=store.currency_rules,pet_experience_rules=store.task_pet_experience_rules,
        resource_rules=store.resource_rules,equipment_rules=store.equipment_attribute_rules)
    before=snapshot(store)
    try:
        with closing(store.leased(1111,rid,epoch).connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            settled=settle_task_battle_transaction(db,1111,rid,epoch,resources,fixture,terminal,inv,**rewards)
            assert 100111 not in load_task_state(db,1111,rid,epoch)[1].active
            assert reconcile_dream_return_successor_transaction(db,1111,rid,epoch,resources,rules,100110)==(100111,)
            encode_scenario_state(100111,2**40)
    except struct.error:pass
    else:raise AssertionError('Contract settlement/continuation late-encoding rollback did not run')
    assert snapshot(store)==before
    with closing(store.leased(1111,rid,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        settled=settle_task_battle_transaction(db,1111,rid,epoch,resources,fixture,terminal,inv,**rewards)
        assert reconcile_dream_return_successor_transaction(db,1111,rid,epoch,resources,rules,100110)==(100111,)
        assert reconcile_dream_return_successor_transaction(db,1111,rid,epoch,resources,rules,100110)==()
        prior=read_completed_task_battle_proof(db,1111,rid,epoch,resources,rules.battles,100110)
    # Original AI8002 targets Lu Liding10084, while return targets Huang10085.
    # This is a separate explicit approach fixture, not claimed navigation.
    source.leave(current)
    return_npc=next(p for p in placements[1501] if p.npc_id==10085)
    current=replace(current,version=current.version+1,x=return_npc.x,y=return_npc.y)
    assert store.save_checkpoint(1111,rid,epoch,current.position,current.version)
    with closing(store.leased(1111,rid,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE');bind_map_instance_transaction(db,1111,rid,epoch,current)
    source.join(current)
    scene=NpcScene(current.address,placements[1501],catalog,interaction_radius=32,binding_capacity=1)
    key=(1501<<32)|return_npc.placement_id;scene.bind(key,return_npc.placement_id)
    with closing(store.leased(1111,rid,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        def open_menu():
            return open_dream_return_transaction(db,1111,rid,epoch,resources,rules,100111,proof(100,'first-menu'),current,
                generation=1,map_generation=generation,now_ms=100)
        for sql in ("DELETE FROM task_journal WHERE role_id=? AND task_id=100111",
                "DELETE FROM task_journal WHERE role_id=? AND task_id=100110",
                "DELETE FROM task_battle_admissions WHERE role_id=? AND task_id=100110"):
            db.execute('SAVEPOINT invalid_first_context');db.execute(sql,(rid,));refuse(open_menu)
            db.execute('ROLLBACK TO invalid_first_context');db.execute('RELEASE invalid_first_context')
        opened=open_menu()
    command=decode_task_intent(C_COMMIT_SCENARIO_QUEST,struct.pack('>iQi',100111,key,0))
    with closing(store.leased(1111,rid,epoch).connect()) as db,db:
        db.execute('BEGIN')
        fresh=proof(101,'first-commit')
        raw=inspect_return_commit_transaction(db,1111,rid,epoch,resources,rules.dialogue,opened.ticket,command,fresh,current,
            generation=1,map_generation=generation,now_ms=101)
        permit=resolve_dream_return_transaction(db,1111,rid,epoch,resources,rules,raw,command,fresh,current,
            generation=1,map_generation=generation,now_ms=101,movement_state=0)
    offer=source.prepare_transfer(current,permit.target_position,request_id=opened.ticket.request_id,
        deadline_ms=opened.ticket.deadline_ms,now_ms=102)
    world_storage.begin(store,1111,rid,epoch,offer)
    receipt=target.activate(source.freeze(target.reserve(offer,now_ms=102),now_ms=102),now_ms=102)
    with closing(store.leased(1111,rid,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE');assets=inv.immutable_snapshot_transaction(db,epoch=epoch)
        result=complete_dream_return_transaction(db,1111,rid,epoch,resources,rules,permit,receipt,inv,
            generation=1,map_generation=generation,now_ms=103,movement_state=0,**rewards)
        assert result.target.position==(1006,2720,1120) and result.completion.started_tasks==(100112,)
        assert result.completion.rewards.experience_awarded==125 and result.completion.rewards.pet_experience.amount==0
        assert inv.immutable_snapshot_transaction(db,epoch=epoch)==assets
        growth=read_growth(db,1111,rid)
    # Controlled actual World cleanup refusal AFTER durable commit. Recovery
    # must retire the old frozen source, never undo the paid public target.
    refuse(lambda:source.finalize(replace(receipt,location=replace(receipt.location,version=receipt.location.version+1))))
    assert source.location(rid)==receipt.frozen.source
    paid_before=snapshot(store)
    with closing(store.leased(1111,rid,epoch).connect()) as db,db:
        db.execute('BEGIN')
        paid=readonly(db.db,lambda:complete_dream_return_transaction(db,1111,rid,epoch,resources,rules,permit,receipt,inv,
            generation=1,map_generation=None,now_ms=opened.ticket.deadline_ms+1,movement_state=0,
            read_committed_world=world_storage.load_committed_transfer_transaction,**rewards))
        assert paid.replayed and paid.target is None and paid.completion is None
        assert not any(kind in (REFRESH_PET,REFRESH_PET_EXP) for kind,_ in paid.messages)
    assert snapshot(store)==paid_before
    epoch2=store.acquire_lease(1111,rid)
    with closing(store.leased(1111,rid,epoch2).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        decision=world_storage.prepare_transfer_recovery_transaction(db,1111,rid,epoch2,offer.transfer_id)
        assert decision.committed and decision.authority_position==(1006,2720,1120)
    for owner in (source,target):
        owner.retire_recovered_transfer(owner.inspect_transfer(rid,offer.transfer_id),decision)
        assert owner.location(rid) is None
    inv2,_,_,_=runtime_storage.load_role(store,1111,rid,epoch2,resources)
    recovered=target.join(Location(rid,epoch2,rules.target_address,decision.authority_version,*decision.authority_position[1:]))
    with closing(store.leased(1111,rid,epoch2).connect()) as db,db:
        db.execute('BEGIN')
        assert read_completed_task_battle_proof(db,1111,rid,epoch2,resources,rules.battles,100110)==prior
        assert inv2.immutable_snapshot_transaction(db,epoch=epoch2)==assets and read_growth(db,1111,rid)==growth
        assert store.position(1111,rid)==(1006,2720,1120)
        assert recovered.address==rules.target_address and source.location(rid) is None
        assert load_story_instance_transaction(db,1111,rid,epoch2,canonical,rules.dialogue.story_rules,
            expected_address=source.address).address==source.address
    assert not rules.battles.enabled_task_ids and not load_task_battle_resources(resources).enabled_task_ids
    return dict(task_contract_verified=True,actual_ai_victory_verified=False,production_reachable=False,
        task_id=100111,predecessor_id=100110,artificial_terminal_input=True,actual_battle_executed=False,
        post_commit_source_refusal_recovered=True)


def main():
    inputs=source_hashes()
    with tempfile.TemporaryDirectory(prefix='dream-return-settlement-') as folder:
        folder=Path(folder);store=AccountStore(folder/'isolated.sqlite3');runtime_storage.prepare(store)
        resources=store.task_resources;placements=load_placements();catalog=maps()
        story=load_story_instance_rules(resources,store.newbie_rules)
        puzzles=load_puzzle_resources(resources,store.newbie_rules,story,placements,policy=load_puzzle_policy())
        battles=load_task_battle_resources(resources)
        rules=load_dream_return_rules(resources,store.newbie_rules,story,placements,catalog,maze_grids(),puzzles=puzzles,battles=battles)
        assert len(rules.targets)==20 and not battles.enabled_task_ids
        policy=json.loads((OUT/'design/newbie-dream-return-v1.json').read_text(encoding='utf-8'))
        for field,value in [('dialogue_deadline_ms',True),('minimum_reading_ms',1),('coordinate_scale',1)]:
            wrong=dict(policy);wrong[field]=value;path=folder/'wrong.json';path.write_text(json.dumps(wrong),encoding='utf-8')
            refuse(lambda:load_dream_return_rules(resources,store.newbie_rules,story,placements,catalog,maze_grids(),
                puzzles=puzzles,battles=battles,path=path))
        with closing(store.connect()) as db,db:
            prepare_puzzle_storage(db);prepare_story_instance_storage(db);prepare_task_battle_storage(db);prepare_dream_return_storage(db)
        check_role(store,puzzles,9,11,100120)
        rid=store.roles(1111)[0]['id'];epoch=store.acquire_lease(1111,rid)
        inv,_,_,_=runtime_storage.load_role(store,1111,rid,epoch,resources)
        # A second actual approved puzzle completion owns a distinct directory.
        # Its inherited late-story setup is the same explicit fixture, not combat.
        check_role(store,puzzles,2,17,100719)
        other=next(r['id'] for r in store.roles(1111) if r['id']!=rid)
        other_epoch=store.acquire_lease(1111,other)
        with closing(store.leased(1111,other,other_epoch).connect()) as db,db:
            db.execute('BEGIN');other_checkpoint=load_map_instance_transaction(db,1111,other,other_epoch)
        version=store.position_version(rid)+1
        assert store.save_checkpoint(1111,rid,epoch,(1501,5464,1993),version)
        with closing(store.leased(1111,rid,epoch).connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');old=load_map_instance_transaction(db,1111,rid,epoch)
            current=Location(rid,epoch,old.address,version,5464,1993)
            bind_map_instance_transaction(db,1111,rid,epoch,current)
        source=MapOwner(current.address,catalog,capacity=1,transfer_capacity=8,mailbox_capacity=8)
        target=MapOwner(rules.target_address,catalog,capacity=4,transfer_capacity=8,mailbox_capacity=8,maze=maze_grids()[1006])
        source.join(current);generation=source.inspect_lifecycle(0).owner_generation
        scene=NpcScene(current.address,placements[1501],catalog,interaction_radius=32,binding_capacity=1)
        key=(1501<<32)|6;scene.bind(key,6)
        assert other_checkpoint.address!=current.address
        def proof(at,request):
            return scene.interact(struct.pack('>q',key),current,current,request_id=request,now_ms=at,deadline_ms=999999)
        def open_menu(db):
            return open_dream_return_transaction(db,1111,rid,epoch,resources,rules,100121,proof(100,'menu'),current,
                generation=1,map_generation=generation,now_ms=100)
        with closing(store.leased(1111,rid,epoch).connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            for sql in ("DELETE FROM task_journal WHERE role_id=? AND task_id=100121",
                    "DELETE FROM task_journal WHERE role_id=? AND task_id=100120",
                    "DELETE FROM task_prologue_puzzles WHERE role_id=? AND task_id=100120"):
                db.execute('SAVEPOINT invalid_context');db.execute(sql,(rid,));refuse(lambda:open_menu(db))
                db.execute('ROLLBACK TO invalid_context');db.execute('RELEASE invalid_context')
            opened=open_menu(db)
        ticket=opened.ticket
        # Completion, not opening, captures the selected pet.
        pet_b=inv.grant_pet(500138);inv.receive(FIGHT_PET,struct.pack('>i',pet_b))
        command=decode_task_intent(C_COMMIT_SCENARIO_QUEST,struct.pack('>iQi',100121,key,0))
        with closing(store.leased(1111,rid,epoch).connect()) as db,db:
            db.execute('BEGIN')
            fresh=proof(101,'commit')
            raw=inspect_return_commit_transaction(db,1111,rid,epoch,resources,rules.dialogue,ticket,command,fresh,current,
                generation=1,map_generation=generation,now_ms=101)
            def resolve(**change):
                args=dict(generation=1,map_generation=generation,now_ms=101,movement_state=0);args.update(change)
                return resolve_dream_return_transaction(db,1111,rid,epoch,resources,rules,raw,command,fresh,current,**args)
            permit=resolve()
            for change in (dict(now_ms=ticket.deadline_ms),dict(movement_state=1),dict(generation=2),dict(map_generation=generation+'-old')):
                refuse(lambda change=change:resolve(**change))
            for changed_proof in (replace(fresh,npc_id=10085),replace(fresh,placement_id=2),
                    replace(fresh,position_version=current.version+1),replace(fresh,role_id=other),
                    replace(fresh,address=other_checkpoint.address)):
                refuse(lambda changed_proof=changed_proof:resolve_dream_return_transaction(
                    db,1111,rid,epoch,resources,rules,raw,command,changed_proof,current,
                    generation=1,map_generation=generation,now_ms=101,movement_state=0))
            foreign=replace(current,address=other_checkpoint.address)
            refuse(lambda:resolve_dream_return_transaction(db,1111,rid,epoch,resources,rules,raw,command,
                replace(fresh,address=foreign.address),foreign,generation=1,map_generation=generation,
                now_ms=101,movement_state=0))
            db.execute('SAVEPOINT changed_revision')
            db.execute('UPDATE task_versions SET revision=revision+1 WHERE role_id=?',(rid,))
            refuse(resolve)
            db.execute('ROLLBACK TO changed_revision');db.execute('RELEASE changed_revision')
        offer=source.prepare_transfer(current,permit.target_position,request_id=ticket.request_id,
            deadline_ms=ticket.deadline_ms,now_ms=102)
        world_storage.begin(store,1111,rid,epoch,offer)
        reserved=target.reserve(offer,now_ms=102);frozen=source.freeze(reserved,now_ms=102)
        receipt=target.activate(frozen,now_ms=102)
        rewards=dict(growth_rules=store.growth_rules,attribute_rules=store.attribute_rules,
            currency_rules=store.currency_rules,pet_experience_rules=store.task_pet_experience_rules)
        def complete(db,**change):
            args=dict(generation=1,map_generation=generation,now_ms=103,movement_state=0,**rewards);args.update(change)
            return complete_dream_return_transaction(db,1111,rid,epoch,resources,rules,permit,
                args.pop('receipt',receipt),inv,**args)
        before=snapshot(store)
        try:
            with closing(store.leased(1111,rid,epoch).connect()) as db,db:
                db.execute('BEGIN IMMEDIATE');complete(db)
                # A real final native scalar encoder fails inside caller txn.
                encode_scenario_state(100121,2**40)
        except struct.error:pass
        else:raise AssertionError('Controlled final native-encoding failure did not run')
        assert snapshot(store)==before, 'World, task and original rewards did not roll back together'
        with closing(store.leased(1111,rid,epoch).connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');xp=read_experience(db,1111,rid).experience
            refuse(lambda:complete(db,receipt=replace(receipt,location=replace(receipt.location,x=receipt.location.x+1))))
            result=complete(db)
            assert result.target.address==rules.target_address and result.target.position==(1006,5360,2304)
            assert result.completion.rewards.experience_awarded==450
            assert result.completion.rewards.pet_experience.recipient_id==pet_b
            assert result.completion.rewards.pet_experience.amount==450
            assert result.completion.started_tasks==(100122,)
            assert read_experience(db,1111,rid).experience==xp+450
        source.finalize(receipt)
        paid_before=snapshot(store)
        with closing(store.leased(1111,rid,epoch).connect()) as db,db:
            db.execute('BEGIN');refuse(lambda:complete(db,now_ms=ticket.deadline_ms+1))
        assert snapshot(store)==paid_before, 'Missing public pure world reader mutated a paid operation'
        # The actual World provider is exercised under an SQLite authorizer
        # allowing SELECT/READ/FUNCTION only; no fake successful reader.
        def read_paid(db):
            # Install instrumentation on the SQLite handle; all gameplay calls
            # still cross the actual current-lease FencedConnection Adapter.
            return readonly(db.db,lambda:complete(db,now_ms=ticket.deadline_ms+1,map_generation=None,
                read_committed_world=world_storage.load_committed_transfer_transaction,
                resource_rules=store.resource_rules,equipment_rules=store.equipment_attribute_rules))
        with closing(store.leased(1111,rid,epoch).connect()) as db,db:
            db.execute('BEGIN');paid=read_paid(db)
            assert paid.replayed and paid.target is None and paid.completion is None
        assert snapshot(store)==paid_before
        # Explicit post-settlement fixture inputs change XP, selected pet and
        # original recipient growth; they are not replayed quest rewards.
        with closing(store.leased(1111,rid,epoch).connect()) as db,db:
            db.execute('BEGIN')
            pet_a=next(p.id for p in inv.immutable_snapshot_transaction(db,epoch=epoch).pets if p.id!=pet_b)
        inv.receive(FIGHT_PET,struct.pack('>i',pet_a))
        with closing(store.leased(1111,rid,epoch).connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            pet=inv.read_pet_state(db,pet_b)
            inv.change_pet_growth(db,pet_b,'later-paid-pet-fixture',pet.progress.state.version,'experience',7)
            credit_experience(db,1111,rid,7,store.growth_rules,store.attribute_rules,epoch)
            # The unique-resource contract is explicitly migrated only in this
            # disposable fixture, preserving the known actual carrier/caps.
            legacy=attribute_snapshot_if_initialized(db,1111,rid,epoch)
            caps=resource_caps_from_projection(current_equipment_totals(db,1111,rid,epoch,
                inv.immutable_snapshot_transaction(db,epoch=epoch),store.equipment_attribute_rules))
            migrate_role_resources(db,1111,rid,epoch,legacy.vitals,caps,origin='explicit_migration',
                migration_id='dream-paid-resource-fixture',rules=store.resource_rules,
                equipment_rules=store.equipment_attribute_rules)
            before_resources=read_role_resources(db,1111,rid,epoch,store.resource_rules)
            changed=plan_resource_values(before_resources,max(1,before_resources.hp-7),max(0,before_resources.mp-3),
                'medicine',store.resource_rules)
            apply_resource_transition(db,1111,rid,epoch,changed,'later-paid-vitals-fixture',
                rules=store.resource_rules,equipment_rules=store.equipment_attribute_rules)
        active=target.ready(receipt.location)
        moved=target.move(MoveCommand(active,'later-dream-paid-walk',999999,0xc0faa,
            b'\0'+struct.pack('>hhQ',active.x+16,active.y,0),movement_state=0),104)
        assert not moved.rejection, moved.rejection
        walked=moved.location
        assert store.save_checkpoint(1111,rid,epoch,walked.position,walked.version)
        later_before=snapshot(store)
        with closing(store.leased(1111,rid,epoch).connect()) as db,db:
            db.execute('BEGIN')
            paid=read_paid(db)
            profile=current_resource_profile(db,1111,rid,epoch,inv.immutable_snapshot_transaction(db,epoch=epoch),
                resource_rules=store.resource_rules,equipment_rules=store.equipment_attribute_rules)
            pet=inv.read_pet_state(db,pet_b)
            expected=((S_REFRESH_USER_EXP,encode_user_experience(read_experience(db,1111,rid).experience)),
                growth_refresh(read_growth(db,1111,rid),profile),
                (REFRESH_PET,pet_record(pet.__dict__)),(REFRESH_PET_EXP,struct.pack('>iQ',pet.id,pet.progress.state.experience)))
            assert paid.messages==expected
            assert (profile.vitals.hp,profile.vitals.mp)==(changed.after.hp,changed.after.mp)
            assert paid.current_position.position==walked.position and paid.current_position.version==walked.version
            assert paid.target is None and paid.completion is None
        assert snapshot(store)==later_before, 'Paid current result changed a later position, HP, pet or reward record'
        with closing(store.leased(1111,other,other_epoch).connect()) as db,db:
            db.execute('BEGIN')
            assert load_map_instance_transaction(db,1111,other,other_epoch)==other_checkpoint
            other_state=load_task_state(db,1111,other,other_epoch)[1]
            assert 100720 in other_state.active and 100121 not in other_state.completed
        checkpoint=store.position(1111,rid)
        with closing(store.leased(1111,rid,epoch).connect()) as db,db:
            db.execute('BEGIN')
            paid_assets=(read_experience(db,1111,rid),read_growth(db,1111,rid),
                inv.immutable_snapshot_transaction(db,epoch=epoch))
        epoch2=store.acquire_lease(1111,rid)
        inv2,_,_,_=runtime_storage.load_role(store,1111,rid,epoch2,resources)
        assert store.position(1111,rid)==checkpoint==walked.position
        with closing(store.leased(1111,rid,epoch2).connect()) as db,db:
            db.execute('BEGIN');state=load_task_state(db,1111,rid,epoch2)[1]
            assert 100121 in state.completed and 100122 in state.active
            assert paid_assets==(read_experience(db,1111,rid),read_growth(db,1111,rid),
                inv2.immutable_snapshot_transaction(db,epoch=epoch2))
            assert db.execute('SELECT COUNT(*) FROM task_dream_returns WHERE role_id=?',(rid,)).fetchone()==(1,)
            historical,current_checkpoint=readonly(db.db,lambda:world_storage.load_committed_transfer_transaction(
                db,1111,rid,epoch2,receipt))
            assert historical==receipt and current_checkpoint.position==walked.position
            readonly(db.db,lambda:refuse(lambda:complete_dream_return_transaction(
                db,1111,rid,epoch2,resources,rules,permit,receipt,inv2,generation=1,map_generation=None,
                now_ms=ticket.deadline_ms+1,movement_state=0,
                read_committed_world=world_storage.load_committed_transfer_transaction,
                resource_rules=store.resource_rules,equipment_rules=store.equipment_attribute_rules)))
        first_contract=check_first_family_contract(store,rules,placements,catalog)
    assert source_hashes()==inputs, 'A task/World/asset input changed during isolated verification'
    report=dict(passed=['Strict formal loader freezes20 tasks/two exact normal public targets; malformed policy refuses',
        'Second-family missing active, missing completed predecessor and missing approved puzzle receipt independently refuse',
        'Fresh real NPC/route/private directory/generation deadline resolves an approved permit from unmodified raw intent',
        'Independent wrong NPC/placement/role/version/revision and foreign owned private directory refuse; other role stays unchanged',
        'Late final native encoding failure rolls back world, task and rewards across all tables',
        'Second-family450/450 uses pet selected at completion, exact public target and only original successor active0',
        'Missing pure world reader refuses; actual public World provider plus SQL authorizer proves paid current XP/HP/original pet after switching and later movement without writes or scene/task replay; new lease keeps current target/assets/one receipt',
        'First-family explicit task contract uses public admit/settle/proof and atomic continuation, independent missing active/predecessor/receipt refusals, original125/pet0 and unchanged assets after new lease'],
        first_family_task_contract_verified=True,first_family_actual_ai_victory_verified=False,
        first_family_production_reachable=False,first_family=first_contract,
        task_contract_verified=True,actual_ai_victory_verified=False,production_reachable=False,
        paid_current_result_verified=True,
        migrated_task_battle_settlement_verified=True,source_sha256=inputs,inputs_stable=True,
        source_after_commit_failure_recovery='actual World finalize rejects a deliberately stale receipt after commit; new lease retires both old memberships and rejoins exact paid public target with assets unchanged; shared transport failure not simulated',
        fixtures=['Inherited explicit late-story puzzle/master journal and exact private NPC approach; no formal battle',
            'Explicit post-settlement XP/pet growth and known-carrier resource migration/value transition fixture; not gameplay, medicine use or combat',
            '32px NpcScene is an isolated proof fixture, not deployed v2 or GUI'],
        shared_runtime_wired=False,native_gui_verified=False,live_server_changed=False,battle_executed=False)
    write_json(OUT/'evidence/task-prologue-return-verification.json',report);print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':main()
