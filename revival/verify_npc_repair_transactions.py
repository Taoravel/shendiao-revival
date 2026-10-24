"""Deterministic owner-side repair outcomes and real outer-transaction abort."""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
import struct
import tempfile
import time
from accounts import AccountStore
from inventory import Inventory,AssetChange
from currency import read_wallet
from world_owner import MapAddress,Location
from world_npcs import NpcScene
import runtime_storage
import npc_repairs
from inspect_client import OUT,write_json


def main():
    with tempfile.TemporaryDirectory() as temp:
        store=AccountStore(Path(temp)/'repair.sqlite3');role=store.create_role(1111,'修理事务',11,1010109)
        prepared=runtime_storage.prepare(store);epoch=store.acquire_lease(1111,role['id'])
        inv=Inventory(store.leased(1111,role['id'],epoch),1111,role['id'])
        runtime_storage.initialize_role_wallet(store,1111,role['id'],epoch,(1000,0,0,0),'explicit_migration')
        with closing(inv.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');inv.apply_settlement(db,AssetChange('gear',grants=((40200,1,1),)))
        key=inv.snapshot()['items'][0]['id']
        with closing(inv.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');inv.wear_equipment(db,key,'wear',0,20)
        placement=next(p for ps in store.npc_resources[0].values() for p in ps if p.npc_id==10004)
        address=MapAddress(placement.map_id,placement.map_id,0)
        location=Location(role['id'],epoch,address,1,placement.x,placement.y)
        scene=NpcScene(address,(placement,),prepared[3],interaction_radius=32,binding_capacity=1)
        npc_key=(placement.map_id<<32)|placement.placement_id;scene.bind(npc_key,placement.placement_id)
        def intent(request):
            now=int(time.monotonic()*1000)
            proof=scene.interact(struct.pack('>q',npc_key),location,location,
                request_id=request,deadline_ms=now+10000,now_ms=now)
            return npc_repairs.plan(store.npc_gameplay,struct.pack('>iqii',2,npc_key,1,key),proof,location,
                request_id=request,now_ms=now,deadline_ms=now+10000)
        def wallet():
            with closing(inv.accounts.connect()) as db:
                db.execute('BEGIN');return read_wallet(db,1111,role['id'],epoch,store.currency_rules)
        failed=intent('failed-attempt')
        npc_repairs.repair(store,inv,failed,draw_source=lambda bound:999)
        state=inv.snapshot()['items'][0]['condition']
        assert (state.version,state.current,state.maximum)==(2,80,90)
        assert next(r.balance for r in wallet() if r.currency=='cash')==960
        def forbidden_draw(bound):raise AssertionError('Committed repair resampled')
        npc_repairs.repair(store,inv,failed,draw_source=forbidden_draw)
        assert inv.snapshot()['items'][0]['condition']==state
        before=inv.snapshot();balances=wallet()
        with closing(store.connect()) as db,db:
            db.execute("CREATE TRIGGER npc_abort_repair BEFORE INSERT ON npc_command_receipts "
                       "WHEN NEW.request_id='rollback' BEGIN SELECT RAISE(ABORT,'controlled repair abort'); END")
        rollback=intent('rollback')
        import sqlite3
        try:npc_repairs.repair(store,inv,rollback,draw_source=lambda bound:0)
        except sqlite3.IntegrityError:pass
        else:raise AssertionError('Controlled repair failure committed')
        assert inv.snapshot()==before and wallet()==balances
        with closing(store.connect()) as db,db:db.execute('DROP TRIGGER npc_abort_repair')
        npc_repairs.repair(store,inv,rollback,draw_source=lambda bound:0)
        state=inv.snapshot()['items'][0]['condition']
        assert (state.version,state.current,state.maximum)==(3,90,90)
        assert next(r.balance for r in wallet() if r.currency=='cash')==940
        stale=intent('old-epoch')
        store.acquire_lease(1111,role['id'])
        try:npc_repairs.repair(store,inv,stale,draw_source=forbidden_draw)
        except ValueError:pass
        else:raise AssertionError('Old repair lease accepted')
    report={'passed':['server-injected failed draw charges40 once and preserves current80/max90',
        'committed retry never invokes draw source','real SQL abort rolls back cash, condition and all repair receipts',
        'same request succeeds after aborted transaction at current cost20',
        'expired role epoch cannot repair or invoke randomness'],'live_database_modified':False}
    write_json(OUT/'evidence/npc-repair-transactions.json',report);print(report)


if __name__=='__main__':main()
