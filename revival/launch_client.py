"""Launch only the isolated client and correct its verified RGBA format constant.

This compatibility candidate never attaches to an existing process or changes an
executable/resource on disk. Use --check-only to inspect guards without launching.
"""
import argparse
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import time

OUT = Path(__file__).resolve().parent
CLIENT = OUT / 'runtime/client/bin/knightclient.exe'
EXPECTED_HASH = 'ec3763022d28c33d47d8ad5c09cf8e1a2edcdfd3d7c87a51732bfe536aae7535'
INSTRUCTION_VA = 0x79687a
OLD_INSTRUCTION = bytes.fromhex('c744241420000000')
NEW_INSTRUCTION = bytes.fromhex('c744241415000000')


def validate_copy():
    client = CLIENT.resolve(strict=True)
    runtime = (OUT / 'runtime/client').resolve(strict=True)
    if client != runtime / 'bin/knightclient.exe':
        raise RuntimeError('Client path escaped the dedicated runtime copy')
    raw = client.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != EXPECTED_HASH:
        raise RuntimeError('Runtime executable differs from the reviewed compatibility candidate')
    pe = struct.unpack_from('<I', raw, 0x3c)[0]
    if struct.unpack_from('<I', raw, pe + 24 + 28)[0] != 0x400000:
        raise RuntimeError('Unexpected executable image base')
    if b'level="asInvoker"' not in raw:
        raise RuntimeError('The runtime copy does not request ordinary user privileges')
    return client, digest


def bind_windows():
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    size_t = ctypes.c_size_t
    kernel.ReadProcessMemory.argtypes = [wintypes.HANDLE,wintypes.LPCVOID,wintypes.LPVOID,size_t,ctypes.POINTER(size_t)]
    kernel.ReadProcessMemory.restype = wintypes.BOOL
    kernel.WriteProcessMemory.argtypes = [wintypes.HANDLE,wintypes.LPVOID,wintypes.LPCVOID,size_t,ctypes.POINTER(size_t)]
    kernel.WriteProcessMemory.restype = wintypes.BOOL
    kernel.VirtualProtectEx.argtypes = [wintypes.HANDLE,wintypes.LPVOID,size_t,wintypes.DWORD,ctypes.POINTER(wintypes.DWORD)]
    kernel.VirtualProtectEx.restype = wintypes.BOOL
    kernel.FlushInstructionCache.argtypes = [wintypes.HANDLE,wintypes.LPCVOID,size_t]
    kernel.FlushInstructionCache.restype = wintypes.BOOL
    kernel.GetProcessId.argtypes = [wintypes.HANDLE]
    kernel.GetProcessId.restype = wintypes.DWORD
    return kernel


