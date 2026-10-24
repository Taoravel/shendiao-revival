"""Disposable creation/ledger/teaching contracts; artificial terminals, no AI."""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
import hashlib
import importlib
import json
import sqlite3
import struct
import tempfile
from accounts import AccountStore
from inspect_client import OUT,write_json
import runtime_storage
from role_skills import (load_other_skill_rules,prepare_other_skill_storage,authorize_new_role_other_skills,
    VerifiedOtherSkillBaseline,adopt_verified_other_skills,read_other_skills,grant_other_skill,other_skill_messages)
from task_first_skill import (load_first_skill_rules,prepare_first_skill_storage,reconcile_first_skill_successor_transaction,
    open_first_skill_transaction,complete_first_skill_transaction)
from task_domain import TaskDomain,TaskEvidence,PROLOGUE_FIRST_SKILL_IDS
from task_persistence import load_task_state,apply_task_plan
from task_newbie_chapter import read_newbie_chapter
from task_protocol import C_COMMIT_SCENARIO_QUEST,encode_scenario_state,S_ACCEPT_SCENARIO_QUEST
from task_session import decode_task_intent
from task_battle import (load_task_battle_resources,prepare_task_battle_storage,open_task_battle_dialogue,
    admit_task_battle_transaction,settle_task_battle_transaction,TASK_BATTLE_SCOPE,SETTLEMENT_PREFIX)
from task_battle_protocol import TaskBattleRequest
from battle_owner import Participant
from battle import Fighter
from training_battle import BattleFinished
from world_owner import MapAddress,Location,MapOwner
from world_npcs import load_placements,NpcScene
from world_catalog import maps
from world_story_instances import load_story_instance_rules,StoryInstanceIntent,allocate_story_instance_transaction
from world_transfer_storage import bind_map_instance_transaction
from progression import credit_experience,read_experience
from role_growth import read_growth,GrowthResourceContext
from role_attribute_storage import attribute_snapshot_if_initialized
from role_attribute_protocol import growth_refresh
from task_growth_resources import current_task_resource_profile
from task_dialog_protocol import S_REFRESH_USER_EXP,encode_user_experience
from role_equipment_storage import current_equipment_totals
from role_equipment import resource_caps_from_projection
from role_resource_storage import migrate_role_resources
from verify_task_prologue_puzzle import snapshot
from verify_world_committed_transfer_read import readonly
from research_other_skill_snapshot import native_other_skills
from battle_protocol import other_skills


def refuse(action):
    try:action()
    except ValueError:return
    raise AssertionError('Unsupported first-skill authority accepted')


def source_hashes():
    names=('role_skills','task_first_skill','task_domain','task_battle','task_chains','task_workflow',
        'task_rewards','role_growth','role_resource_storage','role_equipment_storage','runtime_storage','accounts',
        'world_story_instances','world_transfer_storage','battle_protocol','verify_task_first_skill',
        'research_other_skill_snapshot','research_battle')
    result={n:hashlib.sha256(Path(importlib.import_module(n).__file__).read_bytes()).hexdigest() for n in names}
    for name in ('design/newbie-first-skill-v1.json',)+tuple('catalogs/knight.gsp.skill.'+n+'.json' for n in
            ('cskillitem','cskillshowlist','cskillshowlistclient')):
        result[name]=hashlib.sha256((OUT/name).read_bytes()).hexdigest()
    return result


