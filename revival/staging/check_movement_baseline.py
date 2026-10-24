"""Run the strengthened joined=true drain counterexample against exact live BASE."""
import hashlib
import json
from pathlib import Path
import runpy
import sys

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'runtime/deployments/npc-loyalty-20261023T193742Z'
manifest=json.loads((BASE/'manifest.json').read_text(encoding='utf-8'))
def verify():
    for name,value in manifest['sha256'].items():
        assert hashlib.sha256((BASE/'source'/name).read_bytes()).hexdigest()==value,name
verify()
sys.path[:0]=[str(BASE/'source'),str(ROOT)]
import inspect_client
inspect_client.ROOT=ROOT.parent
inspect_client.OUT=BASE/'source'
try:
    try:runpy.run_path(str(ROOT/'verify_runtime_movement_lifecycle.py'),run_name='__main__')
    except AssertionError as error:
        assert str(error)=='Movement accepted before exact scene drain',str(error)
        result=dict(expected_red_reproduced=True,joined_true=True,failure=str(error),
            baseline_source=str(BASE/'source'),production_hashes_preserved=len(manifest['sha256']),
            live_service_changed=False,native_gui_verified=False)
    else:raise AssertionError('Published BASE unexpectedly passed the new lifecycle gate')
finally:verify()
(ROOT/'evidence/world-movement-joined-drain-baseline.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(result)
