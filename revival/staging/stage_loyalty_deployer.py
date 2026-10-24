"""Derive a one-use guarded rollout from the proven private-story procedure."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
text=(ROOT/'staging/deploy_private_story_release.ps1').read_text(encoding='utf-8')
text=text.replace('$story','$loyalty')
for old,new in (
    ('staging/private-story-candidate.json','staging/npc-loyalty-candidate.json'),
    ("-ne 'private-story-20261023T190051Z'","-ne 'npc-loyalty-20261023T193742Z'"),
    ('-ne 1439','-ne 1440'),('-ne 18','-ne 3'),
    ('evidence/reviews/private-story-release-20261024/REVIEW-root.md',
     'evidence/reviews/npc-loyalty-release-20261024-r2/REVIEW-root.md'),
    ('OwningProcess -ne 12336','OwningProcess -ne 14480'),
    ("'ProcessId=12336'","'ProcessId=14480'"),
    ('Stop-Process -Id 12336','Stop-Process -Id 14480'),
    ('Wait-Process -Id 12336','Wait-Process -Id 14480'),
    ('*wild-auto-20261023T181143Z*run_release.py*','*private-story-20261023T190051Z*run_release.py*'),
):
    if old not in text:raise ValueError('Expected proven deployment seam missing: '+old)
    text=text.replace(old,new)
start=text.index('$loyaltyRecovery = ')
end=text.index('$loyaltyReview = ',start)
text=text[:start]+text[end:]
old="if ((($loyaltyCandidate.new_empty_tables | Sort-Object) -join ',') -ne 'task_prologue_touches,world_story_instances') { throw 'Unexpected new table allowlist' }"
if text.count(old)!=1:raise ValueError('Table allowlist seam changed')
text=text.replace(old,"if ($loyaltyCandidate.new_empty_tables.Count -ne 0) { throw 'No schema changes authorized' }")
(ROOT/'staging/deploy_npc_loyalty_release.ps1').write_text(text,encoding='utf-8')
print('Loyalty deployment procedure staged; no service action executed')
