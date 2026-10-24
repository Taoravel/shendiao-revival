"""Guild hourly source, fees/resources/research in disposable real stores."""
from pathlib import Path
from contextlib import closing
from dataclasses import replace
import asyncio,json,sqlite3,tempfile,time,threading
from inspect_client import OUT,write_json
from verify_faction_payments import Fixture
from verify_guild_buildings import fixture_policy as building_policy
from verify_guild_research import fixture_policy as research_policy
from faction_domain import OrganizationStore


def fixture_policy():
    # Explicit local examples only; original server curves are unavailable.
    return dict(revision='isolated-guild-maintenance-1',origin='explicit_test_fixture',
        period_ms=3600000,partitions=16,batch_limit=2,member_limit=1024,
        scheduler_enabled=False,scan_interval_ms=100,max_lateness_ms=300000,
        popularity_max=5000,online_gain=3,hourly_decay=1,
        basic_costs=(1000,2000,3000,4000,5000),initial_resources=5,
        resource_growth=tuple(3+n for n in range(21)),resource_caps=tuple(100+20*n for n in range(21)),
        fund_caps=(1000000000,)*21,research_power=tuple(10*n for n in range(21)),
        research_experience=tuple(7*n for n in range(21)))


def make(path,*,funds=10000000,start=None,build=None,maintenance=None):
    f=Fixture(path);f.policy['guild_initial_funds']=funds;f.policy['guild_funds_origin']='explicit_test_fixture'
    f.org=OrganizationStore(path,f.policy,building_policy=build or building_policy(),
        research_policy=research_policy(f),guild_maintenance_policy=maintenance or fixture_policy())
    f.org.initialize();command=f.family();f.fund(command)
    family=f.org.execute(command,f.now())['organization']
    with closing(f.accounts.connect()) as db,db:db.execute('UPDATE organizations SET level=3 WHERE id=?',(family,))
    command=f.cmd(1,family,'create_guild',('维护研究帮','同心协力',command.args[2]));f.fund(command)
    stamp=f.now() if start is None else start
    guild=f.org.execute(command,stamp)['organization']
    return f,guild,stamp


def baseline(f,guild,start):
    state=f.org.guild_maintenance_snapshot(guild)
    assert (state.clock.guild,state.clock.created_ms,state.clock.next_due_ms,state.clock.state,state.clock.revision)==(
        guild,start,start+3600000,'active',1)
    assert (state.resources.amount,state.resources.origin,state.research_power,state.normal_fee)==(5,'explicit_test_fixture',10,16000)
    original=f.org.guild_practice_materials(guild)
    f.org.initialize();assert f.org.guild_maintenance_snapshot(guild)==state
    assert f.org.guild_practice_materials(guild)==original


def normal(f,guild,start):
    from guild_maintenance import GuildMaintenanceCommand
    f.org.execute(f.cmd(1,guild,'set_research',(300101,)),f.now())
    prior=f.org.snapshot(guild)[0]['revision'];materials=f.org.guild_practice_materials(guild)
    due=start+3600000
    command=GuildMaintenanceCommand(guild,due,due+5000,online=((1,f.epochs[1]),(2,f.epochs[2]),(3,'stale'),(16,f.epochs[16])))
    one=f.org.maintain_guild(command,due)
    assert (one.mode,one.fee,one.online_count,one.status)==('normal',16000,2,'maintained')
    assert (one.after.funds,one.after.popularity,one.after.resources,one.after.power)==(9984000,2005,9,10)
    assert one.research.after.level==0 and one.research.after.experience==7
    assert one.revision==prior+1 and one.next_due_ms==due+3600000
    assert f.org.maintain_guild(replace(command,online=()),due)==one
    assert f.org.guild_maintenance_snapshot(guild).resources.amount==9
    assert f.org.guild_practice_materials(guild)==materials
    two=f.org.maintain_guild(GuildMaintenanceCommand(guild,due+3600000,due+3605000),due+3600000)
    assert (two.after.funds,two.after.popularity,two.after.resources)==(9968000,2004,13)
    assert (two.research.after.level,two.research.after.experience,two.research.after.next_experience)==(1,4,20)
    assert f.org.maintain_guild(command,due)==one


