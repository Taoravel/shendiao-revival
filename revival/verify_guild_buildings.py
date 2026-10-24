"""Guild construction through public organization seams, disposable stores."""
from pathlib import Path
from contextlib import closing
from dataclasses import replace
import asyncio,json,sqlite3,tempfile,struct,threading
from verify_faction_payments import Fixture
from faction_domain import OrganizationStore
from inspect_client import OUT,write_json


def fixture_policy():
    # Only native per-building construction/cost arithmetic is recovered.
    # Initial state, guild caps and maintenance projection are isolated design
    # examples. They never configure the real service or shared baseline.
    return dict(revision='isolated-buildings-1',origin='explicit_test_fixture',
        initial_levels=(1,1,1),initial_popularity=2000,caps=(4,8,12,16,20),
        maintenance_base=10000,maintenance_per_level=(1000,2000,3000))


def make(path,*,funds=50000000,policy=None):
    f=Fixture(path)
    f.policy['guild_initial_funds']=funds;f.policy['guild_funds_origin']='explicit_test_fixture'
    f.org=OrganizationStore(path,f.policy,building_policy=policy or fixture_policy());f.org.initialize()
    c=f.family();f.fund(c);family=f.org.execute(c,f.now())['organization']
    with closing(f.accounts.connect()) as db,db:db.execute('UPDATE organizations SET level=3 WHERE id=?',(family,))
    c=f.cmd(1,family,'create_guild',('建筑恢复帮','同心协力',c.args[2]));f.fund(c)
    guild=f.org.execute(c,f.now())['organization']
    return f,guild


def baseline(f,guild):
    state=f.org.guild_building_snapshot(guild)
    assert state.guild==guild and state.selected==-1 and state.generation==0
    assert state.popularity==2000 and state.origin=='explicit_test_fixture'
    assert tuple((b.building_type,b.level,b.construction) for b in state.buildings)==((0,1,0),(1,1,0),(2,1,0))
    f.org.initialize();assert f.org.guild_building_snapshot(guild)==state


def selection(f,guild):
    state=f.org.guild_building_snapshot(guild);wallet=f.wallet(1)
    c=f.cmd(1,guild,'choose_building',(0,),key='choose-hall')
    result=f.org.execute(c,f.now());assert f.org.execute(c,f.now())==result
    current=f.org.guild_building_snapshot(guild)
    assert (current.selected,current.generation,current.popularity)==(0,1,1800)
    assert current.buildings==state.buildings
    assert f.org.guild_assets(guild).funds==49400000 and f.wallet(1)==wallet
    f.reject(lambda:f.org.execute(f.cmd(1,guild,'choose_building',(0,)),f.now()),'construction_unchanged')
    f.reject(lambda:f.org.execute(f.cmd(3,guild,'choose_building',(1,)),f.now()),'permission_denied')
    f.org.execute(f.cmd(1,guild,'appoint',(2,'deputy')),f.now())
    f.org.execute(f.cmd(1,guild,'set_authority',(2,0,True)),f.now())
    f.reject(lambda:f.org.execute(f.cmd(2,guild,'choose_building',(1,)),f.now()),'permission_denied')
    f.org.execute(f.cmd(1,guild,'set_authority',(2,5,True)),f.now())
    f.org.execute(f.cmd(2,guild,'choose_building',(1,)),f.now())
    current=f.org.guild_building_snapshot(guild)
    assert (current.selected,current.generation,current.popularity)==(1,2,1600)
    assert f.org.guild_assets(guild).funds==47600000


