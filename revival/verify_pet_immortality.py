"""Known template kind controls care loss in the existing owned transaction seam."""
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib
import json
import sqlite3
import struct
from accounts import AccountStore
from inventory import Inventory,pet_record
from inventory_test_support import known_cash_context
from inspect_client import OUT,write_json
from native_gameplay_probe import probe
from pet_care import PetCare


def refused(action,errors=(ValueError,)):
    try:action()
    except errors:return
    raise AssertionError('Invalid care attempt accepted')


def main():
    with TemporaryDirectory() as tmp:
        store=AccountStore(Path(tmp)/'immortality.sqlite3')
        role=store.create_role(1111,'永生宠物',12,1010101)
        config=Inventory.prepare(store)
        inv=Inventory(store,1111,role['id'],config,**known_cash_context(store,1111,role['id']))
        pet=inv.grant_pet(500069)
        before=inv.immutable_snapshot()
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            care=inv.read_pet_state(db,pet).care
            after=inv.change_pet_care(db,pet,'immortal:death',care.version,'defeat',1)
            assert after==care, '神兽死亡错误扣减忠诚/寿命或制造养护版本'
        assert inv.immutable_snapshot()==before
        rules=config.care_rules
        special=(500069,500070,500071,500072,500101,500123,500124,500125,500126)
        assert tuple(k for k in rules.template_kinds if rules.has_immortal_care(k))==special
        assert len(rules.template_kinds)==158
        for template in rules.template_kinds:
            for life in (0,1,49,50):
                assert rules.battle_care_ready(PetCare(0,1,37,life),template)==(template in special or life>=50)
            assert not rules.battle_care_ready(PetCare(0,1,0,6000),template)
        for invalid in (None,True,'500069',0,500159):
            refused(lambda:rules.has_immortal_care(invalid))
            refused(lambda:rules.battle_care_ready(PetCare(0,1,100,6000),invalid))
        refused(lambda:rules.battle_care_ready(None,500069))
        try:rules.template_kinds[500001]=2
        except TypeError:pass
        else:raise AssertionError('Startup kind snapshot mutable')
        # Actual low-care imports exercise all nine kind2 definitions, ordinary
        # misleading names, and kind3 without requiring growth initialization.
        ids={}
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            for template in special+(500030,500120,500050,500155):
                key=db.execute('INSERT INTO inventory_pets(role_id,template_id,name) VALUES(?,?,?)',
                    (role['id'],template,'原分类导入')).lastrowid
                ids[template]=key
                inv.initialize_pet_care(db,key,1,37,12)
                initial=inv.read_pet_state(db,key).care
                result=inv.change_pet_care(db,key,f'kind:{template}',0,'defeat',1)
                if template in special:assert result==initial
                else:assert (result.version,result.loyalty,result.lifetime)==(1,17,0)
        before=inv.immutable_snapshot()
        # Captured receipts are read-only, even after independent later food.
        immortal=ids[500069]
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            fed=inv.change_pet_care(db,immortal,'immortal:later-feed',0,'feed',31000)
            assert (fed.version,fed.loyalty,fed.lifetime)==(1,42,12)
        before=inv.immutable_snapshot()
        with closing(store.connect()) as db,db:
            db.execute('BEGIN')
            writes=[]
            def authorizer(op,table,*other):
                if op in (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE):
                    writes.append(table);return sqlite3.SQLITE_DENY
                return sqlite3.SQLITE_OK
            db.set_authorizer(authorizer)
            old=inv.change_pet_care(db,immortal,'kind:500069',0,'defeat',1)
            assert (old.version,old.loyalty,old.lifetime)==(0,37,12) and not writes
            assert inv.read_pet_state(db,immortal).care==fed
        assert inv.immutable_snapshot()==before
        _,decoded=probe(0xf89ba0,0xf5df70,0xf5f1f0,payload=pet_record({
            'id':immortal,'template_id':500069,'name':'','care':fed}))
        assert struct.unpack_from('<i',decoded,0x90)[0]==42
        assert struct.unpack_from('<i',decoded,0xb0)[0]==12
        # Historical format1 defeated god-pet receipts are immutable history,
        # even though their old loss is now known to have been incorrect.
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            fingerprint=hashlib.sha256(json.dumps(['defeat',1],separators=(',',':')).encode()).hexdigest()
            db.execute('INSERT INTO inventory_pet_care_receipts VALUES(?,?,?,?,?)',
                (role['id'],immortal,'legacy:death',fingerprint,
                 json.dumps({'version':5,'grade':1,'loyalty':17,'lifetime':0})))
            saved=inv.change_pet_care(db,immortal,'legacy:death',0,'defeat',1)
            assert saved==PetCare(5,1,17,0) and inv.read_pet_state(db,immortal).care==fed
        assert inv.immutable_snapshot()==before
        # A no-loss settlement still records its identity atomically; failures
        # must not leave a phantom receipt or require a different retry key.
        with closing(store.connect()) as db,db:
            db.executescript("CREATE TRIGGER fail_immortal_receipt BEFORE INSERT ON inventory_pet_care_receipts BEGIN SELECT RAISE(ABORT,'care receipt failed'); END")
        def settle(identity='immortal:abort',expected=1,operation='defeat',value=1):
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                return inv.change_pet_care(db,immortal,identity,expected,operation,value)
        refused(settle,(sqlite3.IntegrityError,))
        assert inv.immutable_snapshot()==before
        with closing(store.connect()) as db,db:db.execute('DROP TRIGGER fail_immortal_receipt')
        assert settle()==fed and settle()==fed
        for identity,expected,operation,value in (('invalid:version',0,'defeat',1),
                ('invalid:bool',True,'defeat',1),('invalid:value',1,'defeat',True),
                ('immortal:abort',1,'feed',31000)):
            refused(lambda:settle(identity,expected,operation,value))
        assert inv.immutable_snapshot()==before
        # Fresh no-op receipts must roll back with the outer role settlement.
        try:
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                inv.change_pet_care(db,immortal,'immortal:outer',1,'defeat',1)
                raise RuntimeError('outer role transaction abort')
        except RuntimeError:pass
        assert settle('immortal:outer')==fed and inv.immutable_snapshot()==before
        # Actual opaque role lease protects both fresh and paid care calls.
        token='宠物永生:0008';store.inventory_config=config
        with closing(store.connect()) as db,db:
            db.execute('UPDATE role_leases SET epoch=? WHERE role_id=?',(token,role['id']))
        old=Inventory(store.leased(1111,role['id'],inv.epoch),1111,role['id'],config,
                      epoch=inv.epoch,currency_rules=inv.currency_rules)
        active=Inventory(store.leased(1111,role['id'],token),1111,role['id'],config,
                         epoch=token,currency_rules=inv.currency_rules)
        from runtime_core import StaleEpoch
        for identity in ('immortal:abort','immortal:replacement'):
            try:
                with closing(old.accounts.connect()) as db,db:
                    db.execute('BEGIN IMMEDIATE')
                    old.change_pet_care(db,immortal,identity,1,'defeat',1)
            except StaleEpoch:pass
            else:raise AssertionError('Stale care owner admitted')
        with closing(active.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            assert active.change_pet_care(db,immortal,'immortal:replacement',1,'defeat',1)==fed
            assert active.change_pet_care(db,immortal,'kind:500069',0,'defeat',1)==PetCare(0,1,37,12)
        assert active.immutable_snapshot()==before
        assert Inventory(AccountStore(store.path),1111,role['id'],config).immutable_snapshot()==before
    report={'passed':['158 frozen original kinds and lifetime0/1/49/50 gates; unknown and bool refuse',
        'all9 kind2 low-care imports preserve37/12 without version or asset revision churn',
        'ordinary misleading names and kind3 keep ordinary17/0 loss; never name or life6000 classification',
        'paid SQL read-only history preserves later42/12 care; original decoder retains literal care integers',
        'old flat receipt remains historical without rewriting current care',
        'receipt failure and outer role abort roll back; same key retries once; version/payload conflicts refuse',
        'real opaque fenced replacement supports fresh and paid calls; stale owner rejected; reopen preserved'],
        'source':'kind2 classifier and god-pet no-loss client_verified; lifetime gate inferred; kind3 ordinary fallback designed',
        'native_gui_tested':False,'battle_executed':False,'live_server_changed':False}
    write_json(OUT/'evidence/pet-immortality-verification.json',report)
    print('PASS',', '.join(report['passed']))


if __name__=='__main__':main()
