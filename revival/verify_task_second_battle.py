"""Second-battle Task contract after natural creation, actual first win and teaching.

Disposable DB only. The future AI8027 engine/consumer/shared checks belong to
main; these checks cannot enable the running immutable first-battle release.
"""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
import struct
from verify_local_prologue_teaching import main


def refused(call):
    try:call()
    except ValueError:return
    raise AssertionError('Invalid second-battle authority accepted')


def check(store,first,proof,current,generation,map_generation,inventory,*,after_admission=None):
    from task_first_skill_proof import read_completed_first_skill_proof
    from task_second_battle import load_second_battle_rules,open_second_battle_transaction,admit_second_battle_transaction
    from task_battle import load_task_battle_resources
    from task_dialog_protocol import decode_visit_npc
    from verify_world_committed_transfer_read import readonly
    from task_battle_protocol import decode_task_battle_request
    from role_equipment_storage import current_equipment_projection
    from task_persistence import load_task_state
    from battle_owner import Participant
    from battle import Fighter
    from role_skills import grant_other_skill,read_other_skills
    from verify_task_first_battle import snapshot
    rid=current.role_id;epoch=current.login_epoch
    ids=frozenset((100190,100290,100390,100490,100590,100690,100790,100890,100990,103290))
    registry=load_task_battle_resources(store.task_resources,enabled_task_ids=ids,
        engine_revision='2026-10-24.task-pve-ai8027.1')
    # This registry is an explicit Task CONTRACT fixture, not an implemented
    # AI8027 engine. Actual battle capability and resource consumer are main's.
    policy=Path(__import__('task_second_battle').__file__).parent/'design/task-pve-ai8027-v1.json'
    rules=load_second_battle_rules(store.task_resources,first,registry,store.npc_resources[0],path=policy)
    assert len(rules.route_tasks)==43 and set(rules.route_tasks.values())==ids
    disabled=load_second_battle_rules(store.task_resources,first,load_task_battle_resources(store.task_resources),
        store.npc_resources[0],path=policy)
    with closing(store.connect()) as db,db:
        before=snapshot(db)
        db.execute('BEGIN')
        completed=readonly(db,lambda:read_completed_first_skill_proof(
            db,1111,rid,epoch,store.task_resources,first,100179))
        assert completed.task_id==100179 and completed.chapter_id
        assert completed.skills.entries==((100008,1),)
        assert completed.predecessor[1].startswith('task-battle:')
        def opening(*,candidate=rules,q=100190,p=proof,c=current,state=0):
            return open_second_battle_transaction(db,1111,rid,epoch,store.task_resources,candidate,q,p,c,
                generation=generation,map_generation=map_generation,now_ms=3000,deadline_ms=5000,movement_state=state)
        menu=readonly(db,opening)
        assert decode_visit_npc(menu.messages[0][1])==(proof.entity_key,[],[100190])
        assert menu.skills==completed.skills
        refused(lambda:opening(candidate=disabled))
        refused(lambda:opening(q=101004))
        refused(lambda:opening(q=100290))
        refused(lambda:opening(p=replace(proof,npc_id=10910)))
        refused(lambda:opening(state=1))
        for table,column,value in (('task_first_skills','grant_receipt','null'),
                ('task_first_skills','predecessor','[]'),('task_first_skills','fingerprint','0'*64),
                ('task_reward_channels','receipt','null')):
            db.execute('SAVEPOINT corrupt_teaching')
            query=f'UPDATE {table} SET {column}=? WHERE role_id=? AND task_id=100179'
            if table=='task_reward_channels':query+=" AND channel='character_exp'"
            db.execute(query,(value,rid));refused(opening)
            db.execute('ROLLBACK TO corrupt_teaching');db.execute('RELEASE corrupt_teaching')
        db.execute('SAVEPOINT missing_ledger')
        db.execute('DELETE FROM role_other_skills WHERE role_id=?',(rid,));refused(opening)
        db.execute('ROLLBACK TO missing_ledger');db.execute('RELEASE missing_ledger')
        actor,_=load_task_state(db,1111,rid,epoch)
        profile=current_equipment_projection(db,1111,rid,epoch,inventory.immutable_snapshot_transaction(db,epoch=epoch),
            store.equipment_attribute_rules)
        attrs=profile.attributes;vitals=profile.vitals
        participant=Participant(rid,epoch,generation,attrs.growth_revision+1,'自然旧序章教学',actor.shape,actor.level,
            Fighter(1,0,hp=vitals.hp,max_hp=vitals.max_hp,mp=vitals.mp,max_mp=vitals.max_mp,
                attack=attrs.physical_attack,defense=attrs.physical_defense,speed=attrs.speed),authorized_skills=(100008,))
        request=decode_task_battle_request(struct.pack('>iQ',100190,proof.entity_key))
        def admit(*,ticket=menu.ticket,p=proof,c=current,actor=participant,gen=map_generation,now=3001):
            return admit_second_battle_transaction(db,1111,rid,epoch,store.task_resources,rules,ticket,request,p,c,
                actor,'second-dream-task-contract',generation=generation,map_generation=gen,now_ms=now,movement_state=0)
        refused(lambda:admit(gen=map_generation+'-retired'))
        refused(lambda:admit(ticket=replace(menu.ticket,chapter_id='wrong-chapter')))
        refused(lambda:admit(ticket=replace(menu.ticket,teaching_fingerprint='0'*64)))
        refused(lambda:admit(actor=replace(participant,authorized_skills=())))
        refused(lambda:admit(actor=replace(participant,authorized_skills=(100008,100009))))
        refused(lambda:admit(p=replace(proof,entity_key=proof.entity_key+1)))
        refused(lambda:admit(now=5000))
        higher=grant_other_skill(db,1111,rid,epoch,first.skills,100008,7,expected_revision=completed.skills.revision)
        refused(admit)
        current_menu=readonly(db,opening)
        assert current_menu.skills==higher and current_menu.skills.entries==((100008,7),)
        accepted=admit(ticket=current_menu.ticket)
        assert accepted.phase=='admitted' and accepted.task_id==100190
        assert accepted.plan['engine_revision']=='2026-10-24.task-pve-ai8027.1'
        assert tuple(accepted.plan['participant']['authorized_skills'])==(100008,)
        assert admit(ticket=current_menu.ticket,now=5001).replayed
        refused(opening)
        assert read_other_skills(db,1111,rid,epoch,first.skills)==higher
        continuation={} if after_admission is None else after_admission(
            db,store,rules,accepted,participant,inventory)
        db.rollback();assert snapshot(db)==before
    return dict(completed_teaching_readonly=True,original_second_battle_menu_readonly=True,
        exact43_routes_and_ten_tasks=True,unrelated_ai8027_task101004_refused=True,
        corrupt_teaching_and_unknown_skills_refused=True,changed_skill_or_map_generation_refused=True,
        high_skill_value_preserved_and_real_equipment_participant_bound=True,admission_idempotent_and_whole_outer_rollback=True,
        second_battle_registry_is_contract_fixture=True,actual_ai8027_executed=False,continuation=continuation)


if __name__=='__main__':
    main(after_teaching_check=check,extra_sources=('task_first_skill_proof.py','task_second_battle.py'),
        extra_policies=('task-pve-ai8027-v1.json',))