def check_creation(store,rules):
    before=snapshot(store)
    try:
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            rid=db.execute("INSERT INTO roles(account_id,name,school,shape) VALUES(1111,'技能新建',11,1010109)").lastrowid
            first=authorize_new_role_other_skills(db,1111,rid,'actual-new-role-transaction-fixture',rules)
            assert first.entries==() and first.origin=='new_role_creation'
            raise RuntimeError('creation rollback')
    except RuntimeError:pass
    assert snapshot(store)==before
    with closing(store.connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        rid=db.execute("INSERT INTO roles(account_id,name,school,shape) VALUES(1111,'技能新建',11,1010109)").lastrowid
        authorize_new_role_other_skills(db,1111,rid,'actual-new-role-transaction-fixture',rules)
    epoch=store.acquire_lease(1111,rid)
    with closing(store.leased(1111,rid,epoch).connect()) as db,db:
        db.execute('BEGIN')
        assert read_other_skills(db,1111,rid,epoch,rules).entries==()
        refuse(lambda:authorize_new_role_other_skills(db,1111,rid,'retroactive-new-role',rules))
        for entries in (((600005,1),),((100008,0),),((100008,True),),((100007,1),(100007,2))):
            refuse(lambda:adopt_verified_other_skills(db,1111,rid,epoch,rules,
                VerifiedOtherSkillBaseline(entries,'invalid-complete-fixture','0'*64)))
        refuse(lambda:other_skill_messages(None,rules))


def check_role(store,rules,character,school,q,entries):
    resources=store.task_resources
    # Historical complete-baseline contract fixtures predate the new creation
    # hook. Select that explicit old creation configuration, never delete a
    # real role's newly authorized known ledger to manufacture UNKNOWN.
    creation_skills=getattr(store,'other_skill_rules',None)
    store.other_skill_rules=None
    try:role=store.create_role(1111,'首技'+str(character),school,1010100+character)
    finally:store.other_skill_rules=creation_skills
    rid=role['id'];epoch=store.acquire_lease(1111,rid)
    with closing(store.leased(1111,rid,epoch).connect()) as db,db:
        db.execute('BEGIN')
        assert read_other_skills(db,1111,rid,epoch,rules.skills) is None
        refuse(lambda:grant_other_skill(db,1111,rid,epoch,rules.skills,100008,1,expected_revision=0))
        refuse(lambda:authorize_new_role_other_skills(db,1111,rid,'old-chapter-is-not-empty',rules.skills))
        # Each wrong namespace must fail on an UNKNOWN ledger, so an existing
        # baseline-conflict check cannot hide a missing namespace validator.
        for other_map_key in (350001,600018,700001,600005):
            refuse(lambda:adopt_verified_other_skills(db,1111,rid,epoch,rules.skills,
                VerifiedOtherSkillBaseline(((other_map_key,1),),'wrong-native-container','2'*64)))
            assert read_other_skills(db,1111,rid,epoch,rules.skills) is None
        baseline=adopt_verified_other_skills(db,1111,rid,epoch,rules.skills,
            VerifiedOtherSkillBaseline(entries,'explicit-complete-other-wire-fixture-'+str(character),'1'*64))
        changes=db.execute('SELECT total_changes()').fetchone()
        for other_map_key in (350001,600018,700001,600005):
            refuse(lambda:grant_other_skill(db,1111,rid,epoch,rules.skills,other_map_key,1,
                expected_revision=baseline.revision))
        assert db.execute('SELECT total_changes()').fetchone()==changes
    inv,_,spawn,version=runtime_storage.load_role(store,1111,rid,epoch,resources)
    route=store.newbie_rules.routes[(character,school)]
    intro=Location(rid,epoch,MapAddress(spawn[0],spawn[0],0),version,*spawn[1:])
    playback=runtime_storage.newbie_playback(store,1111,rid,epoch,intro,1,'first-skill-intro',1)
    runtime_storage.newbie_finish(store,1111,rid,epoch,struct.pack('>i',route.intro_movie_id),intro,1,2,playback.ticket,inv)
    before_q=resources.definitions[q]['incoming_ids'][0]
    fixture=load_task_battle_resources(resources,enabled_task_ids=frozenset({before_q}),
        engine_revision='isolated-first-skill-contract-v1')
    assert fixture.definitions[before_q].ai_id==8001 and not rules.battles.enabled_task_ids
    with closing(store.leased(1111,rid,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE');origin=read_newbie_chapter(db,1111,rid,epoch,store.newbie_rules).origin
        canonical=StoryInstanceIntent(origin.chapter_id,origin.creation_id,origin.policy,origin.route_fingerprint,
            rules.story_rules.source_tasks[(character,school)])
        address=allocate_story_instance_transaction(db,1111,rid,epoch,canonical,rules.story_rules).address
        current=Location(rid,epoch,address,1,1049,1559)
        # Explicit historical master/approach fixture, never claimed natural play.
        db.execute("UPDATE task_journal SET state='completed' WHERE role_id=? AND task_id=?",(rid,route.successor_task_id))
        db.execute('UPDATE role_positions SET map_id=?,x=?,y=? WHERE role_id=?',(*current.position,rid))
        db.execute('UPDATE position_versions SET version=1 WHERE role_id=?',(rid,))
        bind_map_instance_transaction(db,1111,rid,epoch,current)
        for action in ('offer','accept'):
            actor,state=load_task_state(db,1111,rid,epoch)
            apply_task_plan(db,actor,TaskDomain(resources).plan(actor,state,action,before_q),'first-skill-contract:'+action)
        legacy=attribute_snapshot_if_initialized(db,1111,rid,epoch)
        caps=resource_caps_from_projection(current_equipment_totals(db,1111,rid,epoch,
            inv.immutable_snapshot_transaction(db,epoch=epoch),store.equipment_attribute_rules))
        migrate_role_resources(db,1111,rid,epoch,legacy.vitals,caps,origin='explicit_migration',
            migration_id='first-skill-explicit-known-resource-fixture',rules=store.resource_rules,
            equipment_rules=store.equipment_attribute_rules)
    owner=MapOwner(address,maps(),capacity=1,transfer_capacity=8,mailbox_capacity=8);owner.join(current)
    map_gen=owner.inspect_lifecycle(0).owner_generation
    scene=NpcScene(address,load_placements()[1501],maps(),interaction_radius=32,binding_capacity=1)
    key=(1501<<32)|10;scene.bind(key,10)
    def proof(at):return scene.interact(struct.pack('>q',key),current,current,
        request_id='first-skill-npc-'+str(at),now_ms=at,deadline_ms=999999)
    rewards=dict(growth_rules=store.growth_rules,attribute_rules=store.attribute_rules,currency_rules=store.currency_rules,
        pet_experience_rules=store.task_pet_experience_rules,resource_rules=store.resource_rules,
        equipment_rules=store.equipment_attribute_rules)
    participant=Participant(rid,epoch,1,7,role['name'],role['shape'],role['level'],
        Fighter(1,0,hp=100,max_hp=100,mp=50,max_mp=50,attack=25,defense=5,speed=10))
    battle_id='first-skill-contract-'+str(character)
    with closing(store.leased(1111,rid,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        opened=open_task_battle_dialogue(db,1111,rid,epoch,resources,fixture,before_q,proof(10),current,
            generation=1,now_ms=11,deadline_ms=500)
        admit_task_battle_transaction(db,1111,rid,epoch,resources,fixture,opened.ticket,TaskBattleRequest(before_q,key),
            current,participant,battle_id,generation=1,now_ms=12)
    terminal=BattleFinished(battle_id,SETTLEMENT_PREFIX+battle_id,rid,0,True,2,fixture.engine_revision,epoch,7,
        scope=TASK_BATTLE_SCOPE,task_event_eligible=True,outcome='victory')
    with closing(store.leased(1111,rid,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        settle_task_battle_transaction(db,1111,rid,epoch,resources,fixture,terminal,inv,**rewards)
        assert q not in load_task_state(db,1111,rid,epoch)[1].active
        assert reconcile_first_skill_successor_transaction(db,1111,rid,epoch,resources,rules,before_q)==(q,)
        assert read_other_skills(db,1111,rid,epoch,rules.skills)==baseline,'Activation granted skill early'
    def menu(db):return open_first_skill_transaction(db,1111,rid,epoch,resources,rules,q,proof(1000),current,
        generation=1,map_generation=map_gen,now_ms=1000,movement_state=0)
    with closing(store.leased(1111,rid,epoch).connect()) as db,db:
        db.execute('BEGIN')
        for sql in ("DELETE FROM task_journal WHERE role_id=? AND task_id="+str(q),
                "DELETE FROM task_journal WHERE role_id=? AND task_id="+str(before_q),
                'DELETE FROM task_battle_admissions WHERE role_id=?','DELETE FROM role_other_skills WHERE role_id=?'):
            db.execute('SAVEPOINT invalid_first_skill');db.execute(sql,(rid,));refuse(lambda:menu(db))
            db.execute('ROLLBACK TO invalid_first_skill');db.execute('RELEASE invalid_first_skill')
        ticket=menu(db).ticket
        actor,state=load_task_state(db,1111,rid,epoch)
        refuse(lambda:TaskDomain(resources).plan(actor,state,'complete',q,
            evidence=TaskEvidence(q,rid,epoch,'npc_dialogue_completed','plain-is-not-skill',1501,10908)))
    command=decode_task_intent(C_COMMIT_SCENARIO_QUEST,struct.pack('>iQi',q,key,0))
    def complete(db,**overrides):
        kw=dict(proof=proof(2000),location=current,generation=1,map_generation=map_gen,now_ms=2000,movement_state=0,**rewards)
        kw.update(overrides)
        return complete_first_skill_transaction(db,1111,rid,epoch,resources,rules,ticket,kw.pop('command',command),inv,**kw)
    with closing(store.leased(1111,rid,epoch).connect()) as db,db:
        db.execute('BEGIN');changes=db.execute('SELECT total_changes()').fetchone()
        for bad in (dict(now_ms=1999),dict(now_ms=ticket.deadline_ms),dict(generation=2),dict(map_generation='replaced'),
                dict(movement_state=1),dict(command=replace(command,opaque=1)),dict(command=replace(command,npc_key=key+1)),
                dict(proof=replace(proof(2000),npc_id=10085)),dict(proof=replace(proof(2000),placement_id=11)),
                dict(location=replace(current,version=2,x=current.x+1))):refuse(lambda:complete(db,**bad))
        assert db.execute('SELECT total_changes()').fetchone()==changes
        db.execute('SAVEPOINT changed_skills')
        grant_other_skill(db,1111,rid,epoch,rules.skills,100009,8,expected_revision=baseline.revision)
        refuse(lambda:complete(db));db.execute('ROLLBACK TO changed_skills');db.execute('RELEASE changed_skills')
    before=snapshot(store)
    for fault in ('late_sql','late_encoding'):
        try:
            with closing(store.leased(1111,rid,epoch).connect()) as db,db:
                # Offline fault instrumentation on this temporary connection,
                # before gameplay BEGIN; the real call still uses its fence.
                if fault=='late_sql':db.db.execute("CREATE TEMP TRIGGER reject_teaching BEFORE INSERT ON task_first_skills BEGIN SELECT RAISE(ABORT,'late teaching receipt fixture'); END")
                db.execute('BEGIN IMMEDIATE')
                complete(db)
                if fault=='late_encoding':encode_scenario_state(q,2**40)
        except (sqlite3.IntegrityError,struct.error):pass
        else:raise AssertionError('Late teaching rollback not exercised')
        assert snapshot(store)==before
    with closing(store.leased(1111,rid,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE');assets=inv.immutable_snapshot_transaction(db,epoch=epoch)
        result=complete(db);skills=result.skills
        assert dict(skills.entries)[100008]==max(dict(entries).get(100008,0),1)
        assert all(dict(skills.entries)[k]==v for k,v in entries)
        assert result.completion.rewards.experience_awarded==120 and result.completion.rewards.pet_experience.amount==0
        successor=resources.definitions[q]['next_ids'][0]
        assert result.completion.started_tasks==(successor,) and successor in load_task_state(db,1111,rid,epoch)[1].active
        assert inv.immutable_snapshot_transaction(db,epoch=epoch)==assets
        payload=result.messages[-1][1]
    # Execute original decoder/Process/consumer, not a Python mirror of map replacement.
    assert native_other_skills(payload,dict(entries))==dict(skills.entries)
    omitted=dict(skills.entries);omitted.pop(next(k for k in omitted if k!=100008))
    assert native_other_skills(other_skills(omitted),dict(skills.entries))==omitted
    # Later independent learning and XP use public owned Interfaces, not task retry.
    with closing(store.leased(1111,rid,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        later=grant_other_skill(db,1111,rid,epoch,rules.skills,100008,9,expected_revision=skills.revision)
        later=grant_other_skill(db,1111,rid,epoch,rules.skills,100009,6,expected_revision=later.revision)
        context=GrowthResourceContext(inv.immutable_snapshot_transaction(db,epoch=epoch),store.equipment_attribute_rules,store.resource_rules)
        credit_experience(db,1111,rid,7,store.growth_rules,store.attribute_rules,epoch,resource_context=context)
        balance=read_experience(db,1111,rid);growth=read_growth(db,1111,rid)
    before=snapshot(store)
    with closing(store.leased(1111,rid,epoch).connect()) as db,db:
        db.execute('BEGIN')
        paid=readonly(db.db,lambda:complete(db,now_ms=ticket.deadline_ms+1,map_generation=None,proof=None,location=None))
        assert paid.replayed and paid.completion is None and paid.skills==later
        assert paid.messages[-1:]==other_skill_messages(later,rules.skills)
        actor,_=load_task_state(db,1111,rid,epoch)
        profile=current_task_resource_profile(db,actor,inv,store.resource_rules,store.equipment_attribute_rules)
        expected=((S_REFRESH_USER_EXP,encode_user_experience(balance.experience)),
            growth_refresh(growth,profile))+other_skill_messages(later,rules.skills)
        assert paid.messages==expected,'Paid teaching replayed historical XP/profile instead of exact current authority'
        assert not any(k==S_ACCEPT_SCENARIO_QUEST for k,_ in paid.messages)
        paid_payload=paid.messages[-1][1]
    assert snapshot(store)==before
    assert native_other_skills(paid_payload,dict(skills.entries))==dict(later.entries)
    epoch2=store.acquire_lease(1111,rid)
    inv2,_,_,_=runtime_storage.load_role(store,1111,rid,epoch2,resources)
    with closing(store.leased(1111,rid,epoch2).connect()) as db,db:
        db.execute('BEGIN')
        assert readonly(db.db,lambda:read_other_skills(db,1111,rid,epoch2,rules.skills))==later
        assert read_experience(db,1111,rid)==balance and read_growth(db,1111,rid)==growth
        refuse(lambda:read_other_skills(db,1111,rid,epoch,rules.skills))
        refuse(lambda:complete_first_skill_transaction(db,1111,rid,epoch2,resources,rules,ticket,command,inv2,
            proof=None,location=None,generation=1,map_generation=None,now_ms=3000,movement_state=0,**rewards))
        assert db.execute('SELECT COUNT(*) FROM task_first_skills WHERE role_id=?',(rid,)).fetchone()==(1,)
    assert not load_task_battle_resources(resources).enabled_task_ids
    return dict(task_id=q,baseline=entries,after=skills.entries,later=later.entries,packet_hex=payload.hex(),
        task_contract_verified=True,actual_ai_victory_verified=False,production_reachable=False)


def main():
    inputs=source_hashes()
    with tempfile.TemporaryDirectory(prefix='task-first-skill-') as folder:
        store=AccountStore(Path(folder)/'state.sqlite3');runtime_storage.prepare(store)
        story=load_story_instance_rules(store.task_resources,store.newbie_rules)
        rules=load_first_skill_rules(store.task_resources,store.newbie_rules,story,load_placements())
        assert len(rules.route_tasks)==43 and set(rules.definitions)==PROLOGUE_FIRST_SKILL_IDS
        central=json.loads((OUT/'design/newbie-first-skill-v1.json').read_text(encoding='utf8'))
        for field,value in (('grant_value',True),('fee',1),('minimum_elapsed_ms',0),('snapshot_flag',0),('task_ids',[100179]*10)):
            p=Path(folder)/'wrong.json';p.write_text(json.dumps(dict(central,**{field:value})),encoding='utf8')
            refuse(lambda:load_first_skill_rules(store.task_resources,store.newbie_rules,story,load_placements(),path=p))
        with closing(store.connect()) as db,db:
            prepare_other_skill_storage(db);prepare_first_skill_storage(db);prepare_task_battle_storage(db)
        check_creation(store,rules.skills)
        results=[check_role(store,rules,9,11,100179,((100007,3),(310202,4),(700004,2))),
            check_role(store,rules,6,17,100779,((100008,7),(100009,4)))]
    assert source_hashes()==inputs,'Skill verification input changed during run'
    report=dict(passed=['Strict approved10 tasks/43 routes and three-table identity;26 display entries are distinct from five native OtherSkills identities; malformed policy refuses',
        'Explicit fresh creation empty authorization rolls back with creation; historical labels remain unknown; malformed/duplicate/foreign-native-container baselines refuse',
        'Actual admit/settle AI8001 contract with explicit artificial terminal activates teaching only; default battle registry remains empty',
        'Independent absent active/predecessor/receipt/ledger and wrong key/NPC/clock/state/generations/revisions refuse',
        'Late SQL receipt failure and actual late native encoding failure roll back all DB tables',
        'Original120XP/zero other rewards, max(existing,1), all other skills and assets preserved; original battle successor only active0',
        'Paid after later public learning/XP is SQL-authorizer pure with exact current XP/profile/full-map messages; new lease keeps authority and rejects old ticket',
        'Original native decoder/Process/consumer preserves both actual full snapshots and later paid map; deliberate omission really deletes old key'],
        native_other_skill_ids=sorted(rules.skills.catalog_ids),
        cross_namespace_baseline_and_grant_rejected=True,special310202_and700004_preserved=True,
        roles=results,source_sha256=inputs,inputs_stable=True,task_contract_verified=True,
        actual_ai_victory_verified=False,production_reachable=False,shared_runtime_wired=False,
        native_skill_consumer_verified=True,native_gui_verified=False,live_server_changed=False,battle_executed=False,
        fixtures=['Explicit complete historical skill baselines, late master journal and adopted NPC approach',
            'Numeric Participant/BattleFinished contract only, no actual AI8001 execution',
            'Explicit temporary fresh creation transaction, shared accounts creation/login untouched'])
    write_json(OUT/'evidence/task-first-skill-verification.json',report);print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':main()
