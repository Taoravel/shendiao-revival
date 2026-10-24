"""Offline original local-player movement correction dispatch/state probes."""
from pathlib import Path
import hashlib
import json
import struct

from native_inspect import BASE, DATA, capstone, u32
from native_gameplay_probe import probe
from verify_movement_reports_native import OriginalReports
from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_EIP, UC_X86_REG_ESP

ROOT = Path(__file__).resolve().parent


class Reconciliation(OriginalReports):
    packet, canvas, canvas_vtable, guard, text = 0x500b000, 0x500d000, 0x500d800, 0x500e000, 0x500e800

    def __init__(self):
        super().__init__()
        self.dynamic_current = True
        self.found_role = self.role
        self.requests = []
        self.position_sets = []
        self.w(0x294454c, self.role)
        self.w(0x2944798, self.guard)
        self.uc.mem_write(0x2945060 + 0x1ed, b'\0')
        self.w(0x29a4a70 + 0x40, self.canvas)
        self.w(self.canvas, self.canvas_vtable)
        self.w(self.canvas_vtable + 0xc, self.stop + 0x400)
        self.w(self.canvas_vtable + 0x28, self.stop + 0x410)
        self.make_list(self.path + 0x20, (), floats=True)
        self.make_list(self.path + 0x38, (), floats=True)
        self.make_list(self.path + 0x2c, ((56., 8.), (56., 56.)), floats=True)
        self.make_list(self.role + 0x340, ((56., 8.), (56., 56.)), floats=True)
        self.make_list(self.role + 0x34c, ((8, 8),))
        self.w(self.role + 0x328, 56, 56)
        self.w(self.role + 0x364, 56, 8)
        self.uc.mem_write(self.path + 8, struct.pack('<ff', 12., 8.))
        self.w(self.packet + 8, 42, 0)
        self.w(self.packet + 0x10, 0x2278e54)
        self.uc.mem_write(self.packet + 0x14, struct.pack('<hhB', 100, 100, 0))
        for addr in (u32(0x22443e8), u32(0x22443ec)):
            if not BASE <= addr < BASE + len(DATA) and addr & ~4095 not in getattr(self, 'mapped_imports', set()):
                self.uc.mem_map(addr & ~4095, 4096)
                self.mapped_imports = getattr(self, 'mapped_imports', set()) | {addr & ~4095}

    def hook(self, emu, addr, size, user):
        sp = emu.reg_read(UC_X86_REG_ESP)
        if addr == self.stop + 0x100:
            packet = self.read(sp + 4)
            kind = self.read(packet + 4)
            if kind != 0xc0faf:
                super().hook(emu, addr, size, user)
                return
            self.requests.append({'operation': 'client_relocation_report', 'type': hex(kind),
                'field_8_u64': struct.unpack('<Q', emu.mem_read(packet + 8, 8))[0],
                'position': struct.unpack('<hh', emu.mem_read(packet + 0x14, 4)),
                'state_byte': emu.mem_read(packet + 0x18, 1)[0]})
            self.ret(4, 1)
        elif addr == 0x11d5330:
            self.ret(8, self.found_role)
        elif addr == 0x11d5400:
            self.ret(8, 0)  # No companion actor in this fixture.
        elif addr == 0x837060:
            self.ret(value=self.text)
        elif addr == u32(0x22443e8):
            self.ret(value=self.text + 4)
        elif addr == u32(0x22443ec):
            self.ret()
        elif addr == 0x806de0:
            self.ret()
        elif addr == self.stop + 0x400:
            out = self.read(sp + 4)
            self.w(out, 8192, 8192)
            self.ret(4, out)
        elif addr == self.stop + 0x410:
            self.ret(8, 0)  # Scene tile flags clear; original mask test runs.
        elif addr == 0x12143b0:
            self.requests.append({'operation': 'replan_old_target', 'x': self.read(sp + 4), 'y': self.read(sp + 8)})
            self.ret(12, 1)
        elif addr in (0x120fcc0, 0x1212390, 0x1212240, 0x120f110, 0x12172f0):
            self.ret()
        elif addr in (0x844a90, 0x11f5ad0):
            self.ret(8, 0)
        elif addr == 0x1212430:
            self.ret(4)
        elif addr == 0x11e9500:
            self.ret(8, 0)  # Animation resource boundary.
        elif addr == 0x11eb000:
            self.ret(value=0)  # No queued animation action in this fixture.
        elif addr == 0x1203620:
            self.ret(12)  # Animation/action reset boundary.
        elif addr == 0x11f5e20:
            self.ret(4)  # Appearance update; original +218 byte setter retained.
        elif addr == 0x6526f0:
            point = struct.unpack('<ii', emu.mem_read(self.read(sp + 4), 8))
            self.position_sets.append(point)  # Observe actual engine setter.
        else:
            super().hook(emu, addr, size, user)

    def process(self, address):
        self.call(address, (0, 0), ecx=self.packet)
        self.call(0x12061a0, (self.packet + 0x100,), ecx=self.role)
        return {'current': struct.unpack('<ii', self.uc.mem_read(self.packet + 0x100, 8)),
            'position_sets_projected': self.position_sets, 'requests': self.requests,
            'future_engine': self.points(self.path + 0x2c, floats=True),
            'future_local': self.points(self.role + 0x340, floats=True),
            'history_local': self.points(self.role + 0x34c),
            'movement_state_218': self.uc.mem_read(self.role + 0x218, 1)[0],
            'target_328': struct.unpack('<ii', self.uc.mem_read(self.role + 0x328, 8)),
            'lookahead_358': struct.unpack('<ii', self.uc.mem_read(self.role + 0x358, 8))}


