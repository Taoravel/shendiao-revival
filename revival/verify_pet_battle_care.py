"""Selected state and actual ordinary combat readiness are distinct."""
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
import struct

from accounts import AccountStore
from inventory import Inventory,FIGHT_PET,REFRESH_PET
from pet_care import PetCare
from native_gameplay_probe import probe
from inspect_client import OUT,write_json


def main():
    with TemporaryDirectory() as tmp:
        store=AccountStore(Path(tmp)/'battle-care.sqlite3')
        role=store.create_role(1111,'寿命参战',12,1010101)
        config=Inventory.prepare(store);inv=Inventory(store,1111,role['id'],config)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('UPDATE roles SET level=5 WHERE id=?',(role['id'],))
            pet=db.execute('INSERT INTO inventory_pets(role_id,template_id,name) VALUES(?,?,?)',
                (role['id'],500001,'已知寿命零')).lastrowid
            inv.initialize_pet_care(db,pet,1,100,0)
        inv.fight_pet(pet)
        current=inv.immutable_snapshot()
        assert current.pets[0].fighting==1 and current.pets[0].care.lifetime==0
        inv.fight_pet(None)
        messages=inv.receive(FIGHT_PET,struct.pack('>i',pet))
        assert (0xc07d9,struct.pack('>i',pet)) in messages
        assert inv.immutable_snapshot().pets[0].fighting==1
        for grade in (1,2,3,4,5,6):
            for lifetime,allowed in ((0,False),(1,False),(49,False),(50,True),(51,True)):
                care=PetCare(0,grade,100,lifetime)
                assert config.care_rules.ordinary_battle_care_ready(care) is allowed
        assert not config.care_rules.ordinary_battle_care_ready(PetCare(0,1,0,50))
        try:config.care_rules.ordinary_battle_care_ready(None)
        except ValueError:pass
        else:raise AssertionError('Unknown care treated as combat ready')
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            no_loyalty=db.execute('INSERT INTO inventory_pets(role_id,template_id,name) VALUES(?,?,?)',
                (role['id'],500001,'已知忠诚零')).lastrowid
            inv.initialize_pet_care(db,no_loyalty,1,0,50)
        before=inv.immutable_snapshot()
        try:inv.receive(FIGHT_PET,struct.pack('>i',no_loyalty))
        except ValueError:pass
        else:raise AssertionError('Zero loyalty displaced selected pet')
        assert inv.immutable_snapshot()==before
        # Normal care food can restore lifetime without toggling selection;
        # the care-only gate changes while actual HP remains a separate gate.
        from inventory_test_support import known_cash_context
        inv=Inventory(store,1111,role['id'],config,**known_cash_context(store,1111,role['id']))
        inv.grant_item(32036)
        key=inv.immutable_snapshot().items[0].id
        messages=inv.receive_pet_consumable(struct.pack('>iiQ',key,1,pet),inv.epoch,'battle-care:restore')
        current=inv.immutable_snapshot().pets[0]
        assert current.fighting==1 and current.care.lifetime==1000
        assert config.care_rules.ordinary_battle_care_ready(current.care)
        _,raw=probe(0xf9d7b0,0xf9d840,0xf9d880,payload=next(b for k,b in messages if k==REFRESH_PET))
        assert struct.unpack_from('<i',raw,8+0xb0)[0]==1000
        assert Inventory(AccountStore(store.path),1111,role['id'],config).immutable_snapshot()==inv.immutable_snapshot()
    report={'passed':['original help36001 allows selected fighting state at known lifetime0',
        'native FIGHT_PET acknowledges low-life selected key; zero loyalty cannot displace it',
        'ordinary care-only gate0/1/49 false and50/51 true at all six colors; unknown care rejected',
        'real lifetime food changes0 to1000 without toggling selection; native decoder and reopen retain1000'],
        'database':'disposable','native_gui_verified':False,'battle_executed':False,'live_server_changed':False}
    write_json(OUT/'evidence/pet-battle-care-verification.json',report)
    print('PASS',', '.join(report['passed']))


if __name__=='__main__':main()
