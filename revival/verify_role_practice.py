"""Personal cash practice through public planning and fenced transactions."""
from inspect_client import OUT,write_json
import json
import role_practice as p
import tempfile
from pathlib import Path
from contextlib import closing
from verify_guild_offices import setup
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from faction_domain import OrganizationStore
import asyncio


async def bounded_owner(f,guild,rules):
    from game_runtime import GameRuntime
    from faction_runtime import OrganizationOutcome
    import runtime_storage
    runtime=GameRuntime(f.accounts,runtime_storage.prepare(f.accounts))
    try:
        revision=f.tx(1,lambda db:p.read(db,1111,1,f.epochs[1],rules))[0].revision
        commands=[f.cmd(1,guild,'reserve_practice',(360001,revision)) for _ in range(2)]
        results=await asyncio.gather(*(runtime.social_runtime.organizations.command(c,f.now()) for c in commands),return_exceptions=True)
        assert sum(isinstance(r,OrganizationOutcome) for r in results)==1
        assert [str(r) for r in results if isinstance(r,Exception)]==['insufficient_practice_materials']
        winner=commands[next(i for i,r in enumerate(results) if isinstance(r,OrganizationOutcome))]
        await runtime.social_runtime.organizations.command(f.cmd(1,guild,'resolve_practice',(winner.request_id,)),f.now())
        assert f.org.guild_practice_materials(guild).available==3
    finally:await runtime.close()


