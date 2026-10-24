"""Real guild-family events and family-owned archive, disposable stores."""
from pathlib import Path
from dataclasses import replace
from contextlib import closing
import asyncio,json,sqlite3,tempfile,threading
from inspect_client import OUT,write_json
from verify_guild_offices import setup


def sources(f,first,second,guild):
    events=[]
    for family in (first,second):
        pending=f.org.pending_family_guild_history(family%f.org.maintenance_rules.partitions)
        assert len(pending)==1 and pending[0][0]==family
        event=f.org.family_guild_history_event(pending[0][1])
        assert (event.guild,event.family,event.template_id,event.guild_name)==(guild,family,5,'职位帮派')
        assert event.family_token
        events.append(event)
    return tuple(events)


def history(f,family):
    actor=f.org.snapshot(family)[0]['leader']
    token=dict(f.org.family_audience(family).members)[actor]
    return f.org.family_projection(actor,f.epochs[actor],family,token,()).view.history


def consume(f,events):
    from family_guild_history import FamilyGuildHistoryCommand
    for event in events:
        c=FamilyGuildHistoryCommand(event,'delivery:'+str(event.sequence),f.now()+5000)
        f.reject(lambda:f.org.ack_family_guild_history(c,f.now()),'family_guild_history_inbox_missing')
        before=f.org.snapshot(event.family)[0]['revision']
        result=f.org.consume_family_guild_history(c,f.now())
        assert result.family_revision==before+1
        rows=history(f,event.family)
        assert rows[-1].template_id==5 and rows[-1].parameters[1]=='职位帮派'
        assert f.org.consume_family_guild_history(c,f.now())==result
        assert history(f,event.family)==rows
        assert f.org.snapshot(event.family)[0]['revision']==before+1
        assert f.org.ack_family_guild_history(c,f.now())==result
        assert f.org.ack_family_guild_history(c,f.now())==result
        assert not f.org.pending_family_guild_history(event.family%f.org.maintenance_rules.partitions)


def departures(f,first,second,guild,joins):
    from family_guild_history import FamilyGuildHistoryCommand
    def current(family):
        rows=f.org.pending_family_guild_history(family%f.org.maintenance_rules.partitions)
        assert rows and rows[0][0]==family
        return f.org.family_guild_history_event(rows[0][1])
    def delivery(event):return FamilyGuildHistoryCommand(event,'delivery:'+str(event.sequence),f.now()+5000)
    f.org.execute(f.cmd(16,guild,'leave',(second,)),f.now())
    left=current(second)
    assert left.template_id==6 and left.family_token==joins[1].family_token
    with closing(f.accounts.connect()) as db,db:db.execute('UPDATE organizations SET name=? WHERE id=?',('新帮派名',guild))
    f.org.execute(f.cmd(16,guild,'apply'),f.now())
    f.org.execute(f.cmd(1,guild,'review',(second,False)),f.now())
    f.reject(lambda:f.org.family_guild_history_event(left.sequence+1),'guild_family_history_source_missing')
    f.org.execute(f.cmd(16,guild,'apply'),f.now())
    f.org.execute(f.cmd(1,guild,'review',(second,True)),f.now())
    # Pending directory returns earliest only, so obtain the next immutable
    # source by its real sequence; no guessed history row is inserted.
    joined=f.org.family_guild_history_event(left.sequence+1)
    assert joined.template_id==5 and joined.guild_name=='新帮派名' and joined.family_token!=left.family_token
    f.reject(lambda:f.org.consume_family_guild_history(delivery(joined),f.now()),'family_guild_history_order_pending')
    done=f.org.consume_family_guild_history(delivery(left),f.now())
    assert history(f,second)[-1].parameters[1]=='职位帮派'
    f.reject(lambda:f.org.consume_family_guild_history(delivery(joined),f.now()),'family_guild_history_order_pending')
    assert f.org.ack_family_guild_history(delivery(left),f.now())==done
    f.org.consume_family_guild_history(delivery(joined),f.now());f.org.ack_family_guild_history(delivery(joined),f.now())
    assert [c.template_id for c in history(f,second)]==[1,5,6,5]
    f.org.execute(f.cmd(1,guild,'expel',(second,)),f.now())
    expelled=current(second);assert expelled.template_id==6 and expelled.family_token==joined.family_token
    f.org.consume_family_guild_history(delivery(expelled),f.now());f.org.ack_family_guild_history(delivery(expelled),f.now())
    assert [c.template_id for c in history(f,second)]==[1,5,6,5,6]
    from verify_guild_dissolution import terminal
    source,now=terminal(f,first)
    closed=f.org.apply_guild_family_dissolution(source,'terminal-history',now+5000,now)
    assert closed.state=='dissolution_pending'
    retired=current(first);assert retired.template_id==6 and retired.family_token==joins[0].family_token
    receipt=f.org.consume_family_guild_history(delivery(retired),f.now())
    assert f.org.ack_family_guild_history(delivery(retired),f.now())==receipt


