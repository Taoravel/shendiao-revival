"""New transfer replay probe against unchanged exact collision r3."""
import hashlib,json,runpy,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RELEASE=ROOT/'runtime/deployments/world-collision-20261023T202823Z'
record=json.loads((RELEASE/'candidate.json').read_text(encoding='utf-8'))
manifest=json.loads((RELEASE/'manifest.json').read_text(encoding='utf-8'))
def verify():
    for directory,hashes in ((RELEASE/'source',manifest['sha256']),
            (RELEASE/'harness',record['harness_sha256']),
            (RELEASE/'harness/workspace',record['workspace_sha256'])):
        for name,value in hashes.items():
            assert hashlib.sha256((directory/name).read_bytes()).hexdigest()==value,name
verify()
sys.path[:0]=[str(RELEASE/'harness'),str(RELEASE/'source')]
import inspect_client
inspect_client.ROOT=ROOT.parent;inspect_client.OUT=RELEASE/'harness/workspace'
try:
    try:runpy.run_path(str(ROOT/'verify_runtime_transfer_replays.py'),run_name='__main__')
    except ValueError as error:
        assert str(error) in ('Map membership expired','Position version mismatch'),str(error)
        result=dict(expected_red_reproduced=True,failure=type(error).__name__+': '+str(error),
            source=str(RELEASE/'source'),all_frozen_inputs_preserved=True,
            live_service_changed=False,native_gui_verified=False)
    else:raise AssertionError('Historical transfer result did not expose the frozen r3 projection bug')
finally:verify()
(ROOT/'evidence/world-transfer-replay-r3-baseline.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(result)
