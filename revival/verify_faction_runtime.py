"""Organization chat through actual runtime, RC4 and native MPPC decoder.

All organizations below are explicit disposable fixtures, not native creation
or fee acceptance. No real character, wallet, server port or process is changed.
"""
import asyncio
from contextlib import closing
from dataclasses import replace
import json
from pathlib import Path
import struct
import tempfile
import threading
import time
import uuid
from unittest.mock import patch
from accounts import AccountStore
from game_runtime import GameRuntime
from faction_domain import OrganizationCommand
from faction_protocol import LEFT_FAMILY
from faction_runtime import OrganizationDelivery
from social_owner import SocialCommand
from verify_runtime import Peer
from inspect_client import OUT,write_json
import runtime_storage
import social_protocol as p


def now():return int(time.time()*1000)
def packet(channel,content,extra=''):return struct.pack('>i',channel)+p.text(content)+p.text(extra)+b'\0'


def fixture(directory):
    store=AccountStore(Path(directory)/'state.db')
    with closing(store.connect()) as db,db:
        for rid,name in enumerate(('族长甲','成员乙','族长丙','局外丁'),1):
            db.execute('INSERT INTO roles(id,account_id,name,school,shape,level) VALUES(?,1111,?,12,1010101,40)',(rid,name))
    return store


def seed(rt):
    # This fixture only establishes membership to exercise runtime routing.
    # It never claims native consent, construction or wallet funding.
    with closing(rt.social_runtime.organizations.store.connect()) as db,db:
        db.executemany('INSERT INTO organizations(id,kind,name,aim,leader) VALUES(?,?,?,?,?)',
            [(101,'family','甲方家族','同心协力',1),(102,'family','乙方家族','同心协力',3),
             (103,'guild','测试帮派','同心协力',1)])
        db.executemany('INSERT INTO family_members VALUES(?,?,?,?)',
            [(1,101,'leader',1),(2,101,'member',1),(3,102,'leader',1)])
        db.executemany('INSERT INTO guild_families VALUES(?,?,?)',[(101,103,1),(102,103,1)])
        from guild_offices import new_family
        for family in (101,102):new_family(db,family)


def command(rt,actor,organization,operation,args=()):
    s=rt.online_snapshot()[actor]
    return OrganizationCommand(actor,s.login_epoch,uuid.uuid4().hex,now()+5000,organization,operation,args)


