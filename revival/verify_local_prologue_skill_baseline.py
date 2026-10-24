"""Approved explicit designed-origin ledger enrollment, never a historical proof.

This first slice tests the role ledger's public permit/read/grant transaction.
Task cohort qualification and full teaching are separate public-interface slices.
"""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
import tempfile
from accounts import AccountStore
from inventory import Inventory
import role_skills as skills
from verify_world_committed_transfer_read import readonly


def main():
    with tempfile.TemporaryDirectory(prefix='local-prologue-baseline-') as folder:
        store=AccountStore(Path(folder)/'temporary.sqlite3')
        store.inventory_config=Inventory.prepare(store)
        rules=skills.load_other_skill_rules()
        policy=skills.load_local_prologue_baseline_rules()
        with closing(store.connect()) as db:skills.prepare_other_skill_storage(db)
        role=store.create_role(1111,'本地序章兼容接口',11,1010109)
        rid=role['id'];epoch=store.acquire_lease(1111,rid)
        # Explicit trusted-caller permit fixture. This does not claim the Task
        # cohort has been proved or that a real predecessor battle was played.
        permit=skills.LocalPrologueBaselinePermit(1111,rid,policy.revision,policy.policy_sha256,
            policy.evidence_sha256,'local-prologue:'+str(rid),'fixture-creation','fixture-chapter','a'*64,
            100179,100107,'fixture-battle','b'*64,'c'*64,'d'*64,'fixture-teaching-commit',epoch)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            assert skills.read_other_skills(db,1111,rid,epoch,rules) is None
            enrolled=skills.enroll_local_prologue_other_skills(db,1111,rid,epoch,rules,policy,permit)
            assert enrolled.origin=='designed_local_prologue_baseline' and enrolled.entries==()
            assert skills.read_local_prologue_baseline_receipt(db,1111,rid,epoch,rules,policy).permit.original_epoch==epoch
            learned=skills.grant_other_skill(db,1111,rid,epoch,rules,100008,7,expected_revision=0)
            assert learned.entries==((100008,7),)
            current=readonly(db,lambda:skills.enroll_local_prologue_other_skills(db,1111,rid,epoch,rules,policy,permit))
            assert current==learned
        new_epoch=store.acquire_lease(1111,rid)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN')
            current=readonly(db,lambda:skills.enroll_local_prologue_other_skills(db,1111,rid,new_epoch,rules,
                policy,replace(permit,original_epoch=new_epoch)))
            assert current.entries==((100008,7),) and current.revision==1
            assert skills.read_local_prologue_baseline_receipt(db,1111,rid,new_epoch,rules,policy).permit.original_epoch==epoch
    print('Designed-origin ledger preserves learned7 and original receipt across same/new lease without DML')


if __name__=='__main__':main()
