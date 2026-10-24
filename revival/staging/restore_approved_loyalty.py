"""Snapshot/check recovery of the last approved immutable service, no login."""
import argparse
from datetime import datetime,timezone
import hashlib,json
from pathlib import Path
import socket,sqlite3,struct,sys
from master_ready_preflight import table_state

ROOT=Path(__file__).resolve().parents[1]
RELEASE=ROOT/'runtime/deployments/npc-loyalty-20261023T193742Z'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--recovery',type=Path)
    parser.add_argument('--pid',type=int);args=parser.parse_args()
    manifest=json.loads((RELEASE/'manifest.json').read_text(encoding='utf-8'))
    acceptance=json.loads((ROOT/'evidence/reviews/npc-loyalty-release-20261024-r2/acceptance-root.json').read_text(encoding='utf-8'))
    assert acceptance['status']=='accepted_for_main_coordinated_deployment'
    assert hashlib.sha256((RELEASE/'manifest.json').read_bytes()).hexdigest()==acceptance['manifest_sha256']
    assert hashlib.sha256((RELEASE/'run_release.py').read_bytes()).hexdigest()==manifest['runner_sha256']
    for name,value in manifest['sha256'].items():
        assert hashlib.sha256((RELEASE/'source'/name).read_bytes()).hexdigest()==value,name
    if args.pid is None:
        recovery=ROOT/'runtime/recoveries'/('loyalty-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
        recovery.mkdir(parents=True,exist_ok=False)
        with sqlite3.connect((ROOT/'runtime/accounts.sqlite3').as_uri()+'?mode=ro',uri=True) as db:
            db.execute('BEGIN');before=table_state(db)
            assert db.execute('PRAGMA quick_check').fetchone()==('ok',)
            with sqlite3.connect(recovery/'accounts-before.sqlite3') as saved:db.backup(saved)
        assert len(before)==110,'Unexpected current formal database schema'
        record=dict(recovery=str(recovery),release=str(RELEASE),approved_source_files=len(manifest['sha256']),
            before_tables=before,quick_check_before='ok',formal_database_read_only=True,started=False)
        (recovery/'recovery.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
        (ROOT/'staging/loyalty-recovery.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
        print(json.dumps(dict(recovery=str(recovery),tables=len(before),source_files=len(manifest['sha256']))));return
    assert args.recovery is not None
    record=json.loads((args.recovery/'recovery.json').read_text(encoding='utf-8'))
    startup=json.loads((ROOT/'runtime/deployment.json').read_text(encoding='utf-8'))
    assert startup['pid']==args.pid
    for name,value in startup['source_sha256_at_startup'].items():assert manifest['sha256'][name]==value,name
    with sqlite3.connect((ROOT/'runtime/accounts.sqlite3').as_uri()+'?mode=ro',uri=True) as db:
        assert table_state(db)==record['before_tables'],'Approved restore changed formal database rows'
        assert db.execute('PRAGMA quick_check').fetchone()==('ok',)
    sys.path.insert(0,str(RELEASE/'source'))
    from wire import FrameReader,frame,read_octets
    with socket.create_connection(('127.0.0.1',28993),timeout=5) as client:
        reader=FrameReader();frames=[]
        while not frames:frames.extend(reader.feed(client.recv(65536)))
        assert frames[0][0]==101
        _,offset=read_octets(frames[0][1]);version=struct.unpack_from('>I',frames[0][1],offset)[0]
        assert version==601
        client.sendall(frame(100,b'\0'*4));frames=[]
        while not frames:frames.extend(reader.feed(client.recv(65536)))
        assert frames[0]==(100,b'\0'*4)
    record.update(started=True,pid=args.pid,verified_utc=datetime.now(timezone.utc).isoformat(),
        startup_python_hashes=len(startup['source_sha256_at_startup']),source_hashes_match=True,
        version=version,unauthenticated_heartbeat=True,all110_table_rows_unchanged=True,
        quick_check_after='ok',real_authentication=False,native_gui_verified=False)
    (args.recovery/'recovery.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    (ROOT/'evidence/approved-loyalty-service-recovery.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in record.items() if k!='before_tables'}))


if __name__=='__main__':main()
