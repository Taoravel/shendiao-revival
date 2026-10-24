"""Generate a hash-guarded CPUID compatibility candidate in the runtime copy.

This is an experiment, not a verified login fix. Never patches the original.
"""
import hashlib
import json
from pathlib import Path
import struct
from inspect_client import ROOT, OUT, write_json


def align(value, size):
    return (value + size - 1) // size * size


def main():
    original = ROOT / 'bin/knightclient.exe'
    source = original.read_bytes()
    manifest = json.loads((OUT / 'evidence/original-manifest.json').read_text(encoding='utf-8'))
    key = str(original.relative_to(ROOT))
    if hashlib.sha256(source).hexdigest() != manifest[key]['sha256']:
        raise ValueError('Original executable differs from baseline')
    data = bytearray(source)
    pe = struct.unpack_from('<I', data, 0x3c)[0]
    count = struct.unpack_from('<H', data, pe + 6)[0]
    opt = pe + 24
    optional_size = struct.unpack_from('<H', data, pe + 20)[0]
    sections = opt + optional_size
    base = struct.unpack_from('<I', data, opt + 28)[0]
    sa, fa = struct.unpack_from('<II', data, opt + 32)
    image_size = struct.unpack_from('<I', data, opt + 56)[0]
    new_rva = align(image_size, sa)
    raw = align(len(data), fa)
    new_header = sections + count * 40
    if any(data[new_header:new_header+40]):
        raise ValueError('No vacant PE section header')

    def va(offset):
        for i in range(count):
            o = sections + i * 40
            vs, rva, size, pos = struct.unpack_from('<4I', data, o + 8)
            if pos <= offset < pos + size:
                return base + rva + offset - pos
        raise ValueError('Offset outside file-backed sections')

    sites = [(0x636b, '0fa290e8f5f2ffff', 3),
             (0xa41218, '0fa260f860', None),
             (0xa42566, '0fa29ce8fe0c0000', 3),
             (0xa438e3, '0fa280fb12', None)]
    code = bytearray()
    report = []
    for offset, expected_hex, call_at in sites:
        expected = bytes.fromhex(expected_hex)
        if data[offset:offset+len(expected)] != expected:
            raise ValueError(f'Unexpected instructions at {offset:x}')
        site = va(offset)
        stub = base + new_rva + len(code)
        # CPUID preserves EFLAGS. Save/restore flags around clearing only ECX bit31.
        block = bytearray.fromhex('0fa29c81e1ffffff7f9d')
        tail = bytearray(expected[2:])
        if call_at is not None:
            old_target = site + call_at + 5 + struct.unpack_from('<i', expected, call_at + 1)[0]
            new_call = stub + len(block) + call_at - 2
            struct.pack_into('<i', tail, call_at - 2 + 1, old_target - new_call - 5)
        block += tail
        block += b'\xe9' + struct.pack('<i', site + len(expected) - (stub + len(block) + 5))
        code += block
        data[offset:offset+len(expected)] = b'\xe9' + struct.pack('<i', stub - site - 5) + b'\x90' * (len(expected) - 5)
        report.append({'offset': hex(offset), 'original_va': hex(site), 'stub_va': hex(stub), 'original': expected_hex, 'trampoline': block.hex()})
    raw_size = align(len(code), fa)
    data += b'\0' * (raw - len(data)) + code + b'\0' * (raw_size - len(code))
    data[new_header:new_header+40] = struct.pack('<8s6I2HI', b'.compat\0', len(code), new_rva, raw_size, raw, 0, 0, 0, 0, 0x60000020)
    struct.pack_into('<H', data, pe + 6, count + 1)
    struct.pack_into('<I', data, opt + 56, align(new_rva + len(code), sa))
    struct.pack_into('<I', data, opt + 64, 0)  # checksum will no longer be valid
    struct.pack_into('<II', data, opt + 96 + 4 * 8, 0, 0)  # signature applies to original only
    old_level = b'level="requireAdministrator"'
    new_level = b'level="asInvoker"'.ljust(len(old_level), b' ')
    if data.count(old_level) != 1:
        raise ValueError('Unexpected application manifest')
    data = data.replace(old_level, new_level)
    target = OUT / 'runtime/client/bin/knightclient.exe'
    target.write_bytes(data)
    write_json(OUT / 'evidence/client-compat-candidate.json', {
        'original_sha256': hashlib.sha256(source).hexdigest(),
        'candidate_sha256': hashlib.sha256(data).hexdigest(), 'sites': report,
        'scope': 'CPUID output ECX bit31 only; other registers and query leaves preserved',
        'execution_level': 'asInvoker in runtime copy only',
        'native_verified': False})
    print(str(target))


if __name__ == '__main__':
    main()
