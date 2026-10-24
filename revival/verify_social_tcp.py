"""Real temporary TCP listener: two encrypted clients approve and filter chat."""
import asyncio
import hashlib
import hmac
import json
import struct
import tempfile
from pathlib import Path
from accounts import AccountStore
from game_runtime import GameRuntime
from crypto import ArcFour
from wire import FrameReader,frame,octets,read_octets
from verify_mppc_native import NativeDecoder
from inspect_client import OUT,write_json
import runtime_storage
import social_protocol as p


class TCPPeer:
    def __init__(self,reader,writer):
        self.reader,self.writer=reader,writer
        self.frames=FrameReader();self.pending=[]
        self.outgoing=self.incoming=self.decoder=None

    async def send(self,kind,body):
        data=frame(kind,body)
        self.writer.write(self.outgoing.transform(data) if self.outgoing else data)
        await self.writer.drain()

    async def read(self,kind):
        async def wait():
            while True:
                for i,(k,b) in enumerate(self.pending):
                    if k==kind:return self.pending.pop(i)[1]
                data=await self.reader.read(65536)
                if not data:raise ConnectionError('Unexpected TCP close')
                if self.incoming:data=self.decoder.feed(self.incoming.transform(data))
                self.pending.extend(self.frames.feed(data))
        return await asyncio.wait_for(wait(),3)

    async def login(self,role):
        challenge,_=read_octets(await self.read(101))
        secret=hashlib.md5(b'11111111').digest()
        proof=hmac.new(secret,challenge,hashlib.md5).digest()
        await self.send(103,octets(b'1111')+octets(proof)+bytes(4)+octets(b'')+bytes(4)+octets(b''))
        nonce,_=read_octets(await self.read(106))
        self.outgoing=ArcFour(hmac.new(secret,b'1111'+nonce,hashlib.md5).digest())
        client_nonce=b'0123456789abcdef'
        self.incoming=ArcFour(hmac.new(secret,b'1111'+client_nonce,hashlib.md5).digest());self.decoder=NativeDecoder()
        await self.send(106,octets(client_nonce)+bytes(4));await self.read(110)
        await self.send(0xc0005,struct.pack('>Q',role['id'])+octets(b'')+b'\0')
        for kind in (0xc0006,0xc0007,0xc0fa9):await self.read(kind)
        await self.send(0xc003d,b'');await self.read(p.FRIENDS_INIT)

    async def close(self):
        self.writer.close();await self.writer.wait_closed()


async def check(store):
    loop=asyncio.get_running_loop();errors=[]
    previous=loop.get_exception_handler()
    loop.set_exception_handler(lambda loop,context:errors.append(context))
    runtime=GameRuntime(store,runtime_storage.prepare(store))
    server=await asyncio.start_server(runtime.handle_socket,'127.0.0.1',0)
    port=server.sockets[0].getsockname()[1]
    peers=[]
    try:
        roles=store.roles(1111)
        for role in roles:
            peer=TCPPeer(*await asyncio.open_connection('127.0.0.1',port));peers.append(peer)
            await peer.login(role)
        a,b=roles;pa,pb=peers
        await pa.send(p.REQUEST_SEND,p.text('真实网络申请')+struct.pack('>Q',b['id']))
        assert await pb.read(p.REQUEST_RECEIVE)==p.request_notice(a,'真实网络申请')
        await pb.send(p.AGREE_SEND,struct.pack('>Q',a['id']))
        assert await pa.read(p.ADD_RECEIVE)==p.friend_added(b,True,p.GROUP_FRIEND)
        await pb.send(p.ADD_SEND,struct.pack('>Q',a['id'])+p.text(''));await pb.read(p.ADD_RECEIVE)
        await pb.send(p.MOVE_GROUP_SEND,p.text(p.GROUP_BLACK)+struct.pack('>Q',a['id'])+p.text(''))
        await pb.read(p.MOVE_GROUP_RECEIVE)
        await pa.send(p.CHAT_SEND,struct.pack('>i',p.WORLD_CHANNEL)+p.text('屏蔽验证')+p.text('')+b'\0')
        await pa.read(p.CHAT_RECEIVE)
        await runtime.social_runtime.idle()
        await pb.send(100,b'ping');assert await pb.read(100)==b'ping'
        assert not any(k==p.CHAT_RECEIVE for k,_ in pb.pending)
        assert {row['id'] for row in runtime.social_store.friends(a['id'])}=={b['id']}
    finally:
        for peer in peers:await peer.close()
        server.close();await server.wait_closed()
        await runtime.close()
        await asyncio.sleep(0)
        loop.set_exception_handler(previous)
    assert not errors,[str(e.get('exception',e.get('message'))) for e in errors]


def main():
    with tempfile.TemporaryDirectory() as d:
        store=AccountStore(Path(d)/'tcp.db')
        for name in ('网络甲','网络乙'):store.create_role(1111,name,12,1010101)
        asyncio.run(check(store))
    result={'transport':'real ephemeral loopback TCP, two authenticated encrypted clients',
      'passed':['friend request visible to recipient','acceptance persists and notifies applicant',
                'native MPPC and continuous cipher decode','public blacklist filter before target send','heartbeat remains responsive'],
      'persistent_user_store_changed':False,'live_listener_28993_changed':False,'native_gui_verified':False}
    write_json(OUT/'evidence/social-tcp-verification.json',result);print(json.dumps(result))


if __name__=='__main__':main()