def boundaries(directory):
    from guild_maintenance import GuildMaintenanceCommand
    for name,funds,pop,mode,fee,left,amount in (
            ('exact48',768000,2000,'normal',16000,752000,9),
            ('below48',767999,2000,'basic',1000,766999,5),
            ('low-exact48',1152000,1000,'normal',24000,1128000,9),
            ('low-below48',1151999,1000,'basic',1500,1150499,5)):
        f,guild,start=make(directory/(name+'.db'),funds=funds,build=dict(building_policy(),initial_popularity=pop))
        f.org.execute(f.cmd(1,guild,'set_research',(300101,)),f.now())
        due=start+3600000;command=GuildMaintenanceCommand(guild,due,due+5000)
        before=f.org.guild_maintenance_snapshot(guild)
        f.reject(lambda:f.org.maintain_guild(command,due-1),'guild_maintenance_not_due')
        assert f.org.guild_maintenance_snapshot(guild)==before
        result=f.org.maintain_guild(command,due)
        assert (result.mode,result.fee,result.after.funds,result.after.resources)==(mode,fee,left,amount)
        assert (result.research is not None)==(mode=='normal')
        assert f.org.guild_research_snapshot(guild).skills[0].experience==(7 if mode=='normal' else 0)


def degrade(path):
    from guild_maintenance import GuildMaintenanceCommand
    from guild_buildings import ConstructionWork
    f,guild,start=make(path)
    f.org.execute(f.cmd(1,guild,'choose_building',(0,)),f.now())
    old_generation=f.org.guild_building_snapshot(guild).generation
    # Explicit old progression metadata only; no construction reward is faked.
    with closing(f.accounts.connect()) as db,db:
        db.execute('UPDATE organizations SET level=2 WHERE id=?',(guild,))
        db.execute('UPDATE guild_buildings SET level=8,construction=33 WHERE guild=?',(guild,))
        db.execute('UPDATE guild_assets SET funds=0 WHERE guild=?',(guild,))
    due=start+3600000
    result=f.org.maintain_guild(GuildMaintenanceCommand(guild,due,due+5000),due)
    state=f.org.guild_building_snapshot(guild)
    assert result.status=='degraded' and (result.before.level,result.after.level)==(2,1)
    assert (result.after.funds,result.after.popularity)==(5000000,2299)
    assert result.recovery_funds==5000000 and result.recovery_popularity==500
    assert result.research is None and result.after.resources==5
    assert state.selected==-1 and state.generation==old_generation+1
    assert all((b.level,b.construction)==(4,0) for b in state.buildings)
    f.reject(lambda:f.org.apply_guild_construction(ConstructionWork(guild,old_generation,'old-task-after-degrade',due+5000),due),
        'construction_generation_stale')


def terminal_closure(path,*,late_family=False):
    from guild_maintenance import GuildMaintenanceCommand
    from family_guild_history import FamilyGuildHistoryCommand
    from verify_family_guild_history import history
    f,guild,start=make(path,funds=0,build=dict(building_policy(),initial_popularity=0))
    family=f.org.membership(1,f.epochs[1],'family');old=f.org.guild_scope(1,f.epochs[1]);source=None
    if late_family:
        from verify_guild_dissolution import terminal
        source,_=terminal(f,family)
    due=start+3600000;command=GuildMaintenanceCommand(guild,due,due+5000)
    result=f.org.maintain_guild(command,due)
    assert result.status=='retired' and (result.after.level,result.after.state)==(0,'retired')
    assert result.after.resources==5 and result.research is None
    assert f.org.guild_maintenance_snapshot(guild).clock.state=='retired'
    f.reject(lambda:f.org.guild_scope(1,f.epochs[1]),'not_in_guild')
    event=f.org.guild_maintenance_terminal(guild,due)
    assert (family,old[1]) in event.families and (1,old[1],old[2]) in event.members
    assert event.state=='pending'
    if source is not None:
        from family_maintenance import FamilyGuildClosureCommand
        closed=f.org.apply_guild_family_dissolution(source,'family-after-guild-retire',due+5000,due)
        assert closed.state=='dissolution_pending'
        assert f.org.ack_family_guild_dissolution(FamilyGuildClosureCommand(source,'family-retire-ack',due+5000),due)
    templates=[]
    for _ in range(3):
        pending=f.org.pending_family_guild_history(family%f.org.maintenance_rules.partitions)
        if not pending:break
        source_event=f.org.family_guild_history_event(pending[0][1]);templates.append(source_event.template_id)
        delivery=FamilyGuildHistoryCommand(source_event,'retire-history:'+str(source_event.sequence),due+5000)
        f.org.consume_family_guild_history(delivery,due);f.org.ack_family_guild_history(delivery,due)
    assert templates==[5,6]
    if not late_family:assert [row.template_id for row in history(f,family)]==[1,5,6]
    assert f.org.maintain_guild(command,due)==result
    assert not f.org.pending_family_guild_history(family%f.org.maintenance_rules.partitions)
    f.reject(lambda:f.org.maintain_guild(GuildMaintenanceCommand(guild,due+3600000,due+3605000),due+3600000),'guild_dissolution_pending')


