"""Actual existing role on a read-only backup -> real Peer battle and teaching.

Only the new temporary database is changed. Original role/task/profile/skills
are never seeded, skipped, healed or edited to make the test pass.
"""
import argparse
import asyncio
from contextlib import closing
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sqlite3
import struct
import sys
from tempfile import TemporaryDirectory
import time
from unittest.mock import patch


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--seed-db',type=Path,required=True)
    parser.add_argument('--role-id',type=int,default=4)
    parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--case',choices=('win','recover','late-recover','source-drift','notice','defeat','paid-pet'),default='win')
    args=parser.parse_args();source=args.source.resolve()
    sys.path.insert(0,str(source))
    import inspect_client
    inspect_client.ROOT=Path('D:/神雕侠侣');inspect_client.OUT=source
    from accounts import AccountStore
    from game_runtime import GameRuntime
    from verify_runtime import Peer
    from world_newbie import check_birth_site
    from world_catalog import maps,maze_grids
    from world_movement import ROLE_MOVE,ROLE_STOP
    from world_entity_protocol import VISIT_NPC
    from task_dialog_protocol import S_VISIT_NPC,decode_visit_npc
    from task_protocol import C_COMMIT_SCENARIO_QUEST,S_ACCEPT_SCENARIO_QUEST,decode_accept_scenario_quest
    from task_persistence import load_task_state
    from role_skills import read_other_skills
    from role_resource_storage import read_role_resources,ResourceNotInitialized
    from role_attribute_storage import read_attribute_snapshot
    from research_other_skill_snapshot import native_other_skills
    from research_battle_commands import native_action
    from progression import read_experience
    from currency import read_wallet
    from wire import compact
    import runtime_storage
    import task_pve_runtime_storage as combat
    import battle_protocol as p

    def read(store,owner):
        with closing(store.leased(1111,owner.id,owner.epoch).connect()) as db:
            db.execute('BEGIN')
            actor,tasks=load_task_state(db,1111,owner.id,owner.epoch)
            skills=read_other_skills(db,1111,owner.id,owner.epoch,store.other_skill_rules)
            exp=read_experience(db,1111,owner.id)
            total=sum(store.growth_rules.costs[level] for level in range(1,exp.level))+exp.experience
            wallet={row.currency:row.balance for row in read_wallet(db,1111,owner.id,owner.epoch,store.currency_rules)}
            return tasks,skills,total,wallet

    def vitals(store,owner):
        with closing(store.leased(1111,owner.id,owner.epoch).connect()) as db:
            db.execute('BEGIN')
            try:return read_role_resources(db,1111,owner.id,owner.epoch,store.resource_rules)
            except ResourceNotInitialized:return read_attribute_snapshot(db,1111,owner.id,owner.epoch).vitals

    async def run(store,prepared,role):
        runtime=GameRuntime(store,prepared,prologue_touch=True)
        try:
            peer=Peer(runtime);await peer.login(role);owner=runtime.roles[role['id']]
            fixture_pet=None
            if args.case=='paid-pet':
                from progression import credit_experience
                from inventory import AssetChange,FIGHT_PET
                def owned_pet_fixture():
                    with closing(store.leased(1111,owner.id,owner.epoch).connect()) as db,db:
                        db.execute('BEGIN IMMEDIATE')
                        # Explicit isolated eligibility fixture for the original
                        # pet uselevel5, not the ordinary Role4 cohort scenario.
                        credit_experience(db,1111,owner.id,sum(store.growth_rules.costs[level]
                            for level in range(1,5)),store.growth_rules,store.attribute_rules,owner.epoch)
                        granted=owner.inventory.apply_settlement(db,AssetChange('paid-pet-owned-fixture',pets=(500001,)))
                        pet_key=granted.created_pet_ids[0]
                        owner.inventory.change_pet_growth(db,pet_key,'paid-pet-level-fixture',0,
                            'experience',owner.inventory.growth_rules.thresholds[0])
                        return pet_key
                fixture_pet=await owner.io(owned_pet_fixture)
                await peer.request(FIGHT_PET,struct.pack('>i',fixture_pet))
            before=read(store,owner)
            before_vitals=vitals(store,owner)
            assert 100107 in before[0].active and owner.map_address.map_id==1501
            character=store.task_resources.shape_to_role_config[role['shape']]
            route=store.newbie_rules.routes[(character,role['school'])]
            walk=check_birth_site(replace(route,home_map_id=1501,first_npc_id=10908,
                cinematic_endpoint=owner.position.value),maps(),maze_grids()[1501],
                store.npc_resources[0][1501],state_byte=0,interaction_allowed=store.npc_interaction_rules.allows,
                max_visited=100000)
            assert walk.status=='reachable',walk
            path=walk.path
            await peer.request(ROLE_MOVE,struct.pack('>hhhhQ',*path[0],*path[-1],0))
            await peer.request(ROLE_STOP,compact(len(path))+b''.join(struct.pack('>hh',*point) for point in path)
                               +struct.pack('>hhQ',*path[-1],0))
            key=(1501<<32)|walk.placement_id
            menu=await peer.request(VISIT_NPC,struct.pack('>q',key))
            assert any(100107 in decode_visit_npc(body)[2] for kind,body in menu if kind==S_VISIT_NPC)
            if args.case=='notice':
                with patch.object(combat,'participant',side_effect=ValueError('private internal details')):
                    refused=await peer.request(0xc4a4c,struct.pack('>iQ',100107,key))
                assert any(kind==0xc1772 for kind,_ in refused) and owner.battle is None
                assert all(b'private internal details' not in body for _,body in refused)
                return dict(normal_request_has_visible_refusal=True,case='notice',client_rendered=False)
            opening=await peer.request(0xc4a4c,struct.pack('>iQ',100107,key))
            assert owner.battle is not None and p.BATTLE_START in dict(opening)
            admitted=owner.battle;battle_id=admitted.key
            rounds=0;original_terminal=None
            if args.case=='defeat':
                defend=native_action(p.DEFEND,0)
                for _ in range(200):
                    await peer.request(p.SEND_ACTION,defend)
                    if admitted.domain.participant.pet is not None:
                        await peer.request(p.SEND_ACTION,native_action(p.DEFEND,0,is_role=False))
                    await peer.request(p.CLIENT_PLAY_END,b'\0')
                    if owner.battle is None:break
                else:raise AssertionError('Original role did not reach the actual defeat scenario')
                event=admitted.domain.terminal().finished
                assert event.outcome=='defeat' and not event.won
                assert event.combat_resources[0].hp==0
                restored=vitals(store,owner)
                maximum=restored.caps.hp_max if hasattr(restored,'caps') else restored.max_hp
                maximum_mp=restored.caps.mp_max if hasattr(restored,'caps') else restored.max_mp
                assert (restored.hp,restored.mp)==(maximum,maximum_mp)
                assert read(store,owner)==before
                await peer.request(VISIT_NPC,struct.pack('>q',key))
                await peer.request(0xc4a4c,struct.pack('>iQ',100107,key))
                retry=owner.battle
                await peer.request(p.SEND_ACTION,defend)
                if retry.domain.participant.pet is not None:
                    await peer.request(p.SEND_ACTION,native_action(p.DEFEND,0,is_role=False))
                await peer.request(p.CLIENT_PLAY_END,b'\0')
                await peer.request(p.SEND_ACTION,native_action(p.ESCAPE,0))
                if retry.domain.participant.pet is not None:
                    await peer.request(p.SEND_ACTION,native_action(p.DEFEND,0,is_role=False))
                await peer.request(p.CLIENT_PLAY_END,b'\0')
                assert owner.battle is None and retry.domain.terminal().finished.outcome=='escape'
                wounded=vitals(store,owner)
                assert wounded.hp<restored.hp
                paid=await owner.io(combat.settle,store,1111,owner.id,owner.epoch,battle_id)
                assert paid.replayed and vitals(store,owner)==wounded
                return dict(case='defeat',actual_raw_role_hp_zero=True,dream_recovery_to_current_caps=True,
                    defeat_and_escape_keep_original_task_active=True,no_task_reward=True,
                    subsequent_real_damage_preserved_on_old_paid_replay=True)
            if args.case in ('late-recover','source-drift'):
                await peer.request(p.SEND_ACTION,native_action(p.DEFEND,0))
                await peer.request(p.CLIENT_PLAY_END,b'\0')
                assert next(f.hp for f in (await admitted.call('snapshot')).fighters if f.id==1)<before_vitals.hp
            for _ in range(201):
                state=await admitted.call('snapshot');rounds=state.round_number
                packets=await peer.request(p.SEND_ACTION,native_action(p.ATTACK,21))
                if admitted.domain.participant.pet is not None:
                    packets+=await peer.request(p.SEND_ACTION,native_action(p.ATTACK,21,is_role=False))
                assert p.ROUND_SCRIPT in dict(packets)
                after=await admitted.call('snapshot')
                if args.case in ('recover','late-recover','source-drift') and next(f.hp for f in after.fighters if f.id==21)==0:
                    old_epoch=owner.epoch
                    if args.case!='recover':
                        with closing(store.connect()) as db,db:
                            db.execute("CREATE TRIGGER controlled_late_consumer BEFORE UPDATE OF status ON "
                                "task_pve_runtime_battles WHEN NEW.status='settled' BEGIN "
                                "SELECT RAISE(ABORT,'controlled final consumer SQL failure'); END")
                    from contextlib import nullcontext
                    fault=(patch.object(combat,'settle',side_effect=ValueError('controlled consumer failure'))
                           if args.case=='recover' else nullcontext())
                    with fault:
                        try:assert await peer.request(p.CLIENT_PLAY_END,b'\0')==[]
                        except sqlite3.IntegrityError:
                            assert args.case!='recover'
                        original_terminal=admitted.domain.terminal().finished
                        assert original_terminal is not None and original_terminal.won
                        assert read(store,owner)==before and vitals(store,owner)==before_vitals
                        try:await peer.connection.close()
                        except (ValueError,sqlite3.IntegrityError):pass
                        try:await runtime.close()
                        except (ValueError,sqlite3.IntegrityError):pass
                    if args.case!='recover':
                        with closing(store.connect()) as db,db:db.execute('DROP TRIGGER controlled_late_consumer')
                    if args.case=='source-drift':
                        from inventory import Inventory,AssetChange
                        drift_epoch=store.acquire_lease(1111,role['id'])
                        inventory=Inventory(store.leased(1111,role['id'],drift_epoch),1111,role['id'])
                        with closing(store.leased(1111,role['id'],drift_epoch).connect()) as db,db:
                            db.execute('BEGIN IMMEDIATE')
                            inventory.apply_settlement(db,AssetChange('controlled-drift',grants=((49009,1,1),)))
                        runtime=GameRuntime(store,prepared,prologue_touch=True)
                        peer=Peer(runtime)
                        try:await peer.login(role)
                        except ValueError:pass
                        else:raise AssertionError('Changed complete asset source was overwritten during recovery')
                        with closing(store.connect()) as db:
                            row=db.execute('SELECT terminal,status FROM task_pve_runtime_battles '
                                'WHERE role_id=? AND battle_id=?',(role['id'],battle_id)).fetchone()
                            assert row[1]=='terminal' and json.loads(row[0])['won'] is True
                            assert db.execute('SELECT phase FROM task_battle_admissions WHERE role_id=? AND battle_id=?',
                                              (role['id'],battle_id)).fetchone()[0]=='admitted'
                        return dict(case=args.case,source_drift_refused=True,original_producer_pending=True,
                                    late_consumer_failure_rolled_back_all_assets=True)
                    runtime=GameRuntime(store,prepared,prologue_touch=True)
                    peer=Peer(runtime);await peer.login(role);owner=runtime.roles[role['id']]
                    assert owner.epoch!=old_epoch
                    with closing(store.leased(1111,owner.id,owner.epoch).connect()) as db:
                        db.execute('BEGIN')
                        saved=db.execute('SELECT terminal,status FROM task_pve_runtime_battles '
                            'WHERE role_id=? AND battle_id=?',(owner.id,battle_id)).fetchone()
                    from dataclasses import asdict
                    assert json.loads(saved[0])==json.loads(json.dumps(asdict(original_terminal)))
                    assert saved[1]=='settled'
                    break
                done=await peer.request(p.CLIENT_PLAY_END,b'\0')
                if owner.battle is None:
                    assert p.BATTLE_END in dict(done)
                    active=[decode_accept_scenario_quest(body) for kind,body in done if kind==S_ACCEPT_SCENARIO_QUEST]
                    assert any(info.quest_id==100179 and info.state==0 for info in active)
                    break
            else:raise AssertionError('Dedicated real first battle did not finish')
            won=read(store,owner)
            assert 100107 in won[0].completed and 100179 in won[0].active
            assert won[2]-before[2]==120 and won[3]['bound_silver']-before[3]['bound_silver']==400
            if args.case=='paid-pet':
                from inventory import FREE_PET,REST_PET
                await peer.request(REST_PET,b'')
                await peer.request(FREE_PET,struct.pack('>i',fixture_pet))
                with closing(store.leased(1111,owner.id,owner.epoch).connect()) as db:
                    db.execute('BEGIN')
                    assert owner.inventory.read_pet_state(db,fixture_pet) is None
                paid=await owner.io(combat.settle,store,1111,owner.id,owner.epoch,battle_id)
                assert paid.replayed and read(store,owner)==won
                return dict(case='paid-pet',actual_owned_pet_participated=True,
                    actual_free_pet_request=True,paid_reads_current_without_requiring_released_pet=True,
                    controlled_owned_pet_and_uselevel_fixture=True)
            teaching=await peer.request(VISIT_NPC,struct.pack('>q',key))
            assert any(100179 in decode_visit_npc(body)[2] for kind,body in teaching if kind==S_VISIT_NPC)
            assert read(store,owner)[1]==won[1],'NPC visit enrolled or changed the skill ledger'
            command=struct.pack('>iQi',100179,key,0)
            await peer.request(C_COMMIT_SCENARIO_QUEST,command)
            assert 100179 in read(store,owner)[0].active,'Premature teaching commit was accepted'
            await asyncio.sleep(1.05)
            learned=await peer.request(C_COMMIT_SCENARIO_QUEST,command)
            after=read(store,owner)
            assert 100179 in after[0].completed and 100190 in after[0].active
            assert after[2]-won[2]==120 and dict(after[1].entries).get(100008)==1
            payload=dict(learned)[p.OTHER_SKILLS]
            assert native_other_skills(payload)==dict(after[1].entries)
            await peer.request(C_COMMIT_SCENARIO_QUEST,command)
            paid=read(store,owner)
            assert paid==after,'Paid teaching replay changed task, skill, experience or wallet'
            await peer.connection.close()
            peer=Peer(runtime);await peer.login(role);owner=runtime.roles[role['id']]
            assert read(store,owner)==after
            assert native_other_skills(dict(peer.initial)[p.OTHER_SKILLS])==dict(after[1].entries)
            return dict(case=args.case,existing_role_id=role['id'],real_engine_rounds=rounds,
                real_original_battle_id=battle_id,original_event_preserved=True if original_terminal is not None else None,
                battle_awarded_xp=120,battle_awarded_bound_silver=400,teaching_awarded_xp=120,
                teaching_successor=100190,learned_skill=dict(after[1].entries),
                ledger_origin=after[1].origin,reconnect_and_paid_preserve_current=True,
                enrollment_on_visit=False,native_skill_consumer_verified=True)
        finally:
            await runtime.close()

    with TemporaryDirectory(prefix='task-pve-existing-role-') as folder:
        target=Path(folder)/'copy.sqlite3'
        started=time.monotonic()
        def progress(status,remaining,total):
            if time.monotonic()-started>15:raise TimeoutError('Read-only copy deadline')
        with (closing(sqlite3.connect(args.seed_db.resolve().as_uri()+'?mode=ro',uri=True)) as original,
              closing(sqlite3.connect(target)) as destination):
            original.backup(destination,pages=1000,progress=progress)
        store=AccountStore(target);prepared=runtime_storage.prepare(store)
        role=store.owned_role(1111,args.role_id)
        if role is None:raise ValueError('Requested existing role not available in this copy')
        result=asyncio.run(asyncio.wait_for(run(store,prepared,role),90))
    result.update(source=str(source),live_database_access='read-only consistent backup only',
        original_database_written=False,client_operated=False,listener_started=False,
        source_role_task_or_profile_seeded=args.case=='paid-pet',native_gui_verified=False)
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=True))


if __name__=='__main__':main()
