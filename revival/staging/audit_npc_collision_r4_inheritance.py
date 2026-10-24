"""Verify collision-only candidate preserves deployed NPC domains/wrappers."""
import ast
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RELEASE=ROOT/'runtime/deployments/world-collision-20261023T204238Z'


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def functions(path):
    tree=ast.parse(path.read_text(encoding='utf8'))
    return {node.name:ast.dump(node,include_attributes=False) for node in tree.body
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name!='prepare'}


def main():
    manifest=json.loads((RELEASE/'manifest.json').read_text(encoding='utf8'))
    base=Path(manifest['base_release'])
    assert base.name=='npc-loyalty-20261023T193742Z'
    old=json.loads((base/'manifest.json').read_text(encoding='utf8'))
    def selected(name):
        return ((name.startswith('npc_') and name.endswith('.py'))
            or (name.startswith('design/npc-') and name.endswith('.json'))
            or name in ('world_npcs.py','world_entity_protocol.py'))
    old_npc={name:digest for name,digest in old['sha256'].items() if selected(name)}
    new_npc={name:digest for name,digest in manifest['sha256'].items() if selected(name)}
    assert old_npc==new_npc,'Collision candidate added/removed/changed NPC domain inputs'
    for release,entries in ((base,old_npc),(RELEASE,new_npc)):
        for name,digest in entries.items():assert sha(release/'source'/name)==digest,name
    old_storage=base/'source/runtime_storage.py';new_storage=RELEASE/'source/runtime_storage.py'
    assert sha(old_storage)==old['sha256']['runtime_storage.py']
    assert sha(new_storage)==manifest['sha256']['runtime_storage.py']
    old_functions=functions(old_storage);new_functions=functions(new_storage)
    assert old_functions==new_functions,'Collision candidate changed storage behavior outside startup prepare'
    # The ordinary repair activation remains a later independent slice.
    assert '_require_unmigrated_operation' in old_functions['repair_role_equipment']
    result=dict(scope='static preservation of NPC domains and non-startup storage functions in collision r4',
        candidate=str(RELEASE),base=str(base),npc_input_count=len(new_npc),npc_inputs_sha256=new_npc,
        runtime_storage_non_prepare_functions_unchanged=len(new_functions),
        runtime_storage_base_sha256=sha(old_storage),runtime_storage_candidate_sha256=sha(new_storage),
        repair_guard_remains_for_later_slice=True,identification_not_added_by_this_slice=True,
        actual_current_process_not_inspected=True,actual_peer_tests_rerun_by_this_audit=False,
        source_modified=False,database_accessed=False,service_restarted=False,native_gui_verified=False)
    output=ROOT/'evidence/npc-collision-r4-inheritance-audit-20261024.json'
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(passed=True,npc_inputs=len(new_npc),unchanged_storage_functions=len(new_functions),
        report=str(output)),ensure_ascii=False))


if __name__=='__main__':main()
