"""Native group manager flows through actual role/connection/storage owners."""
import asyncio
from contextlib import closing
import datetime
import json
from pathlib import Path
import struct
import tempfile
import time
from accounts import AccountStore
from game_runtime import GameRuntime
from inspect_client import OUT,write_json
from verify_runtime import Peer
from group_runtime import GroupDelivery,GroupHistoryDelivery
from wire import read_compact
import social_protocol as sp
import runtime_storage
import group_protocol as p


def message_fields(body):
    content,pos=p.read_text(body)
    sender,pos=p.read_text(body,pos)
    stamp,pos=p.read_text(body,pos)
    gid=struct.unpack_from('>Q',body,pos)[0]
    return content,sender,stamp,gid


def history_fields(body):
    page,last=struct.unpack_from('>iB',body)
    count,pos=read_compact(body,5)
    rows=[]
    for _ in range(count):
        content,pos=p.read_text(body,pos)
        name,pos=p.read_text(body,pos)
        stamp,pos=p.read_text(body,pos)
        assert body[pos] in (0,1) and body[pos+1:pos+3]==bytes(2)
        pos+=3
        datetime.datetime.strptime(stamp,'%Y-%m-%d %H:%M:%S')
        rows.append((content,name,stamp))
    assert pos==len(body)
    return page,bool(last),rows


