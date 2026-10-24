"""Controlled blocked group I/O: cancellation preserves entity ownership."""
import asyncio
from contextlib import closing
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
from social_owner import SocialCommand
from verify_runtime import Peer
from inspect_client import OUT,write_json
import runtime_storage
import group_protocol as p


async def check(store):
    rt=GameRuntime(store,runtime_storage.prepare(store))
    release=threading.Event()
    try:
        a,b=store.roles(1111);pa,pb=Peer(rt),Peer(rt)
        await pa.login(a);await pb.login(b)
        ids=[]
        for name in ('并发甲群','并发乙群'):
            await pa.request(p.CREATE,b'')
            response=await pa.request(p.NAME,p.text(name))
            ids.append(struct.unpack_from('>Q',response[0][1])[0])
        groups=rt.social_runtime.groups
        first,other=ids
        entered=threading.Event();seen=[]
        original=groups.store.execute
        def command(kind,body):
            s=rt.online_snapshot()[a['id']]
            return s,SocialCommand(a['id'],s.login_epoch,uuid.uuid4().hex,int(time.time()*1000)+5000,kind,body)
        def slow(s,cmd,now):
            if cmd.kind==p.SEND and p.message_request(cmd.body)[0]==first:
                entered.set()
                if not release.wait(3):raise AssertionError('Missing fixture release')
            seen.append((cmd.kind,p.identity(cmd.body) if cmd.kind==p.LEAVE else p.message_request(cmd.body)[0]))
            return original(s,cmd,now)
        send=lambda gid:p.text('并发验证')+p.text('')+struct.pack('>Q',gid)+b'\0'
        with patch.object(groups.store,'execute',slow):
            s,cmd=command(p.SEND,send(first))
            abandoned=asyncio.create_task(groups.request(s,cmd,int(time.time()*1000)))
            assert await asyncio.to_thread(entered.wait,1)
            actor=groups.owners[('group',first)]['owner']
            abandoned.cancel()
            try:await abandoned
            except asyncio.CancelledError:pass
            s,next_cmd=command(p.LEAVE,struct.pack('>Q',first))
            following=asyncio.create_task(groups.request(s,next_cmd,int(time.time()*1000)))
            for _ in range(3):await asyncio.sleep(0)
            assert groups.owners[('group',first)]['owner'] is actor and not following.done()
            s,independent=command(p.SEND,send(other))
            assert not (await asyncio.wait_for(groups.request(s,independent,int(time.time()*1000)),.7)).rejection
            assert await asyncio.wait_for(pb.request(100,b'ping'),.7)==[(100,b'ping')]
            assert not following.done()
            release.set()
            assert not (await following).rejection
        assert seen.index((p.SEND,first))<seen.index((p.LEAVE,first))
        assert len(groups.store.initial(a['id'])['groups'])==1
        await rt.social_runtime.idle()
        assert not groups.owners and not groups.inflight
    finally:
        release.set();await rt.close()


def main():
    with tempfile.TemporaryDirectory() as directory:
        store=AccountStore(Path(directory)/'state.db')
        for name in ('并发群主','并发路人'):store.create_role(1111,name,12,1010101)
        with closing(store.connect()) as db,db:db.execute('UPDATE roles SET level=20')
        asyncio.run(check(store))
    result=dict(passed=['caller cancellation retains original group owner until accepted work finishes',
        'same-group leave waits behind blocked message commit','independent group chat commits before release',
        'unrelated role heartbeat responds before release','correct durable order and idle owner cleanup'],
        native_gui_verified=False,commercial_capacity_verified=False)
    write_json(OUT/'evidence/group-concurrency-verification.json',result)
    print(json.dumps(result))


if __name__=='__main__':main()
