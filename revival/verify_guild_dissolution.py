"""Guild-owned family dissolution through real public storage/runtime Interfaces."""
from pathlib import Path
from contextlib import closing
import tempfile
import asyncio
from verify_guild_offices import setup
from verify_family_maintenance import tick
from dataclasses import replace
import sqlite3
import json
import threading
from inspect_client import OUT,write_json


def terminal(f,family):
    with closing(f.accounts.connect()) as db,db:
        db.execute('UPDATE organizations SET level=1 WHERE id=?',(family,))
        db.execute('UPDATE family_assets SET popularity=1 WHERE family=?',(family,))
    command,receipt=tick(f,family)
    assert receipt.state=='dissolution_pending'
    return f.org.family_dissolution_pending(family),command.due_ms


def check_successor(directory):
    f,first,second,guild=setup(Path(directory)/'guild-closure.db')
    f.org.execute(f.cmd(1,guild,'appoint',(17,'deputy')),f.now())
    f.org.execute(f.cmd(1,guild,'set_authority',(17,0,True)),f.now())
    event,now=terminal(f,first)
    receipt=f.org.apply_guild_family_dissolution(event,'close-family-1',now+5000,now)
    assert receipt.guild==guild and receipt.old_leader==1 and receipt.new_leader==17
    assert receipt.state=='active' and receipt.family_token==event.guild_token
    assert f.org.family_guild(first) is None
    org,members=f.org.snapshot(guild)
    assert org['leader']==17 and members==(16,17,18)
    office=f.org.guild_office_snapshot(guild)
    assert office.leader==17 and office.deputy_authority==0 and not office.offices
    assert f.org.apply_guild_family_dissolution(event,'retry-other-request',now+5000,now+1)==receipt


def check_last_family(directory):
    f,first,second,guild=setup(Path(directory)/'guild-last-family.db')
    f.org.execute(f.cmd(16,guild,'leave',(second,)),f.now())
    assets=f.org.guild_assets(guild)
    event,now=terminal(f,first)
    receipt=f.org.apply_guild_family_dissolution(event,'close-last-family',now+5000,now)
    assert receipt.state=='dissolution_pending' and receipt.new_leader==0
    assert f.org.guild_lifecycle(guild).state=='dissolution_pending'
    assert f.org.guild_assets(guild)==assets
    assert f.org.family_guild(first) is None
    f.reject(lambda:f.org.snapshot(guild),'guild_dissolution_pending')
    f.reject(lambda:f.org.execute(f.cmd(16,guild,'apply'),f.now()),'guild_dissolution_pending')
    assert f.org.apply_guild_family_dissolution(event,'last-retry',now+5000,now+1)==receipt
    f.org=type(f.org)(f.accounts.path,f.policy);f.org.initialize()
    assert f.org.guild_lifecycle(guild).state=='dissolution_pending'
    assert f.org.apply_guild_family_dissolution(event,'after-restart',now+5000,now+2)==receipt


async def check_automatic(directory):
    from game_runtime import GameRuntime
    import runtime_storage
    f,first,second,guild=setup(Path(directory)/'guild-auto-closure.db')
    event,stamp=terminal(f,first)
    runtime=GameRuntime(f.accounts,runtime_storage.prepare(f.accounts))
    try:
        scheduler=runtime.social_runtime.organizations.family.maintenance
        await scheduler.run_once(f.now())
        assert f.org.family_guild(first) is None,'durable closure was not dispatched'
        assert f.org.snapshot(guild)[0]['leader']==16
        assert f.org.family_guild_dissolution_done(first,event.due_ms)
        # Remaining role/task/map cleanup is still pending, not falsely acked.
        assert f.org.family_dissolution_pending(first)==event
        await scheduler.run_once(f.now())
        assert f.org.snapshot(guild)[0]['revision']==4
    finally:await runtime.close()


def check_unconsumed_member(directory,refresh_first=False):
    f,first,second,guild=setup(Path(directory)/f'guild-late-join-{refresh_first}.db')
    f.org.execute(f.cmd(2,first,'leave'),f.now())
    f.org.execute(f.cmd(2,first,'apply'),f.now())
    f.org.execute(f.cmd(1,first,'review',(2,True)),f.now())
    # Guild has not consumed the family join event into its read model yet.
    event,now=terminal(f,first)
    if refresh_first:f.org.refresh_guild(guild)
    receipt=f.org.apply_guild_family_dissolution(event,'unconsumed-new-member',now+5000,now)
    assert receipt.new_leader==16 and (2,dict(event.members)[2]) in receipt.closed_memberships
    assert f.org.family_guild(first) is None