async def check(store,checks):
    rt=GameRuntime(store,runtime_storage.prepare(store))
    roles=store.roles(1111)
    peers=[Peer(rt) for _ in roles]
    try:
        for peer,role in zip(peers,roles):await peer.login(role)
        a,b,c,d=peers;org=rt.social_runtime.organizations;seed(rt)
        expected=[(p.CHAT_RECEIVE,p.chat_message(roles[0],10,'家族消息'))]
        assert await a.request(p.CHAT_SEND,packet(10,'家族消息'))==expected
        assert await b.take()==expected
        assert await c.take()==[] and await d.take()==[]
        assert await a.request(p.CHAT_SEND,packet(10,'立即刷屏'))==[]
        assert await b.take()==[]
        assert await d.request(p.CHAT_SEND,packet(10,'冒充家族'))==[]
        checks.append('native family channel is membership scoped; sender echo, cooldown and outsider denial')
        expected=[(p.CHAT_RECEIVE,p.chat_message(roles[2],4,'帮派消息'))]
        assert await c.request(p.CHAT_SEND,packet(4,'帮派消息'))==expected
        assert await a.take()==expected and await b.take()==expected and await d.take()==[]
        assert await d.request(p.CHAT_SEND,packet(4,'冒充帮派'))==[]
        checks.append('native guild channel spans admitted families and excludes nonmembers')
        await b.request(p.ADD_SEND,struct.pack('>Q',1)+p.text(''))
        await b.request(p.MOVE_GROUP_SEND,p.text(p.GROUP_BLACK)+struct.pack('>Q',1)+p.text(''))
        expected=[(p.CHAT_RECEIVE,p.chat_message(roles[0],4,'屏蔽验证'))]
        assert await a.request(p.CHAT_SEND,packet(4,'屏蔽验证'))==expected
        assert await c.take()==expected and await b.take()==[]
        checks.append('recipient-owned blacklist filters guild chat without breaking other recipients')
        # Public request seam rejects malformed, rich and expired inputs.
        s=rt.online_snapshot()[2]
        def social(body):return SocialCommand(2,s.login_epoch,uuid.uuid4().hex,now()+5000,p.CHAT_SEND,body)
        for body in (packet(10,'附件','额外内容'),packet(10,'损坏')+b'\0'):
            assert (await org.request(s,social(body),now())).rejection
        expired=replace(social(packet(10,'过期')),deadline_ms=now()-1)
        try:expired_result=await org.request(s,expired,now())
        except TimeoutError:pass
        else:assert expired_result.rejection=='invalid_request_or_deadline'
        checks.append('unsupported rich content, malformed tail and expired command reject before publishing')
        mute=command(rt,1,103,'mute',(3,))
        await org.command(mute,now())
        s3=rt.online_snapshot()[3]
        muted=SocialCommand(3,s3.login_epoch,uuid.uuid4().hex,now()+5000,p.CHAT_SEND,packet(4,'禁言验证'))
        assert (await org.request(s3,muted,now())).rejection=='muted'
        assert await c.request(p.CHAT_SEND,muted.body)==[]
        checks.append('persisted guild mute is enforced through runtime before any native send')
        # Retry of an accepted social command must not rebroadcast, even after
        # passing the ordinary cooldown. The receipt fingerprint is immutable.
        retry=social(packet(10,'只发送一次'))
        assert not (await org.request(s,retry,now())).rejection
        await a.take();await b.take()
        assert not (await org.request(s,retry,now())).rejection
        assert await a.take()==[] and await b.take()==[]
        assert (await org.request(s,replace(retry,body=packet(10,'换内容')),now())).rejection=='request_id_conflict'
        checks.append('committed chat request retry is silent; same key with changed content rejects')
        from faction_domain import OrganizationStore
        limited=OrganizationStore(store.path,dict(org.policy,chat_receipt_limit=1,chat_interval_ms=0))
        assert limited.chat(101,2,s.login_epoch,'只发送一次',now(),retry.request_id,retry.deadline_ms) is None
        try:limited.chat(101,2,s.login_epoch,'限额拒绝',now(),uuid.uuid4().hex,now()+5000)
        except ValueError as error:assert str(error)=='chat_receipts_full'
        else:raise AssertionError('Unexpired chat dedup window evicted')
        assert limited.chat(101,2,s.login_epoch,'过期后空间',retry.deadline_ms+1,uuid.uuid4().hex,retry.deadline_ms+5000)
        checks.append('bounded chat receipt window preserves unexpired dedup; expired requests release capacity')
        # Capture a delayed guild message, then rotate a family membership. Guild
        # revision itself is unchanged: family stamps must also invalidate it.
        stamp=now()+3001
        event=org.store.chat(103,1,rt.online_snapshot()[1].login_epoch,'迟到消息',stamp)
        delayed=OrganizationDelivery(2,s.login_epoch,p.CHAT_RECEIVE,p.chat_message(roles[0],4,event.content),event)
        guild_revision=org.store.snapshot(103)[0]['revision']
        await org.command(command(rt,2,101,'leave'),now())
        assert await b.take()==[(LEFT_FAMILY,b'')]
        await org.command(command(rt,2,101,'apply'),now())
        await org.command(command(rt,1,101,'review',(2,True)),now())
        assert org.store.snapshot(103)[0]['revision']==guild_revision
        assert not org.store.authorize_delivery(event,2)
        rt.social_runtime.offer(delayed)
        assert await b.take()==[]
        checks.append('queued guild chat is fenced across family leave/rejoin even when guild revision is unchanged')
        outcome=await org.command(command(rt,1,101,'appoint',(2,'deputy')),now())
        assert outcome.organization==101 and outcome.revision==org.store.snapshot(101)[0]['revision']
        try:outcome.revision=0
        except (AttributeError,TypeError):pass
        else:raise AssertionError('Mutable cross-owner result')
        old=rt.online_snapshot()[2]
        await b.connection.close()
        b=Peer(rt);await b.login(roles[1]);peers[1]=b
        stale=SocialCommand(2,old.login_epoch,uuid.uuid4().hex,now()+5000,p.CHAT_SEND,packet(4,'旧连接'))
        assert (await org.request(old,stale,now())).rejection=='stale_epoch'
        rt.social_runtime.offer(delayed)
        assert await b.take()==[]
        assert await d.request(100,b'org!')==[(100,b'org!')]
        await asyncio.wait_for(org.guild.idle(),1)
        assert not org.owners and not org.inflight
        checks.append('frozen command outcomes, replacement login fencing, native cipher continuity and idle owner retirement')
    finally:await rt.close()
    rt=GameRuntime(store,runtime_storage.prepare(store))
    try:
        a,b,c=(Peer(rt) for _ in range(3))
        for peer,role in zip((a,b,c),roles[:3]):await peer.login(role)
        expected=[(p.CHAT_RECEIVE,p.chat_message(roles[1],4,'重登帮派'))]
        assert await b.request(p.CHAT_SEND,packet(4,'重登帮派'))==expected
        assert await a.take()==expected and await c.take()==expected
        s=rt.online_snapshot()[3]
        cmd=SocialCommand(3,s.login_epoch,uuid.uuid4().hex,now()+5000,p.CHAT_SEND,packet(4,'仍禁言'))
        assert (await rt.social_runtime.organizations.request(s,cmd,now())).rejection=='muted'
        checks.append('runtime restart restores family hierarchy, guild membership and mute without wallet initialization')
    finally:await rt.close()


