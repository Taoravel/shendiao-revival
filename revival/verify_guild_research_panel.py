"""Current research over actual original encrypted peer paths; no live game."""
from pathlib import Path
from dataclasses import replace
from contextlib import closing
import asyncio,json,sqlite3,struct,tempfile
from verify_guild_research import make
import guild_research_protocol as p
from inspect_client import OUT,write_json


def research(messages):
    rows=[body for kind,body in messages if kind==p.REFRESH_RESEARCH]
    assert rows,'current original research refresh missing'
    body=rows[-1];assert body[4]==14 and len(body)==285
    return struct.unpack_from('>i',body)[0],{row[0]:row[1:] for row in struct.iter_unpack('>5i',body[5:])}


async def runtime_for(f):
    from game_runtime import GameRuntime
    from faction_runtime import OrganizationRuntime
    from verify_guild_research import fixture_policy
    import runtime_storage
    rt=GameRuntime(f.accounts,runtime_storage.prepare(f.accounts))
    await rt.social_runtime.organizations.close()
    policy=dict(f.policy);policy['family_maintenance']=dict(policy['family_maintenance'],scheduler_enabled=False)
    rt.social_runtime.organizations=OrganizationRuntime(rt.social_runtime,policy,research_policy=fixture_policy(f))
    return rt


async def current_panel(f,guild):
    from verify_runtime import Peer
    from guild_research import ResearchAward
    import faction_protocol as fp
    rt=await runtime_for(f)
    try:
        peer=Peer(rt);await peer.login(f.accounts.roles(1111)[0])
        selected,rows=research(peer.initial+await peer.take())
        assert selected==0 and rows[300101]==(0,3,0,10)
        queried=research(await peer.request(fp.REQUEST_FACTION,b''))
        assert queried==(selected,rows)
        owner=rt.social_runtime.organizations
        def command(skill):
            return replace(f.cmd(1,guild,'set_research',(skill,)),epoch=rt.online_snapshot()[1].login_epoch)
        await owner.command(command(300101),f.now())
        assert research(await peer.take())[0]==300101
        event=ResearchAward(guild,'panel-source:1',35,f.now()+5000)
        committed=await owner.award_guild_research(event,f.now())
        selected,rows=research(await peer.take())
        assert selected==300101 and rows[300101]==(2,3,5,30)
        await owner.award_guild_research(replace(event,request_id='panel-source:2',experience=6),f.now())
        assert research(await peer.take())[1][300101]==(2,3,11,30)
        await owner.command(command(310103),f.now());await peer.take()
        assert await owner.award_guild_research(event,f.now())==committed
        selected,rows=research(await peer.take())
        assert selected==310103 and rows[300101]==(2,3,11,30) and rows[310103]==(0,3,0,10)
        original=owner.store.guild_audience
        def unavailable(*args):raise ValueError('fixture_projection_unavailable')
        owner.store.guild_audience=unavailable
        try:
            result=await owner.award_guild_research(replace(event,request_id='projection-failure',experience=6),f.now())
            assert result.after.experience==6
        finally:owner.store.guild_audience=original
        assert not any(kind==p.REFRESH_RESEARCH for kind,_ in await peer.take())
        def database_unavailable(*args):raise sqlite3.OperationalError('fixture database is locked')
        owner.store.guild_audience=database_unavailable
        try:
            result=await owner.award_guild_research(replace(event,request_id='projection-database-failure',experience=1),f.now())
            assert result.after.experience==7
        finally:owner.store.guild_audience=original
        before=f.org.guild_research_snapshot(guild)
        with closing(f.accounts.connect()) as db,db:
            db.execute("CREATE TRIGGER fixture_panel_commit BEFORE INSERT ON guild_research_receipts WHEN NEW.request_id='panel-commit-failure' BEGIN SELECT RAISE(ABORT,'fixture_commit_failure'); END")
        try:
            try:await owner.award_guild_research(replace(event,request_id='panel-commit-failure',experience=1),f.now())
            except sqlite3.IntegrityError as error:assert 'fixture_commit_failure' in str(error)
            else:raise AssertionError('Actual award commit failure was swallowed')
        finally:
            with closing(f.accounts.connect()) as db,db:db.execute('DROP TRIGGER fixture_panel_commit')
        assert f.org.guild_research_snapshot(guild)==before
        assert research(await peer.request(fp.REQUEST_FACTION,b''))[1][310103]==(0,3,7,10)
    finally:await rt.close()
    # A new runtime and original authentication stream read persisted values.
    rt=await runtime_for(f)
    try:
        peer=Peer(rt);await peer.login(f.accounts.roles(1111)[0])
        selected,rows=research(peer.initial+await peer.take())
        assert selected==310103 and rows[300101]==(2,3,11,30) and rows[310103]==(0,3,7,10)
    finally:await rt.close()


