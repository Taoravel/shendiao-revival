"""Freeze NPC-owned changes atop the separately reviewed asset R2 inputs."""
import difflib
import hashlib
import json
from pathlib import Path
import shutil


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    root=Path(__file__).resolve().parents[1]
    provider=root/'evidence/reviews/equipment-identification-assets-20261024-r2'
    ready=json.loads((root/'evidence/equipment-identification-assets-ready.json').read_text(encoding='utf8'))
    assert ready['status']=='asset_provider_ready_fixed_r2'
    for name,digest in ready['production_sha256'].items():assert sha(root/name)==digest,name
    original=json.loads((provider/'manifest.json').read_text(encoding='utf8'))
    review=root/'evidence/reviews/npc-equipment-identification-20261024-r1'
    if review.exists():raise ValueError('Preserve existing NPC review; choose a new revision')
    current=review/'current';review.mkdir(parents=True)
    for name,digest in original['files'].items():
        if not name.startswith('current/'):continue
        source=provider/name;assert sha(source)==digest,name
        target=review/name;target.parent.mkdir(parents=True,exist_ok=True)
        if source.suffix in ('.bin','.pfs'):target.hardlink_to(source)
        else:shutil.copy2(source,target)
    owned=('npc_equipment_identification.py','verify_npc_identification_dialogue.py',
        'verify_npc_equipment_identification.py','verify_npc_identification_startup.py')
    changes=[];scope={}
    for name in owned:
        baseline=review/'base'/name;baseline.parent.mkdir(exist_ok=True);baseline.write_bytes(b'')
        target=current/'revival'/name;target.write_bytes((root/name).read_bytes())
        scope[name]={'base_source':'new NPC-owned file','base_sha256':sha(baseline),'current_sha256':sha(target)}
        changes.extend(difflib.unified_diff([],target.read_text(encoding='utf8').splitlines(True),
            fromfile='base/'+name,tofile='current/'+name))
    references=('evidence/equipment-identification-assets-ready.json','evidence/EQUIPMENT_IDENTIFICATION_CAS_INTEGRATION.md',
        'evidence/NPC_EQUIPMENT_IDENTIFICATION_DECISION.md','evidence/NPC_IDENTIFICATION_INTEGRATION.md',
        'design/npc-equipment-identification-v1.json','evidence/npc-identification-dialogue-baseline.json',
        'evidence/npc-equipment-identification-settlement-baseline.json',
        'evidence/npc-identification-startup-catalog-baseline.json')
    for name in references:
        target=review/'references'/name;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes((root/name).read_bytes())
    (review/'changes.diff').write_text(''.join(changes),encoding='utf8')
    manifest=dict(scope=scope,provider_review=str(provider),provider_production=ready['production_sha256'],
        provider_aggregate_sha256=ready['fixed_review']['aggregate_sha256'],
        comparison='non-Git four new NPC files versus exact empty bytes; asset delta remains separately reviewed',
        diff_sha256=sha(review/'changes.diff'),
        files={str(path.relative_to(review)).replace('\\','/'):sha(path) for path in review.rglob('*') if path.is_file()},
        verified_scope='NPC domain only; shared query/confirm registry and encrypted route not activated',
        excluded='full random result model, default unidentified generation, history migration, full inventory release closure')
    (review/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
    for name,row in scope.items():assert sha(root/name)==row['current_sha256'],name
    print('Frozen NPC review:',len(scope),'changed files;',len(manifest['files']),'fixed inputs')


if __name__=='__main__':main()
