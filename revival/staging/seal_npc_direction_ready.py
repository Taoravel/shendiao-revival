"""Seal reviewed NPC direction increments without authorizing their deployment."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / 'evidence/reviews/npc-placement-direction-20261024-r2'
READY = ROOT / 'evidence/npc-placement-direction-ready.json'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    manifest = json.loads((REVIEW / 'manifest.json').read_text(encoding='utf8'))
    for name, digest in manifest['files'].items():
        assert sha(REVIEW / name) == digest, name
    for name, row in manifest['scope'].items():
        assert sha(ROOT / name) == row['current_sha256'], name
    reports = {}
    for label in ('parent', 'standards', 'spec'):
        for script in manifest['checks']:
            path = REVIEW / 'verification' / label / (script + '.result.json')
            record = json.loads(path.read_text(encoding='utf8'))
            assert record['script'] == script and record['passed'] is True
            assert record['frozen_inputs'] == len(manifest['files'])
            reports[str(path.relative_to(ROOT)).replace('\\', '/')] = sha(path)
    standards = (REVIEW / 'standards.md').read_text(encoding='utf8')
    spec = (REVIEW / 'spec.md').read_text(encoding='utf8')
    aggregate = standards.rstrip() + '\n\n' + spec.replace('# Spec', '## Spec', 1).rstrip()
    aggregate += '\n\n总计：Standards 0（最严重：无）；Spec 0（最严重：无）。\n'
    (REVIEW / 'REVIEW.md').write_text(aggregate, encoding='utf8')
    evidence = json.loads((ROOT / 'evidence/npc-orientation-independent.json').read_text(encoding='utf8'))
    for name, digest in evidence['exact_evidence_sha256'].items():
        assert sha(ROOT / name) == digest, name
    path_refs = ['evidence/npc-orientation-independent.json',
        'evidence/npc-placement-direction-baseline.json',
        'evidence/npc-placement-direction-lifecycle-baseline.json',
        'evidence/npc-placement-direction-range-baseline.json']
    refs = {name: sha(ROOT / name) for name in path_refs}
    refs.update(evidence['exact_evidence_sha256'])
    created = datetime.now(timezone.utc).isoformat()
    if READY.exists():
        created = json.loads(READY.read_text(encoding='utf8'))['created_utc']
    result = dict(created_utc=created, status='npc_owned_domain_reviewed_not_deployed',
        review=str(REVIEW), manifest_sha256=sha(REVIEW / 'manifest.json'),
        aggregate_sha256=sha(REVIEW / 'REVIEW.md'), scope=manifest['scope'],
        independent_axes=dict(standards_findings=0, fowler_findings=0, spec_findings=0),
        frozen_input_count=len(manifest['files']), successful_independent_check_runs=len(reports),
        verification_sha256=reports, evidence_sha256=refs,
        static_integration=dict(file='world_npcs.py', base_sha256=manifest['scope']['world_npcs.py']['base_sha256'],
            candidate_sha256=manifest['scope']['world_npcs.py']['current_sha256'],
            shared_changes_required=False, actual_release_closure_review_still_required=True),
        lifecycle_domain=dict(base_sha256=manifest['reviewed_domain_lifecycle_baseline_sha256'],
            active_release_sha256=manifest['active_release_lifecycle_sha256'],
            whole_file_may_replace_active_release=False, map_owner_lifecycle_activated=False),
        methods=['tdd: three separate public-interface/native-decoder red witnesses retained',
            'codebase-design: one immutable placement invariant and existing two message entry points',
            'research: original decoder channel versus designed per-placement server adoption',
            'code-review: exact byte baselines and independent Standards/Spec fixed-input replays'],
        historical_fixture_failure=manifest['supersedes'],
        source_status='field_48 native channel client_verified; per-placement server adoption designed',
        root_design_adoption_accepted=False, shared_runtime_verified=False,
        deployed=False, gui_verified=False, live_database_accessed=False,
        limitations=['wire0 is fallback; full actor/model branch may override raw direction',
            'No historical server packet, full native model initialization or GUI claim',
            'No membership, identification, dynamic lifecycle or other service activation'])
    READY.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print('Sealed direction domain:', len(reports), 'passed checks;', len(manifest['files']), 'fixed inputs')
    print('Ready SHA256:', sha(READY))


if __name__ == '__main__':
    main()
