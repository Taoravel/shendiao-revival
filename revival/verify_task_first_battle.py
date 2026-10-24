"""Run the new Task gate at the frozen natural level2/private-NPC checkpoint.

The injected Module is an explicit isolated candidate, not a gameplay overlay
or evidence of shared integration. Its numeric Participant is a binding fixture;
no actual AI is executed. Original natural prefix remains the frozen release.
"""
from contextlib import closing
from dataclasses import replace
import hashlib
import importlib.util
from pathlib import Path
import struct
import sys
import time
from diagnose_growth_first_battle_runtime import main as natural_probe


def refused(call):
    try:call()
    except ValueError:return
    raise AssertionError('Invalid first-battle authority accepted')


def snapshot(db):
    tables=tuple(row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"))
    return tuple((name,tuple(sorted((tuple(row) for row in db.execute(
        'SELECT * FROM "'+name.replace('"','""')+'"')),key=repr))) for name in tables)


async def check(store,runtime,owner,role,key):
    path=Path(__file__).with_name('task_first_battle.py')
    sha=hashlib.sha256(path.read_bytes()).hexdigest()
    spec=importlib.util.spec_from_file_location('isolated_task_first_battle',path)
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    from task_battle import prepare_task_battle_storage,load_task_battle_resources
    from task_battle_protocol import TaskBattleRequest
    from battle_owner import Participant
    from battle import Fighter
    from task_dialog_protocol import decode_visit_npc
    from task_persistence import load_task_state
    rid=role['id'];epoch=owner.epoch
    generation=runtime.connections[rid].generation
    target=runtime.map(owner.map_address)
    lifecycle=await target.mailbox.call('inspect_lifecycle',int(time.monotonic()*1000))
    map_generation=lifecycle.owner_generation
    proof,current=await target.mailbox.call('npc',rid,epoch,owner.position.version,struct.pack('>q',key),
        request_id='first-battle-scope-proof',deadline=time.monotonic()+30)
    with closing(store.connect()) as db:
        prepare_task_battle_storage(db)
    registry=load_task_battle_resources(store.task_resources,enabled_task_ids=module.FIRST_DREAM_TASK_IDS,
        engine_revision='2026-10-24.task-pve-ai8001.1')
    rules=module.load_first_battle_rules(store.task_resources,store.newbie_rules,store.story_instance_rules,
        registry,store.npc_resources[0],path=path.parent/'design/task-pve-ai8001-v1.json')
    disabled=module.load_first_battle_rules(store.task_resources,store.newbie_rules,store.story_instance_rules,
        load_task_battle_resources(store.task_resources),store.npc_resources[0],path=path.parent/'design/task-pve-ai8001-v1.json')
    assert len(rules.route_tasks)==43 and set(rules.route_tasks.values())==module.FIRST_DREAM_TASK_IDS
    with closing(store.leased(1111,rid,epoch).connect()) as db:
        before=snapshot(db);db.execute('BEGIN IMMEDIATE')
        actor,_=load_task_state(db,1111,rid,epoch)
        def opening(*,candidate=rules,q=100107,p=proof,c=current,state=0):
            return module.open_first_battle_transaction(db,1111,rid,epoch,store.task_resources,candidate,q,p,c,
                generation=generation,map_generation=map_generation,now_ms=10,deadline_ms=1000,movement_state=state)
        changes=db.execute('SELECT total_changes()').fetchone()[0]
        menu=opening()
        assert db.execute('SELECT total_changes()').fetchone()[0]==changes
        assert decode_visit_npc(menu.messages[0][1])==(key,[],[100107])
        refused(lambda:opening(candidate=disabled))
        refused(lambda:opening(q=100205))
        refused(lambda:opening(p=replace(proof,npc_id=10909)))
        refused(lambda:opening(p=replace(proof,placement_id=11)))
        refused(lambda:opening(p=replace(proof,position_version=current.version+1)))
        refused(lambda:opening(state=1))
        other=replace(current.address,instance_id=current.address.instance_id+1)
        refused(lambda:opening(c=replace(current,address=other),p=replace(proof,address=other)))
        refused(lambda:opening(c=replace(current,x=current.x+1)))
        # Preserve a matching checkpoint while deliberately corrupting only its
        # directory identity; this reaches the real directory read, not a nearer
        # position guard. The fixture is rolled back before any admission.
        db.execute('SAVEPOINT foreign_directory')
        db.execute('UPDATE world_instance_positions SET instance_id=? WHERE role_id=?',(other.instance_id,rid))
        refused(lambda:opening(c=replace(current,address=other),p=replace(proof,address=other)))
        db.execute('ROLLBACK TO foreign_directory');db.execute('RELEASE foreign_directory')
        db.execute('SAVEPOINT wrong_route')
        db.execute('UPDATE roles SET school=12 WHERE id=?',(rid,))
        refused(opening)
        db.execute('ROLLBACK TO wrong_route');db.execute('RELEASE wrong_route')
        request=TaskBattleRequest(100107,key)
        # Explicit numeric CONTRACT fixture, not a current combat loadout or AI.
        participant=Participant(rid,epoch,generation,7,role['name'],actor.shape,actor.level,
            Fighter(1,0,hp=100,max_hp=100,mp=50,max_mp=50,attack=25,defense=5,speed=10))
        def admit(*,ticket=menu.ticket,r=request,p=proof,c=current,gen=map_generation,now=11):
            return module.admit_first_battle_transaction(db,1111,rid,epoch,store.task_resources,rules,
                ticket,r,p,c,participant,'first-battle-gate-contract',generation=generation,
                map_generation=gen,now_ms=now,movement_state=0)
        refused(lambda:admit(gen=map_generation+'-retired'))
        refused(lambda:admit(ticket=replace(menu.ticket,chapter_id='foreign-chapter')))
        refused(lambda:admit(ticket=replace(menu.ticket,rules_fingerprint='0'*64)))
        refused(lambda:admit(r=replace(request,npc_key=key+1)))
        refused(lambda:admit(p=replace(proof,entity_key=key+1)))
        refused(lambda:admit(now=1000))
        admission=admit();assert admission.phase=='admitted' and admission.task_id==100107
        replay=admit(now=1001)
        assert replay.replayed and replay.fingerprint==admission.fingerprint
        refused(opening)
        assert db.execute('SELECT COUNT(*) FROM task_battle_admissions WHERE role_id=?',(rid,)).fetchone()[0]==1
        db.rollback()
        assert snapshot(db)==before
    assert hashlib.sha256(path.read_bytes()).hexdigest()==sha
    return dict(passed=['43 original routes/exact ten first battles and disabled registry refuses',
        'natural current chapter/bloodmark/private checkpoint and actual map NPC proof open original task menu with no DML',
        'other route/NPC/placement/position/state/checkpoint and actual mismatching directory reject',
        'changed projection/chapter/policy/key/expiry reject; same accepted admission is durable/idempotent',
        'existing admission blocks another menu and outer rollback preserves every table'],
        source=str(path),source_sha256=sha,natural_prefix_is_frozen=True,
        participant_is_numeric_contract_fixture=True,actual_ai_executed=False,shared_runtime_wired=False)


if __name__=='__main__':natural_probe(admission_check=check)
