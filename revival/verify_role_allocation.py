"""Owned potential debit, asymmetric native field order and durable replay."""
from contextlib import closing
from pathlib import Path
import struct
import tempfile
from accounts import AccountStore
from inspect_client import OUT,write_json
from item_effects import VitalState
from progression import credit_experience
from role_attributes import AttributeBaseline
from role_attribute_storage import initialize_attribute_baseline,read_attribute_snapshot
from role_growth import initialize_growth,read_growth
from role_growth_actions import allocation_transaction
from role_growth_protocol import decode_allocation_request
import runtime_storage


def main():
    with tempfile.TemporaryDirectory(prefix='role-allocation-') as folder:
        store=AccountStore(Path(folder)/'state.sqlite3')
        role=store.create_role(1111,'人物加点',11,1010109)
        runtime_storage.prepare(store)
        epoch=store.acquire_lease(1111,role['id'])
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            growth=initialize_growth(db,1111,role['id'],epoch,store.growth_rules,expected_level=1,free_points=0)
            initialize_attribute_baseline(db,1111,role['id'],epoch,
                AttributeBaseline(role['id'],1,0,(10,10,10,10,10),(100,100,20,5,40,20,10,20,5)),
                growth,store.attribute_rules,VitalState(role['id'],0,70,100,40,100))
            credit_experience(db,1111,role['id'],150,store.growth_rules,store.attribute_rules,epoch)
        native=struct.pack('>5i',0,0,0,1,2)  # native AGI1, END2
        deltas=decode_allocation_request(native)
        assert deltas==(0,0,0,2,1)
        def apply(key,amounts=deltas,lease=epoch):
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                return allocation_transaction(db,1111,role['id'],lease,amounts,key,store.growth_rules,store.attribute_rules)
        first=apply('allocate:first')
        assert first.growth.free_points==2
        a=first.attributes.attributes
        assert a.five_stats==(11,11,11,13,12)
        assert (a.physical_defense,a.dodge,a.speed)==(14,24,11)
        assert (first.attributes.vitals.hp,first.attributes.vitals.mp)==(80,46)
        assert apply('allocate:first')==first
        second=apply('allocate:strength',(0,0,1,0,0))
        assert (second.growth.free_points,second.attributes.attributes.physical_attack)==(1,26)
        replay=apply('allocate:first')
        assert replay.growth==second.growth and replay.attributes==second.attributes and replay.messages==second.messages
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            credit_experience(db,1111,role['id'],195,store.growth_rules,store.attribute_rules,epoch)
        current=apply('allocate:first')
        assert (current.growth.level,current.growth.free_points,current.growth.experience)==(3,6,61)
        assert current.attributes.attributes.five_stats==(12,12,13,14,13)
        for key,values in (('allocate:first',(0,0,0,1,2)),('overspend',(99,0,0,0,0)),
                           ('noop',(0,0,0,0,0)),('negative',(0,0,-1,0,0)),('bool',(True,0,0,0,0))):
            try:apply(key,values)
            except ValueError:pass
            else:raise AssertionError('Invalid allocation or receipt conflict accepted')
        try:
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                allocation_transaction(db,1111,role['id'],epoch,(1,0,0,0,0),'outer-failure',store.growth_rules,store.attribute_rules)
                raise RuntimeError('Caller common settlement failed')
        except RuntimeError:pass
        with closing(store.connect()) as db,db:
            db.execute('BEGIN')
            assert read_growth(db,1111,role['id'])==current.growth
            assert read_attribute_snapshot(db,1111,role['id'],epoch)==current.attributes
            assert db.execute('SELECT COUNT(*) FROM role_growth_receipts WHERE role_id=?',(role['id'],)).fetchone()==(2,)
        store.acquire_lease(1111,role['id'])
        try:apply('expired')
        except ValueError:pass
        else:raise AssertionError('Expired epoch allocated potential')
    result={'passed':['native AGI1/END2 becomes internal END2/AGI1',
        'five points are debited by three; defense/dodge/speed reflect correct dimensions',
        'same trusted request never debits again after another allocation or level gain',
        'replay refreshes current level/stats/points instead of historical receipt',
        'overspend/no-op/negative/bool/conflicting payload and old lease refuse',
        'outer failure rolls back points attributes and receipt together'],
        'runtime_connected':False,'live_server_changed':False,'battle_executed':False,'native_gui_tested':False}
    write_json(OUT/'evidence/role-allocation-verification.json',result)
    print(result)


if __name__=='__main__':main()
