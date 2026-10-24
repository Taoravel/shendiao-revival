"""Bounded original movement-byte transition probes; stdout only, offline."""
import hashlib
import json
import struct
from pathlib import Path

from native_inspect import DATA
from pfs import PfsArchive
from inspect_client import ROOT
from native_gameplay_probe import probe
from verify_world_movement_reconciliation_native import Reconciliation
from unicorn import UC_HOOK_MEM_WRITE
from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_EIP,
    UC_X86_REG_ESI, UC_X86_REG_ESP)


class Transitions(Reconciliation):
    def __init__(self, tile_flags=0):
        super().__init__()
        self.w(self.role + 0x26c, self.actor)
        self.tile_flags = tile_flags
        self.queries = []
        self.state_writes = []
        self.special_reports = []
        self.halt = set()
        self.uc.hook_add(UC_HOOK_MEM_WRITE, self.on_write)

    def on_write(self, emu, access, address, size, value, user):
        if address <= self.role + 0x218 < address + size:
            self.state_writes.append({'pc': hex(emu.reg_read(UC_X86_REG_EIP)),
                                      'address': hex(address), 'size': size, 'value': value})

    def hook(self, emu, addr, size, user):
        sp = emu.reg_read(UC_X86_REG_ESP)
        if addr in self.halt:
            emu.emu_stop()
        elif addr == self.stop + 0x410:
            self.queries.append({'x': self.read(sp + 4), 'y': self.read(sp + 8),
                                 'flags': self.tile_flags})
            self.ret(8, self.tile_flags)
        elif addr == self.stop + 0x100 and self.read(self.read(sp + 4) + 4) == 0xc0fcf:
            packet = self.read(sp + 4)
            self.special_reports.append({'type': '0xc0fcf',
                'position': struct.unpack('<hh', emu.mem_read(packet + 12, 4)),
                'byte': emu.mem_read(packet + 16, 1)[0]})
            self.ret(4, 1)
        else:
            super().hook(emu, addr, size, user)

    def state(self):
        return self.uc.mem_read(self.role + 0x218, 1)[0]

    def prepare(self, prior):
        self.uc.mem_write(self.role + 0x218, bytes([prior]))
        self.w(self.role + 0x1c8, 0, 0, 0)
        self.state_writes.clear()

    def select_mask(self):
        self.uc.reg_write(UC_X86_REG_ESI, self.role)
        self.uc.reg_write(UC_X86_REG_ESP, self.stack)
        self.uc.emu_start(0x12028f7, 0x120291b, count=1000)
        assert self.uc.reg_read(UC_X86_REG_EIP) == 0x120291b
        return self.read(self.path + 0x48)


