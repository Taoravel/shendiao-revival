"""Manual leveling/allocation through role/connection/storage owners, no battle."""
import asyncio
from contextlib import closing
import json
from pathlib import Path
import struct
import tempfile
from accounts import AccountStore
from game_runtime import GameRuntime
from inspect_client import OUT,write_json
from item_effects import VitalState
from role_attributes import AttributeBaseline
from role_attribute_storage import initialize_attribute_baseline
from role_growth import initialize_growth
from role_growth_protocol import C_REQ_LEVEL_UP,C_ADD_POINT_TO_ATTR
from runtime_core import StaleEpoch
from verify_growth_runtime import GrowthPeer,role_values,world_vitals
import runtime_storage


def levels(runtime,owner):
    endpoint=runtime.social_runtime.endpoints[owner.id]
    return (owner.role['level'],owner.snapshot().level,runtime.online[owner.id].level,
            endpoint.snapshot.level,endpoint.domain.snapshot.level)


async def check(store,prepared,role,missing):
    runtime=GameRuntime(store,prepared)
    try:
        peer=GrowthPeer(runtime);await peer.login(role)
        owner=runtime.roles[role['id']]
        first_epoch=owner.epoch
        request=struct.pack('>i',0)
        # Growing the protocol set must never reinterpret another operation's
        # short body as a valid upgrade request.
        assert await peer.request(C_ADD_POINT_TO_ATTR,request)==[]
        assert levels(runtime,owner)==(10,)*5
        first=await peer.request(C_REQ_LEVEL_UP,request)
        assert [kind for kind,_ in first]==[0xc000d,0xc32c8]
        assert role_values(first)[490]==11 and role_values(first)[500]==5
        assert levels(runtime,owner)==(11,)*5
        second=await peer.request(C_REQ_LEVEL_UP,request)
        assert role_values(second)[490]==12 and role_values(second)[500]==10
        assert levels(runtime,owner)==(12,)*5
        assert owner.role['experience']==7
        with closing(store.connect()) as db:
            receipts=db.execute('SELECT request_id,result FROM role_growth_receipts WHERE role_id=?',
                                (role['id'],)).fetchall()
        assert len(receipts)==2
        first_id=next(key for key,data in receipts if json.loads(data)['level']==11)
        replay=await owner.mailbox.call('receive',C_REQ_LEVEL_UP,request,request_id=first_id)
        for kind,body in replay:peer.connection.offer(kind,body,owner.epoch)
        assert await peer.take()==second
        assert levels(runtime,owner)==(12,)*5
        for body in (request,b'',bytes(3),bytes(5),struct.pack('>i',99),struct.pack('>i',-1)):
            assert await peer.request(C_REQ_LEVEL_UP,body)==[]
        # Sentinel guards only: neither battle nor transfer execution starts.
        owner.battle=object()
        allocation=struct.pack('>5i',0,0,0,1,2)
        try:
            assert await peer.request(C_REQ_LEVEL_UP,request)==[]
            assert await peer.request(C_ADD_POINT_TO_ATTR,allocation)==[]
        finally:owner.battle=None
        owner.transfer=object()
        try:
            assert await peer.request(C_REQ_LEVEL_UP,request)==[]
            assert await peer.request(C_ADD_POINT_TO_ATTR,allocation)==[]
        finally:owner.transfer=None
        allocated=await peer.request(C_ADD_POINT_TO_ATTR,allocation)
        values=role_values(allocated)
        assert {k:values[k] for k in (490,500,40,50,100,120,130)}=={
            490:12,500:7,40:14,50:13,100:17,120:26,130:12}
        assert levels(runtime,owner)==(12,)*5
        more=struct.pack('>5i',1,0,0,0,0)
        latest=await peer.request(C_ADD_POINT_TO_ATTR,more)
        assert role_values(latest)[500]==6 and role_values(latest)[60]==100
        with closing(store.connect()) as db:
            receipts=db.execute('SELECT request_id,result FROM role_growth_receipts WHERE role_id=?',
                                (role['id'],)).fetchall()
        allocation_id=next(key for key,data in receipts if json.loads(data)['allocated_points']==[0,0,0,2,1])
        for opcode,body,key in ((C_ADD_POINT_TO_ATTR,allocation,allocation_id),(C_REQ_LEVEL_UP,request,first_id)):
            replay=await owner.mailbox.call('receive',opcode,body,request_id=key)
            for kind,payload in replay:peer.connection.offer(kind,payload,owner.epoch)
            assert await peer.take()==latest
        try:await owner.mailbox.call('receive',C_ADD_POINT_TO_ATTR,more,request_id=allocation_id)
        except ValueError:pass
        else:raise AssertionError('Allocation request ID accepted changed intent')
        for body in (bytes(20),struct.pack('>5i',-1,0,0,0,0),struct.pack('>5i',7,0,0,0,0),bytes(19),bytes(21)):
            assert await peer.request(C_ADD_POINT_TO_ATTR,body)==[]
        other=GrowthPeer(runtime);await other.login(missing)
        assert await other.request(C_REQ_LEVEL_UP,request)==[]
        assert await other.request(C_ADD_POINT_TO_ATTR,allocation)==[]
        await other.connection.close()
        await peer.connection.close()
        peer=GrowthPeer(runtime);await peer.login(role)
        assert world_vitals(peer)==(12,(100,130,130,52,112))
        assert role_values(peer.initial)[500]==6
        owner=runtime.roles[role['id']]
        assert levels(runtime,owner)==(12,)*5
        try:runtime_storage.manual_level(store,1111,role['id'],first_epoch,0,'expired')
        except StaleEpoch:pass
        else:raise AssertionError('Expired role lease upgraded')
        with closing(store.connect()) as db:
            assert db.execute('SELECT COUNT(*) FROM role_growth_receipts WHERE role_id=?',
                              (role['id'],)).fetchone()==(4,)
            assert db.execute('SELECT 1 FROM role_growth WHERE role_id=?',(missing['id'],)).fetchone() is None
    finally:await runtime.close()


