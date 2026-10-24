"""One disposable role-medicine slice through live owner routing and native wire."""
import asyncio
from contextlib import closing
from dataclasses import replace
from pathlib import Path
import struct
import tempfile
from unittest.mock import patch
from accounts import AccountStore
from game_runtime import GameRuntime
from inventory import USE_ITEM,QUERY_BAG
from item_effects import VitalState
from native_gameplay_probe import probe
from native_inspect import u32
from role_growth import initialize_growth
from role_attributes import AttributeBaseline
from role_attribute_storage import initialize_attribute_baseline,read_attribute_snapshot,update_role_vitals
import runtime_storage
from verify_runtime import Peer
from inspect_client import OUT,write_json


async def check(store,prepared,role,missing):
    runtime=GameRuntime(store,prepared)
    try:
        peer=Peer(runtime);await peer.login(role)
        owner=runtime.roles[role['id']]
        epoch=owner.epoch
        # Legacy fixture cash is explicitly known, independently of its resource
        # baseline. A bag refresh must preserve it instead of supplying default0.
        await owner.io(runtime_storage.initialize_role_wallet,store,1111,role['id'],epoch,
                       (1234,0,0,0),'explicit_migration')
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            growth=initialize_growth(db,1111,role['id'],epoch,store.growth_rules,expected_level=1,free_points=0)
            initialize_attribute_baseline(db,1111,role['id'],epoch,
                AttributeBaseline(role['id'],1,0,(10,10,10,10,10),(500,1000,20,5,40,20,10,20,5)),
                growth,store.attribute_rules,VitalState(role['id'],0,1,500,1,1000))
        await owner.io(owner.inventory.grant_item,32000,3)
        key=(await owner.io(owner.inventory.snapshot))['items'][0]['id']
        body=struct.pack('>iiQ',key,0,role['id'])
        replies=await peer.request(USE_ITEM,body)
        assert [kind for kind,_ in replies]==[0xc32c8,0xc03f3], 'Role use-item context handler not connected'
        assert struct.unpack_from('>Q',replies[1][1],4)[0]==1234
        probe(0xec3590,0xec36b0,0xec3730,payload=replies[0][1])
        probe(0xef6220,u32(0x2284234),u32(0x2284238),payload=replies[1][1])
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            current=read_attribute_snapshot(db,1111,role['id'],epoch)
            assert current.vitals.hp==201
            request_id=db.execute('SELECT settlement_id FROM inventory_role_consumables WHERE role_id=?',
                                  (role['id'],)).fetchone()[0]
            update_role_vitals(db,1111,role['id'],epoch,current.vitals,
                              replace(current.vitals,hp=10,version=current.vitals.version+1))
        before=await owner.io(owner.inventory.snapshot)
        # Retry the same trusted command ID; ordinary new wire clicks have no
        # client retry token and are distinct operations, not inferred retries.
        retried=await owner.mailbox.call('receive',USE_ITEM,body,request_id=request_id)
        for kind,payload in retried:peer.connection.offer(kind,payload,epoch)
        retry_wire=await peer.take()
        assert struct.unpack_from('>f',retry_wire[0][1],5)[0]==10
        assert await owner.io(owner.inventory.snapshot)==before
        for malformed in (body[:-1],struct.pack('>iiQ',key,0,missing['id'])):
            assert await peer.request(USE_ITEM,malformed)==[]
        # These sentinels exercise the existing guards, without starting battle
        # or a map handoff and without invoking either subsystem.
        owner.battle=object()
        try:assert await peer.request(USE_ITEM,body)==[]
        finally:owner.battle=None
        owner.transfer=object()
        try:assert await peer.request(USE_ITEM,body)==[]
        finally:owner.transfer=None
        assert await owner.io(owner.inventory.snapshot)==before
        pet_body=struct.pack('>iiQ',key,1,999)
        with patch.object(owner.inventory,'receive',return_value=[]) as pet_route:
            assert await peer.request(USE_ITEM,pet_body)==[]
            pet_route.assert_called_once()
            args=pet_route.call_args.args
            assert args[:2]==(USE_ITEM,pet_body) and len(args)==3 and callable(args[2])
        other=Peer(runtime);await other.login(missing)
        other_owner=runtime.roles[missing['id']]
        await other_owner.io(other_owner.inventory.grant_item,32000)
        other_before=await other_owner.io(other_owner.inventory.snapshot)
        other_key=other_before['items'][0]['id']
        assert await other.request(USE_ITEM,struct.pack('>iiQ',other_key,0,missing['id']))==[]
        assert await other_owner.io(other_owner.inventory.snapshot)==other_before
        with closing(store.connect()) as db:
            db.execute('BEGIN')
            assert read_attribute_snapshot(db,1111,role['id'],epoch).vitals.hp==10
            assert db.execute('SELECT quantity FROM inventory_items WHERE id=?',(key,)).fetchone()==(2,)
    finally:await runtime.close()
    return {'passed':['native CUseItem role kind routed with current epoch/request_id',
            'real explicit baseline healing and one-item debit',
            'continuous RC4/native MPPC replies accepted by original world-map and bag decoders',
            'same trusted request replay consumes once and refreshes current wounds',
            'truncated/foreign target refused before write','existing battle/transfer guards prevent medicine',
            'pet kind retains legacy route','missing baseline refuses without training resource fallback'],
            'database':'disposable','battle_started':False,'online_server_changed':False,'native_gui_tested':False}


def main():
    with tempfile.TemporaryDirectory() as directory:
        store=AccountStore(Path(directory)/'medicine.sqlite3')
        # These are explicit legacy baseline/missing-baseline fixtures. New
        # prepared creations now correctly own a durable automatic template.
        role=store.create_role(1111,'药品接线',12,1010101)
        missing=store.create_role(1111,'缺少基线',12,1010101)
        prepared=runtime_storage.prepare(store)
        result=asyncio.run(check(store,prepared,role,missing))
    write_json(OUT/'evidence/role-consumable-runtime.json',result)
    print(result)


if __name__=='__main__':main()