def recovery_and_proofs(directory):
    from guild_maintenance import GuildMaintenanceCommand,GuildClockResumeCommand
    f,guild,start=make(directory/'resume.db');due=start+3600000;now=due+300001
    before=f.org.guild_maintenance_snapshot(guild)
    tick=GuildMaintenanceCommand(guild,due,now+5000)
    f.reject(lambda:f.org.maintain_guild(tick,now),'guild_maintenance_overdue_resume_required')
    resumed=f.org.resume_guild_maintenance(GuildClockResumeCommand(guild,due,now+5000),now)
    assert resumed.status=='resumed' and resumed.mode=='none' and resumed.fee==0
    assert resumed.before==resumed.after and resumed.next_due_ms==now+3600000
    after=f.org.guild_maintenance_snapshot(guild)
    assert (after.funds,after.resources,after.popularity)==(before.funds,before.resources,before.popularity)
    assert after.clock.revision==2 and after.clock.next_due_ms==now+3600000
    assert f.org.maintain_guild(tick,now)==resumed
    for missing in ('fund','research'):
        f,guild,start=make(directory/('missing-'+missing+'.db'))
        f.org.execute(f.cmd(1,guild,'set_research',(300101,)),f.now())
        due=start+3600000;c=GuildMaintenanceCommand(guild,due,due+5000)
        result=f.org.maintain_guild(c,due)
        disabled=OrganizationStore(f.org.path,f.policy);disabled.initialize()
        assert disabled.maintain_guild(c,due)==result
        with closing(f.accounts.connect()) as db,db:
            if missing=='fund':db.execute('DELETE FROM organization_fund_ledger WHERE organization=? AND request_id=?',(guild,c.request_id))
            else:db.execute('DELETE FROM guild_research_receipts WHERE guild=? AND request_id=?',(guild,c.request_id))
        f.reject(lambda:f.org.maintain_guild(c,due),'guild_maintenance_outcome_unknown')
    f,guild,start=make(directory/'member-limit-replay.db');due=start+3600000
    c=GuildMaintenanceCommand(guild,due,due+5000,((1,f.epochs[1]),(2,f.epochs[2])))
    result=f.org.maintain_guild(c,due);assert result.online_count==2
    changed=OrganizationStore(f.org.path,f.policy,building_policy=building_policy(),research_policy=research_policy(f),
        guild_maintenance_policy=dict(fixture_policy(),member_limit=1));changed.initialize()
    assert changed.maintain_guild(c,due)==result
    f,guild,start=make(directory/'new-member-limit.db',maintenance=dict(fixture_policy(),member_limit=1));due=start+3600000
    c=GuildMaintenanceCommand(guild,due,due+5000,((1,f.epochs[1]),(2,f.epochs[2])))
    f.reject(lambda:f.org.maintain_guild(c,due),'invalid_guild_maintenance_observation')