async def scope_filtering(f,guild):
    from verify_runtime import Peer
    from guild_runtime import GuildWake
    from faction_domain import OrganizationStore
    from verify_guild_research import fixture_policy
    rt=await runtime_for(f)
    try:
        roles={r['id']:r for r in f.accounts.roles(1111)}
        leader,member=Peer(rt),Peer(rt)
        await leader.login(roles[1]);await member.login(roles[2])
        research(member.initial+await member.take());await leader.take()
        epoch=rt.online_snapshot()[2].login_epoch
        old=f.org.guild_scope(2,epoch);wake=GuildWake(2,epoch,0,b'',*old)
        family=f.org.membership(2,epoch,'family')
        def command(actor,org,op,args=()):
            return replace(f.cmd(actor,org,op,args),epoch=rt.online_snapshot()[actor].login_epoch)
        f.org.execute(command(2,family,'leave'),f.now())
        rt.social_runtime.offer(wake)
        assert not any(kind==p.REFRESH_RESEARCH for kind,_ in await member.take())
        f.org.execute(command(2,family,'apply'),f.now())
        f.org.execute(command(1,family,'review',(2,True)),f.now())
        rt.social_runtime.organizations.guild.nudge(guild)
        await rt.social_runtime.organizations.guild.idle()
        research(await member.take())
        new=f.org.guild_scope(2,epoch);assert new!=old
        rt.social_runtime.offer(wake)
        assert not any(kind==p.REFRESH_RESEARCH for kind,_ in await member.take())
        rt.social_runtime.offer(GuildWake(2,epoch,0,b'',*new))
        research(await member.take())
        f.reject(lambda:f.org.guild_projection(2,'expired-epoch',*new,()),'stale_epoch')
        raw=fixture_policy(f);raw['costs']=tuple((s,(11,20,30)) for s in f.policy['guild_research_skill_ids'])
        wrong=OrganizationStore(f.accounts.path,f.policy,research_policy=raw)
        f.reject(lambda:wrong.guild_projection(2,epoch,*new,()),'guild_research_recipe_conflict')
    finally:await rt.close()


async def unknown(path):
    from verify_guild_offices import setup
    from verify_runtime import Peer
    from faction_domain import OrganizationStore
    from verify_guild_research import fixture_policy
    import faction_protocol as fp
    f,_,_,guild=setup(path)
    f.org=OrganizationStore(f.accounts.path,f.policy,research_policy=fixture_policy(f))
    rt=await runtime_for(f)
    try:
        peer=Peer(rt);await peer.login(f.accounts.roles(1111)[0])
        messages=peer.initial+await peer.take()+await peer.request(fp.REQUEST_FACTION,b'')
        clears=[body for kind,body in messages if kind==p.REFRESH_RESEARCH]
        assert clears and all(body==bytes(5) for body in clears),'unknown guild must invalidate stale client research cache'
        f.reject(lambda:f.org.guild_research_snapshot(guild),'guild_research_state_unknown')
    finally:await rt.close()


def malformed(state):
    first=state.skills[0]
    for invalid in (replace(state,selected_skill=True),replace(state,selected_skill=360001),
            replace(state,skills=list(state.skills)),replace(state,skills=state.skills[:-1]),
            replace(state,skills=(first,)*14),
            *(replace(state,skills=(replace(first,**change),*state.skills[1:])) for change in (
                dict(cap=0),dict(cap=True),dict(level=4),dict(experience=10),dict(experience=-1),
                dict(next_experience=2**31),dict(level=3,experience=1,next_experience=0)))):
        try:p.refresh(invalid)
        except ValueError:pass
        else:raise AssertionError('Malformed research projection accepted')


def main():
    with tempfile.TemporaryDirectory() as d:
        f,guild=make(Path(d)/'panel.db')
        state=f.org.guild_research_snapshot(guild)
        body=p.refresh(state)
        assert body[:5]==struct.pack('>iB',0,14)
        assert body[5:25]==struct.pack('>5i',300101,0,3,0,10)
        malformed(state)
        asyncio.run(current_panel(f,guild))
        f,guild=make(Path(d)/'scope.db');asyncio.run(scope_filtering(f,guild))
        asyncio.run(unknown(Path(d)/'unknown.db'))
    result=dict(passed=['frozen complete research codec validates all fourteen original skill identities and absolute levels/experience',
        'actual encrypted login/query and research choice carry current c563a values',
        'committed awards notify recipient owner; replay of old receipt sends current selection and experience',
        'presentation failure preserves committed reward; native query and runtime restart recover current values',
        'departed and rejoined old membership generations cannot deliver queued research; current scope can',
        'expired lease and changed recipe refuse projection; unknown old state explicitly clears stale client cache without fabricating levels'],
        source_event_is_fixture=True,production_recipe_configured=False,normal_maintenance_source_integrated=False,
        shared_npc_registered=False,native_gui_verified=False,live_server_changed=False)
    write_json(OUT/'evidence/guild-research-panel-verification.json',result);print(json.dumps(result))


if __name__=='__main__':main()