def main():
    with tempfile.TemporaryDirectory(prefix='manual-level-runtime-') as folder:
        store=AccountStore(Path(folder)/'state.sqlite3')
        role=store.create_role(1111,'升级入口',11,1010109)
        missing=store.create_role(1111,'未知成长',11,1010109)
        prepared=runtime_storage.prepare(store)
        epoch=store.acquire_lease(1111,role['id'])
        with closing(store.leased(1111,role['id'],epoch).connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('UPDATE roles SET level=10 WHERE id=?',(role['id'],))
            db.execute('INSERT INTO role_progress VALUES(?,?)',
                       (role['id'],store.growth_rules.costs[10]+store.growth_rules.costs[11]+7))
            growth=initialize_growth(db,1111,role['id'],epoch,store.growth_rules,expected_level=10,free_points=0)
            initialize_attribute_baseline(db,1111,role['id'],epoch,
                AttributeBaseline(role['id'],10,0,(10,10,10,10,10),(100,100,20,5,40,20,10,20,5)),
                growth,store.attribute_rules,VitalState(role['id'],0,70,100,40,100))
        asyncio.run(check(store,prepared,role,missing))
    report=dict(passed=['native request owner route upgrades L10 to11 then12, one level per new request',
        'committed level reaches role, online and both social snapshots before current displays',
        'trusted old request replay returns current L12/XP7/free10 without another debit',
        'insufficient XP, malformed/nonzero mode, missing profile and old epoch refuse',
        'allocation opcode with a four-byte zero never dispatches a level upgrade',
        'asymmetric native allocation swaps AGI/END correctly and spends only current free points',
        'old allocation/upgrade replay after further allocation refresh current stats without re-debit',
        'zero/negative/excess allocation and changed intent on old key refuse',
        'battle/transfer guard sentinels reject without starting either subsystem',
        'continuous native MPPC/RC4 responses and reconnect preserve HP100/130 MP52/112 and free6'],
        database='disposable',battle_executed=False,native_gui_verified=False,live_server_changed=False)
    write_json(OUT/'evidence/manual-level-runtime-verification.json',report)
    print(report)


if __name__=='__main__':main()
