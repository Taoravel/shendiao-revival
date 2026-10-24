"""Real SQLite caller transaction around the actual map handoff receipt."""
from contextlib import closing
from dataclasses import asdict,replace
import json
import sqlite3
from pathlib import Path
import tempfile
from unittest.mock import patch
from accounts import AccountStore
from inspect_client import OUT,write_json
from world_catalog import maps
from world_owner import MapAddress,MapOwner,Location
import world_transfer_storage as storage
from world_transfer_storage import commit_transfer_transaction
import runtime_storage


class CallerDatabase:
    """Real SQLite operations, rejecting transaction ownership by the callee."""
    def __init__(self,db):self.db=db
    @property
    def in_transaction(self):return self.db.in_transaction
    def execute(self,sql,args=()):
        assert sql.lstrip().split(None,1)[0].upper() not in (
            'BEGIN','COMMIT','ROLLBACK','SAVEPOINT','RELEASE','CREATE','ALTER','DROP')
        return self.db.execute(sql,args)


def refused(action):
    try:action()
    except ValueError:return
    raise AssertionError('Stale, conflicting or malformed durable transfer accepted')


def state(store,rid):
    with closing(store.connect()) as db:
        return (db.execute('SELECT map_id,x,y FROM role_positions WHERE role_id=?',(rid,)).fetchone(),
                db.execute('SELECT version FROM position_versions WHERE role_id=?',(rid,)).fetchone()[0],
                db.execute('SELECT stage FROM world_handoffs WHERE role_id=?',(rid,)).fetchone()[0],
                db.execute('SELECT phase FROM caller_probe WHERE role_id=?',(rid,)).fetchone()[0])


