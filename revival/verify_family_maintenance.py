"""Family maintenance through public organization storage; no live server."""
from pathlib import Path
from dataclasses import replace
from contextlib import closing
import asyncio,tempfile,threading
from verify_family_products import make
from family_maintenance import MaintenanceCommand,ClockResumeCommand
from faction_domain import OrganizationStore
import json
import sqlite3
from inspect_client import OUT,write_json


def check_clock(f,family):
    clock=f.org.family_maintenance_snapshot(family)
    assert clock.family==family and clock.state=='active'
    assert clock.next_due_ms==clock.created_ms+3600000 and clock.revision==1
    assert clock.origin.startswith('designed_new_family')
    first=clock
    f.org.initialize()
    assert f.org.family_maintenance_snapshot(family)==first


def check_normal(f,family):
    for choice in ((1,-1),(-1,1)):f.org.execute(f.cmd(1,family,'set_family_products',choice),f.now())
    clock=f.org.family_maintenance_snapshot(family)
    command=MaintenanceCommand(family,clock.next_due_ms,tuple((rid,f.epochs[rid]) for rid in range(1,16)),
        'hour-1',clock.next_due_ms+5000)
    cash=f.cash(1)
    receipt=f.org.maintain_family(command,clock.next_due_ms)
    assert receipt.mode=='normal' and receipt.fee==37000 and receipt.online_count==15
    assert receipt.funds_after==2963000 and receipt.popularity_after==1020
    assert receipt.drug_after==30 and receipt.special_after==60
    assert f.org.family_assets(family).funds==2963000 and f.cash(1)==cash
    state=f.org.family_products_snapshot(family)
    assert state.drug_stock==30 and state.special_stock==60
    assert f.org.family_maintenance_snapshot(family).next_due_ms==clock.next_due_ms+3600000
    assert f.org.maintain_family(command,clock.next_due_ms+1)==receipt
    assert f.org.family_assets(family).funds==2963000
    f.reject(lambda:f.org.maintain_family(replace(command,online=()),clock.next_due_ms+1),'maintenance_intent_conflict')


def tick(f,family,online=()):
    clock=f.org.family_maintenance_snapshot(family)
    command=MaintenanceCommand(family,clock.next_due_ms,online,'hour:'+str(clock.next_due_ms),clock.next_due_ms+5000)
    return command,f.org.maintain_family(command,clock.next_due_ms)


def check_simple(f,family):
    # At the exact strict threshold, only base maintenance is due. Existing
    # stock stays available, and the enabled stock is not replenished.
    with closing(f.accounts.connect()) as db,db:
        db.execute('UPDATE family_assets SET funds=?,popularity=1000 WHERE family=?',(48*37000,family))
        db.execute('UPDATE family_products SET drug_stock=2,special_stock=3 WHERE family=?',(family,))
    command,receipt=tick(f,family)
    assert receipt.mode=='simple' and receipt.fee==12000 and receipt.funds_after==48*37000-12000
    assert receipt.popularity_after==990 and (receipt.drug_after,receipt.special_after)==(2,3)
    # Starting popularity controls the 50% surcharge, including basic-only cost.
    command,receipt=tick(f,family)
    assert receipt.mode=='simple' and receipt.fee==18000 and receipt.popularity_after==980
    with closing(f.accounts.connect()) as db,db:
        db.execute('UPDATE family_assets SET funds=3000000,popularity=999 WHERE family=?',(family,))
    command,receipt=tick(f,family)
    assert receipt.mode=='normal' and receipt.fee==55500 and receipt.popularity_after==989
    assert (receipt.drug_after,receipt.special_after)==(30,60)


def check_downgrade(f,family):
    with closing(f.accounts.connect()) as db,db:
        db.execute('UPDATE organizations SET level=3 WHERE id=?',(family,))
        db.execute('UPDATE family_assets SET funds=100,popularity=1000,construction=49 WHERE family=?',(family,))
    command,receipt=tick(f,family)
    assert receipt.mode=='simple' and receipt.fee==100
    assert (receipt.level_before,receipt.level_after,receipt.state)==(3,2,'active')
    assert receipt.funds_after==5000000 and receipt.popularity_after==1990
    org,_=f.org.snapshot(family)
    assert org['level']==2 and f.org.family_assets(family).construction==0
    assert f.org.maintain_family(command,command.due_ms+1)==receipt
    assert f.org.family_assets(family).funds==5000000
    with closing(f.accounts.connect()) as db,db:
        db.execute('UPDATE organizations SET level=1 WHERE id=?',(family,))
        db.execute('UPDATE family_assets SET popularity=1 WHERE family=?',(family,))
    command,receipt=tick(f,family)
    assert (receipt.level_before,receipt.level_after,receipt.state)==(1,0,'dissolution_pending')
    clock=f.org.family_maintenance_snapshot(family)
    assert clock.state=='dissolution_pending'
    pending=f.org.family_dissolution_pending(family)
    assert pending.family==family and pending.due_ms==command.due_ms
    assert tuple(rid for rid,_ in pending.members)==tuple(range(1,16))
    assert len(pending.members)==len({generation for _,generation in pending.members})
    f.reject(lambda:tick(f,family),'family_dissolution_pending')
    assert f.org.maintain_family(command,command.due_ms+1)==receipt