async def check(store,checks):
    rt=GameRuntime(store,runtime_storage.prepare(store))
    a,b,c=store.roles(1111);pa,pb,pc=Peer(rt),Peer(rt),Peer(rt)
    try:
        await pa.login(a);await pb.login(b);await pc.login(c)
        await pa.request(p.CREATE,b'')
        gid=struct.unpack_from('>Q',(await pa.request(p.NAME,p.text('管理验收')))[0][1])[0]
        await pb.request(p.JOIN,struct.pack('>Q',gid));await pa.take()
        await pa.request(p.RESPOND,struct.pack('>iQQ',0,b['id'],gid));await pb.take()
        sent=await pa.request(p.SEND,p.text('群内报时')+p.text('')+struct.pack('>Q',gid)+b'\0')
        content,sender,stamp,group=message_fields(sent[0][1])
        assert (content,sender,group)==('群内报时',a['name'],gid)
        try:datetime.datetime.strptime(stamp,'%Y-%m-%d %H:%M:%S')
        except ValueError:raise AssertionError('Native group header must contain a server timestamp, got '+repr(stamp)) from None
        assert await pb.take()==sent
        checks.append('native group header receives server timestamp rather than echoed content')
        groups=rt.social_runtime.groups
        current=lambda:groups.store.initial(a['id'])['groups'][0]
        config=lambda scope,flash,notice,allow:struct.pack('>Qii',gid,scope,flash)+p.text(notice)+p.text('')+struct.pack('>i',allow)
        # Scope 0 is a personal setting, even if shared fields are forged.
        assert await pb.request(p.CONFIG,config(1,0,'越权公告',0))==[]
        assert current()['notice']=='' and current()['allow_join']==1
        revision=current()['version']
        own=await pb.request(p.CONFIG,config(0,0,'篡改公告',0))
        assert own==[(p.CONFIGURED,p.configured(current(),b['id']))]
        assert current()['version']==revision and current()['allow_join']==1
        assert next(m for m in current()['members'] if m['id']==b['id'])['flash']==0
        assert await pa.take()==[]
        assert [k for k,_ in await pa.request(p.MANAGER,struct.pack('>QQQ',1,gid,b['id']))]==[p.UPDATED]
        await pb.take()
        assert current()['managers']==[b['id']]
        changed=await pb.request(p.CONFIG,config(1,0,'群友同心',0))
        assert [k for k,_ in changed]==[p.CONFIGURED,p.UPDATED]
        owner_changes=await pa.take()
        assert owner_changes[0]==(p.CONFIGURED,p.configured(current(),a['id']))
        assert changed[0][1]!=owner_changes[0][1]  # Different personal flash flags.
        assert current()['notice']=='群友同心' and current()['allow_join']==0
        assert await pc.request(p.JOIN,struct.pack('>Q',gid))==[]
        checks.append('member-only personal flash; owner appoints manager; shared notice/join permission with per-recipient flags')
        invite=struct.pack('>QQ',c['id'],gid)
        assert await pb.request(p.INVITE,invite)==[(p.INVITE_ACK,struct.pack('>Q',c['id']))]
        assert await pc.take()==[(p.INVITED,p.invited(gid,b['name'],current()['name']))]
        assert await pc.request(p.INVITE_REPLY,struct.pack('>iQ',0,gid))==[]
        assert groups.store.initial(c['id'])['groups']==[]
        assert await pc.request(p.INVITE_REPLY,struct.pack('>iQ',1,gid))==[]
        await pc.connection.close()
        await pb.request(p.INVITE,invite)
        pc=Peer(rt);await pc.login(c)
        assert pc.initial[0][0]==sp.FRIENDS_INIT
        assert (p.INVITED,p.invited(gid,b['name'],current()['name'])) in pc.initial
        assert [k for k,_ in await pc.request(p.INVITE_REPLY,struct.pack('>iQ',1,gid))]==[p.UPDATED]
        await pa.take();await pb.take()
        assert len(groups.store.initial(c['id'])['groups'])==1
        checks.append('invite Agree=1 / Refuse=0; unsolicited replies rejected; offline invitation replay and authorized acceptance')
        assert await pc.request(p.MANAGER,struct.pack('>QQQ',1,gid,c['id']))==[]
        assert await pb.request(p.EXPEL,struct.pack('>QQ',a['id'],gid))==[]
        assert await pc.request(p.EXPEL,struct.pack('>QQ',b['id'],gid))==[]
        # Blacklist applies to retained history, including messages before joining.
        await pc.request(sp.ADD_SEND,struct.pack('>Q',a['id'])+sp.text(''))
        await pc.request(sp.MOVE_GROUP_SEND,sp.text(sp.GROUP_BLACK)+struct.pack('>Q',a['id'])+sp.text(''))
        sent=await pb.request(p.SEND,p.text('管理消息')+p.text('')+struct.pack('>Q',gid)+b'\0')
        assert await pa.take()==await pc.take()==sent
        history=await pc.request(p.HISTORY,struct.pack('>Qi',gid,-1))
        assert len(history)==1 and history[0][0]==p.HISTORY_PAGE
        page,last,rows=history_fields(history[0][1])
        assert page==1 and last and [(r[0],r[1]) for r in rows]==[('管理消息',b['name'])]
        # History pagination fixture contains no role assets; actual requests still
        # cross the runtime and native-encrypted connection, not a helper endpoint.
        with closing(store.connect()) as db,db:
            db.executemany('INSERT INTO common_group_messages(group_id,sender,plain,formatted,created_ms) VALUES(?,?,?,?,?)',
                [(gid,b['id'],f'分页{i:02d}','',int(time.time()*1000)+i) for i in range(25)])
        page,last,rows=history_fields((await pc.request(p.HISTORY,struct.pack('>Qi',gid,-1)))[0][1])
        assert page==2 and last and len(rows)==6
        page,last,rows=history_fields((await pc.request(p.HISTORY,struct.pack('>Qi',gid,1)))[0][1])
        assert page==1 and not last and len(rows)==20
        assert await pc.request(p.HISTORY,struct.pack('>Qi',gid,3))==[]
        member=next(m for m in current()['members'] if m['id']==c['id'])
        delayed=GroupHistoryDelivery(c['id'],pc.connection.epoch,p.HISTORY_PAGE,b'',gid,member['generation'],current()['version'],
            records=((a['id'],'屏蔽内容',a['name'],stamp),(b['id'],'可见内容',b['name'],stamp)),page=1,last=True)
        rt.social_runtime.offer(delayed)
        rows=history_fields((await pc.take())[0][1])[2]
        assert [(r[0],r[1]) for r in rows]==[('可见内容',b['name'])]
        checks.append('native history paging and request-time/recipient-time blacklist filtering without exposing blocked sender text')
        kicked=await pb.request(p.EXPEL,struct.pack('>QQ',c['id'],gid))
        assert [k for k,_ in kicked]==[p.UPDATED]
        await pa.take()
        assert await pc.take()==[(p.LEFT,struct.pack('>Q',gid))]
        rt.social_runtime.offer(delayed)
        assert await pc.take()==[]
        assert await pc.request(p.HISTORY,struct.pack('>Qi',gid,-1))==[]
        # A previously authorized invitation dies when its manager is demoted.
        await pb.request(p.INVITE,invite);notice=await pc.take()
        with closing(store.connect()) as db:
            token=db.execute('SELECT token FROM common_group_invitations WHERE group_id=? AND role_id=?',(gid,c['id'])).fetchone()[0]
        delayed_invite=GroupDelivery(c['id'],pc.connection.epoch,p.INVITED,notice[0][1],gid,'',current()['version'],0,token)
        await pa.request(p.MANAGER,struct.pack('>QQQ',0,gid,b['id']));await pb.take()
        rt.social_runtime.offer(delayed_invite)
        assert await pc.take()==[]
        assert await pc.request(p.INVITE_REPLY,struct.pack('>iQ',1,gid))==[]
        assert groups.store.initial(c['id'])['groups']==[] and current()['managers']==[]
        assert await pb.request(p.CONFIG,config(1,1,'撤权后公告',1))==[]
        checks.append('owner protected from expulsion; manager kicks ordinary member; stale history/invite denied after kick or demotion')
        before=current()
        for kind,body in ((p.CONFIG,struct.pack('>Qii',gid,0,1)+b'\x80'),(p.NAME,b'\x80'),
                (p.MANAGER,struct.pack('>QQQ',2,gid,b['id'])),(p.INVITE_REPLY,struct.pack('>iQ',2,gid)),
                (p.HISTORY,struct.pack('>Qi',gid,0)),(p.INVITE,b'bad')):
            assert await pb.request(kind,body)==[]
        assert current()==before
        assert await pb.request(100,b'ping')==[(100,b'ping')]
        checks.append('truncated native strings and invalid management enums leave state unchanged and connection responsive')
    finally:await rt.close()
    rt=GameRuntime(store,runtime_storage.prepare(store))
    try:
        pb=Peer(rt);await pb.login(b)
        group=rt.social_runtime.groups.store.initial(b['id'])['groups'][0]
        assert group['notice']=='群友同心' and group['allow_join']==0 and group['managers']==[]
        assert (p.INITIAL,p.initial([group],rt.online_snapshot(),b['id'])) in pb.initial
        assert next(m for m in group['members'] if m['id']==b['id'])['flash']==0
        checks.append('manager demotion, notice, public-join flag and personal message setting survive runtime restart')
    finally:await rt.close()