def check_pending_successor(directory):
    f,first,second,guild=setup(Path(directory)/'guild-pending-successor.db')
    first_event,now=terminal(f,first)
    second_event,other_now=terminal(f,second)
    receipt=f.org.apply_guild_family_dissolution(first_event,'wait-successor',now+5000,now)
    assert receipt.state=='succession_pending' and receipt.new_leader==0
    f.reject(lambda:f.org.snapshot(guild),'guild_succession_pending')
    assert f.org.guild_audience(guild).members==()
    result=f.org.apply_guild_family_dissolution(second_event,'close-other',other_now+5000,other_now)
    assert result.state=='dissolution_pending' and f.org.family_guild(second) is None
    assert f.org.guild_lifecycle(guild).state=='dissolution_pending'


def check_faults(directory):
    from family_maintenance import FamilyGuildClosureCommand
    f,first,second,guild=setup(Path(directory)/'guild-closure-faults.db')
    event,now=terminal(f,first)
    before=f.org.snapshot(guild);assets=f.org.guild_assets(guild)
    f.reject(lambda:f.org.apply_guild_family_dissolution(replace(event,guild_token='stale'),
        'stale-token',now+5000,now),'source_missing')
    f.reject(lambda:f.org.apply_guild_family_dissolution(replace(event,members=event.members[:-1]),
        'missing-member',now+5000,now),'source_missing')
    f.reject(lambda:f.org.apply_guild_family_dissolution(event,'expired',now-1,now),'deadline')
    command=FamilyGuildClosureCommand(event,'ack-without-commit',now+5000)
    f.reject(lambda:f.org.ack_family_guild_dissolution(command,now),'receipt_missing')
    assert not f.org.family_guild_dissolution_done(first,event.due_ms)
    with closing(f.accounts.connect()) as db,db:
        db.execute("CREATE TRIGGER fixture_closure_abort BEFORE INSERT ON guild_family_dissolution_receipts BEGIN SELECT RAISE(ABORT,'late_receipt_fault'); END")
    try:f.org.apply_guild_family_dissolution(event,'late-fault',now+5000,now)
    except sqlite3.IntegrityError:pass
    else:raise AssertionError('Late receipt fault ignored')
    assert f.org.snapshot(guild)==before and f.org.guild_assets(guild)==assets
    assert f.org.family_guild(first)==guild and f.org.guild_lifecycle(guild).state=='active'
    with closing(f.accounts.connect()) as db,db:db.execute('DROP TRIGGER fixture_closure_abort')
    receipt=f.org.apply_guild_family_dissolution(event,'recover-fault',now+5000,now)
    assert receipt.new_leader==16
    assert f.org.ack_family_guild_dissolution(command,now)
    assert f.org.ack_family_guild_dissolution(command,now+1)


def check_unknown_and_generation(directory):
    f,first,second,guild=setup(Path(directory)/'guild-unknown-member.db')
    event,now=terminal(f,first)
    with closing(f.accounts.connect()) as db,db:
        db.execute('DELETE FROM guild_member_state WHERE guild=? AND role_id=2',(guild,))
    f.reject(lambda:f.org.apply_guild_family_dissolution(event,'unknown-consumed-profile',now+5000,now),
        'guild_member_state_unknown')
    assert f.org.family_guild(first)==guild and f.org.guild_lifecycle(guild).state=='active'
    f,first,second,guild=setup(Path(directory)/'guild-new-generation.db')
    event,now=terminal(f,first)
    with closing(f.accounts.connect()) as db,db:
        db.execute("UPDATE guild_family_generations SET generation='fresh-family-link' WHERE family=?",(first,))
    f.reject(lambda:f.org.apply_guild_family_dissolution(event,'late-old-generation',now+5000,now),
        'stale_guild_family_generation')
    assert f.org.family_guild(first)==guild


