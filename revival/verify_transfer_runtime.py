"""Durable portal handoff and designed exact-send activation at runtime Seams."""
import asyncio
from contextlib import closing
from pathlib import Path
import struct
import tempfile
from accounts import AccountStore
from game_runtime import GameRuntime
from game_runtime import SceneSendBarrier
from runtime_core import StaleEpoch
from wire import frame
import runtime_storage
from verify_runtime import Peer
from inspect_client import OUT,write_json


async def check(store,prepared,role):
    rt=GameRuntime(store,prepared)
    try:
        p=Peer(rt);await p.login(role)
        stop=b'\0'+struct.pack('>hhQ',8592,7104,0)
        gate=asyncio.Event()
        async def blocked_drain(): await gate.wait()
        p.writer.drain=blocked_drain
        await p.connection.receive(p.output.transform(frame(0xc0faa,stop)+frame(0xc0faa,stop)))
        await asyncio.sleep(0)
        owner=rt.roles[role['id']]
        assert owner.transfer and owner.position.value==(1014,896,3776)
        assert role['id'] not in rt.map(1007).positions
        with closing(store.connect()) as db:
            assert db.execute('SELECT map_id,x,y FROM role_positions WHERE role_id=?',(role['id'],)).fetchone()==(1014,896,3776)
            assert db.execute('SELECT stage FROM world_handoffs WHERE role_id=?',(role['id'],)).fetchone()==('committed',)
        version=owner.position.version
        assert p.connection.metrics['old_scene_batch_rejected']==1
        assert owner.position.version==version
        bad=SceneSendBarrier(role['id'],owner.epoch,p.connection.generation+1,
            owner.transfer.frozen.reservation.offer.transfer_id,version,b'wrong')
        try: await owner.mailbox.call('scene_sent',bad)
        except StaleEpoch: pass
        else: raise AssertionError('Foreign send barrier accepted')
        gate.set()
        result=await p.take()
        assert result[0][0]==0xc0fa9
        assert not owner.transfer
        assert await p.request(0xc0faa,stop)==[]
        await p.request(0xc0fa1,struct.pack('>hhhhQ',896,3776,912,3792,0))
        await p.request(0xc0faa,b'\0'+struct.pack('>hhQ',912,3792,0))
        assert owner.position.value==(1014,912,3792)
        await p.connection.close()
    finally: await rt.close()
    # New runtime = process-loss recovery from committed target snapshot.
    rt=GameRuntime(store,prepared)
    try:
        p=Peer(rt);await p.login(role)
        assert rt.roles[role['id']].position.value==(1014,912,3792)
    finally:await rt.close()
    return {'passed':['portal reserve/freeze/activate','target and durable handoff commit together',
            'source finalized after durable commit','same source read batch remainder rejected',
            'foreign send barrier refused','exact scene write/drain barrier releases target',
            'stale source point refused; target move continues','new runtime reloads committed target'],
            'activation':'designed server delivery barrier; not a client loading acknowledgement',
            'native_general_scene_ready_verified':False,'live_server_changed':False}


def main():
    with tempfile.TemporaryDirectory() as d:
        store=AccountStore(Path(d)/'transfer.sqlite3')
        role=store.create_role(1111,'过图测试',12,1010101)
        prepared=runtime_storage.prepare(store)
        result=asyncio.run(check(store,prepared,role))
    write_json(OUT/'evidence/transfer-runtime.json',result)
    print(result)


if __name__=='__main__':main()
