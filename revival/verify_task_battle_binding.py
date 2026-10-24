"""Task-only binding/receipt fixture, NOT a formal enemy AI or combat test."""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
import json
import struct
import tempfile
from accounts import AccountStore
from inventory import Inventory
from tasks import prepare_task_store
from task_domain import TaskDomain
from task_persistence import load_task_state,apply_task_plan
from task_rewards import prepare_reward_storage
from task_pet_experience import load_task_pet_experience_rules
from task_battle_protocol import TaskBattleRequest,encode_task_battle_request,decode_task_battle_request
from task_battle import (load_task_battle_resources,prepare_task_battle_storage,open_task_battle_dialogue,
    admit_task_battle_transaction,settle_task_battle_transaction,acknowledge_task_battle_transaction,
    cancel_task_battle_transaction,TASK_BATTLE_SCOPE,SETTLEMENT_PREFIX)
from battle_owner import Participant,BattleAborted
from battle import Fighter
from training_battle import BattleFinished
from task_session import TaskIntent
from task_protocol import C_COMMIT_SCENARIO_QUEST,S_REFRESH_SCENARIO_QUEST_STATE
from progression import read_experience,credit_experience
from currency import prepare_wallet_storage,load_currency_rules,initialize_wallet,read_wallet
from world_npcs import NpcScene,load_placements
from world_owner import MapAddress,Location
from world_catalog import maps
from inspect_client import OUT


def refused(call):
    try:call()
    except ValueError:return
    raise AssertionError('Invalid task battle binding accepted')


