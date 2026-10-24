"""Run inherited task/exit acceptance against the final wild source snapshot."""
import hashlib
import json
from pathlib import Path
import runpy
import shutil
import sys

root=Path(__file__).resolve().parent
release=Path(sys.argv[1]).resolve()
script=sys.argv[2]
harnesses=('research_task_existing_quest.py','verify_task_master_card.py',
           'verify_first_master_runtime.py','verify_exit_initialization_runtime.py','verify_role_exit_native.py',
           'research_battle_damage.py','verify_battle_damage_presentation.py')
assert script in harnesses
assert release.parent==(root/'runtime/deployments').resolve()
source=release/'source'
manifest=json.loads((release/'manifest.json').read_text(encoding='utf-8'))
def verify():
    for name,expected in manifest['sha256'].items():
        assert hashlib.sha256((source/name).read_bytes()).hexdigest()==expected,name
verify()
checks=release/'acceptance'/script.removesuffix('.py');checks.mkdir(parents=True,exist_ok=False)
workspace=checks/'configuration';workspace.mkdir()
for name in ('design','catalogs','decoded','extracted','evidence'):
    if (source/name).exists():shutil.copytree(source/name,workspace/name)
hashes={}
for name in harnesses:
    shutil.copy2(root/name,checks/name)
    hashes[name]=hashlib.sha256((checks/name).read_bytes()).hexdigest()
sys.path[:0]=[str(source),str(checks)]
import inspect_client
inspect_client.ROOT=root.parent;inspect_client.OUT=workspace
sys.argv=[str(checks/script)]
runpy.run_path(str(checks/script),run_name='__main__')
modules={name:str(sys.modules[name].__file__) for name in
    ('game_runtime','runtime_storage','role_protocol','task_master_card','task_cart_dialogue') if name in sys.modules}
assert all(Path(path).parent==source for path in modules.values()),modules
verify()
result=dict(script=script,passed=True,production_modules=modules,harness_sha256=hashes,
            manifest_files_unchanged=len(manifest['sha256']),real_database_modified=False,native_gui_verified=False)
(checks/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