def failures(path):
    from family_guild_history import FamilyGuildHistoryCommand
    from faction_domain import OrganizationStore
    f,first,second,guild=setup(path);events=sources(f,first,second,guild);consume(f,events)
    c=f.cmd(16,guild,'leave',(second,),key='history-source-atomic')
    scope=f.org.guild_scope(16,f.epochs[16]);org=f.org.snapshot(guild)
    with closing(f.accounts.connect()) as db,db:
        db.execute("CREATE TRIGGER fixture_history_source BEFORE INSERT ON organization_receipts WHEN NEW.request_id='history-source-atomic' BEGIN SELECT RAISE(ABORT,'history_source_late'); END")
    try:f.org.execute(c,f.now())
    except sqlite3.IntegrityError as error:assert 'history_source_late' in str(error)
    else:raise AssertionError('Late command receipt failure accepted')
    assert f.org.guild_scope(16,f.epochs[16])==scope and f.org.snapshot(guild)==org
    assert not f.org.pending_family_guild_history(second%f.org.maintenance_rules.partitions)
    with closing(f.accounts.connect()) as db,db:db.execute('DROP TRIGGER fixture_history_source')
    result=f.org.execute(c,f.now());assert f.org.execute(c,f.now())==result
    due=f.org.pending_family_guild_history(second%f.org.maintenance_rules.partitions)
    assert len(due)==1
    event=f.org.family_guild_history_event(due[0][1])
    delivery=FamilyGuildHistoryCommand(event,'history-delivery',f.now()+5000)
    before=history(f,second);family=f.org.snapshot(second)
    with closing(f.accounts.connect()) as db,db:
        db.execute("CREATE TRIGGER fixture_history_inbox BEFORE INSERT ON family_guild_history_inbox BEGIN SELECT RAISE(ABORT,'history_inbox_late'); END")
    try:f.org.consume_family_guild_history(delivery,f.now())
    except sqlite3.IntegrityError as error:assert 'history_inbox_late' in str(error)
    else:raise AssertionError('Late inbox failure accepted')
    assert history(f,second)==before and f.org.snapshot(second)==family
    with closing(f.accounts.connect()) as db,db:db.execute('DROP TRIGGER fixture_history_inbox')
    settled=f.org.consume_family_guild_history(delivery,f.now())
    after=history(f,second);assert len(after)==len(before)+1
    with closing(f.accounts.connect()) as db,db:
        db.execute("CREATE TRIGGER fixture_history_ack BEFORE UPDATE OF state ON guild_family_history_outbox WHEN NEW.state='done' BEGIN SELECT RAISE(ABORT,'history_ack_late'); END")
    try:f.org.ack_family_guild_history(delivery,f.now())
    except sqlite3.IntegrityError as error:assert 'history_ack_late' in str(error)
    else:raise AssertionError('Late ack failure accepted')
    assert history(f,second)==after and f.org.pending_family_guild_history(second%f.org.maintenance_rules.partitions)==due
    with closing(f.accounts.connect()) as db,db:db.execute('DROP TRIGGER fixture_history_ack')
    f.org=OrganizationStore(f.accounts.path,f.policy);f.org.initialize()
    assert f.org.consume_family_guild_history(delivery,f.now())==settled
    assert f.org.ack_family_guild_history(delivery,f.now())==settled
    assert history(f,second)==after and not f.org.pending_family_guild_history(second%f.org.maintenance_rules.partitions)
    for changed in (replace(event,guild_name='伪造帮派'),replace(event,family_token='other-generation')):
        f.reject(lambda:f.org.consume_family_guild_history(replace(delivery,event=changed),f.now()),'family_guild_history_source_conflict')
    f.reject(lambda:f.org.consume_family_guild_history(replace(delivery,deadline_ms=0),f.now()),'family_guild_history_deadline')


