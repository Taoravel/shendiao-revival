"""Supply exact pinned resources for dependencies using __file__ paths."""
from pathlib import Path
import hashlib,json,shutil
root=Path(__file__).resolve().parents[1]
review=root/'evidence/reviews/guild-maintenance-20261024T051526Z'
resources=json.loads((review/'resource-inputs.json').read_text(encoding='utf-8'))
for name,record in resources.items():
    source=root/name;target=review/'source'/name
    assert hashlib.sha256(source.read_bytes()).hexdigest()==record['sha256']
    target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
runner=review/'verify_fixed_candidate.py';text=runner.read_text(encoding='utf-8')
check="for name,record in resources.items():assert sha(root/name)==record['sha256'],name"
text=text.replace(check,check+"\nfor name,record in resources.items():assert sha(source/name)==record['sha256'],'Pinned resource alias: '+name")
runner.write_text(text,encoding='utf-8')
print(json.dumps(dict(resource_aliases=len(resources),runner_sha256=hashlib.sha256(runner.read_bytes()).hexdigest())))
