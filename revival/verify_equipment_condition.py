"""Owned gear wear, cash repair and common-transaction failure semantics."""
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
import sqlite3
from accounts import AccountStore
from inventory import Inventory
from currency import load_currency_rules,prepare_wallet_storage,initialize_wallet,read_wallet
from inspect_client import OUT,write_json


def main():
    with TemporaryDirectory() as tmp:
        store=AccountStore(Path(tmp)/'state.sqlite3')
        role=store.create_role(1111,'装备耐久',12,1010101);epoch=store.acquire_lease(1111,role['id'])
        config=Inventory.prepare(store);inv=Inventory(store,1111,role['id'],config)
        money=load_currency_rules()
        with closing(store.connect()) as db:prepare_wallet_storage(db)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            initialize_wallet(db,1111,role['id'],epoch,(10000,777,0,0),'explicit_migration',money)
        inv.grant_item(40200,binding=1);key=inv.snapshot()['items'][0]['id']
        def state():
            with closing(store.connect()) as db:
                db.execute('BEGIN');return inv.equipment_condition(db,key)
        def wallet():
            with closing(store.connect()) as db:
                db.execute('BEGIN');return read_wallet(db,1111,role['id'],epoch,money)
        def wear(request,version,amount):
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE');return inv.wear_equipment(db,key,request,version,amount)
        def repair(request,version,draw,owner_epoch=None):
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                return inv.repair_equipment(db,key,epoch if owner_epoch is None else owner_epoch,request,version,draw,money)
        def refused(call):
            before=inv.snapshot();balances=wallet()
            try:call()
            except ValueError:pass
            else:raise AssertionError('Invalid equipment operation accepted')
            assert inv.snapshot()==before and wallet()==balances
        assert (state().current,state().maximum,state().color_tier)==(100,100,1)
        refused(lambda:repair('full',0,0))
        inv.equip(key,0)
        assert inv.equipment_attributes()[2]
        damaged=wear('wear:20',0,20)
        assert damaged.current==80 and wear('wear:20',0,20)==damaged
        first=repair('repair:success',1,599)
        assert (first.cost,first.success,first.after.current)==(40,True,100)
        assert (wallet()[0].balance,wallet()[1].balance)==(9960,777)
        assert repair('repair:success',1,599)==first
        worn=wear('later:wear',2,10)
        assert repair('repair:success',1,599)==first and state()==worn
        failure=repair('repair:failure',3,600)
        assert (failure.cost,failure.success,failure.after.current,failure.after.maximum)==(20,False,90,90)
        assert wallet()[0].balance==9940
        refused(lambda:repair('repair:success',1,600))
        refused(lambda:repair('stale-condition',3,0))
        refused(lambda:repair('stale-lease',4,0,epoch+1))
        broken=wear('wear:broken',4,1000)
        assert broken.current==0 and inv.equipment_attributes()[2]==()
        before=inv.snapshot();balances=wallet()
        with closing(store.connect()) as db,db:
            db.executescript("CREATE TRIGGER fail_condition BEFORE UPDATE ON inventory_equipment_conditions BEGIN SELECT RAISE(ABORT,'condition failure'); END;")
        try:repair('repair:db-failure',5,0)
        except sqlite3.IntegrityError:pass
        else:raise AssertionError('Injected condition save failure did not execute')
        assert inv.snapshot()==before and wallet()==balances
        with closing(store.connect()) as db,db:db.execute('DROP TRIGGER fail_condition')
        repaired=repair('repair:db-failure',5,0)
        assert repaired.after.current==90 and wallet()[0].balance==9760
        assert inv.equipment_attributes()[2]==((81,20),(811,20),(1231,6))
        # Outer common receipt failure undoes both a trusted wear and repair.
        before=inv.snapshot();balances=wallet()
        try:
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                inv.wear_equipment(db,key,'outer:wear',6,10)
                inv.repair_equipment(db,key,epoch,'outer:repair',7,0,money)
                raise RuntimeError('common settlement failure')
        except RuntimeError:pass
        assert inv.snapshot()==before and wallet()==balances
        # Existing unknown equipment is not initialized by snapshot/reopen.
        with closing(store.connect()) as db,db:
            legacy=db.execute('INSERT INTO inventory_items(role_id,template_id,quantity,slot) VALUES(?,?,1,?)',
                (role['id'],40200,5)).lastrowid
        assert 'condition' not in next(x for x in inv.snapshot()['items'] if x['id']==legacy)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            inv.initialize_equipment_condition(db,legacy,0,10,3)
            try:inv.initialize_equipment_condition(db,legacy,100,100,1)
            except ValueError:pass
            else:raise AssertionError('Existing condition reset')
        before=inv.snapshot();balances=wallet()
        try:
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE');inv.repair_equipment(db,legacy,epoch,'maximum10',0,0,money)
        except ValueError:pass
        else:raise AssertionError('Maximum<=10 repaired')
        assert inv.snapshot()==before and wallet()==balances
        other_role=store.create_role(1111,'他人装备',12,1010101)
        other_epoch=store.acquire_lease(1111,other_role['id'])
        other=Inventory(store,1111,other_role['id'],config)
        try:
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE');other.wear_equipment(db,key,'foreign',6,1)
        except ValueError:pass
        else:raise AssertionError('Other role damaged owned equipment')
        # An ample bound-silver wallet cannot cover an insufficient cash fee.
        other.grant_item(40200)
        other_key=other.snapshot()['items'][0]['id']
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            initialize_wallet(db,1111,other_role['id'],other_epoch,(0,10000,0,0),'explicit_migration',money)
            other.wear_equipment(db,other_key,'poor:wear',0,20)
        poor=other.snapshot()
        try:
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                other.repair_equipment(db,other_key,other_epoch,'poor:repair',1,0,money)
        except ValueError:pass
        else:raise AssertionError('Bound silver substituted for insufficient cash')
        assert other.snapshot()==poor
        with closing(store.connect()) as db:
            db.execute('BEGIN')
            assert tuple(v.balance for v in read_wallet(db,1111,other_role['id'],other_epoch,money))==(0,10000,0,0)
        assert Inventory(AccountStore(store.path),1111,role['id'],config).snapshot()==inv.snapshot()
        assert next(x for x in inv.snapshot()['items'] if x['id']==key)['binding']==1
    report={'passed':['new ordinary gear gets explicit designed100/white1 baseline',
        'wear version and retry receipt preserve item identity','broken gear loses baseEffect; repair restores it',
        'NPC cost uses original level row; success599 and failure600 follow designed scale',
        'cash debit never spends bound silver','insufficient cash cannot substitute bound silver',
        'repair replay never pays or heals twice',
        'later wear not overwritten by old repair receipt','failure lowers maximum and clamps current',
        'stale version lease and payload conflict refuse','real DB abort undoes currency debit and condition receipt',
        'outer common transaction failure rolls back both domains','unknown legacy condition remains unknown',
        'explicit import cannot reset and maximum10 cannot repair','foreign gear refused','reopen preserves binding and condition'],
        'native_client_ui_tested':False,'NPC_service_route_connected':False,'battle_wear_connected':False}
    write_json(OUT/'evidence/equipment-condition-verification.json',report)
    print('PASS:',', '.join(report['passed']))


if __name__=='__main__':main()
