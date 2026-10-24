"""Explicit resource migration BEFORE the natural opening/card/equip/cart/title.

Uses the real creation provenance and shared initialization Adapter. Known70/40
wounds/migration are a controlled pre-client fixture; auto activation stays off.
"""
import asyncio
from contextlib import closing
from dataclasses import replace
import json
from pathlib import Path
import tempfile
from accounts import AccountStore
from inspect_client import OUT,write_json
from role_attribute_storage import read_attribute_snapshot,update_role_vitals
from role_equipment import resource_caps_from_projection
from role_equipment_storage import current_equipment_totals
from role_resource_storage import migrate_role_resources,read_role_resources
from verify_newbie_jiaxing_runtime import check as natural_chain
from world_newbie import load_newbie_routes
import runtime_storage


def main():
    route=load_newbie_routes()[(9,11)]
    audit=json.loads((OUT/'evidence/newbie-birth-sites-audit.json').read_text(encoding='utf-8'))
    witness=next(r for r in audit['routes'] if (r['character_id'],r['school_id'])==(9,11))
    with tempfile.TemporaryDirectory(prefix='resource-opening-') as folder:
        store=AccountStore(Path(folder)/'state.sqlite3');prepared=runtime_storage.prepare(store)
        role=store.create_role(1111,'单资源完整开场',11,1010109)
        epoch=store.acquire_lease(1111,role['id'])
        inv,_,_,_=runtime_storage.load_role(store,1111,role['id'],epoch,store.task_resources)
        with closing(inv.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            old=read_attribute_snapshot(db,1111,role['id'],epoch)
            known=replace(old.vitals,hp=70,mp=40,version=old.vitals.version+1)
            update_role_vitals(db,1111,role['id'],epoch,old.vitals,known)
            totals=current_equipment_totals(db,1111,role['id'],epoch,inv.immutable_snapshot_transaction(db),store.equipment_attribute_rules)
            before=migrate_role_resources(db,1111,role['id'],epoch,known,resource_caps_from_projection(totals),
                origin='explicit_migration',migration_id='controlled-before-opening',rules=store.resource_rules,
                equipment_rules=store.equipment_attribute_rules)
        asyncio.run(natural_chain(store,prepared,role,route,witness))
        epoch=store.acquire_lease(1111,role['id'])
        with closing(store.leased(1111,role['id'],epoch).connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            current=read_role_resources(db,1111,role['id'],epoch,store.resource_rules)
            assert (current.hp,current.mp,current.caps.hp_max,current.caps.mp_max)==(80,46,110,106)
            assert current.version==before.version+1
            assert db.execute('SELECT count(*) FROM task_master_choices WHERE role_id=? AND selected_item IS NOT NULL',
                (role['id'],)).fetchone()==(1,)
            assert db.execute('SELECT count(*) FROM task_cart_transfers WHERE role_id=?',(role['id'],)).fetchone()==(1,)
    result=dict(passed=['explicit known resource transfer before original client opening authorization',
        'actual shared opening/card source/equip resource/type59 growth/cart/title stages remain one resource contract',
        'natural chain has no task offer/item grant/XP/spawn shortcut and preserves unique weapon/cart receipts',
        'known70/40 becomes80/46 only on original120XP growth; source-only and equip stages do not heal or bump resource version'],
        migration_fixture='explicit pre-client known wounds after real shared initialization; not automatic activation',
        database='disposable',native_gui_verified=False,live_server_changed=False,battle_executed=False)
    write_json(OUT/'evidence/resource-opening-runtime-verification.json',result);print(result)


if __name__=='__main__':main()
