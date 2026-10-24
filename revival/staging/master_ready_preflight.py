"""Read-only live backup and frozen startup checks on its disposable copy."""
from datetime import datetime,timezone
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import sys

ROOT=Path(__file__).resolve().parents[1]


def table_state(db):
    result={}
    for (name,) in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND (name NOT LIKE 'sqlite_%' OR name='sqlite_sequence') ORDER BY name"):
        quoted='"'+name.replace('"','""')+'"'
        rows=sorted(repr(tuple(row)).encode('utf-8') for row in db.execute('SELECT * FROM '+quoted))
        digest=hashlib.sha256()
        for row in rows:digest.update(len(row).to_bytes(8,'big'));digest.update(row)
        result[name]={'rows':len(rows),'sha256':digest.hexdigest()}
    return result


def verify_preserved_tables(before,after,candidate):
    """Preserve every old row; admit only declared empty startup receipt tables."""
    allowed=candidate.get('new_empty_tables',[])
    if type(allowed) is not list or any(type(name) is not str for name in allowed):
        raise ValueError('Explicit new-empty-table allowlist required')
    if any(after.get(name)!=rows for name,rows in before.items()):
        raise ValueError('Candidate changed existing database rows or removed a table')
    added=set(after)-set(before)
    if added-set(allowed) or any(after[name]['rows'] for name in added):
        raise ValueError('Unexpected or populated new startup table')
    return sorted(added)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--candidate-record',type=Path,default=ROOT/'staging/master-ready-candidate.json')
    parser.add_argument('--reuse-backup',action='store_true')
    args=parser.parse_args();candidate=json.loads(args.candidate_record.read_text(encoding='utf-8'))
    release=Path(candidate['release'])
    source=release/'source';manifest=json.loads((release/'manifest.json').read_text(encoding='utf-8'))
    def verify():
        for name,value in manifest['sha256'].items():
            if hashlib.sha256((source/name).read_bytes()).hexdigest()!=value:raise ValueError('Candidate hash mismatch: '+name)
    verify()
    required=candidate.get('checks_required',('research_task_existing_quest.py','verify_task_master_card.py','verify_first_master_runtime.py',
        'verify_exit_initialization_runtime.py','verify_role_lifecycle_runtime.py'))
    for script in required:
        check=json.loads((release/'checks'/(script+'.result.json')).read_text(encoding='utf-8'))
        if not check['passed']:
            raise ValueError('Candidate check incomplete: '+script)
        if (candidate.get('acceptance_input_sha256') is not None
                and check.get('acceptance_input_sha256')!=candidate['acceptance_input_sha256']):
            raise ValueError('Candidate check used a different frozen acceptance input set: '+script)
    backup=release/'accounts-before.sqlite3'
    if backup.exists() and not args.reuse_backup:raise ValueError('Refuse to overwrite an existing deployment backup')
    with sqlite3.connect((ROOT/'runtime/accounts.sqlite3').as_uri()+'?mode=ro',uri=True) as original:
        original.execute('BEGIN')
        before=table_state(original)
        if backup.exists():
            with sqlite3.connect(backup) as saved:
                if table_state(saved)!=before:raise ValueError('Existing backup differs from the current read-only snapshot')
        else:
            with sqlite3.connect(backup) as saved:original.backup(saved)
    migration=release/'migration-check.sqlite3';shutil.copy2(backup,migration)
    sys.path.insert(0,str(source))
    import inspect_client
    inspect_client.ROOT=ROOT.parent;inspect_client.OUT=source
    from accounts import AccountStore
    import runtime_storage
    store=AccountStore(migration);runtime_storage.prepare(store)
    with sqlite3.connect(migration) as db:
        after=table_state(db);integrity=db.execute('PRAGMA quick_check').fetchone()[0]
    added=verify_preserved_tables(before,after,candidate)
    if integrity!='ok':raise ValueError('Migration copy integrity failed')
    verify()
    result={'created_utc':datetime.now(timezone.utc).isoformat(),'release':str(release),
        'candidate_hashes_verified':len(manifest['sha256']),'checks_passed':list(required),
        'backup':str(backup),'schema_and_all_existing_rows_preserved':len(before),'tables':before,
        'quick_check':integrity,'added_empty_tables':added,'real_database_read_only':True,'real_authentication':False,
        'native_gui_verified':False,'scope':manifest.get('scope','scoped immutable source release'),
        'unrelated_gameplay_included':False,'automatic_resource_migration':False}
    (release/'preflight.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({key:value for key,value in result.items() if key!='tables'},ensure_ascii=True))


if __name__=='__main__':main()
