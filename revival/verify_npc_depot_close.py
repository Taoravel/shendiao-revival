"""Original keyless warehouse-close codec and actual owner access invalidation."""
import asyncio
from pathlib import Path
import struct
import tempfile
from accounts import AccountStore
from game_runtime import GameRuntime
from inventory import QUERY_BAG
from native_gameplay_probe import probe
from verify_runtime import Peer
from inspect_client import OUT,write_json
import npc_depot
import npc_gameplay
import runtime_storage


async def check(store,prepared,role,npc):
    rt=GameRuntime(store,prepared)
    try:
        peer=Peer(rt);await peer.login(role);owner=rt.roles[role['id']]
        await owner.io(npc_gameplay.initialize_depot,owner.inventory,98765,'explicit_migration')
        key=(npc.map_id<<32)|npc.placement_id
        query=struct.pack('>iQ',2,0)
        assert await peer.request(QUERY_BAG,query)==[]
        assert await peer.request(npc_depot.OPEN_DEPOT,struct.pack('>q',key))
        assert await peer.request(npc_depot.CLOSE_DEPOT,b'\0')==[]
        assert await peer.request(QUERY_BAG,query), 'Malformed close revoked an otherwise valid warehouse access'
        assert await peer.request(npc_depot.CLOSE_DEPOT,b'')==[]
        assert await peer.request(QUERY_BAG,query)==[], 'Native close left warehouse access active'
        assert await peer.request(npc_depot.CLOSE_DEPOT,b'')==[]
        assert await peer.request(npc_depot.OPEN_DEPOT,struct.pack('>q',key))
        assert await peer.request(QUERY_BAG,query)
        # Controlled occupancy fixtures check gate precedence only. No battle,
        # intro or map handoff is executed or claimed by these two cases.
        for attribute in ('transfer','battle'):
            assert await peer.request(npc_depot.OPEN_DEPOT,struct.pack('>q',key))
            before=await owner.io(owner.inventory.snapshot)
            previous=getattr(owner,attribute)
            setattr(owner,attribute,object())
            try:
                assert await peer.request(npc_depot.CLOSE_DEPOT,b'\0')==[]
                assert owner.npc_depot_ticket is not None
                assert await peer.request(npc_depot.CLOSE_DEPOT,b'')==[]
                assert owner.npc_depot_ticket is None
            finally:setattr(owner,attribute,previous)
            assert await peer.request(QUERY_BAG,query)==[]
            assert await owner.io(owner.inventory.snapshot)==before
        return {'passed':['native keyless empty close invalidates current role access',
            'malformed close rejects before revoking an existing valid access',
            'duplicate close is harmless; reopening reauthorizes same known warehouse',
            'controlled loading/battle occupancy gates preserve malformed access and permit valid revocation'],
            'state_gate_fixtures_only':True,'battle_executed':False,'scene_handoff_executed':False,
            'native_gui_verified':False,'live_database_modified':False}
    finally:await rt.close()


def main():
    original,raw=probe(0xd8efd0,0xd8eff0,0xd8f000)
    assert original==b'' and struct.unpack_from('<I',raw,4)[0]==npc_depot.CLOSE_DEPOT
    npc_depot.decode_close(original)
    for invalid in (b'\0',b'\0'*8,bytearray()):
        try:npc_depot.decode_close(invalid)
        except ValueError:pass
        else:raise AssertionError('Unknown close fields accepted')
    write_json(OUT/'evidence/npc-depot-close-native.json',{
        'protocol':'0xc04fb','constructor':'0xd8efd0','marshal':'0xd8eff0','unmarshal':'0xd8f000',
        'original_body':'empty','native_ui_close_sender':'0x10c221a..0x10c223f',
        'server_rejects_unknown_fields':True,'native_gui_verified':False})
    with tempfile.TemporaryDirectory() as temp:
        store=AccountStore(Path(temp)/'close.sqlite3');role=store.create_role(1111,'关闭仓库',11,1010109)
        prepared=runtime_storage.prepare(store)
        npc=next(p for ps in store.npc_resources[0].values() for p in ps if p.npc_id==10003)
        store.save_position(1111,role['id'],(npc.map_id,npc.x,npc.y))
        try:report=asyncio.run(check(store,prepared,role,npc))
        except AssertionError as error:
            write_json(OUT/'evidence/npc-depot-close-runtime-baseline.json',{
                'failure':str(error),'live_database_modified':False})
            raise
    write_json(OUT/'evidence/npc-depot-close-runtime.json',report);print(report)


if __name__=='__main__':main()