def rollback_unknown_caps(directory):
    from guild_maintenance import GuildMaintenanceCommand
    f,guild,start=make(directory/'rollback.db');due=start+3600000
    f.org.execute(f.cmd(1,guild,'set_research',(300101,)),f.now())
    c=GuildMaintenanceCommand(guild,due,due+5000)
    before=f.org.guild_maintenance_snapshot(guild);research=f.org.guild_research_snapshot(guild)
    with closing(f.accounts.connect()) as db,db:
        db.execute("CREATE TRIGGER fixture_clock_tail BEFORE INSERT ON guild_maintenance_receipts BEGIN SELECT RAISE(ABORT,'maintenance_tail_fault'); END")
    try:
        try:f.org.maintain_guild(c,due)
        except sqlite3.IntegrityError as e:assert 'maintenance_tail_fault' in str(e)
        else:raise AssertionError('maintenance partial commit')
        assert f.org.guild_maintenance_snapshot(guild)==before and f.org.guild_research_snapshot(guild)==research
    finally:
        with closing(f.accounts.connect()) as db,db:db.execute('DROP TRIGGER fixture_clock_tail')
    # Historical excess is retained, never silently discarded to a new cap.
    with closing(f.accounts.connect()) as db,db:db.execute('UPDATE guild_resources SET amount=999 WHERE guild=?',(guild,))
    done=f.org.maintain_guild(c,due);assert done.after.resources==999
    changed=OrganizationStore(f.org.path,f.policy,building_policy=building_policy(),research_policy=research_policy(f),
        guild_maintenance_policy=dict(fixture_policy(),online_gain=4));changed.initialize()
    assert changed.maintain_guild(c,due)==done
    f.reject(lambda:changed.guild_maintenance_snapshot(guild),'guild_maintenance_recipe_changed')
    with closing(f.accounts.connect()) as db,db:
        db.execute('DELETE FROM guild_maintenance_clocks WHERE guild=?',(guild,))
        db.execute('DELETE FROM guild_resources WHERE guild=?',(guild,))
    f.org.initialize();f.reject(lambda:f.org.guild_maintenance_snapshot(guild),'guild_maintenance_unknown')


async def runtime_for(f,*,scheduled=False):
    from game_runtime import GameRuntime
    from faction_runtime import OrganizationRuntime
    import runtime_storage
    rt=GameRuntime(f.accounts,runtime_storage.prepare(f.accounts))
    await rt.social_runtime.organizations.close()
    policy=dict(f.policy);policy['family_maintenance']=dict(policy['family_maintenance'],scheduler_enabled=False)
    rt.social_runtime.organizations=OrganizationRuntime(rt.social_runtime,policy,building_policy=building_policy(),
        research_policy=research_policy(f),guild_maintenance_policy=dict(fixture_policy(),scheduler_enabled=scheduled))
    return rt


async def runtime_source(f,guild,start):
    from verify_runtime import Peer
    from guild_maintenance import GuildMaintenanceCommand
    rt=await runtime_for(f);entered,released=threading.Event(),threading.Event()
    try:
        peer=Peer(rt);await peer.login(f.accounts.roles(1111)[0]);await peer.take()
        f.epochs[1]=rt.online_snapshot()[1].login_epoch;owner=rt.social_runtime.organizations
        await owner.command(f.cmd(1,guild,'set_research',(300101,)),f.now());await peer.take()
        original=owner.store.maintain_guild
        def blocked(c,now):
            entered.set()
            if not released.wait(5):raise TimeoutError('maintenance fixture not released')
            return original(c,now)
        owner.store.maintain_guild=blocked
        due=start+3600000;c=GuildMaintenanceCommand(guild,due,due+5000,((1,f.epochs[1]),))
        jobs=[asyncio.create_task(owner.maintain_guild(c,due)) for _ in range(8)]
        assert await asyncio.to_thread(entered.wait,2)
        try:
            family=f.org.membership(1,f.epochs[1],'family')
            await asyncio.wait_for(owner.command(f.cmd(1,family,'set_family_products',(1,-1)),f.now()),2)
            assert (100,b'free') in await asyncio.wait_for(peer.request(100,b'free'),2)
            assert not released.is_set()
        finally:released.set()
        receipts=await asyncio.gather(*jobs)
        assert all(r==receipts[0] for r in receipts) and receipts[0].after.resources==9
        messages=await peer.take();assert any(k==0xc563a for k,_ in messages)
        assert f.org.guild_maintenance_snapshot(guild).funds==9984000
    finally:released.set();await rt.close()
    rt=await runtime_for(f)
    try:
        peer=Peer(rt);await peer.login(f.accounts.roles(1111)[0]);await peer.take()
        result=await rt.social_runtime.organizations.maintain_guild(c,due)
        assert result==receipts[0] and f.org.guild_maintenance_snapshot(guild).funds==9984000
    finally:await rt.close()


