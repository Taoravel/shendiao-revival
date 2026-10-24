"""Known origin/insight persist without guessing existing unknown pet values."""
from pathlib import Path
from tempfile import TemporaryDirectory
from contextlib import closing
import sqlite3
import struct
from unittest.mock import patch
from accounts import AccountStore
from inventory import Inventory,pet_record,USE_ITEM,REFRESH_PET,AssetChange
from inventory_test_support import known_cash_context
from research_pet_traits import native_traits
from inspect_client import OUT,write_json


def refused(action,errors=(ValueError,)):
    try:action()
    except errors:return
    raise AssertionError('Unknown, foreign or already-known traits accepted')


def main():
    with TemporaryDirectory() as tmp:
        store=AccountStore(Path(tmp)/'traits.sqlite3')
        role=store.create_role(1111,'还童身份',12,1010101)
        config=Inventory.prepare(store)
        inv=Inventory(store,1111,role['id'],config,**known_cash_context(store,1111,role['id']))
        key=inv.grant_pet(500001)
        pet=inv.snapshot()['pets'][0]
        value=native_traits(pet_record(pet))
        assert (value['origin'],value['insight'])==(2,0),'新宝宝使用未确认的默认身份0'
        assert inv.immutable_snapshot().pets[0].traits.baby
        # Old constructor defaults do not become authoritative traits on load.
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            legacy=db.execute('INSERT INTO inventory_pets(role_id,template_id,name) VALUES(?,?,?)',
                (role['id'],500001,'旧身份未知')).lastrowid
        before=inv.immutable_snapshot()
        assert next(p for p in before.pets if p.id==legacy).traits is None
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            with (patch.object(Path,'read_text',side_effect=AssertionError('hot file read')),
                  patch.object(store,'connect',side_effect=AssertionError('nested connection'))):
                imported=inv.initialize_pet_traits(db,legacy,1,73)
                current=inv.read_pet_state(db,legacy)
                assert current.traits==imported and not current.traits.baby
                assert current.care is None and current.progress is None
                record=pet_record(current.__dict__)
        assert (native_traits(record)['origin'],native_traits(record)['insight'])==(1,73)
        # Invalid complete imports cannot replace either a known new or old pet.
        before=inv.immutable_snapshot()
        for target,origin,insight in ((key,1,99),(legacy,2,0),(legacy,True,0),
                (legacy,2,True),(legacy,0,73),(legacy,3,73),(legacy,2,-1),(legacy,2,2**31)):
            try:
                with closing(store.connect()) as db,db:
                    db.execute('BEGIN IMMEDIATE');inv.initialize_pet_traits(db,target,origin,insight)
            except ValueError:pass
            else:raise AssertionError('Known/invalid traits overwritten')
            assert inv.immutable_snapshot()==before
        # A real grant failure after traits are already inserted rolls the
        # whole pet and all subrecords back; the same grant then succeeds.
        command=AssetChange('traits:grant-abort',pets=(500001,))
        with closing(store.connect()) as db,db:
            db.executescript("CREATE TRIGGER fail_after_traits BEFORE INSERT ON inventory_pet_flags BEGIN SELECT RAISE(ABORT,'late pet grant failure'); END")
        def grant():
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE');return inv.apply_settlement(db,command)
        refused(grant,(sqlite3.IntegrityError,))
        assert inv.immutable_snapshot()==before
        with closing(store.connect()) as db,db:db.execute('DROP TRIGGER fail_after_traits')
        granted=grant();after=inv.immutable_snapshot()
        assert grant()==granted and inv.immutable_snapshot()==after
        new=next(p for p in after.pets if p.id==granted.created_pet_ids[0])
        assert (new.traits.origin,new.traits.insight)==(2,0)
        # Ordinary native updates retain the independent origin/insight fields.
        inv.grant_item(31000)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            inv.change_pet_care(db,key,'traits:care-loss',0,'defeat',1)
        item=next(i.id for i in inv.immutable_snapshot().items if i.template_id==31000)
        replies=inv.receive(USE_ITEM,struct.pack('>iiQ',item,1,key))
        payload=next(body for kind,body in replies if kind==REFRESH_PET)
        # native_traits accepts the Pet bean, so take the current public state;
        # the refresh decoder independently confirms the exact known values.
        from native_gameplay_probe import probe
        _,raw=probe(0xf9d7b0,0xf9d840,0xf9d880,payload=payload)
        assert struct.unpack_from('<i',raw,8+0x38)[0]==0 and struct.unpack_from('<i',raw,8+0xb4)[0]==2
        current=next(p for p in inv.immutable_snapshot().pets if p.id==key)
        assert (current.traits.origin,current.traits.insight,current.care.loyalty)==(2,0,85)
        inv.grant_item(31000)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');inv.initialize_pet_growth(db,legacy)
            inv.initialize_pet_care(db,legacy,1,80,6000)
        item=next(i.id for i in inv.immutable_snapshot().items if i.template_id==31000)
        replies=inv.receive(USE_ITEM,struct.pack('>iiQ',item,1,legacy))
        _,raw=probe(0xf9d7b0,0xf9d840,0xf9d880,payload=next(b for k,b in replies if k==REFRESH_PET))
        assert struct.unpack_from('<i',raw,8+0x38)[0]==73 and struct.unpack_from('<i',raw,8+0xb4)[0]==1
        # Unknown old instances remain unknown when an outer transaction aborts.
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            pending=db.execute('INSERT INTO inventory_pets(role_id,template_id,name) VALUES(?,?,?)',
                (role['id'],500001,'导入回滚')).lastrowid
        before=inv.immutable_snapshot()
        try:
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE');inv.initialize_pet_traits(db,pending,2,999)
                raise RuntimeError('later common transaction failure')
        except RuntimeError:pass
        assert inv.immutable_snapshot()==before
        foreign_role=store.create_role(1111,'其他身份',12,1010101)
        other=Inventory(store,1111,foreign_role['id'],config)
        foreign=other.grant_pet(500001)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            refused(lambda:inv.initialize_pet_traits(db,foreign,1,73))
            refused(lambda:inv.initialize_pet_traits(db,True,1,73))
        # Opaque fenced import succeeds; obsolete owner and all reads remain
        # side-effect free. No old-row automatic migration was introduced.
        token='宠物身份:00010';store.inventory_config=config;old_epoch=inv.epoch
        with closing(store.connect()) as db,db:db.execute('UPDATE role_leases SET epoch=? WHERE role_id=?',(token,role['id']))
        active=Inventory(store.leased(1111,role['id'],token),1111,role['id'],config,
                         epoch=token,currency_rules=inv.currency_rules)
        with closing(active.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');active.initialize_pet_traits(db,pending,2,999)
        from runtime_core import StaleEpoch
        try:
            with closing(store.leased(1111,role['id'],old_epoch).connect()) as db,db:
                db.execute('BEGIN IMMEDIATE');inv.initialize_pet_traits(db,pending,2,999)
        except StaleEpoch:pass
        else:raise AssertionError('Stale traits import admitted')
        before=active.immutable_snapshot()
        assert Inventory(AccountStore(store.path),1111,role['id'],config).immutable_snapshot()==before
    report={'passed':['new grants explicitly persist baby2/insight0 and original return UI consumer receives them',
        'known old wild1/insight73 imports once in same transaction, no hot read/nested connection; unknown care/growth stay unknown',
        'bool/range/unknown-origin/foreign/already-known initialization refuses without mutation',
        'late full grant failure rolls pet/traits/subrecords/reward receipt back; same grant retries once',
        'actual ordinary food native refresh preserves baby2/insight0 and imported wild1/insight73 while loyalty changes',
        'outer import failure preserves unknown old traits; opaque fenced import and reopen retain known state, stale owner rejected'],
        'source_status':'layout/consumers client_verified; new baby2/insight0 baseline designed; original RNG/range unknown',
        'live_server_changed':False,'native_gui_verified':False,'rebirth_completed':False}
    write_json(OUT/'evidence/pet-traits-verification.json',report)
    print('PASS',', '.join(report['passed']))


if __name__=='__main__':main()
