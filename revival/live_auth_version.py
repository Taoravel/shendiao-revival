"""Read only recognized LoginImpl version fields; never emit credential memory."""
import ctypes as C
from ctypes import wintypes as W
import json
import struct
import sys
from inspect_client import OUT, write_json


class MemoryInfo(C.Structure):
    _fields_ = [('base', C.c_void_p), ('allocation_base', C.c_void_p),
                ('allocation_protect', W.DWORD), ('size', C.c_size_t),
                ('state', W.DWORD), ('protect', W.DWORD), ('type', W.DWORD)]


def main():
    pid = int(sys.argv[1])
    kernel = C.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [W.DWORD, W.BOOL, W.DWORD]
    kernel.OpenProcess.restype = W.HANDLE
    kernel.CloseHandle.argtypes = [W.HANDLE]
    kernel.VirtualQueryEx.argtypes = [W.HANDLE, C.c_void_p, C.POINTER(MemoryInfo), C.c_size_t]
    kernel.VirtualQueryEx.restype = C.c_size_t
    kernel.ReadProcessMemory.argtypes = [W.HANDLE, C.c_void_p, C.c_void_p, C.c_size_t, C.POINTER(C.c_size_t)]
    handle = kernel.OpenProcess(0x410, False, pid)
    if not handle:
        raise C.WinError(C.get_last_error())
    matches = []
    marker = struct.pack('<II', 0x2471914, 0x247196c)
    address = 0
    try:
        while address < 0x80000000:
            info = MemoryInfo()
            if not kernel.VirtualQueryEx(handle, C.c_void_p(address), C.byref(info), C.sizeof(info)):
                break
            base = info.base or 0
            address = base + info.size
            if info.state != 0x1000 or info.type != 0x20000 or info.protect & 0x100 or not info.protect & (4|8|0x40|0x80):
                continue
            for chunk in range(base, address, 16*1024*1024):
                length = min(16*1024*1024+512, address-chunk)
                buffer = C.create_string_buffer(length)
                actual = C.c_size_t()
                if not kernel.ReadProcessMemory(handle, C.c_void_p(chunk), buffer, length, C.byref(actual)):
                    continue
                data = buffer.raw[:actual.value]
                start = 0
                while True:
                    start = data.find(marker, start)
                    if start < 0:
                        break
                    if start+0xd4 <= len(data):
                        matches.append({'address': hex(chunk+start), 'check_version': data[start+0xcc],
                                        'version': struct.unpack_from('<I', data, start+0xd0)[0]})
                    start += 4
    finally:
        kernel.CloseHandle(handle)
    write_json(OUT / 'evidence/live-auth-version.json', {'pid': pid, 'recognized_login_objects': matches})
    print(json.dumps(matches))


if __name__ == '__main__':
    main()
