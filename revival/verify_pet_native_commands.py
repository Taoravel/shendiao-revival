"""Pet allocation and refresh requests against original native codecs."""
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
import struct
from accounts import AccountStore
from inventory import Inventory, ADD_PET_POINT, REFRESH_PET, REFRESH_PET_EXP, QUERY_PETS, FREE_PET, REMOVE_PET
from native_gameplay_probe import probe
from inspect_client import OUT, write_json


def main():
    with TemporaryDirectory() as tmp:
        store=AccountStore(Path(tmp)/'state.sqlite3')
        role=store.create_role(1111,'宠物加点',12,1010101)
        store.inventory_config=Inventory.prepare(store)
        inv=Inventory(store,1111,role['id'])
        pet=inv.grant_pet(500001)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            inv.change_pet_growth(db,pet,'test:experience',0,'experience',55)
        body=struct.pack('>6i',pet,5,0,0,0,0)
        native,_=probe(0x8184f0,0xe530d0,0xdba720,
                       {8:struct.pack('<6i',pet,5,0,0,0,0)})
        assert native == body
        replies=inv.receive(ADD_PET_POINT,body)
        assert [x[0] for x in replies] == [REFRESH_PET,REFRESH_PET_EXP]
        probe(0xf9d7b0,0xf9d840,0xf9d880,payload=replies[0][1])
        expected,_=probe(0x8184f0,0xe54020,0xdc0bf0,
                         {8:struct.pack('<i',pet),0x10:struct.pack('<Q',5)})
        assert replies[1][1] == expected
        before=inv.snapshot()
        try:
            inv.receive(ADD_PET_POINT,body)
        except ValueError:
            pass
        else:
            raise AssertionError('Exhausted potential accepted')
        assert inv.snapshot() == before
        queried=inv.receive(QUERY_PETS,struct.pack('>iQ',1,role['id']))
        assert (REFRESH_PET_EXP,struct.pack('>iQ',pet,5)) in queried
        with closing(store.connect()) as db,db:
            db.execute('BEGIN')
            progress=inv.pet_progress(db,pet)
            assert progress.state.allocated == (5,0,0,0,0)
            assert progress.attributes.potential == 0
        inv.fight_pet(pet)
        try:
            inv.free_pet(pet)
        except ValueError:
            pass
        else:
            raise AssertionError('Fighting pet released')
        inv.fight_pet()
        released=inv.receive(FREE_PET,struct.pack('>i',pet))
        assert released == [(REMOVE_PET,struct.pack('>ii',1,pet))]
        native,_=probe(0xdc0ea0,0xe540d0,0xdc0f40,{8:struct.pack('<ii',1,pet)})
        assert released[0][1] == native
        assert not inv.snapshot()['pets']
        replacement=inv.grant_pet(500001)
        assert replacement != pet
    result={'passed':['original add-point request bytes','native full pet refresh decoder',
                      'original experience refresh bytes','allocated points persist',
                      'insufficient potential refusal without mutation','query restores experience',
                      'fighting pet release refusal','native remove-pet reply','released capacity reusable without key reuse'],
            'native_ui_tested':False,'live_gateway_restarted':False}
    write_json(OUT/'evidence/pet-native-command-verification.json',result)
    print('PASS:',', '.join(result['passed']))


if __name__=='__main__':main()
