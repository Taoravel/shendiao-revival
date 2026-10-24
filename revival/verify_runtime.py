"""Disposable integration checks through actual owner/connection/storage Seams."""
import asyncio
from contextlib import closing
import hashlib
import hmac
from pathlib import Path
import struct
import tempfile
import threading
from unittest.mock import patch
from accounts import AccountStore
from connection_codec import ConnectionCodec
from crypto import ArcFour
from wire import frame,octets,read_octets,FrameReader
from verify_mppc_native import NativeDecoder
from runtime_core import BlockingIO,SerialOwner,Backpressure,StaleEpoch,AsyncLog
from game_runtime import GameRuntime,ConnectionOwner,Position
from inventory import AssetChange
from inspect_client import OUT,write_json
import runtime_storage
import social_protocol as sp


class Writer:
    def __init__(self): self.packets=[]; self.closed=False
    def write(self,data): self.packets.append(data)
    async def drain(self): await asyncio.sleep(0)
    def close(self): self.closed=True


class Peer:
    def __init__(self,rt):
        self.writer=Writer(); self.connection=ConnectionOwner(rt,self.writer)
        self.output=self.input=self.decoder=None
        self.frames=FrameReader()
    async def take(self):
        await asyncio.wait_for(self.connection.rt.social_runtime.idle(),1)
        await asyncio.wait_for(self.connection.queue.join(),1)
        packets=self.writer.packets[:]; self.writer.packets.clear()
        if self.input:
            packets=[self.decoder.feed(self.input.transform(x)) for x in packets]
        return self.frames.feed(b''.join(packets))
    async def request(self,kind,body):
        raw=frame(kind,body)
        await self.connection.receive(self.output.transform(raw) if self.output else raw)
        return await self.take()
    async def login(self,role):
        challenge,_=read_octets((await self.take())[0][1])
        secret=hashlib.md5(b'11111111').digest()
        proof=hmac.new(secret,challenge,hashlib.md5).digest()
        response=await self.request(103,octets(b'1111')+octets(proof)+bytes(4)+octets(b'')+bytes(4)+octets(b''))
        nonce,_=read_octets(response[0][1])
        self.output=ArcFour(hmac.new(secret,b'1111'+nonce,hashlib.md5).digest())
        nonce=b'0123456789abcdef'
        self.input=ArcFour(hmac.new(secret,b'1111'+nonce,hashlib.md5).digest()); self.decoder=NativeDecoder()
        assert (await self.request(106,octets(nonce)+bytes(4)))[0][0]==110
        assert (await self.request(0xc0078,struct.pack('>Q',role['id'])))==[(0xc0079,b'')]
        entered=await self.request(0xc0005,struct.pack('>Q',role['id'])+octets(b'')+b'\0')
        assert [k for k,b in entered[:3]]==[0xc0006,0xc0007,0xc0fa9]
        if len(entered)>3:
            # Explicit server-normalization command for the original Scene
            # state-setter exception. A broad extra-frame allowance hides bugs.
            _,offset=read_octets(entered[2][1])
            x,y=struct.unpack_from('>hh',entered[2][1],offset)
            map_id=struct.unpack_from('>Q',entered[2][1],offset+9)[0]
            assert map_id==1404 and entered[3:]==[(0xc0fa4,struct.pack('>QhhB',role['id'],x,y,0))]
        self.initial=await self.request(0xc003d,b'')


