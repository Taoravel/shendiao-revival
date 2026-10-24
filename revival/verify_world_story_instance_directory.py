"""Natural fresh origins -> caller-transaction private story identities.

Disposable DB, actual encrypted role owners; no task injection or live state.
"""
import asyncio
import hashlib
from contextlib import closing
from dataclasses import replace
from pathlib import Path
import struct
import tempfile
import sqlite3
from unittest.mock import patch

from accounts import AccountStore
from game_runtime import GameRuntime
from verify_growth_runtime import GrowthPeer
from task_newbie_chapter import read_newbie_chapter
from world_owner import MapOwner,Location,MoveCommand
from inspect_client import OUT,write_json
import runtime_storage
from world_story_instances import (load_story_instance_rules,prepare_story_instance_storage,
    StoryInstanceIntent,allocate_story_instance_transaction,load_story_instance_transaction)


def refused(action):
    try:action()
    except ValueError:return
    raise AssertionError('Foreign/stale/malformed story identity was accepted')


class CallerDatabase:
    """Expose only statements inside the caller's current transaction."""
    def __init__(self,db):self.db=db
    @property
    def in_transaction(self):return self.db.in_transaction
    def execute(self,sql,args=()):
        assert sql.lstrip().split(None,1)[0].upper() not in (
            'BEGIN','COMMIT','ROLLBACK','SAVEPOINT','RELEASE','CREATE','ALTER','DROP','PRAGMA')
        return self.db.execute(sql,args)


