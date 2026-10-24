"""Public NPC depot settlement seam; original 64-bit transfer requests.

Temporary storage and real map proofs. Shared wire routing is checked separately;
this script does not register a substitute owner or touch the running service.
"""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
import struct
import tempfile
import time
import sqlite3
from accounts import AccountStore
from inventory import Inventory
from world_owner import MapAddress,Location
from world_npcs import NpcScene
from inspect_client import OUT,write_json
import runtime_storage
import npc_gameplay
import npc_depot
from currency import read_wallet

DEPOSIT,DRAW=0xc03fb,0xc03fc


def main():
    with tempfile.TemporaryDirectory() as temp:
        store=AccountStore(Path(temp)/'depot-money.sqlite3')
        role=store.create_role(1111,'仓库银两',11,1010109)
        with closing(store.connect()) as db,db:
            db.executemany('INSERT INTO accounts VALUES(?,?,?)',
                ((2222+i,('offline-depot'+str(i)).encode(),b'offline-fixture-only') for i in range(4)))
        fixtures={label:(2222+i,store.create_role(2222+i,'仓银'+str(i),11,1010109))
            for i,label in enumerate(('overflow-depot','overflow-cash','unknown-depot','unknown-wallet'))}
        prepared=runtime_storage.prepare(store);epoch=store.acquire_lease(1111,role['id'])
        inv=Inventory(store.leased(1111,role['id'],epoch),1111,role['id'])
        runtime_storage.initialize_role_wallet(store,1111,role['id'],epoch,
            (10000000000,12345,0,0),'explicit_migration')
        npc_gameplay.initialize_depot(inv,98765,'explicit_migration')
        npc=next(p for ps in store.npc_resources[0].values() for p in ps if p.npc_id==10003)
        address=MapAddress(npc.map_id,npc.map_id,0)
        location=Location(role['id'],epoch,address,1,npc.x,npc.y)
        scene=NpcScene(address,(npc,),prepared[3],interaction_radius=32,binding_capacity=1)
        key=(npc.map_id<<32)|npc.placement_id;scene.bind(key,npc.placement_id)
        def command(request):
            now=int(time.monotonic()*1000)
            proof=scene.interact(struct.pack('>q',key),location,location,request_id=request,
                now_ms=now,deadline_ms=now+10000)
            return store.npc_gameplay.services.plan(struct.pack('>qi',key,6),proof,location,
                request_id=request,now_ms=now,deadline_ms=now+10000)
        def transfer(kind,amount,request):
            return npc_gameplay.depot_operation(store,inv,command(request),kind,struct.pack('>qq',key,amount))
        def balances(messages):
            values={}
            for kind,body in messages:
                if kind==0xc03fa:
                    slot,value=struct.unpack('>iq',body);values[slot]=value
            assert set(values)=={1,2}
            return values[1],values[2]
        deposited=balances(transfer(DEPOSIT,4294967303,'deposit'))
        assert deposited==(5705032697,4295066068),deposited
        withdrawn=balances(transfer(DRAW,4294967301,'draw'))
        assert withdrawn==(9999999998,98767),withdrawn
        assert balances(transfer(DEPOSIT,4294967303,'deposit'))==withdrawn
        def rejected(action):
            try:action()
            except ValueError:return
            raise AssertionError('Invalid warehouse money request was accepted')
        def state(inventory=inv):
            with closing(inventory.accounts.connect()) as db:
                db.execute('BEGIN')
                wallet=read_wallet(db,inventory.account_id,inventory.role_id,inventory.epoch,store.currency_rules)
                return tuple((r.currency,r.balance,r.revision) for r in wallet),npc_depot.cash_balance(db,inventory)
        before=state()
        rejected(lambda:transfer(DEPOSIT,9999999999,'cash-insufficient'))
        rejected(lambda:transfer(DRAW,98768,'depot-insufficient'))
        rejected(lambda:transfer(DEPOSIT,4294967302,'deposit'))
        for body in (struct.pack('>qq',key,0),struct.pack('>qq',key,-1),
                     struct.pack('>qq',key+1,1),struct.pack('>qq',key,1)[:-1]):
            rejected(lambda b=body:npc_gameplay.depot_operation(store,inv,command('malformed'),DEPOSIT,b))
        expired=replace(command('expired'),deadline_ms=int(time.monotonic()*1000)-1)
        rejected(lambda:npc_gameplay.depot_operation(store,inv,expired,DEPOSIT,struct.pack('>qq',key,1)))
        assert state()==before
        with closing(store.connect()) as db,db:
            db.execute("CREATE TRIGGER npc_abort_depot_cash BEFORE INSERT ON npc_command_receipts "
                "WHEN NEW.request_id='late-abort' BEGIN SELECT RAISE(ABORT,'controlled depot abort'); END")
        try:transfer(DEPOSIT,10,'late-abort')
        except sqlite3.IntegrityError:pass
        else:raise AssertionError('Late receipt insertion failure committed money')
        assert state()==before
        with closing(store.connect()) as db,db:db.execute('DROP TRIGGER npc_abort_depot_cash')
        assert balances(transfer(DEPOSIT,10,'late-abort'))==(9999999988,98777)
        assert balances(transfer(DEPOSIT,4294967303,'deposit'))==(9999999988,98777)

        def fixture(label,cash,depot):
            aid,r=fixtures[label];e=store.acquire_lease(aid,r['id'])
            other=Inventory(store.leased(aid,r['id'],e),aid,r['id'])
            if cash is not None:
                runtime_storage.initialize_role_wallet(store,aid,r['id'],e,(cash,0,0,0),'explicit_migration')
            if depot is not None:npc_gameplay.initialize_depot(other,depot,'explicit_migration')
            now=int(time.monotonic()*1000);loc=replace(location,role_id=r['id'],login_epoch=e)
            proof=scene.interact(struct.pack('>q',key),loc,loc,request_id=label,
                now_ms=now,deadline_ms=now+10000)
            cmd=store.npc_gameplay.services.plan(struct.pack('>qi',key,6),proof,loc,
                request_id=label,now_ms=now,deadline_ms=now+10000)
            return other,cmd
        for label,cash,depot,kind in (('overflow-depot',10,2**63-1,DEPOSIT),
                                     ('overflow-cash',2**63-1,10,DRAW)):
            other,cmd=fixture(label,cash,depot);old=state(other)
            rejected(lambda:npc_gameplay.depot_operation(store,other,cmd,kind,struct.pack('>qq',key,1)))
            assert state(other)==old
        for label,cash,depot in (('unknown-depot',10,None),('unknown-wallet',None,10)):
            other,cmd=fixture(label,cash,depot)
            rejected(lambda:npc_gameplay.depot_operation(store,other,cmd,DEPOSIT,struct.pack('>qq',key,1)))
            if cash is None:
                runtime_storage.initialize_role_wallet(store,other.account_id,other.role_id,other.epoch,
                    (10,0,0,0),'explicit_migration')
            else:npc_gameplay.initialize_depot(other,10,'explicit_migration')
            assert balances(npc_gameplay.depot_operation(store,other,cmd,DEPOSIT,struct.pack('>qq',key,1)))==(9,11)
        new_epoch=store.acquire_lease(1111,role['id'])
        current=Inventory(store.leased(1111,role['id'],new_epoch),1111,role['id'])
        before=state(current)
        rejected(lambda:transfer(DRAW,1,'old-owner'))
        assert state(current)==before
        assert before[1]==98777 and dict((name,value) for name,value,revision in before[0])['cash']==9999999988
        with closing(current.accounts.connect()) as db:
            db.execute('BEGIN')
            wallet=read_wallet(db,1111,role['id'],new_epoch,store.currency_rules)
            assert next(r.balance for r in wallet if r.currency=='bound_silver')==12345
        report={'passed':['native 64bit deposit4294967303 and draw4294967301',
            'cash plus depot total10000098765 conserved',
            'accepted retry returns current balances without moving money again',
            'bound silver12345 untouched',
            'zero/negative/truncation/wrong NPC/expired/conflicting replay refused',
            'both insufficient balances and both signed64 overflows reject unchanged',
            'late common-receipt SQL abort rolls back both balances and ledger/audit; same key later succeeds',
            'unknown wallet and depot baselines refuse without writing zero or consuming request key',
            'new lease preserves cash9999999988/depot98777; old owner cannot transfer'],
            'seam':'npc_gameplay.depot_operation with real NpcScene proof and role lease',
            'shared_wire_route_verified':False,'native_gui_verified':False,'live_database_modified':False}
    write_json(OUT/'evidence/npc-depot-money-verification.json',report);print(report)


if __name__=='__main__':main()