def main():
    cases = []
    # Same packet/role, exactly one guard change per fixture.
    for name, field, value, expected in (
        ('baseline', None, 0, True),
        ('scene_absent', 0x2944564, 0, False),
        ('main_absent', 0x294454c, 0, False),
        ('world_mode_54', 'world', 1, False),
        ('app_mode_1ed', 'app', 1, False),
        ('role_flag_10', 'role', 0x10, False),
        ('role_flag_4', 'role', 4, False),
        ('role_flag_8', 'role', 8, False),
        ('other_role_flag_1', 'role', 1, True)):
        run = Reconciliation()
        if isinstance(field, int):
            run.w(field, value)
        elif field == 'world':
            run.w(run.guard + 0x54, value)
        elif field == 'app':
            run.uc.mem_write(0x2945060 + 0x1ed, bytes([value]))
        elif field == 'role':
            run.w(run.role + 0x214, value)
        actual = run.process(0x11d7fc0)
        assert bool(actual['position_sets_projected']) == expected, (name, actual)
        if expected:
            assert actual['current'] == (100, 100)
            assert actual['requests'] == [{'operation': 'replan_old_target', 'x': 56, 'y': 56}]
        cases.append({'case': 'SRoleMove_local_' + name, 'result': actual})

    for flag in (0, 1, 2):
        run = Reconciliation()
        run.uc.mem_write(run.packet + 0x18, bytes([flag]))
        actual = run.process(0x11d7a20)
        assert actual['current'] == (100, 100)
        assert actual['movement_state_218'] == int(flag == 1)
        assert actual['target_328'] == actual['lookahead_358'] == (100, 100)
        assert actual['future_engine'] == []
        assert actual['future_local'] == [(56., 8.), (56., 56.)]
        assert actual['history_local'] == [(8, 8)]
        assert actual['requests'] == []
        cases.append({'case': 'SSetRoleLocation_local_flag_' + str(flag), 'result': actual})

    for name, field, value, moved in (
        ('role_flag_10_does_not_gate', 'role', 0x10, True),
        ('world_mode_does_not_gate', 'world', 1, True),
        ('app_mode_does_not_gate', 'app', 1, True),
        ('virtual_158_blocks_actor_write', '158', 1, False),
        ('virtual_15c_blocks_actor_write', '15c', 1, False)):
        run = Reconciliation()
        if field == 'role':run.w(run.role + 0x214, value)
        elif field == 'world':run.w(run.guard + 0x54, value)
        elif field == 'app':run.uc.mem_write(0x2945060 + 0x1ed, bytes([value]))
        elif field == '158':run.w(run.role + 0x2c0, value)
        elif field == '15c':run.w(run.role + 0x2cc, value)
        actual = run.process(0x11d7a20)
        assert bool(actual['position_sets_projected']) == moved
        assert actual['target_328'] == (100, 100)
        assert actual['current'] == ((100, 100) if moved else (8, 8))
        cases.append({'case': 'SSetRoleLocation_' + name, 'result': actual})

    run = Reconciliation()
    run.process(0x11d7a20)
    run.call(0x12171d0, (0, 1))
    assert run.sent[-1]['current'] == (100, 100)
    assert run.sent[-1]['points'] == [(8, 8)]
    cases.append({'case': 'SSetRoleLocation_then_CHECK_retains_old_history', 'sent': run.sent[-1]})

    # Distinct location messages: neither assume generic resync nor Stop effect.
    run = Reconciliation()
    actual = run.process(0x11c56c0)
    assert actual['current'] == (8, 8) and actual['position_sets_projected'] == []
    cases.append({'case': 'SRoleStop_no_op', 'result': actual})
    run = Reconciliation()
    actual = run.process(0x11c9f90)
    assert actual['current'] == (8, 8) and actual['position_sets_projected'] == []
    assert actual['requests'][0]['operation'] == 'client_relocation_report'
    assert actual['requests'][0]['position'] == (8, 8)
    cases.append({'case': 'SRelocateRolePos_requests_current_report', 'result': actual})
    for mode, expected in ((1, (31, 32)), (2, (41, 42)), (3, None)):
        run = Reconciliation()
        run.w(run.role + 0x13c, mode)
        run.w(run.role + 0x150, 31, 32)
        run.w(run.role + 0x158, 41, 42)
        run.uc.mem_write(run.role + 0x3d6, b'\x01')
        actual = run.process(0x11c9f90)
        if expected is None:
            assert actual['requests'] == []
        else:
            assert actual['requests'][0]['position'] == expected
            assert actual['requests'][0]['state_byte'] == 1
        cases.append({'case': 'SRelocateRolePos_special_13c_' + str(mode), 'result': actual})

    codecs = []
    for flag in (0, 1, 2):
        body, decoded = probe(0xdad6d0, 0xe50f60, 0xdad780, fields={
            8: struct.pack('<q', 42), 0x14: struct.pack('<hh', 100, 100), 0x18: bytes([flag])})
        assert body == struct.pack('>qhhB', 42, 100, 100, flag)
        assert decoded[0x18] == flag
        codecs.append({'type': '0xc0fa4', 'flag': flag, 'hex': body.hex()})
    body, _ = probe(0xdabe80, 0xdabea0, 0xdabeb0)
    assert body == b''
    codecs.append({'type': '0xc0fbb', 'hex': ''})
    body, decoded = probe(0xdaa6b0, 0xe50770, 0xdaa7a0, fields={
        8: struct.pack('<Q', 0x1122334455667788), 0x14: struct.pack('<hh', 8, 8), 0x18: b'\x01'})
    assert body == struct.pack('>QhhB', 0x1122334455667788, 8, 8, 1)
    codecs.append({'type': '0xc0faf', 'hex': body.hex()})
    report = {'image_sha256': hashlib.sha256(DATA).hexdigest(), 'cases': cases, 'codecs': codecs,
        'scope': 'original handlers, gates, virtual position setter, engine queue clear and main coordinate fields; unrelated UI/animation/speed helpers adapted',
        'adapters': ['memory alloc/free/security cookie from OriginalReports', 'scene role-ID/companion lookup',
            'empty map tile flags and fixed renderer dimensions', 'logs/resource text and CRT strings',
            'replan target capture at 12143b0; actual A* not run', 'UI/map-status helpers 120fcc0/1212390/1212240/12172f0/1212430',
            'animation 11e9500/11eb000/1203620; camera-offset 11f5ad0', 'movement speed helper120f110 and appearance11f5e20',
            'network output capture'],
        'no_client_gui_service_started': True}
    (ROOT / 'evidence/world-movement-reconciliation-native.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    cs = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    text = 'native-image.bin SHA256 ' + report['image_sha256'] + '\n'
    for start, length in ((0x11d7fc0, 0x1aa), (0x1212080, 0xc7), (0x1217460, 0x111),
        (0x11d7a20, 0x6a), (0x1213b80, 0x178), (0x11f6480, 0x53), (0x11f6120, 0x32b),
        (0x6526f0, 0x54), (0x120b6f0, 0x88), (0x1202bd0, 0x11), (0x806ba0, 0x1d),
        (0x11c9f90, 0x12), (0x11c56c0, 3), (0xdad6d0, 0x2a), (0xe50f60, 0x50),
        (0x1212890, 0x1df), (0xdabe80, 0x40), (0xe50770, 0x60), (0x1203da0, 0x34), (0x1203e30, 0x19)):
        text += '\n' + '\n'.join(f'{i.address:08x} {i.mnemonic:8} {i.op_str}'
            for i in cs.disasm(DATA[start-BASE:start-BASE+length], start)) + '\n'
    (ROOT / 'evidence/world-movement-reconciliation-native-disassembly.txt').write_text(text, encoding='utf-8')
    print(json.dumps({'handler_cases': len(cases), 'original_codec_cases': len(codecs)}))


if __name__ == '__main__':
    main()
