"""Replay stopped orientation research before changing its production inputs."""
import hashlib
import json
from pathlib import Path
import runpy
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
EXPECTED={
    'research_npc_orientation.py':'50e0e19857d47e9db25bc7dbd4fa0a9d3c010453a708cf7ac8e29e7483a176ca',
    'evidence/NPC_ORIENTATION_NATIVE_RESEARCH.md':'c3801b00d9b54e8ec3f5c5751204addfc039e42b03b7e185b7a65374ffecfef2',
    'evidence/npc-orientation-native.json':'7b591890986641147fab2262abc44443bbc7c01b5ee8b63048d29f60c64f91cf',
    'evidence/npc-orientation-native.txt':'2c0f7d2e5764702a8ac0d4b31af890d53a9a6d191bcbf7624bf3987ddf1c49dc'}


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    for name,digest in EXPECTED.items():assert sha(ROOT/name)==digest,name
    old=json.loads((ROOT/'evidence/npc-orientation-native.json').read_text(encoding='utf8'))
    for name,digest in old['unchanged_workspace_source_sha256'].items():
        assert sha(ROOT/name)==digest,'Use preserved original source for historical replay: '+name
    watched={name:sha(ROOT/name) for name in (*old['historical_files_sha256'],
        *old['unchanged_workspace_source_sha256'],'evidence/native-image.bin')}
    runpy.run_path(str(ROOT/'research_npc_orientation.py'),run_name='__main__')
    for name,digest in EXPECTED.items():assert sha(ROOT/name)==digest,name
    for name,digest in watched.items():assert sha(ROOT/name)==digest,name
    output=dict(independent_parent_replay=True,case_count=102,exact_evidence_sha256=EXPECTED,
        preserved_source_and_historical_sha256=watched,original_zero_rows=13,
        production_changed=False,server_direction_policy_approved=False,
        entire_native_model_or_gui_verified=False,live_database_or_service_accessed=False)
    (ROOT/'evidence/npc-orientation-independent.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('PASS parent102 orientation replay;four output SHA and old19/10 plus production inputs unchanged')


if __name__=='__main__':main()
