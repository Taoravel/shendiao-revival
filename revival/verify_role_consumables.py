"""Real role attribute storage plus atomic inventory medicine settlements."""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import sqlite3
import struct
from accounts import AccountStore
from inventory import Inventory
from item_effects import VitalState
from role_growth import load_growth_rules,prepare_growth_storage,initialize_growth
from role_attributes import load_attribute_rules,AttributeBaseline
from role_attribute_storage import (prepare_attribute_storage,initialize_attribute_baseline,
    read_attribute_snapshot,update_role_vitals)
from inspect_client import OUT,write_json
from native_gameplay_probe import probe
from native_inspect import u32
from inventory_test_support import known_cash_context


def main():
    with TemporaryDirectory() as tmp:
        store=AccountStore(Path(tmp)/'state.sqlite3')
        role=store.create_role(1111,'人物用药',12,1010101)
        epoch=store.acquire_lease(1111,role['id'])
        config=Inventory.prepare(store)
        inv=Inventory(store,1111,role['id'],config,**known_cash_context(store,1111,role['id'],epoch=epoch))
        with closing(store.connect()) as db:
            prepare_growth_storage(db);prepare_attribute_storage(db)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            growth=initialize_growth(db,1111,role['id'],epoch,load_growth_rules(),expected_level=1,free_points=0)
            baseline=AttributeBaseline(role['id'],1,0,(10,10,10,10,10),(500,1000,20,5,40,20,10,20,5))
            initialize_attribute_baseline(db,1111,role['id'],epoch,baseline,growth,load_attribute_rules(),
                VitalState(role['id'],0,1,500,1,1000))
        inv.grant_item(32000,3)
        key=inv.snapshot()['items'][0]['id']
        def vitals():
            with closing(store.connect()) as db:
                db.execute('BEGIN')
                return read_attribute_snapshot(db,1111,role['id'],epoch).vitals
        def use(request='role-item:1',item=key,owner_epoch=epoch):
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                return inv.use_role_consumable(db,item,owner_epoch,request)
        result=use()
        assert (vitals().hp,vitals().version)==(201,1)
        assert inv.snapshot()['items'][0]['quantity']==2
        assert use()==result
        assert vitals()==result.vitals
        # An old successful receipt remains an acknowledgement; it never writes
        # its old vitals back over later authoritative damage.
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            current=read_attribute_snapshot(db,1111,role['id'],epoch).vitals
            update_role_vitals(db,1111,role['id'],epoch,current,replace(current,hp=50,version=2))
        assert use()==result and vitals().hp==50
        before=inv.snapshot();prior=vitals()
        with closing(store.connect()) as db,db:
            db.executescript("CREATE TRIGGER fail_role_vitals BEFORE UPDATE ON role_attribute_snapshots BEGIN SELECT RAISE(ABORT,'vital failure'); END;")
        try:use('role-item:fail')
        except sqlite3.IntegrityError:pass
        else:raise AssertionError('Injected resource persistence failure did not run')
        assert inv.snapshot()==before and vitals()==prior
        with closing(store.connect()) as db,db:db.execute('DROP TRIGGER fail_role_vitals')
        retried=use('role-item:fail')
        assert retried.vitals.hp==250 and vitals().hp==250
        inv.grant_item(32001,quality=10)
        quality_key=next(x['id'] for x in inv.snapshot()['items'] if x['template_id']==32001)
        quality=use('role-item:quality',quality_key)
        assert quality.vitals.mp==601 and vitals().mp==601
        for request,item,old_epoch in (('role-item:1',quality_key,epoch),('stale-epoch',key,epoch+1)):
            before=inv.snapshot();prior=vitals()
            try:use(request,item,old_epoch)
            except ValueError:pass
            else:raise AssertionError('Conflicting receipt or invalid lease accepted')
            assert inv.snapshot()==before and vitals()==prior
        # Caller failures after the medicine receipt must undo everything.
        before=inv.snapshot();prior=vitals()
        try:
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                inv.use_role_consumable(db,key,epoch,'outer-failure')
                raise RuntimeError('common settlement save failed')
        except RuntimeError:pass
        assert inv.snapshot()==before and vitals()==prior
        # Full/dead role resources are read from the real store, not supplied by
        # the use request, and failed no-op uses leave no settlement behind.
        for hp in (500,0):
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                current=read_attribute_snapshot(db,1111,role['id'],epoch).vitals
                update_role_vitals(db,1111,role['id'],epoch,current,replace(current,hp=hp,version=current.version+1))
            before=inv.snapshot();prior=vitals()
            try:use(f'no-heal:{hp}')
            except ValueError:pass
            else:raise AssertionError('Full/dead role consumed ordinary medicine')
            assert inv.snapshot()==before and vitals()==prior
        old_epoch=epoch
        epoch=store.acquire_lease(1111,role['id'])
        try:use('expired-real-lease',key,old_epoch)
        except ValueError:pass
        else:raise AssertionError('Replaced role lease consumed medicine')
        assert use(owner_epoch=epoch)==result
        # No missing-baseline fallback to training values.
        missing=store.create_role(1111,'未建属性',12,1010101)
        missing_epoch=store.acquire_lease(1111,missing['id'])
        missing_inv=Inventory(store,1111,missing['id'],config)
        missing_inv.grant_item(32000)
        missing_key=missing_inv.snapshot()['items'][0]['id']
        before=missing_inv.snapshot()
        try:
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                missing_inv.use_role_consumable(db,missing_key,missing_epoch,'no-baseline')
        except ValueError:pass
        else:raise AssertionError('Training HP silently used for role medicine')
        assert missing_inv.snapshot()==before
        # A valid resource baseline with no wallet must also roll back the native
        # item operation, rather than committing a heal then failing its bag reply.
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            growth=initialize_growth(db,1111,missing['id'],missing_epoch,load_growth_rules(),expected_level=1,free_points=0)
            baseline=AttributeBaseline(missing['id'],1,0,(10,10,10,10,10),(500,1000,20,5,40,20,10,20,5))
            no_wallet_before=initialize_attribute_baseline(db,1111,missing['id'],missing_epoch,baseline,growth,
                load_attribute_rules(),VitalState(missing['id'],0,1,500,1,1000))
        no_wallet_inv=Inventory(store,1111,missing['id'],config,currency_rules=inv.currency_rules)
        try:no_wallet_inv.receive_role_consumable(struct.pack('>iiQ',missing_key,0,missing['id']),missing_epoch,'no-wallet')
        except ValueError:pass
        else:raise AssertionError('Role heal committed before discovering missing wallet authority')
        assert missing_inv.snapshot()==before
        with closing(store.connect()) as db:
            db.execute('BEGIN')
            assert read_attribute_snapshot(db,1111,missing['id'],missing_epoch)==no_wallet_before
        # The context-aware native request Adapter returns world resource and
        # carried-bag replies. Replay refreshes current wounds, not old receipts.
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            current=read_attribute_snapshot(db,1111,role['id'],epoch).vitals
            update_role_vitals(db,1111,role['id'],epoch,current,replace(current,hp=1,version=current.version+1))
        body=struct.pack('>iiQ',key,0,role['id'])
        replies=inv.receive_role_consumable(body,epoch,'native-role-item')
        assert [x[0] for x in replies]==[0xc32c8,0xc03f3] and vitals().hp==201
        probe(0xec3590,0xec36b0,0xec3730,payload=replies[0][1])
        probe(0xef6220,u32(0x2284234),u32(0x2284238),payload=replies[1][1])
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            current=read_attribute_snapshot(db,1111,role['id'],epoch).vitals
            update_role_vitals(db,1111,role['id'],epoch,current,replace(current,hp=10,version=current.version+1))
        before=inv.snapshot()
        again=inv.receive_role_consumable(body,epoch,'native-role-item')
        assert vitals().hp==10 and again[0][1]!=replies[0][1] and inv.snapshot()==before
        assert struct.unpack_from('>f',again[0][1],5)[0]==10
        for invalid in (body[:-1],struct.pack('>iiQ',key,0,missing['id']),struct.pack('>iiQ',key,1,role['id'])):
            try:inv.receive_role_consumable(invalid,epoch,'invalid-role-target')
            except ValueError:pass
            else:raise AssertionError('Invalid native role target consumed medicine')
            assert inv.snapshot()==before
        precision=store.create_role(1111,'原生精度',12,1010101)
        precision_epoch=store.acquire_lease(1111,precision['id'])
        precision_inv=Inventory(store,1111,precision['id'],config)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            growth=initialize_growth(db,1111,precision['id'],precision_epoch,load_growth_rules(),expected_level=1,free_points=0)
            baseline=AttributeBaseline(precision['id'],1,0,(10,10,10,10,10),
                (16777217,1000,20,5,40,20,10,20,5))
            initial=initialize_attribute_baseline(db,1111,precision['id'],precision_epoch,baseline,growth,
                load_attribute_rules(),VitalState(precision['id'],0,16777216,16777217,1,1000))
        precision_inv.grant_item(32000)
        before_precision=precision_inv.snapshot()
        precision_key=before_precision['items'][0]['id']
        try:precision_inv.receive_role_consumable(struct.pack('>iiQ',precision_key,0,precision['id']),precision_epoch,'float-precision')
        except ValueError:pass
        else:raise AssertionError('Inexact native resource silently rounded after consumption')
        assert precision_inv.snapshot()==before_precision
        with closing(store.connect()) as db:
            db.execute('BEGIN')
            assert read_attribute_snapshot(db,1111,precision['id'],precision_epoch)==initial
        assert Inventory(AccountStore(store.path),1111,role['id'],config).snapshot()==inv.snapshot()
        assert use(owner_epoch=epoch)==result
    report={'passed':['authoritative role resource read/write and item debit in one transaction',
        'same request replay never consumes twice','replay cannot overwrite later wounds',
        'real resource persistence abort undoes debit receipt version and vital change',
        'failed request can safely retry','persisted instance quality drives role formula',
        'payload conflict and replaced real lease rejected','outer common-settlement failure rolls back',
        'full and dead authoritative roles refuse without consumption',
        'missing baseline refuses without invented training vitals','reopen keeps assets and receipts',
        'native role use Adapter returns original-compatible world resource and bag replies',
        'replayed native request refreshes latest wounds instead of stale receipt values',
        'missing bag wallet rolls back native role heal debit and receipt',
        'inexact native float encoding rolls back before commit'],
        'native_world_resource_refresh_verified':True,'CUseItem_role_context_adapter_implemented':True,
        'shared_runtime_role_dispatch_connected':False,
        'live_characters_changed':False}
    write_json(OUT/'evidence/role-consumables-verification.json',report)
    print('PASS:',', '.join(report['passed']))


if __name__=='__main__':main()
