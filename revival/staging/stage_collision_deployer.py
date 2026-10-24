"""Prepare the established coordinated switch, without executing it."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
candidate=json.loads((ROOT/'staging/world-collision-candidate.json').read_text(encoding='utf-8'))
recovered=json.loads((ROOT/'evidence/approved-loyalty-service-recovery.json').read_text(encoding='utf-8'))
if (not recovered['started'] or Path(recovered['release']).name!='npc-loyalty-20261023T193742Z'
        or not recovered['source_hashes_match'] or not recovered['all110_table_rows_unchanged']):
    raise ValueError('Approved BASE recovery has not been verified')
text=(ROOT/'staging/deploy_npc_loyalty_release.ps1').read_text(encoding='utf-8')
replacements=[
    ('$loyalty','$collision'),
    ('staging/npc-loyalty-candidate.json','staging/world-collision-candidate.json'),
    ("'npc-loyalty-20261023T193742Z'",repr(Path(candidate['release']).name)),
    ('evidence/reviews/npc-loyalty-release-20261024-r2','evidence/reviews/world-collision-root-20261024-r4'),
    ('1440','1442'),('14480',str(recovered['pid'])),
    ('.Count -ne 3)', '.Count -ne 6)'),
    ('*private-story-20261023T190051Z*run_release.py*','*npc-loyalty-20261023T193742Z*run_release.py*'),
    ('private story candidate','world collision candidate'),
    ('private production scope','world collision production scope'),
    ('Private candidate','Collision candidate'),('Private listener','Collision listener'),
    ('Private post-deployment','Collision post-deployment'),
]
for before,after in replacements:
    if before not in text:raise ValueError('Established deployer anchor missing: '+before)
    text=text.replace(before,after)
anchor='--candidate-record $collisionRecord --pid $collisionStarted.Id'
if text.count(anchor)!=1:raise ValueError('Exact post-start verifier invocation missing')
text=text.replace(anchor,anchor+' --previous-pid $collisionAcceptance.expected_base_pid')
target=ROOT/'staging/deploy_world_collision_release.ps1'
target.write_text(text,encoding='utf-8')
print(str(target))
