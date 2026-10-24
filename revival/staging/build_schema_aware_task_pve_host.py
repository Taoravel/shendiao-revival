"""Narrow schema-aware derivative of the approved detached host; keep r2."""
import difflib
import hashlib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    original=ROOT/'staging/launch_detached_release.py'
    if hashlib.sha256(original.read_bytes()).hexdigest()!='79c055364c0699005987cd3a7ce538dc4a582eb1cdeb211ce66da39b99ebd0c0':
        raise ValueError('Reviewed r2 host source changed')
    text=original.read_text(encoding='utf-8')
    replacements={
        'from master_ready_preflight import table_state':
            'from master_ready_preflight import table_state,verify_preserved_tables',
        "    require(len(before)==110,'Unexpected formal schema; no migration authorized')":
            "    candidate=json.loads((release/'candidate.json').read_text(encoding='utf-8'))\n"
            "    preflight=json.loads((release/'preflight.json').read_text(encoding='utf-8'))\n"
            "    require(candidate['release']==str(release),'Schema candidate identity mismatch')\n"
            "    require(candidate['new_empty_tables']==manifest['new_empty_tables'],\n"
            "        'New empty-table scope differs from the approved manifest')\n"
            "    require(set(before)==set(preflight['tables']) and\n"
            "        preflight['candidate_hashes_verified']==len(manifest['sha256']),\n"
            "        'Formal table set differs from the exact candidate preflight')\n"
            "    with sqlite3.connect(recovery/'accounts-before.sqlite3') as saved:\n"
            "        before_schema={name:sql for name,sql in saved.execute(\n"
            "            \"SELECT name,sql FROM sqlite_master WHERE type='table'\")}\n",
        "        require(table_state(db)==before,'Recovery changed formal rows')":
            "        added_empty_tables=verify_preserved_tables(before,table_state(db),candidate)\n"
            "        after_schema={name:sql for name,sql in db.execute(\n"
            "            \"SELECT name,sql FROM sqlite_master WHERE type='table'\")}\n"
            "        require(all(after_schema.get(name)==sql for name,sql in before_schema.items()),\n"
            "            'Startup changed an existing table schema')",
        "before_tables=before,all110_table_rows_unchanged=True,quick_check='ok',":
            "before_tables=before,all_preexisting_table_rows_unchanged=True,\n"
            "        preexisting_table_count=len(before),added_empty_tables=added_empty_tables,\n"
            "        preexisting_table_schema_unchanged=True,quick_check='ok',",
    }
    changed=text
    for old,new in replacements.items():
        if changed.count(old)!=1:raise ValueError('Approved host seam changed: '+old)
        changed=changed.replace(old,new,1)
    target=ROOT/'staging/launch_detached_scoped_release.py'
    target.write_text(changed,encoding='utf-8')
    (ROOT/'staging/task-pve-host-schema.diff').write_text(''.join(difflib.unified_diff(
        text.splitlines(True),changed.splitlines(True),fromfile='approved-host-r2',tofile='schema-scoped-host')),
        encoding='utf-8')
    print(hashlib.sha256(target.read_bytes()).hexdigest())


if __name__=='__main__':main()
