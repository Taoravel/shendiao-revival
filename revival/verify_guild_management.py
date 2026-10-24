"""Native guild requests through GameRuntime and recipient-owned cipher streams."""
import asyncio
from contextlib import closing
import json
from pathlib import Path
import struct
import tempfile
import threading
import uuid
from unittest.mock import patch
from verify_guild_offices import setup
from verify_runtime import Peer
from game_runtime import GameRuntime
from faction_domain import OrganizationCommand
from verify_family_management import now
from wire import read_compact
import runtime_storage
import social_protocol as sp
import faction_protocol as p
import guild_protocol as g
from inspect_client import OUT,write_json
from guild_runtime import GuildWake


def latest(frames,kind):return next(b for k,b in reversed(frames) if k==kind)


def roster(frames):
    body=latest(frames,g.ADD_GUILD_MEMBERS);count,pos=read_compact(body);rows={}
    for _ in range(count):
        rid,a,b,c,level=struct.unpack_from('>Qiiii',body,pos);pos+=24
        name,pos=sp.read_text(body,pos)
        school,prestige,upper,weekly,historical,family_rank,guild_rank=struct.unpack_from('>iiiQQii',body,pos);pos+=36
        family_name,pos=sp.read_text(body,pos);family=struct.unpack_from('>i',body,pos)[0];pos+=4
        offline,pos=sp.read_text(body,pos)
        rows[rid]=dict(name=name,level=level,school=school,prestige=(prestige,upper),dues=(weekly,historical),
            family_rank=family_rank,guild_rank=guild_rank,family_name=family_name,family=family,offline=offline)
    assert pos==len(body)
    return rows


