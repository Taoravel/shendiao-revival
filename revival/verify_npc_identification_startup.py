"""Strict startup selection of the approved NPC fixed identification recipe."""
from pathlib import Path
from contextlib import closing
from dataclasses import FrozenInstanceError
import json
import tempfile
from accounts import AccountStore
from inspect_client import OUT,write_json
import npc_equipment_identification as identification
import npc_identification_query
import runtime_storage


def main():
    with tempfile.TemporaryDirectory(prefix='npc-identify-startup-') as directory:
        store=AccountStore(Path(directory)/'state.sqlite3');runtime_storage.prepare(store)
        npc_identification_query.prepare(store)
        policy=json.loads((OUT/'design/npc-equipment-identification-v1.json').read_text(encoding='utf8'))
        changed=dict(policy);changed['fee_catalog']='unsupported-fee-catalog'
        path=Path(directory)/'unsupported-policy.json';path.write_text(json.dumps(changed),encoding='utf8')
        try:identification.load_rules(store.npc_identification_query_rules,store.inventory_config,path=path)
        except ValueError:pass
        else:
            baseline=OUT/'evidence/npc-identification-startup-catalog-baseline.json'
            if not baseline.exists():write_json(baseline,{'failure':'Unsupported fee catalog policy accepted by fixed identification loader'})
            raise AssertionError('Unsupported fee catalog policy accepted by fixed identification loader')
        invalid=[]
        for key in ('npc_id','map_id','placement_id','service_id','confirmation_type',
                'confirmation_mode','confirmation_auxiliary_argument','dialogue_deadline_ms'):
            invalid.extend((key,value) for value in (None,True,'1',0.5,policy[key]+1))
        invalid.extend((key,'unsupported') for key in
            ('revision','query_policy','handler','fee_catalog','fee_currency','fee_purpose'))
        invalid.extend(('fee_keys',value) for value in (None,True,[],[True]+policy['fee_keys'][1:],policy['fee_keys']+[151]))
        with closing(store.connect()) as db:before=tuple(db.iterdump())
        for key,value in invalid:
            changed=dict(policy);changed[key]=value;path.write_text(json.dumps(changed),encoding='utf8')
            try:identification.prepare(store,path=path)
            except ValueError:pass
            else:raise AssertionError(f'Unsupported startup field accepted: {key}={value!r}')
        for value in (None,[],True):
            path.write_text(json.dumps(value),encoding='utf8')
            try:identification.prepare(store,path=path)
            except ValueError:pass
            else:raise AssertionError('Non-object identification policy accepted')
        with closing(store.connect()) as db:assert tuple(db.iterdump())==before
        services=store.npc_gameplay.services
        identification.prepare(store);rules=store.npc_identification_rules
        assert store.npc_gameplay.services is services
        assert rules.query_rules is store.npc_identification_query_rules
        assert rules.fees[1]==100 and rules.fees[50]==15000 and rules.fees.get(51) is None
        try:rules.dialogue_deadline_ms=3000000
        except FrozenInstanceError:pass
        else:raise AssertionError('Mutable NPC identification recipe')
        try:rules.fees[50]=100
        except TypeError:pass
        else:raise AssertionError('Mutable frozen original fee table')
        rejected=len(invalid)+4 # Three non-objects plus the initial real catalog RED.
    write_json(OUT/'evidence/npc-identification-startup-verification.json',{
        'passed':['strict approved recipe and original exact fee table frozen without registry change',
            'unsupported recipe rejects before schema writes; original51 has no fallback'],
        'invalid_startup_cases':rejected,'deployed':False,'live_database_modified':False})
    print('PASS identification startup:',rejected,'unsupported policy cases')


if __name__=='__main__':main()
