"""Encrypted owner/connection integration of approval replay and recipient filters."""
import asyncio
import json
import struct
import tempfile
from pathlib import Path
from accounts import AccountStore
from game_runtime import GameRuntime
from verify_runtime import Peer
from inspect_client import OUT,write_json
import runtime_storage
import social_protocol as p


class RecordingPeer(Peer):
    async def request(self,kind,body):
        result=await super().request(kind,body)
        if kind==0xc003d:self.enter_result=result
        return result


async def check(store):
    rt=GameRuntime(store,runtime_storage.prepare(store))
    a,b,c=store.roles(1111)
    pa,pb=RecordingPeer(rt),RecordingPeer(rt)
    try:
        await pa.login(a);await pb.login(b)
        req=p.text('一起闯江湖')+struct.pack('>Q',b['id'])
        assert await pa.request(p.REQUEST_SEND,req)==[]
        assert await pb.take()==[(p.REQUEST_RECEIVE,p.request_notice(a,'一起闯江湖'))]
        assert await pb.request(p.AGREE_SEND,struct.pack('>Q',a['id']))==[]
        assert await pa.take()==[(p.ADD_RECEIVE,p.friend_added(b,True,p.GROUP_FRIEND))]
        assert rt.social_store.friends(a['id'])[0]['id']==b['id']
        await pb.request(p.ADD_SEND,struct.pack('>Q',a['id'])+p.text(''))
        move=p.text(p.GROUP_BLACK)+struct.pack('>Q',a['id'])+p.text('')
        assert (await pb.request(p.MOVE_GROUP_SEND,move))[0][0]==p.MOVE_GROUP_RECEIVE
        private=struct.pack('>Q',b['id'])+p.text('你好')+p.text('')+bytes(5)
        assert await pa.request(p.PRIVATE_SEND,private)==[] and await pb.take()==[]
        world=struct.pack('>i',p.WORLD_CHANNEL)+p.text('世界消息')+p.text('')+b'\0'
        assert (await pa.request(p.CHAT_SEND,world))[0][0]==p.CHAT_RECEIVE
        assert await pb.take()==[]
        await pb.request(p.MOVE_GROUP_SEND,p.text(p.GROUP_FRIEND)+struct.pack('>Q',a['id'])+p.text(''))
        reverse=struct.pack('>Q',a['id'])+p.text('双向消息')+p.text('')+bytes(5)
        replies=await asyncio.wait_for(asyncio.gather(pa.request(p.PRIVATE_SEND,private),pb.request(p.PRIVATE_SEND,reverse)),2)
        received_a=replies[0]+await pa.take()
        received_b=replies[1]+await pb.take()
        assert received_a==[(p.PRIVATE_RECEIVE,p.private_message(b,'双向消息'))]
        assert received_b==[(p.PRIVATE_RECEIVE,p.private_message(a,'你好'))]
        # Offline recipient: its pending application survives until its join.
        await pa.request(p.REQUEST_SEND,p.text('离线申请')+struct.pack('>Q',c['id']))
        pc=RecordingPeer(rt);await pc.login(c)
        assert pc.enter_result[0][0]==p.FRIENDS_INIT
        assert (p.REQUEST_RECEIVE,p.request_notice(a,'离线申请')) in pc.enter_result
        await pa.connection.close()
        await pc.request(p.AGREE_SEND,struct.pack('>Q',a['id']))
        assert rt.social_store.relation_events(a['id'])
        pa=RecordingPeer(rt);await pa.login(a)
        assert pa.enter_result[0][0]==p.FRIENDS_INIT
        assert {r['id'] for r in rt.social_store.friends(a['id'])}=={b['id'],c['id']}
        assert not rt.social_store.relation_events(a['id'])
        assert await pa.request(100,b'ping')==[(100,b'ping')]
        assert all(not e.poisoned for e in rt.social_runtime.endpoints.values())
    finally:await rt.close()
    assert not rt.social_runtime.endpoints


def main():
    with tempfile.TemporaryDirectory() as d:
        store=AccountStore(Path(d)/'state.db')
        for name in ('接线甲','接线乙','接线丙'):store.create_role(1111,name,12,1010101)
        asyncio.run(check(store))
    result={'passed':['encrypted approval end-to-end creates durable contact','recipient-owned private/public blacklist filter',
      'simultaneous bidirectional private messages without owner cycle','offline incoming request replay',
      'offline applicant approval outbox replay after login','friends initialization precedes replay notices',
      'continuous cipher/native MPPC across notifications and heartbeat','social endpoint shutdown cleanup'],
      'shared_runtime_integrated':True,'live_server_restarted':False,'native_gui_verified':False}
    write_json(OUT/'evidence/social-runtime-verification.json',result)
    print(json.dumps(result))


if __name__=='__main__':main()