async def check(f,guild,passed):
    rt=GameRuntime(f.accounts,runtime_storage.prepare(f.accounts));roles={r['id']:r for r in f.accounts.roles(1111)}
    try:
        a,b,o,m=Peer(rt),Peer(rt),Peer(rt),Peer(rt)
        await a.login(roles[1])
        assert g.UPDATE_GUILD in [k for k,_ in a.initial] and len(roster(a.initial))==18
        assert roster(a.initial)[1]['guild_rank']==6 and roster(a.initial)[1]['offline']==''
        await b.login(roles[2]);await o.login(roles[19]);await m.login(roles[17]);org=rt.social_runtime.organizations
        assert roster(b.initial)[2]['offline']==''
        assert not any(k in (g.UPDATE_GUILD,g.ADD_GUILD_MEMBERS) for k,_ in o.initial)
        passed.append('login publishes native guild basic data and full cross-family roster; outsider receives none')
        await a.take();await b.take();await m.take()
        frames=await a.request(p.REQUEST_FACTION,b'');assert len(roster(frames))==18
        assert await o.request(p.REQUEST_FACTION,b'')==[]
        await a.request(p.FAMILY_POSITION,struct.pack('>Qi',2,1));await b.take()
        frames=await a.request(p.FACTION_POSITION,struct.pack('>Qi',2,5))
        assert roster(frames)[2]['guild_rank']==5 and roster(frames)[2]['family_rank']==1
        assert roster(await b.take())[2]['guild_rank']==5
        online=rt.online_snapshot()
        grant=OrganizationCommand(1,online[1].login_epoch,uuid.uuid4().hex,now()+5000,guild,'set_authority',(2,6,True))
        await org.command(grant,now())
        assert latest(await b.take(),p.DEPUTY_AUTHORITY)==struct.pack('>i',64)
        assert latest(await m.take(),p.DEPUTY_AUTHORITY)==bytes(4)
        frames=await b.request(p.FACTION_POSITION,struct.pack('>Qi',3,3))
        assert roster(frames)[3]['guild_rank']==3
        frames=await b.request(p.RESIGN_FACTION_OFFICE,b'')
        assert roster(frames)[2]['guild_rank']==0 and roster(frames)[2]['family_rank']==1
        assert latest(frames,p.DEPUTY_AUTHORITY)==bytes(4)
        passed.append('original query, nomination, delegated appointment and resignation update all clients; family office and private authority remain independent')
        await a.take();await b.take();await m.take()
        before=org.store.snapshot(guild)
        assert await a.request(p.FACTION_POSITION,struct.pack('>Qi',3,2))==[]
        assert await a.request(p.REQUEST_FACTION,b'\0')==[]
        assert await o.request(p.FACTION_POSITION,struct.pack('>Qi',3,5))==[]
        assert org.store.snapshot(guild)==before
        assert await o.request(100,b'gld!')==[(100,b'gld!')]
        passed.append('reserved native rank, malformed request and outsider nomination preserve state and native cipher continuity')
        await o.request(p.JOIN_FAMILY,p.family_join_request((1,)))
        await a.request(p.FAMILY_REVIEW,struct.pack('>Qi',19,1))
        await org.guild.idle()
        frames=await o.take()
        assert 19 in roster(frames)
        passed.append('native family approval schedules the independent guild owner and publishes the joined guild roster')
        old=org.store.guild_scope(19,rt.online_snapshot()[19].login_epoch)
        old_wake=GuildWake(19,rt.online_snapshot()[19].login_epoch,0,b'',*old)
        await a.take();await b.take();await m.take()
        frames=await o.request(p.LEAVE_FAMILY,b'');await org.guild.idle();frames+=await o.take()
        assert (p.LEFT_FAMILY,b'') in frames and (p.LEFT_FACTION,b'') in frames
        remaining=await a.take();assert 19 not in roster(remaining)
        assert (g.REMOVE_GUILD_MEMBER,struct.pack('>Q',19)) in remaining
        await b.take();await m.take()
        await o.request(p.JOIN_FAMILY,p.family_join_request((1,)))
        await a.request(p.FAMILY_REVIEW,struct.pack('>Qi',19,1));await org.guild.idle()
        frames=await o.take();assert roster(frames)[19]['prestige']==(0,0)
        current=org.store.guild_scope(19,rt.online_snapshot()[19].login_epoch);assert current!=old
        await a.take();await b.take();await m.take()
        rt.social_runtime.offer(old_wake);assert await o.take()==[]
        rt.social_runtime.offer(GuildWake(19,old_wake.login_epoch,0,b'',*old,departed=True));assert await o.take()==[]
        passed.append('native family departure clears both memberships and roster cache; rejoin rotates scope and rejects old guild/departure wakes')
        await o.request(p.LEAVE_FAMILY,b'');await org.guild.idle();await o.take();await a.take();await b.take();await m.take()
        with patch.object(org.guild,'nudge',return_value=False):
            await o.request(p.JOIN_FAMILY,p.family_join_request((1,)))
            await a.request(p.FAMILY_REVIEW,struct.pack('>Qi',19,1))
        frames=await o.take();assert not any(k==g.ADD_GUILD_MEMBERS for k,_ in frames)
        frames=await o.request(p.REQUEST_FACTION,b'');assert 19 in roster(frames)
        passed.append('lost transient family-to-guild nudge is recovered by native query from the durable membership handoff')
        await a.take();await b.take();await m.take()
        stamp=rt.online_snapshot()[2]
        await b.connection.close()
        frames=await a.take();assert len(roster(frames)[2]['offline'])==19
        await m.take();await o.take()
        b=Peer(rt);await b.login(roles[2]);assert roster(b.initial)[2]['offline']==''
        await a.take();await m.take();await o.take()
        await org.guild.presence(stamp)
        assert await a.take()==[]
        passed.append('guild offline text and reconnect restore through target-owned streams; stale presence cannot mark a replacement offline')
        online=rt.online_snapshot();command=OrganizationCommand(1,online[1].login_epoch,uuid.uuid4().hex,
            now()+5000,guild,'appoint',(4,'right_elder'))
        with patch.object(org.store,'refresh_guild',side_effect=ValueError('guild_member_state_unknown')):
            result=await org.command(command,now())
        assert result.organization==guild
        frames=await a.request(p.REQUEST_FACTION,b'');assert roster(frames)[4]['guild_rank']==4
        passed.append('a committed office receipt remains successful when presentation refresh is deferred; next native query repairs display')
        await a.take();await b.take();await m.take();await o.take()
        entered,released=threading.Event(),threading.Event()
        original=org.store.refresh_guild
        def paused(identity,requester=()):
            if identity==guild and not requester:
                entered.set()
                if not released.wait(5):raise TimeoutError('controlled guild pause not released')
            return original(identity,requester)
        try:
            with patch.object(org.store,'refresh_guild',side_effect=paused):
                departed=await asyncio.wait_for(o.request(p.LEAVE_FAMILY,b''),2)
                assert (p.LEFT_FAMILY,b'') in departed
                assert await asyncio.to_thread(entered.wait,2)
                before=org.store.snapshot(1)[0]['revision']
                await asyncio.wait_for(a.request(p.FAMILY_POSITION,struct.pack('>Qi',3,0)),2)
                assert org.store.snapshot(1)[0]['revision']==before+1 and not released.is_set()
                assert await m.request(100,b'live')==[(100,b'live')]
                released.set();await org.guild.idle()
        finally:released.set()
        await o.take();await a.take();await b.take();await m.take()
        await o.request(p.JOIN_FAMILY,p.family_join_request((1,)))
        await a.request(p.FAMILY_REVIEW,struct.pack('>Qi',19,1));await org.guild.idle()
        assert 19 in roster(await o.take())
        passed.append('paused actual guild refresh does not hold the family owner: independent family command and another-family heartbeat complete before release')
        family_head=Peer(rt);await family_head.login(roles[16])
        assert roster(family_head.initial)[16]['guild_rank']==2
        frames=await family_head.request(p.FACTION_POSITION,struct.pack('>Qi',17,1))
        assert roster(frames)[17]['guild_rank']==1
        before=org.store.guild_office_snapshot(guild)
        assert await family_head.request(p.FACTION_POSITION,struct.pack('>Qi',4,1))==[]
        assert org.store.guild_office_snapshot(guild)==before
        await a.take()
        assert await a.request(p.FACTION_POSITION,struct.pack('>Qi',16,1))==[]
        assert org.store.guild_office_snapshot(guild)==before
        passed.append('original family patrol request now reaches guild appointment; family head can appoint within its own family only')
    finally:await rt.close()
    rt=GameRuntime(f.accounts,runtime_storage.prepare(f.accounts))
    try:
        a=Peer(rt);await a.login(roles[1]);rows=roster(a.initial)
        assert len(rows)==19 and rows[3]['guild_rank']==3 and rows[4]['guild_rank']==4
        assert rows[2]['guild_rank']==0 and rows[2]['family_rank']==1 and rows[19]['prestige']==(0,0)
        assert rows[17]['guild_rank']==1
        passed.append('restart restores current guild roster, independent family/guild offices and membership baselines without regranting')
    finally:await rt.close()


def main():
    passed=[]
    with tempfile.TemporaryDirectory() as directory:
        f,_,_,guild=setup(Path(directory)/'state.db')
        with closing(f.accounts.connect()) as db,db:
            db.execute("INSERT INTO roles(id,account_id,name,school,shape,level) VALUES(19,1111,'帮外侠客',12,1010101,40)")
        asyncio.run(check(f,guild,passed))
    report=dict(passed=passed,native_source_integrated=True,native_gui_verified=False,live_store_changed=False)
    write_json(OUT/'evidence/guild-management-verification.json',report);print(json.dumps(report))


if __name__=='__main__':main()
