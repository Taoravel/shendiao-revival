"""Freeze direction domain diff atop the actual approved repair dependencies."""
import difflib
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]
REVIEW=ROOT/'evidence/reviews/npc-placement-direction-20261024-r1'
RELEASE=ROOT/'runtime/deployments/npc-repair-20261024T023920Z'
SCOPE=('world_npcs.py','npc_lifecycle.py','verify_npc_placement_direction.py')
CHECKS=('verify_npc_placement_direction.py','verify_world_npcs.py','verify_npc_lifecycle.py',
    'verify_npc_motion.py','verify_npc_lifecycle_rules.py','verify_npc_cell_interaction.py')


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    assert (REVIEW/'base').is_dir() and not (REVIEW/'manifest.json').exists()
    current=REVIEW/'current';source=current/'revival';source.mkdir(parents=True,exist_ok=True)
    record=json.loads((RELEASE/'candidate.json').read_text(encoding='utf8'))
    manifest=json.loads((RELEASE/'manifest.json').read_text(encoding='utf8'))
    def put(src,dst,expected=None):
        if expected is not None:assert sha(src)==expected,str(src)
        dst.parent.mkdir(parents=True,exist_ok=True)
        if dst.exists():
            if sha(dst)==sha(src):return
            if dst.suffix in ('.bin','.pfs'):
                assert dst.resolve().is_relative_to(current)
                dst.unlink()  # Detach this snapshot link; never overwrite its source inode.
        if src.suffix in ('.bin','.pfs') and not dst.exists():dst.hardlink_to(src)
        else:shutil.copy2(src,dst)
    # Only frozen non-Python fixture resources; published production takes
    # precedence over overlapping fixture copies. No workspace database/log.
    for name,digest in record['workspace_sha256'].items():
        if Path(name).suffix in ('.py','.sqlite3','.log') or name.startswith('runtime/'):continue
        put(RELEASE/'harness/workspace'/name,source/name,digest)
    for name,digest in manifest['sha256'].items():put(RELEASE/'source'/name,source/name,digest)
    helper_overrides={}
    for name,digest in record['harness_sha256'].items():
        if name in manifest['sha256'] and digest!=manifest['sha256'][name]:
            assert name.startswith(('research_','verify_')),name
            helper_overrides[name]=dict(production_snapshot_sha256=manifest['sha256'][name],
                explicit_test_helper_sha256=digest)
        put(RELEASE/'harness'/name,source/name,digest)
    for name,digest in record['harness_resource_sha256'].items():put(RELEASE/'harness'/name,source/name,digest)
    for archive in ('config.pfs','map.pfs'):put(ROOT.parent/'artres'/archive,current/'artres'/archive)
    put(ROOT.parent/'AGENTS.md',current/'AGENTS.md')
    for name in ('ARCHITECTURE.md','DESIGN_AUTHORITY.md'):put(ROOT/name,source/name)
    # Explicit domain-only override: strict Life was already reviewed as8a,
    # but remains absent from active shared control in the approved release.
    put(ROOT/'design/npc-lifecycle-v1.json',source/'design/npc-lifecycle-v1.json')
    for name in set(SCOPE)|set(CHECKS):put(ROOT/name,source/name)
    changes=[];scope={}
    for name in SCOPE:
        baseline=REVIEW/'base'/name
        scope[name]=dict(base_sha256=sha(baseline),current_sha256=sha(source/name))
        changes.extend(difflib.unified_diff(baseline.read_text(encoding='utf8').splitlines(True),
            (source/name).read_text(encoding='utf8').splitlines(True),fromfile='base/'+name,tofile='current/'+name))
    refs=('evidence/NPC_PLACEMENT_DIRECTION_INTEGRATION.md','evidence/NPC_ORIENTATION_NATIVE_RESEARCH.md',
        'evidence/npc-orientation-independent.json','evidence/npc-orientation-native.json',
        'evidence/WORLD_NPC_DIRECTION_NATIVE.md','evidence/WORLD_NPC_SHAPE_DIRECTION_NATIVE.md',
        'evidence/WORLD_NEXT_INTEGRATION_GAPS.md','evidence/npc-placement-direction-baseline.json',
        'evidence/npc-placement-direction-lifecycle-baseline.json','evidence/npc-placement-direction-range-baseline.json',
        'evidence/npc-lifecycle-startup-ready.json')
    for name in refs:put(ROOT/name,REVIEW/'references'/name)
    (REVIEW/'changes.diff').write_text(''.join(changes),encoding='utf8')
    result=dict(scope=scope,context_release=str(RELEASE),checks=CHECKS,
        explicit_research_helper_overrides=helper_overrides,
        comparison='non-Git exact177f Scene and reviewed8a Life; new test empty base',
        active_release_lifecycle_sha256=manifest['sha256']['npc_lifecycle.py'],
        reviewed_domain_lifecycle_baseline_sha256=scope['npc_lifecycle.py']['base_sha256'],
        static_publishable_input='world_npcs.py; actual release candidate and review still required',
        lifecycle_activated=False,member_or_identification_activated=False,
        diff_sha256=sha(REVIEW/'changes.diff'),
        files={str(p.relative_to(REVIEW)).replace('\\','/'):sha(p) for p in REVIEW.rglob('*') if p.is_file()})
    for name,row in scope.items():assert sha(ROOT/name)==row['current_sha256'],name
    for folder,entries in ((RELEASE/'source',manifest['sha256']),
            (RELEASE/'harness',record['harness_sha256']),
            (RELEASE/'harness/workspace',record['workspace_sha256']),
            (RELEASE/'harness',record['harness_resource_sha256'])):
        for name,digest in entries.items():assert sha(folder/name)==digest,name
    (REVIEW/'manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('Frozen direction domain:',len(scope),'scope files;',len(result['files']),'inputs')


if __name__=='__main__':main()