async def concurrency(store,checks):
    rt=GameRuntime(store,runtime_storage.prepare(store));release=threading.Event()
    try:
        roles=store.roles(1111);peers=[Peer(rt) for _ in roles]
        for peer,role in zip(peers,roles):await peer.login(role)
        seed(rt);org=rt.social_runtime.organizations
        entered=threading.Event();seen=[];original=org.store.execute
        def slow(cmd,stamp):
            if cmd.organization==101 and cmd.operation=='appoint':
                entered.set()
                if not release.wait(3):raise AssertionError('Missing fixture release')
            seen.append(cmd.operation)
            return original(cmd,stamp)
        with patch.object(org.store,'execute',slow):
            abandoned=asyncio.create_task(org.command(command(rt,1,101,'appoint',(2,'deputy')),now()))
            assert await asyncio.to_thread(entered.wait,1)
            owner=org.owners[('organization',101)]['owner']
            abandoned.cancel()
            try:await abandoned
            except asyncio.CancelledError:pass
            following=asyncio.create_task(org.command(command(rt,2,101,'leave'),now()))
            for _ in range(3):await asyncio.sleep(0)
            assert org.owners[('organization',101)]['owner'] is owner and not following.done()
            expected=[(p.CHAT_RECEIVE,p.chat_message(roles[2],10,'独立家族'))]
            assert await asyncio.wait_for(peers[2].request(p.CHAT_SEND,packet(10,'独立家族')),.7)==expected
            assert await asyncio.wait_for(peers[3].request(100,b'free'),.7)==[(100,b'free')]
            assert not following.done()
            release.set();await following
        assert seen==['appoint','leave'] and 2 not in org.store.snapshot(101)[1]
        # A committed family command may enqueue independent guild work. The
        # retirement assertion applies after that public work-drain seam too.
        await asyncio.wait_for(org.guild.idle(),1)
        assert not org.owners and not org.inflight
        checks.append('blocked organization retains owner after cancellation; same-owner leave waits while another family and heartbeat advance')
    finally:release.set();await rt.close()


def main():
    checks=[]
    with tempfile.TemporaryDirectory() as directory:asyncio.run(check(fixture(directory),checks))
    with tempfile.TemporaryDirectory() as directory:asyncio.run(concurrency(fixture(directory),checks))
    report=dict(passed=checks,source_chat_runtime_integrated=True,native_gui_verified=False,
                paid_native_creation_integrated=False,live_server_restarted=False,commercial_capacity_verified=False)
    write_json(OUT/'evidence/faction-runtime-verification.json',report)
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':main()
