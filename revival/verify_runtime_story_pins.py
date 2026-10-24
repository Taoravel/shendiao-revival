"""Actual SerialOwner terminal paths behind the story-map factory Seam."""
import asyncio
from dataclasses import replace
from pathlib import Path
import tempfile
import time
from accounts import AccountStore
from game_runtime import MapOwner
from inspect_client import OUT,write_json
from runtime_story_maps import RuntimeStoryMaps
from verify_runtime_private_role import fixtures
import runtime_storage


class GatedMap(MapOwner):
    """Second factory Adapter: production map behavior plus a controlled hold."""
    async def handle(self,command):
        if command.operation=='controlled_hold':
            entered,release=command.args
            entered.set();await release.wait();return 'finished'
        return await super().handle(command)


async def check(store,prepared):
    entries,_=await fixtures(store,prepared);records=[record for role,record in entries]
    clock=[1000];registry={}
    rules=store.story_instance_rules
    def create(record):
        assert record.address not in registry
        owner=GatedMap(record.address,prepared[3],store.npc_resources,
            interaction_rules=store.npc_interaction_rules,story_rules=rules)
        registry[record.address]=owner
        return owner
    def forget(address,owner):
        assert registry[address] is owner
        del registry[address]
    limited=RuntimeStoryMaps(replace(rules,loaded_capacity=1),create,forget,clock=lambda:clock[0])
    try:
        await limited.get_map(records[0],request_id='one-slot',deadline_ms=10000)
        try:await limited.get_map(records[1],request_id='cannot-load',deadline_ms=10000)
        except ValueError:pass
        else:raise AssertionError('Private runtime bypassed the process projection budget')
        assert limited.pool.loaded_count==1 and records[1].address not in registry
    finally:
        await limited.close()
        for owner in tuple(registry.values()):await owner.mailbox.close()
        registry.clear()
    manager=RuntimeStoryMaps(rules,create,forget,clock=lambda:clock[0])
    release=asyncio.Event()
    try:
        a=await manager.get_map(records[0],request_id='load-a',deadline_ms=10000)
        b=await manager.get_map(records[1],request_id='load-b',deadline_ms=10000)
        entered=asyncio.Event()
        waiter=asyncio.create_task(a.mailbox.call('controlled_hold',entered,release))
        await asyncio.wait_for(entered.wait(),1)
        waiter.cancel();await asyncio.gather(waiter,return_exceptions=True)
        clock[0]=61000
        collecting=asyncio.create_task(manager.collect())
        await b.mailbox.call('inspect_lifecycle',clock[0])
        assert not collecting.done(), 'Cancelled observer made the actual running map command terminal'
        release.set()
        assert await asyncio.wait_for(collecting,1)==(), 'Observer cancellation allowed premature idle retirement'
        entered=asyncio.Event();release=asyncio.Event()
        hold=asyncio.create_task(a.mailbox.call('controlled_hold',entered,release))
        await asyncio.wait_for(entered.wait(),1)
        expired=asyncio.create_task(a.mailbox.call('inspect_lifecycle',clock[0],deadline=time.monotonic()-1))
        await asyncio.sleep(0);expired.cancel();await asyncio.gather(expired,return_exceptions=True)
        clock[0]=121000;release.set();await hold
        retired=await manager.collect()
        assert records[0].address not in retired and records[0].address in registry
        assert a.mailbox.metrics['deadline_rejected']>=1
        clock[0]=181000
        await manager.collect()
        assert manager.pool.loaded_count==0 and not registry
    finally:
        release.set()
        await manager.close()
        for owner in tuple(registry.values()):await owner.mailbox.close()
    return dict(passed=['runtime admission enforces a smaller explicit test process budget before creating another map',
        'cancelled observer retains a running SerialOwner command; another map continues',
        'actual terminal command starts the full idle window, not the cancellation time',
        'queued deadline rejection releases its pin after actual dequeue; later idle retirement drains exact Adapters'],
        factory_adapter='real MapOwner plus explicit controlled-hold subclass',
        native_gui_verified=False,live_server_changed=False,battle_executed=False)


def main():
    with tempfile.TemporaryDirectory(prefix='story-runtime-pins-') as directory:
        store=AccountStore(Path(directory)/'state.sqlite3')
        result=asyncio.run(asyncio.wait_for(check(store,runtime_storage.prepare(store)),30))
    write_json(OUT/'evidence/runtime-story-pins-verification.json',result);print(result)


if __name__=='__main__':main()
