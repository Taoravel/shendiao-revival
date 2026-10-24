"""Accept the precise repair wrapper delta and replay the original actual owner.

No live DB/service access. Frozen production, helpers and catalogs remain intact;
only external verification report sinks are redirected to an NPC-owned folder.
"""
import argparse
import ast
import copy
import hashlib
import json
from pathlib import Path
import runpy
import sys
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
PROBE='verify_npc_repair_resource_runtime.py'


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def verify_delta(base,source):
    original=ast.parse((base/'source/runtime_storage.py').read_text(encoding='utf8'))
    actual=ast.parse((source/'runtime_storage.py').read_text(encoding='utf8'))
    old=next(n for n in original.body if isinstance(n,ast.FunctionDef) and n.name=='repair_role_equipment')
    new=next(n for n in actual.body if isinstance(n,ast.FunctionDef) and n.name==old.name)
    expected=copy.deepcopy(old)
    guards=[n for n in expected.body if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call)
        and isinstance(n.value.func,ast.Name) and n.value.func.id=='_require_unmigrated_operation']
    assert len(guards)==1,'Expected exact published temporary repair gate'
    expected.body.remove(guards[0])
    call=expected.body[-1].value
    assert isinstance(expected.body[-1],ast.Return) and isinstance(call,ast.Call)
    assert isinstance(call.func,ast.Attribute) and call.func.attr=='repair'
    assert isinstance(call.func.value,ast.Name) and call.func.value.id=='npc_repairs'
    assert not call.keywords
    call.keywords=ast.parse('f(resource_rules=accounts.resource_rules, '
        'equipment_rules=accounts.equipment_attribute_rules)').body[0].value.keywords
    def normalized(node):
        value=copy.deepcopy(node)
        for entry in ast.walk(value):
            if isinstance(entry,ast.Call):entry.keywords.sort(key=lambda k:k.arg or '')
        return ast.dump(value,include_attributes=False)
    assert normalized(new)==normalized(expected),'Repair delta exceeds the approved gate/dependency change'
    actual.body[actual.body.index(new)]=old
    assert ast.dump(actual,include_attributes=False)==ast.dump(original,include_attributes=False),(
        'Other storage imports/constants/functions changed')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--candidate-record',required=True,type=Path)
    args=parser.parse_args();record=json.loads(args.candidate_record.read_text(encoding='utf8'))
    release=Path(record['release']).resolve();source,harness=release/'source',release/'harness'
    assert release.is_relative_to(ROOT/'runtime/deployments')
    manifest=json.loads((release/'manifest.json').read_text(encoding='utf8'))
    base=Path(manifest['base_release']).resolve()
    assert base.name=='world-collision-20261023T204238Z'
    prior=json.loads((base/'manifest.json').read_text(encoding='utf8'))
    assert sha(base/'source/runtime_storage.py')==prior['sha256']['runtime_storage.py']
    assert set(prior['sha256'])==set(manifest['sha256'])
    changes=[name for name,digest in manifest['sha256'].items() if prior['sha256'][name]!=digest]
    assert changes==['runtime_storage.py'],changes
    def verify():
        for name,digest in manifest['sha256'].items():assert sha(source/name)==digest,name
        assert sha(release/'run_release.py')==manifest['runner_sha256']
        for name,digest in record['harness_sha256'].items():assert sha(harness/name)==digest,name
        for name,digest in record.get('harness_resource_sha256',{}).items():assert sha(harness/name)==digest,name
        for name,digest in record['workspace_sha256'].items():assert sha(harness/'workspace'/name)==digest,name
    verify();verify_delta(base,source)
    expected_probe=sha(ROOT/PROBE)
    assert record['harness_sha256'].get(PROBE)==expected_probe,'Original red probe must remain exact'
    sys.path[:0]=[str(harness),str(source)]
    import inspect_client
    inspect_client.ROOT=ROOT.parent;inspect_client.OUT=harness/'workspace'
    output=ROOT/'evidence'/('npc-repair-candidate-owner-'+release.name)
    output.mkdir(exist_ok=True)
    original_write=Path.write_text
    def sink(path,data,*args,**kwargs):
        if path.parent==inspect_client.OUT/'evidence' and path.name.startswith('npc-repair-resource-runtime-'):
            return original_write(output/path.name,data,*args,**kwargs)
        if path.is_relative_to(release):raise AssertionError('Unexpected immutable candidate write: '+str(path))
        return original_write(path,data,*args,**kwargs)
    sys.argv=[str(harness/PROBE)]
    with patch.object(Path,'write_text',sink):runpy.run_path(str(harness/PROBE),run_name='__main__')
    verify()
    origins={}
    for name,module in tuple(sys.modules.items()):
        file=getattr(module,'__file__',None)
        if not file or name=='__main__':continue
        path=Path(file).resolve()
        if ROOT in path.parents:
            assert path.parent in (source,harness),str(path)
            origins[name]=str(path)
    result=dict(candidate=str(release),base=str(base),production_changed_inputs=changes,
        exact_approved_repair_ast_delta=True,source_inputs_verified=len(manifest['sha256']),
        harness_inputs_verified=len(record['harness_sha256']),
        config_inputs_verified=len(record['workspace_sha256']),original_probe_sha256=expected_probe,
        actual_project_module_origins=origins,actual_known_profile_owner_and_paid_current_only_passed=True,
        output_sinks_only_redirected=True,live_database_modified=False,live_service_changed=False,
        native_gui_verified=False,other_candidate_regressions_claimed=False)
    (output/'owner-acceptance.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('PASS exact repair-only candidate and original actual owner:',release.name)


if __name__=='__main__':main()