async def check(store,prepared):
    rt=GameRuntime(store,prepared)
    checks=[]
    try:
        a,b=store.roles(1111)
        pa,pb=Peer(rt),Peer(rt)
        await pa.login(a)
        rt.training=True
        await pb.login(b)
        rt.training=False
        checks.append('native decoder accepts authentication/preflight/world sequence')
        from inventory import QUERY_BAG,BAG_INFO
        from task_protocol import C_REQUEST_QUEST_CAN_ACCEPT,S_REQUEST_QUEST_CAN_ACCEPT
        # These fixture roles predate startup policy injection and have unknown
        # wallets. A bag response must not silently overwrite their cash with 0.
        assert await pa.request(QUERY_BAG,struct.pack('>iQ',1,0))==[]
        owner=rt.roles[a['id']]
        await owner.io(runtime_storage.initialize_role_wallet,store,1111,a['id'],owner.epoch,
                       (2**40+7,0,0,0),'explicit_migration')
        bag=await pa.request(QUERY_BAG,struct.pack('>iQ',1,0))
        assert bag[0][0]==BAG_INFO and struct.unpack_from('>Q',bag[0][1],4)[0]==2**40+7
        assert (await pa.request(C_REQUEST_QUEST_CAN_ACCEPT,b''))[0][0]==S_REQUEST_QUEST_CAN_ACCEPT
        checks.append('prepared inventory/task routing; unknown cash refused and explicit64-bit cash preserved')
        private=struct.pack('>Q',b['id'])+sp.text('你好')+sp.text('')+bytes(5)
        assert await pa.request(sp.PRIVATE_SEND,private)==[]
        assert (await pb.take())==[(sp.PRIVATE_RECEIVE,sp.private_message(a,'你好'))]
        assert await pb.request(100,bytes(4))==[(100,bytes(4))]
        checks.append('logical cross-connection social delivery preserves continuous native RC4/MPPC')
        owner=rt.roles[a['id']]
        change=AssetChange('runtime:once',grants=((31000,100),),pets=(500001,))
        first=await owner.mailbox.call('settle',change)
        second=await owner.mailbox.call('settle',change)
        assert first==second
        snap=await owner.io(owner.inventory.snapshot)
        assert sum(i['quantity'] for i in snap['items'])==100 and len(snap['pets'])==1
        try:
            await owner.mailbox.call('settle',AssetChange('runtime:rollback',grants=((31000,1),),pets=(-1,)))
        except ValueError: pass
        else: raise AssertionError('Invalid settlement committed')
        assert await owner.io(owner.inventory.snapshot)==snap
        with closing(store.connect()) as db:
            assert not db.execute('SELECT 1 FROM role_settlements WHERE settlement_id=?',('runtime:rollback',)).fetchone()
        checks.append('role-owner atomic asset/common receipt replay applies once')
        # Pause an actual role storage call. Other map and battle owners remain runnable.
        entered,release=threading.Event(),threading.Event()
        original_settle=runtime_storage.settle
        def slow(*args):
            entered.set()
            if not release.wait(2): raise TimeoutError('Fixture release missing')
            return original_settle(*args)
        injection=patch.object(runtime_storage,'settle',slow)
        injection.start()
        pending=asyncio.create_task(owner.mailbox.call('settle',AssetChange('runtime:slow')))
        try:
            assert await asyncio.to_thread(entered.wait,1)
            assert await asyncio.wait_for(pb.request(100,b'abcd'),.5)==[(100,b'abcd')]
            pos=Position(999,99,(1014,896,3776),1,(56,236))
            assert await asyncio.wait_for(rt.map(1014).mailbox.call('join',pos),.5)==pos
            moved,blocked=await asyncio.wait_for(rt.map(1014).mailbox.call('move',999,99,1,
                0xc0fa1,struct.pack('>hhhhQ',896,3776,912,3792,0)),.5)
            assert not blocked and moved.value==pos.value
            from battle_protocol import SEND_ACTION,ROUND_SCRIPT
            assert [k for k,b in await asyncio.wait_for(pb.request(SEND_ACTION,struct.pack('>iiiBB',1,21,0,1,0)),.5)]==[ROUND_SCRIPT]
            checks.append('controlled slow role I/O: peer heartbeat, other map and battle progress before release')
        finally:
            release.set(); await pending; injection.stop()
        # One mailbox orders conflicting commands while leaving another independent.
        gate=asyncio.Event(); order=[]
        async def serial(command):
            order.append(command.operation)
            if command.operation=='first': await gate.wait()
            return tuple(order)
        mailbox=SerialOwner('ordered',serial,capacity=1)
        first=asyncio.create_task(mailbox.call('first')); await asyncio.sleep(0)
        await asyncio.sleep(0)
        second=asyncio.create_task(mailbox.call('second')); await asyncio.sleep(0)
        try: await mailbox.call('overflow')
        except Backpressure: pass
        else: raise AssertionError('Mailbox did not reject overflow')
        gate.set(); await first
        assert await second==('first','second')
        await mailbox.close()
        checks.append('same-owner FIFO and bounded mailbox reject')
        old_epoch=pa.connection.epoch
        fenced=store.leased(1111,a['id'],old_epoch)
        await pa.connection.close()
        pa=Peer(rt); await pa.login(a)
        try:
            with closing(fenced.connect()) as db,db:
                db.execute('UPDATE roles SET level=2 WHERE id=?',(a['id'],))
        except StaleEpoch: pass
        else: raise AssertionError('Old epoch wrote after reconnect')
        assert not pa.connection.offer(100,b'old!',old_epoch)
        replay=await rt.roles[a['id']].mailbox.call('settle',change)
        assert replay['settlement_id']=='runtime:once' and replay['created_pet_ids']==[snap['pets'][0]['id']]
        checks.append('old epoch cannot write/send; reconnect receipt persists')
        slow_writer=Writer()
        slow_conn=ConnectionOwner(rt,slow_writer,capacity=1)
        assert not slow_conn.offer(100,b'full') and slow_writer.closed
        await slow_conn.close()
        checks.append('full target send queue disconnects slow connection')
    finally:
        await rt.close()
    return checks


def main():
    with tempfile.TemporaryDirectory() as temp:
        store=AccountStore(Path(temp)/'state.sqlite3')
        store.create_role(1111,'运行甲',12,1010101)
        store.create_role(1111,'运行乙',11,1010109)
        prepared=runtime_storage.prepare(store)
        checks=asyncio.run(check(store,prepared))
    result={'passed':checks,'live_server_changed':False,'commercial_capacity_verified':False,
            'remaining':['SQLite file single writer','native general-scene ready binding and handoff fault recovery',
                         'unsupported task reward channels and activation policy','native UI live regression']}
    write_json(OUT/'evidence/runtime-verification.json',result)
    print(result)


if __name__=='__main__': main()
