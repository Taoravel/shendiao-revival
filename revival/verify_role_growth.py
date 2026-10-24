"""Necessary ordinary growth/points checks using temporary local accounts."""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
import json
import tempfile
from accounts import AccountStore
from inspect_client import OUT
from progression import credit_experience,read_experience
from progression_protocol import decode_level_up_request
from role_growth import (load_growth_rules,prepare_growth_storage,initialize_growth,
    read_growth,plan_growth_credit,plan_potential_allocation,apply_growth_plan,request_manual_level,
    request_potential_allocation)


def main():
    rules = load_growth_rules()
    with tempfile.TemporaryDirectory() as directory:
        accounts = AccountStore(Path(directory)/'growth.sqlite3')
        role = accounts.create_role(1111,'成长基线',11,1010109)
        epoch = accounts.acquire_lease(1111,role['id'])
        with closing(accounts.connect()) as db:
            prepare_growth_storage(db)
        with closing(accounts.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            state = initialize_growth(db,1111,role['id'],epoch,rules,expected_level=1,free_points=0)
            example = plan_growth_credit(state,150,rules).after
            assert (example.level,example.experience,example.automatic_points,example.free_points) == (2,61,(1,1,1,1,1),5)
            assert (plan_growth_credit(state,270,rules).after.level,plan_growth_credit(state,270,rules).after.experience) == (2,181)
            from role_growth import plan_manual_level
            for terminal in (155,1001):
                try: plan_manual_level(replace(state,level=terminal),0,rules)
                except ValueError: pass
                else: raise AssertionError('Terminal/special level advanced as ordinary')
            enough = sum(rules.costs[i] for i in range(1,11))
            credited = credit_experience(db,1111,role['id'],enough,rules)
            assert (credited.level,credited.experience) == (10,5781)
            advanced = read_growth(db,1111,role['id'])
            assert advanced.automatic_points == (9,9,9,9,9) and advanced.free_points == 45
            manual = request_manual_level(db,1111,role['id'],epoch,decode_level_up_request(bytes(4)),'manual-1',rules)
            assert (manual.level,manual.experience,manual.free_points) == (11,0,50)
            allocate = plan_potential_allocation(manual,(2,0,0,0,3),manual.revision,rules)
            allocated = apply_growth_plan(db,1111,role['id'],epoch,allocate,'allocate-1',rules)
            assert allocated.allocated_points == (2,0,0,0,3) and allocated.free_points == 45
            assert request_manual_level(db,1111,role['id'],epoch,0,'manual-1',rules) == manual
            assert read_growth(db,1111,role['id']) == allocated
            first=request_potential_allocation(db,1111,role['id'],epoch,(1,0,0,0,0),'points-1',rules)
            later=request_potential_allocation(db,1111,role['id'],epoch,(0,0,0,0,1),'points-2',rules)
            assert later.free_points==first.free_points-1
            assert request_potential_allocation(db,1111,role['id'],epoch,(1,0,0,0,0),'points-1',rules)==later
            try:
                request_potential_allocation(db,1111,role['id'],epoch,(0,1,0,0,0),'points-1',rules)
                raise AssertionError('Allocation request changed intent')
            except ValueError as error:
                assert 'different intent' in str(error)
            allocated=later
        try:
            with closing(accounts.connect()) as db, db:
                db.execute('BEGIN IMMEDIATE')
                credit_experience(db,1111,role['id'],100,rules)
                raise RuntimeError('controlled caller rollback')
        except RuntimeError:
            pass
        with closing(accounts.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            assert read_growth(db,1111,role['id']) == allocated
            for field in (1,1001):
                try: request_manual_level(db,1111,role['id'],epoch,field,'bad-mode',rules)
                except ValueError: pass
                else: raise AssertionError('Unknown mode accepted')
            try: request_manual_level(db,1111,role['id'],epoch,0,'insufficient',rules)
            except ValueError as error: assert str(error)=='Insufficient experience'
            else: raise AssertionError('Level advanced without experience')
            assert read_growth(db,1111,role['id']) == allocated
            try: initialize_growth(db,1111,role['id'],epoch,rules,expected_level=11,free_points=999)
            except ValueError: pass
            else: raise AssertionError('Existing baseline reset')
        old = accounts.create_role(1111,'未定阶段',11,1010109)
        with closing(accounts.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            assert credit_experience(db,1111,old['id'],150).level == 1
            assert read_experience(db,1111,old['id']).experience == 150
        report = {'passed':['original threshold examples 150->L2/61 and 270->L2/181',
            'automatic advancement stops at 10; original L10 cost 5781 consumed once manually',
            'automatic five-stat increments/free points and versioned allocation',
            'successful request replay after allocation does not replay upgrades',
            'potential request replay after later allocation returns current state; changed deltas reject without reallocation',
            'unknown mode/insufficient XP/baseline reset rejected; caller rollback preserves ledger',
            'uninitialized role preserves level and old experience-bank behavior'],
            'policy':'designed ordinary phase only','live_client_tested':False}
    (OUT/'evidence/role-growth-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__ == '__main__': main()
