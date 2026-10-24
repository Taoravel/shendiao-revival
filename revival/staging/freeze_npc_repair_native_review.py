"""Fixed exact R1 BASE -> R2; published and reviewed Asset dependency closures."""
import difflib
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT/'evidence/reviews/npc-repair-columns-20261024-r1'
DEST=ROOT/'evidence/reviews/npc-repair-native-messages-20261024-r1'
CONTEXT=ROOT/'staging/npc-repair-native-context-v1'


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    assert not DEST.exists(),'Never overwrite a fixed review'
    old=json.loads((OLD/'manifest.json').read_text(encoding='utf8'))
    context=json.loads((CONTEXT/'manifest.json').read_text(encoding='utf8'))
    external=dict(old['external_inputs']);external.update(context['inputs'])
    external.update({str(CONTEXT/'context'/name):digest for name,digest in context['files'].items()})
    external[str(CONTEXT/'manifest.json')]=sha(CONTEXT/'manifest.json')
    for name,digest in external.items():assert sha(Path(name))==digest,name
    DEST.mkdir(parents=True)
    def copy(source,name):
        target=DEST/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
    copy(OLD/'current/npc_repairs.py','base/npc_repairs.py')
    copy(ROOT/'staging/npc-repair-column-candidate-v2/npc_repairs.py','current/npc_repairs.py')
    assert sha(DEST/'base/npc_repairs.py')=='e648d4f977a58d774d670e606a0f72e722c657e17f66f50413ff9170d227dd9b'
    # Existing R1 regressions are exact fixed test inputs, not new scope changes.
    for name in ('current/staging/verify_npc_repair_column_candidate.py',
            'current/fixtures/verify_npc_repair_resource_runtime.py',
            'current/fixtures/verify_npc_equipped_repair_runtime.py'):
        assert sha(OLD/name)==old['local_inputs'][name];copy(OLD/name,name)
    copy(ROOT/'staging/npc_repair_column_review_runner.py','verify_regression.py')
    copy(ROOT/'staging/npc_repair_native_review_runner.py','verify_native.py')
    owned=('staging/verify_npc_repair_native_messages.py','staging/run_npc_repair_native_check.py',
        'staging/prepare_npc_repair_native_context.py','staging/prepare_npc_repair_native_candidate.py',
        'evidence/NPC_REPAIR_NATIVE_MESSAGES_CANDIDATE.md')
    scope={};diff=[]
    for name in ('npc_repairs.py',)+owned:
        if name!='npc_repairs.py':copy(ROOT/name,'current/'+name)
        before=(DEST/'base'/name).read_text(encoding='utf8') if name=='npc_repairs.py' else ''
        after=(DEST/'current'/name).read_text(encoding='utf8')
        diff.extend(difflib.unified_diff(before.splitlines(True),after.splitlines(True),
            fromfile='base/'+name,tofile='current/'+name))
        scope[name]=dict(base_sha256=sha(DEST/'base'/name) if name=='npc_repairs.py' else hashlib.sha256(b'').hexdigest(),
            current_sha256=sha(DEST/'current'/name),base_is_new_empty=name!='npc_repairs.py')
    for name in ('AGENTS.md','GLOSSARY.md'):copy(ROOT.parent/name,'standards/'+name)
    for name in ('ARCHITECTURE.md','DESIGN_AUTHORITY.md'):copy(ROOT/name,'standards/'+name)
    copy(ROOT/'evidence/EQUIPMENT_NATIVE_COLUMNS_INTEGRATION.md','references/ASSET_INTEGRATION.md')
    (DEST/'changes.diff').write_text(''.join(diff),encoding='utf8')
    manifest=dict(workspace_root=str(ROOT),context_release=old['context_release'],scope=scope,
        comparison='non-Git exact E648 R1 bytes -> R2; added test/prep/spec files have empty BASE',
        source_scope='one NPC-owned inactive production module; shared and live untouched',
        spec='current/evidence/NPC_REPAIR_NATIVE_MESSAGES_CANDIDATE.md',
        methods='TDD real two-process RED/green; codebase-design existing real adapters; two-axis code-review',
        checks=old['checks'],external_inputs=external,local_inputs={},
        native_provider_selected_in_shared=False,root_final_policy_adopted=False,shared_deployment=False,
        asset_network_refresh_and_shop_query_fixed=False)
    manifest['local_inputs']={str(path.relative_to(DEST)).replace('\\','/'):sha(path)
        for path in DEST.rglob('*') if path.is_file()}
    (DEST/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('Frozen R2 review:',len(scope),'scope files;',len(manifest['local_inputs']),'local;',len(external),'external')
    print('Manifest SHA:',sha(DEST/'manifest.json'))


if __name__=='__main__':main()
