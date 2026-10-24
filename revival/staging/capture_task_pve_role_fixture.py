"""Consistent read-only save snapshot for parent QA; never a deployment input."""
from contextlib import closing
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sqlite3

ROOT=Path(__file__).resolve().parents[1]


def main():
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder=ROOT/'evidence/fixtures'/('task-pve-existing-role4-'+stamp)
    folder.mkdir(parents=True,exist_ok=False)
    target=folder/'accounts.sqlite3'
    source=ROOT/'runtime/accounts.sqlite3'
    with (closing(sqlite3.connect(source.resolve().as_uri()+'?mode=ro',uri=True)) as original,
          closing(sqlite3.connect(target)) as copy):
        original.backup(copy)
    with closing(sqlite3.connect(target.resolve().as_uri()+'?mode=ro',uri=True)) as db:
        if db.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise ValueError('Fixture integrity failed')
        tables=tuple(row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"))
        role=db.execute('SELECT id,name,school,shape,level FROM roles WHERE id=4').fetchone()
        if role is None:raise ValueError('Role4 absent from the consistent snapshot')
        active=tuple(row[0] for row in db.execute("SELECT task_id FROM task_journal WHERE role_id=4 AND state='active' ORDER BY task_id"))
    record=dict(snapshot=str(target),sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
        size_bytes=target.stat().st_size,source_read_only=True,source_written=False,
        table_count=len(tables),tables=tables,role_id=role[0],
        role_name_sha256=hashlib.sha256(role[1].encode('utf-8')).hexdigest(),
        school=role[2],shape=role[3],level=role[4],active_tasks=active,
        captured_utc=datetime.now(timezone.utc).isoformat(),
        scope='Private QA fixture only; never production source, config, migration or live account replacement')
    (folder/'manifest.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    (ROOT/'staging/task-pve-role-fixture-current.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    print(json.dumps({key:record[key] for key in ('snapshot','sha256','table_count','role_id','active_tasks')}))


if __name__=='__main__':main()
