"""Original43-route chapter transactions; controlled creation Adapter, no GUI."""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
import json
import struct
import tempfile
from accounts import AccountStore
from inventory import Inventory
from tasks import prepare_task_store
from task_rewards import prepare_reward_storage
from task_persistence import load_task_state
from task_newbie_chapter import (load_newbie_chapter_rules,prepare_newbie_chapter_storage,
    record_newbie_creation,initialize_newbie_chapter,authorize_newbie_playback,finish_newbie_chapter,read_newbie_chapter)
from task_protocol import decode_accept_scenario_quest
from world_newbie import NewbieFlow,load_newbie_routes
from world_catalog import maps,maze_grids
from world_owner import Location,MapAddress
from inspect_client import OUT


def refused(action):
    try:
        action()
    except ValueError:
        return
    raise AssertionError('Unauthorized newbie operation accepted')


def main():
    with tempfile.TemporaryDirectory() as directory:
        accounts=AccountStore(Path(directory)/'chapters.sqlite3')
        resources=prepare_task_store(accounts)
        inventory_config=Inventory.prepare(accounts)
        routes=load_newbie_routes()
        rules=load_newbie_chapter_rules(resources,routes,maps(),maze_grids())
        with closing(accounts.connect()) as db:
            prepare_reward_storage(db);prepare_newbie_chapter_storage(db)
        sequence=0

        def create(route,*,abort=False):
            nonlocal sequence
            sequence+=1
            shape=next(shape for shape,ident in resources.shape_to_role_config.items() if ident==route.character_id)
            # Creation-path Adapter: role insert, independent origin and world's
            # one-time spawn share ONE transaction. Shared AccountStore wiring is
            # deliberately not modified by this task-system verification.
            with closing(accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                role_id=db.execute('INSERT INTO roles(account_id,name,school,shape) VALUES(?,?,?,?)',
                    (1111,f'章节{sequence}',route.school_id,shape)).lastrowid
                origin=record_newbie_creation(db,1111,role_id,f'controlled-create:{sequence}',resources,rules)
                db.execute('INSERT INTO role_positions VALUES(?,?,?,?)',(role_id,*origin.spawn))
                if abort:
                    raise RuntimeError('controlled fresh provenance/spawn rollback')
            epoch=accounts.acquire_lease(1111,role_id)
            location=Location(role_id,epoch,MapAddress(route.home_map_id,1,0),1,*origin.spawn[1:])
            return role_id,epoch,location,Inventory(accounts,1111,role_id,inventory_config)

        try:
            create(next(iter(routes.values())),abort=True)
            raise AssertionError('Fresh creation did not abort')
        except RuntimeError:
            pass
        with closing(accounts.connect()) as db:
            assert db.execute('SELECT COUNT(*) FROM roles').fetchone()[0]==0
            assert db.execute('SELECT COUNT(*) FROM task_newbie_origins').fetchone()[0]==0
            assert db.execute('SELECT COUNT(*) FROM role_positions').fetchone()[0]==0

        for index,route in enumerate(routes.values()):
            role_id,epoch,location,inv=create(route)
            flow=NewbieFlow(resources,routes)
            with closing(accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                chapter=initialize_newbie_chapter(db,1111,role_id,epoch,flow,rules)
                assert chapter.phase=='authorized' and chapter.intro_discriminator==0
                _,state=load_task_state(db,1111,role_id,epoch)
                assert state.active==frozenset({route.intro_task_id})
                playback=authorize_newbie_playback(db,1111,role_id,epoch,flow,rules,location,
                    generation=1,request_id='intro-first',now_ms=10)
                bean=decode_accept_scenario_quest(playback.messages[0][1])
                assert (bean.quest_id,bean.state,bean.value1,bean.value2,bean.npc_key)==(route.intro_task_id,0,0,0,0)
                assert playback.messages[1:]==((0xc0017,struct.pack('>i',route.intro_movie_id)),)
                retry_flow=NewbieFlow.from_ticket(resources,routes,playback.ticket)
                same=authorize_newbie_playback(db,1111,role_id,epoch,retry_flow,rules,location,
                    generation=1,request_id='intro-first',now_ms=11)
                assert same.ticket==playback.ticket
            body=struct.pack('>i',route.intro_movie_id)
            def finish_local(db,*,end_body=body,end_location=location,end_generation=1,clock=12):
                local_flow=NewbieFlow.from_ticket(resources,routes,playback.ticket)
                return finish_newbie_chapter(db,1111,role_id,epoch,local_flow,rules,end_body,end_location,inv,
                    generation=end_generation,now_ms=clock)
            if index==0:
                with closing(accounts.connect()) as db,db:
                    db.execute('BEGIN IMMEDIATE')
                    refused(lambda: finish_local(db,end_body=struct.pack('>i',99999)))
                    refused(lambda: finish_local(db,end_location=replace(location,version=2)))
                    refused(lambda: finish_local(db,end_generation=2))
                try:
                    with closing(accounts.connect()) as db,db:
                        db.execute('BEGIN IMMEDIATE')
                        finish_local(db)
                        raise RuntimeError('controlled failure after root/next/reward/chapter writes')
                except RuntimeError:
                    pass
                with closing(accounts.connect()) as db,db:
                    db.execute('BEGIN')
                    assert read_newbie_chapter(db,1111,role_id,epoch,rules).phase=='playing'
                    _,state=load_task_state(db,1111,role_id,epoch)
                    assert state.active==frozenset({route.intro_task_id}) and not state.completed
                    assert db.execute('SELECT COUNT(*) FROM task_reward_channels WHERE role_id=?',(role_id,)).fetchone()[0]==0
            with closing(accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                result=finish_local(db,clock=13)
                assert result.evidence.source_id==playback.ticket.source_id
                assert result.chapter.phase=='completed' and result.chapter.intro_discriminator==1
                assert result.completion.rewards.experience_awarded==0 and result.completion.rewards.experience_balance==0
                _,state=load_task_state(db,1111,role_id,epoch)
                assert state.completed==frozenset({route.intro_task_id}) and state.active==frozenset({route.successor_task_id})
                assert result.completion.started_tasks==(route.successor_task_id,)
                assert db.execute('SELECT map_id,x,y FROM role_positions WHERE role_id=?',(role_id,)).fetchone()==route.cinematic_endpoint
            # The owner clears its frozen ticket only after this commit. No
            # worker reaches into a RoleOwner's mutable NewbieFlow to clear it.
            with closing(accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                duplicate=finish_newbie_chapter(db,1111,role_id,epoch,NewbieFlow(resources,routes),rules,body,location,inv,generation=1,now_ms=14)
                assert duplicate.evidence is None and duplicate.messages==()
                assert duplicate.completion.rewards.experience_balance==0
                assert authorize_newbie_playback(db,1111,role_id,epoch,flow,rules,location,
                    generation=2,request_id='must-not-replay',now_ms=15).messages==()

        # Pending connection replacement needs a new permit; old epoch/body has
        # no authority even when its movie ID happens to be the same.
        route=next(iter(routes.values()))
        role_id,old_epoch,location,inv=create(route)
        old_flow=NewbieFlow(resources,routes)
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            initialize_newbie_chapter(db,1111,role_id,old_epoch,old_flow,rules)
            old=authorize_newbie_playback(db,1111,role_id,old_epoch,old_flow,rules,location,
                generation=1,request_id='old-connection',now_ms=1)
            refused(lambda: finish_newbie_chapter(db,1111,role_id,old_epoch,old_flow,rules,
                struct.pack('>i',route.intro_movie_id),location,inv,generation=1,now_ms=old.ticket.deadline_ms))
        new_epoch=accounts.acquire_lease(1111,role_id)
        new_location=replace(location,login_epoch=new_epoch)
        new_flow=NewbieFlow(resources,routes)
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            refused(lambda: finish_newbie_chapter(db,1111,role_id,old_epoch,old_flow,rules,
                struct.pack('>i',route.intro_movie_id),location,inv,generation=1,now_ms=2))
            pending=initialize_newbie_chapter(db,1111,role_id,new_epoch,new_flow,rules)
            assert pending.phase=='playing'
            new=authorize_newbie_playback(db,1111,role_id,new_epoch,new_flow,rules,new_location,
                generation=2,request_id='new-connection',now_ms=2)
            assert new.ticket.source_id!=old.ticket.source_id
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            local_flow=NewbieFlow.from_ticket(resources,routes,new.ticket)
            finish_newbie_chapter(db,1111,role_id,new_epoch,local_flow,rules,
                struct.pack('>i',route.intro_movie_id),new_location,inv,generation=2,now_ms=3)
        # Empty legacy progress/XP does not synthesize independent provenance.
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            legacy_id=db.execute('INSERT INTO roles(account_id,name,school,shape) VALUES(1111,?,?,?)',('旧角零经验',11,1010109)).lastrowid
            db.execute('INSERT INTO role_leases VALUES(?,?,1)',(legacy_id,'legacy-lease'))
            assert initialize_newbie_chapter(db,1111,legacy_id,'legacy-lease',NewbieFlow(resources,routes),rules) is None
        report=dict(passed=['all43 original routes: independent provenance, root authorization, bean before correct movie, original zero XP, exactly selected successor',
            'fresh role/provenance/designed spawn rollback leaves no partial creation',
            'transaction-local flows restored from frozen tickets preserve source/request/deadline across retries and rollback',
            'wrong movie/location/generation and expired permit rejected; root/next/rewards/chapter roll back together',
            'completed duplicates acknowledge without messages/awards/replay; authoritative position unchanged',
            'new connection reauthorizes pending chapter; old epoch refuses; legacy zero XP has no implied chapter'],
            tested_adapter='controlled creation and world spawn in one temporary-DB transaction',
            shared_runtime_tested=False,native_gui_tested=False,opening_policy='designed',route_values='client_verified')
    (OUT/'evidence/task-newbie-chapter-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':
    main()