class DenseTransitions(Transitions):
    """Original Maze loader + World query; host only provides buffer ABI."""
    map_obj, source_obj = 0x5300000, 0x5301000
    source_buffer, dest_buffer, buffer_vt = 0x5302000, 0x5302100, 0x5302200
    source_data, dest_data = 0x5310000, 0x5350000

    def __init__(self, raw):
        super().__init__()
        self.raw = raw
        assert len(raw) < 0x40000
        self.uc.mem_write(self.source_data, raw)
        self.w(self.source_obj + 4, self.source_buffer)
        self.w(self.map_obj + 0x84 + 4, self.dest_buffer)
        self.w(self.source_buffer, self.buffer_vt)
        self.w(self.dest_buffer, self.buffer_vt)
        for offset in (0xc, 0x14, 0x1c, 0x34):
            self.w(self.buffer_vt + offset, self.stop + 0x700 + offset)
        self.w(self.canvas_vtable + 0x28, 0x6036e0)
        self.w(self.canvas + 0x298, self.map_obj)
        self.uc.reg_write(UC_X86_REG_ESI, self.map_obj + 0x84)
        self.uc.reg_write(UC_X86_REG_EBX, self.source_obj)
        self.w(self.stack, self.stop)
        self.uc.reg_write(UC_X86_REG_ESP, self.stack)
        self.uc.emu_start(0x672490, self.stop, count=100000)
        assert self.uc.reg_read(UC_X86_REG_EIP) == self.stop
        assert self.uc.reg_read(UC_X86_REG_EAX) & 255 == 1
        header, width, height = struct.unpack_from('<III', raw)
        assert (self.read(self.map_obj + 0x8c), self.read(self.map_obj + 0x90),
                self.read(self.map_obj + 0x94)) == (width, height, self.dest_data + header)
        assert bytes(self.uc.mem_read(self.dest_data, len(raw))) == raw

    def hook(self, emu, addr, size, user):
        sp = emu.reg_read(UC_X86_REG_ESP)
        if addr == self.stop + 0x71c:
            self.ret(value=len(self.raw))
        elif addr == self.stop + 0x714:
            self.ret(value=self.source_data)
        elif addr == self.stop + 0x734:
            assert self.read(sp + 4) == len(self.raw)
            self.ret(4)
        elif addr == self.stop + 0x70c:
            self.ret(value=self.dest_data)
        elif addr == 0x19191c2:
            dst, src, count = (self.read(sp + i) for i in (4, 8, 12))
            emu.mem_write(dst, bytes(emu.mem_read(src, count)))
            self.ret(value=dst)
        elif addr == 0x6036e0:
            self.queries.append({'x': struct.unpack('<i', emu.mem_read(sp+4,4))[0],
                'y': struct.unpack('<i', emu.mem_read(sp+8,4))[0], 'original_query': True})
        else:
            super().hook(emu, addr, size, user)

    def jump(self, position, prior=2, missing_map=False):
        self.prepare(prior)
        self.uc.mem_write(self.path + 8, struct.pack('<ff', position[0]*1.5, position[1]))
        if missing_map:
            self.w(self.canvas + 0x298, 0)
        self.call(0x6036e0, position, ecx=self.canvas)
        raw_flags = self.uc.reg_read(UC_X86_REG_EAX)
        self.call(0x12126d0, ecx=self.role)
        return {'position': position, 'raw_flags_u32': raw_flags, 'prior': prior,
            'after': self.state(), 'queries': self.queries, 'outbound': self.special_reports,
            'writes': self.state_writes,
            'original_6284f0_clear': {str(mask): self.clear(position, mask) for mask in (1,8)}}

    def clear(self, position, mask):
        wrapper, query = 0x5303000, 0x5303100
        width, height = self.read(self.map_obj+0x8c), self.read(self.map_obj+0x90)
        self.w(wrapper+4, query)
        self.w(query, width, height, self.read(self.map_obj+0x94), mask, 0, 0, width, height)
        self.uc.reg_write(UC_X86_REG_EAX, position[0] & 0xffffffff)
        self.call(0x6284f0, (wrapper, position[1]))
        result = bool(self.uc.reg_read(UC_X86_REG_EAX) & 255)
        gx, gy = int(position[0]/16), int(position[1]/16)
        expected = 0 <= gx < width and 0 <= gy < height and not (
            self.raw[12+gy*width+gx] & mask)
        assert result == expected
        return result


