"""Offline original-image role metadata projections; never opens a client."""
import hashlib
import json
import struct
from contextlib import redirect_stdout
from pathlib import Path
from native_inspect import DATA, u32, disasm
from verify_world_intro_black_native import Replay
from verify_world_roles_native import inner_fields
from world_role_protocol import RoleBasic
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_ESP

OUT = Path(__file__).parent / 'evidence'


class MetadataReplay(Replay):
    """Keep original constructors/decoders; adapt external C++ string/atomic ABI."""
    def __init__(self):
        super().__init__()
        self.ctor, self.copy = u32(0x2244450), u32(0x22444b4)
        self.inc, self.dec = u32(0x2244334), u32(0x2244354)
        for address in (self.ctor, self.copy, self.inc, self.dec):
            page = address & ~4095
            if not any(begin <= page <= end for begin, end, _ in self.e.mem_regions()):
                self.e.mem_map(page, 4096)

    def string(self, dst, raw):
        assert len(raw) <= 14
        self.e.mem_write(dst, bytes(28))
        self.w(dst + 20, len(raw) // 2)
        self.w(dst + 24, 7)
        self.e.mem_write(dst + 4, raw + b'\0\0')

    def hook(self, e, a, size, user):
        sp = e.reg_read(UC_X86_REG_ESP)
        if self.imports.get(a) == 'string':
            src, units = self.r(sp + 4), []
            while self.r16(src):
                units.append(self.r16(src)); src += 2
            self.string(e.reg_read(UC_X86_REG_ECX), struct.pack('<' + 'H' * len(units), *units))
            self.ret(4, e.reg_read(UC_X86_REG_ECX))
        elif a == self.ctor:
            dst = e.reg_read(UC_X86_REG_ECX)
            self.string(dst, b''); self.ret(value=dst)
        elif a == self.copy:
            dst, src = e.reg_read(UC_X86_REG_ECX), self.r(sp + 4)
            p = src + 4 if self.r(src + 24) < 8 else self.r(src + 4)
            self.string(dst, bytes(e.mem_read(p, self.r(src + 20) * 2)))
            self.ret(4, dst)
        elif a in (self.inc, self.dec):
            p = self.r(sp + 4)
            value = self.r(p) + (1 if a == self.inc else -1)
            self.w(p, value); self.ret(4, value)
        elif a == 0x19191c2:  # original memcpy import thunk, cdecl
            dst, src, n = (self.r(sp + x) for x in (4, 8, 12))
            e.mem_write(dst, bytes(e.mem_read(src, n))); self.ret(value=dst)
        elif a == 0x6519d0:
            self.calls.append({'original_direction_vector': list(struct.unpack(
                '<3f', e.mem_read(self.r(sp + 4), 12)))})
            self.ret(4)
        else:
            super().hook(e, a, size, user)


def project(packed=0x71, shape=1010109, blob_key=None, blob_value=0):
    r = MetadataReplay()
    inner, outer, inthead, blobhead, node, raw = (0x5010000, 0x5011000,
        0x5014000, 0x5014100, 0x5014200, 0x5015000)
    role = RoleBasic(123456, '侠客', shape, 1680, 5311, packed)
    for off, value in inner_fields(role).items():
        r.e.mem_write(inner + off, value)
    r.w(inner + 0x28, 7)
    for at, head, marker in ((inner + 0x34, inthead, 0x15),
                             (inner + 0x40, blobhead, 0x19)):
        r.w(at + 4, head, 0); r.w(head, head, head, head)
        r.e.mem_write(head + marker, b'\1')
    if blob_key is not None:
        value = struct.pack('>i', blob_value)
        r.w(inner + 0x48, 1); r.w(blobhead, node, node, node)
        r.w(node, blobhead, blobhead, blobhead)
        r.e.mem_write(node + 0xc, bytes([blob_key]))
        r.w(node + 0x10, 0x224c100, raw)
        r.w(raw - 12, 4, 4, 1); r.e.mem_write(raw, value)
    r.w(outer + 0xc, 0x2278e54)
    r.e.mem_write(outer + 0x10, struct.pack('<hhB', 1680, 5311, 0))
    r.w(outer + 0x1c, 0x5013000, 0); r.w(0x5013000, 0x5013000, 0x5013000)
    r.run(0x11dd8a0, r.scene, outer, inner, end=0x11da180)
    info = r.r(r.e.reg_read(UC_X86_REG_ESP) + 4)
    return {f'{off:02x}': r.r(info + off) for off in
            (0x24, 0x48, 0x4c, 0x50, 0x54, 0x7c, 0x88, 0xb4, 0xc8, 0xd8, 0xe0, 0xe4)}


def direction(number):
    r = MetadataReplay()
    player, playervt, sprite, state = 0x5017000, 0x5018000, 0x5019000, 0x501a000
    r.w(player, playervt); r.w(player + 0x48, sprite)
    # Original xor eax,eax;ret boundary = neither alternate movement mode.
    r.w(playervt + 0x158, 0x1209dc4, 0x1209dc4)
    r.w(sprite, 0x2462544); r.w(sprite + 0x1a8, state)
    r.run(0x11f5b00, player, number)
    assert len(r.calls) == 1
    return r.calls[0]['original_direction_vector']


def integer_property_dispatch(key, value):
    class DispatchReplay(MetadataReplay):
        def hook(self, e, a, size, user):
            sp = e.reg_read(UC_X86_REG_ESP)
            if a == 0x11edd30:
                self.calls.append({'original_property_dispatch': [self.r(sp + 4),
                                   self.r(sp + 8), self.r(sp + 12)]})
                self.ret(12)
            elif a == 0x11ec1c0:
                self.calls.append({'original_key1_extra': self.r(sp + 4)}); self.ret(4)
            elif a in (0x11eb1b0, 0x11eb070, 0x11ebb00):
                self.ret()
            else:
                super().hook(e, a, size, user)
    r = DispatchReplay()
    obj, tree, head, node, cachehead = 0x5017000, 0x5018000, 0x5019000, 0x501a000, 0x501b000
    r.w(tree + 4, head, 1); r.w(head, node, node, node)
    r.e.mem_write(head + 0x15, b'\1')
    r.w(node, head, head, head); r.e.mem_write(node + 0xc, bytes([key]))
    r.w(node + 0x10, value)
    r.w(obj + 0xcc, cachehead, 0); r.w(cachehead, cachehead, cachehead, cachehead)
    r.e.mem_write(cachehead + 0x15, b'\1')
    r.run(0x11f0970, obj, tree)
    expected = [{'original_property_dispatch': [key, value, 0]}]
    if key == 1:
        expected.append({'original_key1_extra': value})
    assert r.calls == expected, r.calls
    return r.calls


def main():
    rows = []
    baseline = project()
    for packed in (0x70, 0x71, 0x72, 0x79, 0x7f, 0x01, 0x31, 0xf1):
        observed = project(packed=packed)
        assert observed['48'] == 10 + (packed & 15)
        assert observed['54'] == packed >> 4
        assert {k: v for k, v in observed.items() if k not in ('48', '54')} == {
            k: v for k, v in baseline.items() if k not in ('48', '54')}
        rows.append({'kind': 'packed_single_variable', 'input': packed, 'RoleInfo': observed})
    scalar_dest = {3: '24', 8: 'b4', 12: 'b0', 19: 'd8', 21: '7c',
                   23: 'c8', 25: 'e0', 26: 'e4'}
    for key, dest in scalar_dest.items():
        if dest == 'b0':  # not part of the captured standard projection list yet
            continue
        for value in (111, 37):
            observed = project(blob_key=key, blob_value=value)
            assert observed[dest] == value, (key, dest, observed)
            assert observed['48'] == baseline['48']
            assert observed['54'] == baseline['54']
            rows.append({'kind': 'scalar_blob_single_variable', 'key': key,
                         'BE_i32': value, 'destination': dest, 'RoleInfo': observed})
    vectors = [(0., -1., 0.), (1., -1., 0.), (1., 0., 0.), (1., 1., 0.),
               (0., 1., 0.), (-1., 1., 0.), (-1., 0., 0.), (-1., -1., 0.)]
    for number in range(16):
        observed = direction(number)
        assert observed == list(vectors[number] if number < 8 else (0., 0., 0.))
        rows.append({'kind': 'original_player_to_engine_direction', 'input': number,
                     'original_engine_vector': observed})
    for key in range(1, 7):
        rows.append({'kind': 'original_integer_property_dispatch', 'key': key,
                     'value': 49009, 'calls': integer_property_dispatch(key, 49009)})
    output = {'original_image_sha256': hashlib.sha256(DATA).hexdigest(),
              'passed': len(rows), 'original_handler': '0x11dd8a0',
              'capture_boundary': '0x11da180', 'results': rows,
              'scope': 'Original role metadata handler until engine-player creation; no rendering/UI/client'}
    (OUT / 'world-role-metadata-native.json').write_text(json.dumps(output, indent=2), encoding='utf-8')
    with (OUT / 'world-role-metadata-native-disassembly.txt').open('w', encoding='utf-8') as f:
        with redirect_stdout(f):
            for address, size in ((0x11dd92f, 76), (0x11dda91, 31),
                                  (0x11ddd09, 109), (0x11ddc9c, 109),
                                  (0x11f0970, 620), (0x11edd30, 420),
                                  (0x120c698, 24), (0x120d6c6, 19),
                                  (0x1209d80, 7), (0x11f5b00, 46),
                                  (0x12041c0, 51), (0x89eee0, 11),
                                  (0x652750, 36), (0x651700, 226),
                                  (0xc99111, 16), (0x86a4c5, 6),
                                  (0xc976eb, 16), (0x89b6b5, 6)):
                print('\n' + hex(address)); disasm(address, size)
    print(json.dumps({'passed': len(rows), 'output': str(OUT / 'world-role-metadata-native.json')}))


if __name__ == '__main__':
    main()