async def periodic_source(f,guild,start):
    from verify_runtime import Peer
    rt=await runtime_for(f,scheduled=True)
    try:
        peer=Peer(rt);await peer.login(f.accounts.roles(1111)[0]);await peer.take()
        due=start+3600000
        deadline=time.monotonic()+15
        while time.monotonic()<deadline:
            state=await rt.io.run(('organization',guild),f.org.guild_maintenance_snapshot,guild)
            if state.clock.next_due_ms>due:break
            await asyncio.sleep(.1)
        assert state.clock.next_due_ms==due+3600000 and state.funds==9984000 and state.resources.amount==9
        assert (100,b'free') in await peer.request(100,b'free')
    finally:await rt.close()


async def runtime_terminal(f,guild,start):
    from verify_runtime import Peer
    from guild_maintenance import GuildMaintenanceCommand
    from faction_protocol import LEFT_FACTION
    rt=await runtime_for(f)
    try:
        peer=Peer(rt);await peer.login(f.accounts.roles(1111)[0]);await peer.take()
        due=start+3600000;c=GuildMaintenanceCommand(guild,due,due+5000)
        owner=rt.social_runtime.organizations
        result=await owner.maintain_guild(c,due);assert result.status=='retired'
        assert any(k==LEFT_FACTION for k,_ in await peer.take()),'Retired guild member cache not cleared'
        assert await owner.maintain_guild(c,due)==result
    finally:await rt.close()


async def directory_capacity(f,guild,start):
    rt=await runtime_for(f);release,entered=threading.Event(),threading.Event()
    try:
        owner=rt.social_runtime.organizations;scheduler=owner.guild.maintenance;due=start+3600000;part=guild%16
        first=f.org.guild_maintenance_page(part,due);assert first.entries==((guild,due),)
        # Directory-only records stand for other entities; no economic baseline
        # or reward is invented for them. They arrive after this finite round.
        with closing(f.accounts.connect()) as db,db:
            db.execute("INSERT INTO organizations(id,kind,name,aim,leader) VALUES(?,'guild','directory-only','fixture',1)",(guild+16,))
            db.execute('''INSERT INTO guild_maintenance_clocks
                SELECT ?,partition,created_ms,next_due_ms,state,revision,recipe,origin FROM guild_maintenance_clocks WHERE guild=?''',(guild+16,guild))
        assert f.org.guild_maintenance_page(part,due,None,first.ceiling).entries==((guild,due),)
        original=owner.store.maintain_guild
        def blocked(c,now):
            entered.set()
            if not release.wait(5):raise TimeoutError('directory fixture release missing')
            return original(c,now)
        owner.store.maintain_guild=blocked
        scheduler.limit=0;await scheduler.scan(part,due)
        assert part not in scheduler.cursors and not scheduler.jobs
        scheduler.limit=1;await scheduler.scan(part,due)
        assert await asyncio.to_thread(entered.wait,2)
        assert scheduler.cursors[part]==(due,guild)
        await scheduler.scan(part,due);assert scheduler.cursors[part]==(due,guild)
        release.set();await scheduler.idle()
        assert f.org.guild_maintenance_snapshot(guild).clock.next_due_ms==due+3600000
    finally:release.set();await rt.close()


