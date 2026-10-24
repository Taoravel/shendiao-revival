"""Seal only a fully verified, independently reviewed immutable candidate."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,shutil

root=Path(__file__).resolve().parents[1]
review=root/'evidence/reviews/guild-maintenance-20261024T051526Z-r3'
first=root/'evidence/reviews/guild-maintenance-20261024T051526Z'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
write=lambda p,v:p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
manifest=read(review/'candidate.json');manifest_sha=sha(review/'candidate.json')
assert manifest_sha=='9a7bc1f32301cef107a60f7e50f6c11d8698451025e5bdc1cf89e4dbbee734e6'
for name,digest in manifest['dependency_source_sha256'].items():assert sha(review/'source'/name)==digest,name
for name,digest in manifest['candidate_sha256'].items():assert sha(root/name)==digest,name
for name,digest in manifest['specification_sha256'].items():assert sha(review/name)==digest,name
resources=read(review/'resource-inputs.json')
for name,record in resources.items():
    assert sha(root/name)==record['sha256'],name
    assert sha(review/'source'/name)==record['sha256'],name
axes={axis:read(review/(axis+'-review.json')) for axis in ('standards','spec')}
counts={axis:value.get('findings_count',value.get('counts')) for axis,value in axes.items()}
for axis,value in axes.items():
    assert value['candidate_manifest_sha256']==manifest_sha
    assert counts[axis] and not any(counts[axis].values()),(axis,counts[axis])
scripts=read(review/'results/script-results.json');assert len(scripts)==32 and all(v['exit_code']==0 for v in scripts)
closure=read(review/'results/import-closure.json');assert not closure['unfrozen_workspace_code_imported']
for name,value in closure['modules'].items():assert sha(Path(value['path']))==value['sha256'],name
source_imports=sum(Path(v['path']).is_relative_to(review/'source') for v in closure['modules'].values())
domain=read(review/'results/guild-maintenance-verification.json');native=read(review/'results/guild-maintenance-native-verification.json')
assert len(domain['passed'])==12 and len(native['passed'])==5
for name,digest in native['source_sha256'].items():assert sha(review/'source'/name)==digest,name
status='guild_hourly_maintenance_verified_reviewed_explicit_policy_not_activated'
report=dict(batch=25,revision='r3',created_utc=datetime.now(timezone.utc).isoformat(),
    status=status,fixed_review_directory=str(review),candidate_manifest_sha256=manifest_sha,
    scope=manifest['scope'],baseline_origin=manifest['baseline_origin'],candidate_sha256=manifest['candidate_sha256'],
    diff_sha256=manifest['diff_sha256'],resource_manifest_sha256=manifest['resource_manifest_sha256'],
    source_python_files=sum(n.endswith('.py') for n in manifest['dependency_source_sha256']),
    frozen_dependencies=len(manifest['dependency_source_sha256']),enumerated_resource_files=len(resources),
    specification_files=len(manifest['specification_sha256']),actual_imported_repo_modules=source_imports,
    actual_imports_including_harness=len(closure['modules']),script_count=len(scripts),new_check_groups=17,
    axis_counts=counts,standards_findings=0,spec_findings=0,
    review_report_sha256={n:sha(review/n) for n in ('standards-review.md','standards-review.json','spec-review.md','spec-review.json')},
    verification_harnesses={'verify_fixed_candidate.py':dict(path=str(review/'verify_fixed_candidate.py'),sha256=sha(review/'verify_fixed_candidate.py'))},
    results_sha256={p.relative_to(review).as_posix():sha(p) for p in sorted((review/'results').iterdir()) if p.is_file()},
    prior_revisions=[dict(directory=str(first),status='not_accepted',standards=dict(P0=0,P1=0,P2=2,P3=1),spec=dict(P0=0,P1=0,P2=1,P3=0)),
        dict(directory=str(first)+'-r2',status='intermediate_observation_fix_not_accepted')],
    methods=['research','codebase-design','tdd','diagnosing-bugs','code-review','writing-for-agents'],
    functional_reds_observed=['terminal source absent','clock resume Interface absent','Runtime policy/maintenance Interface absent',
        'periodic switch incorrectly changed economic recipe','new observation policy blocks historical successful replay',
        'single shared job slot starves a second partition during repeated local failure'],
    fixture_corrections_not_functional_reds=['LEFT_FACTION expected constant corrected','frozen __file__ dependencies require pinned resource copies'],
    original_maintenance_scalar_consumers_verified=True,actual_hourly_research_source_same_transaction=True,
    separate_practice_material_account_preserved=True,downgrade_and_terminal_family_overlap_verified=True,
    overdue_resume_grants_historical_income=False,actual_periodic_source_verified=True,
    directory_fairness_with_new_arrivals_and_cross_partition_faults_verified=True,
    postcommit_display_failure_deferred_actual_commit_failure_propagates=True,
    native_evidence_source_hashes_match_executed_fixed_source=True,
    production_policy_configured=False,production_numeric_policy_changed=False,
    actual_task_source_integrated=False,npc_choice_registered=False,complete_details_mapper_implemented=False,
    terminal_other_owner_cleanup_integrated=False,native_gui_verified=False,live_server_changed=False,
    shared_entry_files_edited=False,cross_database_delivery_verified=False,commercial_capacity_verified=False,
    full_social_recovery_complete=False,not_activation_authorization=True,
    runtime_handoff='evidence/GUILD_MAINTENANCE_RUNTIME.md',runtime_handoff_sha256=sha(root/'evidence/GUILD_MAINTENANCE_RUNTIME.md'))
write(review/'review-result.json',report)
write(root/'evidence/guild-maintenance-batch.json',dict(report,review_result_sha256=sha(review/'review-result.json')))
old=read(first/'candidate.json')
write(first/'review-result.json',dict(batch=25,revision='r1',status='not_accepted',candidate_manifest_sha256=sha(first/'candidate.json'),
    axis_counts={k:read(first/(k+'-review.json')).get('findings_count',read(first/(k+'-review.json')).get('counts')) for k in axes},
    script_count=32,fixed_source_edited=False,resolved_by=str(review),review_report_sha256={n:sha(first/n) for n in report['review_report_sha256']}))
intermediate=Path(str(first)+'-r2')
write(intermediate/'review-result.json',dict(batch=25,revision='r2',status='intermediate_not_accepted',
    candidate_manifest_sha256=sha(intermediate/'candidate.json'),full_suite_run=False,independent_review_accepted=False,resolved_by=str(review)))
previous=review/'previous-current-pointers';previous.mkdir(exist_ok=True)
for name in ('guild-maintenance','guild-buildings','family-guild-history','family-history','family-donation','guild-research','guild-research-panel','guild-dissolution'):
    path=root/'evidence'/(name+'-current-review.json');pointer=read(path) if path.exists() else {}
    if path.exists():shutil.copy2(path,previous/path.name)
    pointer.update(review_directory=str(review),status=status,review_result_sha256=sha(review/'review-result.json'),
        candidate_manifest_sha256=manifest_sha,latest_runtime_handoff=report['runtime_handoff'],not_activation_authorization=True)
    if name=='guild-maintenance':pointer['runtime_handoff']=report['runtime_handoff']
    write(path,pointer)
write(root/'evidence/guild-maintenance-pending-review.json',dict(batch=25,pending=False,accepted_revision='r3',
    review_directory=str(review),review_result_sha256=sha(review/'review-result.json'),not_activation_authorization=True))
print(json.dumps(dict(review=str(review),result_sha256=sha(review/'review-result.json'),source_imports=source_imports,
    including_runner=len(closure['modules']),scripts=32,groups=17)))