def unknown(path):
    f,first,second,guild=setup(path)
    # An explicit migration fixture represents an existing relation that never
    # had this outbox. Startup must preserve that lack of historical knowledge.
    with closing(f.accounts.connect()) as db,db:db.execute('DELETE FROM guild_family_history_outbox')
    f.org.initialize()
    assert not f.org.pending_family_guild_history(first%f.org.maintenance_rules.partitions)
    assert not f.org.pending_family_guild_history(second%f.org.maintenance_rules.partitions)
    assert [r.template_id for r in history(f,first)]==[1]
    f.org.execute(f.cmd(2,first,'leave'),f.now())
    assert not f.org.pending_family_guild_history(first%f.org.maintenance_rules.partitions)
    f.org.execute(f.cmd(16,guild,'leave',(second,)),f.now())
    pending=f.org.pending_family_guild_history(second%f.org.maintenance_rules.partitions)
    assert len(pending)==1 and f.org.family_guild_history_event(pending[0][1]).template_id==6


def archive_missing(path):
    from family_guild_history import FamilyGuildHistoryCommand
    f,first,second,guild=setup(path);events=sources(f,first,second,guild)
    command=FamilyGuildHistoryCommand(events[0],'archive-loss',f.now()+5000)
    f.org.consume_family_guild_history(command,f.now())
    with closing(f.accounts.connect()) as db,db:db.execute('DELETE FROM family_history WHERE family=? AND template_id=5',(first,))
    f.reject(lambda:f.org.ack_family_guild_history(command,f.now()),'family_guild_history_archive_unknown')
    f.reject(lambda:f.org.consume_family_guild_history(command,f.now()),'family_guild_history_archive_unknown')
    assert f.org.pending_family_guild_history(first%f.org.maintenance_rules.partitions)


async def runtime_recovery(path):
    from game_runtime import GameRuntime
    from verify_runtime import Peer
    from verify_family_management import panel
    import runtime_storage
    import faction_protocol as p
    f,first,second,guild=setup(path)
    runtime=GameRuntime(f.accounts,runtime_storage.prepare(f.accounts))
    try:
        peer=Peer(runtime);await peer.login(f.accounts.roles(1111)[0])
        f.epochs[1]=runtime.online_snapshot()[1].login_epoch
        scheduler=runtime.social_runtime.organizations.family.maintenance
        await scheduler.run_once(f.now())
        assert [c.template_id for c in history(f,first)]==[1,5]
        assert not f.org.pending_family_guild_history(first%f.org.maintenance_rules.partitions)
        frames=peer.initial+await peer.take()
        courses=[panel(body,include_history=True)[-1] for kind,body in frames if kind==p.UPDATE_FAMILY]
        assert courses and courses[-1][-1][0]==5 and courses[-1][-1][1][1]=='职位帮派'
        await scheduler.run_once(f.now())
        assert [c.template_id for c in history(f,first)]==[1,5]
    finally:await runtime.close()


async def restart_after_consume(path):
    from game_runtime import GameRuntime
    from runtime_core import Backpressure
    import runtime_storage
    f,first,second,guild=setup(path)
    runtime=GameRuntime(f.accounts,runtime_storage.prepare(f.accounts))
    owner=runtime.social_runtime.organizations
    async def stopped_ack(*args):raise Backpressure('fixture guild ack offline')
    owner.ack_family_guild_history=stopped_ack
    try:
        await owner.family.maintenance.run_once(f.now())
        assert [c.template_id for c in history(f,first)]==[1,5]
        revision=f.org.snapshot(first)[0]['revision']
        assert f.org.pending_family_guild_history(first%f.org.maintenance_rules.partitions)
    finally:await runtime.close()
    runtime=GameRuntime(f.accounts,runtime_storage.prepare(f.accounts))
    try:
        await runtime.social_runtime.organizations.family.maintenance.run_once(f.now())
        assert not f.org.pending_family_guild_history(first%f.org.maintenance_rules.partitions)
        assert f.org.snapshot(first)[0]['revision']==revision
        assert [c.template_id for c in history(f,first)]==[1,5]
    finally:await runtime.close()