def progression(f,guild):
    from guild_buildings import ConstructionWork
    f.org.execute(f.cmd(1,guild,'choose_building',(0,)),f.now())
    generation=f.org.guild_building_snapshot(guild).generation
    before=f.org.snapshot(guild)[0]['revision'];assets=f.org.guild_assets(guild)
    first=ConstructionWork(guild,generation,'isolated-task-fixture:1',f.now()+5000)
    one=f.org.apply_guild_construction(first,f.now())
    assert (one.building_type,one.level,one.construction,one.upgraded)==(0,1,1,False)
    assert f.org.apply_guild_construction(first,f.now())==one
    assert f.org.snapshot(guild)[0]['revision']==before+1
    f.reject(lambda:f.org.apply_guild_construction(replace(first,generation=generation+1),f.now()),'guild_construction_intent_conflict')
    for index in range(2,151):
        last=ConstructionWork(guild,generation,'isolated-task-fixture:'+str(index),f.now()+5000)
        result=f.org.apply_guild_construction(last,f.now())
    state=f.org.guild_building_snapshot(guild)
    assert (result.level,result.construction,result.upgraded)==(2,0,True)
    assert (state.selected,state.generation,state.buildings[0].level,state.buildings[0].construction)==(-1,generation+1,2,0)
    assert f.org.guild_assets(guild)==assets
    revision=f.org.snapshot(guild)[0]['revision']
    assert f.org.apply_guild_construction(last,f.now())==result
    assert f.org.snapshot(guild)[0]['revision']==revision
    f.reject(lambda:f.org.apply_guild_construction(replace(first,request_id='late-old-round'),f.now()),'construction_generation_stale')
    f.org.execute(f.cmd(1,guild,'choose_building',(0,)),f.now())
    round2=f.org.guild_building_snapshot(guild).generation
    f.org.apply_guild_construction(ConstructionWork(guild,round2,'round2:1',f.now()+5000),f.now())
    f.org.execute(f.cmd(1,guild,'choose_building',(2,)),f.now())
    f.reject(lambda:f.org.apply_guild_construction(ConstructionWork(guild,round2,'round2:late',f.now()+5000),f.now()),'construction_generation_stale')
    f.org.execute(f.cmd(1,guild,'choose_building',(0,)),f.now())
    assert f.org.guild_building_snapshot(guild).buildings[0].construction==1
    assert f.org.apply_guild_construction(first,f.now())==one


def reserve_and_limits(directory):
    for name,funds,policy,reason in (
            ('reserve',803999,fixture_policy(),'insufficient_building_reserve'),
            ('low-pop-reserve',906023,dict(fixture_policy(),initial_popularity=1100,maintenance_base=10001),'insufficient_building_reserve'),
            ('popularity',50000000,dict(fixture_policy(),initial_popularity=199),'insufficient_guild_popularity'),
            ('cap',50000000,dict(fixture_policy(),initial_levels=(4,1,1)),'guild_building_cap_reached')):
        f,guild=make(directory/(name+'.db'),funds=funds,policy=policy)
        old=f.org.guild_building_snapshot(guild);assets=f.org.guild_assets(guild);org=f.org.snapshot(guild)
        f.reject(lambda:f.org.execute(f.cmd(1,guild,'choose_building',(0,)),f.now()),reason)
        assert f.org.guild_building_snapshot(guild)==old and f.org.guild_assets(guild)==assets and f.org.snapshot(guild)==org
    for funds,policy,left in ((804000,fixture_policy(),204000),
            (906024,dict(fixture_policy(),initial_popularity=1100,maintenance_base=10001),306024)):
        f,guild=make(directory/('exact-'+str(funds)+'.db'),funds=funds,policy=policy)
        f.org.execute(f.cmd(1,guild,'choose_building',(0,)),f.now())
        assert f.org.guild_assets(guild).funds==left
    for target in (True,-1,3,'0'):
        f.reject(lambda:f.org.execute(f.cmd(1,guild,'choose_building',(target,)),f.now()),'invalid_building_choice')


