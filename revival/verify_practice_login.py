"""Known practice state restoration through actual encrypted login owners."""
import asyncio,json,struct,tempfile
from pathlib import Path
from inspect_client import OUT,write_json
from verify_guild_offices import setup
from verify_runtime import Peer
from game_runtime import GameRuntime
from contextlib import closing
from dataclasses import replace
from currency import CurrencyChange,apply_currency
from unittest.mock import patch
import threading
import runtime_storage
import role_practice as p
import practice_protocol as wire


async def check(f,guild,paid,unpaid,orphan,balance,passed):
    rt=GameRuntime(f.accounts,runtime_storage.prepare(f.accounts))
    roles={r['id']:r for r in f.accounts.roles(1111)}
    try:
        a,b=Peer(rt),Peer(rt)
        await a.login(roles[1]);await b.login(roles[2])
        actual=[struct.unpack('>iii',body) for kind,body in a.initial if kind==wire.UPDATE_ASSIST_SKILL]
        assert actual==[(s,0,30 if s==360001 else 0) for s in range(360001,360008)]
        assert not any(kind==wire.UPDATE_ASSIST_SKILL for kind,_ in b.initial)
        passed.append('login restores seven known skills through target-owned native streams; unknown profiles emit no fabricated zeros')
        await rt.social_runtime.organizations.guild.idle()
        epoch=rt.online_snapshot()[1].login_epoch;f.epochs[1]=epoch
        assert f.org.guild_practice_permit(1,epoch,guild,paid.request_id).status=='committed'
        assert f.org.guild_practice_permit(1,epoch,guild,unpaid.request_id).status=='cancelled'
        assert f.org.guild_practice_materials(guild).available==3
        assert f.cash(1)==balance
        assert f.org.guild_practice_permit(1,epoch,guild,orphan.request_id).status=='reserved'
        passed.append('login resolves paid/unpaid previous-epoch reservations through the guild owner without another charge')
        passed.append('an earlier orphan outcome remains pending for repair without blocking later healthy recovery entries or login')
        org=rt.social_runtime.organizations
        live=f.cmd(1,guild,'reserve_practice',(360001,1));await org.command(live,f.now())
        assert org.guild.nudge_recovery(1,epoch)
        await org.guild.idle()
        assert f.org.guild_practice_permit(1,epoch,guild,live.request_id).status=='reserved'
        await org.command(f.cmd(1,guild,'resolve_practice',(live.request_id,)),f.now())
        assert f.org.guild_practice_materials(guild).available==3
        passed.append('recovery leaves the current epoch unexpired purchase active; explicit cancellation remains serialized')
        entered,release=threading.Event(),threading.Event();real=org.store.pending_practices
        def slow(role,lease):
            entered.set()
            if not release.wait(3):raise AssertionError('recovery fixture not released')
            return real(role,lease)
        original_policy=org.policy
        try:
            org.policy={**original_policy,'owner_limit':1}
            with patch.object(org.store,'pending_practices',side_effect=slow):
                assert org.guild.nudge_recovery(1,epoch)
                assert await asyncio.to_thread(entered.wait,1)
                assert org.guild.nudge_recovery(1,epoch)
                assert not org.guild.nudge_recovery(2,rt.online_snapshot()[2].login_epoch)
                assert (100,b'pill') in await asyncio.wait_for(b.request(100,b'pill'),1)
                release.set();await org.guild.idle()
        finally:release.set();org.policy=original_policy
        passed.append('bounded/coalesced actual recovery worker can pause before storage while another role heartbeat completes')
    finally:await rt.close()


def main():
    passed=[]
    with tempfile.TemporaryDirectory() as directory:
        f,_,_,guild=setup(Path(directory)/'practice-login.db');rules=p.load_rules()
        f.tx(1,lambda db:p.initialize(db,1111,1,f.epochs[1],tuple(
            p.PracticeState(s,0,20 if s==360001 else 0,0) for s in rules.skills),'explicit_migration',rules))
        with closing(f.accounts.connect()) as db,db:
            db.execute('UPDATE family_members SET joined_ms=?',(f.now()-rules.tenure_ms,))
            db.execute('UPDATE guild_families SET joined_ms=?',(f.now()-rules.tenure_ms,))
            db.execute('UPDATE guild_member_state SET prestige=500 WHERE role_id=1')
            db.execute('UPDATE guild_assets SET funds=6000000 WHERE guild=?',(guild,))
            db.execute('UPDATE guild_practice_materials SET available=9 WHERE guild=?',(guild,))
        f.org.execute(f.cmd(1,guild,'set_practice_open',(360001,True)),f.now())
        paid=replace(f.cmd(1,guild,'reserve_practice',(360001,0)),request_id='10-paid');f.org.execute(paid,f.now())
        f.tx(1,lambda db:p.settle(db,1111,1,f.epochs[1],guild,paid.request_id,f.now(),rules,f.rules))
        unpaid=replace(f.cmd(1,guild,'reserve_practice',(360001,1)),request_id='20-unpaid');f.org.execute(unpaid,f.now())
        orphan=replace(f.cmd(1,guild,'reserve_practice',(360001,1)),request_id='00-orphan');f.org.execute(orphan,f.now())
        f.tx(1,lambda db:apply_currency(db,1111,1,f.epochs[1],CurrencyChange('practice:'+str(guild)+':00-orphan',
            'skill_training','guild-practice:'+str(guild)+':360001',(('cash',-30000),)),f.rules))
        asyncio.run(check(f,guild,paid,unpaid,orphan,f.cash(1),passed))
    result=dict(passed=passed,native_gui_verified=False,live_store_changed=False)
    write_json(OUT/'evidence/practice-login-verification.json',result);print(json.dumps(result))


if __name__=='__main__':main()
