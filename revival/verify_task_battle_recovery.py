"""Task-only durable-original-terminal recovery, not a formal engine/outbox test.

Numeric Participant and terminal DTO are explicit contract fixtures. The
producer/consumer tables model the caller transaction; real PVE source CAS and
outbox provenance are verified separately by their owning integration Module.
"""
from contextlib import closing
from dataclasses import asdict,replace
import hashlib
import json
from pathlib import Path
import sqlite3
import struct
import tempfile
from accounts import AccountStore
from inventory import Inventory
from inspect_client import OUT,write_json
from tasks import prepare_task_store
from task_domain import TaskDomain
from task_persistence import load_task_state,apply_task_plan
from task_rewards import prepare_reward_storage
from task_pet_experience import load_task_pet_experience_rules
from task_battle import (prepare_task_battle_storage,load_task_battle_resources,open_task_battle_dialogue,
    admit_task_battle_transaction,settle_task_battle_transaction,acknowledge_task_battle_transaction,
    recover_task_battle_transaction,read_task_battle_current_transaction,TaskBattleRecoveryWitness,TASK_BATTLE_SCOPE,SETTLEMENT_PREFIX)
from task_battle_protocol import TaskBattleRequest
from battle_owner import Participant
from battle import Fighter
from training_battle import BattleFinished
from world_owner import Location,MapAddress
from world_npcs import NpcScene,load_placements
from world_catalog import maps
from currency import prepare_wallet_storage,load_currency_rules,initialize_wallet,read_wallet,apply_currency,CurrencyChange
from currency_protocol import encode_currency_balance
from progression import read_experience,credit_experience
from task_dialog_protocol import S_REFRESH_USER_EXP,encode_user_experience
from task_protocol import S_REFRESH_SCENARIO_QUEST_STATE
from verify_world_committed_transfer_read import readonly


