"""Freeze published BASE, observed bad-source prototype and final query scope."""
import difflib
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]
RELEASE=ROOT/'runtime/deployments/npc-repair-20261024T023920Z'
DEST=ROOT/'evidence/reviews/npc-buyback-query-20261024-r1'


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    assert not DEST.exists(),'Preserve sealed reviews'
    published=json.loads((RELEASE/'manifest.json').read_text(encoding='utf8'))
    helpers=json.loads((RELEASE/'candidate.json').read_text(encoding='utf8'));external={}
    for directory,entries in ((RELEASE/'source',published['sha256']),
            (RELEASE/'harness',helpers['harness_sha256']),
            (RELEASE/'harness',helpers['harness_resource_sha256']),
            (RELEASE/'harness/workspace',helpers['workspace_sha256'])):
        external.update({str(directory/name):digest for name,digest in entries.items()})
    for name in ('npc_shop_sales.py','evidence/npc-repair-native-messages-ready.json',
            'evidence/npc-repair-column-candidate-ready.json','evidence/npc-equipment-identification-ready.json',
            'evidence/npc-placement-direction-ready.json','evidence/NPC_SHOP_CATALOG_NATIVE_RESEARCH.md',
            'evidence/npc-shop-catalog-native.json','evidence/NPC_BUYBACK_QUOTE_NATIVE_RESEARCH.md',
            'evidence/npc-buyback-quote-native.json','evidence/npc-buyback-current-price-frame.json'):
        external[str(ROOT/name)]=sha(ROOT/name)
    for name,digest in external.items():assert sha(Path(name))==digest,name
    DEST.mkdir(parents=True)
    def copy(source,name):
        target=DEST/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
    copy(RELEASE/'source/npc_shop_sales.py','base/npc_shop_sales.py')
    copy(ROOT/'staging/npc-buyback-query-candidate-v2/npc_shop_sales.py','current/npc_shop_sales.py')
    copy(ROOT/'staging/npc-buyback-query-candidate-v1/prototype-bad-record-red.py','prototypes/npc_shop_sales_bad_record.py')
    assert sha(DEST/'base/npc_shop_sales.py')=='5bfbc44403d9ab2e3aa93dc0cf6304f20e74e7a1b5a111e757fc04bfb6e01058'
    assert sha(DEST/'prototypes/npc_shop_sales_bad_record.py')=='4fc6504f06dbeb6493cf9c24c935317d01bd87076ed2ee8815b659b16e8ffb19'
    owned=('staging/verify_npc_buyback_query.py','staging/prepare_npc_buyback_query_candidate.py',
        'evidence/NPC_BUYBACK_QUERY_CANDIDATE.md')
    for name in owned:copy(ROOT/name,'current/'+name)
    copy(ROOT/'staging/npc_buyback_query_review_runner.py','verify_frozen.py')
    for name in ('AGENTS.md','GLOSSARY.md'):copy(ROOT.parent/name,'standards/'+name)
    for name in ('ARCHITECTURE.md','DESIGN_AUTHORITY.md'):copy(ROOT/name,'standards/'+name)
    diff=[];scope={}
    for name in ('npc_shop_sales.py',)+owned:
        before=(DEST/'base'/name).read_text(encoding='utf8') if name=='npc_shop_sales.py' else ''
        after=(DEST/'current'/name).read_text(encoding='utf8')
        diff.extend(difflib.unified_diff(before.splitlines(True),after.splitlines(True),
            fromfile='base/'+name,tofile='current/'+name))
        scope[name]=dict(base_sha256=sha(DEST/'base'/name) if name=='npc_shop_sales.py' else hashlib.sha256(b'').hexdigest(),
            current_sha256=sha(DEST/'current'/name),base_empty=name!='npc_shop_sales.py')
    (DEST/'changes.diff').write_text(''.join(diff),encoding='utf8')
    manifest=dict(workspace_root=str(ROOT),release=str(RELEASE),scope=scope,
        comparison='non-Git actual published5bf BASE; new test/preparer/spec empty BASE; observed actual4fc failing prototype retained',
        spec='current/evidence/NPC_BUYBACK_QUERY_CANDIDATE.md',
        checks=('missing_query_red','bad_record_red','readonly_query','legacy_sale_runtime'),
        local_inputs={},external_inputs=external,shared_or_policy_or_deployment_changed=False,
        source='original query4 buyback/c0434 codec verified; service2 read association and response choice proposed server adoption')
    manifest['local_inputs']={str(path.relative_to(DEST)).replace('\\','/'):sha(path) for path in DEST.rglob('*') if path.is_file()}
    (DEST/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('Frozen query review:',len(manifest['local_inputs']),'local;',len(external),'external')
    print('Manifest SHA:',sha(DEST/'manifest.json'))


if __name__=='__main__':main()
