"""Recover one approved immutable Windows server outside the tool's kill-job.

No scheduled task, service installation or change to job/security limits.
CREATE_BREAKAWAY_FROM_JOB is required by the observed permitted host contract.
"""
import argparse
import ctypes
from ctypes import wintypes
from datetime import datetime,timezone
import hashlib,json,os
from pathlib import Path
import socket,sqlite3,struct,subprocess,sys,time
from master_ready_preflight import table_state
from service_health_probe import read_frames

ROOT=Path(__file__).resolve().parents[1]


def require(condition,message):
    if not condition:raise ValueError(message)


def is_in_job(pid):
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
    kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.IsProcessInJob.argtypes=[wintypes.HANDLE,wintypes.HANDLE,ctypes.POINTER(wintypes.BOOL)]
    kernel.IsProcessInJob.restype=wintypes.BOOL
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    handle=kernel.OpenProcess(0x1000,False,pid)
    if not handle:raise ctypes.WinError(ctypes.get_last_error())
    try:
        inside=wintypes.BOOL()
        if not kernel.IsProcessInJob(handle,None,ctypes.byref(inside)):
            raise ctypes.WinError(ctypes.get_last_error())
        return bool(inside.value)
    finally:kernel.CloseHandle(handle)


def caller_job_pids():
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.QueryInformationJobObject.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,
        wintypes.DWORD,ctypes.POINTER(wintypes.DWORD)]
    kernel.QueryInformationJobObject.restype=wintypes.BOOL
    data=ctypes.create_string_buffer(65536);size=wintypes.DWORD()
    if not kernel.QueryInformationJobObject(None,3,data,len(data),ctypes.byref(size)):
        raise ctypes.WinError(ctypes.get_last_error())
    assigned,count=struct.unpack_from('<II',data.raw)
    require(assigned==count and count<8191,'Caller job PID query was truncated')
    ids=[ctypes.c_size_t.from_buffer_copy(data.raw,8+i*ctypes.sizeof(ctypes.c_size_t)).value for i in range(count)]
    require(os.getpid() in ids,'Caller job list does not include the caller')
    return ids


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--release',required=True)
    parser.add_argument('--acceptance',type=Path,required=True)
    args=parser.parse_args()
    if Path(args.release).name!=args.release:raise ValueError('Exact release directory name required')
    release=ROOT/'runtime/deployments'/args.release
    manifest=json.loads((release/'manifest.json').read_text(encoding='utf-8'))
    acceptance=json.loads(args.acceptance.read_text(encoding='utf-8'))
    require(acceptance['status']=='accepted_for_main_coordinated_deployment','Release was not approved')
    require(Path(acceptance['release'])==release,'Approved release identity mismatch')
    require(hashlib.sha256((release/'manifest.json').read_bytes()).hexdigest()==acceptance['manifest_sha256'],
        'Approved manifest hash mismatch')
    def verify_source():
        require(hashlib.sha256((release/'run_release.py').read_bytes()).hexdigest()==manifest['runner_sha256'],
            'Immutable runner hash mismatch')
        for name,value in manifest['sha256'].items():
            require(hashlib.sha256((release/'source'/name).read_bytes()).hexdigest()==value,
                'Immutable source hash mismatch: '+name)
    verify_source()
    proof=json.loads((ROOT/'evidence/windows-detached-host-lifetime-verification.json').read_text(encoding='utf-8'))
    require(proof['all_passed'] and proof['normal_died_on_owned_job_close'] and proof['detached_survived_owned_job_close'],
        'Controlled job-close lifetime verification is missing')
    require(proof['source_sha256']==hashlib.sha256((ROOT/'staging/verify_windows_detached_lifetime.py').read_bytes()).hexdigest(),
        'Controlled job-close verifier hash changed')
    # An occupied listener fails rather than terminating/replacing any owner.
    with socket.socket() as available:available.bind(('127.0.0.1',28993))
    recovery=ROOT/'runtime/recoveries'/('detached-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    recovery.mkdir(parents=True,exist_ok=False)
    with sqlite3.connect((ROOT/'runtime/accounts.sqlite3').as_uri()+'?mode=ro',uri=True) as db:
        db.execute('BEGIN');before=table_state(db)
        require(db.execute('PRAGMA quick_check').fetchone()==('ok',),'Formal database integrity failed')
        with sqlite3.connect(recovery/'accounts-before.sqlite3') as saved:db.backup(saved)
    require(len(before)==110,'Unexpected formal schema; no migration authorized')
    flags=0x01000000|subprocess.DETACHED_PROCESS|subprocess.CREATE_NEW_PROCESS_GROUP
    command=[sys.executable,'-B',str(release/'run_release.py')]
    with (recovery/'server-stdout.log').open('ab',buffering=0) as out, (recovery/'server-stderr.log').open('ab',buffering=0) as err:
        process=subprocess.Popen(command,cwd=ROOT.parent,creationflags=flags,stdin=subprocess.DEVNULL,
            stdout=out,stderr=err,close_fds=True)
    # NULL IsProcessInJob means *any* enclosing job and can remain true after
    # successful escape from the caller's kill-job. Check its exact PID list.
    launch_job_pids=caller_job_pids()
    require(process.pid not in launch_job_pids,'Server still belongs to the caller Windows job')
    (ROOT/'runtime/gateway.pid').write_text(str(process.pid),encoding='utf-8')
    sys.path.insert(0,str(release/'source'))
    from wire import FrameReader,frame,read_octets
    deadline=time.monotonic()+30
    client=None
    while time.monotonic()<deadline:
        if process.poll() is not None:raise RuntimeError('Detached approved runner exited; inspect '+str(recovery))
        try:client=socket.create_connection(('127.0.0.1',28993),timeout=min(.5,deadline-time.monotonic()));break
        except OSError:time.sleep(min(.2,max(0,deadline-time.monotonic())))
    if client is None:raise TimeoutError('Detached server did not become ready')
    with client:
        reader=FrameReader();frames=read_frames(client,reader,deadline)
        require(frames[0][0]==101,'Expected native startup challenge')
        _,offset=read_octets(frames[0][1]);version=struct.unpack_from('>I',frames[0][1],offset)[0]
        require(version==601,'Unexpected native client version')
        remaining=deadline-time.monotonic()
        if remaining<=0:raise TimeoutError('Service health probe deadline expired')
        client.settimeout(remaining);client.sendall(frame(100,b'\0'*4))
        frames=read_frames(client,reader,deadline)
        require(frames[0]==(100,b'\0'*4),'Native unauthenticated heartbeat mismatch')
    startup=json.loads((ROOT/'runtime/deployment.json').read_text(encoding='utf-8'))
    expected={name:value for name,value in manifest['sha256'].items() if name.endswith('.py') and '/' not in name}
    require(startup['pid']==process.pid and startup['source_sha256_at_startup']==expected,
        'Actual startup identity or complete source hash set mismatch')
    with sqlite3.connect((ROOT/'runtime/accounts.sqlite3').as_uri()+'?mode=ro',uri=True) as db:
        require(table_state(db)==before,'Recovery changed formal rows')
        require(db.execute('PRAGMA quick_check').fetchone()==('ok',),'Recovered database integrity failed')
    verify_source()
    result=dict(recovery=str(recovery),release=str(release),pid=process.pid,
        verified_utc=datetime.now(timezone.utc).isoformat(),argv=command,creation_flags=flags,
        creation_flags_names=['CREATE_BREAKAWAY_FROM_JOB','DETACHED_PROCESS','CREATE_NEW_PROCESS_GROUP'],
        actual_target_in_windows_job=is_in_job(process.pid),no_console_window=True,
        caller_pid=os.getpid(),caller_job_process_ids_at_launch=launch_job_pids,
        target_in_caller_job=False,controlled_job_close_proof=proof,
        source_files_verified=len(manifest['sha256']),startup_python_hashes=len(expected),
        source_hashes_match=True,version=version,unauthenticated_heartbeat=True,
        before_tables=before,all110_table_rows_unchanged=True,quick_check='ok',
        formal_database_read_only=True,real_authentication=False,native_gui_verified=False,
        scheduled_task_or_service_installed=False,job_limits_modified=False)
    for path in (recovery/'recovery.json',ROOT/'evidence/detached-service-recovery.json'):
        path.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='before_tables'}))


if __name__=='__main__':main()