def check_resume(f,family):
    first=f.org.family_maintenance_snapshot(family)
    now=first.next_due_ms+300001
    overdue=MaintenanceCommand(family,first.next_due_ms,(),'overdue',now+5000)
    f.reject(lambda:f.org.maintain_family(overdue,now),'maintenance_overdue_resume_required')
    assets=f.org.family_assets(family);products=f.org.family_products_snapshot(family)
    resume=ClockResumeCommand(family,first.next_due_ms,'resume-first',now+5000)
    result=f.org.resume_family_maintenance(resume,now)
    assert result.skipped_from_ms==first.next_due_ms and result.next_due_ms==now+3600000
    assert f.org.family_assets(family)==assets and f.org.family_products_snapshot(family)==products
    assert f.org.resume_family_maintenance(resume,now+1)==result
    assert f.org.family_maintenance_snapshot(family).next_due_ms==now+3600000
    f.reject(lambda:f.org.maintain_family(overdue,now),'maintenance_not_due')


def check_rollback(f,family):
    clock=f.org.family_maintenance_snapshot(family)
    assets=f.org.family_assets(family);products=f.org.family_products_snapshot(family)
    command=MaintenanceCommand(family,clock.next_due_ms,(),'late-fault',clock.next_due_ms+5000)
    for changed,now,error in ((replace(command,online=((1,True),)),clock.next_due_ms,'invalid_family_maintenance_observation'),
            (replace(command,online=((1,f.epochs[1]),(1,f.epochs[1]))),clock.next_due_ms,'invalid_family_maintenance_observation'),
            (command,clock.next_due_ms-1,'maintenance_not_due'),
            (replace(command,deadline_ms=clock.next_due_ms-1),clock.next_due_ms,'maintenance_deadline')):
        f.reject(lambda changed=changed,now=now:f.org.maintain_family(changed,now),error)
    with closing(f.accounts.connect()) as db,db:
        db.execute("CREATE TRIGGER fail_family_tick BEFORE INSERT ON family_maintenance_receipts BEGIN SELECT RAISE(ABORT,'controlled_receipt_failure'); END")
    try:f.org.maintain_family(command,clock.next_due_ms)
    except sqlite3.IntegrityError:pass
    else:raise AssertionError('Controlled late receipt failure did not fire')
    assert f.org.family_maintenance_snapshot(family)==clock
    assert f.org.family_assets(family)==assets and f.org.family_products_snapshot(family)==products
    with closing(f.accounts.connect()) as db,db:db.execute('DROP TRIGGER fail_family_tick')
    receipt=f.org.maintain_family(command,clock.next_due_ms)
    assert receipt.funds_before==assets.funds and receipt.funds_after==assets.funds-12000
    assert receipt.recovery_funds==0 and receipt.recipe=='2026-10-23.family-maintenance.1'


def check_unknown_clock(f,family):
    clock=f.org.family_maintenance_snapshot(family)
    assets=f.org.family_assets(family)
    with closing(f.accounts.connect()) as db,db:db.execute('DELETE FROM family_maintenance WHERE family=?',(family,))
    f.org.initialize()
    f.reject(lambda:f.org.family_maintenance_snapshot(family),'family_maintenance_unknown')
    command=MaintenanceCommand(family,clock.next_due_ms,(),'unknown-clock',clock.next_due_ms+5000)
    f.reject(lambda:f.org.maintain_family(command,clock.next_due_ms),'family_maintenance_unknown')
    assert f.org.family_assets(family)==assets


