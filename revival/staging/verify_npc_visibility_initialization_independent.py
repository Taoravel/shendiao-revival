"""Parent replay of stopped original visibility research with exact evidence."""
import hashlib
import json
from pathlib import Path
import runpy
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
EVIDENCE={
    'research_npc_visibility_initialization.py':'3d330260addfa00d707094441ac995f5684163d085e9be0855d1e790df300c3c',
    'evidence/NPC_VISIBILITY_INITIALIZATION_RESEARCH.md':'2b6f3444a8429741035df6850a93887a5b819e7974f6b8c7e895c2ff4f372b58',
    'evidence/npc-visibility-initialization-native.json':'caac69e34b11dc55e194f7079fc0a7e2efde31cba71b60e4d559b963186413ba',
    'evidence/npc-visibility-initialization-native.txt':'54925df3d378bd95d2cb80091b595a348c9bf083f0392fcf04f11bd7709d1d9c'}


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    for name,digest in EVIDENCE.items():assert sha(ROOT/name)==digest,name
    names=('research_npc_submenu.py','native_inspect.py','pfs.py','bxml.py',
        'research_npc_disappear.py','evidence/NPC_DISAPPEAR_NATIVE_RESEARCH.md',
        'evidence/npc-disappear-native.json','evidence/native-image.bin',
        'catalogs/knight.gsp.npc.cnpcconfig.json','catalogs/knight.gsp.npc.cscenenpcconfig.json',
        'catalogs/knight.gsp.task.cmainmissioninfo.json','world_npcs.py','npc_lifecycle.py',
        'npc_gameplay.py','npc_recovery.py','npc_role_healing.py',
        'design/npc-services-v1.json','evidence/npc-equipment-identification-ready.json')
    inputs={name:sha(ROOT/name) for name in names}
    archive=ROOT.parent/'artres/config.pfs';archive_sha=sha(archive)
    runpy.run_path(str(ROOT/'research_npc_visibility_initialization.py'),run_name='__main__')
    for name,digest in EVIDENCE.items():assert sha(ROOT/name)==digest,name
    for name,digest in inputs.items():assert sha(ROOT/name)==digest,name
    assert sha(archive)==archive_sha
    native=json.loads((ROOT/'evidence/npc-visibility-initialization-native.json').read_text(encoding='utf8'))
    assert native['passed']==170
    assert len(native['initialization_cases'])==10 and len(native['visibility_cases'])==160
    assert len(native['display_lists'])==841 and len(native['sources'])==3
    assert native['scope']['whole_npc_initialization_executed'] is False
    assert native['scope']['display_task_qualification_executed'] is False
    assert native['scope']['server_lifecycle_verified'] is False
    result=dict(independent_parent_replay=True,passed=170,initialization_cases=10,visibility_cases=160,
        exact_evidence_sha256=EVIDENCE,preserved_inputs_sha256=inputs,
        original_config_pfs_sha256=archive_sha,original_27_evidence_preserved=True,
        production_and_identification_ready_unchanged=True,actual_shared_integration=False,
        native_gui_verified=False,whole_npc_initialization_verified=False,
        live_database_or_service_accessed=False)
    path=ROOT/'evidence/npc-visibility-initialization-independent.json'
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('PASS parent170 replay: four evidence SHA identical; old27/production/identification ready unchanged')


if __name__=='__main__':main()
