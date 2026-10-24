"""Public recovery payments compared with independently executed native quotes."""
from contextlib import closing
from dataclasses import FrozenInstanceError
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import struct
import sys
import tempfile
import time
from unittest.mock import patch
from accounts import AccountStore
from currency import initialize_wallet,read_wallet
from inventory import Inventory
from inspect_client import OUT,write_json
from diagnose_npc_loyalty_quote import measure
from world_npcs import NpcScene
from world_owner import MapAddress,Location
import npc_recovery
import runtime_storage


class RecoveryCases:
    """Disposable real owner/lease, legacy import, native proof and wallet."""
    def __init__(self,directory):
        self.store=AccountStore(Path(directory)/'state.sqlite3')
        prepared=runtime_storage.prepare(self.store)
        self.npc=next(p for rows in self.store.npc_resources[0].values() for p in rows if p.npc_id==10086)
        self.address=MapAddress(self.npc.map_id,self.npc.map_id,0)
        self.key=(self.npc.map_id<<32)|self.npc.placement_id
        self.scene=NpcScene(self.address,(self.npc,),prepared[3],binding_capacity=1,
            interaction_rules=self.store.npc_interaction_rules)
        self.scene.bind(self.key,self.npc.placement_id);self.count=0

    def create(self,pets,*,level=21,balance=100000):
        self.count+=1;account=1111+self.count
        # Account provisioning has no public creation Interface; explicit test
        # accounts keep the real three-role cap intact for every scenario.
        with closing(self.store.connect()) as db,db:
            db.execute('INSERT INTO accounts(id,name,login_secret) SELECT ?,?,login_secret FROM accounts WHERE id=1111',
                (account,str(account).encode()))
        role=self.store.create_role(account,f'忠诚核验{self.count}',11,1010109)
        epoch=self.store.acquire_lease(account,role['id'])
        inventory=Inventory(self.store.leased(account,role['id'],epoch),account,role['id'])
        with closing(inventory.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');db.execute('UPDATE roles SET level=? WHERE id=?',(level,role['id']))
            initialize_wallet(db,account,role['id'],epoch,(balance,0,0,0),'explicit_migration',self.store.currency_rules)
            for power,grade,loyalty in pets:
                pet=db.execute('INSERT INTO inventory_pets(role_id,template_id,name) VALUES(?,500001,?)',
                    (role['id'],'忠诚已知夹具')).lastrowid
                inventory.initialize_pet_growth(db,pet)
                inventory.initialize_pet_care(db,pet,grade,loyalty,6000)
                if power is not None:inventory.initialize_pet_blood(db,pet,power)
        return inventory

    def intent(self,inventory,identity,*,kind=3):
        now=int(time.monotonic()*1000)
        current=Location(inventory.role_id,inventory.epoch,self.address,1,self.npc.x,self.npc.y)
        proof=self.scene.interact(struct.pack('>q',self.key),current,current,
            request_id=identity,now_ms=now,deadline_ms=now+30000)
        return npc_recovery.plan(self.store.npc_gameplay,struct.pack('>qi',self.key,kind),proof,current,
            request_id=identity,now_ms=now,deadline_ms=now+30000)

    def cash(self,inventory):
        with closing(inventory.accounts.connect()) as db:
            db.execute('BEGIN')
            return next(r.balance for r in read_wallet(db,inventory.account_id,inventory.role_id,inventory.epoch,self.store.currency_rules)
                if r.currency=='cash')

    def dump(self):
        with closing(self.store.connect()) as db:return tuple(db.iterdump())

    def receipt(self,inventory,identity):
        with closing(self.store.connect()) as db:
            return db.execute('SELECT fee,detail FROM npc_recovery_receipts WHERE role_id=? AND request_id=?',
                (inventory.role_id,identity)).fetchone()


def quote_matrix(cases):
    # Expected scalar amounts are from the independently replayed original,
    # including valid colour6/power52611, not derived from the implementation.
    examples=[(((power,1,99),),fee) for power,fee in enumerate((45,47,49,51,53,55,57,59,61,63))]
    examples.extend(((((9,1,80),(52611,6,399)),1307),
        (((52611,6,399),(9,1,80)),1307),(((9,1,100),(52611,6,399)),47)))
    for index,(pets,expected) in enumerate(examples):
        inventory=cases.create(pets);before=inventory.immutable_snapshot()
        identity=f'native-matrix-{index}';intent=cases.intent(inventory,identity)
        with patch.object(Path,'read_text',side_effect=AssertionError('Hot configuration read')):
            npc_recovery.settle(cases.store,inventory,intent)
        assert cases.cash(inventory)==100000-expected
        after=inventory.immutable_snapshot()
        for old,new in zip(before.pets,after.pets):
            assert new.progress==old.progress and new.care.lifetime==6000
            assert new.care.loyalty==inventory.care_rules.maximum(new.care.grade)
        fee,detail=cases.receipt(inventory,identity);assert fee==expected
        quotes=[row['loyalty_quote'] for row in json.loads(detail)]
        assert all(q['fee_recipe']=='2026-10-24.npc-pet-loyalty.2' and q['source']=='known_ordinary_power' for q in quotes)
    return len(examples)


def refused_without_writes(cases,action):
    before=cases.dump()
    try:action()
    except (ValueError,sqlite3.DatabaseError,MemoryError):pass
    else:raise AssertionError('Invalid recovery was accepted')
    assert cases.dump()==before, 'Refused recovery left assets or receipts behind'


def compatibility_and_kinds(cases):
    for growth in (True,False):
        inventory=cases.create(((None,1,80),));pet=inventory.immutable_snapshot().pets[0]
        if not growth:
            with closing(inventory.accounts.connect()) as db,db:
                db.execute('DELETE FROM inventory_pet_growth WHERE pet_id=?',(pet.id,))
        before=inventory.immutable_snapshot();identity=f'unknown-blood-{growth}'
        npc_recovery.settle(cases.store,inventory,cases.intent(inventory,identity))
        after=inventory.immutable_snapshot()
        assert cases.cash(inventory)==99100 and after.pets[0].progress==before.pets[0].progress
        assert after.pets[0].care.loyalty==100
        fee,detail=cases.receipt(inventory,identity);quote=json.loads(detail)[0]['loyalty_quote']
        assert (fee,quote['power'],quote['remainder'],quote['unit_fee'],quote['source'])==(
            900,None,0,45,'legacy_unknown_remainder_zero')
        with closing(inventory.accounts.connect()) as db:
            assert not db.execute('SELECT 1 FROM inventory_pet_blood WHERE pet_id=?',(pet.id,)).fetchone()
    for level,fee in ((20,0),(21,1260)):
        inventory=cases.create(((9,1,80),),level=level)
        npc_recovery.settle(cases.store,inventory,cases.intent(inventory,f'free-gate-{level}'))
        assert cases.cash(inventory)==100000-fee
    for kind,expected in ((2,20),(4,1280)):
        inventory=cases.create(((9,1,80),));pet=inventory.immutable_snapshot().pets[0]
        with closing(inventory.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            inventory.change_pet_growth(db,pet.id,'fixture:injury',pet.progress.state.version,'resources',(0,0))
        npc_recovery.settle(cases.store,inventory,cases.intent(inventory,f'kind-{kind}',kind=kind))
        updated=inventory.immutable_snapshot().pets[0]
        assert cases.cash(inventory)==100000-expected
        assert (updated.progress.state.hp,updated.progress.state.mp)==(
            updated.progress.attributes.max_hp,updated.progress.attributes.max_mp)
        assert updated.care.loyalty==(80 if kind==2 else 100) and updated.care.lifetime==6000
    for pets in ((),((9,1,100),)):
        inventory=cases.create(pets)
        refused_without_writes(cases,lambda:npc_recovery.settle(cases.store,inventory,cases.intent(inventory,'full-or-empty')))
    return 8


def failures_and_retry(cases):
    inventory=cases.create(((9,1,80),),balance=900)
    refused_without_writes(cases,lambda:npc_recovery.settle(cases.store,inventory,cases.intent(inventory,'insufficient')))
    corruptions=(('state',json.dumps({'version':0,'power':-1})),
        ('state',json.dumps({'version':0,'power':True})),('state',json.dumps({'version':0,'power':1140})),
        ('policy','unknown-blood-policy'))
    for index,(column,value) in enumerate(corruptions):
        inventory=cases.create(((9,1,80),));pet=inventory.immutable_snapshot().pets[0]
        with closing(inventory.accounts.connect()) as db,db:
            db.execute(f'UPDATE inventory_pet_blood SET {column}=? WHERE pet_id=?',(value,pet.id))
        refused_without_writes(cases,lambda:npc_recovery.settle(cases.store,inventory,cases.intent(inventory,f'bad-known-{index}')))
    inventory=cases.create(((9,1,80),));pet=inventory.immutable_snapshot().pets[0]
    with closing(inventory.accounts.connect()) as db,db:
        db.execute('DELETE FROM inventory_pet_growth WHERE pet_id=?',(pet.id,))
    refused_without_writes(cases,lambda:npc_recovery.settle(cases.store,inventory,cases.intent(inventory,'orphan-blood')))
    # This real SQLite failure is deliberately late, after the debit/care
    # changes, and remains part of the same transaction as both receipts.
    inventory=cases.create(((9,1,80),));intent=cases.intent(inventory,'sql-retry')
    with closing(cases.store.connect()) as db,db:
        db.execute("CREATE TRIGGER fail_loyalty_receipt BEFORE INSERT ON npc_recovery_receipts "
            "BEGIN SELECT RAISE(ABORT,'controlled receipt storage failure'); END")
    refused_without_writes(cases,lambda:npc_recovery.settle(cases.store,inventory,intent))
    with closing(cases.store.connect()) as db,db:db.execute('DROP TRIGGER fail_loyalty_receipt')
    npc_recovery.settle(cases.store,inventory,intent);assert cases.cash(inventory)==98740
    inventory=cases.create(((9,1,80),));intent=cases.intent(inventory,'encode-retry')
    original_pack_into=struct.pack_into
    def allocate_packet(fmt,buffer,offset,*values):
        if fmt=='>i' and offset==89:raise MemoryError('Controlled final packet allocation failure')
        return original_pack_into(fmt,buffer,offset,*values)
    with patch.object(struct,'pack_into',allocate_packet):
        refused_without_writes(cases,lambda:npc_recovery.settle(cases.store,inventory,intent))
    npc_recovery.settle(cases.store,inventory,intent);assert cases.cash(inventory)==98740
    return 8


def old_paid_current_only(cases):
    path=Path(__file__).parent/'evidence/reviews/npc-loyalty-quote-20261024/base/npc_recovery.py'
    spec=importlib.util.spec_from_file_location('_npc_original_recovery',path)
    old=importlib.util.module_from_spec(spec);sys.modules[spec.name]=old
    spec.loader.exec_module(old)
    policy=json.loads((OUT/'design/npc-services-v1.json').read_text(encoding='utf8'))
    inventory=cases.create(((9,1,80),));intent=cases.intent(inventory,'paid-before-loyalty-v2')
    new_rules=cases.store.npc_recovery_rules
    try:
        old.prepare(cases.store,policy)
        old.settle(cases.store,inventory,intent)
    finally:
        cases.store.npc_recovery_rules=new_rules;del sys.modules[spec.name]
    assert cases.cash(inventory)==99100
    original_receipt=cases.receipt(inventory,intent.service.request_id)
    assert original_receipt[0]==900 and 'loyalty_quote' not in json.loads(original_receipt[1])[0]
    pet=inventory.immutable_snapshot().pets[0]
    with closing(inventory.accounts.connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        inventory.change_pet_care(db,pet.id,'later-defeat',pet.care.version,'defeat',1)
    inventory.grant_item(36117)
    item=inventory.immutable_snapshot().items[0]
    inventory.receive_pet_consumable(struct.pack('>iiQ',item.id,1,pet.id),inventory.epoch,'later-blood')
    current=inventory.immutable_snapshot();assert current.pets[0].progress.blood.state.power==209
    assert current.pets[0].care.loyalty==80
    before=cases.dump()
    npc_recovery.settle(cases.store,inventory,intent)
    assert cases.dump()==before and inventory.immutable_snapshot()==current and cases.cash(inventory)==99100
    assert cases.receipt(inventory,intent.service.request_id)==original_receipt
    npc_recovery.settle(cases.store,inventory,cases.intent(inventory,'fresh-after-loyalty-v2'))
    assert cases.cash(inventory)==97840 and inventory.immutable_snapshot().pets[0].care.loyalty==100
    before=cases.dump();npc_recovery.settle(cases.store,inventory,cases.intent(inventory,'fresh-after-loyalty-v2'))
    assert cases.dump()==before
    return 1


def startup_contract(cases,directory):
    policy=json.loads((OUT/'design/npc-pet-loyalty-v2.json').read_text(encoding='utf8'))
    service=json.loads((OUT/'design/npc-services-v1.json').read_text(encoding='utf8'))
    rules=cases.store.npc_recovery_rules.loyalty
    assert rules.care_rules is cases.store.inventory_config.care_rules
    assert rules.blood_rules is cases.store.inventory_config.blood_rules
    try:rules.base_unit_fee=1
    except FrozenInstanceError:pass
    else:raise AssertionError('Loyalty startup recipe is mutable')
    invalid=[]
    for key in ('base_unit_fee','power_remainder_coefficient','power_modulus','free_through_level',
                'native_free_sentinel','maximum_total_fee'):
        invalid.extend((key,value) for value in (None,True,0,1.5,'45'))
    invalid.extend((('revision','unknown'),('base_service_policy','unknown'),('currency','bound_silver'),
                    ('payment_purpose','npc_equipment_identify')))
    path=Path(directory)/'invalid-policy.json'
    for key,value in invalid:
        changed=dict(policy);changed[key]=value;path.write_text(json.dumps(changed),encoding='utf8')
        try:npc_recovery.load_loyalty_rules(cases.store.inventory_config,service,path=path)
        except ValueError:pass
        else:raise AssertionError(f'Unsupported startup loyalty field accepted: {key}={value!r}')
    return len(invalid)


def main():
    files=('npc_recovery.py','design/npc-pet-loyalty-v2.json','design/npc-services-v1.json',
        'inventory.py','pet_blood.py','pet_care.py','diagnose_npc_loyalty_quote.py',
        'verify_npc_loyalty_quote.py','evidence/npc-loyalty-quote-native.json',
        'evidence/reviews/npc-loyalty-quote-20261024/base/npc_recovery.py')
    def hashes():return {name:hashlib.sha256((Path(__file__).parent/name).read_bytes()).hexdigest() for name in files}
    before=hashes()
    report=measure()
    # Literals from whole original1136290, not the implementation formula.
    expected={0:900,9:1260,1139:1260}
    differences=[{'power':row['blood_power'],'actual':row['actual_cash_charge'],
                  'expected':expected[row['blood_power']]}
                 for row in report['measurements']
                 if row['actual_cash_charge']!=expected[row['blood_power']]]
    report.update(native_quote_compared=True,native_quote_source='NPC_LOYALTY_QUOTE_NATIVE_RESEARCH.md',
                  expected_charges=expected,differences=differences,passed=not differences)
    if differences:
        path=OUT/'evidence/npc-loyalty-quote-domain-baseline.json'
        if not path.exists():write_json(path,report)
        raise AssertionError(f'Known blood recovery payments differ from original quote: {differences}')
    with tempfile.TemporaryDirectory(prefix='npc-loyalty-domain-') as directory:
        cases=RecoveryCases(directory)
        report['native_matrix_cases']=quote_matrix(cases)
        report['compatibility_and_kind_cases']=compatibility_and_kinds(cases)
        report['failure_rollback_and_retry_cases']=failures_and_retry(cases)
        report['original_paid_compatibility_cases']=old_paid_current_only(cases)
        report['invalid_startup_cases']=startup_contract(cases,directory)
    assert hashes()==before, 'Material recovery inputs changed during verification'
    report['material_input_sha256']=before
    report['verification_groups']=6
    report['production_implementation_changed_for_this_batch']=True
    write_json(OUT/'evidence/npc-loyalty-quote-verification.json',report)
    print('PASS',report['verification_groups'],'groups,',report['invalid_startup_cases'],'invalid startup recipes')


if __name__=='__main__':main()
