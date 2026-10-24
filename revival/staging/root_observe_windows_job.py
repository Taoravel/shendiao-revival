"""Read current tool process job limits; never create/change a job or service."""
import argparse
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import json
import os
from pathlib import Path


class BasicLimits(ctypes.Structure):
    _fields_ = [('process_time', ctypes.c_longlong), ('job_time', ctypes.c_longlong),
        ('flags', wintypes.DWORD), ('min_working_set', ctypes.c_size_t),
        ('max_working_set', ctypes.c_size_t), ('active_process_limit', wintypes.DWORD),
        ('affinity', ctypes.c_size_t), ('priority_class', wintypes.DWORD),
        ('scheduling_class', wintypes.DWORD)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pid', type=int, help='Read external process membership only, without its job limits')
    args = parser.parse_args()
    if args.pid is not None and args.pid < 1:
        parser.error('Positive process ID required')
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    kernel.IsProcessInJob.argtypes = [wintypes.HANDLE, wintypes.HANDLE, ctypes.POINTER(wintypes.BOOL)]
    kernel.IsProcessInJob.restype = wintypes.BOOL
    kernel.QueryInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int,
        ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    kernel.QueryInformationJobObject.restype = wintypes.BOOL
    member, limits, returned = wintypes.BOOL(), BasicLimits(), wintypes.DWORD()
    handle = kernel.GetCurrentProcess() if args.pid is None else kernel.OpenProcess(0x1000, False, args.pid)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        if not kernel.IsProcessInJob(handle, None, ctypes.byref(member)):
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        if args.pid is not None:
            kernel.CloseHandle(handle)
    observed, error = False, None
    if member.value and args.pid is None:
        observed = bool(kernel.QueryInformationJobObject(None, 2, ctypes.byref(limits),
            ctypes.sizeof(limits), ctypes.byref(returned)))
        if not observed:
            error = ctypes.get_last_error()
    flags = limits.flags if observed else None
    report = dict(observed_utc=datetime.now(timezone.utc).isoformat(),
        tool_pid=os.getpid(), tool_parent_pid=os.getppid(),
        observed_process_pid=args.pid or os.getpid(),
        process_in_job=bool(member.value), immediate_job_query_succeeded=observed,
        immediate_job_query_error=error, basic_structure_bytes=ctypes.sizeof(limits),
        returned_bytes=returned.value, immediate_job_limit_flags=flags,
        kill_on_job_close=bool(flags & 0x2000) if flags is not None else None,
        breakaway_ok=bool(flags & 0x800) if flags is not None else None,
        silent_breakaway_ok=bool(flags & 0x1000) if flags is not None else None,
        scope=('Read-only external process membership; no external job limits inferred' if args.pid is not None
            else 'Read-only current tool immediate job; not deceased server cause proof'),
        service_or_job_modified=False, live_database_accessed=False,
        sources=['https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects',
            'https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-queryinformationjobobject',
            'https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_limit_information'])
    name = (f'root-windows-process-job-{args.pid}-20261024.json' if args.pid is not None
        else 'root-windows-tool-job-observation-20261024.json')
    path = Path(__file__).resolve().parents[1]/'evidence'/name
    path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