async def periodic_independence(path):
    from game_runtime import GameRuntime
    from verify_runtime import Peer
    from verify_family_management import panel
    import runtime_storage
    import faction_protocol as p
    f,first,second,guild=setup(path);consume(f,sources(f,first,second,guild))
    runtime=GameRuntime(f.accounts,runtime_storage.prepare(f.accounts))
    entered,released=threading.Event(),threading.Event()
    owner=runtime.social_runtime.organizations;repository=owner.store
    original=repository.consume_family_guild_history
    def blocked(command,now):
        if command.event.family==second and command.event.template_id==6:
            entered.set()
            if not released.wait(5):raise TimeoutError('fixture history release missing')
        return original(command,now)
    repository.consume_family_guild_history=blocked
    try:
        peers={};roles={r['id']:r for r in f.accounts.roles(1111)}
        for rid in (1,16):
            peer=Peer(runtime);await peer.login(roles[rid]);peers[rid]=peer
            f.epochs[rid]=runtime.online_snapshot()[rid].login_epoch
        await owner.command(f.cmd(16,guild,'leave',(second,)),f.now())
        # No run_once call: the real periodic directory starts this consumer.
        assert await asyncio.to_thread(entered.wait,8)
        try:
            await asyncio.wait_for(owner.command(f.cmd(1,first,'set_family_products',(1,-1)),f.now()),2)
            await asyncio.wait_for(owner.command(f.cmd(1,guild,'set_research',(300101,)),f.now()),2)
            assert (100,b'next') in await asyncio.wait_for(peers[1].request(100,b'next'),2)
            assert not released.is_set()
        finally:released.set()
        await owner.family.maintenance.idle()
        frames=await peers[16].take()
        courses=[panel(body,include_history=True)[-1] for kind,body in frames if kind==p.UPDATE_FAMILY]
        assert courses and [row[0] for row in courses[-1]]==[1,5,6]
        assert not f.org.pending_family_guild_history(second%f.org.maintenance_rules.partitions)
    finally:
        released.set();await runtime.close()


def fair_directory(path):
    from verify_faction_payments import Fixture
    from faction_domain import OrganizationStore
    f=Fixture(path);create=f.family();f.fund(create)
    first=f.org.execute(create,f.now())['organization']
    with closing(f.accounts.connect()) as db,db:db.execute('UPDATE organizations SET level=3 WHERE id=?',(first,))
    create_guild=f.cmd(1,first,'create_guild',('公平帮派','同心协力',create.args[2]));f.fund(create_guild)
    guild=f.org.execute(create_guild,f.now())['organization']
    # Padding only allocates unused legacy IDs; actual tested memberships and
    # every outbox event still come from public creation/admission/leave.
    with closing(f.accounts.connect()) as db,db:
        for i in range(14):db.execute("INSERT INTO organizations(kind,name,aim,leader) VALUES('family',?,'pad',1)",(f'旧档{i}',))
    other=f.family(16,name='轮转家族');f.fund(other);second=f.org.execute(other,f.now())['organization']
    assert second-first==16
    f.org.execute(f.cmd(16,guild,'apply'),f.now());f.org.execute(f.cmd(1,guild,'review',(second,True)),f.now())
    # Tenure is an explicit old-member metadata fixture, not a history event.
    with closing(f.accounts.connect()) as db,db:
        db.execute('UPDATE guild_families SET joined_ms=? WHERE guild=?',(f.now()-f.policy['guild_leader_tenure_ms']-1000,guild))
        db.execute('UPDATE family_members SET joined_ms=? WHERE role_id=16',(f.now()-f.policy['guild_leader_tenure_ms']-1000,))
    f.org.execute(f.cmd(1,guild,'appoint',(16,'leader')),f.now())
    for _ in range(4):
        f.org.execute(f.cmd(1,guild,'leave',(first,)),f.now())
        f.org.execute(f.cmd(1,guild,'apply'),f.now())
        f.org.execute(f.cmd(16,guild,'review',(first,True)),f.now())
    raw=json.loads(json.dumps(f.policy));raw['family_maintenance']['batch_limit']=1
    store=OrganizationStore(f.accounts.path,raw)
    part=first%store.maintenance_rules.partitions
    one=store.pending_family_guild_history(part);two=store.pending_family_guild_history(part,one[0][0])
    assert len(one)==len(two)==1 and one[0][0]==first and two[0][0]==second
    assert store.family_guild_history_event(one[0][1]).template_id==5
    assert store.pending_family_guild_history(part,two[0][0])==()
    page=store.family_guild_history_page(part)
    assert page.entries==one and page.ceiling==second
    next_page=store.family_guild_history_page(part,one[0][0],page.ceiling)
    assert next_page.entries==two and next_page.ceiling==second
    assert not store.family_guild_history_page(part,second,page.ceiling).entries
    for after,ceiling in ((first,None),(second,first),(None,True),(None,0)):
        f.reject(lambda:store.family_guild_history_page(part,after,ceiling),'invalid_family_guild_history_scan')