def rollback_restart(path):
    from guild_buildings import ConstructionWork
    f,guild=make(path);c=f.cmd(1,guild,'choose_building',(0,),key='selection-receipt-fault')
    before=f.org.guild_building_snapshot(guild);assets=f.org.guild_assets(guild);org=f.org.snapshot(guild)
    with closing(f.accounts.connect()) as db,db:
        db.execute("CREATE TRIGGER fixture_building_selection BEFORE INSERT ON organization_receipts WHEN NEW.request_id='selection-receipt-fault' BEGIN SELECT RAISE(ABORT,'fixture_selection'); END")
    try:f.org.execute(c,f.now())
    except sqlite3.IntegrityError as error:assert 'fixture_selection' in str(error)
    else:raise AssertionError('Late selection receipt failure accepted')
    assert f.org.guild_building_snapshot(guild)==before and f.org.guild_assets(guild)==assets and f.org.snapshot(guild)==org
    with closing(f.accounts.connect()) as db,db:db.execute('DROP TRIGGER fixture_building_selection')
    f.org.execute(c,f.now());selected=f.org.guild_building_snapshot(guild);org=f.org.snapshot(guild)
    work=ConstructionWork(guild,selected.generation,'work-receipt-fault',f.now()+5000)
    with closing(f.accounts.connect()) as db,db:
        db.execute("CREATE TRIGGER fixture_building_work BEFORE INSERT ON guild_construction_receipts BEGIN SELECT RAISE(ABORT,'fixture_work'); END")
    try:f.org.apply_guild_construction(work,f.now())
    except sqlite3.IntegrityError as error:assert 'fixture_work' in str(error)
    else:raise AssertionError('Late work receipt failure accepted')
    assert f.org.guild_building_snapshot(guild)==selected and f.org.snapshot(guild)==org
    with closing(f.accounts.connect()) as db,db:db.execute('DROP TRIGGER fixture_building_work')
    done=f.org.apply_guild_construction(work,f.now());state=f.org.guild_building_snapshot(guild)
    restored=OrganizationStore(path,f.policy,building_policy=fixture_policy());restored.initialize()
    assert restored.guild_building_snapshot(guild)==state and restored.apply_guild_construction(work,f.now())==done
    changed=OrganizationStore(path,f.policy,building_policy=dict(fixture_policy(),revision='changed-recipe'));changed.initialize()
    f.reject(lambda:changed.guild_building_snapshot(guild),'guild_building_recipe_changed')
    assert changed.apply_guild_construction(work,f.now())==done
    f.reject(lambda:changed.apply_guild_construction(replace(work,request_id='changed-new-work'),f.now()),'guild_building_recipe_changed')
    f.reject(lambda:f.org.apply_guild_construction(replace(work,deadline_ms=f.now()-1),f.now()),'guild_construction_deadline')
    with closing(f.accounts.connect()) as db,db:
        saved=db.execute('SELECT result FROM guild_construction_receipts WHERE guild=? AND source_id=?',(guild,work.request_id)).fetchone()[0]
        malformed=json.loads(saved);malformed['generation']=True
        db.execute('UPDATE guild_construction_receipts SET result=? WHERE guild=? AND source_id=?',
            (json.dumps(malformed),guild,work.request_id))
    f.reject(lambda:f.org.apply_guild_construction(work,f.now()),'guild_construction_receipt_invalid')
    with closing(f.accounts.connect()) as db,db:
        db.execute('UPDATE guild_construction_receipts SET result=? WHERE guild=? AND source_id=?',(saved,guild,work.request_id))
        db.execute('DELETE FROM guild_buildings WHERE guild=? AND building_type=2',(guild,))
    restored.initialize()
    f.reject(lambda:restored.guild_building_snapshot(guild),'guild_building_state_invalid')


def unknown_and_pending(path):
    from verify_guild_offices import setup
    from verify_guild_dissolution import terminal
    from guild_buildings import ConstructionWork
    f,first,second,guild=setup(path)
    f.org=OrganizationStore(path,f.policy,building_policy=fixture_policy());f.org.initialize()
    f.reject(lambda:f.org.guild_building_snapshot(guild),'guild_building_state_unknown')
    f.reject(lambda:f.org.execute(f.cmd(1,guild,'choose_building',(0,)),f.now()),'guild_building_state_unknown')
    f,guild=make(path.with_name('pending.db'));f.org.execute(f.cmd(1,guild,'choose_building',(0,)),f.now())
    work=ConstructionWork(guild,1,'before-terminal',f.now()+5000);done=f.org.apply_guild_construction(work,f.now())
    family=f.org.membership(1,f.epochs[1],'family');source,now=terminal(f,family)
    f.org.apply_guild_family_dissolution(source,'terminal-building-test',now+5000,now)
    assert f.org.apply_guild_construction(work,f.now())==done
    f.reject(lambda:f.org.apply_guild_construction(replace(work,request_id='after-terminal'),f.now()),'guild_dissolution_pending')


def panel(messages):
    rows=[body for kind,body in messages if kind==0xc5628]
    assert rows,'Original construction snapshot missing'
    body=rows[-1];assert len(body)==41 and body[4]==3
    return struct.unpack_from('>i',body)[0],tuple(struct.iter_unpack('>iii',body[5:]))


async def runtime_for(f):
    from game_runtime import GameRuntime
    from faction_runtime import OrganizationRuntime
    import runtime_storage
    runtime=GameRuntime(f.accounts,runtime_storage.prepare(f.accounts))
    await runtime.social_runtime.organizations.close()
    policy=dict(f.policy);policy['family_maintenance']=dict(policy['family_maintenance'],scheduler_enabled=False)
    runtime.social_runtime.organizations=OrganizationRuntime(runtime.social_runtime,policy,building_policy=fixture_policy())
    return runtime


