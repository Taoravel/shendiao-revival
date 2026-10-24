"""Necessary native request and same-transaction ordinary manual-level check."""
from contextlib import closing
from pathlib import Path
import tempfile
from accounts import AccountStore
from inspect_client import OUT,write_json
from item_effects import VitalState
from role_attributes import AttributeBaseline
from role_attribute_storage import initialize_attribute_baseline,read_attribute_snapshot
from role_growth import initialize_growth,read_growth
from role_growth_actions import manual_level_transaction
from role_growth_protocol import C_REQ_LEVEL_UP,decode_level_request
from native_gameplay_probe import probe
import runtime_storage


def main():
    native,raw=probe(0xd57d30,0xe411a0,0xd57dd0,{8:b'\0'*4})
    assert native==bytes(4) and decode_level_request(native)==0 and C_REQ_LEVEL_UP==0xc32cd
    for body in (b'',bytes(3),bytes(5)):
        try:decode_level_request(body)
        except ValueError:pass
        else:raise AssertionError('Malformed native level request accepted')
    with tempfile.TemporaryDirectory(prefix='manual-role-level-') as folder:
        store=AccountStore(Path(folder)/'state.sqlite3')
        role=store.create_role(1111,'手动升级',11,1010109)
        runtime_storage.prepare(store)
        epoch=store.acquire_lease(1111,role['id'])
        costs=store.growth_rules.costs
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('UPDATE roles SET level=10 WHERE id=?',(role['id'],))
            db.execute('INSERT INTO role_progress VALUES(?,?)',(role['id'],costs[10]+costs[11]+7))
            state=initialize_growth(db,1111,role['id'],epoch,store.growth_rules,expected_level=10,free_points=0)
            baseline=AttributeBaseline(role['id'],10,0,(10,10,10,10,10),(100,100,20,5,40,20,10,20,5))
            initialize_attribute_baseline(db,1111,role['id'],epoch,baseline,state,store.attribute_rules,
                VitalState(role['id'],0,70,100,40,100))
        def execute(key,field=0,lease=epoch):
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                return manual_level_transaction(db,1111,role['id'],lease,field,key,store.growth_rules,store.attribute_rules)
        first=execute('manual:first')
        assert (first.growth.level,first.growth.experience,first.growth.free_points)==(11,costs[11]+7,5)
        assert (first.attributes.vitals.hp,first.attributes.vitals.mp)==(80,46)
        assert [kind for kind,_ in first.messages]==[0xc000d,0xc32c8]
        second=execute('manual:second')
        assert (second.growth.level,second.growth.experience,second.growth.free_points)==(12,7,10)
        replay=execute('manual:first')
        assert replay.growth==second.growth and replay.attributes==second.attributes and replay.messages==second.messages
        for key,field in (('insufficient',0),('forged-target',99),('negative-mode',-1)):
            try:execute(key,field)
            except ValueError:pass
            else:raise AssertionError('Invalid or insufficient manual upgrade accepted')
        with closing(store.connect()) as db,db:
            db.execute('BEGIN')
            assert read_growth(db,1111,role['id'])==second.growth
            assert read_attribute_snapshot(db,1111,role['id'],epoch)==second.attributes
            assert db.execute('SELECT COUNT(*) FROM role_growth_receipts WHERE role_id=?',(role['id'],)).fetchone()==(2,)
        # An otherwise-valid third level and its receipt must roll back if the
        # caller's common settlement fails after obtaining the display packets.
        with closing(store.connect()) as db,db:
            db.execute('UPDATE role_progress SET experience=? WHERE role_id=?',(costs[12],role['id']))
        try:
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                before=read_growth(db,1111,role['id'])
                manual_level_transaction(db,1111,role['id'],epoch,0,'outer-failure',store.growth_rules,store.attribute_rules)
                raise RuntimeError('Caller common transaction failed')
        except RuntimeError:pass
        with closing(store.connect()) as db,db:
            db.execute('BEGIN')
            assert read_growth(db,1111,role['id'])==before
            assert not db.execute("SELECT 1 FROM role_growth_receipts WHERE request_id='outer-failure'").fetchone()
        store.acquire_lease(1111,role['id'])
        try:execute('old-epoch')
        except ValueError:pass
        else:raise AssertionError('Replaced login lease upgraded a role')
    result={'passed':['original CReqLevelUp one-BE32 zero bytes match x86 serializer/decoder',
        'ordinary level10 upgrades once per command and preserves missing HP/MP',
        'stable replay after later level returns current state and current display',
        'insufficient XP, forged target, negative mode and stale lease refuse',
        'caller failure rolls back level XP points attributes and request receipt'],
        'policy':'designed ordinary mode0; original field meaning unconfirmed',
        'runtime_connected':False,'live_server_changed':False,'battle_executed':False,'native_gui_tested':False}
    write_json(OUT/'evidence/manual-role-level-verification.json',result)
    print(result)


if __name__=='__main__':main()
