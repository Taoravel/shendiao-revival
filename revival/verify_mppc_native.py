"""Offline differential verification against the original client's decoder.

Only Octets memory-management helpers are replaced with simple emulated buffers;
all bit parsing, literal, history, EOS and fragmented input handling are native.
"""
import json
import random
import struct
import sys
from pathlib import Path

sys.path.insert(0, 'D:/Downloads/LCJDTClient/LCJDTClient/revival/.deps')
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_ESI
from mppc import encode, Encoder

BASE = 0x400000
DATA = (Path(__file__).parent / 'evidence/native-image.bin').read_bytes()


class NativeDecoder:
    def __init__(self):
        self.u = u = Uc(UC_ARCH_X86, UC_MODE_32)
        u.mem_map(BASE, (len(DATA) + 4095) & ~4095)
        u.mem_write(BASE, DATA)
        u.mem_map(0x5000000, 0x100000)
        self.state = 0x5000000
        self.octets = 0x5010000
        self.input = 0x5020000
        self.pending = 0x5050000
        self.stack = 0x50f0000
        self.stop = 0x50ffff0
        self.put(self.state + 0x2000, self.state)
        self.put(self.state + 0x2020, self.pending)
        self.put(self.octets + 4, self.input)
        self.put(self.input - 8, 0)
        self.put(self.pending - 8, 0)
        for address in (0x770210, 0x770440, 0x7700d0, 0x77bd20):
            u.hook_add(UC_HOOK_CODE, self.hook, begin=address, end=address)

    def get(self, address):
        return struct.unpack('<I', self.u.mem_read(address, 4))[0]

    def put(self, address, value):
        self.u.mem_write(address, struct.pack('<I', value))

    def ret(self, cleanup=0):
        from unicorn.x86_const import UC_X86_REG_EIP
        sp = self.u.reg_read(UC_X86_REG_ESP)
        target = self.get(sp)
        self.u.reg_write(UC_X86_REG_ESP, sp + 4 + cleanup)
        self.u.reg_write(UC_X86_REG_EIP, target)

    def hook(self, u, address, size, _):
        sp = u.reg_read(UC_X86_REG_ESP)
        this = u.reg_read(UC_X86_REG_ECX)
        if address == 0x770210:  # Octets make_unique; buffers already private.
            self.ret()
        elif address == 0x770440:  # Octets insert(position, source, count).
            position, source, count = (self.get(sp + i) for i in (4, 8, 12))
            ptr = self.get(this + 4)
            length = self.get(ptr - 8)
            offset = position - ptr
            old = bytes(u.mem_read(ptr, length))
            incoming = bytes(u.mem_read(source, count))
            result = old[:offset] + incoming + old[offset:]
            u.mem_write(ptr, result)
            self.put(ptr - 8, len(result))
            self.ret(12)
        elif address == 0x7700d0:  # Octets reserve; buffers have ample space.
            u.reg_write(UC_X86_REG_EAX, this + 12)
            self.ret(4)
        elif address == 0x77bd20:  # Octets erase(first,last).
            first, last = self.get(sp + 4), self.get(sp + 8)
            ptr = self.get(this + 4)
            length = self.get(ptr - 8)
            old = bytes(u.mem_read(ptr, length))
            result = old[:first-ptr] + old[last-ptr:]
            u.mem_write(ptr, result)
            self.put(ptr - 8, len(result))
            self.ret(8)

    def feed(self, compressed):
        self.u.mem_write(self.input, compressed)
        self.put(self.input - 8, len(compressed))
        self.put(self.stack, self.stop)
        self.put(self.stack + 4, self.octets)
        self.u.reg_write(UC_X86_REG_ESP, self.stack)
        self.u.reg_write(UC_X86_REG_ESI, self.state)
        self.u.emu_start(0x78c390, self.stop, count=5000000)
        length = self.get(self.input - 8)
        return bytes(self.u.mem_read(self.input, length))


def main():
    rng = random.Random(2118)
    cases = [b'', b'\0', bytes.fromhex('010203807f80ff'), bytes(range(256)),
             bytes(rng.randrange(256) for _ in range(8192)),
             bytes(rng.randrange(256) for _ in range(20000))]
    checks = []
    for plain in cases:
        encoded = encode(plain)
        for chunk in (1, 2, 3, 7, len(encoded)):
            decoder = NativeDecoder()
            actual = b''.join(decoder.feed(encoded[i:i+chunk]) for i in range(0, len(encoded), chunk))
            assert actual == plain, (len(plain), chunk, len(actual))
            checks.append({'bytes': len(plain), 'chunk_size': chunk, 'decoded': len(actual)})
    decoder = NativeDecoder()
    encoder = Encoder()
    for plain in cases * 2:
        assert decoder.feed(encoder.encode(plain)) == plain
    output = Path(__file__).parent / 'evidence/mppc-native-validation.json'
    output.write_text(json.dumps({'checks': checks, 'continuous_blocks': len(cases)*2}, indent=2), encoding='utf-8')
    print(output)
    print('30 fragmented native-decoder checks and 12 continuous blocks passed')


if __name__ == '__main__':
    main()
