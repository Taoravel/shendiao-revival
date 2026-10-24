"""Record performed methods, production identity and explicit QA limits."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RELEASE=ROOT/'runtime/deployments/task-pve-20261024T053218Z'


def main():
    deployment=json.loads((RELEASE/'deployment-verification.json').read_text(encoding='utf-8'))
    startup=json.loads((ROOT/'runtime/deployment.json').read_text(encoding='utf-8'))
    manifest=json.loads((RELEASE/'manifest.json').read_text(encoding='utf-8'))
    candidate=json.loads((RELEASE/'candidate.json').read_text(encoding='utf-8'))
    if deployment['pid']!=37096 or startup['pid']!=37096:raise ValueError('Actual deployed identity changed')
    for name in ('runtime_storage.py','game_runtime.py','task_pve.py','task_battle.py','task_first_skill.py','role_skills.py'):
        if startup['source_sha256_at_startup'][name]!=manifest['sha256'][name]:
            raise ValueError('Actual startup capability code differs: '+name)
    policy=json.loads((RELEASE/'source/design/task-pve-ai8001-v1.json').read_text(encoding='utf-8'))
    record=dict(recorded_utc=datetime.now(timezone.utc).isoformat(),release=str(RELEASE),pid=37096,
        methods={
            'diagnosing-bugs':'Preserved original natural 100107 missing menu/admission/route RED; actual Peer went GREEN without Task/profile seeding. Old-pet paid error reproduced after real REST/FREE, then fixed only paid presentation.',
            'codebase-design':'Dedicated per-battle engine; Task owns chapter/NPC/admission/recovery/teaching; Role storage owns full-source CAS and atomic consumer; connection owns encrypted delivery. No wild reward reuse or global lock.',
            'tdd':'Public Owner two-round terminal seam failed missing Module first; public resource recovery and actual combat loadout reads failed missing Interface first. Later guards are regression checks, not separately claimed red-first.',
            'code-review':'Root independently reviewed Standards/Spec for frozen engine, Task slices, final core and schema-scoped host. Task compatibility r1 missing/null receipt defect and original paid-pet defect retained; r2/final close them.',
        },
        decisions=['Exact reviewed BASE plus 19 selected production changes; no hot NPC/Inventory/World source copy',
            'Real current attributes, actual optional owned pet, original NPC and full adopted private map; no training fallback',
            'Producer terminal is durable before delivery; current-lease consumer commits resources/Task/rewards/receipt/outbox status together; original event/epoch never relabelled',
            'Raw death permits only explicit dream-specific recovery; generic medicine/growth revival rules and resource policy bytes unchanged',
            'Old local OtherSkills baseline only inside a fully audited legitimate teaching commit; unknown never becomes verified-empty or startup backfill',
            'Known full OtherSkills map preserved; paid current state does not require a legitimately released historical pet',
            'Local system-labelled chat is a designed visible refusal, not an original system popup',
            'Approved detached Windows launch core retained; narrow schema guards allow only five empty tables and preserve old rows/SQL'],
        capability_evidence=dict(method='Exact prepare executes before startup record/listen; all capability module startup SHA equal reviewed manifest, no additional CLI flag',
            task_pve_enabled_ids=policy['enabled_task_ids'],engine_revision=policy['revision'],
            first_skill_rules_loaded=True,local_baseline_rules_loaded=True,
            baseline_enrollment_on_login_or_startup=False,serve_prologue_touch=True,
            actual_process_memory_introspected=False),
        verification=dict(frozen_checks=20,seal=candidate['acceptance_input_sha256'],
            source_inputs=1454,startup_python_inputs=454,harness_inputs=437,
            source_unchanged=True,original_tables_preserved=110,new_empty_tables=deployment['added_empty_tables'],
            quick_check='ok',version=601,unauthenticated_heartbeat=True,
            real_existing_role_fixture='evidence/fixtures/task-pve-existing-role4-20261024T051401532220Z/manifest.json',
            role4_copy_cases=['win','recover','late-recover','source-drift','notice','defeat'],
            paid_pet_case='Explicit owned pet/uselevel fixture, real battle/rest/free/public paid, not unseeded role4 proof',
            real_role_or_task_rewrite=False,automatic_resource_profile_migration=False),
        artifacts=['evidence/reviews/task-pve-root-20261024-r1/acceptance-root.json',
            'evidence/task-pve-deployment-verification.json','evidence/main-task-pve-liveness-after-publish-20261024.json',
            str(RELEASE/'accounts-at-stop.sqlite3'),str(RELEASE/'accounts-after-startup.sqlite3'),
            str(RELEASE/'changes.diff'),str(RELEASE/'checks')],
        unverified=['Native GUI/rendering and human acceptance; no live authenticated battle was executed by this batch',
            'Original movie10019 automatic playback is not established; original field/Finish preserved, no fabricated SStartPlayCG',
            'Next battle100190/AI8027, later dream return and complete skill formulas are separate recovery work',
            'Full AOI/member-permission integration, commercial capacity and reboot autostart are not established'])
    (ROOT/'evidence/task-pve-runtime-methods-20261024.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(record=str(ROOT/'evidence/task-pve-runtime-methods-20261024.json'),pid=37096,checks=20)))


if __name__=='__main__':main()
