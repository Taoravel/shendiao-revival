"""Research progression through the public Store seam, disposable data only."""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
import asyncio,json,sqlite3,tempfile,threading
from verify_faction_payments import Fixture
from faction_domain import OrganizationStore
from inspect_client import OUT,write_json


def fixture_policy(f):
    # Isolated examples, not recovered server numbers or a production recipe.
    return dict(revision='isolated-research-1',origin='explicit_test_fixture',
        costs=tuple((skill,(10,20,30)) for skill in f.policy['guild_research_skill_ids']))


def make(path):
    f=Fixture(path)
    f.org=OrganizationStore(path,f.policy,research_policy=fixture_policy(f));f.org.initialize()
    command=f.family();f.fund(command);family=f.org.execute(command,f.now())['organization']
    with closing(f.accounts.connect()) as db,db:db.execute('UPDATE organizations SET level=3 WHERE id=?',(family,))
    command=f.cmd(1,family,'create_guild',('研究成长帮','同心协力',command.args[2]));f.fund(command)
    guild=f.org.execute(command,f.now())['organization']
    return f,guild


def baseline(f,guild):
    state=f.org.guild_research_snapshot(guild)
    assert state.guild==guild and state.selected_skill==0 and len(state.skills)==14
    assert all((s.level,s.cap,s.experience,s.next_experience)==(0,3,0,10) for s in state.skills)
    assert state.origin=='explicit_test_fixture'
    f.org.initialize();assert f.org.guild_research_snapshot(guild)==state


def progression(f,guild):
    from guild_research import ResearchAward
    f.org.execute(f.cmd(1,guild,'set_research',(300101,)),f.now())
    before=f.org.snapshot(guild)[0]['revision']
    command=ResearchAward(guild,'isolated-maintenance:1',35,f.now()+5000)
    result=f.org.award_guild_research(command,f.now())
    assert (result.skill_id,result.before.level,result.after.level,result.after.experience,
        result.after.next_experience,result.accepted,result.discarded)==(300101,0,2,5,30,35,0)
    assert f.org.snapshot(guild)[0]['revision']==before+1
    state=f.org.guild_research_snapshot(guild)
    assert state.skills[0]==result.after and all(s.level==0 for s in state.skills[1:])
    f.org.execute(f.cmd(1,guild,'set_research',(310103,)),f.now())
    assert f.org.award_guild_research(command,f.now())==result
    assert f.org.guild_research_snapshot(guild).skills[0]==result.after
    f.reject(lambda:f.org.award_guild_research(replace(command,experience=36),f.now()),'guild_research_intent_conflict')
    f.org.execute(f.cmd(1,guild,'set_research',(300101,)),f.now())
    final=f.org.award_guild_research(replace(command,request_id='isolated-maintenance:2',experience=30),f.now())
    assert (final.after.level,final.after.experience,final.after.next_experience,final.accepted,final.discarded)==(3,0,0,25,5)
    revision=f.org.snapshot(guild)[0]['revision']
    capped=f.org.award_guild_research(replace(command,request_id='isolated-maintenance:3'),f.now())
    assert capped.status=='capped' and capped.accepted==0 and capped.discarded==35
    assert f.org.snapshot(guild)[0]['revision']==revision


