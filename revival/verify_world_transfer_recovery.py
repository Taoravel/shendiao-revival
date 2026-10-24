"""Retire fenced map handoffs using the final durable decision and a new lease."""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
import tempfile
from accounts import AccountStore
from inspect_client import OUT,write_json
from world_owner import MapAddress,MapOwner,Location,MoveCommand
import struct
from world_catalog import maps
import world_transfer_storage as storage
import runtime_storage


def refused(action):
    try:action()
    except ValueError:return
    raise AssertionError('Foreign or stale map recovery accepted')


def check(path,committed):
    store=AccountStore(path);role=store.create_role(1111,'恢复分支',12,1010101)
    runtime_storage.prepare(store)
    rid=role['id'];old_epoch=store.acquire_lease(1111,rid)
    source_pos=(1007,8480,6976)
    store.save_checkpoint(1111,rid,old_epoch,source_pos,2)
    catalog=maps()
    source=MapOwner(MapAddress(1007,1,0),catalog,capacity=1,transfer_capacity=1,mailbox_capacity=1)
    target=MapOwner(MapAddress(1006,2,1),catalog,capacity=1,transfer_capacity=1,mailbox_capacity=1)
    loc=source.join(Location(rid,old_epoch,source.address,2,*source_pos[1:]))
    offer=source.prepare_transfer(loc,(1006,576,3536),request_id='recover-transfer',deadline_ms=10000,now_ms=0)
    storage.begin(store,1111,rid,old_epoch,offer)
    reservation=target.reserve(offer,0)
    frozen=source.freeze(reservation,0)
    receipt=target.activate(frozen,0)
    if committed:storage.commit(store,1111,rid,old_epoch,receipt)
    new_epoch=store.acquire_lease(1111,rid)  # Fence old I/O before reading outcome.
    with closing(store.connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        decision=storage.prepare_transfer_recovery_transaction(db,1111,rid,new_epoch,offer.transfer_id)
        refused(lambda: storage.prepare_transfer_recovery_transaction(db,1111,rid,old_epoch,offer.transfer_id))
        refused(lambda: storage.prepare_transfer_recovery_transaction(db,9999,rid,new_epoch,offer.transfer_id))
        assert storage.prepare_transfer_recovery_transaction(db,1111,rid,new_epoch)==decision
    assert decision.committed is committed
    assert decision.authority_position==(receipt.location.position if committed else source_pos)
    expected_source=source.inspect_transfer(rid,offer.transfer_id)
    expected_target=target.inspect_transfer(rid,offer.transfer_id)
    refused(lambda: source.retire_recovered_transfer(expected_source,replace(decision,transfer_id='other')))
    refused(lambda: source.retire_recovered_transfer(expected_source,replace(decision,new_epoch=old_epoch)))
    recreated=MapOwner(source.address,catalog,capacity=1,transfer_capacity=1,mailbox_capacity=1)
    recreated.join(loc)
    refused(lambda: recreated.retire_recovered_transfer(expected_source,decision))
    assert recreated.location(rid)==loc
    assert source.location(rid)==frozen.source and target.location(rid)==receipt.location
    a=source.retire_recovered_transfer(expected_source,decision)
    b=target.retire_recovered_transfer(expected_target,decision)
    assert a.target_address==target.address and b.target_address==target.address
    assert source.location(rid) is None and target.location(rid) is None
    for owner in (source,target):
        snapshot=owner.inspect_transfer(rid,offer.transfer_id)
        assert all(x is None for x in (snapshot.location,snapshot.offer,snapshot.incoming,snapshot.departure))
    # Retries do not require retaining old objects in live membership maps.
    source.retire_recovered_transfer(expected_source,decision)
    target.retire_recovered_transfer(expected_target,decision)
    owner=target if committed else source
    chosen=decision.authority_position
    joined=owner.join(Location(rid,new_epoch,owner.address,decision.authority_version,*chosen[1:]))
    refused(lambda: owner.retire_recovered_transfer(expected_target if committed else expected_source,decision))
    assert owner.location(rid)==joined
    # Cleared source offers/receipts and target loading receipts release the
    # original slots, so another transfer works in the SAME map owners.
    if not committed:
        fresh=source.prepare_transfer(joined,receipt.location.position,request_id='fresh-after-recovery',deadline_ms=20000,now_ms=1)
        res=target.reserve(fresh,1);freeze=source.freeze(res,1);target.activate(freeze,1)
    with closing(store.connect()) as db:
        stage=db.execute('SELECT stage FROM world_handoffs WHERE transfer_id=?',(offer.transfer_id,)).fetchone()[0]
    assert stage==('committed' if committed else 'cancelled')
    return dict(committed=committed,authority=chosen,source_retired=True,target_retired=True,
                fresh_same_runtime_transfer=not committed,new_epoch_preserved=True)


def cancelled_progress(path):
    store=AccountStore(path);role=store.create_role(1111,'取消后行走',12,1010101)
    runtime_storage.prepare(store)
    rid=role['id'];epoch=store.acquire_lease(1111,rid)
    pos=(1007,8480,6976);store.save_checkpoint(1111,rid,epoch,pos,2)
    catalog=maps()
    source=MapOwner(MapAddress(1007,1,0),catalog,capacity=3,transfer_capacity=3,mailbox_capacity=3)
    target=MapOwner(MapAddress(1006,2,1),catalog,capacity=3,transfer_capacity=3,mailbox_capacity=3)
    loc=source.join(Location(rid,epoch,source.address,2,*pos[1:]))
    offer=source.prepare_transfer(loc,(1006,576,3536),request_id='cancel-then-walk',deadline_ms=10000,now_ms=0)
    storage.begin(store,1111,rid,epoch,offer)
    reservation=target.reserve(offer,0);source.freeze(reservation,0)
    cancellation=target.cancel(reservation);storage.cancel(store,1111,rid,epoch,offer.transfer_id)
    resumed=source.resume(cancellation)
    body=b'\0'+struct.pack('>hhQ',8496,6976,0)
    walked=source.move(MoveCommand(resumed,'post-cancel-walk',10000,0xc0faa,body),1)
    assert not walked.rejection
    store.save_checkpoint(1111,rid,epoch,walked.location.position,walked.location.version)
    new_epoch=store.acquire_lease(1111,rid)
    with closing(store.connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        decision=storage.prepare_transfer_recovery_transaction(db,1111,rid,new_epoch,offer.transfer_id)
    assert not decision.committed and decision.authority_position==walked.location.position
    source.retire_recovered_transfer(source.inspect_transfer(rid,offer.transfer_id),decision)
    target.retire_recovered_transfer(target.inspect_transfer(rid,offer.transfer_id),decision)
    joined=source.join(replace(walked.location,login_epoch=new_epoch))
    assert joined.position==walked.location.position
    return dict(cancelled_then_walked=True,authority=joined.position,version=joined.version)


def main():
    with tempfile.TemporaryDirectory() as directory:
        cases=[check(Path(directory)/f'{flag}.sqlite3',flag) for flag in (False,True)]
        cases.append(cancelled_progress(Path(directory)/'cancelled-progress.sqlite3'))
    report=dict(cases=cases,scope='actual map owners and durable decisions; shared login orchestration pending',
                gui_verified=False,live_server_changed=False)
    write_json(OUT/'evidence/world-transfer-recovery-verification.json',report)
    print(report)


if __name__=='__main__':main()
