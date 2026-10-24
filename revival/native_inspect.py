"""Offline mapped-image inspection; addresses are from the running client dump."""
import argparse
from pathlib import Path
import struct
import sys
sys.path.insert(0, r'D:/Downloads/LCJDTClient/LCJDTClient/revival/.deps')
import capstone
from inspect_client import OUT

BASE = 0x400000
DATA = (OUT / 'evidence/native-image.bin').read_bytes()


def u32(va):
    return struct.unpack_from('<I', DATA, va - BASE)[0]


def refs(va):
    value = struct.pack('<I', va)
    offset = 0
    while True:
        offset = DATA.find(value, offset)
        if offset < 0:
            return
        yield BASE + offset
        offset += 1


def vtables(name):
    at = DATA.find(name.encode('ascii') + b'\0')
    if at < 0:
        return []
    result = []
    for ref in refs(BASE + at - 8):
        col = ref - 12
        if u32(col) != 0 or u32(col + 4) != 0:
            continue
        for found in refs(col):
            vtable = found + 4
            if BASE <= u32(vtable) < 0x2280000:
                result.append(vtable)
    return result


def disasm(va, size):
    code = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    for insn in code.disasm(DATA[va-BASE:va-BASE+size], va):
        print(f'{insn.address:08x} {insn.mnemonic:8} {insn.op_str}')


def main():
    args = argparse.ArgumentParser()
    args.add_argument('--class-name')
    args.add_argument('--disasm', type=lambda x: int(x, 0))
    args.add_argument('--refs', type=lambda x: int(x, 0))
    args.add_argument('--size', type=lambda x: int(x, 0), default=256)
    options = args.parse_args()
    if options.class_name:
        for table in vtables(options.class_name):
            print('VTABLE', hex(table), 'FUNCTIONS', [hex(u32(table+i*4)) for i in range(12)])
            print('REFS', [hex(x) for x in refs(table)][:25])
    if options.disasm:
        disasm(options.disasm, options.size)
    if options.refs:
        print([hex(x) for x in refs(options.refs)])


if __name__ == '__main__':
    main()
