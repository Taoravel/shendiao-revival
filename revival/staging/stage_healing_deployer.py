"""Adapt the proven deployment identity gate to this one fixed candidate."""
from pathlib import Path
root=Path(__file__).resolve().parent
source=(root/'deploy_npc_bound_shop_release.ps1').read_text(encoding='utf-8')
changes={
 'staging/npc-bound-shop-candidate.json':'staging/npc-role-healing-candidate.json',
 'npc-bound-shop-20261023T115742Z':'npc-role-healing-20261023T125539Z',
 'npc-bound-shop-release-20261023':'npc-role-healing-release-20261023',
 '1427':'1429',
 '44084':'39796',
 'npc-close-master-commit-20261023T113819Z':'npc-bound-shop-20261023T115742Z',
}
for before,after in changes.items():
    if not source.count(before):raise ValueError('Deployment template identity changed: '+before)
    source=source.replace(before,after)
target=root/'deploy_npc_role_healing_release.ps1'
if target.exists():raise ValueError('Fixed deploy script already exists')
target.write_text(source,encoding='utf-8')
print(target)
