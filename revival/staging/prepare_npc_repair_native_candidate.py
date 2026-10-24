"""Make the next inactive repair candidate from sealed R1, never overwrite it."""
import difflib
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'staging/npc-repair-column-candidate-v1/npc_repairs.py'
DEST=ROOT/'staging/npc-repair-column-candidate-v2'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert sha(BASE)=='e648d4f977a58d774d670e606a0f72e722c657e17f66f50413ff9170d227dd9b'
    assert not DEST.exists(),'Preserve prior candidates/reviews'
    original=BASE.read_text(encoding='utf8');current=original
    def change(old,new):
        nonlocal current
        assert current.count(old)==1,old
        current=current.replace(old,new)
    change('           resource_rules=None,equipment_rules=None):',
        '           resource_rules=None,equipment_rules=None,equipment_messages=None):')
    change('    The fourth argument is positional for the bounded role I/O call surface.\n',
        '    The fourth argument is positional for the bounded role I/O call surface.\n\n'
        '    Optional startup-selected equipment_messages(db, inventory, item_key)\n'
        '    returns immutable current tip/endure/max logical messages inside this\n'
        '    SAME transaction, including on paid replay. It must read current owned\n'
        '    assets and encode before commit; the selected Asset adapter preserves\n'
        '    known gem sources and native own columns1/3. No arbitrary NPC frames\n'
        '    are relabelled. Its failure rolls back assets, fee and all receipts.\n'
        '    It must not connect, commit, mutate assets or send. None retains the\n'
        '    explicit legacy producer for callers not yet migrated.\n')
    change("    if precommit is not None and not callable(precommit):raise ValueError('Trusted repair precommit callable required')\n",
        "    if precommit is not None and not callable(precommit):raise ValueError('Trusted repair precommit callable required')\n"
        "    if equipment_messages is not None and not callable(equipment_messages):\n"
        "        raise ValueError('Trusted repair equipment producer callable required')\n")
    change('        messages=list(inventory.equipment_refresh(db,item.id)) if item is not None else []\n',
        '        messages=[]\n'
        '        if item is not None:\n'
        '            if equipment_messages is None:\n'
        '                messages.extend(inventory.equipment_refresh(db,item.id))\n'
        '            else:\n'
        '                encoded=equipment_messages(db,inventory,item.id)\n'
        '                if (type(encoded) is not tuple or any(type(row) is not tuple or len(row)!=2\n'
        '                        or type(row[0]) is not int or not 0<=row[0]<=0xffffffff or type(row[1]) is not bytes\n'
        '                        for row in encoded)):\n'
        "                    raise ValueError('Repair equipment producer must return immutable encoded logical messages')\n"
        '                messages.extend(encoded)\n')
    # Review-stage duplication removal after the first complete green run.
    change('REPAIR_EQUIPMENT=0xc0413\n\n\n',
        'REPAIR_EQUIPMENT=0xc0413\n\n\n'
        'def _encoded_messages(messages,producer):\n'
        '    if (type(messages) is not tuple or any(type(row) is not tuple or len(row)!=2\n'
        '            or type(row[0]) is not int or not 0<=row[0]<=0xffffffff or type(row[1]) is not bytes\n'
        '            for row in messages)):\n'
        "        raise ValueError('Repair '+producer+' must return immutable encoded logical messages')\n"
        '    return messages\n\n\n')
    change('                encoded=equipment_messages(db,inventory,item.id)\n'
        '                if (type(encoded) is not tuple or any(type(row) is not tuple or len(row)!=2\n'
        '                        or type(row[0]) is not int or not 0<=row[0]<=0xffffffff or type(row[1]) is not bytes\n'
        '                        for row in encoded)):\n'
        "                    raise ValueError('Repair equipment producer must return immutable encoded logical messages')\n"
        '                messages.extend(encoded)\n',
        "                messages.extend(_encoded_messages(equipment_messages(db,inventory,item.id),'equipment producer'))\n")
    change('            projected=precommit(db,inventory,inventory.immutable_snapshot_transaction(db))\n'
        '            if (type(projected) is not tuple or any(type(row) is not tuple or len(row)!=2\n'
        '                    or type(row[0]) is not int or not 0<=row[0]<=0xffffffff or type(row[1]) is not bytes\n'
        '                    for row in projected)):\n'
        "                raise ValueError('Repair precommit must return immutable encoded logical messages')\n"
        '            messages.extend(projected)\n',
        '            messages.extend(_encoded_messages(\n'
        "                precommit(db,inventory,inventory.immutable_snapshot_transaction(db)),'precommit'))\n")
    DEST.mkdir(parents=True)
    (DEST/'npc_repairs.py').write_text(current,encoding='utf8')
    (DEST/'changes-from-r1.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True),current.splitlines(True),
        fromfile='sealed-r1/npc_repairs.py',tofile='candidate-r2/npc_repairs.py')),encoding='utf8')
    result=dict(base_sha256=sha(BASE),candidate_sha256=sha(DEST/'npc_repairs.py'),
        exact_existing_adapter='equipment_native_columns.item_messages(db, inventory, NativeEquipmentRules, item_key)',
        shared_startup_injection_or_policy_adoption_or_deployment=False,
        old_R1_or_workspace_or_live_modified=False)
    (DEST/'candidate.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('Prepared inactive R2:',result['candidate_sha256'])


if __name__=='__main__':main()
