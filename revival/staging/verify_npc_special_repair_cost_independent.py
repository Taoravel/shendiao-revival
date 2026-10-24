"""Parent replay of stopped research, preserving exact evidence bytes."""
import hashlib
import json
from pathlib import Path
import runpy
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
FILES={'research_npc_special_repair_cost.py':'459e0463fabfa5e53e487250bd7c880a7b337a4c0bc87e7838eaaf9a7fa47078',
    'evidence/NPC_SPECIAL_REPAIR_COST_RESEARCH.md':'ec45ef4fe98ac23916dd78162093fc2048b73ff10304066b7fc8687ecb43b2d3',
    'evidence/npc-special-repair-cost-native.json':'ac36e5ac8499384b208f34b88719ae7fd8240e9c6cf5587c551178885cfe899c',
    'evidence/npc-special-repair-cost-native-disassembly.txt':'38e3e63ddffc171675fcfc2415d7113fb74b4a021e6f482ca623420a3d5f37fb'}


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    for name,digest in FILES.items():assert sha(ROOT/name)==digest,name
    names=('research_equipment_detail_full.py','native_inspect.py','pfs.py','bxml.py',
        'evidence/native-image.bin',*(f'catalogs/knight.gsp.item.{n}.json' for n in (
            'citemattr','cequipeffect','cequipprefixconfig','cgodweapon')))
    inputs={name:sha(ROOT/name) for name in names}
    runpy.run_path(str(ROOT/'research_npc_special_repair_cost.py'),run_name='__main__')
    for name,digest in FILES.items():assert sha(ROOT/name)==digest,name
    for name,digest in inputs.items():assert sha(ROOT/name)==digest,name
    report=json.loads((ROOT/'evidence/npc-special-repair-cost-native.json').read_text(encoding='utf8'))
    assert report['passed']==656 and len(report['sample_items'])==12
    assert {row['tag'] for row in report['sample_items']}==set(range(6,12))
    assert len(report['diagnostic_cases'])==8
    for name,digest in report['historical_96_files_sha256'].items():assert sha(ROOT/name)==digest,name
    result=dict(passed=656,independent_parent_replay=True,evidence_sha256=FILES,
        additional_inputs_sha256=inputs,original_96_evidence_preserved=True,
        production_or_policy_changed=False,shared_or_asset_model_implemented=False,
        native_gui_verified=False,live_database_accessed=False)
    path=ROOT/'evidence/npc-special-repair-cost-independent.json'
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('PASS parent656 replay; four evidence SHA and original96 unchanged')


if __name__=='__main__':main()
