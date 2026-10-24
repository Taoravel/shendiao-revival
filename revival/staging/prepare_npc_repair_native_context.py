"""Isolate the published repair dependencies plus the reviewed Asset adapter.

No workspace Inventory or shared/PVE changes enter this test context. Existing
stages and sealed reviews are never overwritten.
"""
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]
RELEASE=ROOT/'runtime/deployments/npc-repair-20261024T023920Z'
ASSET=ROOT/'evidence/reviews/equipment-native-columns-20261024-r1'
DEST=ROOT/'staging/npc-repair-native-context-v1'
R1=ROOT/'staging/npc-repair-column-candidate-v1/npc_repairs.py'
MODULES=('equipment_native_columns.py','equipment_gems.py','equipment_gem_storage.py',
    'equipment_gem_score.py','equipment_gem_score_storage.py')
CONFIG=('design/equipment-gems-v1.json','design/equipment-gem-score-v1.json',
    'catalogs/knight.gsp.item.citemattr.json','catalogs/knight.gsp.item.cgemeffect.json',
    'catalogs/knight.gsp.item.cgodweapon.json')


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    assert not DEST.exists(),'Preserve the existing isolated context'
    asset=json.loads((ASSET/'manifest.json').read_text(encoding='utf8'))
    release=json.loads((RELEASE/'manifest.json').read_text(encoding='utf8'))
    harness=json.loads((RELEASE/'candidate.json').read_text(encoding='utf8'))
    assert sha(R1)=='e648d4f977a58d774d670e606a0f72e722c657e17f66f50413ff9170d227dd9b'
    inputs={}
    def record(path,digest):
        assert sha(path)==digest,str(path)
        inputs[str(path)]=digest
    for name,digest in asset['files'].items():record(ASSET/name,digest)
    for folder,entries in ((RELEASE/'source',release['sha256']),
            (RELEASE/'harness',harness['harness_sha256']),
            (RELEASE/'harness',harness['harness_resource_sha256']),
            (RELEASE/'harness/workspace',harness['workspace_sha256'])):
        for name,digest in entries.items():record(folder/name,digest)
    record(R1,sha(R1))
    context=DEST/'context';context.mkdir(parents=True)
    origins={}
    def copy(path,name):
        target=context/name;target.parent.mkdir(parents=True,exist_ok=True)
        # Bytes are separate copies, so a later local edit cannot change a seal.
        shutil.copyfile(path,target);origins[name]=str(path)
    for name in release['sha256']:copy(RELEASE/'source'/name,name)
    for name in harness['harness_sha256']:copy(RELEASE/'harness'/name,name)
    for name in harness['harness_resource_sha256']:copy(RELEASE/'harness'/name,name)
    for name in MODULES+CONFIG:
        copy(ASSET/'current/revival'/name,name)
    copy(R1,'npc_repairs.py')
    assert sha(context/'inventory.py')==release['sha256']['inventory.py']
    result=dict(published_release=str(RELEASE),asset_fixed_review=str(ASSET),
        asset_manifest_sha256=sha(ASSET/'manifest.json'),inputs=inputs,
        files={name:sha(context/name) for name in origins},origins=origins,
        candidate_overlay_modules=MODULES,
        context_inventory='exact published; no workspace Inventory or PVE/shared edits',
        service_or_real_database_access=False)
    (DEST/'manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    for name,digest in inputs.items():assert sha(Path(name))==digest,name
    print('Prepared isolated published context:',len(origins),'files;',len(inputs),'guarded original inputs')


if __name__=='__main__':main()
