"""Bind the new public join feedback to the exact currently approved BASE."""
import argparse,hashlib,json,runpy,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'runtime/deployments/npc-repair-20261024T023920Z'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--case',choices=('duplicate','conflict'),required=True)
    case=parser.parse_args().case
    record=json.loads((BASE/'candidate.json').read_text(encoding='utf-8'))
    manifest=json.loads((BASE/'manifest.json').read_text(encoding='utf-8'))
    def verify():
        for folder,hashes in ((BASE/'source',manifest['sha256']),
                (BASE/'harness',record['harness_sha256']),
                (BASE/'harness/workspace',record['workspace_sha256'])):
            for name,value in hashes.items():
                if hashlib.sha256((folder/name).read_bytes()).hexdigest()!=value:raise ValueError('Frozen input changed: '+name)
    verify()
    output=ROOT/'evidence/member-binding-runtime-baseline-20261024';output.mkdir(exist_ok=True)
    probe=output/'verify_runtime_member_join_admission.py';raw=(ROOT/probe.name).read_bytes()
    if probe.exists() and probe.read_bytes()!=raw:raise ValueError('Preserve the original baseline probe')
    probe.write_bytes(raw)
    sys.path[:0]=[str(BASE/'harness'),str(BASE/'source')]
    import inspect_client
    inspect_client.ROOT=ROOT.parent;inspect_client.OUT=BASE/'harness/workspace'
    sys.argv=[str(probe),'--case',case]
    failure=None
    try:
        try:runpy.run_path(str(probe),run_name='__main__')
        except AssertionError as error:failure=str(error)
    finally:verify()
    if failure!=case+' join revoked the current playable member':raise AssertionError(failure)
    report=dict(expected_red_reproduced=True,case=case,failure=failure,release=str(BASE),
        production_inputs_verified=len(manifest['sha256']),harness_inputs_verified=len(record['harness_sha256']),
        config_inputs_verified=len(record['workspace_sha256']),probe_sha256=hashlib.sha256(raw).hexdigest(),
        live_service_changed=False,live_database_accessed=False)
    (output/(case+'-red.json')).write_text(json.dumps(report,indent=2),encoding='utf-8');print(report)


if __name__=='__main__':main()
