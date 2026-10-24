"""Check production compact encoding against the original x86 decoder."""
import json
import struct
import sys
sys.path.insert(0, r'D:/Downloads/LCJDTClient/LCJDTClient/revival/.deps')
import unicorn
from unicorn import x86_const as X
from wire import compact, read_compact, frame, FrameReader
from inspect_client import OUT, write_json


def main():
    mapped = (OUT / 'evidence/native-image.bin').read_bytes()
    samples = [(0, '00'), (127, '7f'), (128, '8080'), (16383, 'bfff'),
               (16384, 'c0004000'), (0xc0002, 'c00c0002'),
               (0x1fffffff, 'dfffffff'), (0x20000000, 'e020000000'),
               (0xffffffff, 'e0ffffffff')]
    for value, expected in samples:
        encoded = bytes.fromhex(expected)
        assert compact(value) == encoded
        u = unicorn.Uc(unicorn.UC_ARCH_X86, unicorn.UC_MODE_32)
        u.mem_map(0x400000, (len(mapped)+4095)//4096*4096)
        u.mem_write(0x400000, mapped)
        u.mem_map(0x8000000, 0x10000)
        stream, buffer, output, stack = 0x8001000, 0x8002000, 0x8003000, 0x800f000
        u.mem_write(buffer-8, struct.pack('<I', len(encoded)))
        u.mem_write(buffer, encoded)
        u.mem_write(stream, struct.pack('<III', 0, buffer, 0))
        u.mem_write(stack, struct.pack('<II', 0x8004000, output))
        u.reg_write(X.UC_X86_REG_ESP, stack)
        u.reg_write(X.UC_X86_REG_ECX, stream)
        u.emu_start(0x7707a0, 0x8004000, count=10000)
        assert struct.unpack('<I', u.mem_read(output, 4))[0] == value
        assert struct.unpack('<I', u.mem_read(stream+8, 4))[0] == len(encoded)
    message = frame(101, b'\x10' + bytes(range(16)) + bytes(10))
    fragmented = 0
    for cut in range(len(message)+1):
        reader = FrameReader()
        assert reader.feed(message[:cut]) + reader.feed(message[cut:]) == [(101, b'\x10' + bytes(range(16)) + bytes(10))]
        fragmented += 1
    result = {'original_x86_compact_decoder': len(samples), 'all_frame_cut_points': fragmented,
              'native_decoder_va': '0x7707a0', 'native_encoder_va': '0x7706b0',
              'authentication_verified': False}
    write_json(OUT / 'evidence/wire-verification.json', result)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
