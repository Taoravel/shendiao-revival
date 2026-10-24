"""Real private NPC reply queue/drain/cancellation and map delivery tracking."""
import asyncio
from pathlib import Path
import struct
import tempfile
from accounts import AccountStore
from game_runtime import GameRuntime
from inspect_client import OUT,write_json
from verify_runtime import Peer
from verify_runtime_private_role import fixtures
from world_entity_protocol import VISIT_NPC
from wire import frame
import runtime_storage


async def check(store,prepared):
    entries,npc=await fixtures(store,prepared)
    runtime=GameRuntime(store,prepared)
    gate=asyncio.Event()
    try:
        role,record=entries[0]
        peer=Peer(runtime);await peer.login(role)
        target=runtime.registered_map(record.address)
        async def slow_drain():await gate.wait()
        peer.writer.drain=slow_drain
        await peer.connection.receive(peer.output.transform(frame(VISIT_NPC,
            struct.pack('>q',(1501<<32)|npc.placement_id))))
        await asyncio.sleep(0)
        snapshot=await target.mailbox.call('inspect_lifecycle',runtime.story_maps.now())
        assert snapshot.pending_scene_deliveries>0, 'Actual private NPC reply was queued without a map-owned delivery ticket'
        await peer.connection.close()
        snapshot=await target.mailbox.call('inspect_lifecycle',runtime.story_maps.now())
        assert snapshot.pending_scene_deliveries==0 and snapshot.members==0
        return dict(passed=['actual private NPC reply registers before slow writer drain',
            'connection pump cancellation releases active and queued scene tickets and private membership'],
            initial_private_checkpoint_fixture=True,native_gui_verified=False,
            live_server_changed=False,battle_executed=False)
    finally:
        gate.set();await runtime.close()


def main():
    with tempfile.TemporaryDirectory(prefix='private-scene-send-') as directory:
        store=AccountStore(Path(directory)/'state.sqlite3')
        result=asyncio.run(asyncio.wait_for(check(store,runtime_storage.prepare(store)),30))
    write_json(OUT/'evidence/private-scene-delivery-runtime-verification.json',result);print(result)


if __name__=='__main__':main()