def check_migration():
    # Reproduce the exact previous table shape, including existing memberships.
    # Startup migration must add settings without resetting or deleting rows.
    with tempfile.TemporaryDirectory() as directory:
        store=AccountStore(Path(directory)/'old.db')
        role=store.create_role(1111,'旧群资料',12,1010101)
        with closing(store.connect()) as db,db:
            db.executescript('''CREATE TABLE common_groups (
              id INTEGER PRIMARY KEY AUTOINCREMENT,owner INTEGER NOT NULL REFERENCES roles(id),name TEXT UNIQUE NOT NULL,
              notice TEXT NOT NULL DEFAULT '',allow_join INTEGER NOT NULL DEFAULT 1,flash INTEGER NOT NULL DEFAULT 1,
              version INTEGER NOT NULL DEFAULT 1,active_ms INTEGER NOT NULL);
              CREATE TABLE common_group_members (
              group_id INTEGER NOT NULL REFERENCES common_groups(id) ON DELETE CASCADE,role_id INTEGER NOT NULL REFERENCES roles(id),
              manager INTEGER NOT NULL DEFAULT 0,generation TEXT NOT NULL,last_chat_ms INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(group_id,role_id));''')
            db.execute('INSERT INTO common_groups(id,owner,name,notice,active_ms) VALUES(1,?,?,?,?)',(role['id'],'原群名','原公告',int(time.time()*1000)))
            db.execute('INSERT INTO common_group_members(group_id,role_id,generation) VALUES(1,?,?)',(role['id'],'retained-generation'))
        from social_owner import SQLiteSocialStore
        from group_store import GroupStore
        social=SQLiteSocialStore(store.path);social.initialize()
        migrated=GroupStore(store.path,social.group_policy).initial(role['id'])['groups'][0]
        assert (migrated['name'],migrated['notice'])==('原群名','原公告')
        assert migrated['members'][0]['generation']=='retained-generation' and migrated['members'][0]['flash']==1
def main():
    checks=[]
    check_migration()
    checks.append('additive startup migration preserves previous group rows and membership generations')
    with tempfile.TemporaryDirectory() as directory:
        store=AccountStore(Path(directory)/'state.db')
        for name in ('管理甲','管理乙','管理丙'):store.create_role(1111,name,12,1010101)
        with closing(store.connect()) as db,db:db.execute('UPDATE roles SET level=20 WHERE id IN (1,2)')
        asyncio.run(check(store,checks))
    result=dict(passed=checks,native_gui_verified=False)
    write_json(OUT/'evidence/group-management-verification.json',result)
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
