"""Actual encrypted Peer and MapOwner control snapshot; disposable storage only."""
import asyncio
from dataclasses import FrozenInstanceError
from pathlib import Path
import struct
import tempfile
from accounts import AccountStore
from game_runtime import GameRuntime
from inspect_client import OUT,write_json
from npc_lifecycle import NpcControlSnapshot
from verify_runtime import Peer
from world_entity_protocol import VISIT_NPC,VISIT_NPC_REPLY
import runtime_storage


async def check(store,prepared,role,npc):
    runtime=GameRuntime(store,prepared)
    try:
        peer=Peer(runtime);await peer.login(role)
        key=(npc.map_id<<32)|npc.placement_id
        assert any(kind==VISIT_NPC_REPLY for kind,body in
            await peer.request(VISIT_NPC,struct.pack('>q',key)))
        control=await runtime.map(npc.map_id).mailbox.call('npc_state')
        assert type(control) is NpcControlSnapshot
        assert control.address.map_id==npc.map_id and control.generation
        assert control.revision==0 and len(control.presence)<=512
        assert any(e.entity_key==key and e.placement.npc_id==10003 for e in control.presence)
        assert control.next_entity_key>max(e.entity_key for e in control.presence)
        try:control.revision=99
        except FrozenInstanceError:pass
        else:raise AssertionError('MapOwner exposed a mutable NPC control snapshot')
        return {'passed':['actual encrypted warehouse NPC visit remains compatible',
            'actual MapOwner mailbox returns frozen current NPC control snapshot'],
            'dynamic_change_delivery_verified':False,'native_gui_verified':False,
            'live_database_modified':False}
    finally:await runtime.close()


def main():
    with tempfile.TemporaryDirectory() as temp:
        store=AccountStore(Path(temp)/'lifecycle.sqlite3')
        role=store.create_role(1111,'NPC控制快照',11,1010109)
        prepared=runtime_storage.prepare(store)
        npc=next(p for ps in store.npc_resources[0].values() for p in ps if p.npc_id==10003)
        store.save_position(1111,role['id'],(npc.map_id,npc.x,npc.y))
        try:report=asyncio.run(check(store,prepared,role,npc))
        except (ValueError,AssertionError,AttributeError) as error:
            write_json(OUT/'evidence/npc-lifecycle-runtime-baseline.json',{
                'failure':str(error),'exception':type(error).__name__,
                'seam':'actual GameRuntime MapOwner mailbox npc_state',
                'live_database_modified':False})
            raise
    write_json(OUT/'evidence/npc-lifecycle-runtime.json',report);print(report)


if __name__=='__main__':main()