def cross_guild_order(path):
    from family_guild_history import FamilyGuildHistoryCommand
    from currency import CurrencyChange,apply_currency
    f,first,second,guild=setup(path);consume(f,sources(f,first,second,guild))
    f.org.execute(f.cmd(16,guild,'leave',(second,)),f.now())
    left=f.org.family_guild_history_event(f.org.pending_family_guild_history(second%f.org.maintenance_rules.partitions)[0][1])
    with closing(f.accounts.connect()) as db,db:
        for rid in range(19,31):db.execute('INSERT INTO roles(id,account_id,name,school,shape,level) VALUES(?,1111,?,12,1010101,40)',(rid,f'新角色{rid}'))
        db.execute('UPDATE organizations SET level=3 WHERE id=?',(second,))
    for rid in range(19,31):
        f.epochs[rid]=f.accounts.acquire_lease(1111,rid)
        f.org.execute(f.cmd(rid,second,'apply'),f.now());f.org.execute(f.cmd(16,second,'review',(rid,True)),f.now())
    # Explicit disposable currency credit; funding still uses the real fenced
    # wallet debit/organization funding Interface, never a fabricated grant.
    f.tx(16,lambda db:apply_currency(db,1111,16,f.epochs[16],CurrencyChange('cross-guild-fixture',
        'explicit_fixture','isolated_history',(('cash',f.policy['guild_create_fee']),)),f.rules))
    command=f.cmd(16,second,'create_guild',('跨帮新居','同心协力',tuple((rid,f.epochs[rid]) for rid in range(16,31))))
    f.fund(command);new=f.org.execute(command,f.now())['organization']
    joined=f.org.family_guild_history_event(left.sequence+1)
    assert joined.guild==new and joined.family==second and joined.family_token!=left.family_token
    def delivery(event):return FamilyGuildHistoryCommand(event,'cross:'+str(event.sequence),f.now()+5000)
    f.reject(lambda:f.org.consume_family_guild_history(delivery(joined),f.now()),'family_guild_history_order_pending')
    f.org.consume_family_guild_history(delivery(left),f.now());f.org.ack_family_guild_history(delivery(left),f.now())
    f.org.consume_family_guild_history(delivery(joined),f.now());f.org.ack_family_guild_history(delivery(joined),f.now())
    rows=history(f,second)
    assert [r.template_id for r in rows]==[1,5,6,5]
    assert [r.parameters[1] for r in rows[1:]]==['职位帮派','职位帮派','跨帮新居']


async def presentation_failure(path):
    from game_runtime import GameRuntime
    from family_guild_history import FamilyGuildHistoryCommand
    import runtime_storage
    f,first,second,guild=setup(path);event=sources(f,first,second,guild)[0]
    runtime=GameRuntime(f.accounts,runtime_storage.prepare(f.accounts))
    owner=runtime.social_runtime.organizations
    await owner.family.maintenance.close()
    old=owner.store.family_audience
    def unavailable(*args):raise sqlite3.OperationalError('fixture presentation database is locked')
    owner.store.family_audience=unavailable
    try:
        c=FamilyGuildHistoryCommand(event,'presentation-failure',f.now()+5000)
        result=await owner.consume_family_guild_history(c,f.now())
        assert result.family==first
        assert [row.template_id for row in history(f,first)]==[1,5]
        assert await owner.ack_family_guild_history(c,f.now())==result
    finally:
        owner.store.family_audience=old;await runtime.close()


