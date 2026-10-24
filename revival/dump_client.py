"""Read only the running isolated game image for offline protocol investigation."""
import ctypes as C
from ctypes import wintypes as W
import json
from inspect_client import OUT


def main():
    info = json.loads((OUT / 'evidence/live-client-module.json').read_text(encoding='utf-8-sig'))
    kernel = C.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [W.DWORD, W.BOOL, W.DWORD]
    kernel.OpenProcess.restype = W.HANDLE
    kernel.ReadProcessMemory.argtypes = [W.HANDLE, C.c_void_p, C.c_void_p, C.c_size_t, C.POINTER(C.c_size_t)]
    kernel.CloseHandle.argtypes = [W.HANDLE]
    handle = kernel.OpenProcess(0x410, False, info['pid'])
    if not handle:
        raise C.WinError(C.get_last_error())
    image = bytearray(info['size'])
    read_bytes = 0
    try:
        for start in range(0, len(image), 4096):
            length = min(4096, len(image) - start)
            buffer = C.create_string_buffer(length)
            actual = C.c_size_t()
            if kernel.ReadProcessMemory(handle, C.c_void_p(info['base'] + start), buffer, length, C.byref(actual)):
                image[start:start+actual.value] = buffer.raw[:actual.value]
                read_bytes += actual.value
    finally:
        kernel.CloseHandle(handle)
    (OUT / 'evidence/native-image.bin').write_bytes(image)
    print(json.dumps({'mapped_bytes': len(image), 'readable_bytes': read_bytes}))


if __name__ == '__main__':
    main()