async def current_panel(f,guild):
    from verify_runtime import Peer
    from guild_buildings import ConstructionWork
    rt=await runtime_for(f)
    try:
        peer=Peer(rt);await peer.login(f.accounts.roles(1111)[0])
        assert panel(peer.initial+await peer.take())==(-1,((0,1,0),(1,1,0),(2,1,0)))
        assert panel(await peer.request(0xc5627,b''))[0]==-1
        owner=rt.social_runtime.organizations;epoch=rt.online_snapshot()[1].login_epoch
        c=replace(f.cmd(1,guild,'choose_building',(0,)),epoch=epoch)
        await owner.command(c,f.now());assert panel(await peer.take())[0]==0
        work=ConstructionWork(guild,1,'runtime-task-fixture:1',f.now()+5000)
        one=await owner.apply_guild_construction(work,f.now())
        assert panel(await peer.take())[1][0]==(0,1,1)
        await owner.apply_guild_construction(replace(work,request_id='runtime-task-fixture:2'),f.now())
        assert panel(await peer.take())[1][0]==(0,1,2)
        assert await owner.apply_guild_construction(work,f.now())==one
        assert panel(await peer.take())[1][0]==(0,1,2)
    finally:await rt.close()
    rt=await runtime_for(f)
    try:
        peer=Peer(rt);await peer.login(f.accounts.roles(1111)[0])
        assert panel(peer.initial+await peer.take())==(0,((0,1,2),(1,1,0),(2,1,0)))
    finally:await rt.close()


async def scope_and_faults(f,guild):
    from verify_runtime import Peer
    from guild_runtime import GuildWake
    from guild_buildings import ConstructionWork
    rt=await runtime_for(f)
    try:
        roles={r['id']:r for r in f.accounts.roles(1111)}
        leader,member=Peer(rt),Peer(rt);await leader.login(roles[1]);await member.login(roles[2])
        panel(leader.initial+await leader.take())
        assert not any(kind==0xc5628 for kind,_ in member.initial+await member.take())
        assert not any(kind==0xc5628 for kind,_ in await member.request(0xc5627,b''))
        owner=rt.social_runtime.organizations
        for rid in (1,2):f.epochs[rid]=rt.online_snapshot()[rid].login_epoch
        def cmd(actor,identity,operation,args=()):return f.cmd(actor,identity,operation,args)
        await owner.command(cmd(1,guild,'appoint',(2,'deputy')),f.now())
        await owner.command(cmd(1,guild,'set_authority',(2,5,True)),f.now())
        panel(await member.take());assert panel(await member.request(0xc5627,b''))[0]==-1
        wake=GuildWake(2,f.epochs[2],0,b'',*f.org.guild_scope(2,f.epochs[2]))
        await owner.command(cmd(1,guild,'set_authority',(2,5,False)),f.now())
        await member.take();rt.social_runtime.offer(wake)
        assert not any(kind==0xc5628 for kind,_ in await member.take())
        assert not any(kind==0xc5628 for kind,_ in await member.request(0xc5627,b''))
        await owner.command(cmd(1,guild,'set_authority',(2,5,True)),f.now());await member.take()
        family=f.org.membership(2,f.epochs[2],'family')
        await owner.command(cmd(2,family,'leave'),f.now());await owner.guild.idle();await member.take()
        rt.social_runtime.offer(wake)
        assert not any(kind==0xc5628 for kind,_ in await member.take())
        await owner.command(cmd(2,family,'apply'),f.now());await owner.command(cmd(1,family,'review',(2,True)),f.now())
        await owner.guild.idle();await member.take();rt.social_runtime.offer(wake)
        assert not any(kind==0xc5628 for kind,_ in await member.take())
        await leader.take()
        assert not any(kind==0xc5628 for kind,_ in await leader.request(0xc5627,b'bad'))
        original=owner.store.guild_audience
        def unavailable(*args):raise sqlite3.OperationalError('fixture postcommit presentation lock')
        owner.store.guild_audience=unavailable
        try:
            selected=await owner.command(cmd(1,guild,'choose_building',(0,)),f.now())
            assert selected.organization==guild
            work=ConstructionWork(guild,1,'postcommit-display',f.now()+5000)
            receipt=await owner.apply_guild_construction(work,f.now());assert receipt.construction==1
        finally:owner.store.guild_audience=original
        assert panel(await leader.request(0xc5627,b''))[1][0]==(0,1,1)
        old=f.org.guild_building_snapshot(guild)
        with closing(f.accounts.connect()) as db,db:
            db.execute("CREATE TRIGGER fixture_runtime_work BEFORE INSERT ON guild_construction_receipts WHEN NEW.source_id='runtime-fault' BEGIN SELECT RAISE(ABORT,'runtime_work_fault'); END")
        try:
            try:await owner.apply_guild_construction(replace(work,request_id='runtime-fault'),f.now())
            except sqlite3.IntegrityError as error:assert 'runtime_work_fault' in str(error)
            else:raise AssertionError('Actual runtime commit failure swallowed')
        finally:
            with closing(f.accounts.connect()) as db,db:db.execute('DROP TRIGGER fixture_runtime_work')
        assert f.org.guild_building_snapshot(guild)==old
    finally:await rt.close()


