"""Encrypted runtime acceptance for persisted player chat groups (not GUI)."""
import asyncio
from contextlib import closing
from dataclasses import replace
import json
from pathlib import Path
import struct
import tempfile
import time
import uuid
from accounts import AccountStore
from game_runtime import GameRuntime
from group_runtime import GroupDelivery
from group_store import GroupStore
from social_owner import SocialCommand
from runtime_core import StaleEpoch
from verify_runtime import Peer
from inspect_client import OUT,write_json
import runtime_storage
import social_protocol as sp
import group_protocol as p
from verify_group_management import message_fields


async def check(store,checks):
    rt=GameRuntime(store,runtime_storage.prepare(store))
    a,b,c=store.roles(1111)
    pa,pb,pc=Peer(rt),Peer(rt),Peer(rt)
    try:
        await pa.login(a);await pb.login(b);await pc.login(c)
        assert await pc.request(p.CREATE,b'')==[]
        assert await pa.request(p.CREATE,b'')==[(p.CREATE_READY,b'')]
        created=await pa.request(p.NAME,p.text('华山论剑'))
        gid=struct.unpack_from('>Q',created[0][1])[0]
        assert [k for k,_ in created]==[p.CREATED,p.UPDATED]
        group=rt.social_runtime.groups.store.initial(a['id'])['groups'][0]
        assert created[1][1]==p.updated(group,rt.online_snapshot())
        assert await pb.request(p.SEARCH,p.text('华山论剑')+bytes(12))==[(p.SEARCHED,p.searched(group))]
        checks.append('native two-stage creation, level gate, exact name lookup and full roster update')
        assert await pb.request(p.JOIN,struct.pack('>Q',gid))==[]
        assert await pa.take()==[(p.JOIN_NOTICE,p.join_notice(b['id'],gid,b['name']))]
        # A nonmember cannot approve its own request or spoof another applicant.
        assert await pb.request(p.RESPOND,struct.pack('>iQQ',0,b['id'],gid))==[]
        assert len(rt.social_runtime.groups.store.initial(b['id'])['groups'])==0
        response=await pa.request(p.RESPOND,struct.pack('>iQQ',0,b['id'],gid))
        assert [k for k,_ in response]==[p.UPDATED]
        assert [k for k,_ in await pb.take()]==[p.UPDATED]
        checks.append('durable applications, owner approval and unauthorized self-approval rejection')
        chat=lambda text:p.text(text)+p.text('')+struct.pack('>Q',gid)+b'\0'
        sent=await pb.request(p.SEND,chat('群友你好'))
        assert len(sent)==1 and sent[0][0]==p.MESSAGE
        assert message_fields(sent[0][1])[:2]==('群友你好',b['name'])
        assert message_fields(sent[0][1])[3]==gid
        assert await pa.take()==sent
        assert await pc.request(p.SEND,chat('越权群聊'))==[]
        assert await pa.take()==[]
        # Blacklist uses the server-verified sender identity, not packet strings.
        await pb.request(sp.ADD_SEND,struct.pack('>Q',a['id'])+sp.text(''))
        await pb.request(sp.MOVE_GROUP_SEND,sp.text(sp.GROUP_BLACK)+struct.pack('>Q',a['id'])+sp.text(''))
        assert (await pa.request(p.SEND,chat('屏蔽验证')))[0][0]==p.MESSAGE
        assert await pb.take()==[]
        checks.append('group chat sender identity, membership authorization and recipient blacklist')
        group=rt.social_runtime.groups.store.initial(b['id'])['groups'][0]
        member=next(m for m in group['members'] if m['id']==b['id'])
        delayed=GroupDelivery(b['id'],pb.connection.epoch,p.MESSAGE,p.message(gid,a['name'],'积压消息'),
            gid,member['generation'],group['version'],a['id'])
        assert await pb.request(p.LEAVE,struct.pack('>Q',gid))==[(p.LEFT,struct.pack('>Q',gid))]
        assert [k for k,_ in await pa.take()]==[p.UPDATED]
        # Return to the same group; the old membership capability must stay invalid.
        await pb.request(p.JOIN,struct.pack('>Q',gid));await pa.take()
        await pa.request(p.RESPOND,struct.pack('>iQQ',0,b['id'],gid));await pb.take()
        await pb.request(sp.MOVE_GROUP_SEND,sp.text(sp.GROUP_FRIEND)+struct.pack('>Q',a['id'])+sp.text(''))
        rt.social_runtime.offer(delayed)
        assert await pb.take()==[]
        checks.append('leave and rejoin rotate membership generation; old queued messages are rejected')
        await pa.connection.close()
        assert await pc.request(p.JOIN,struct.pack('>Q',gid))==[]
        pa=Peer(rt);await pa.login(a)
        assert pa.initial[0][0]==sp.FRIENDS_INIT
        assert p.INITIAL in [k for k,_ in pa.initial]
        assert (p.JOIN_NOTICE,p.join_notice(c['id'],gid,c['name'])) in pa.initial
        await pa.request(p.RESPOND,struct.pack('>iQQ',0,c['id'],gid));await pb.take();await pc.take()
        assert len(rt.social_runtime.groups.store.initial(c['id'])['groups'])==1
        checks.append('offline owner application replay after persisted roster initialization')
        # Replaying one exact transport request must not create a second group.
        s=rt.online_snapshot()[a['id']]
        command=SocialCommand(a['id'],s.login_epoch,uuid.uuid4().hex,int(time.time()*1000)+5000,p.CREATE,b'')
        assert not rt.social_runtime.groups.store.execute(s,command,int(time.time()*1000))['replayed']
        assert rt.social_runtime.groups.store.execute(s,command,int(time.time()*1000))['replayed']
        try:rt.social_runtime.groups.store.execute(s,replace(command,body=b'bad'),int(time.time()*1000))
        except ValueError as e:assert str(e)=='group_request_conflict'
        else:raise AssertionError('Duplicate key changed its command')
        checks.append('transactional command receipts reject request-id conflicts')
        assert await pc.request(100,b'grp!')==[(100,b'grp!')]
        assert not rt.social_runtime.groups.owners
        checks.append('continuous native cipher/MPPC stream and idle group owner cleanup')
    finally:await rt.close()
    # Restart the actual runtime against the same database, no state fixtures.
    rt=GameRuntime(store,runtime_storage.prepare(store))
    try:
        pa=Peer(rt);await pa.login(a)
        groups=rt.social_runtime.groups.store.initial(a['id'])['groups']
        assert len(groups)==1 and len(groups[0]['members'])==3
        assert p.INITIAL in [k for k,_ in pa.initial]
        # Replace the authoritative lease while retaining the old snapshot.
        s=rt.online_snapshot()[a['id']]
        store.acquire_lease(1111,a['id'])
        stale=SocialCommand(a['id'],s.login_epoch,uuid.uuid4().hex,int(time.time()*1000)+5000,p.LEAVE,struct.pack('>Q',gid))
        try:rt.social_runtime.groups.store.execute(s,stale,int(time.time()*1000))
        except StaleEpoch:pass
        else:raise AssertionError('Old lease dissolved group')
        assert len(rt.social_runtime.groups.store.initial(a['id'])['groups'])==1
        checks.append('runtime restart restores membership; database fencing prevents stale owner dissolution')
    finally:await rt.close()


def main():
    checks=[]
    with tempfile.TemporaryDirectory() as directory:
        store=AccountStore(Path(directory)/'state.db')
        for name in ('群主甲','群友乙','群友丙'):store.create_role(1111,name,12,1010101)
        # Level 20 applies only to the disposable acceptance fixture.
        with closing(store.connect()) as db,db:db.execute('UPDATE roles SET level=20 WHERE id IN (1,2)')
        asyncio.run(check(store,checks))
    result=dict(passed=checks,source_runtime_integrated=True,native_gui_verified=False,live_server_restarted=False)
    write_json(OUT/'evidence/group-runtime-verification.json',result)
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
