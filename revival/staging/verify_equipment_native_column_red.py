"""Migration RED: native own-equipment3, retained internal equipment4.

Deliberately outside the normal top-level verification suite. Current shared
entry remains untouched; integration owns the future passing Adapter path.
"""
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib
import json
import struct
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from accounts import AccountStore
from inventory import Inventory,QUERY_BAG,InventoryNotReady
from currency import initialize_wallet
from inspect_client import OUT
import runtime_storage


def main():
    with TemporaryDirectory(prefix='equipment-native-column-') as tmp:
        store=AccountStore(Path(tmp)/'state.sqlite3');runtime_storage.prepare(store)
        role=store.create_role(1111,'装备原栏复现',12,1010101);rid=role['id'];epoch=store.acquire_lease(1111,rid)
        inv=Inventory(store.leased(1111,rid,epoch),1111,rid)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');initialize_wallet(db,1111,rid,epoch,(1000,0,0,0),'explicit_migration',store.currency_rules)
        inv.grant_item(49001);key=inv.immutable_snapshot().items[0].id
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');inv.equip_transaction(db,key,0,epoch,'native-column-known-wear')
        native_error=None
        try:native=inv.receive(QUERY_BAG,struct.pack('>iQ',3,0))
        except InventoryNotReady as error:native=[];native_error=str(error)
        internal=inv.receive(QUERY_BAG,struct.pack('>iQ',4,0))
        snapshot=inv.immutable_snapshot()
        def columns(messages):return [struct.unpack_from('>i',body)[0] for kind,body in messages if kind==0xc03f3]
        with closing(store.connect()) as db:
            db.execute('BEGIN')
            projected=columns(inv.equipment_bag_messages(db,epoch))
            refresh=[(kind,struct.unpack_from('>i',body)[0]) for kind,body in inv.equipment_refresh(db,key)]
            tip_column=struct.unpack_from('>i',inv.equipment_tip_message(db,key,epoch)[1])[0]
        report={'status':'known_protocol_migration_red_not_fixed','goal':'active','fixture':'temporary real public Inventory equip of49001; no real role/DB/service',
            'native_own_query':{'column':3,'target':0,'response_columns':columns(native),'error':native_error},
            'legacy_internal_query':{'column':4,'target':0,'response_columns':columns(internal)},
            'actual_equipment_slots':[(i.id,i.template_id,i.equipment_slot) for i in snapshot.items],
            'owned_public_producer_columns':projected,'owned_endurance_producer_columns':refresh,'owned_tip_producer_column':tip_column,
            'owned_inventory_sha256':hashlib.file_digest((OUT/'inventory.py').open('rb'),'sha256').hexdigest(),
            'shared_or_database_edits':False,'source':'NPC_REPAIR_COLUMN_RESEARCH.md actual CEquipDialog/click paths and27 independently replayed combinations'}
        (OUT/'evidence/equipment-native-column-red.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(report,ensure_ascii=False),flush=True)
        assert any(i.equipment_slot==0 for i in snapshot.items),'Fixture did not equip actual owned item'
        assert columns(native)==[3], 'RED: native own-equipment column3 gets no current equipment bag; internal4 is a distinct server representation'


if __name__=='__main__':main()
