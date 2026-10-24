"""Instance identity survives durable transfer, later walking and a new lease."""
from contextlib import closing
from pathlib import Path
import tempfile
import sqlite3
import struct
from dataclasses import replace
from unittest.mock import patch
from accounts import AccountStore
import runtime_storage
import world_transfer_storage as storage
from world_owner import MapAddress,Location,MapOwner,MoveCommand
from world_catalog import maps
from inspect_client import OUT,write_json


class CallerDatabase:
    def __init__(self,db):self.db=db
    @property
    def in_transaction(self):return self.db.in_transaction
    def execute(self,sql,args=()):
        assert sql.lstrip().split(None,1)[0].upper() not in (
            'BEGIN','COMMIT','ROLLBACK','SAVEPOINT','RELEASE','CREATE','ALTER','DROP','PRAGMA')
        return self.db.execute(sql,args)


def refused(action):
    try:action()
    except ValueError:return
    raise AssertionError('Foreign or stale map-instance operation accepted')


def main():
    with tempfile.TemporaryDirectory() as temp:
        store=AccountStore(Path(temp)/'roles.sqlite3')
        role=store.create_role(1111,'实例归属',12,1010101)
        runtime_storage.prepare(store)
        rid=role['id'];epoch=store.acquire_lease(1111,rid)
        position=(1007,8480,6976)
        assert store.save_checkpoint(1111,rid,epoch,position,2)
        address=MapAddress(1007,101,3)
        source=Location(rid,epoch,address,2,*position[1:])
        try:
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                storage.bind_map_instance_transaction(CallerDatabase(db),1111,rid,epoch,source)
                raise RuntimeError('later adoption caller failure')
        except RuntimeError as error:
            assert str(error)=='later adoption caller failure'
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            assert storage.load_map_instance_transaction(db,1111,rid,epoch) is None
            changes=db.total_changes
            for wrong in (replace(source,x=source.x+1),replace(source,version=1),
                    replace(source,x=float(source.x)),replace(source,login_epoch=True)):
                refused(lambda candidate=wrong:storage.bind_map_instance_transaction(db,1111,rid,epoch,candidate))
            assert db.total_changes==changes
            adopted=storage.bind_map_instance_transaction(db,1111,rid,epoch,source)
            assert adopted.address==address and adopted.position==position and adopted.version==2
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            loaded=storage.load_map_instance_transaction(db,1111,rid,epoch)
            assert loaded==adopted
        catalog=maps()
        source_owner=MapOwner(address,catalog,capacity=1,transfer_capacity=2,mailbox_capacity=1)
        target_address=MapAddress(1006,202,7)
        target_owner=MapOwner(target_address,catalog,capacity=1,transfer_capacity=2,mailbox_capacity=1)
        source_owner.join(source)
        foreign_owner=MapOwner(replace(address,instance_id=999),catalog,
            capacity=1,transfer_capacity=1,mailbox_capacity=1)
        foreign=foreign_owner.join(replace(source,address=foreign_owner.address))
        foreign_offer=foreign_owner.prepare_transfer(foreign,(1006,576,3536),
            request_id='wrong-bound-instance',deadline_ms=10000,now_ms=0)
        refused(lambda:storage.begin(store,1111,rid,epoch,foreign_offer))
        with closing(store.connect()) as db:
            assert db.execute('SELECT COUNT(*) FROM world_handoffs WHERE transfer_id=?',
                (foreign_offer.transfer_id,)).fetchone()[0]==0
        offer=source_owner.prepare_transfer(source,(1006,576,3536),
            request_id='instanced-handoff',deadline_ms=10000,now_ms=0)
        storage.begin(store,1111,rid,epoch,offer)
        receipt=target_owner.activate(source_owner.freeze(target_owner.reserve(offer,0),0),0)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('UPDATE world_instance_positions SET instance_id=999 WHERE role_id=?',(rid,))
            changes=db.total_changes
            refused(lambda:storage.commit_transfer_transaction(db,1111,rid,epoch,receipt))
            assert db.total_changes==changes
            db.rollback()
        with closing(store.connect()) as db,db:
            db.execute("CREATE TRIGGER fail_instance_update BEFORE UPDATE ON world_instance_positions "
                "BEGIN SELECT RAISE(ABORT,'late instance update');END")
        try:
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                storage.commit_transfer_transaction(CallerDatabase(db),1111,rid,epoch,receipt)
        except sqlite3.IntegrityError as error:
            assert str(error)=='late instance update'
        else:raise AssertionError('Late instance SQL failure did not run')
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            assert storage.load_map_instance_transaction(db,1111,rid,epoch)==adopted
            assert db.execute('SELECT stage FROM world_handoffs WHERE transfer_id=?',
                (offer.transfer_id,)).fetchone()==('prepared',)
            db.execute('DROP TRIGGER fail_instance_update')
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            with patch('sqlite3.connect',side_effect=AssertionError('Nested SQLite connection')):
                assert storage.commit_transfer_transaction(CallerDatabase(db),1111,rid,epoch,receipt)
                loaded=storage.load_map_instance_transaction(CallerDatabase(db),1111,rid,epoch)
            assert loaded.address==target_address and loaded.position==(1006,576,3536)
            assert loaded.version==loaded.entry_version==4 and loaded.transfer_id==offer.transfer_id
        source_owner.finalize(receipt)
        active=target_owner.ready(receipt.location)
        walked=target_owner.move(MoveCommand(active,'walk-after-instance',1000,0xc0faa,
            b'\0'+struct.pack('>hhQ',592,3536,0)),1).location
        assert walked.version==6 and store.save_checkpoint(1111,rid,epoch,walked.position,walked.version)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            assert storage.commit_transfer_transaction(db,1111,rid,epoch,receipt) is False
            latest=storage.load_map_instance_transaction(db,1111,rid,epoch)
            assert latest.address==target_address and latest.position==(1006,592,3536)
            assert latest.version==6 and latest.entry_version==4
            refused(lambda:storage.bind_map_instance_transaction(db,1111,rid,epoch,
                replace(walked,address=replace(target_address,instance_id=999))))
            refused(lambda:storage.load_map_instance_transaction(db,9999,rid,epoch))
        # Controlled same-template portal fixture: this is NOT a housing rule
        # or a claim that the original 1594/1627 entry now resolves correctly.
        controlled=dict(catalog)
        controlled[1006]=dict(catalog[1006],portals={(38,221):(1006,624,3536)})
        target_owner.leave(walked)
        restarted=MapOwner(target_address,controlled,capacity=1,transfer_capacity=2,mailbox_capacity=1)
        restarted.join(walked)
        second_address=MapAddress(1006,303,9)
        second=MapOwner(second_address,controlled,capacity=1,transfer_capacity=2,mailbox_capacity=1)
        moved=restarted.move(MoveCommand(walked,'same-template-instance',1000,0xc0faa,
            b'\0'+struct.pack('>hhQ',608,3536,0)),2)
        assert moved.offer is not None and moved.offer.target_position==(1006,624,3536)
        assert store.save_checkpoint(1111,rid,epoch,moved.location.position,moved.location.version)
        storage.begin(store,1111,rid,epoch,moved.offer)
        second_receipt=second.activate(restarted.freeze(second.reserve(moved.offer,2),2),2)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            assert storage.commit_transfer_transaction(db,1111,rid,epoch,second_receipt)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            assert storage.commit_transfer_transaction(db,1111,rid,epoch,receipt) is False
            newest=storage.load_map_instance_transaction(db,1111,rid,epoch)
            assert newest.address==second_address and newest.position==(1006,624,3536)
            assert newest.version==newest.entry_version==9
            assert newest.transfer_id==moved.offer.transfer_id
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('UPDATE world_instance_positions SET entry_version=4 WHERE role_id=?',(rid,))
            changes=db.total_changes
            refused(lambda:storage.commit_transfer_transaction(db,1111,rid,epoch,receipt))
            assert db.total_changes==changes
            db.rollback()
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('UPDATE role_positions SET map_id=1007 WHERE role_id=?',(rid,))
            changes=db.total_changes
            refused(lambda:storage.load_map_instance_transaction(db,1111,rid,epoch))
            assert db.total_changes==changes
            db.rollback()
        new_epoch=store.acquire_lease(1111,rid)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            changes=db.total_changes
            refused(lambda:storage.load_map_instance_transaction(db,1111,rid,epoch))
            assert db.total_changes==changes
            recovered=storage.prepare_transfer_recovery_transaction(db,1111,rid,new_epoch)
            joined=storage.load_map_instance_transaction(db,1111,rid,new_epoch)
            assert joined.address==second_address and joined.login_epoch==new_epoch
            assert joined.position==recovered.authority_position and joined.version==recovered.authority_version
        report=dict(passed=['explicit trusted instance adoption and durable reload',
            'caller adoption failure rolls back to unknown; mismatched/typed locations refuse before writes',
            'late instance SQL failure rolls back position, journal and address together',
            'full target address commits in the caller transaction without nested I/O or DDL',
            'later walking and exact replay preserve current point and instance',
            'foreign account and explicit rebind refused',
            'wrong source instance cannot create a recovery journal',
            'commit rechecks source instance even after the offer was journaled',
            'same-template different-instance handoff persists full target address',
            'old receipt cannot rewind a later same-template instance',
            'corrupt instance/position or replay identity refuses instead of selecting a default instance',
            'new lease recovery retains instance while old lease is fenced'],
            shared_runtime_integrated=False,gui_verified=False,live_server_changed=False)
        write_json(OUT/'evidence/world-instance-persistence-verification.json',report)
        print(report)


if __name__=='__main__':main()