def sha(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def refused(call):
    try:call()
    except ValueError:return
    raise AssertionError('Invalid terminal recovery accepted')


def snapshot(store):
    with closing(store.connect()) as db:
        names=tuple(row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"))
        return tuple((n,tuple(sorted((tuple(row) for row in db.execute('SELECT * FROM "'+n+'"')),key=repr))) for n in names)


def main():
    path=Path(__file__).with_name('task_battle.py');source_sha=hashlib.sha256(path.read_bytes()).hexdigest()
    groups=[]
    with tempfile.TemporaryDirectory(prefix='task-terminal-recovery-') as directory:
        store=AccountStore(Path(directory)/'temporary.sqlite3');resources=prepare_task_store(store)
        config=Inventory.prepare(store);store.inventory_config=config
        cash=load_currency_rules();pets=load_task_pet_experience_rules()
        registry=load_task_battle_resources(resources,enabled_task_ids=frozenset({100107}),engine_revision='task-recovery-contract-fixture')
        with closing(store.connect()) as db:
            prepare_reward_storage(db);prepare_wallet_storage(db);prepare_task_battle_storage(db)
            db.executescript('''CREATE TABLE probe_producer (battle_id TEXT PRIMARY KEY,event TEXT NOT NULL);
                CREATE TABLE probe_consumer (battle_id TEXT PRIMARY KEY,phase TEXT NOT NULL);''')
        for index,outcome in enumerate(('victory','defeat','escape')):
            role=store.create_role(1111,'任务终局恢复'+str(index),11,1010109);rid=role['id']
            original_epoch=store.acquire_lease(1111,rid)
            battle_id='original-task-terminal-'+str(index)
            with closing(store.leased(1111,rid,original_epoch).connect()) as db,db:
                db.execute('BEGIN IMMEDIATE');initialize_wallet(db,1111,rid,original_epoch,(0,0,0,0),'explicit_migration',cash)
                for action in ('offer','accept'):
                    actor,state=load_task_state(db,1111,rid,original_epoch)
                    apply_task_plan(db,actor,TaskDomain(resources).plan(actor,state,action,100107),'binding-fixture:'+action)
                location=Location(rid,original_epoch,MapAddress(1501,1,0),1,1049,1559)
                scene=NpcScene(location.address,load_placements()[1501],maps(),interaction_radius=32,binding_capacity=1)
                key=(1501<<32)|10;scene.bind(key,10)
                proof=scene.interact(struct.pack('>Q',key),location,location,request_id='recovery-binding-fixture',now_ms=1,deadline_ms=100)
                participant=Participant(rid,original_epoch,1,7,role['name'],role['shape'],role['level'],
                    Fighter(1,0,hp=100,max_hp=100,mp=50,max_mp=50,attack=25,defense=5,speed=10))
                menu=open_task_battle_dialogue(db,1111,rid,original_epoch,resources,registry,100107,proof,location,
                    generation=1,now_ms=2,deadline_ms=100)
                admission=admit_task_battle_transaction(db,1111,rid,original_epoch,resources,registry,menu.ticket,
                    TaskBattleRequest(100107,key),location,participant,battle_id,generation=1,now_ms=3)
                event=BattleFinished(battle_id,SETTLEMENT_PREFIX+battle_id,rid,0 if outcome=='victory' else 1,
                    outcome=='victory',2,registry.engine_revision,original_epoch,7,
                    scope=TASK_BATTLE_SCOPE,task_event_eligible=True,outcome=outcome)
                # Deliberately durable producer before any reward consumer commit.
                db.execute('INSERT INTO probe_producer VALUES(?,?)',(battle_id,json.dumps(asdict(event),sort_keys=True)))
                db.execute('INSERT INTO probe_consumer VALUES(?,?)',(battle_id,'pending'))
            # SQLite stores leases as TEXT. The same current lease expressed
            # as str(int_epoch) must not become a supposedly NEW lease.
            alias_epoch=str(original_epoch)
            alias_inv=Inventory(store,1111,rid,config,epoch=alias_epoch,currency_rules=cash)
            alias_witness=TaskBattleRecoveryWitness(rid,alias_epoch,admission.fingerprint,sha(asdict(event)),
                'fixture-producer:'+battle_id,sha(('fixture-producer',asdict(event))),sha(asdict(participant)))
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                refused(lambda:recover_task_battle_transaction(db,1111,rid,alias_epoch,resources,registry,
                    event,alias_inv,alias_witness,currency_rules=cash,pet_experience_rules=pets))
            epoch=store.acquire_lease(1111,rid)
            inv=Inventory(store,1111,rid,config,epoch=epoch,currency_rules=cash)
            witness=TaskBattleRecoveryWitness(rid,epoch,admission.fingerprint,sha(asdict(event)),
                'fixture-producer:'+battle_id,sha(('fixture-producer',asdict(event))),sha(asdict(participant)))
            def recover(db,*,terminal=event,proof=witness,rules=registry):
                return recover_task_battle_transaction(db,1111,rid,epoch,resources,rules,terminal,inv,proof,
                    currency_rules=cash,pet_experience_rules=pets)
            with closing(store.leased(1111,rid,epoch).connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                refused(lambda:settle_task_battle_transaction(db,1111,rid,epoch,resources,registry,event,inv))
                refused(lambda:acknowledge_task_battle_transaction(db,1111,rid,epoch,resources,registry,battle_id,inv))
                refused(lambda:read_task_battle_current_transaction(db,1111,rid,epoch,resources,registry,event,inv))
                for bad in (replace(witness,current_epoch=original_epoch),replace(witness,role_id=rid+1),
                        replace(witness,admission_fingerprint='0'*64),replace(witness,terminal_fingerprint='0'*64),
                        replace(witness,source_fingerprint='unknown'),replace(witness,producer_receipt_id=''),
                        replace(witness,recovery_revision='unknown-policy')):
                    refused(lambda:recover(db,proof=bad))
                for bad in (replace(event,scope='local_training_only'),replace(event,scope='wild_encounter_v1'),
                        replace(event,task_event_eligible=False),replace(event,snapshot_version=8),
                        replace(event,revision='another-engine'),replace(event,login_epoch=epoch)):
                    refused(lambda:recover(db,terminal=bad,proof=replace(witness,terminal_fingerprint=sha(asdict(bad)))))
                refused(lambda:recover(db,rules=load_task_battle_resources(resources)))
            before=snapshot(store)
            if outcome=='victory':
                with closing(store.connect()) as db:
                    db.execute('''CREATE TRIGGER probe_late_consumer_failure BEFORE UPDATE ON probe_consumer
                        BEGIN SELECT RAISE(ABORT,'late consumer fault after task reward'); END''')
                try:
                    with closing(store.leased(1111,rid,epoch).connect()) as db,db:
                        db.execute('BEGIN IMMEDIATE');recover(db)
                        db.execute("UPDATE probe_consumer SET phase='settled' WHERE battle_id=?",(battle_id,))
                except sqlite3.DatabaseError:pass
                else:raise AssertionError('Late real SQLite consumer failure did not run')
                assert snapshot(store)==before
                with closing(store.connect()) as db:db.execute('DROP TRIGGER probe_late_consumer_failure')
            with closing(store.leased(1111,rid,epoch).connect()) as db,db:
                db.execute('BEGIN IMMEDIATE');result=recover(db)
                db.execute("UPDATE probe_consumer SET phase='settled' WHERE battle_id=?",(battle_id,))
                state=load_task_state(db,1111,rid,epoch)[1]
                assert (100107 in state.completed)==(outcome=='victory')
                assert read_experience(db,1111,rid).experience==(120 if outcome=='victory' else 0)
                assert read_wallet(db,1111,rid,epoch,cash)[1].balance==(400 if outcome=='victory' else 0)
                assert db.execute('SELECT result_fingerprint FROM task_battle_admissions WHERE role_id=?',(rid,)).fetchone()[0]==sha(asdict(event))
                assert event.login_epoch==original_epoch and admission.plan['epoch']==original_epoch
                if outcome=='victory':
                    credit_experience(db,1111,rid,5,login_epoch=epoch)
                    apply_currency(db,1111,rid,epoch,CurrencyChange('later-wallet:'+battle_id,'task_reward','later-fixture',(('bound_silver',7),)),cash)
            # Original event survives another new lease. Paid recovery must never
            # invoke reward/chain writers, even when later legitimate values differ.
            epoch=store.acquire_lease(1111,rid);inv=Inventory(store,1111,rid,config,epoch=epoch,currency_rules=cash)
            witness=replace(witness,current_epoch=epoch)
            before=snapshot(store)
            with closing(store.connect()) as db,db:
                db.execute('BEGIN')
                paid=readonly(db,lambda:recover(db,proof=witness))
                assert paid.replayed and paid.completion is None
                assert not any(kind==S_REFRESH_SCENARIO_QUEST_STATE for kind,_ in paid.messages)
                if outcome=='victory':
                    expected=((S_REFRESH_USER_EXP,encode_user_experience(125)),)+tuple(encode_currency_balance(row.currency,row.balance)
                        for row in read_wallet(db,1111,rid,epoch,cash) if row.currency in ('cash','bound_silver'))
                    assert paid.messages==expected
                else:assert paid.messages==()
                public=readonly(db,lambda:read_task_battle_current_transaction(db,1111,rid,epoch,resources,
                    registry,event,inv,currency_rules=cash))
                assert public.messages==paid.messages and public.replayed
                bad=replace(event,rounds=3)
                refused(lambda:recover(db,terminal=bad,proof=replace(witness,terminal_fingerprint=sha(asdict(bad)))))
            assert snapshot(store)==before
            if outcome=='escape':
                # A separate legitimate retry of the still-active quest, settled
                # normally under its original current lease, exercises pure paid
                # reads where original event epoch == current epoch.
                same_id=battle_id+'-same-lease'
                current_location=replace(location,login_epoch=epoch)
                current_proof=scene.interact(struct.pack('>Q',key),current_location,current_location,
                    request_id='same-lease-query-binding-fixture',now_ms=1,deadline_ms=100)
                with closing(store.connect()) as db,db:
                    db.execute('BEGIN IMMEDIATE')
                    same_menu=open_task_battle_dialogue(db,1111,rid,epoch,resources,registry,100107,current_proof,current_location,
                        generation=1,now_ms=2,deadline_ms=100)
                    admit_task_battle_transaction(db,1111,rid,epoch,resources,registry,same_menu.ticket,
                        TaskBattleRequest(100107,key),current_location,replace(participant,login_epoch=epoch),same_id,
                        generation=1,now_ms=3)
                    same_event=replace(event,battle_id=same_id,settlement_id=SETTLEMENT_PREFIX+same_id,
                        login_epoch=epoch,winner_side=0,won=True,outcome='victory')
                    settle_task_battle_transaction(db,1111,rid,epoch,resources,registry,same_event,inv,
                        currency_rules=cash,pet_experience_rules=pets)
                    same=readonly(db,lambda:read_task_battle_current_transaction(db,1111,rid,epoch,
                        resources,registry,same_event,inv,currency_rules=cash))
                    assert same.replayed and same.completion is None
                    assert not any(kind==S_REFRESH_SCENARIO_QUEST_STATE for kind,_ in same.messages)
        groups=['Actual registered admission and separately durable original terminal survive lease replacement; ordinary old-epoch settle/empty ack still reject',
            'Wrong current owner/witness/admission/event/engine/snapshot, same SQLite TEXT lease int/str aliases and training/wild/disabled capabilities reject',
            'Real late SQLite consumer failure rolls back task120XP/SMoney400/terminal and leaves original producer pending',
            'Trusted recovery keeps original event epoch/fingerprint; victory pays only original task, defeat/escape stay active and grant0',
            'After later legitimate XP/wallet and another lease, SQL-authorizer paid query is pure current125XP/407bound silver with no state1/chain/reward replay',
            'Public paid-current query rejects pending, accepts same original lease or a later lease, and remains SQL-authorizer read-only']
    assert hashlib.sha256(path.read_bytes()).hexdigest()==source_sha
    record=dict(passed=groups,source_sha256=source_sha,original_event_unchanged=True,actual_ai_executed=False,
        participant_and_terminal_are_contract_fixtures=True,real_producer_source_cas_verified=False,
        caller_outbox_is_explicit_sql_fixture=True,shared_runtime_wired=False,live_server_changed=False,native_gui_verified=False)
    write_json(OUT/'evidence/task-battle-recovery-verification.json',record)
    print(json.dumps(record,ensure_ascii=False))


if __name__=='__main__':main()
