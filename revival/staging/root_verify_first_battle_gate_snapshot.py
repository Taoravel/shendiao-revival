"""Independent natural-prefix replay of the explicitly isolated Task gate."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import runpy
import sys


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def files(directory):
    return {str(p.relative_to(directory)):sha(p) for p in directory.rglob('*') if p.is_file()}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--review',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    review=args.review.resolve(strict=True)
    output=args.output.resolve()
    root=Path(__file__).resolve().parents[2]
    record=json.loads((review/'manifest.json').read_text(encoding='utf-8'))
    source=Path(record['published_source_directory']).resolve(strict=True)
    base=source.parent
    if output.is_relative_to(review) or output.is_relative_to(base):
        raise ValueError('Independent output required')
    manifest=json.loads((base/'manifest.json').read_text(encoding='utf-8'))
    candidate=json.loads((base/'candidate.json').read_text(encoding='utf-8'))
    sets=((source,manifest['sha256']), (base/'harness',candidate['harness_sha256']),
          (base/'harness/workspace',candidate['workspace_sha256']),
          (review/'inputs',record['dependencies']))
    def verify():
        for directory,expected in sets:
            for name,wanted in expected.items():
                if sha(directory/name)!=wanted:
                    raise ValueError('Frozen input changed: '+str(directory/name))
        for name,entry in record['files'].items():
            if sha(review/'source'/name)!=entry['source_sha256']:
                raise ValueError('Task candidate changed: '+name)
    verify()
    before=files(review)
    harness=output/'harness'
    own_inputs={}
    for name,entry in record['files'].items():
        target=harness/name
        target.parent.mkdir(parents=True,exist_ok=True)
        raw=(review/'source'/name).read_bytes()
        if target.exists() and target.read_bytes()!=raw:
            raise ValueError('Preserve original independent harness: '+name)
        target.write_bytes(raw)
        own_inputs[name]=sha(target)
    policy='design/task-pve-ai8001-v1.json'
    target=harness/policy
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes((review/'inputs'/policy).read_bytes())
    own_inputs[policy]=sha(target)
    sys.path=[str(harness),str(base/'harness'),str(source)]+[s for s in sys.path
        if s and not Path(s).resolve().is_relative_to(root)]
    diagnostic=harness/'diagnose_growth_first_battle_runtime.py'
    spec=importlib.util.spec_from_file_location('diagnose_growth_first_battle_runtime',diagnostic)
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    # Only ROOT derivation needs the original filename. The actual code loaded
    # above is byte-identical frozen candidate code, never the hot workspace.
    virtual=root/'revival/diagnose_growth_first_battle_runtime.py'
    module.__file__=str(virtual)
    child=output/'natural-gate.json'
    sys.argv=[str(harness/'verify_task_first_battle.py'),'--source',str(source),
              '--report',str(child),'--expect-missing']
    try:
        runpy.run_path(sys.argv[0],run_name='__main__')
    finally:
        verify()
    result=json.loads(child.read_text(encoding='utf-8'))
    gate=result['isolated_new_admission_check']
    stable=before==files(review) and all(sha(harness/n)==h for n,h in own_inputs.items())
    passed=(len(gate['passed'])==5 and gate['participant_is_numeric_contract_fixture']
        and not result['first_battle_available'] and result['task_still_active']
        and not result['task_completed'] and stable)
    origins={}
    for name,loaded in tuple(sys.modules.items()):
        filename=getattr(loaded,'__file__',None)
        if not filename:
            continue
        path=Path(filename).resolve()
        if name==spec.name:
            origins[name]=dict(path=str(diagnostic),sha256=sha(diagnostic),virtual_filename=str(virtual))
            continue
        if path.is_relative_to(root):
            own=name=='__main__' and path==Path(__file__).resolve()
            if not own and not any(path.is_relative_to(d) for d in (harness,base/'harness',source)):
                raise ValueError('Unapproved application import: '+str(path))
            origins[name]=dict(path=str(path),sha256=sha(path))
    summary=dict(passed=bool(passed),gate_groups=gate['passed'],review=str(review),
        review_sha256=before,frozen_inputs_stable=stable,own_harness_sha256=own_inputs,
        base_input_counts=[len(expected) for _,expected in sets[:3]],
        actual_import_origins=origins,child_report=str(child),child_report_sha256=sha(child),
        root_harness_sha256=sha(Path(__file__)),candidate_injection_only=True,
        participant_is_numeric_contract_fixture=True,actual_ai_executed=False,
        shared_runtime_wired=False,live_database=False,live_socket=False,service_changed=False,
        native_gui_verified=False)
    (output/'verification.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',
        encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in summary.items() if k not in
        ('review_sha256','actual_import_origins','own_harness_sha256')},ensure_ascii=False))
    if not passed:
        raise SystemExit(1)


if __name__=='__main__':
    main()
