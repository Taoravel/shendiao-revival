"""Paid generic commands read current native messages without mutation."""
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
import struct
import sqlite3

from accounts import AccountStore
from inventory import (Inventory,MOVE_ITEM,USE_ITEM,FIGHT_PET,PET_INFO,REFRESH_PET,BAG_INFO,
    ADD_PET_POINT,RENAME_PET,FREE_PET,REST_PET)
from inventory_test_support import known_cash_context
from research_pet_binding import native_column_bindings
from research_pet_skills import native_record_skills
from native_gameplay_probe import probe
from native_inspect import u32
from wire import octets,read_octets
from inspect_client import OUT,write_json


def refused(action):
    try:action()
    except ValueError:return
    raise AssertionError('Unfenced or malformed current mutation read accepted')


def main():
    with TemporaryDirectory() as directory:
        store=AccountStore(Path(directory)/'state.sqlite3')
        role=store.create_role(1111,'当前变更回复',12,1010101)
        config=Inventory.prepare(store)
        inv=Inventory(store,1111,role['id'],config,**known_cash_context(store,1111,role['id'],balances=(71,0,0,0)))
        inv.grant_item(32000,3);key=inv.immutable_snapshot().items[0].id
        paid=struct.pack('>6iq',1,key,0,1,7,0,-1)
        inv.receive(MOVE_ITEM,paid)
        inv.move_item(key,2)
        before=inv.immutable_snapshot()
        with closing(store.connect()) as db:
            db.execute('BEGIN')
            messages=inv.current_mutation_messages_transaction(db,MOVE_ITEM,paid,inv.epoch)
        assert inv.immutable_snapshot()==before and messages[0][0]==BAG_INFO
        probe(0xef6220,u32(0x2284234),u32(0x2284238),payload=messages[0][1])
        assert struct.unpack_from('>Q',messages[0][1],4)[0]==71
        # Compare the whole current bag to the independent original item codec:
        # the paid move went to7, but the current location is2.
        item,_=probe(0x8184f0,0x822040,0x81a590,
            {4:struct.pack('<i',32000),12:struct.pack('<i',key),0x10:struct.pack('<i',2),0x20:struct.pack('<i',3)})
        assert messages[0][1]==struct.pack('>iQi',1,71,40)+b'\1'+item+b'\0'
        first=inv.grant_pet(500001);second=inv.grant_pet(500051)
        with closing(store.connect()) as db,db:
            # This isolated legacy fixture explicitly qualifies the actor for
            # the original dog's uselevel5; no character growth is exercised.
            db.execute('UPDATE roles SET level=5 WHERE id=?',(role['id'],))
            p=inv.pet_progress(db,first)
            inv.change_pet_growth(db,first,'fixture:wounds',p.state.version,'resources',(1,1))
        medicine=struct.pack('>iiQ',key,1,first)
        inv.receive_pet_consumable(medicine,inv.epoch,'paid:medicine')
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            p=inv.pet_progress(db,first)
            inv.change_pet_growth(db,first,'fixture:xp',p.state.version,'experience',50)
        points=struct.pack('>6i',first,1,0,0,0,0)
        inv.receive(ADD_PET_POINT,points)
        inv.receive(ADD_PET_POINT,points)
        rename=struct.pack('>i',first)+octets('最初名字'.encode('utf-16le'))
        inv.receive(RENAME_PET,rename);inv.rename_pet(first,'后来名字')
        selected=struct.pack('>i',first)
        inv.receive(FIGHT_PET,selected);inv.receive(FIGHT_PET,struct.pack('>i',second))
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            p=inv.pet_progress(db,first)
            inv.change_pet_growth(db,first,'fixture:later-wounds',p.state.version,'resources',(6,1))
        def current(kind,payload,epoch=None):
            with closing(store.connect()) as db:
                db.execute('BEGIN')
                def read_only(action,*args):
                    return sqlite3.SQLITE_DENY if action in (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,
                        sqlite3.SQLITE_DELETE,sqlite3.SQLITE_CREATE_TABLE,sqlite3.SQLITE_DROP_TABLE) else sqlite3.SQLITE_OK
                db.set_authorizer(read_only)
                result=inv.current_mutation_messages_transaction(db,kind,payload,inv.epoch if epoch is None else epoch)
                assert db.in_transaction
                return result
        before=inv.immutable_snapshot()
        for kind,payload in ((USE_ITEM,medicine),(ADD_PET_POINT,points),(RENAME_PET,rename),(FIGHT_PET,selected)):
            reply=current(kind,payload)
            assert native_column_bindings(next(b for k,b in reply if k==PET_INFO))==((first,0,False),(second,0,False))
            assert (0xc07d9,struct.pack('>i',second)) in reply and (0xc07d9,selected) not in reply
            bean=next(b for k,b in reply if k==REFRESH_PET)
            name,_=read_octets(bean,8)
            assert name.decode('utf-16le')=='后来名字'
            _,decoded=probe(0xf9d7b0,0xf9d840,0xf9d880,payload=bean)
            assert struct.unpack_from('<i',decoded,0x48)[0]==6
            assert struct.unpack_from('<h',decoded,0x80)[0]==3
            assert native_record_skills(bean)[0]==(200091,200061)
            assert inv.immutable_snapshot()==before
        inv.free_pet(first)
        before=inv.immutable_snapshot()
        gone=current(USE_ITEM,medicine)
        assert native_column_bindings(next(b for k,b in gone if k==PET_INFO))==((second,0,False),)
        assert (0xc07dd,struct.pack('>ii',1,first)) in gone and (0xc07d9,struct.pack('>i',second)) in gone
        assert not any(k==REFRESH_PET for k,b in gone) and inv.immutable_snapshot()==before
        inv.receive(REST_PET,b'');inv.free_pet(second)
        before=inv.immutable_snapshot()
        empty=current(FIGHT_PET,selected)
        assert native_column_bindings(next(b for k,b in empty if k==PET_INFO))==()
        assert (0xc07db,b'') in empty and not any(k==0xc07d9 for k,b in empty)
        assert inv.immutable_snapshot()==before
        refused(lambda:current(MOVE_ITEM,paid,inv.epoch+1))
        refused(lambda:current(USE_ITEM,medicine[:-1]))
        refused(lambda:current(USE_ITEM,struct.pack('>iiQ',key,0,role['id'])))
        with closing(store.connect()) as db:
            refused(lambda:inv.current_mutation_messages_transaction(db,MOVE_ITEM,paid,inv.epoch))
        before=inv.immutable_snapshot()
        old_epoch=inv.epoch;token='当前回复:00007'
        with closing(store.connect()) as db,db:db.execute('UPDATE role_leases SET epoch=? WHERE role_id=?',(token,role['id']))
        store.inventory_config=config
        inv=Inventory(store.leased(1111,role['id'],token),1111,role['id'],epoch=token,currency_rules=inv.currency_rules)
        refused(lambda:current(MOVE_ITEM,paid,old_epoch))
        assert current(MOVE_ITEM,paid)[0][0]==BAG_INFO and inv.immutable_snapshot()==before
    report={'passed':['paid move7 later moved2 returns current original-codec bag and actual71 cash',
        'real prior medicine/allocation/rename/selection requests return laterHP6/potential3/name/current selected pet',
        'released original pet yields current owned column/removal/current other selection; empty column explicitly rests',
        'SQL authorizer forbids writes throughout current reply construction; no repeated heal/point/debit or nested transaction',
        'native full-column/refresh/learned-skill codecs consume current messages; current opaque lease works, obsolete/missing/malformed context refuses'],
        'live_server_changed':False,'native_gui_tested':False,'shared_paid_routing_connected_by_this_window':False}
    write_json(OUT/'evidence/inventory-current-mutation-messages-verification.json',report)
    print('PASS',', '.join(report['passed']))


if __name__=='__main__':main()
