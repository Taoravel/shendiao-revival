"""Real owned wear commands obey the original equipment eligibility facts."""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from types import MappingProxyType
from unittest.mock import patch
import struct

from accounts import AccountStore
from inventory import Inventory
from inventory_test_support import known_cash_context
from inspect_client import OUT,write_json
from native_gameplay_probe import probe
from native_inspect import u32


def refused(action,reason):
    try:action()
    except ValueError as error:
        assert reason in str(error),str(error)
        return
    raise AssertionError('Ineligible equipment wear accepted: '+reason)


def main():
    with TemporaryDirectory() as tmp:
        store=AccountStore(Path(tmp)/'eligibility.sqlite3')
        role=store.create_role(1111,'原形象十',min(store.choices[1010110]),1010110)
        config=Inventory.prepare(store)
        inv=Inventory(store,1111,role['id'],config,**known_cash_context(store,1111,role['id']))
        inv.grant_item(42000)
        key=inv.immutable_snapshot().items[0].id
        before=inv.immutable_snapshot()
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            refused(lambda:inv.equip_transaction(db,key,1,inv.epoch,'eligibility:male-bracer'),'sex')
        assert inv.immutable_snapshot()==before
        # Original10771d0 ignores roleNeed outside weapon slot0. Injecting a
        # nonempty list at the frozen-config seam checks the actual branch;
        # this does not claim the original42001 template has such a list.
        rules=dict(config.equipment_rules)
        rules[42001]=((20,21),rules[42001][1])
        alternate=replace(config,equipment_rules=MappingProxyType(rules))
        nonweapon=Inventory(store,1111,role['id'],alternate,epoch=inv.epoch,currency_rules=inv.currency_rules)
        inv.grant_item(42001)
        female_key=next(x.id for x in inv.immutable_snapshot().items if x.template_id==42001)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            nonweapon.equip_transaction(db,female_key,1,inv.epoch,'eligibility:nonweapon-list')
        assert next(x.equipment_slot for x in inv.immutable_snapshot().items if x.id==female_key)==1
        # Each original color's ten explicitly known shapes is checked against
        # independent sex fixtures: original characters1..5=1,6..10=2.
        for prefix in (1010100,1020200,1030300):
            for character,sex in ((1,1),(2,1),(3,1),(4,1),(5,1),(6,2),(7,2),(8,2),(9,2),(10,2)):
                shape=prefix+character
                assert config.shape_sexes[shape]==sex
                matching,wrong=(key,female_key) if sex==1 else (female_key,key)
                with closing(store.connect()) as db,db:
                    db.execute('BEGIN IMMEDIATE')
                    current=inv.immutable_snapshot_transaction(db)
                    worn=next((x for x in current.items if x.equipment_slot==1),None)
                    if worn:inv.unequip_transaction(db,worn.id,-1,inv.epoch,'eligibility:remove:'+str(shape))
                    # Trusted fixture changes are uncommitted: wear must read
                    # this transaction's shape, rather than cache constructor sex.
                    db.execute('UPDATE roles SET shape=?,school=? WHERE id=?',(shape,min(store.choices[shape]),role['id']))
                    before=inv.immutable_snapshot_transaction(db)
                    with patch.object(store,'connect',side_effect=AssertionError('Nested equipment connection')),patch.object(
                            Path,'read_text',side_effect=AssertionError('Hot equipment file read')):
                        refused(lambda:inv.equip_transaction(db,wrong,1,inv.epoch,'eligibility:wrong:'+str(shape)),'sex')
                        assert inv.immutable_snapshot_transaction(db)==before
                        event=inv.equip_transaction(db,matching,1,inv.epoch,'eligibility:wear:'+str(shape))
                        assert not event.replayed and event.item_key==matching
                        replies=inv.equipment_bag_messages(db,inv.epoch)
                    assert next(x.equipment_slot for x in inv.immutable_snapshot_transaction(db).items if x.id==matching)==1
        for kind,body in replies:
            assert kind==0xc03f3
            probe(0xef6220,u32(0x2284234),u32(0x2284238),payload=body)
        try:config.shape_sexes[1010110]=1
        except TypeError:pass
        else:raise AssertionError('Startup shape sex metadata is mutable')
        try:config.equipment[42000]['sexNeed']='2'
        except TypeError:pass
        else:raise AssertionError('Startup equipment sex metadata is mutable')
        # Current actual original weapon20/21 survives preparation verbatim;
        # raising level cannot turn its list into an empty/unrestricted rule.
        assert config.equipment_rules[49197][0]==(20,21)
        for template in (49197,40109,45011,42002):inv.grant_item(template)
        keys={x.template_id:x.id for x in inv.immutable_snapshot().items}
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('UPDATE roles SET level=10 WHERE id=?',(role['id'],))
            before=inv.immutable_snapshot_transaction(db)
            refused(lambda:inv.equip_transaction(db,keys[49197],0,inv.epoch,'eligibility:original20-21'),'character')
            assert inv.immutable_snapshot_transaction(db)==before
            #40109 has an empty roleNeed but original sex1, so it is NOT free
            #for sex2. Original source facts must be checked independently.
            refused(lambda:inv.equip_transaction(db,keys[40109],0,inv.epoch,'eligibility:empty-list'),'sex')
            db.execute('UPDATE roles SET shape=1010101,school=12,level=1 WHERE id=?',(role['id'],))
            inv.equip_transaction(db,keys[40109],0,inv.epoch,'eligibility:empty-list')
            inv.equip_transaction(db,keys[45011],4,inv.epoch,'eligibility:need-one-item-level100')
            before=inv.immutable_snapshot_transaction(db)
            refused(lambda:inv.equip_transaction(db,keys[42002],1,inv.epoch,'eligibility:need-ten'),'level')
            assert inv.immutable_snapshot_transaction(db)==before
            # The very first refused sex request left no paid command receipt.
            inv.equip_transaction(db,key,1,inv.epoch,'eligibility:male-bracer')
        # Native receive and legacy public equip share the exact same gate,
        # including replacement: a failed swap preserves the current male item.
        before=inv.immutable_snapshot()
        refused(lambda:inv.receive(0xc03f5,struct.pack('>ii',female_key,1)),'sex')
        refused(lambda:inv.equip(female_key,1),'sex')
        assert inv.immutable_snapshot()==before
        assert Inventory(store,1111,role['id'],config).immutable_snapshot()==before
        token='装备性别:00007';store.inventory_config=config
        with closing(store.connect()) as db,db:db.execute('UPDATE role_leases SET epoch=? WHERE role_id=?',(token,role['id']))
        active=Inventory(store.leased(1111,role['id'],token),1111,role['id'],config,epoch=token,currency_rules=inv.currency_rules)
        refused(lambda:active.receive(0xc03f5,struct.pack('>ii',female_key,1)),'sex')
        with closing(active.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            old=active.equip_transaction(db,key,1,token,'eligibility:male-bracer')
            assert old.replayed
        assert active.immutable_snapshot()==before
    report={'passed':['original sex2 shape1010110 refuses sex1 bracer before any asset change',
        'all30 original shapes accept matching bracer and refuse opposite sex in the current uncommitted role transaction',
        'startup sex/shape metadata frozen; no file read or nested connection during wear/current bag encoding',
        'original49197 roleNeed20/21 retained and refused; empty weapon list unrestricted but independent sex gate enforced',
        'nonweapon ignores injected roleNeed at public configuration seam, without relabeling original template metadata',
        'original level100/needLevel1 belt accepted at role1; needLevel10 bracer refuses without replacement',
        'same previously refused command later succeeds; native/legacy/current opaque lease share gate; reopen retains current gear',
        'original complete carried/equipped bag decoders consume current results'],
        'database':'disposable','live_server_changed':False,'native_gui_tested':False}
    write_json(OUT/'evidence/equipment-eligibility-verification.json',report)
    print('PASS',', '.join(report['passed']))


if __name__=='__main__':main()
