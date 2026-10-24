"""Natural frozen prefix + explicit Task candidate + real dedicated engine.

No listener or real save. The Task completion contract consumes a genuine
engine terminal; full battle resource/outbox persistence is main's separate
integration check. Candidate modules/config are copied before any imports.
"""
import argparse
import asyncio
from contextlib import closing
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import struct
import sys
import tempfile


def refused(call):
    try:call()
    except ValueError:return
    raise AssertionError('Invalid local teaching compatibility accepted')


def main(*,after_teaching_check=None,extra_sources=(),extra_policies=()):
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args();base=args.source.resolve();report=args.report.resolve()
    workspace=Path(__file__).resolve().parent
    if base in report.parents:raise ValueError('Report must be outside the frozen release')
    selected=('role_skills.py','task_first_skill.py','task_domain.py','task_battle.py','task_first_battle.py',
        'task_pve.py','verify_master_commit_card_runtime.py','research_first_master_dialogue_end.py',
        'verify_world_committed_transfer_read.py')+tuple(extra_sources)
    policies=('newbie-first-skill-v1.json','local-prologue-other-skills-baseline-v1.json','task-pve-ai8001-v1.json')+tuple(extra_policies)
    h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory(prefix='local-teaching-candidate-') as folder:
        layer=Path(folder)/'candidate';layer.mkdir();(layer/'design').mkdir()
        before={}
        for name in selected:
            shutil.copy2(workspace/name,layer/name);before[name]=h(layer/name)
        for name in policies:
            shutil.copy2(workspace/'design'/name,layer/'design'/name);before['design/'+name]=h(layer/'design'/name)
        sys.path.insert(0,str(base));sys.path.insert(0,str(layer))
        import inspect_client
        inspect_client.ROOT=workspace.parent;inspect_client.OUT=base
        from accounts import AccountStore
        from game_runtime import GameRuntime
        import runtime_storage
        import verify_newbie_cart_runtime
        from verify_master_commit_card_runtime import check as native_master
        from verify_prologue_touch_runtime import check as natural_prefix
        from verify_runtime import Peer
        from world_newbie import load_newbie_routes,check_birth_site
        from world_catalog import maps,maze_grids
        from world_owner import Location
        from world_entity_protocol import VISIT_NPC
        from world_movement import ROLE_MOVE,ROLE_STOP
        from task_persistence import load_task_state
        from task_first_battle import load_first_battle_rules,open_first_battle_transaction,admit_first_battle_transaction
        from task_battle import prepare_task_battle_storage,load_task_battle_resources,settle_task_battle_transaction
        from task_battle_protocol import TaskBattleRequest
        from task_first_skill import (load_first_skill_rules,prepare_first_skill_storage,reconcile_first_skill_successor_transaction,
            open_first_skill_transaction,complete_first_skill_transaction)
        from role_skills import (prepare_other_skill_storage,load_local_prologue_baseline_rules,read_other_skills,
            read_local_prologue_baseline_receipt,grant_other_skill)
        from role_equipment_storage import current_equipment_projection
        from battle_owner import Participant
        from battle import Fighter
        from task_pve import TaskPveBattle,load_task_pve_rules
        import battle_protocol as bp
        from task_session import decode_task_intent
        from task_protocol import C_COMMIT_SCENARIO_QUEST
        from progression import read_experience,credit_experience
        from role_skills import enroll_local_prologue_other_skills
        from task_dialog_protocol import S_REFRESH_USER_EXP,encode_user_experience
        from role_attribute_protocol import growth_refresh
        from task_growth_resources import current_task_resource_profile
        from role_attribute_storage import attribute_snapshot_if_initialized
        from role_growth import read_growth
        from role_skills import other_skill_messages
        from verify_world_committed_transfer_read import readonly
        from wire import compact
        for name in selected:
            module=sys.modules.get(Path(name).stem)
            if module is not None:assert Path(module.__file__).resolve()==layer/name,name
        assert Path(runtime_storage.__file__).resolve().parent==base
        verify_newbie_cart_runtime.master_prefix=native_master
        store=AccountStore(Path(folder)/'disposable.sqlite3');prepared=runtime_storage.prepare(store)
        resources=store.task_resources
        with closing(store.connect()) as db:
            prepare_other_skill_storage(db);prepare_task_battle_storage(db);prepare_first_skill_storage(db)
        first=load_first_skill_rules(resources,store.newbie_rules,store.story_instance_rules,store.npc_resources[0],
            path=layer/'design/newbie-first-skill-v1.json')
        policy=load_local_prologue_baseline_rules(layer/'design/local-prologue-other-skills-baseline-v1.json',
            attribute_rules=store.attribute_rules,growth_rules=store.growth_rules,currency_rules=store.currency_rules)
        pve=load_task_pve_rules(layer/'design/task-pve-ai8001-v1.json')
        registry=load_task_battle_resources(resources,enabled_task_ids=pve.enabled_task_ids,engine_revision=pve.revision)
        gate=load_first_battle_rules(resources,store.newbie_rules,store.story_instance_rules,registry,
            store.npc_resources[0],path=layer/'design/task-pve-ai8001-v1.json')
        route=load_newbie_routes()[(9,11)]
        witness=next(r for r in json.loads((base/'evidence/newbie-birth-sites-audit.json').read_text(encoding='utf8'))['routes']
            if (r['character_id'],r['school_id'])==(9,11))
        # Reproduce a role actually created by the old local configuration.
        # No ledger is deleted or a journal/profile manually seeded. Newer BASE
        # AccountStore legitimately authorizes empty skills for new creation;
        # disable only that creation capability for this historical-role case.
        creation_skills=getattr(store,'other_skill_rules',None)
        store.other_skill_rules=None
        try:role=store.create_role(1111,'自然旧序章教学',11,1010109)
        finally:store.other_skill_rules=creation_skills
        rid=role['id']

        async def run():
            prefix=await natural_prefix(store,prepared,role,route,witness)
            runtime=GameRuntime(store,prepared,prologue_touch=True)
            try:
                peer=Peer(runtime);await peer.login(role);owner=runtime.roles[rid];epoch=owner.epoch
                walk=check_birth_site(replace(route,home_map_id=1501,first_npc_id=10908,
                    cinematic_endpoint=owner.position.value),maps(),maze_grids()[1501],store.npc_resources[0][1501],
                    state_byte=0,interaction_allowed=store.npc_interaction_rules.allows,max_visited=100000)
                assert walk.status=='reachable';path=walk.path
                await peer.request(ROLE_MOVE,struct.pack('>hhhhQ',*path[0],*path[-1],0))
                await peer.request(ROLE_STOP,compact(len(path))+b''.join(struct.pack('>hh',*point) for point in path)
                    +struct.pack('>hhQ',*path[-1],0))
                target=runtime.map(owner.map_address)
                projection=(await target.mailbox.call('inspect_lifecycle',runtime.story_maps.now())).owner_generation
                key=(1501<<32)|10
                proof,current=await target.mailbox.call('npc',rid,epoch,owner.position.version,struct.pack('>q',key),
                    request_id='local-teaching-actual-map-proof',deadline=asyncio.get_running_loop().time()+30)
                generation=runtime.connections[rid].generation;inv=owner.inventory
                rewards=dict(growth_rules=store.growth_rules,attribute_rules=store.attribute_rules,currency_rules=store.currency_rules,
                    pet_experience_rules=store.task_pet_experience_rules,resource_rules=store.resource_rules,
                    equipment_rules=store.equipment_attribute_rules)
                with closing(store.leased(1111,rid,epoch).connect()) as db,db:
                    db.execute('BEGIN IMMEDIATE')
                    assert read_other_skills(db,1111,rid,epoch,first.skills) is None
                    actor,_=load_task_state(db,1111,rid,epoch)
                    profile=current_equipment_projection(db,1111,rid,epoch,inv.immutable_snapshot_transaction(db,epoch=epoch),
                        store.equipment_attribute_rules)
                    attrs=profile.attributes;vitals=profile.vitals
                    participant=Participant(rid,epoch,generation,attrs.growth_revision+1,role['name'],actor.shape,actor.level,
                        Fighter(1,0,hp=vitals.hp,max_hp=vitals.max_hp,mp=vitals.mp,max_mp=vitals.max_mp,
                            attack=attrs.physical_attack,defense=attrs.physical_defense,speed=attrs.speed))
                    engine=TaskPveBattle(participant,pve,registry.definitions[100107],clock=lambda:0)
                    opened=open_first_battle_transaction(db,1111,rid,epoch,resources,gate,100107,proof,current,
                        generation=generation,map_generation=projection,now_ms=10,deadline_ms=1000,movement_state=0)
                    admit_first_battle_transaction(db,1111,rid,epoch,resources,gate,opened.ticket,TaskBattleRequest(100107,key),
                        proof,current,participant,engine.id,generation=generation,map_generation=projection,now_ms=11,movement_state=0)
                engine.opening();rounds=0
                while engine.finished() is None:
                    rounds+=1;assert rounds<=10
                    engine.receive(bp.SEND_ACTION,bytes.fromhex('0000000100000015000000000100'))
                    assert engine.finished() is None
                    engine.receive(bp.CLIENT_PLAY_END,b'\0')
                terminal=engine.finished();assert terminal.won and terminal.revision==pve.revision
                with closing(store.leased(1111,rid,epoch).connect()) as db,db:
                    db.execute('BEGIN IMMEDIATE')
                    settle_task_battle_transaction(db,1111,rid,epoch,resources,registry,terminal,inv,**rewards)
                    assert reconcile_first_skill_successor_transaction(db,1111,rid,epoch,resources,first,100107)==(100179,)
                    before_exp=read_experience(db,1111,rid).experience
                    def opening(*,enabled=policy):
                        return open_first_skill_transaction(db,1111,rid,epoch,resources,first,100179,proof,current,
                            generation=generation,map_generation=projection,now_ms=1000,movement_state=0,baseline_policy=enabled)
                    refused(lambda:opening(enabled=None))
                    db.execute('SAVEPOINT invalid_creation')
                    db.execute("UPDATE role_restoration_origins SET creation_profile='{}' WHERE role_id=?",(rid,))
                    refused(opening)
                    db.execute('ROLLBACK TO invalid_creation');db.execute('RELEASE invalid_creation')
                    db.execute('SAVEPOINT already_paid')
                    db.execute('INSERT INTO task_reward_channels VALUES(?,?,?,?,?)',(rid,100179,'character_exp','0'*64,'{}'))
                    refused(opening)
                    db.execute('ROLLBACK TO already_paid');db.execute('RELEASE already_paid')
                    rejected_reward_corruptions=[]
                    for corruption in ('missing','null'):
                        db.execute('SAVEPOINT corrupt_prefix_reward')
                        if corruption=='missing':
                            db.execute("DELETE FROM task_reward_channels WHERE role_id=? AND task_id=100105 AND channel='character_exp'",(rid,))
                        else:
                            db.execute("UPDATE task_reward_channels SET receipt='null' WHERE role_id=? AND task_id=100105 AND channel='character_exp'",(rid,))
                        refused(opening)
                        rejected_reward_corruptions.append(corruption)
                        db.execute('ROLLBACK TO corrupt_prefix_reward');db.execute('RELEASE corrupt_prefix_reward')
                    db.execute('SAVEPOINT lost_receipt')
                    commands=tuple(db.execute('SELECT request_id,receipt FROM task_command_receipts WHERE role_id=?',(rid,)))
                    source=next(name for name,encoded in commands if json.loads(encoded)['effect_id']==f'task:{rid}:100105')
                    db.execute('DELETE FROM task_command_receipts WHERE role_id=? AND request_id=?',(rid,source))
                    refused(opening)
                    db.execute('ROLLBACK TO lost_receipt');db.execute('RELEASE lost_receipt')
                    changes=db.execute('SELECT total_changes()').fetchone()[0]
                    menu=opening()
                    assert db.execute('SELECT total_changes()').fetchone()[0]==changes
                    assert menu.ticket.skill_revision is None
                    assert read_other_skills(db,1111,rid,epoch,first.skills) is None
                command=decode_task_intent(C_COMMIT_SCENARIO_QUEST,struct.pack('>iQi',100179,key,0))
                def complete(db):
                    return complete_first_skill_transaction(db,1111,rid,epoch,resources,first,menu.ticket,command,inv,
                        proof=proof,location=current,generation=generation,map_generation=projection,now_ms=2001,
                        movement_state=0,baseline_policy=policy,**rewards)
                with closing(store.connect()) as db:
                    db.execute('''CREATE TRIGGER probe_teaching_late_fault BEFORE INSERT ON task_first_skills
                        BEGIN SELECT RAISE(ABORT,'late teaching receipt failure'); END''')
                try:
                    with closing(store.leased(1111,rid,epoch).connect()) as db,db:
                        db.execute('BEGIN IMMEDIATE');complete(db)
                except sqlite3.DatabaseError:pass
                else:raise AssertionError('Late teaching failure did not execute')
                with closing(store.leased(1111,rid,epoch).connect()) as db,db:
                    db.execute('BEGIN')
                    assert read_other_skills(db,1111,rid,epoch,first.skills) is None
                    assert read_local_prologue_baseline_receipt(db,1111,rid,epoch,first.skills,policy) is None
                    assert read_experience(db,1111,rid).experience==before_exp
                with closing(store.connect()) as db:db.execute('DROP TRIGGER probe_teaching_late_fault')
                next_check={}
                with closing(store.leased(1111,rid,epoch).connect()) as db,db:
                    db.execute('BEGIN IMMEDIATE');result=complete(db)
                    assert result.skills.origin=='designed_local_prologue_baseline' and result.skills.entries==((100008,1),)
                    state=load_task_state(db,1111,rid,epoch)[1]
                    assert 100179 in state.completed and 100190 in state.active
                    assert result.completion.rewards.experience_awarded==120
                    receipt=read_local_prologue_baseline_receipt(db,1111,rid,epoch,first.skills,policy)
                    assert receipt.permit.creation_id and receipt.permit.original_epoch==epoch
                if after_teaching_check is not None:
                    next_check=after_teaching_check(store,first,proof,current,generation,projection,inv)
                with closing(store.leased(1111,rid,epoch).connect()) as db,db:
                    db.execute('BEGIN IMMEDIATE')
                    later=grant_other_skill(db,1111,rid,epoch,first.skills,100009,3,expected_revision=result.skills.revision)
                    credit_experience(db,1111,rid,5,store.growth_rules,store.attribute_rules,epoch)
                with closing(store.connect()) as db,db:
                    db.execute('BEGIN')
                    paid=readonly(db,lambda:complete(db))
                    assert paid.replayed and paid.completion is None and paid.skills==later
                    actor,_=load_task_state(db,1111,rid,epoch)
                    profile=current_task_resource_profile(db,actor,inv,store.resource_rules,store.equipment_attribute_rules)
                    if profile is None:profile=attribute_snapshot_if_initialized(db,1111,rid,epoch)
                    expected=((S_REFRESH_USER_EXP,encode_user_experience(read_experience(db,1111,rid).experience)),)+(
                        (growth_refresh(read_growth(db,1111,rid),profile),) if profile is not None else ())+other_skill_messages(later,first.skills)
                    assert paid.messages==expected
                    replayed=readonly(db,lambda:enroll_local_prologue_other_skills(db,1111,rid,epoch,first.skills,policy,receipt.permit))
                    assert replayed==later
                return dict(next_check=next_check,natural_prefix=prefix,real_task_pve_engine_victory=True,engine_rounds=rounds,
                    explicit_snapshot_version_fixture=True,battle_resource_and_outbox_consumer_verified=False,
                    old_local_role_unknown_before_commit=True,explicit_old_creation_configuration=True,enrollment_on_visit=False,
                    original_teaching_reward=120,original_successor=100190,late_failure_keeps_baseline_unknown=True,
                    missing_policy_creation_or_command_and_paid_reward_refused=True,
                    prefix_reward_corruptions_refused=rejected_reward_corruptions,
                    paid_after_later_skill_and_growth_is_pure_current=True,
                    shared_runtime_wired=False,actual_human_role_eligibility_verified=False,native_gui_verified=False)
            finally:await runtime.close()
        result=asyncio.run(asyncio.wait_for(run(),90))
        assert before=={name:h(layer/name) for name in before}
        result.update(candidate_sources=before,base=str(base),database='new disposable only',live_server_changed=False)
        report.parent.mkdir(parents=True,exist_ok=True);report.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
        print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
