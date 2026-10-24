"""Independent frozen-source/data and unauthenticated health audit, no restart."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import socket
import sqlite3
import struct
import sys
from master_ready_preflight import table_state


def main():
    root=Path(__file__).resolve().parents[1]
    candidate=json.loads((root/'staging/npc-loyalty-candidate.json').read_text(encoding='utf8'))
    release=Path(candidate['release']);source=release/'source'
    manifest=json.loads((release/'manifest.json').read_text(encoding='utf8'))
    startup=json.loads((root/'runtime/deployment.json').read_text(encoding='utf8'))
    assert candidate['status']=='deployed' and candidate['pid']==startup['pid']==48572
    assert hashlib.sha256((release/'run_release.py').read_bytes()).hexdigest()==manifest['runner_sha256']
    for name,digest in manifest['sha256'].items():
        assert hashlib.sha256((source/name).read_bytes()).hexdigest()==digest,name
    assert all(manifest['sha256'].get(name)==digest for name,digest in startup['source_sha256_at_startup'].items())
    with sqlite3.connect((release/'accounts-at-stop.sqlite3').as_uri()+'?mode=ro',uri=True) as db:
        before=table_state(db)
    with sqlite3.connect((root/'runtime/accounts.sqlite3').as_uri()+'?mode=ro',uri=True) as db:
        db.execute('BEGIN');after=table_state(db);integrity=db.execute('PRAGMA quick_check').fetchone()[0]
    assert integrity=='ok' and before==after
    sys.path.insert(0,str(source))
    from wire import FrameReader,frame,read_octets
    with socket.create_connection(('127.0.0.1',28993),timeout=5) as client:
        reader=FrameReader();messages=[]
        while not messages:messages.extend(reader.feed(client.recv(65536)))
        assert messages[0][0]==101
        _,offset=read_octets(messages[0][1]);version=struct.unpack_from('>I',messages[0][1],offset)[0]
        assert version==601
        client.sendall(frame(100,b'\0\0\0\0'));messages=[]
        while not messages:messages.extend(reader.feed(client.recv(65536)))
        assert messages[0]==(100,b'\0\0\0\0')
    report=dict(recorded_utc=datetime.now(timezone.utc).isoformat(),pid=startup['pid'],release=str(release),
        os_process_and_unique_listener_observed_separately='Win32 command names this runner;127.0.0.1:28993 owner48572',
        source_hashes_verified=len(manifest['sha256']),runner_hash_verified=True,
        startup_python_hashes_verified=len(startup['source_sha256_at_startup']),
        changed_inputs=manifest['changed_modules'],version=version,unauthenticated_heartbeat='passed',
        preexisting_tables_preserved=len(before),preexisting_rows_unchanged=True,new_tables=[],quick_check=integrity,
        exact_candidate_owner_checks='npc-loyalty-candidate-owner-20261024',
        root_shared_review='reviews/npc-loyalty-release-20261024-r2/REVIEW-root.md',
        real_authentication=False,database_mode='read-only',live_database_modified=False,
        service_restarted_by_this_audit=False,native_gui_verified=False,battle_executed=False)
    (root/'evidence/npc-loyalty-deployment-owner-verification.json').write_text(
        json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print('PASS deployed48572:',len(manifest['sha256']),'frozen inputs;',len(before),'tables unchanged;601/heartbeat')


if __name__=='__main__':main()