def main():
    original=bytes.fromhex('0001870b1122334455667788')
    assert encode_task_battle_request(TaskBattleRequest(100107,0x1122334455667788))==original
    assert decode_task_battle_request(original)==TaskBattleRequest(100107,0x1122334455667788)
    for body in (b'',original[:-1],original+b'\0',struct.pack('>iQ',1000,1),struct.pack('>iQ',500000,1)):
        refused(lambda:decode_task_battle_request(body))
    with tempfile.TemporaryDirectory() as directory:
        accounts=AccountStore(Path(directory)/'task-battle.sqlite3')
        resources=prepare_task_store(accounts)
        config=Inventory.prepare(accounts)
        cash=load_currency_rules();pets=load_task_pet_experience_rules()
        disabled=load_task_battle_resources(resources)
        assert not disabled.enabled_task_ids and len(disabled.definitions)+len(disabled.exclusions)==362
        # Explicit CONTRACT FIXTURE capability, not an approved live PVE engine.
        registry=load_task_battle_resources(resources,enabled_task_ids=frozenset({100107}),
            engine_revision='offline_binding_fixture_v1')
        refused(lambda:load_task_battle_resources(resources,enabled_task_ids=frozenset({999999}),engine_revision='no'))
        role=accounts.create_role(1111,'战斗任务绑定',11,1010109)
        role_id=role['id'];epoch=accounts.acquire_lease(1111,role_id)
        inv=Inventory(accounts,1111,role_id,config,epoch=epoch,currency_rules=cash)
        with closing(accounts.connect()) as db:
            prepare_reward_storage(db);prepare_wallet_storage(db);prepare_task_battle_storage(db)
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            initialize_wallet(db,1111,role_id,epoch,(0,0,0,0),'explicit_migration',cash)
            for action in ('offer','accept'):
                actor,state=load_task_state(db,1111,role_id,epoch)
                apply_task_plan(db,actor,TaskDomain(resources).plan(actor,state,action,100107),action)
        address=MapAddress(1501,1,0);placements=load_placements()[1501]
        npc=next(x for x in placements if x.npc_id==10908)
        location=Location(role_id,epoch,address,1,npc.x,npc.y)
        scene=NpcScene(address,placements,maps(),interaction_radius=32,binding_capacity=1)
        scene.bind(3110,npc.placement_id)
        proof=scene.interact(struct.pack('>Q',3110),location,location,request_id='npc-fixture',deadline_ms=500,now_ms=1)
        # Explicit numeric fixture checks the frozen Participant contract only;
        # no original enemy values or actual character loadout are claimed.
        participant=Participant(role_id,epoch,1,7,role['name'],role['shape'],role['level'],
            Fighter(1,0,hp=100,max_hp=100,mp=50,max_mp=50,attack=25,defense=5,speed=10))
        request=TaskBattleRequest(100107,3110)
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            refused(lambda:open_task_battle_dialogue(db,1111,role_id,epoch,resources,disabled,100107,proof,location,
                generation=1,now_ms=2,deadline_ms=500))

        def admit(db,battle_id):
            dialogue=open_task_battle_dialogue(db,1111,role_id,epoch,resources,registry,100107,proof,location,
                generation=1,now_ms=2,deadline_ms=500)
            if battle_id=='defeat':
                refused(lambda:admit_task_battle_transaction(db,1111,role_id,epoch,resources,registry,dialogue.ticket,
                    TaskIntent(C_COMMIT_SCENARIO_QUEST,100107,3110,0),location,participant,battle_id,generation=1,now_ms=3))
                refused(lambda:admit_task_battle_transaction(db,1111,role_id,epoch,resources,registry,dialogue.ticket,
                    replace(request,npc_key=999),location,participant,battle_id,generation=1,now_ms=3))
                refused(lambda:admit_task_battle_transaction(db,1111,role_id,epoch,resources,registry,dialogue.ticket,
                    request,replace(location,version=2),participant,battle_id,generation=1,now_ms=3))
                refused(lambda:admit_task_battle_transaction(db,1111,role_id,epoch,resources,registry,dialogue.ticket,
                    request,location,replace(participant,stats=None),battle_id,generation=1,now_ms=3))
                refused(lambda:admit_task_battle_transaction(db,1111,role_id,epoch,resources,registry,dialogue.ticket,
                    request,location,replace(participant,attribute_version=0),battle_id,generation=1,now_ms=3))
            result=admit_task_battle_transaction(db,1111,role_id,epoch,resources,registry,dialogue.ticket,
                request,location,participant,battle_id,generation=1,now_ms=3)
            retry=admit_task_battle_transaction(db,1111,role_id,epoch,resources,registry,dialogue.ticket,
                request,location,participant,battle_id,generation=1,now_ms=1000)
            assert retry.replayed and retry.fingerprint==result.fingerprint
            return result

        def terminal(battle_id,outcome):
            winner=0 if outcome=='victory' else -1 if outcome=='draw' else 1
            return BattleFinished(battle_id,SETTLEMENT_PREFIX+battle_id,role_id,winner,outcome=='victory',2,
                registry.engine_revision,epoch,7,scope=TASK_BATTLE_SCOPE,task_event_eligible=True,outcome=outcome)

        def settle(db,event):
            return settle_task_battle_transaction(db,1111,role_id,epoch,resources,registry,event,inv,
                currency_rules=cash,pet_experience_rules=pets)

        for outcome in ('defeat','draw','escape'):
            with closing(accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                bound=admit(db,outcome)
                assert bound.plan['ai_id']==8001
                if outcome=='defeat':
                    event=terminal(outcome,'victory')
                    for bad in (replace(event,scope='local_training_only'),replace(event,scope='wild_encounter_v1'),
                        replace(event,task_event_eligible=False),replace(event,snapshot_version=8),
                        replace(event,revision='wrong-engine'),replace(event,role_id=role_id+1),
                        replace(event,battle_id='unregistered',settlement_id=SETTLEMENT_PREFIX+'unregistered'),
                        replace(event,won=False),replace(event,item_rewards=((43000,1),))):
                        refused(lambda:settle(db,bad))
                result=settle(db,terminal(outcome,outcome))
                assert result.completion is None and result.admission.phase=='lost'
                assert settle(db,terminal(outcome,outcome)).replayed
                refused(lambda:settle(db,terminal(outcome,'victory')))
                assert 100107 in load_task_state(db,1111,role_id,epoch)[1].active
                assert read_experience(db,1111,role_id).experience==0
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');admit(db,'cancelled')
            aborted=BattleAborted('cancelled',role_id,epoch,'controlled-host-retirement')
            assert cancel_task_battle_transaction(db,1111,role_id,epoch,aborted).completion is None
            assert cancel_task_battle_transaction(db,1111,role_id,epoch,aborted).replayed
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');admit(db,'victory')
            refused(lambda:admit(db,'duplicate-pending'))
        event=terminal('victory','victory')
        try:
            with closing(accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE');settle(db,event)
                raise RuntimeError('after task/XP/wallet/terminal receipt')
        except RuntimeError:pass
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            assert 100107 in load_task_state(db,1111,role_id,epoch)[1].active
            assert read_experience(db,1111,role_id).experience==0
            assert read_wallet(db,1111,role_id,epoch,cash)[1].balance==0
            assert db.execute("SELECT phase FROM task_battle_admissions WHERE battle_id='victory'").fetchone()[0]=='admitted'
            result=settle(db,event)
            assert result.completion.rewards.experience_balance==120
            assert read_wallet(db,1111,role_id,epoch,cash)[1].balance==400
            effect=json.loads(db.execute('SELECT payload FROM task_effects WHERE role_id=? AND task_id=100107',(role_id,)).fetchone()[0])
            assert effect['continuation_fields']['ScenarioInfoAnimationID']=='10019'
            assert effect['next_ids']==[100179]
            assert any(k==S_REFRESH_SCENARIO_QUEST_STATE for k,_ in result.messages)
            again=settle(db,event)
            assert again.replayed and not any(k==S_REFRESH_SCENARIO_QUEST_STATE for k,_ in again.messages)
        old_epoch=epoch;epoch=accounts.acquire_lease(1111,role_id)
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            refused(lambda:settle(db,event))  # old event cannot mutate new lease
            credit_experience(db,1111,role_id,5,login_epoch=epoch)
            acknowledged=acknowledge_task_battle_transaction(db,1111,role_id,epoch,resources,registry,'victory',inv,
                currency_rules=cash,pet_experience_rules=pets)
            assert acknowledged.replayed and acknowledged.completion.rewards.experience_balance==125
            assert not any(k==S_REFRESH_SCENARIO_QUEST_STATE for k,_ in acknowledged.messages)
        report=dict(passed=['original0xc4a4c exact12-byte codec; trailing/out-of-range refused; ordinary CCommit cannot admit battle',
            'default enabled set empty; explicit fixture task100107 AI8001 binds actual NPC/current role/epoch/Participant/version before launch',
            'duplicate admission returns receipt without re-launch; wrong NPC/location/loadout/result identity and training/wild/unqualified result rejected',
            'defeat/draw/escape/cancel leave original quest active without rewards; result conflicts reject',
            'task completion/original120XP/SMoney400/raw continuations/terminal receipt share rollback and commit',
            'same terminal and new-lease paid acknowledgement return current125XP without repeated state1/presentation'],
            metadata_binding_candidates=len(disabled.definitions),metadata_excluded=len(disabled.exclusions),
            formal_pve_tasks_enabled_by_default=0,tested_adapter='explicit Participant/BattleFinished contract fixtures; actual task/reward/inventory/wallet transaction',
            enemy_ai_tested=False,combat_simulated=False,shared_runtime_tested=False,native_gui_tested=False)
    (OUT/'evidence/task-battle-binding-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':main()
