"""Independently verify a recovered release, keeping the original report intact.

The main integrator supplies actual PID/release and its pre-recovery DB backup.
This observer never starts/stops a service or authenticates a character.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import socket
import sqlite3
import struct
import subprocess
import sys
from master_ready_preflight import table_state


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def os_state(pid):
    if type(pid) is not int or pid<1:raise ValueError('Actual positive OS PID required')
    command=(f'$p=@(Get-CimInstance Win32_Process -Filter "ProcessId = {pid}"); '
        '$l=@(Get-NetTCPConnection -LocalPort 28993 -State Listen -ErrorAction SilentlyContinue); '
        '[pscustomobject]@{ processes=@($p | Select-Object ProcessId,CommandLine); '
        'listeners=@($l | Select-Object LocalAddress,LocalPort,OwningProcess) } | ConvertTo-Json -Depth 5 -Compress')
    return json.loads(subprocess.check_output(['powershell.exe','-NoProfile','-Command',command],
        encoding='utf8',timeout=20))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--release',required=True,type=Path)
    parser.add_argument('--pid',required=True,type=int)
    parser.add_argument('--before-db',required=True,type=Path)
    args=parser.parse_args();root=Path(__file__).resolve().parents[1]
    release=args.release.resolve();source=release/'source'
    if not release.is_relative_to(root/'runtime/deployments'):
        raise ValueError('Exact managed immutable deployment required')
    manifest=json.loads((release/'manifest.json').read_text(encoding='utf8'))
    startup=json.loads((root/'runtime/deployment.json').read_text(encoding='utf8'))
    if startup['pid']!=args.pid:raise ValueError('Historical deployment PID differs from current recovery')
    state=os_state(args.pid)
    assert len(state['processes'])==len(state['listeners'])==1,state
    command=state['processes'][0]['CommandLine']
    assert str(release/'run_release.py').casefold() in command.casefold(),command
    assert state['listeners'][0]==dict(LocalAddress='127.0.0.1',LocalPort=28993,OwningProcess=args.pid)
    assert sha(release/'run_release.py')==manifest['runner_sha256']
    for name,digest in manifest['sha256'].items():assert sha(source/name)==digest,name
    assert all(manifest['sha256'].get(name)==digest for name,digest in startup['source_sha256_at_startup'].items())
    before_path=args.before_db.resolve();live_path=(root/'runtime/accounts.sqlite3').resolve()
    if before_path==live_path:raise ValueError('Separate pre-recovery backup required')
    with sqlite3.connect(before_path.as_uri()+'?mode=ro',uri=True) as db:
        db.execute('BEGIN');before=table_state(db);assert db.execute('PRAGMA quick_check').fetchone()==('ok',)
        before_schema=db.execute("SELECT type,name,tbl_name,sql FROM sqlite_master "
            "WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name").fetchall()
    with sqlite3.connect(live_path.as_uri()+'?mode=ro',uri=True) as db:
        db.execute('BEGIN');after=table_state(db);assert db.execute('PRAGMA quick_check').fetchone()==('ok',)
        after_schema=db.execute("SELECT type,name,tbl_name,sql FROM sqlite_master "
            "WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name").fetchall()
    assert before==after and before_schema==after_schema,'Recovery changed schemas or persisted rows relative to provided pre-recovery backup'
    sys.path.insert(0,str(source))
    from wire import FrameReader,frame,read_octets
    with socket.create_connection(('127.0.0.1',28993),timeout=5) as client:
        reader=FrameReader();messages=[]
        while not messages:
            chunk=client.recv(65536)
            if not chunk:raise ValueError('Service closed before hello')
            messages.extend(reader.feed(chunk))
        assert messages[0][0]==101
        _,offset=read_octets(messages[0][1]);version=struct.unpack_from('>I',messages[0][1],offset)[0]
        assert version==601
        client.sendall(frame(100,b'\0\0\0\0'));messages=[]
        while not messages:
            chunk=client.recv(65536)
            if not chunk:raise ValueError('Service closed before unauthenticated heartbeat')
            messages.extend(reader.feed(chunk))
        assert messages[0]==(100,b'\0\0\0\0')
    assert os_state(args.pid)==state,'OS process/listener changed during observation'
    report=dict(recorded_utc=datetime.now(timezone.utc).isoformat(),pid=args.pid,release=str(release),
        os_state=state,source_hashes_verified=len(manifest['sha256']),runner_hash_verified=True,
        startup_python_hashes_verified=len(startup['source_sha256_at_startup']),version=version,
        unauthenticated_heartbeat='passed',provided_pre_recovery_backup=str(before_path),
        provided_backup_sha256=sha(before_path),preexisting_tables_preserved=len(before),
        preexisting_rows_and_schemas_equal=True,database_mode='read-only',live_database_modified=False,
        real_authentication=False,service_restarted_by_this_audit=False,native_gui_verified=False,
        gameplay_tests_rerun_by_this_observer=False)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    path=root/'evidence'/f'npc-runtime-recovery-owner-{stamp}.json'
    with path.open('x',encoding='utf8') as stream:json.dump(report,stream,ensure_ascii=False,indent=2)
    print(json.dumps(dict(passed=True,pid=args.pid,frozen_inputs=len(manifest['sha256']),
        unchanged_tables=len(before),report=str(path)),ensure_ascii=False))


if __name__=='__main__':main()