async def check_independence(directory):
    from game_runtime import GameRuntime
    from family_maintenance import MaintenanceCommand
    import runtime_storage
    f,first,second,guild=setup(Path(directory)/'guild-isolated-closure.db')
    event,stamp=terminal(f,first)
    runtime=GameRuntime(f.accounts,runtime_storage.prepare(f.accounts))
    entered,released=threading.Event(),threading.Event()
    repository=runtime.social_runtime.organizations.store
    original=repository.apply_guild_family_dissolution
    def slow(*args):
        entered.set()
        if not released.wait(5):raise TimeoutError('fixture closure release')
        return original(*args)
    repository.apply_guild_family_dissolution=slow
    scheduler=runtime.social_runtime.organizations.family.maintenance
    try:
        pending=asyncio.create_task(scheduler.run_once(f.now()))
        assert await asyncio.to_thread(entered.wait,2)
        owner=runtime.social_runtime.organizations
        command=f.cmd(16,second,'set_family_products',(1,-1))
        await asyncio.wait_for(owner.command(command,f.now()),1)
        # The source family owner is free while its outbox waits for guild IO.
        duplicate=MaintenanceCommand(first,event.due_ms,(),'same-terminal-tick',event.due_ms+5000)
        result=await asyncio.wait_for(owner.maintain_family(duplicate,event.due_ms),1)
        assert result.state=='dissolution_pending' and not pending.done()
        released.set();await pending
        assert f.org.family_guild_dissolution_done(first,event.due_ms)
    finally:
        released.set();await runtime.close()


async def check_periodic_native(directory):
    from game_runtime import GameRuntime
    from verify_runtime import Peer
    import runtime_storage
    import faction_protocol as p
    import guild_protocol as g
    f,first,second,guild=setup(Path(directory)/'guild-periodic-native.db')
    f.org.execute(f.cmd(1,guild,'appoint',(17,'deputy')),f.now())
    runtime=GameRuntime(f.accounts,runtime_storage.prepare(f.accounts))
    completed=threading.Event()
    repository=runtime.social_runtime.organizations.store
    original=repository.ack_family_guild_dissolution
    def observe(command,now):
        result=original(command,now);completed.set();return result
    repository.ack_family_guild_dissolution=observe
    try:
        roles=f.accounts.roles(1111);a,b=Peer(runtime),Peer(runtime)
        await a.login(next(r for r in roles if r['id']==1))
        await b.login(next(r for r in roles if r['id']==17))
        await runtime.social_runtime.organizations.guild.idle()
        await a.take();await b.take()
        event,stamp=terminal(f,first)
        assert await asyncio.to_thread(completed.wait,8),'Periodic closure directory did not dispatch'
        await runtime.social_runtime.organizations.family.maintenance.idle()
        left=await a.take();current=await b.take()
        assert (p.LEFT_FACTION,b'') in left
        assert any(kind==g.UPDATE_GUILD for kind,body in current)
        assert f.org.snapshot(guild)[0]['leader']==17
        assert f.org.family_guild_dissolution_done(first,event.due_ms)
    finally:await runtime.close()


if __name__=='__main__':
    with tempfile.TemporaryDirectory() as directory:
        check_successor(directory)
        check_last_family(directory)
        asyncio.run(check_automatic(directory))
        check_unconsumed_member(directory)
        check_unconsumed_member(directory,True)
        check_pending_successor(directory)
        check_faults(directory)
        check_unknown_and_generation(directory)
        asyncio.run(check_independence(directory))
        asyncio.run(check_periodic_native(directory))
    result=dict(passed=['emergency successor honors deputy rank and clears delegated authority',
        'last family retires guild operations without deleting or refunding historical funds',
        'retries with new transport IDs and restart preserve the same durable receipt',
        'partition directory dispatches guild commit then qualified family acknowledgment',
        'guild ack does not falsely complete role/task/map cleanup',
        'fresh unconsumed family join event needs no invented zero guild profile',
        'an earlier guild refresh preserves fresh pending joins before advancing its cursor',
        'no eligible successor blocks authority until remaining pending family is processed',
        'stale scope, altered roster, expiry and ack without durable receipt are rejected',
        'late receipt failure rolls back link, leadership, lifecycle and financial state',
        'consumed unknown guild prestige stays pending rather than being zero-filled',
        'late event cannot remove a fresh guild-family generation',
        'blocked guild closure leaves source and other family owners independently usable',
        'actual periodic source emits original encrypted guild-leave and surviving-guild refresh'],
        live_server_changed=False,native_gui_verified=False,shared_entry_files_edited=False,
        actual_periodic_guild_consumer_integrated=True,role_task_inventory_map_cleanup_complete=False)
    write_json(OUT/'evidence/guild-dissolution-verification.json',result)
    print(json.dumps(result))