def require_ordinary_token():
    advapi = ctypes.WinDLL('advapi32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    advapi.OpenProcessToken.argtypes = [wintypes.HANDLE,wintypes.DWORD,ctypes.POINTER(wintypes.HANDLE)]
    advapi.OpenProcessToken.restype = wintypes.BOOL
    advapi.GetTokenInformation.argtypes = [wintypes.HANDLE,ctypes.c_int,wintypes.LPVOID,wintypes.DWORD,ctypes.POINTER(wintypes.DWORD)]
    advapi.GetTokenInformation.restype = wintypes.BOOL
    token = wintypes.HANDLE()
    if not advapi.OpenProcessToken(kernel.GetCurrentProcess(), 8, ctypes.byref(token)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        elevated = wintypes.DWORD()
        returned = wintypes.DWORD()
        if not advapi.GetTokenInformation(token,20,ctypes.byref(elevated),ctypes.sizeof(elevated),ctypes.byref(returned)):
            raise ctypes.WinError(ctypes.get_last_error())
        if elevated.value:
            raise RuntimeError('Launch from an ordinary user session; elevated execution is refused')
    finally:
        kernel.CloseHandle(token)


def read_instruction(kernel, handle):
    buffer = ctypes.create_string_buffer(8)
    count = ctypes.c_size_t()
    ok = kernel.ReadProcessMemory(handle,INSTRUCTION_VA,buffer,8,ctypes.byref(count))
    return bytes(buffer.raw) if ok and count.value == 8 else None


def apply_verified_patch(kernel, handle):
    if read_instruction(kernel, handle) != OLD_INSTRUCTION:
        raise RuntimeError('Instruction changed before patch; refusing the write')
    old_protection = wintypes.DWORD()
    if not kernel.VirtualProtectEx(handle,INSTRUCTION_VA,8,0x40,ctypes.byref(old_protection)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        if read_instruction(kernel, handle) != OLD_INSTRUCTION:
            raise RuntimeError('Instruction changed after protection change; refusing the write')
        count = ctypes.c_size_t()
        byte = ctypes.create_string_buffer(b'\x15')
        if not kernel.WriteProcessMemory(handle,INSTRUCTION_VA+4,byte,1,ctypes.byref(count)) or count.value != 1:
            raise RuntimeError('Failed to write the single verified format byte')
        if read_instruction(kernel, handle) != NEW_INSTRUCTION:
            raise RuntimeError('Patched instruction verification failed')
    finally:
        ignored = wintypes.DWORD()
        if not kernel.VirtualProtectEx(handle,INSTRUCTION_VA,8,old_protection.value,ctypes.byref(ignored)):
            raise ctypes.WinError(ctypes.get_last_error())
    if not kernel.FlushInstructionCache(handle,INSTRUCTION_VA,8):
        raise ctypes.WinError(ctypes.get_last_error())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-only',action='store_true')
    args = parser.parse_args()
    if os.name != 'nt':
        raise SystemExit('Windows is required')
    client,digest = validate_copy()
    if args.check_only:
        print(json.dumps({'validated_client':str(client),'sha256':digest,
                          'instruction_va':hex(INSTRUCTION_VA),'expected_instruction':OLD_INSTRUCTION.hex(),
                          'candidate_instruction':NEW_INSTRUCTION.hex(),'launched':False},ensure_ascii=False))
        return
    require_ordinary_token()
    kernel = bind_windows()
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    log_path = OUT / 'evidence' / f'client-launch-{timestamp}.json'
    log = {'started_utc':timestamp,'client':str(client),'sha256':digest,
           'instruction_va':hex(INSTRUCTION_VA),'write_va':hex(INSTRUCTION_VA+4),
           'expected_instruction':OLD_INSTRUCTION.hex(),'candidate_instruction':NEW_INSTRUCTION.hex(),
           'existing_process_attached':False,'disk_files_modified':False,'status':'starting'}
    process = None
    try:
        # Direct child creation returns the owned process handle. No OpenProcess.
        process = subprocess.Popen([str(client)],cwd=client.parent.parent,
                                   stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        log['owned_pid'] = process.pid
        handle = wintypes.HANDLE(int(process._handle))
        if kernel.GetProcessId(handle) != process.pid:
            raise RuntimeError('Created process handle identity mismatch')
        deadline = time.monotonic() + 20
        latest = None
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f'Owned client exited before unpacking: {process.returncode}')
            latest = read_instruction(kernel,handle)
            if latest == OLD_INSTRUCTION:
                break
            time.sleep(0.02)
        else:
            log['last_observed_instruction'] = latest.hex() if latest is not None else None
            raise RuntimeError('Timed out waiting for the exact unpacked instruction; nothing was written')
        apply_verified_patch(kernel,handle)
        log['status'] = 'patch_applied_readback_verified'
        log['visual_validation'] = 'pending_real_client_screenshot'
        print('Client started; RGBA texture format compatibility patch verified.')
    except Exception as error:
        log['status'] = 'failed'
        log['error'] = str(error)
        if process is not None and process.poll() is None:
            process.terminate()
            process.wait(timeout=10)
            log['owned_child_terminated'] = True
        raise
    finally:
        log_path.write_text(json.dumps(log,ensure_ascii=False,indent=2),encoding='utf-8')
        print(f'Launch report: {log_path}')


if __name__ == '__main__':
    main()