def main():
    rules=p.load_rules()
    before=p.PracticeState(360001,0,40,0)
    after=p.plan(before,22,500,rules)
    assert after==p.PracticeState(360001,1,0,1)
    assert p.plan(after,25,500,rules)==p.PracticeState(360001,1,10,2)
    passed=['original next-level experience plus fixed cash-practice gain advances one skill']
    with tempfile.TemporaryDirectory() as directory:
        f,_,second,guild=setup(Path(directory)/'practice.db')
        with closing(f.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            states=p.initialize(db,1111,1,f.epochs[1],tuple(p.PracticeState(s,0,0,0) for s in rules.skills),
                'explicit_migration',rules)
            assert len(states)==7 and p.read(db,1111,1,f.epochs[1],rules)==states
        passed.append('explicit seven-skill role baseline is persistent and readable through the fenced interface')
        f.reject(lambda:f.org.execute(f.cmd(1,guild,'reserve_practice',(360001,0)),f.now()),'practice_tenure')
        passed.append('new member cannot reserve a cash practice before the original seven-day tenure')
        # Known balances/tenure are explicit test migrations, never player grants.
        with closing(f.accounts.connect()) as db,db:
            db.execute('UPDATE guild_practice_materials SET available=6,origin=? WHERE guild=?',('explicit_fixture',guild))
            db.execute('UPDATE family_members SET joined_ms=?',(f.now()-rules.tenure_ms,))
            db.execute('UPDATE guild_families SET joined_ms=?',(f.now()-rules.tenure_ms,))
            db.execute('UPDATE guild_member_state SET prestige=500 WHERE role_id=1')
            db.execute('UPDATE guild_assets SET funds=6000000 WHERE guild=?',(guild,))
        f.org.execute(f.cmd(1,guild,'set_practice_open',(360001,True)),f.now())
        command=f.cmd(1,guild,'reserve_practice',(360001,0));cash=f.cash(1)
        f.org.execute(command,f.now())
        assert f.org.guild_practice_materials(guild).available==3
        result=f.tx(1,lambda db:p.settle(db,1111,1,f.epochs[1],guild,command.request_id,f.now(),rules,f.rules))
        assert result.state==p.PracticeState(360001,0,10,1) and f.cash(1)==cash-30000
        assert f.tx(1,lambda db:p.settle(db,1111,1,f.epochs[1],guild,command.request_id,f.now(),rules,f.rules))==result
        assert f.cash(1)==cash-30000
        passed.append('guild reserves three materials, role atomically spends cash and gains experience once')
        f.org.execute(f.cmd(1,guild,'resolve_practice',(command.request_id,)),f.now())
        assert f.org.guild_practice_permit(1,f.epochs[1],guild,command.request_id).status=='committed'
        f.org.execute(command,f.now())
        assert f.org.guild_practice_materials(guild).available==3 and f.cash(1)==cash-30000
        passed.append('guild finalizes the role proof; retry cannot reserve or debit twice')
        failed=f.cmd(1,guild,'reserve_practice',(360001,1));f.org.execute(failed,f.now())
        with closing(f.accounts.connect()) as db,db:
            db.execute("CREATE TRIGGER fixture_practice_failure BEFORE INSERT ON role_practice_receipts BEGIN SELECT RAISE(ABORT,'practice_receipt_failure'); END")
        before_cash=f.cash(1)
        try:f.tx(1,lambda db:p.settle(db,1111,1,f.epochs[1],guild,failed.request_id,f.now(),rules,f.rules))
        except sqlite3.IntegrityError as error:assert 'practice_receipt_failure' in str(error)
        else:raise AssertionError('missing receipt fault')
        assert f.cash(1)==before_cash and f.tx(1,lambda db:p.read(db,1111,1,f.epochs[1],rules))[0]==result.state
        with closing(f.accounts.connect()) as db,db:db.execute('DROP TRIGGER fixture_practice_failure')
        f.org.execute(f.cmd(1,guild,'resolve_practice',(failed.request_id,)),f.now())
        assert f.org.guild_practice_materials(guild).available==3
        assert f.org.guild_practice_permit(1,f.epochs[1],guild,failed.request_id).status=='cancelled'
        f.reject(lambda:f.tx(1,lambda db:p.settle(db,1111,1,f.epochs[1],guild,failed.request_id,f.now(),rules,f.rules)),
            'practice_reservation_not_active')
        passed.append('late role receipt failure rolls back cash and experience; guild refunds once and fences a delayed purchase')
        for i in range(8):
            current=f.tx(1,lambda db:p.read(db,1111,1,f.epochs[1],rules))[0]
            racing=f.cmd(1,guild,'reserve_practice',(360001,current.revision));f.org.execute(racing,f.now())
            resolution=f.cmd(1,guild,'resolve_practice',(racing.request_id,))
            cash_before=f.cash(1)
            def buy():
                try:return f.tx(1,lambda db:p.settle(db,1111,1,f.epochs[1],guild,racing.request_id,f.now(),rules,f.rules))
                except ValueError as error:
                    assert str(error)=='practice_reservation_not_active';return None
            with ThreadPoolExecutor(max_workers=2) as pool:
                a=pool.submit(buy);b=pool.submit(f.org.execute,resolution,f.now());b.result();purchase=a.result()
            status=f.org.guild_practice_permit(1,f.epochs[1],guild,racing.request_id).status
            assert status==('committed' if purchase else 'cancelled')
            assert f.cash(1)==cash_before-(30000 if purchase else 0)
            assert f.org.guild_practice_materials(guild).available==(0 if purchase else 3)
            # Restore only fixture materials for the next independent race.
            with closing(f.accounts.connect()) as db,db:db.execute('UPDATE guild_practice_materials SET available=3 WHERE guild=?',(guild,))
        passed.append('eight concurrent role-purchase/guild-resolution races conserve cash, skill progress and reserved materials')
        # A failed eligibility check leaves resources available; the whole table
        # is evaluated without normalizing special-stage level1129 into ordinary.
        for state,role_level,prestige in [(p.PracticeState(360001,0,0,0),21,500),
            (p.PracticeState(360001,0,0,0),40,499),(p.PracticeState(360001,43,0,0),155,3500)]:
            f.reject(lambda:p.plan(state,role_level,prestige,rules),'practice_level_or_prestige_cap')
        f.reject(lambda:p.plan(p.PracticeState(360001,0,0,0),1129,3500,rules),'practice_ordinary_role_or_prestige_unknown')
        current=f.tx(1,lambda db:p.read(db,1111,1,f.epochs[1],rules))[0]
        stale=f.cmd(1,guild,'reserve_practice',(360001,current.revision));f.org.execute(stale,f.now())
        old_epoch=f.epochs[1];f.epochs[1]=f.accounts.acquire_lease(1111,1)
        assert [x.reservation for x in f.org.pending_practices(1,f.epochs[1])]==[stale.request_id]
        f.reject(lambda:f.org.pending_practices(1,old_epoch),'stale_epoch')
        f.reject(lambda:f.tx(1,lambda db:p.settle(db,1111,1,f.epochs[1],guild,stale.request_id,f.now(),rules,f.rules)),
            'practice_reservation_expired_or_stale')
        f.org.execute(f.cmd(1,guild,'resolve_practice',(stale.request_id,)),f.now())
        assert f.org.guild_practice_materials(guild).available==3
        assert not f.org.pending_practices(1,f.epochs[1])
        f.org=OrganizationStore(f.accounts.path,f.policy);f.org.initialize()
        assert f.tx(1,lambda db:p.read(db,1111,1,f.epochs[1],rules))[0]==current
        assert f.org.guild_practice_permit(1,f.epochs[1],guild,stale.request_id).status=='cancelled'
        f.reject(lambda:f.tx(1,lambda db:p.initialize(db,1111,1,f.epochs[1],
            tuple(p.PracticeState(s,1,0,0) for s in rules.skills),'explicit_migration',rules)), 'practice_baseline_cannot_reset')
        passed.append('ordinary level/prestige gates, special-stage rejection, replaced lease, restart and immutable baselines')
        with closing(f.accounts.connect()) as db,db:
            db.execute('UPDATE guild_practice_materials SET available=21 WHERE guild=?',(guild,))
        cash_before=f.cash(1)
        for skill in rules.skills:
            before=next(s for s in f.tx(1,lambda db:p.read(db,1111,1,f.epochs[1],rules)) if s.skill==skill)
            c=f.cmd(1,guild,'reserve_practice',(skill,before.revision))
            # Open the next type with sufficient fixture funds and native slot
            # limits unchanged; close after use to reuse the existing slot.
            if skill!=360001:
                if skill==360002:f.org.execute(f.cmd(1,guild,'set_practice_open',(360001,False)),f.now())
                with closing(f.accounts.connect()) as db,db:db.execute('UPDATE guild_assets SET funds=6000000 WHERE guild=?',(guild,))
                f.org.execute(f.cmd(1,guild,'set_practice_open',(skill,True)),f.now())
            f.org.execute(c,f.now())
            f.tx(1,lambda db:p.settle(db,1111,1,f.epochs[1],guild,c.request_id,f.now(),rules,f.rules))
            f.org.execute(f.cmd(1,guild,'resolve_practice',(c.request_id,)),f.now())
            if skill!=360001:f.org.execute(f.cmd(1,guild,'set_practice_open',(skill,False)),f.now())
        assert f.cash(1)==cash_before-170000 and f.org.guild_practice_materials(guild).available==0
        passed.append('all seven combat practice skills settle their explicit designed cash recipes and original three-material/ten-XP costs')
        with closing(f.accounts.connect()) as db,db:db.execute('UPDATE guild_assets SET funds=6000000 WHERE guild=?',(guild,))
        f.org.execute(f.cmd(1,guild,'set_practice_open',(360001,True)),f.now())
        f.tx(17,lambda db:p.initialize(db,1111,17,f.epochs[17],tuple(p.PracticeState(s,0,0,0) for s in rules.skills),'explicit_migration',rules))
        with closing(f.accounts.connect()) as db,db:
            db.execute('UPDATE guild_practice_materials SET available=3 WHERE guild=?',(guild,))
            db.execute('UPDATE guild_member_state SET prestige=500 WHERE role_id=17')
        departed=f.cmd(17,guild,'reserve_practice',(360001,0));f.org.execute(departed,f.now())
        f.org.execute(f.cmd(17,second,'leave'),f.now())
        f.reject(lambda:f.tx(17,lambda db:p.settle(db,1111,17,f.epochs[17],guild,departed.request_id,f.now(),rules,f.rules)),'not_member')
        f.org.execute(f.cmd(17,second,'apply'),f.now());f.org.execute(f.cmd(16,second,'review',(17,True)),f.now())
        f.reject(lambda:f.tx(17,lambda db:p.settle(db,1111,17,f.epochs[17],guild,departed.request_id,f.now(),rules,f.rules)),'practice_tenure')
        f.org.execute(f.cmd(17,guild,'resolve_practice',(departed.request_id,)),f.now())
        assert f.org.guild_practice_materials(guild).available==3
        revision=f.tx(1,lambda db:p.read(db,1111,1,f.epochs[1],rules))[0].revision
        expired=f.cmd(1,guild,'reserve_practice',(360001,revision));f.org.execute(expired,f.now())
        f.reject(lambda:f.tx(1,lambda db:p.settle(db,1111,1,f.epochs[1],guild,expired.request_id,expired.deadline_ms,rules,f.rules)),
            'practice_reservation_expired_or_stale')
        f.org.execute(f.cmd(1,guild,'resolve_practice',(expired.request_id,)),f.now())
        closed=f.cmd(1,guild,'reserve_practice',(360001,revision));f.org.execute(closed,f.now())
        f.org.execute(f.cmd(1,guild,'set_practice_open',(360001,False)),f.now())
        f.reject(lambda:f.tx(1,lambda db:p.settle(db,1111,1,f.epochs[1],guild,closed.request_id,f.now(),rules,f.rules)),
            'practice_not_open')
        f.org.execute(f.cmd(1,guild,'resolve_practice',(closed.request_id,)),f.now())
        with closing(f.accounts.connect()) as db,db:db.execute('UPDATE guild_assets SET funds=6000000 WHERE guild=?',(guild,))
        f.org.execute(f.cmd(1,guild,'set_practice_open',(360001,True)),f.now())
        short=f.cmd(1,guild,'reserve_practice',(360001,revision));f.org.execute(short,f.now())
        cash=f.cash(1)
        with closing(f.accounts.connect()) as db,db:db.execute("UPDATE role_wallet_balances SET balance=0 WHERE role_id=1 AND currency='cash'")
        f.reject(lambda:f.tx(1,lambda db:p.settle(db,1111,1,f.epochs[1],guild,short.request_id,f.now(),rules,f.rules)),
            'Insufficient or overflowing currency')
        f.org.execute(f.cmd(1,guild,'resolve_practice',(short.request_id,)),f.now())
        assert f.org.guild_practice_materials(guild).available==3
        with closing(f.accounts.connect()) as db,db:db.execute("UPDATE role_wallet_balances SET balance=? WHERE role_id=1 AND currency='cash'",(cash,))
        passed.append('deadline expiry, revoked open type and insufficient role cash refuse without experience, recover all reserved materials')
        asyncio.run(bounded_owner(f,guild,rules))
        passed.append('actual bounded guild owner admits only one competing reservation for the final three materials')
        with closing(f.accounts.connect()) as db,db:db.execute('DELETE FROM guild_practice_materials WHERE guild=?',(guild,))
        f.org.initialize()
        f.reject(lambda:f.org.guild_practice_materials(guild),'practice_materials_unknown')
        passed.append('departure/rejoin cannot use an old reservation; compensation survives membership loss; startup does not zero-fill unknown guild resources')
    result={'passed':passed,
            'native_gui_verified':False,'live_store_changed':False}
    write_json(OUT/'evidence/role-practice-verification.json',result);print(json.dumps(result))


if __name__=='__main__':main()
