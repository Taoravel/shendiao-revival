"""Controlled owned Windows job closure: normal child dies, detached survives.

Only disposable sleep workers are started/stopped. Existing jobs, services,
listeners, game files and the formal database are never modified.
"""
import ctypes
from ctypes import wintypes as W
from datetime import datetime,timezone
import hashlib,json,os
from pathlib import Path
import subprocess,sys,time

ROOT=Path(__file__).resolve().parents[1]
K=ctypes.WinDLL('kernel32',use_last_error=True)
K.CreateJobObjectW.argtypes=[ctypes.c_void_p,W.LPCWSTR];K.CreateJobObjectW.restype=W.HANDLE
K.SetInformationJobObject.argtypes=[W.HANDLE,ctypes.c_int,ctypes.c_void_p,W.DWORD];K.SetInformationJobObject.restype=W.BOOL
K.AssignProcessToJobObject.argtypes=[W.HANDLE,W.HANDLE];K.AssignProcessToJobObject.restype=W.BOOL
K.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];K.OpenProcess.restype=W.HANDLE
K.IsProcessInJob.argtypes=[W.HANDLE,W.HANDLE,ctypes.POINTER(W.BOOL)];K.IsProcessInJob.restype=W.BOOL
K.CloseHandle.argtypes=[W.HANDLE]
K.GetExitCodeProcess.argtypes=[W.HANDLE,ctypes.POINTER(W.DWORD)];K.GetExitCodeProcess.restype=W.BOOL
K.TerminateProcess.argtypes=[W.HANDLE,W.UINT];K.TerminateProcess.restype=W.BOOL


class Basic(ctypes.Structure):
    _fields_=[('process_time',ctypes.c_int64),('job_time',ctypes.c_int64),('flags',W.DWORD),
        ('min_working',ctypes.c_size_t),('max_working',ctypes.c_size_t),('active',W.DWORD),
        ('affinity',ctypes.c_size_t),('priority',W.DWORD),('scheduling',W.DWORD)]


class Extended(ctypes.Structure):
    _fields_=[('basic',Basic),('io',ctypes.c_uint64*6),('process_mem',ctypes.c_size_t),
        ('job_mem',ctypes.c_size_t),('peak_process',ctypes.c_size_t),('peak_job',ctypes.c_size_t)]


def checked(value):
    if not value:raise ctypes.WinError(ctypes.get_last_error())
    return value


def open_process(pid):return checked(K.OpenProcess(0x1101,False,pid))


def inside(handle,job=None):
    result=W.BOOL();checked(K.IsProcessInJob(handle,job,ctypes.byref(result)));return bool(result.value)


def alive(handle):
    code=W.DWORD();checked(K.GetExitCodeProcess(handle,ctypes.byref(code)));return code.value==259


def producer(directory):
    deadline=time.monotonic()+10
    while not (directory/'go').exists():
        if time.monotonic()>deadline:raise TimeoutError('Producer was not assigned its controlled job')
        time.sleep(.02)
    child=[sys.executable,'-B','-c','import time; time.sleep(90)','controlled-detached-host-probe']
    normal=subprocess.Popen(child,creationflags=subprocess.CREATE_NO_WINDOW,
        stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    detached=subprocess.Popen(child,creationflags=0x01000000|subprocess.DETACHED_PROCESS|subprocess.CREATE_NEW_PROCESS_GROUP,
        stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    (directory/'children.json').write_text(json.dumps(dict(producer=os.getpid(),normal=normal.pid,
        detached=detached.pid)),encoding='utf-8')
    time.sleep(90)


def main():
    if len(sys.argv)==3 and sys.argv[1]=='--producer':producer(Path(sys.argv[2]));return
    directory=ROOT/'evidence'/('windows-detached-host-probe-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    directory.mkdir(exist_ok=False)
    job=checked(K.CreateJobObjectW(None,None));handles=[];result={}
    try:
        limits=Extended();limits.basic.flags=0x2800
        checked(K.SetInformationJobObject(job,9,ctypes.byref(limits),ctypes.sizeof(limits)))
        with (directory/'producer-stderr.log').open('wb') as errors:
            process=subprocess.Popen([sys.executable,'-B',str(Path(__file__).resolve()),'--producer',str(directory)],
                creationflags=subprocess.CREATE_NO_WINDOW,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=errors)
        parent_handle=open_process(process.pid);handles.append(parent_handle)
        checked(K.AssignProcessToJobObject(job,parent_handle))
        assert inside(parent_handle,job)
        (directory/'go').write_text('assigned',encoding='utf-8')
        deadline=time.monotonic()+10
        while not (directory/'children.json').exists():
            if process.poll() is not None:raise RuntimeError('Controlled producer exited: '+str(directory))
            if time.monotonic()>deadline:raise TimeoutError('Controlled children did not start')
            time.sleep(.02)
        children=json.loads((directory/'children.json').read_text(encoding='utf-8'))
        normal=open_process(children['normal']);detached=open_process(children['detached']);handles.extend([normal,detached])
        result.update(children=children,normal_in_owned_job=inside(normal,job),
            detached_in_owned_job=inside(detached,job),detached_in_any_job=inside(detached))
        assert result['normal_in_owned_job'] and not result['detached_in_owned_job']
        checked(K.CloseHandle(job));job=None
        deadline=time.monotonic()+3
        while alive(normal) and time.monotonic()<deadline:time.sleep(.02)
        result.update(normal_died_on_owned_job_close=not alive(normal),
            detached_survived_owned_job_close=alive(detached))
        assert result['normal_died_on_owned_job_close'] and result['detached_survived_owned_job_close']
        result['all_passed']=True
    finally:
        if job:K.CloseHandle(job)
        # Stable handles refer only to this probe's own processes, never reused PIDs.
        for handle in handles:
            if alive(handle):K.TerminateProcess(handle,0)
            K.CloseHandle(handle)
        result.update(source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            owned_job_limits='KILL_ON_JOB_CLOSE|BREAKAWAY_OK',host_job_limits_changed=False,
            live_database_accessed=False,service_started=False)
        (directory/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        (ROOT/'evidence/windows-detached-host-lifetime-verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))


if __name__=='__main__':main()
