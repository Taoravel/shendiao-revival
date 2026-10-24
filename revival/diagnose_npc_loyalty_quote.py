"""Measure actual recovery charges for known blood power in disposable storage."""
from contextlib import closing
from dataclasses import asdict
from pathlib import Path
import struct
import tempfile
import time
from accounts import AccountStore
from currency import initialize_wallet,read_wallet
from inventory import Inventory
from inspect_client import OUT,write_json
from world_npcs import NpcScene
from world_owner import MapAddress,Location
import npc_recovery
import runtime_storage


def measure():
    with tempfile.TemporaryDirectory(prefix='npc-loyalty-quote-') as directory:
        store=AccountStore(Path(directory)/'state.sqlite3')
        roles=[store.create_role(1111,name,11,1010109) for name in ('忠诚零血脉','忠诚个位九','忠诚血脉上限')]
        with closing(store.connect()) as db,db:
            db.executemany('UPDATE roles SET level=21 WHERE id=?',((role['id'],) for role in roles))
        prepared=runtime_storage.prepare(store)
        npc=next(p for rows in store.npc_resources[0].values() for p in rows if p.npc_id==10086)
        address=MapAddress(npc.map_id,npc.map_id,0);key=(npc.map_id<<32)|npc.placement_id
        scene=NpcScene(address,(npc,),prepared[3],binding_capacity=1,interaction_rules=store.npc_interaction_rules)
        scene.bind(key,npc.placement_id)
        rows=[]
        for role,power in zip(roles,(0,9,1139)):
            epoch=store.acquire_lease(1111,role['id'])
            inventory=Inventory(store.leased(1111,role['id'],epoch),1111,role['id'])
            with closing(inventory.accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                initialize_wallet(db,1111,role['id'],epoch,(5000,0,0,0),'explicit_migration',store.currency_rules)
                # Known legacy fixture; public one-time initialization preserves
                # the exact blood power and BASE profile supplied by authority.
                pet_id=db.execute('INSERT INTO inventory_pets(role_id,template_id,name,fighting,released) '
                    'VALUES(?,500001,?,0,0)',(role['id'],'血脉报价夹具')).lastrowid
                inventory.initialize_pet_growth(db,pet_id)
                inventory.initialize_pet_care(db,pet_id,1,80,6000)
                inventory.initialize_pet_blood(db,pet_id,power)
            before=inventory.immutable_snapshot();pet=before.pets[0]
            assert pet.progress.blood.state.power==power and pet.care.loyalty==80
            now=int(time.monotonic()*1000);identity=f'known-blood-{power}'
            current=Location(role['id'],epoch,address,1,npc.x,npc.y)
            proof=scene.interact(struct.pack('>q',key),current,current,
                request_id=identity,deadline_ms=now+10000,now_ms=now)
            intent=npc_recovery.plan(store.npc_gameplay,struct.pack('>qi',key,3),proof,current,
                request_id=identity,now_ms=now,deadline_ms=now+10000)
            messages=npc_recovery.settle(store,inventory,intent)
            after=inventory.immutable_snapshot();updated=after.pets[0]
            with closing(inventory.accounts.connect()) as db:
                db.execute('BEGIN')
                cash=next(row.balance for row in read_wallet(db,1111,role['id'],epoch,store.currency_rules)
                    if row.currency=='cash')
            assert updated.care.loyalty==100 and updated.care.lifetime==6000
            assert updated.progress==pet.progress
            rows.append({'blood_power':power,'blood_level':pet.progress.blood.level,
                'colour':pet.care.grade,'maximum_power':pet.progress.blood.maximum_power,
                'missing_loyalty':20,'actual_cash_charge':5000-cash,
                'before_care':asdict(pet.care),'after_care':asdict(updated.care),
                'logical_refresh_types':[kind for kind,body in messages]})
        return {'scope':'public npc_recovery.plan/settle, real known imports and wallet; disposable legacy role21 fixtures',
            'measurements':rows,'native_quote_compared':False,'production_modified':False,
            'live_database_modified':False,'native_gui_verified':False,'shared_runtime_verified':False}


def main():
    report=measure()
    write_json(OUT/'evidence/npc-loyalty-server-observation.json',report)
    baseline=OUT/'evidence/npc-loyalty-server-baseline.json'
    if not baseline.exists():write_json(baseline,report)
    print(report)


if __name__=='__main__':main()