async def check(store,prepared):
    files=('world_story_instances.py','verify_world_story_instance_directory.py',
        'design/story-instance-v1.json','design/newbie-bloodmark-v1.json')
    source_hashes={name:hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in files}
    rules=load_story_instance_rules(prepared[0],store.newbie_rules)
    with closing(store.connect()) as db,db:
        prepare_story_instance_storage(db)
        db.execute('CREATE TABLE caller_terminal(value INTEGER CHECK(value=1))')
    runtime=GameRuntime(store,prepared)
    try:
        role=store.create_role(1111,'梦境目录甲',11,1010109)
        peer=GrowthPeer(runtime);await peer.login(role)
        owner=runtime.roles[role['id']]
        await peer.request(0xc0018,struct.pack('>i',11001))
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            chapter=read_newbie_chapter(db,1111,owner.id,owner.epoch,store.newbie_rules)
            assert chapter.phase=='completed'
            origin=chapter.origin
            intent=StoryInstanceIntent(origin.chapter_id,origin.creation_id,origin.policy,
                origin.route_fingerprint,100106)
            assert load_story_instance_transaction(db,1111,owner.id,owner.epoch,intent,rules) is None
            allocated=allocate_story_instance_transaction(db,1111,owner.id,owner.epoch,intent,rules)
            assert allocated.address.map_id==1501 and allocated.address.partition_id==0
            assert 4611686018427387904<=allocated.address.instance_id<9223372036854775808
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            assert load_story_instance_transaction(db,1111,owner.id,owner.epoch,intent,rules)==allocated
            assert allocate_story_instance_transaction(db,1111,owner.id,owner.epoch,intent,rules)==allocated
            assert load_story_instance_transaction(db,1111,owner.id,owner.epoch,intent,rules,
                expected_address=allocated.address)==allocated
            refused(lambda:load_story_instance_transaction(db,1111,owner.id,owner.epoch,intent,rules,
                expected_address=replace(allocated.address,partition_id=False)))
        second_role=store.create_role(1111,'梦境目录乙',11,1010109)
        second_peer=GrowthPeer(runtime);await second_peer.login(second_role)
        second=runtime.roles[second_role['id']]
        await second_peer.request(0xc0018,struct.pack('>i',11001))
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            origin2=read_newbie_chapter(db,1111,second.id,second.epoch,store.newbie_rules).origin
            intent2=StoryInstanceIntent(origin2.chapter_id,origin2.creation_id,origin2.policy,
                origin2.route_fingerprint,100106)
            bits=iter([allocated.address.instance_id-4611686018427387904,7])
            second_allocation=allocate_story_instance_transaction(db,1111,second.id,second.epoch,
                intent2,rules,random_bits=lambda count:next(bits))
            assert second_allocation.address.instance_id==4611686018427387911
            assert second_allocation.address!=allocated.address
            assert load_story_instance_transaction(db,1111,owner.id,owner.epoch,intent,rules)==allocated
            for wrong in (replace(intent,chapter_id='foreign-chapter'),replace(intent,creation_id='foreign-create'),
                    replace(intent,origin_policy='foreign-policy'),replace(intent,route_fingerprint='foreign-route'),
                    replace(intent,source_task_id=100206),replace(intent,source_task_id=True)):
                refused(lambda candidate=wrong:allocate_story_instance_transaction(db,1111,owner.id,owner.epoch,candidate,rules))
            refused(lambda:load_story_instance_transaction(db,9999,owner.id,owner.epoch,intent,rules))
            refused(lambda:load_story_instance_transaction(db,1111,second.id,second.epoch,intent,rules))
            refused(lambda:load_story_instance_transaction(db,1111,owner.id,True,intent,rules))
            refused(lambda:load_story_instance_transaction(db,1111,owner.id,owner.epoch,intent,rules,
                expected_address=second_allocation.address))
        # Controlled domain admissions: real catalog and owners, not a claim
        # that the unfinished bloodmark task/shared router admitted these roles.
        catalog=prepared[3]
        first_map=MapOwner(allocated.address,catalog,capacity=1,transfer_capacity=1,mailbox_capacity=1)
        second_map=MapOwner(second_allocation.address,catalog,capacity=1,transfer_capacity=1,mailbox_capacity=1)
        first_location=first_map.join(Location(owner.id,owner.epoch,allocated.address,1,1008,1264))
        second_location=second_map.join(Location(second.id,second.epoch,second_allocation.address,1,1008,1264))
        moved=first_map.move(MoveCommand(first_location,'private-isolation-move',1000,0xc0faa,
            b'\0'+struct.pack('>hhQ',1009,1264,1501)),1)
        assert moved.location.position==(1501,1009,1264)
        assert second_map.location(second.id)==second_location
        third_role=store.create_role(1111,'梦境目录丙',11,1010109)
        third_peer=GrowthPeer(runtime);await third_peer.login(third_role)
        third=runtime.roles[third_role['id']]
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            origin3=read_newbie_chapter(db,1111,third.id,third.epoch,store.newbie_rules).origin
            intent3=StoryInstanceIntent(origin3.chapter_id,origin3.creation_id,origin3.policy,
                origin3.route_fingerprint,100106)
            refused(lambda:allocate_story_instance_transaction(db,1111,third.id,third.epoch,intent3,rules))
        await third_peer.request(0xc0018,struct.pack('>i',11001))
        collisions=[]
        def exhausted(count):
            assert count==62
            collisions.append(count)
            return allocated.address.instance_id-4611686018427387904
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            refused(lambda:allocate_story_instance_transaction(db,1111,third.id,third.epoch,
                intent3,rules,random_bits=exhausted))
            assert len(collisions)==8
            assert load_story_instance_transaction(db,1111,third.id,third.epoch,intent3,rules) is None
            for invalid in (-1,2**62,True,1.5):
                refused(lambda value=invalid:allocate_story_instance_transaction(db,1111,third.id,third.epoch,
                    intent3,rules,random_bits=lambda count:value))
        try:
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                with (patch('sqlite3.connect',side_effect=AssertionError('Nested connection')),
                        patch('builtins.open',side_effect=AssertionError('Hot-path file read')),
                        patch('pathlib.Path.open',side_effect=AssertionError('Hot-path Path read'))):
                    provisional=allocate_story_instance_transaction(CallerDatabase(db),1111,third.id,third.epoch,
                        intent3,rules,random_bits=lambda count:99)
                    assert load_story_instance_transaction(CallerDatabase(db),1111,third.id,third.epoch,
                        intent3,rules)==provisional
                    db.execute('INSERT INTO caller_terminal VALUES(2)')
        except sqlite3.IntegrityError:pass
        else:raise AssertionError('Late caller SQL failure did not happen')
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            assert load_story_instance_transaction(db,1111,third.id,third.epoch,intent3,rules) is None
            refused(lambda:load_story_instance_transaction(db,1111,third.id,third.epoch,intent3,rules,
                expected_address=provisional.address))
        # Corrupt identity is a test-only DB fault, rolled back immediately.
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            db.execute("UPDATE world_story_instances SET source_task_id=100206 WHERE role_id=?",(owner.id,))
            refused(lambda:allocate_story_instance_transaction(db,1111,owner.id,owner.epoch,intent,rules))
            refused(lambda:load_story_instance_transaction(db,1111,owner.id,owner.epoch,intent,rules))
            db.rollback()
        with closing(store.connect()) as db:
            refused(lambda:load_story_instance_transaction(db,1111,owner.id,owner.epoch,intent,rules))
        await peer.connection.close()
        peer=GrowthPeer(runtime);await peer.login(role)
        renewed=runtime.roles[role['id']]
        assert renewed.epoch!=owner.epoch
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            refused(lambda:load_story_instance_transaction(db,1111,owner.id,owner.epoch,intent,rules))
            assert load_story_instance_transaction(db,1111,renewed.id,renewed.epoch,intent,rules,
                expected_address=allocated.address)==allocated
            assert allocate_story_instance_transaction(db,1111,renewed.id,renewed.epoch,intent,rules,
                random_bits=lambda count:(_ for _ in ()).throw(AssertionError('Replay reallocated')))==allocated
        await peer.connection.close()
        await second_peer.connection.close()
        await third_peer.connection.close()
        assert source_hashes=={name:hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in files}
        return dict(passed=['fresh completed origin allocates and durably reloads one stable private identity',
            'actual database ID collision retries and separates two natural role origins',
            'exact typed full address, original source task and frozen creation intent are fenced',
            'foreign account, role and malformed lease cannot read or allocate',
            'two allocated private MapOwners isolate controlled domain movement',
            'pending natural intro cannot allocate a story directory',
            'eight actual unique collisions exhaust locally without allocation',
            'malformed entropy refuses without a directory write',
            'late caller SQL error rolls allocation back and missing expected identity refuses',
            'caller hot path needs no nested connection, transaction control, DDL or file reads',
            'conflicting persistent identity refuses instead of replacing',
            'no caller transaction refuses and a new natural lease reloads the original identity'],
            natural_roles=3,route_count=len(rules.source_tasks),policy=rules.revision,
            source_sha256=source_hashes,
            domain_entry_scope='controlled independent MapOwner admissions, not natural bloodmark task/transfer',
            shared_runtime_integrated=False,live_server_changed=False,gui_verified=False)
    finally:await runtime.close()


def main():
    with tempfile.TemporaryDirectory(prefix='world-story-directory-') as folder:
        store=AccountStore(Path(folder)/'roles.sqlite3')
        prepared=runtime_storage.prepare(store)
        result=asyncio.run(asyncio.wait_for(check(store,prepared),60))
    write_json(OUT/'evidence/world-story-instance-directory-verification.json',result)
    print(result)


if __name__=='__main__':main()