async def cross_partition_capacity(f,guild,start):
    rt=await runtime_for(f);release=threading.Event();entered=threading.Event();admitted=[]
    try:
        owner=rt.social_runtime.organizations;scheduler=owner.guild.maintenance;scheduler.limit=1
        due=start+3600000;other=guild+1
        # Directory/view-only entity, used solely for admission/failure testing.
        # The injected storage Adapter never writes economics for either guild.
        with closing(f.accounts.connect()) as db,db:
            db.execute("INSERT INTO organizations(id,kind,name,aim,leader) VALUES(?,'guild','cross-partition-only','fixture',1)",(other,))
            db.execute('INSERT INTO guild_view_state SELECT ?,reserved,origin,join_cursor FROM guild_view_state WHERE guild=?',(other,guild))
            db.execute('''INSERT INTO guild_maintenance_clocks SELECT ?,?,created_ms,next_due_ms,state,revision,recipe,origin
                FROM guild_maintenance_clocks WHERE guild=?''',(other,other%16,guild))
        def storage_failure(c,now):
            admitted.append(c.guild);entered.set()
            if not release.wait(3):raise TimeoutError('cross-partition fixture release missing')
            raise sqlite3.OperationalError('controlled per-guild storage fault')
        owner.store.maintain_guild=storage_failure
        for _ in range(4):
            entered.clear();release.clear()
            await scheduler.scan(guild%16,due);await scheduler.scan(other%16,due)
            assert await asyncio.to_thread(entered.wait,2)
            # Let the admitted source stay in flight while its own empty page
            # is reached, the phase that previously reset its round too early.
            await scheduler.scan(guild%16,due);await scheduler.scan(other%16,due)
            release.set();await scheduler.idle()
        assert guild in admitted and other in admitted,admitted
    finally:release.set();await rt.close()


def main():
    with tempfile.TemporaryDirectory() as d:
        f,guild,start=make(Path(d)/'maintenance.db');baseline(f,guild,start);normal(f,guild,start)
        boundaries(Path(d));degrade(Path(d)/'degrade.db')
        terminal_closure(Path(d)/'terminal.db');terminal_closure(Path(d)/'late-family.db',late_family=True)
        recovery_and_proofs(Path(d))
        rollback_unknown_caps(Path(d))
        f,guild,start=make(Path(d)/'runtime.db');asyncio.run(runtime_source(f,guild,start))
        f,guild,start=make(Path(d)/'runtime-terminal.db',funds=0)
        asyncio.run(runtime_terminal(f,guild,start))
        f,guild,start=make(Path(d)/'directory.db',start=int(time.time()*1000)-3600000)
        asyncio.run(directory_capacity(f,guild,start))
        f,guild,start=make(Path(d)/'cross-partition.db',start=int(time.time()*1000)-3600000)
        asyncio.run(cross_partition_capacity(f,guild,start))
        f,guild,start=make(Path(d)/'periodic.db',start=int(time.time()*1000)-3600000+8000)
        asyncio.run(periodic_source(f,guild,start))
    result=dict(passed=['explicit new-guild maintenance clock/resources and current fee/power survive restart; practice materials remain a separate account',
        'real hourly source checks current online leases and atomically deducts fees, refreshes resources, advances selected research and records the clock receipt once',
        'exact48 comparison and post-observation low popularity choose normal/basic fees; basic maintenance grants no resource or research',
        'insufficient maintenance degrades once, recovers designed funds/popularity, fences construction and clamps building levels without granting production',
        'terminal guild detaches families, produces exactly one leave history and durable cleanup event, and acknowledges an earlier family closure without duplicate effects',
        'overdue resume grants no historical income; disabled or changed policy replays historical receipts and missing ledger/research proofs reject',
        'lowering current observation capacity preserves a historical successful source with its original observations but rejects oversized fresh sources',
        'late receipt failure rolls back clock, money, resources and research; known resource excess survives caps and missing historical baselines stay unknown',
        'eight real runtime duplicate hourly sources settle once, project research and survive restart while a separate family command and encrypted heartbeat advance during blocked I/O',
        'real encrypted guild retirement clears current member cache; directory round ceilings fence new arrivals and capacity refusal preserves the unaccepted source',
        'with one shared job slot a repeatedly failing partition cannot monopolize admission and starve a second pending partition',
        'actual periodic partition loops discover and settle a naturally due source without manual clock invocation'],
        production_policy_configured=False,native_gui_verified=False,live_server_changed=False)
    write_json(OUT/'evidence/guild-maintenance-verification.json',result);print(json.dumps(result))


if __name__=='__main__':main()
