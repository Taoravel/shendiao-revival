"""Fixed review seam for the first full-address factory slice only."""
import difflib,hashlib,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
review=ROOT/'evidence/reviews/shared-private-map-factory-20261023'
current=review/'current';current.mkdir(exist_ok=False)
names=('game_runtime.py','verify_runtime_private_map_factory.py','verify_runtime_map_address_identity.py')
manifest={}
for name in names:
    shutil.copy2(ROOT/name,current/name)
    manifest[name]=hashlib.sha256((current/name).read_bytes()).hexdigest()
before=review/'base/game_runtime.py'
manifest['base/game_runtime.py']=hashlib.sha256(before.read_bytes()).hexdigest()
(review/'changes.diff').write_text(''.join(difflib.unified_diff(before.read_text(encoding='utf-8').splitlines(True),
    (current/'game_runtime.py').read_text(encoding='utf-8').splitlines(True),fromfile='base/game_runtime.py',
    tofile='current/game_runtime.py')),encoding='utf-8')
(review/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps(manifest))