async def concurrent_and_independent(f,guild):
    from verify_runtime import Peer
    from guild_buildings import ConstructionWork
    rt=await runtime_for(f);entered,released=threading.Event(),threading.Event()
    try:
        peer=Peer(rt);await peer.login(f.accounts.roles(1111)[0]);await peer.take()
        f.epochs[1]=rt.online_snapshot()[1].login_epoch;owner=rt.social_runtime.organizations
        await owner.command(f.cmd(1,guild,'choose_building',(0,)),f.now());await peer.take()
        original=owner.store.apply_guild_construction
        def blocked(command,now):
            if command.request_id=='blocked-task-fixture':
                entered.set()
                if not released.wait(5):raise TimeoutError('fixture construction release missing')
            return original(command,now)
        owner.store.apply_guild_construction=blocked
        work=ConstructionWork(guild,1,'blocked-task-fixture',f.now()+5000)
        tasks=[asyncio.create_task(owner.apply_guild_construction(work,f.now())) for _ in range(8)]
        assert await asyncio.to_thread(entered.wait,2)
        try:
            family=f.org.membership(1,f.epochs[1],'family')
            await asyncio.wait_for(owner.command(f.cmd(1,family,'set_family_products',(1,-1)),f.now()),2)
            assert (100,b'free') in await asyncio.wait_for(peer.request(100,b'free'),2)
            assert not released.is_set()
        finally:released.set()
        receipts=await asyncio.gather(*tasks)
        assert all(r==receipts[0] for r in receipts) and receipts[0].construction==1
        assert f.org.guild_building_snapshot(guild).buildings[0].construction==1
    finally:
        released.set();await rt.close()


def main():
    with tempfile.TemporaryDirectory() as d:
        f,guild=make(Path(d)/'buildings.db');baseline(f,guild);selection(f,guild)
        f,guild=make(Path(d)/'progress.db');progression(f,guild)
        f,guild=make(Path(d)/'runtime.db');asyncio.run(current_panel(f,guild))
        reserve_and_limits(Path(d));rollback_restart(Path(d)/'rollback.db');unknown_and_pending(Path(d)/'unknown.db')
        f,guild=make(Path(d)/'scope.db');asyncio.run(scope_and_faults(f,guild))
        f,guild=make(Path(d)/'independent.db');asyncio.run(concurrent_and_independent(f,guild))
    result=dict(passed=['explicit new-guild construction baseline survives initialization without filling historical unknown state',
        'real selection and target switching charge guild funds/popularity once, preserve building progress and require independent deputy bit5',
        'trusted source fixtures add exactly one point, upgrade at150, close the round, reject old targets and preserve historical receipts',
        'actual encrypted login/c5627 query/selection/contribution/old replay/restart project current authorized construction state',
        'exact12-hour designed reserve, post-charge low popularity rounded surcharge, insufficient popularity and adopted caps reject atomically',
        'late selection/contribution receipt faults roll back; restart and recipe changes preserve historical successful receipts',
        'unknown historical guilds are not initialized; terminal guild rejects new work while retaining prior receipts',
        'ordinary/revoked/rejoined members cannot query or receive stale building wakes; committed selection/work survives display failure and actual commit faults propagate',
        'eight same-source commands consume once; blocked construction leaves a separate family command and encrypted heartbeat independent'],
        production_policy_configured=False,actual_task_source_integrated=False,npc_choice_registered=False,
        hourly_guild_maintenance_integrated=False,native_gui_verified=False,live_server_changed=False)
    write_json(OUT/'evidence/guild-buildings-verification.json',result);print(json.dumps(result))


if __name__=='__main__':main()
