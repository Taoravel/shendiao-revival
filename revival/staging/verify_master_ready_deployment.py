"""At-stop backup or post-start read-only data/hash/unauthenticated health checks."""
from datetime import datetime,timezone
import argparse
import hashlib
import json
from pathlib import Path
import socket
import sqlite3
import struct
import sys
from master_ready_preflight import ROOT,table_state,verify_preserved_tables


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--at-stop',action='store_true')
    parser.add_argument('--pid',type=int)
    parser.add_argument('--previous-pid',type=int)
    parser.add_argument('--candidate-record',type=Path,default=ROOT/'staging/master-ready-candidate.json')
    args=parser.parse_args();candidate=json.loads(args.candidate_record.read_text(encoding='utf-8'))
    release=Path(candidate['release'])
    if args.at_stop:
        path=release/'accounts-at-stop.sqlite3'
        if path.exists():raise ValueError('At-stop backup already exists')
        with sqlite3.connect((ROOT/'runtime/accounts.sqlite3').as_uri()+'?mode=ro',uri=True) as db:
            with sqlite3.connect(path) as saved:db.backup(saved)
        print('Consistent at-stop backup saved');return
    if args.pid is None:raise ValueError('Actual started PID required')
    manifest=json.loads((release/'manifest.json').read_text(encoding='utf-8'))
    for name,expected in manifest['sha256'].items():
        if hashlib.sha256((release/'source'/name).read_bytes()).hexdigest()!=expected:
            raise ValueError('Started source hash changed: '+name)
    startup=json.loads((ROOT/'runtime/deployment.json').read_text(encoding='utf-8'))
    if startup['pid']!=args.pid:raise ValueError('Startup identity mismatch')
    for name,value in startup['source_sha256_at_startup'].items():
        if manifest['sha256'].get(name)!=value:raise ValueError('Startup Python differs: '+name)
    with sqlite3.connect(release/'accounts-at-stop.sqlite3') as old:before=table_state(old)
    with sqlite3.connect((ROOT/'runtime/accounts.sqlite3').as_uri()+'?mode=ro',uri=True) as db:
        after=table_state(db);integrity=db.execute('PRAGMA quick_check').fetchone()[0]
    added=verify_preserved_tables(before,after,candidate)
    if integrity!='ok':raise ValueError('Deployment integrity failed')
    sys.path.insert(0,str(release/'source'))
    from wire import FrameReader,frame,read_octets
    with socket.create_connection(('127.0.0.1',28993),timeout=5) as client:
        reader=FrameReader();frames=[]
        while not frames:frames.extend(reader.feed(client.recv(65536)))
        if frames[0][0]!=101:raise ValueError('Expected native challenge')
        _,pos=read_octets(frames[0][1]);version=struct.unpack_from('>I',frames[0][1],pos)[0]
        if version!=601:raise ValueError('Wrong client version')
        client.sendall(frame(100,b'\0\0\0\0'));frames=[]
        while not frames:frames.extend(reader.feed(client.recv(65536)))
        if frames[0]!=(100,b'\0\0\0\0'):raise ValueError('Unauthenticated heartbeat failed')
    previous_pid=candidate['base_pid_at_staging']
    if args.previous_pid is not None:
        previous=json.loads((release/'previous-deployment.json').read_text(encoding='utf-8'))
        if previous['pid']!=args.previous_pid:raise ValueError('Actual previous startup identity mismatch')
        previous_pid=args.previous_pid
    record={'pid':args.pid,'previous_pid':previous_pid,'base_pid_at_staging':candidate['base_pid_at_staging'],
        'recorded_utc':datetime.now(timezone.utc).isoformat(),
        'release':str(release/'run_release.py'),'source_frozen':True,'design_and_catalogs_frozen':True,
        'source_hashes_verified':len(manifest['sha256']),'startup_hashes_match':True,
        'version':version,'unauthenticated_heartbeat':'passed','quick_check':integrity,
        'preexisting_tables_preserved':len(before),'preexisting_rows_unchanged':True,'added_empty_tables':added,
        'role_or_task_rewrite':False,'real_roles_deleted':0,'automatic_resource_profile_migration':False,
        'native_gui_verified':False,'real_authentication':False,'battle_executed_by_this_batch':False,
        'backup':str(release/'accounts-at-stop.sqlite3'),'changed_modules':manifest['changed_modules'],
        'scope':manifest.get('scope','scoped immutable source release')}
    for path in (release/'deployment-verification.json',ROOT/'evidence/latest-deployment-verification.json',
                 ROOT/'evidence'/(candidate.get('verification_name','master-ready-exit')+'-deployment-verification.json')):
        pending=path.with_suffix('.pending.json')
        pending.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8');pending.replace(path)
    print(json.dumps(record,ensure_ascii=True))


if __name__=='__main__':main()