async def check_background(f,family):
    from game_runtime import GameRuntime
    import runtime_storage
    import time
    due=int(time.time()*1000)+20
    with closing(f.accounts.connect()) as db,db:
        # Plausible aged clock, explicitly disposable. Production new clocks
        # keep the one-hour interval rather than using this accelerated age.
        db.execute('UPDATE family_maintenance SET created_ms=?,next_due_ms=? WHERE family=?',(due-3600000,due,family))
    runtime=GameRuntime(f.accounts,runtime_storage.prepare(f.accounts))
    completed=threading.Event()
    repository=runtime.social_runtime.organizations.store
    original=repository.maintain_family
    def observe(command,now):
        result=original(command,now);completed.set();return result
    repository.maintain_family=observe
    try:
        assert await asyncio.to_thread(completed.wait,8),'Actual periodic directory did not dispatch maintenance'
        await runtime.social_runtime.organizations.family.maintenance.idle()
        assert f.org.family_assets(family).funds==2988000
        assert f.org.family_maintenance_snapshot(family).next_due_ms==due+3600000
    finally:await runtime.close()


async def check_runtime(f,family):
    from game_runtime import GameRuntime
    import runtime_storage
    runtime=GameRuntime(f.accounts,runtime_storage.prepare(f.accounts))
    try:
        clock=f.org.family_maintenance_snapshot(family)
        command=MaintenanceCommand(family,clock.next_due_ms,(),'runtime-tick',clock.next_due_ms+5000)
        first,second=await asyncio.gather(*(runtime.social_runtime.organizations.maintain_family(command,clock.next_due_ms) for _ in range(2)))
        assert first==second and first.fee==12000 and first.popularity_after==990
        assert f.org.family_assets(family).funds==2988000
        scheduler=runtime.social_runtime.organizations.family.maintenance
        await scheduler.run_once(clock.next_due_ms+3600000)
        assert f.org.family_assets(family).funds==2970000
        assert f.org.family_assets(family).popularity==980
    finally:await runtime.close()


async def check_independence(f,first,second):
    from game_runtime import GameRuntime
    from verify_runtime import Peer
    import runtime_storage
    runtime=GameRuntime(f.accounts,runtime_storage.prepare(f.accounts))
    entered,released=threading.Event(),threading.Event()
    repository=runtime.social_runtime.organizations.store
    original=repository.maintain_family
    def slow(command,now):
        if command.family==first:
            entered.set()
            if not released.wait(5):raise TimeoutError('controlled_release_missing')
        return original(command,now)
    repository.maintain_family=slow
    try:
        peer=Peer(runtime)
        role=next(role for role in f.accounts.roles(1111) if role['id']==16)
        await peer.login(role)
        clock=f.org.family_maintenance_snapshot(first)
        slow_command=MaintenanceCommand(first,clock.next_due_ms,(),'blocked-maintenance',clock.next_due_ms+5000)
        pending=asyncio.create_task(runtime.social_runtime.organizations.maintain_family(slow_command,clock.next_due_ms))
        assert await asyncio.to_thread(entered.wait,2)
        try:
            other=f.org.family_maintenance_snapshot(second)
            command=MaintenanceCommand(second,other.next_due_ms,(),'other-maintenance',other.next_due_ms+5000)
            done=await asyncio.wait_for(runtime.social_runtime.organizations.maintain_family(command,other.next_due_ms),2)
            assert done.fee==12000 and not pending.done()
            replies=await asyncio.wait_for(peer.request(100,b'ping'),2)
            # The independent family's newly committed panel can legitimately
            # arrive on this same native stream before the heartbeat echo.
            assert replies.count((100,b'ping'))==1
            assert not pending.done()
        finally:released.set()
        assert (await pending).fee==12000
        with closing(f.accounts.connect()) as db,db:
            db.execute('UPDATE family_assets SET popularity=1 WHERE family=?',(second,))
        terminal=f.org.family_maintenance_snapshot(second)
        result=await runtime.social_runtime.organizations.maintain_family(
            MaintenanceCommand(second,terminal.next_due_ms,(),'terminal-online',terminal.next_due_ms+5000),terminal.next_due_ms)
        assert result.state=='dissolution_pending'
        import faction_protocol as fp
        assert (fp.LEFT_FAMILY,b'') in await peer.take()
    finally:
        released.set()
        await runtime.close()


def check_directory(f,first,second):
    policy=json.loads(json.dumps(f.policy))
    policy['family_maintenance']['batch_limit']=1
    store=OrganizationStore(f.accounts.path,policy)
    a=store.family_maintenance_snapshot(first);b=store.family_maintenance_snapshot(second)
    now=max(a.next_due_ms,b.next_due_ms)
    assert first%16==second%16
    assert store.due_family_maintenance(first%16,now)==((first,a.next_due_ms),)
    assert store.due_family_maintenance(first%16,now,(a.next_due_ms,first))==((second,b.next_due_ms),)