def run(path):
    store=AccountStore(path)
    role=store.create_role(1111,'车夫事务',12,1010101)
    runtime_storage.prepare(store)
    rid=role['id'];epoch=store.acquire_lease(1111,rid)
    initial=(1007,8480,6976)
    assert store.save_checkpoint(1111,rid,epoch,initial,2)
    with closing(store.connect()) as db,db:
        storage.prepare(db)
        db.execute('CREATE TABLE caller_probe(role_id INTEGER PRIMARY KEY,phase TEXT NOT NULL)')
        db.execute('INSERT INTO caller_probe VALUES(?,?)',(rid,'active'))
    catalog=maps()
    source=MapOwner(MapAddress(1007,1,0),catalog,capacity=3,transfer_capacity=3,mailbox_capacity=3)
    target=MapOwner(MapAddress(1006,1,0),catalog,capacity=3,transfer_capacity=3,mailbox_capacity=3)
    loc=source.join(Location(rid,epoch,source.address,2,*initial[1:]))
    offer=source.prepare_transfer(loc,(1006,576,3536),request_id='cart-transaction-test',deadline_ms=10000,now_ms=0)
    assert storage.begin(store,1111,rid,epoch,offer)=='prepared'
    refused(lambda: storage.begin(store,1111,rid,epoch,replace(offer,deadline_ms=20000)))
    refused(lambda: storage.begin(store,9999,rid,epoch,offer))
    refused(lambda: storage.begin(store,1111,rid,epoch,replace(offer,transfer_id='foreign-source',
        source=replace(loc,role_id=rid+1))))
    reserved=target.reserve(offer,0)
    frozen=source.freeze(reserved,0)
    receipt=target.activate(frozen,0)
    def rejected(candidate=receipt,*,sql=None,args=(),account_id=1111,attempt_epoch=epoch):
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            if sql:db.execute(sql,args)
            changes=db.total_changes
            refused(lambda: commit_transfer_transaction(CallerDatabase(db),account_id,rid,attempt_epoch,candidate))
            assert db.total_changes==changes
            db.rollback()
    # Exact dataclass type alone is insufficient: bool equals the integer1.
    rejected(replace(receipt,location=replace(receipt.location,role_id=True)))
    rejected(replace(receipt,location=replace(receipt.location,x=592)))
    rejected(replace(receipt,location=replace(receipt.location,version=5)))
    rejected(replace(receipt,frozen=replace(frozen,source=replace(frozen.source,version=9))))
    rejected(replace(receipt,frozen=replace(frozen,reservation=replace(reserved,
        offer=replace(offer,deadline_ms=20000)))))
    rejected(account_id=9999)
    rejected(attempt_epoch='old-epoch')
    rejected(sql='UPDATE position_versions SET version=3 WHERE role_id=?',args=(rid,))
    rejected(sql='UPDATE position_versions SET version=1 WHERE role_id=?',args=(rid,))
    rejected(sql='UPDATE role_positions SET x=x+16 WHERE role_id=?',args=(rid,))
    rejected(sql='UPDATE role_positions SET map_id=1006 WHERE role_id=?',args=(rid,))
    rejected(sql='DELETE FROM position_versions WHERE role_id=?',args=(rid,))
    rejected(sql="UPDATE world_handoffs SET offer='' WHERE transfer_id=?",args=(offer.transfer_id,))
    with closing(store.connect()) as db:
        refused(lambda: commit_transfer_transaction(CallerDatabase(db),1111,rid,epoch,receipt))
    # A failure after both modules' SQL must roll back both changes. The probe
    # is caller-owned fixture state, not a claim of real task/reward integration.
    try:
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            with patch('sqlite3.connect',side_effect=AssertionError('Nested connection')):
                assert commit_transfer_transaction(CallerDatabase(db),1111,rid,epoch,receipt) is True
            db.execute('UPDATE caller_probe SET phase=? WHERE role_id=?',('completed',rid))
            raise RuntimeError('Injected failure after caller writes')
    except RuntimeError as error:
        assert str(error)=='Injected failure after caller writes'
    assert state(store,rid)==(initial,2,'prepared','active')
    with closing(store.connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        assert commit_transfer_transaction(CallerDatabase(db),1111,rid,epoch,receipt) is True
        db.execute('UPDATE caller_probe SET phase=? WHERE role_id=?',('completed',rid))
    assert state(store,rid)==((1006,576,3536),4,'committed','completed')
    # Identical receipt replay must not rewind a later accepted checkpoint.
    assert store.save_checkpoint(1111,rid,epoch,(1006,592,3536),5)
    with closing(store.connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        assert commit_transfer_transaction(CallerDatabase(db),1111,rid,epoch,receipt) is False
    assert state(store,rid)==((1006,592,3536),5,'committed','completed')
    # A replay cannot bless a journal/current-position contradiction.
    rejected(sql='UPDATE position_versions SET version=3 WHERE role_id=?',args=(rid,))
    rejected(sql='UPDATE position_versions SET version=4 WHERE role_id=?',args=(rid,))
    new_epoch=store.acquire_lease(1111,rid)
    assert new_epoch!=epoch
    rejected()  # Same exact committed receipt, but the real lease was replaced.
    # Startup migration can recover a full offer from an old completed receipt,
    # but must not invent the missing deadline of a legacy prepared decision.
    with closing(sqlite3.connect(':memory:')) as db,db:
        db.execute('CREATE TABLE roles(id INTEGER PRIMARY KEY)')
        db.execute('INSERT INTO roles VALUES(?)',(rid,))
        db.execute("CREATE TABLE world_handoffs(transfer_id TEXT PRIMARY KEY,role_id INTEGER,epoch TEXT,"
            "stage TEXT,source TEXT,target TEXT,receipt TEXT NOT NULL DEFAULT '')")
        for ident,stage,body in ((offer.transfer_id,'committed',json.dumps(asdict(receipt),sort_keys=True)),
                                 ('legacy-prepared','prepared','')):
            db.execute('INSERT INTO world_handoffs VALUES(?,?,?,?,?,?,?)',
                (ident,rid,str(epoch),stage,json.dumps(asdict(offer.source),sort_keys=True),json.dumps(offer.target_position),body))
        storage.prepare(db)
        migrated=dict(db.execute('SELECT transfer_id,offer FROM world_handoffs'))
        assert migrated[offer.transfer_id]==json.dumps(asdict(offer),sort_keys=True)
        assert migrated['legacy-prepared']==''
        changes=db.total_changes
        storage.prepare(db)
        assert db.total_changes==changes
    return dict(passed=['real MapOwner reserve/freeze/loading receipt joins caller transaction',
        'late caller failure rolls back target/version/decision and caller state together',
        'retry records one decision; identical replay does not rewind later position',
        'callee performs no transaction control, schema work or nested connection',
        'full offer including deadline is immutable across retries',
        'raw caller transaction checks current actual lease and account ownership',
        'older/newer/mismatched/missing source checkpoints and malformed receipts rejected before writes',
        'committed replay checks durable position consistency without rewinding later progress',
        'startup migrates exact legacy receipt offers once; unresolved prepared rows are not guessed'],
        task_reward_workflow_tested=False,shared_runtime_tested=False,
        gui_verified=False,live_server_changed=False)


def main():
    with tempfile.TemporaryDirectory() as directory:
        report=run(Path(directory)/'caller-transfer.sqlite3')
    write_json(OUT/'evidence/world-transfer-transaction-verification.json',report)
    print(report)


if __name__=='__main__':main()