async def scheduler_backpressure(*,backlog=False):
    """Actual scheduler with isolated storage/owner Adapters, capacity one.

    This deliberately tests directory scheduling, not membership persistence;
    the separate real Store/Runtime cases cover committed history effects.
    """
    from types import SimpleNamespace
    from family_guild_history import FamilyGuildHistoryEvent
    from family_maintenance_runtime import FamilyMaintenanceRuntime
    rows={1:[11,12] if backlog else [11],2:[21]};consumed=[]
    class Directory:
        maintenance_rules=SimpleNamespace(batch_limit=2,partitions=1)
        def pending_family_guild_history(self,partition,after):
            return tuple((family,sequences[0]) for family,sequences in sorted(rows.items()) if family>(after or 0))[:2]
        def family_guild_history_page(self,partition,after,ceiling):
            from family_guild_history import FamilyGuildHistoryPage
            if ceiling is None:ceiling=max(rows,default=None)
            entries=tuple((family,sequences[0]) for family,sequences in sorted(rows.items())
                if family>(after or 0) and family<=ceiling)[:2]
            return FamilyGuildHistoryPage(entries,ceiling)
        def family_guild_history_event(self,sequence):
            return FamilyGuildHistoryEvent(sequence,99,sequence//10,'generation',5,'帮派',0,'source:'+str(sequence))
    class IO:
        async def run(self,key,operation,*args):return operation(*args)
    class Owner:
        policy={'owner_limit':1,'family_maintenance':{'scheduler_enabled':False,'scan_interval_ms':5000}}
        async def consume_family_guild_history(self,command,now):consumed.append(command.event.family)
        async def ack_family_guild_history(self,command,now):
            family=command.event.family;rows[family].pop(0)
            if not rows[family]:rows.pop(family)
    runtime=SimpleNamespace(io=IO(),log=lambda **kw:None)
    scheduler=FamilyMaintenanceRuntime(SimpleNamespace(owner=Owner(),rt=runtime,store=Directory()))
    try:
        await scheduler.scan_history(0);await scheduler.idle()
        assert consumed==[1]
        # New higher IDs keep arriving while the previously rejected family
        # remains pending. It must be retried before advancing to new arrivals.
        for family in range(3,9):
            rows[family]=[family*10+1]
            await scheduler.scan_history(0);await scheduler.idle()
        assert consumed[1]==2,('Capacity rejection skipped an older family',consumed)
        if backlog:assert consumed.count(1)==2,('New arrivals prevent revisiting an older family backlog',consumed)
    finally:await scheduler.close()


def main():
    with tempfile.TemporaryDirectory() as d:
        f,first,second,guild=setup(Path(d)/'history.db')
        events=sources(f,first,second,guild);consume(f,events)
        departures(f,first,second,guild,events)
        failures(Path(d)/'failures.db');unknown(Path(d)/'unknown.db');archive_missing(Path(d)/'archive-loss.db')
        asyncio.run(runtime_recovery(Path(d)/'runtime.db'))
        asyncio.run(restart_after_consume(Path(d)/'restart.db'))
        asyncio.run(periodic_independence(Path(d)/'periodic.db'))
        fair_directory(Path(d)/'directory.db')
        cross_guild_order(Path(d)/'cross-guild.db')
        asyncio.run(presentation_failure(Path(d)/'presentation.db'))
        asyncio.run(scheduler_backpressure())
        asyncio.run(scheduler_backpressure(backlog=True))
    report=dict(passed=['real guild founding/admission sources and family-owned history consumption with guild acknowledgement',
        'voluntary departure, rejected/reaccepted application, expulsion and terminal retirement preserve order, including two different guilds',
        'late command/source and family inbox failures roll back; failed ack/presentation preserve consumed history',
        'source forgery, expiry, out-of-order delivery, missing inbox/archive and unknown historical relations refuse fake completion',
        'family consumption before runtime restart recovers guild ack without duplicate history or revision',
        'actual periodic source and encrypted native family panel display history while another family/guild command and heartbeat remain independent',
        'bounded family-ID directory seeks skip a single family backlog and preserve another family in the same partition',
        'actual scheduler capacity-one backpressure retries an unscheduled older family despite continuing new directory arrivals (isolated Adapters)',
        'bounded scheduler scan rounds revisit an older family backlog despite continuing new higher family IDs (isolated Adapters)'],
        same_sqlite_two_owner_outbox_inbox_verified=True,cross_database_delivery_verified=False,
        shared_entry_files_edited=False,native_gui_verified=False,live_server_changed=False,
        family_activity_template7_producer_implemented=False)
    write_json(OUT/'evidence/family-guild-history-verification.json',report);print(json.dumps(report))


if __name__=='__main__':main()
