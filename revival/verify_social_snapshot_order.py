"""Targeted social snapshot ordering; no storage, battle, socket or native UI."""
import asyncio
from dataclasses import replace
from types import SimpleNamespace
from social_owner import RoleSnapshot
from social_runtime import SocialEndpoint,SnapshotUpdate
from runtime_core import StaleEpoch
from inspect_client import OUT,write_json


async def check():
    rt=SimpleNamespace(social_store=object(),social_limits=dict(max_contacts=100,max_text=256),log=lambda **_:None)
    router=SimpleNamespace(rt=rt,endpoints={})
    first=RoleSnapshot(1,100,'角色',1,12,1010101,1007)
    endpoint=SocialEndpoint(router,first,8)
    router.endpoints[1]=endpoint
    newest=replace(first,level=3)
    try:
        # Both are queued before the caller waits. FIFO processing must still
        # refuse a captured older revision arriving behind the newest one.
        new=asyncio.create_task(endpoint.call('snapshot',SnapshotUpdate(newest,2)))
        old=asyncio.create_task(endpoint.call('snapshot',SnapshotUpdate(replace(first,level=2),1)))
        assert await new==newest
        try:await old
        except StaleEpoch:pass
        else:raise AssertionError('Queued older revision replaced new snapshot')
        for update in (SnapshotUpdate(first,0),SnapshotUpdate(replace(newest,level=4),2),
                       SnapshotUpdate(replace(newest,login_epoch=99),3)):
            try:await endpoint.call('snapshot',update)
            except StaleEpoch:pass
            else:raise AssertionError('Old/conflicting/foreign epoch snapshot accepted')
        # Request envelopes carry a version too; an old request must not silently
        # overwrite the sender profile before executing the command.
        try:await endpoint.call('request',(SnapshotUpdate(first,0),None,0))
        except StaleEpoch:pass
        else:raise AssertionError('Stale request profile replaced committed level')
        assert endpoint.snapshot==endpoint.domain.snapshot==newest and endpoint.snapshot_revision==2
    finally:await endpoint.close()
    return {'passed':['queued older revision refused','equal-version conflicting state refused',
        'foreign epoch refused','stale request cannot replace sender profile',
        'endpoint/domain stay on same newest immutable snapshot'],
        'database_accessed':False,'battle_executed':False,'live_server_changed':False}


if __name__=='__main__':
    result=asyncio.run(check())
    write_json(OUT/'evidence/social-snapshot-order.json',result)
    print(result)
