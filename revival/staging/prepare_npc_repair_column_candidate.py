"""Prepare one inactive NPC module candidate; leave workspace/release untouched."""
import difflib
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / 'runtime/deployments/npc-repair-20261024T023920Z'
DEST = ROOT / 'staging/npc-repair-column-candidate-v1'
BASE_SHA = '3cc4ff7dc2a956946fd31debb18b1a3773d6ca472b93b218fcc257e5aaf86884'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    source = RELEASE / 'source/npc_repairs.py'
    assert sha(source) == BASE_SHA and sha(ROOT / 'npc_repairs.py') == BASE_SHA
    assert not DEST.exists(), 'Preserve the prior candidate and its review'
    before = source.read_text(encoding='utf8')
    after = before

    def change(old, new):
        nonlocal after
        assert after.count(old) == 1, old
        after = after.replace(old, new)

    change('column not in (1,4)', 'column not in (1,3,4)')
    change('    service=intent.service\n',
        '    service=intent.service\n'
        '    if type(intent.column) is not int or intent.column not in (1,3,4):\n'
        "        raise ValueError('Unsupported repair source column')\n"
        '    # Native3 is equipped. Historical receipts used token4 for the same\n'
        '    # physical intent; keep that private identity without aliasing bags.\n'
        '    receipt_column=4 if intent.column==3 else intent.column\n')
    change('        intent.column,intent.item_key),', '        receipt_column,intent.item_key),')
    change('        if not old:\n            if item is None or (4 if item.equipment_slot is not None else 1)!=intent.column:',
        '        if not old:\n'
        '            if intent.column==4:\n'
        "                raise ValueError('Legacy equipped repair requires an existing paid receipt')\n"
        '            if item is None or (3 if item.equipment_slot is not None else 1)!=intent.column:')
    DEST.mkdir()
    (DEST / 'npc_repairs.py').write_text(after, encoding='utf8')
    (DEST / 'changes.diff').write_text(''.join(difflib.unified_diff(before.splitlines(True),
        after.splitlines(True), fromfile='published/npc_repairs.py', tofile='candidate/npc_repairs.py')), encoding='utf8')
    result = dict(status='inactive_npc_only_preparation', base_release=str(RELEASE),
        production_base_sha256=BASE_SHA, candidate_sha256=sha(DEST / 'npc_repairs.py'),
        proposed_behavior=['Native fresh column1 carried and3 equipped only',
            'Legacy4 may only replay an existing matching stable paid receipt',
            'Private original receipt token4 retained for native3 physical intent',
            'No bag-column alias, persistence migration, new source initialization or special855'],
        root_final_policy_and_asset_interface_adoption=False, review_complete=False,
        workspace_module_modified=False, frozen_release_modified=False, shared_or_service_changed=False)
    (DEST / 'candidate.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    assert sha(source) == BASE_SHA and sha(ROOT / 'npc_repairs.py') == BASE_SHA
    print('Prepared inactive NPC column candidate:', result['candidate_sha256'])


if __name__ == '__main__':
    main()