def rollback_restart(f,guild):
    from guild_research import ResearchAward
    f.org.execute(f.cmd(1,guild,'set_research',(310103,)),f.now())
    command=ResearchAward(guild,'late-receipt-failure',15,f.now()+5000)
    state=f.org.guild_research_snapshot(guild);org=f.org.snapshot(guild)
    wallet=f.wallet(1);assets=f.org.guild_assets(guild)
    with closing(f.accounts.connect()) as db,db:
        db.execute("CREATE TRIGGER fixture_research_receipt BEFORE INSERT ON guild_research_receipts BEGIN SELECT RAISE(ABORT,'late_research_receipt'); END")
    try:f.org.award_guild_research(command,f.now())
    except sqlite3.IntegrityError as error:assert 'late_research_receipt' in str(error)
    else:raise AssertionError('Late receipt failure accepted')
    assert f.org.guild_research_snapshot(guild)==state and f.org.snapshot(guild)==org
    with closing(f.accounts.connect()) as db,db:db.execute('DROP TRIGGER fixture_research_receipt')
    result=f.org.award_guild_research(command,f.now())
    assert (result.after.level,result.after.experience)==(1,5)
    assert f.wallet(1)==wallet and f.org.guild_assets(guild)==assets
    f.org=OrganizationStore(f.accounts.path,f.policy,research_policy=fixture_policy(f));f.org.initialize()
    assert f.org.award_guild_research(command,f.now())==result
    policy=fixture_policy(f);policy['costs']=tuple((s,(11,20,30)) for s in f.policy['guild_research_skill_ids'])
    wrong=OrganizationStore(f.accounts.path,f.policy,research_policy=policy);wrong.initialize()
    f.reject(lambda:wrong.guild_research_snapshot(guild),'guild_research_recipe_conflict')
    # The already committed receipt is historical, even after a policy change.
    assert wrong.award_guild_research(command,f.now())==result
    assert f.org.guild_research_snapshot(guild).skills[4]==result.after


def unknown_and_zero(path):
    from guild_research import ResearchAward
    from verify_guild_offices import setup
    f,_,_,guild=setup(path)
    f.org=OrganizationStore(f.accounts.path,f.policy,research_policy=fixture_policy(f));f.org.initialize()
    f.reject(lambda:f.org.guild_research_snapshot(guild),'guild_research_state_unknown')
    c=ResearchAward(guild,'unknown-existing',10,f.now()+5000)
    f.reject(lambda:f.org.award_guild_research(c,f.now()),'guild_research_state_unknown')
    f.org.initialize();f.reject(lambda:f.org.guild_research_snapshot(guild),'guild_research_state_unknown')
    for value in (True,-1,2**31,None):
        f.reject(lambda:f.org.award_guild_research(replace(c,experience=value),f.now()),'invalid_guild_research_award')
    f.reject(lambda:f.org.award_guild_research(replace(c,deadline_ms=0),f.now()),'guild_research_deadline')
    raw=fixture_policy(f)
    for costs in (raw['costs'][:-1],raw['costs']+(raw['costs'][0],),
            tuple((s,(True,20,30)) for s in f.policy['guild_research_skill_ids']),
            tuple((s,(0,20,30)) for s in f.policy['guild_research_skill_ids'])):
        try:OrganizationStore(f.accounts.path,f.policy,research_policy=dict(raw,costs=costs))
        except ValueError:pass
        else:raise AssertionError('Incomplete or malformed progression recipe accepted')


def idle_and_lifecycle(path):
    from guild_research import ResearchAward
    from verify_guild_dissolution import terminal
    f,guild=make(path)
    c=ResearchAward(guild,'idle-event',10,f.now()+10_000_000)
    org=f.org.snapshot(guild)
    result=f.org.award_guild_research(c,f.now())
    assert result.status=='idle' and result.before is None and result.accepted==0 and result.discarded==10
    assert f.org.snapshot(guild)==org
    f.org.execute(f.cmd(1,guild,'set_research',(300101,)),f.now())
    zero=f.org.award_guild_research(replace(c,request_id='zero-event',experience=0),f.now())
    assert zero.status=='no_gain' and zero.before==zero.after
    family=f.org.membership(1,f.epochs[1],'family')
    # Use the real terminal family and guild closure Interfaces.
    event,now=terminal(f,family)
    closed=f.org.apply_guild_family_dissolution(event,'close-research-guild',now+5000,now)
    assert closed.state=='dissolution_pending'
    assert f.org.award_guild_research(c,now)==result
    f.reject(lambda:f.org.award_guild_research(replace(c,request_id='after-closure'),now),'guild_dissolution_pending')


