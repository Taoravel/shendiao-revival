"""Real owned worn assets encoded in original column3, internal4 preserved."""
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
import struct
import sqlite3
from accounts import AccountStore
from inventory import Inventory,QUERY_BAG
from currency import initialize_wallet
from native_gameplay_probe import probe
from equipment_gems import GemState,embed
from equipment_gem_score import GemScoreBasis,project
from research_equipment_gem_detail import NativeGemEquipmentDetail
from wire import read_octets
import runtime_storage
import equipment_native_columns as native
import equipment_gem_storage as sockets
import equipment_gem_score_storage as scores
import equipment_gem_presentation as presentation


def main():
    with TemporaryDirectory(prefix='native-owned-equipment-') as tmp:
        store=AccountStore(Path(tmp)/'state.sqlite3');runtime_storage.prepare(store)
        role=store.create_role(1111,'自身装备原列',12,1010101);rid=role['id'];epoch=store.acquire_lease(1111,rid)
        inv=Inventory(store.leased(1111,rid,epoch),1111,rid)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');initialize_wallet(db,1111,rid,epoch,(1000,0,0,0),'explicit_migration',store.currency_rules)
        inv.grant_item(49001);key=inv.immutable_snapshot().items[0].id
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');inv.equip_transaction(db,key,0,epoch,'known-native-equip')
        before=inv.immutable_snapshot()
        with closing(store.connect()) as db:
            sockets.prepare(db);scores.prepare(db)
        rules=native.NativeEquipmentRules.load()
        with closing(store.connect()) as db:
            db.execute('BEGIN');db.set_authorizer(lambda action,*args:sqlite3.SQLITE_DENY if action in
                (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE) else sqlite3.SQLITE_OK)
            messages=native.query_bag(db,inv,struct.pack('>iQ',3,0))
            assert len(messages)==1 and messages[0][0]==0xc03f3
            body=messages[0][1]
            assert struct.unpack_from('>iQi',body)==(3,0,16)
            assert body[16]==1 and struct.unpack_from('>4i',body,17)==(49001,0,key,0)
            probe(0xef6220,0xef62d0,0xef6350,payload=body)
            current=native.item_messages(db,inv,rules,key)
            assert tuple(kind for kind,_ in current)==(0xc03fe,0xc0412,0xc0414)
            assert struct.unpack_from('>ii',current[0][1])==(3,key)
            assert current[1][1]==struct.pack('>iBii',3,1,key,100)
            assert current[2][1]==struct.pack('>iii',3,key,100)
            probe(0xd9c110,0xe4e5c0,0xe0a240,payload=current[0][1])
            assert native.query_tips(db,inv,rules,struct.pack('>ii',3,key))==(current[0],)
            assert native.query_endures(db,inv,rules,struct.pack('>i',3))==current[1:]
            for body in (struct.pack('>iQ',4,0),struct.pack('>iQ',3,rid+1),struct.pack('>iQ',3,0)+b'\0'):
                try:native.query_bag(db,inv,body)
                except ValueError:pass
                else:raise AssertionError('Foreign/NPC/trailing own equipment query accepted')
            for column in (1,4):
                try:native.query_tips(db,inv,rules,struct.pack('>ii',column,key))
                except ValueError:pass
                else:raise AssertionError('Wrong native equipment namespace accepted')
        assert inv.immutable_snapshot()==before
        legacy=inv.receive(QUERY_BAG,struct.pack('>iQ',4,0))
        assert struct.unpack_from('>i',legacy[0][1])[0]==4
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');inv.wear_equipment(db,key,'known-native-damage',0,20)
            worn=native.item_messages(db,inv,rules,key)
            assert worn[1][1]==struct.pack('>iBii',3,1,key,80)
            probe(0xef9850,0xefa210,0xefa2a0,payload=worn[1][1])
            probe(0xd9dfb0,0xe4e950,0xd9e050,payload=worn[2][1])
            repair=inv.repair_equipment(db,key,epoch,'known-native-repair',1,0,store.currency_rules)
            assert repair.after.current==100
            assert native.item_messages(db,inv,rules,key)[1][1]==struct.pack('>iBii',3,1,key,100)
        # Real source/presentation import and CAS fixture; this does not claim
        # the paid gem-material/cash controller or an NPC repair permission.
        with closing(store.connect()) as db,db:db.execute('UPDATE roles SET level=10 WHERE id=?',(rid,))
        inv.grant_item(45001);inv.grant_item(35005)
        belt=next(i.id for i in inv.immutable_snapshot().items if i.template_id==45001)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');inv.equip_transaction(db,belt,4,epoch,'known-native-belt')
            sockets.initialize(db,inv,rules.gems,belt,GemState(0,(),rules.gems.revision),0,'explicit_known_socket_profile')
            basis=GemScoreBasis(rid,belt,rules.score.revision,0,'native-column-known-plain-score')
            scores.initialize(db,inv,rules.score,rules.gems,basis,'explicit_known_pre_gem_score')
            old=sockets.read(db,inv,rules.gems,belt)
            material=next(i for i in inv.immutable_snapshot_transaction(db).items if i.template_id==35005)
            plan=embed(rules.gems,old.item,old.state,material,0,flags=(0,0))
            change=project(rules.score,rules.gems,old.item,old.state,plan.after,basis)
            saved=sockets.replace_state(db,inv,rules.gems,old,plan.after)
            try:native.item_messages(db,inv,rules,belt)
            except ValueError:pass
            else:raise AssertionError('Pending gem score source silently encoded')
            presentation.apply(db,inv,rules.gems,rules.score,old,saved,change)
        gem_before=inv.immutable_snapshot()
        with closing(store.connect()) as db:
            db.execute('BEGIN');db.set_authorizer(lambda action,*args:sqlite3.SQLITE_DENY if action in
                (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE) else sqlite3.SQLITE_OK)
            gem_messages=native.item_messages(db,inv,rules,belt)
            assert struct.unpack_from('>ii',gem_messages[0][1])==(3,belt)
            detail,end=read_octets(gem_messages[0][1],8);assert end==len(gem_messages[0][1])
            parsed=NativeGemEquipmentDetail(45001).parse(detail)
            assert parsed['gems']==[35005] and parsed['score']==50
            request,source=native.socket_basis(db,inv,rules,0xc0425,struct.pack('>iBi',belt,1,material.id))
            assert request.source_column==4 and source.item.equipment_slot==4
        assert inv.immutable_snapshot()==gem_before
        try:
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                inv.wear_equipment(db,key,'native-late-fault',2,10)
                changed=native.item_messages(db,inv,rules,key)
                assert changed[1][1]==struct.pack('>iBii',3,1,key,90)
                probe(0xef9850,0xefa210,0xefa2a0,payload=changed[1][1])
                raise RuntimeError('controlled native encode-before-commit failure')
        except RuntimeError as error:assert str(error)=='controlled native encode-before-commit failure'
        assert inv.immutable_snapshot()==gem_before
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');inv.unequip_transaction(db,belt,3,epoch,'known-native-remove')
            carried=native.item_messages(db,inv,rules,belt)
            assert struct.unpack_from('>ii',carried[0][1])==(1,belt)
            for column in (3,4):
                try:native.query_tips(db,inv,rules,struct.pack('>ii',column,belt))
                except ValueError:pass
                else:raise AssertionError('Removed item remained in worn native namespace')
            try:native.socket_basis(db,inv,rules,0xc0425,struct.pack('>iBi',belt,1,material.id))
            except ValueError:pass
            else:raise AssertionError('Socket source1 searched the carried container')
            request,source=native.socket_basis(db,inv,rules,0xc0425,struct.pack('>iBi',belt,0,material.id))
            assert request.source_column==1 and source.item.equipment_slot is None
            # Both malformed source bytes and unknown trailing wire are rejected.
            for payload in (struct.pack('>iBi',belt,3,material.id),struct.pack('>iBi',belt,0,material.id)+b'\0'):
                try:native.socket_basis(db,inv,rules,0xc0425,payload)
                except ValueError:pass
                else:raise AssertionError('Unproven native socket source accepted')
        other=store.create_role(1111,'他人原列资产',12,1010101);other_epoch=store.acquire_lease(1111,other['id'])
        other_inv=Inventory(store.leased(1111,other['id'],other_epoch),1111,other['id'])
        with closing(store.connect()) as db:
            db.execute('BEGIN')
            try:native.item_messages(db,other_inv,rules,key)
            except ValueError:pass
            else:raise AssertionError('Other role read native equipment instance')
        current_epoch=store.acquire_lease(1111,rid)
        with closing(store.connect()) as db:
            db.execute('BEGIN')
            try:native.query_bag(db,inv,struct.pack('>iQ',3,0))
            except ValueError:pass
            else:raise AssertionError('Replaced lease emitted current native equipment')
        current_inv=Inventory(store.leased(1111,rid,current_epoch),1111,rid)
        with closing(store.connect()) as db:
            db.execute('BEGIN');db.set_authorizer(lambda action,*args:sqlite3.SQLITE_DENY if action in
                (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE) else sqlite3.SQLITE_OK)
            assert native.query_bag(db,current_inv,struct.pack('>iQ',3,rid))[0][1][16]==1
        print('PASS actual owned native bag/tips/endure3, worn repair100→80→100, gem-aware current detail and score50; '
            'internal4 unchanged; original codecs/parser and SQL readonly; carried source0/worn source1, '
            'late encode rollback, foreign role/old lease/namespace guards')


if __name__=='__main__':main()