def check():
    cases = []
    for byte in (0, 1, 255):
        body, decoded = probe(0xdaaab0, 0xe507f0, 0xdaab70, fields={
            12: struct.pack('<hh', 8, 8), 16: bytes([byte])})
        assert body == struct.pack('>hhB', 8, 8, byte) and decoded[16] == byte
        cases.append({'case': 'CRoleJumpStop_codec', 'byte': byte, 'body_hex': body.hex()})
    for prior, value in ((0, 1), (1, 0), (1, 1), (0, 2), (2, 255)):
        r = Transitions(); r.prepare(prior)
        r.call(0x1205c80, (value,), ecx=r.role)
        assert r.state() == value
        assert len(r.state_writes) == int(prior != value)
        assert all(w['pc'] == '0x1205c9d' for w in r.state_writes)
        cases.append({'case': 'setter_raw_byte', 'prior': prior, 'argument': value,
                      'after': r.state(), 'writes': r.state_writes, 'mask': r.select_mask()})
    for prior in (0, 1, 2):
        for flags in (0, 1, 8, 9):
            r = Transitions(flags); r.prepare(prior)
            r.uc.mem_write(r.role + 0x3d6, b'\x02')
            r.call(0x12126d0, ecx=r.role)
            expected = 1 if not flags & 8 else 0 if not flags & 1 else prior
            assert r.state() == expected, (prior, flags, r.state())
            assert r.special_reports == [{'type': '0xc0fcf', 'position': (8, 8), 'byte': 1}]
            assert r.uc.mem_read(r.role + 0x3d6, 1) == b'\0'
            cases.append({'case': 'local_conversion_completion', 'prior': prior,
                'world_tile_flags': flags, 'after': r.state(), 'mask': r.select_mask(),
                'queries': r.queries, 'writes': r.state_writes,
                'outbound': r.special_reports})
    for prior in (0, 1, 2):
        r = Transitions(); r.prepare(prior)
        r.halt = {0x120d67e}
        r.uc.reg_write(UC_X86_REG_ESI, r.role)
        r.uc.reg_write(UC_X86_REG_ESP, r.stack)
        r.uc.emu_start(0x120d66d, r.stop, count=10000)
        assert r.uc.reg_read(UC_X86_REG_EIP) == 0x120d67e
        assert r.state() == prior and not r.state_writes
        cases.append({'case': 'appearance_reapply_preserves', 'prior': prior,
                      'after': r.state(), 'writes': r.state_writes})
    dense = struct.pack('<III', 12, 2, 2) + bytes((0, 1, 8, 9))
    for point, flags in (((0,0),0), ((16,0),1), ((0,16),8), ((16,16),9),
                         ((-1,0),0), ((-16,0),0xffffffff), ((32,0),0xffffffff),
                         ((0,32),0xffffffff)):
        r = DenseTransitions(dense)
        result = r.jump(point)
        assert result['raw_flags_u32'] == flags
        expected = 1 if not flags & 8 else 0 if not flags & 1 else 2
        assert result['after'] == expected
        cases.append({'case':'original_dense_loader_World_JumpStop', **result})
    r = DenseTransitions(dense)
    result = r.jump((8,8), missing_map=True)
    assert result['raw_flags_u32'] == 0xffffffff and result['after'] == 2
    cases.append({'case':'original_missing_map_preserves', **result})
    entry = 'map_1006_jiaxing/maze.dat'
    raw = PfsArchive(ROOT / 'artres/map.pfs').read(entry)
    _, width, _ = struct.unpack_from('<III', raw)
    for point in ((360,2264), (361,2264), (1664,960)):
        flags = raw[12 + (point[1]//16)*width + point[0]//16]
        r = DenseTransitions(raw); result = r.jump(point)
        assert result['raw_flags_u32'] == flags
        assert result['after'] == (1 if not flags & 8 else 0 if not flags & 1 else 2)
        cases.append({'case':'fresh_PFS_1006_original_loader_World_JumpStop',
            'entry': entry, 'entry_sha256': hashlib.sha256(raw).hexdigest(), **result})
    return {'image_sha256': hashlib.sha256(DATA).hexdigest(),
        'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'base_harness_sha256': hashlib.sha256(Path(__file__).with_name(
            'verify_world_movement_reconciliation_native.py').read_bytes()).hexdigest(),
        'all_passed': True, 'case_count': len(cases), 'cases': cases,
        'adapters': ['inherited Reconciliation presentation/CRT/actor fixture',
            'historical 12 cases: World virtual+28 returns fixture tile flags',
            'dense/fresh cases: original 672490 loader, 6036e0 World query, 11c5c00 and 6284f0 execute',
            'host buffer source length/data and destination reserve/data ABI; CRT memcpy',
            'sender captures original c0fcf object before wire encoding'],
        'not_proven': ['all writers exhausted', 'full conversion animation producer',
            'c0fcf authoritative server meaning', 'full SEnterWorld model construction',
            '1404/516023 special branch gameplay', 'GUI/runtime integration']}


if __name__ == '__main__':
    print(json.dumps(check(), ensure_ascii=False, indent=2))
