"""Verify and snapshot the latest reviewed release; never restore an old DB."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import socket
import sqlite3
import struct
import sys
from master_ready_preflight import table_state

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT/'runtime/deployments/npc-role-healing-20261023T125539Z'
RECORD = ROOT/'staging/reviewed-service-recovery.json'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pid', type=int)
    args = parser.parse_args()
    manifest = json.loads((RELEASE/'manifest.json').read_text(encoding='utf-8'))
    for name, expected in manifest['sha256'].items():
        if hashlib.sha256((RELEASE/'source'/name).read_bytes()).hexdigest() != expected:
            raise ValueError('Reviewed source changed: '+name)
    if hashlib.sha256((RELEASE/'run_release.py').read_bytes()).hexdigest() != manifest['runner_sha256']:
        raise ValueError('Reviewed runner changed')
    with sqlite3.connect((ROOT/'runtime/accounts.sqlite3').as_uri()+'?mode=ro', uri=True) as db:
        db.execute('BEGIN')
        rows = table_state(db)
        if db.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
            raise ValueError('Current account store failed integrity check')
        if not args.pid:
            stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
            backup = RELEASE/('accounts-recovery-'+stamp+'.sqlite3')
            with sqlite3.connect(backup) as saved:
                db.backup(saved)
            record = dict(release=str(RELEASE), backup=str(backup), tables=rows,
                recorded_utc=datetime.now(timezone.utc).isoformat(), source_hashes_verified=len(manifest['sha256']))
            RECORD.write_text(json.dumps(record, indent=2), encoding='utf-8')
            print(json.dumps({k:v for k,v in record.items() if k!='tables'}))
            return
    record = json.loads(RECORD.read_text(encoding='utf-8'))
    if rows != record['tables']:
        raise ValueError('Startup changed existing account data')
    startup = json.loads((ROOT/'runtime/deployment.json').read_text(encoding='utf-8'))
    if startup['pid'] != args.pid:
        raise ValueError('Startup PID mismatch')
    for name, actual in startup['source_sha256_at_startup'].items():
        if manifest['sha256'].get(name) != actual:
            raise ValueError('Startup source mismatch: '+name)
    sys.path.insert(0, str(RELEASE/'source'))
    from wire import FrameReader, frame, read_octets
    with socket.create_connection(('127.0.0.1', 28993), timeout=5) as client:
        reader = FrameReader()
        frames = []
        while not frames:
            frames.extend(reader.feed(client.recv(65536)))
        if frames[0][0] != 101:
            raise ValueError('Missing native challenge')
        _, offset = read_octets(frames[0][1])
        if struct.unpack_from('>I', frames[0][1], offset)[0] != 601:
            raise ValueError('Unexpected version')
        client.sendall(frame(100, bytes(4)))
        frames = []
        while not frames:
            frames.extend(reader.feed(client.recv(65536)))
        if frames[0] != (100, bytes(4)):
            raise ValueError('Heartbeat failed')
    record.update(pid=args.pid, quick_check='ok', version=601,
        unauthenticated_heartbeat='passed', preexisting_rows_unchanged=True,
        recovered_utc=datetime.now(timezone.utc).isoformat(), old_database_restored=False,
        gameplay_changes=False, native_gui_verified=False)
    RECORD.write_text(json.dumps(record, indent=2), encoding='utf-8')
    (ROOT/'evidence/reviewed-service-recovery.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in record.items() if k!='tables'}))


if __name__ == '__main__':
    main()