def check_pending_permissions(f,family):
    with closing(f.accounts.connect()) as db,db:db.execute('UPDATE organizations SET level=3 WHERE id=?',(family,))
    command=f.cmd(1,family,'create_guild',('待解帮派','同心协力',tuple((rid,f.epochs[rid]) for rid in range(1,16))))
    f.fund(command);guild=f.org.execute(command,f.now())['organization']
    assert f.org.guild_scope(1,f.epochs[1])[0]==guild
    event=f.org.chat(guild,1,f.epochs[1],'排队中的旧帮派消息',f.now())
    family_event=f.org.chat(family,1,f.epochs[1],'排队中的旧家族消息',f.now())
    with closing(f.accounts.connect()) as db,db:
        db.execute('UPDATE organizations SET level=1 WHERE id=?',(family,))
        db.execute('UPDATE family_assets SET popularity=1 WHERE family=?',(family,))
    _,receipt=tick(f,family)
    assert receipt.state=='dissolution_pending'
    f.reject(lambda:f.org.guild_scope(1,f.epochs[1]),'not_in_guild')
    f.reject(lambda:f.org.membership(1,f.epochs[1],'family'),'not_in_family')
    f.reject(lambda:f.org.chat(guild,1,f.epochs[1],'关闭后消息',f.now()),'not_member')
    assert not f.org.authorize_delivery(event,1)
    assert not f.org.authorize_delivery(family_event,1)
    assert f.org.snapshot(guild)[1]==()
    f.reject(lambda:f.org.execute(f.cmd(1,guild,'change_aim',('关闭后修改宗旨',)),f.now()),'not_member')
    f.reject(lambda:f.org.execute(f.cmd(1,guild,'set_authority',(1,)),f.now()),'not_member')


if __name__=='__main__':
    with tempfile.TemporaryDirectory() as directory:
        f,family=make(directory)
        check_clock(f,family)
        check_normal(f,family)
        check_simple(f,family)
        check_downgrade(f,family)
    with tempfile.TemporaryDirectory() as directory:
        f,family=make(directory)
        check_resume(f,family)
    with tempfile.TemporaryDirectory() as directory:
        f,family=make(directory)
        asyncio.run(check_runtime(f,family))
    with tempfile.TemporaryDirectory() as directory:
        f,first=make(directory)
        command=f.family(16,name='独立家族');f.fund(command)
        second=f.org.execute(command,f.now())['organization']
        asyncio.run(check_independence(f,first,second))
    with tempfile.TemporaryDirectory() as directory:
        f,first=make(directory)
        # Explicit sparse allocated IDs put two actual created families into
        # one directory partition; no membership or asset bypass is used.
        with closing(f.accounts.connect()) as db,db:db.execute("UPDATE sqlite_sequence SET seq=16 WHERE name='organizations'")
        command=f.family(16,name='分页家族');f.fund(command)
        second=f.org.execute(command,f.now())['organization']
        check_directory(f,first,second)
    with tempfile.TemporaryDirectory() as directory:
        f,family=make(directory)
        check_rollback(f,family)
    with tempfile.TemporaryDirectory() as directory:
        f,family=make(directory)
        asyncio.run(check_background(f,family))
    with tempfile.TemporaryDirectory() as directory:
        f,family=make(directory)
        check_pending_permissions(f,family)
    with tempfile.TemporaryDirectory() as directory:
        f,family=make(directory)
        check_unknown_clock(f,family)
    result=dict(passed=['explicit new-family durable hourly clock; startup does not reset it',
        'normal maintenance, bounded observed online population, stock refresh, role cash untouched',
        'same family/hour replay is single-charge; changed observation conflicts',
        'strict normal threshold; simple base-only charge and preserved inventory',
        'low starting popularity applies designed fifty-percent total/base fee order',
        'downgrade adds client-text five-million funds and one-thousand popularity once',
        'terminal level zero creates fenced durable dissolution intent; further ticks stop',
        'overdue pause/resume records new clock without invented online history or backcharge',
        'actual organization owner serializes duplicate ticks and scheduler dispatch',
        'controlled blocked family persistence allows another family commit/heartbeat; terminal wake clears online native family',
        'bounded indexed directory supports continuation past an earlier failing family',
        'malformed/early/expired observations and late receipt fault leave assets and clock atomic',
        'actual periodic directory automatically dispatches a due family and cleanly drains on close',
        'pending family revokes native membership/guild scope and mutations; queued family/guild messages are filtered',
        'startup does not invent historical maintenance clocks or alter unknown-family assets'],
        live_server_changed=False,native_gui_verified=False,
        actual_periodic_source_integrated=True,original_hourly_formula_verified=False,
        dissolution_role_guild_task_consumers_integrated=False,automatic_construction_upgrade_implemented=False)
    write_json(OUT/'evidence/family-maintenance-verification.json',result);print(json.dumps(result))
