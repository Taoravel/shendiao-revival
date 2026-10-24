"""Independent public NPC/asset contract: actual ledgers, replay and late rollback."""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import sqlite3
import struct
import time
from accounts import AccountStore
from inventory import Inventory
from currency import read_wallet
from role_resource_storage import read_role_resources
from verify_resource_owner_runtime import fixture
from verify_equipment_identification_cas import known_unidentified
from world_npcs import NpcScene
from world_owner import MapAddress,Location
from world_role_delivery import RoleViewBinding
from inspect_client import OUT,write_json
import runtime_storage
import npc_identification_query
import npc_equipment_identification as identification


def main():
    with TemporaryDirectory(prefix='identify-npc-asset-') as tmp:
        store=AccountStore(Path(tmp)/'state.sqlite3');role=store.create_role(1111,'鉴定跨域验证',11,1010109)
        prepared=runtime_storage.prepare(store);npc_identification_query.prepare(store);identification.prepare(store)
        npc=next(p for p in store.npc_resources[0][1007] if p.npc_id==10890 and p.placement_id==75)
        fixture(store,role,npc)
        with closing(store.connect()) as db:epoch=db.execute('SELECT epoch FROM role_leases WHERE role_id=?',(role['id'],)).fetchone()[0]
        inv=Inventory(store.leased(1111,role['id'],epoch),1111,role['id'])
        key=known_unidentified(store,inv,slot=2)
        with closing(inv.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');runtime_storage._synchronize_source(db,store,inv,'identify:compat-fixture-source',replayed=False)
        address=MapAddress(1007,1007,0);entity=(1007<<32)|75
        scene=NpcScene(address,(npc,),prepared[3],binding_capacity=1,interaction_rules=store.npc_interaction_rules)
        scene.bind(entity,75);location=Location(role['id'],epoch,address,1,npc.x,npc.y)
        binding=RoleViewBinding(address,'known-compat-map',role['id'],epoch,1,1)
        def admitted(request):
            now=int(time.monotonic()*1000)
            def proof(name):return scene.interact(struct.pack('>q',entity),location,location,
                request_id=name,now_ms=now,deadline_ms=now+30000)
            dialogue=identification.query(inv,b'\1'+struct.pack('>iQi',key,entity,1),proof(request+':query'),
                location,binding,rules=store.npc_identification_rules,request_id=request,now_ms=now,deadline_ms=now+30000)
            return identification.confirm(dialogue.ticket,struct.pack('>iii',key,0,1),proof(request+':confirm'),
                location,binding,now_ms=now,deadline_ms=now+30000)
        def current():
            with closing(store.connect()) as db:
                db.execute('BEGIN');assets=inv.immutable_snapshot_transaction(db)
                resources=read_role_resources(db,1111,role['id'],epoch,store.resource_rules)
                wallet=read_wallet(db,1111,role['id'],epoch,store.currency_rules)
                counts=tuple(db.execute('SELECT COUNT(*) FROM '+table+' WHERE role_id=?',(role['id'],)).fetchone()[0]
                    for table in ('npc_equipment_identification_receipts','npc_command_receipts','role_wallet_receipts','role_resource_receipts'))
                return assets,resources,wallet,counts
        intent=admitted('identify:compat-confirm');before=current()
        for table in ('npc_equipment_identification_receipts','npc_command_receipts','role_resource_receipts'):
            with closing(store.connect()) as db,db:
                db.execute(f"CREATE TRIGGER identify_compat_fault BEFORE INSERT ON {table} BEGIN SELECT RAISE(ABORT,'actual NPC/domain/source identification receipt failure'); END")
            try:identification.settle(store,inv,intent)
            except sqlite3.IntegrityError:pass
            else:raise AssertionError('Real NPC receipt failure committed fees or asset')
            assert current()==before
            with closing(store.connect()) as db,db:db.execute('DROP TRIGGER identify_compat_fault')
        with patch('equipment_detail.encode',side_effect=RuntimeError('late actual NPC detail encoding')):
            try:identification.settle(store,inv,intent)
            except RuntimeError:pass
            else:raise AssertionError('Late actual NPC tip failure committed')
        assert current()==before
        replies=identification.settle(store,inv,intent);after=current()
        assert next(i for i in after[0].items if i.id==key).detail.identified==1
        assert after[2][0].balance==1900 and (after[1].hp,after[1].mp,after[1].version)==(10,20,0)
        assert tuple(b-a for a,b in zip(before[3],after[3]))==(1,1,1,1)
        # Keep the true FencedConnection Adapter and prohibit every SQL data
        # mutation at the underlying standard SQLite connection.
        sqlite_connect=sqlite3.connect
        def readonly(*args,**kwargs):
            db=sqlite_connect(*args,**kwargs);db.set_authorizer(lambda action,*rest:sqlite3.SQLITE_DENY if action in
                (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE) else sqlite3.SQLITE_OK)
            return db
        with patch('accounts.sqlite3.connect',side_effect=readonly):
            paid=identification.settle(store,inv,intent)
        assert current()==after and paid==replies
        # A fresh dialogue does not grant another payment for already1.
        fresh=admitted('identify:compat-fresh')
        try:identification.settle(store,inv,fresh)
        except ValueError:pass
        else:raise AssertionError('Fresh already-identified target charged twice')
        assert current()==after
        # A later legitimate source-only move changes current state. Paid
        # confirmation remains a strict current read, not old item restoration.
        def hook(db,inventory,snapshot,*,replayed):
            runtime_storage._synchronize_source(db,store,inventory,'identify:compat-later-move',replayed=replayed)
        inv.move_item(key,3,precommit=hook);moved=current()
        with patch('accounts.sqlite3.connect',side_effect=readonly):
            identification.settle(store,inv,intent)
        assert current()==moved and next(i for i in moved[0].items if i.id==key).slot==3
    write_json(OUT/'evidence/equipment-identification-npc-compat-verification.json',{'passed':[
        'actual original query/confirm domain -> NPC settle -> public asset CAS/cash/actual root source; no private NPC asset SQL',
        'real NPC dedicated/common/source receipt insert failures plus late tip encoding roll every item/cash/source/receipt back; same failed ticket then pays once',
        'committed ticket strictly SQL-readonly using true fenced connection; fresh already1 dialogue refuses no extra fee; later legitimate move retained under paid current reads',
        'cash2000->1900, NPC/common/wallet/source each1 new receipt, roleHP10/MP20/version0 unchanged'],
        'shared_encrypted_confirmation_tested':False,'deployed':False,'live_server_changed':False,'native_gui_verified':False})
    print('PASS actual NPC/public asset contract: dedicated/common/source/encoding rollback, fenced readonly paid, later current state')


if __name__=='__main__':main()
