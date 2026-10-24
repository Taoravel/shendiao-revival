"""Actual private-owner capacity/idle/cold reload; explicit checkpoint fixture."""
import asyncio
from pathlib import Path
import tempfile
from accounts import AccountStore
from game_runtime import GameRuntime,Position
from inspect_client import OUT,write_json
from verify_runtime import Peer
from verify_runtime_private_role import fixtures
import runtime_storage


async def check(store,prepared):
    entries,_=await fixtures(store,prepared)
    clock=[1000]
    # The clock is an explicit server Adapter, never a client timestamp.
    runtime=GameRuntime(store,prepared,story_clock=lambda:clock[0])
    try:
        try:runtime.map(entries[0][1].address)
        except ValueError:pass
        else:raise AssertionError('Private address alone bypassed the validated projection loading budget')
        peers=[]
        for role,record in entries:
            peer=Peer(runtime);await peer.login(role);peers.append(peer)
        role,record=entries[0];other=entries[1][0]
        owner=runtime.roles[role['id']];map_owner=runtime.registered_map(record.address)
        try:
            await map_owner.mailbox.call('join',Position(other['id'],runtime.roles[other['id']].epoch,
                owner.position.value,owner.position.version,owner.position.arrival))
        except ValueError:pass
        else:raise AssertionError('Private runtime owner admitted a second member beyond its published capacity1')
        original=await map_owner.mailbox.call('inspect_lifecycle',clock[0])
        assert original.enabled and original.members==1
        assert await runtime.story_maps.collect()==()
        await peers[0].connection.close()
        assert await runtime.story_maps.collect()==()
        clock[0]=60999
        assert await runtime.story_maps.collect()==()
        clock[0]=61000
        assert await runtime.story_maps.collect()==(record.address,)
        assert runtime.registered_map(record.address) is None
        assert runtime.registered_map(entries[1][1].address) is not None
        try:await map_owner.mailbox.call('location',role['id'],owner.epoch)
        except ValueError:pass
        else:raise AssertionError('Retired map Adapter still accepted an old member call')
        replacement=Peer(runtime);await replacement.login(role)
        rebuilt=runtime.registered_map(record.address)
        current=await rebuilt.mailbox.call('inspect_lifecycle',clock[0])
        assert current.address==original.address and current.owner_generation!=original.owner_generation
        assert current.members==1 and runtime.roles[role['id']].map_address==record.address
        return dict(passed=['actual private runtime map rejects a second member',
            'busy map cannot retire; all-empty map remains until published60000ms boundary',
            'retirement removes only its projection; other private map remains live',
            'old Adapter rejects after retirement; real login cold-rebuilds original persistent address and new map generation'],
            initial_private_checkpoint_fixture=True,native_gui_verified=False,
            battle_executed=False,live_server_changed=False)
    finally:await runtime.close()


def main():
    with tempfile.TemporaryDirectory(prefix='runtime-story-life-') as directory:
        store=AccountStore(Path(directory)/'state.sqlite3')
        result=asyncio.run(check(store,runtime_storage.prepare(store)))
    write_json(OUT/'evidence/runtime-story-lifecycle-verification.json',result);print(result)


if __name__=='__main__':main()