async def owner_check(path):
    from guild_research import ResearchAward
    from faction_runtime import OrganizationRuntime
    from game_runtime import GameRuntime
    from verify_runtime import Peer
    from family_maintenance import MaintenanceCommand
    import runtime_storage
    f,guild=make(path)
    f.org.execute(f.cmd(1,guild,'set_research',(300101,)),f.now())
    create=f.family(16,name='隔离家族');f.fund(create)
    other=f.org.execute(create,f.now())['organization']
    rt=GameRuntime(f.accounts,runtime_storage.prepare(f.accounts))
    await rt.social_runtime.organizations.close()
    policy=dict(f.policy);policy['family_maintenance']=dict(policy['family_maintenance'],scheduler_enabled=False)
    owner=OrganizationRuntime(rt.social_runtime,policy,research_policy=fixture_policy(f))
    rt.social_runtime.organizations=owner
    entered,released=threading.Event(),threading.Event()
    try:
        c=ResearchAward(guild,'owner-duplicate',5,f.now()+5000)
        results=await asyncio.gather(*(owner.award_guild_research(c,f.now()) for _ in range(8)))
        assert all(value==results[0] for value in results)
        assert f.org.guild_research_snapshot(guild).skills[0].experience==5
        original=owner.store.award_guild_research
        def slow(command,now):
            if command.request_id=='blocked-research':
                entered.set()
                if not released.wait(5):raise TimeoutError('controlled_release_missing')
            return original(command,now)
        owner.store.award_guild_research=slow
        peer=Peer(rt);role=next(role for role in f.accounts.roles(1111) if role['id']==16)
        await peer.login(role)
        pending=asyncio.create_task(owner.award_guild_research(replace(c,request_id='blocked-research'),f.now()))
        assert await asyncio.to_thread(entered.wait,2)
        try:
            clock=f.org.family_maintenance_snapshot(other)
            done=await asyncio.wait_for(owner.maintain_family(MaintenanceCommand(other,clock.next_due_ms,(),
                'other-family-continues',clock.next_due_ms+5000),clock.next_due_ms),2)
            assert done.fee==12000 and not pending.done()
            assert (100,b'ping') in await asyncio.wait_for(peer.request(100,b'ping'),2)
            assert not pending.done()
        finally:released.set()
        assert (await pending).after.level==1
    finally:
        released.set();await rt.close()


def main():
    with tempfile.TemporaryDirectory() as directory:
        f,guild=make(Path(directory)/'research.db');baseline(f,guild);progression(f,guild)
        rollback_restart(f,guild)
        unknown_and_zero(Path(directory)/'unknown.db')
        idle_and_lifecycle(Path(directory)/'closed.db')
        asyncio.run(owner_check(Path(directory)/'owner.db'))
    report=dict(passed=['explicit recipe initializes only new guilds and startup preserves state',
        'multi-level consumption retains remainder; cap discards excess; switch/replay fixes the original selected skill',
        'late receipt failure rolls back progress/revisions; retry and restart preserve the single result',
        'same-version curve changes reject current projection; prior committed receipt remains historical',
        'unknown old state, invalid awards and expiry reject without initialization',
        'idle/zero rewards preserve progress; real terminal guild closure refuses new awards and permits old receipts',
        'actual bounded organization owner deduplicates eight awards; blocked research permits independent family maintenance and encrypted heartbeat'],
        production_recipe_configured=False,normal_guild_maintenance_source_integrated=False,
        source_eligibility_proven_by_this_module=False,shared_runtime_activation=False,native_gui_verified=False,
        live_server_changed=False,fixtures='explicit temporary curves10/20/30; trusted event calls are isolated examples, not normal-maintenance proof')
    write_json(OUT/'evidence/guild-research-verification.json',report);print(json.dumps(report))


if __name__=='__main__':main()
