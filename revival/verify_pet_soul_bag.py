"""Current orb flags and separate detail messages through original Item/Bag."""
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
import struct
import sqlite3
from accounts import AccountStore
from inventory import Inventory,item_record
from currency import initialize_wallet
from pet_soul_item_storage import OrbRules,OrbSource
from pet_soul_item_data import OrbTips
import pet_soul_item_storage as orbs
from pet_soul_bag import current_messages
from native_gameplay_probe import probe
import runtime_storage


def main():
    with TemporaryDirectory(prefix='soul-orb-bag-') as tmp:
        store=AccountStore(Path(tmp)/'state.sqlite3');runtime_storage.prepare(store);rules=OrbRules.load()
        with closing(store.connect()) as db:orbs.prepare(db)
        role=store.create_role(1111,'元魂背包详情',12,1010101);rid=role['id'];epoch=store.acquire_lease(1111,rid)
        inv=Inventory(store.leased(1111,rid,epoch),1111,rid)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');initialize_wallet(db,1111,rid,epoch,(123,0,0,0),'explicit_migration',store.currency_rules)
        inv.grant_item(31276,binding=1);inv.grant_item(31277);inv.grant_item(31000,3)
        items=inv.immutable_snapshot().items;first,second,generic=items
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            for item,flags,tips in ((first,160,OrbTips(61,10001,-205,204)),(second,0x80000000,OrbTips(120,10002,205,-204))):
                orbs.initialize(db,inv,rules,OrbSource(rid,item.id,item.template_id,0,rules.revision,
                    'known-bag-orb-'+str(item.id),tips,flags,None),'explicit_known_orb_instance')
            messages=current_messages(db,inv,rules,store.currency_rules)
            assert tuple(kind for kind,_ in messages)==(0xc03f3,0xc03fe,0xc03fe)
            bag=messages[0][1]
            assert bag[:17]==struct.pack('>iQiB',1,123,40,3) and len(bag)==162 and bag[-1:]==b'\0'
            first_record=bag[17:65];second_record=bag[65:113]
            assert struct.unpack_from('>4i',first_record)==(31276,161,first.id,0)
            assert struct.unpack_from('>IIII',second_record)==(31277,0x80000000,second.id,1)
            assert bag[113:161]==item_record(vars(generic))
            # Native Item contains only its original scalar fields. The orb
            # data goes in separate SItemTips, not inserted into these48 bytes.
            original,raw=probe(0x8184f0,0x822040,0x81a590,{4:struct.pack('<i',31276),8:struct.pack('<I',161),
                12:struct.pack('<i',first.id),16:struct.pack('<i',0),32:struct.pack('<i',1)})
            assert original==first_record and struct.unpack_from('<I',raw,8)[0]==161
            original,raw=probe(0x8184f0,0x822040,0x81a590,{4:struct.pack('<i',31277),8:struct.pack('<I',0x80000000),
                12:struct.pack('<i',second.id),16:struct.pack('<i',1),32:struct.pack('<i',1)})
            assert original==second_record and struct.unpack_from('<I',raw,8)[0]==0x80000000
            def observer(emu,target):
                read=lambda address:struct.unpack('<I',emu.mem_read(address,4))[0]
                begin,end=read(target+0x28),read(target+0x2c)
                assert end-begin==192
                assert read(begin+8)==161 and read(begin+16)==0
                assert read(begin+64+8)==0x80000000 and read(begin+64+16)==1
            probe(0xef6220,0xef62d0,0xef6350,payload=bag,observer=observer)
            assert messages[1][1][9:].hex()=='0000003d00002711ffffff33000000cc'
            assert messages[2][1][9:].hex()=='0000007800002712000000cdffffff34'
            db.set_authorizer(lambda action,*args:sqlite3.SQLITE_DENY if action in
                (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE) else sqlite3.SQLITE_OK)
            assert current_messages(db,inv,rules,store.currency_rules)==messages
        # A newly granted orb with unknown data must not turn into zero-XP tips.
        inv.grant_item(31278)
        with closing(store.connect()) as db:
            db.execute('BEGIN')
            try:current_messages(db,inv,rules,store.currency_rules)
            except ValueError:pass
            else:raise AssertionError('Unknown orb silently omitted or given zero data')
        print('PASS original scalar48-byte Item flags161/high-bit and nonempty Bag decoder; separate current orb4 tips, '
            'same unmodified non-orb format, readonly repeat, unknown orb refuses; no embedded data or GUI claim')


if __name__=='__main__':main()
