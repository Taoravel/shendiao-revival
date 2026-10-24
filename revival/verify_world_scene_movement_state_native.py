"""Offline SRoleEnterScene byte consumers; no process, socket or state writes.

Runs original image codecs, Process argument construction, scene success/gate
slice, real main-character relocation/state setter, and original mask selector.
The synchronous resource loader and presentation systems are explicit seams.
"""
import hashlib
import json
import struct
from pathlib import Path

from native_inspect import DATA, u32
from native_gameplay_probe import probe
from pfs import PfsArchive
from bxml import decode
from verify_world_movement_reconciliation_native import Reconciliation
from unicorn.x86_const import (UC_X86_REG_EBP, UC_X86_REG_EBX, UC_X86_REG_ECX,
    UC_X86_REG_EDI, UC_X86_REG_EIP, UC_X86_REG_ESI, UC_X86_REG_ESP)


class SceneStateProbe(Reconciliation):
    def __init__(self):
        super().__init__()
        self.captured = []
        self.halt_at = set()
        self.weather_lookup = []
        self.stop_after_weather_lookup = False
        self.w(self.role + 0x26c, self.actor)
        self.w(0x294cd3c, 0)
        self.uc.mem_write(0x2945060 + 0x20, b'\0')
        for slot in (0x224446c,):
            addr = u32(slot)
            if not 0x400000 <= addr < 0x400000 + len(DATA):
                page = addr & ~4095
                if page not in getattr(self, 'mapped_imports', set()):
                    self.uc.mem_map(page, 4096)
                    self.mapped_imports = getattr(self, 'mapped_imports', set()) | {page}

    def hook(self, emu, addr, size, user):
        sp = emu.reg_read(UC_X86_REG_ESP)
        if addr in self.halt_at:
            emu.emu_stop()
        elif addr == u32(0x224446c):
            dst, src = emu.reg_read(UC_X86_REG_ECX), self.read(sp + 4)
            # Host wstring copy ABI; these fixtures use empty strings only.
            assert self.read(src + 0x14) == 0
            emu.mem_write(dst, bytes(28))
            self.ret(4, dst)
        elif addr == 0x11e21f0:
            self.captured.append({'operation': 'scene_load_boundary',
                'scene_id': struct.unpack('<Q', emu.mem_read(sp + 4, 8))[0],
                'position': struct.unpack('<ii', emu.mem_read(sp + 12, 8)),
                'reason': self.read(sp + 48),
                # C++ bool ABI uses its low byte; upper EAX bits are retained.
                'normalized_byte_a': self.read(sp + 52) & 255})
            self.ret(52)
        elif addr in (0x120f2b0, 0x120f350):
            self.ret()
        elif addr == 0x1219ff0 and not self.stop_after_weather_lookup:
            self.captured.append({'operation': 'weather_boundary',
                'signed_byte_b': struct.unpack('<i', emu.mem_read(sp + 4, 4))[0]})
            self.ret(32)
        elif addr == self.stop + 0x600:
            self.weather_lookup.append(struct.unpack('<i', emu.mem_read(sp + 4, 4))[0])
            emu.emu_stop()
        else:
            super().hook(emu, addr, size, user)

    def process_prefix(self, a=0, b=0, *, app_gate=False, scene_absent=False):
        self.uc.mem_write(self.packet, bytes(0x80))
        self.uc.mem_write(self.packet + 0x28, struct.pack('<hh', 100, 120))
        self.uc.mem_write(self.packet + 0x2c, bytes([a]))
        self.w(self.packet + 0x38, 1007, 0)
        self.uc.mem_write(self.packet + 0x40, bytes([b]))
        if app_gate:
            self.uc.mem_write(0x2945060 + 0x20, b'\1')
        if scene_absent:
            self.w(0x2944564, 0)
        self.halt_at = {0x11e3219}
        self.call(0x11e3140, (0, 0), ecx=self.packet) if app_gate or scene_absent else self.run_until(0x11e3140, self.packet, (0, 0))
        return self.captured

    def run_until(self, address, obj, args=()):
        self.w(self.stack, self.stop, *args)
        self.uc.reg_write(UC_X86_REG_ESP, self.stack)
        self.uc.reg_write(UC_X86_REG_ECX, obj)
        self.uc.emu_start(address, self.stop, count=150000)
        allowed = self.halt_at | {self.stop}
        if self.stop_after_weather_lookup and self.weather_lookup:
            allowed.add(self.stop + 0x600)
        assert self.uc.reg_read(UC_X86_REG_EIP) in allowed

    def scene_success_slice(self, normalized_a, prior, *, success=1, reason=0, map_id=1007):
        self.uc.mem_write(self.role + 0x218, bytes([prior]))
        self.uc.mem_write(self.stack + 0x17, bytes([success]))
        self.w(self.stack + 0xb0, reason, normalized_a)
        self.w(self.scene + 0x110, map_id)
        self.uc.reg_write(UC_X86_REG_ESP, self.stack)
        self.uc.reg_write(UC_X86_REG_EBX, 0)
        self.uc.reg_write(UC_X86_REG_ESI, self.scene)
        self.uc.reg_write(UC_X86_REG_EBP, 100)
        self.uc.reg_write(UC_X86_REG_EDI, 120)
        self.halt_at = {0x11e26de, 0x11e272d, 0x11e2e7a}
        self.uc.emu_start(0x11e269b, self.stop, count=150000)
        branch = self.uc.reg_read(UC_X86_REG_EIP)
        assert branch in self.halt_at
        state = self.uc.mem_read(self.role + 0x218, 1)[0]
        self.halt_at = set()
        self.uc.reg_write(UC_X86_REG_ESI, self.role)
        self.uc.reg_write(UC_X86_REG_ESP, self.stack)
        self.uc.emu_start(0x12028f7, 0x120291b, count=1000)
        assert self.uc.reg_read(UC_X86_REG_EIP) == 0x120291b
        return {'branch': hex(branch), 'state_218': state,
            'mask': self.read(self.path + 0x48),
            'position_sets_projected': self.position_sets}

    def weather_prefix(self, signed_b):
        # Original cleanup, getter 89dd60 and wrapper 87a970 retained.
        root, provider, vt = 0x5030000, 0x5032000, 0x5032100
        self.w(0x2945aec, root)
        self.w(root + 0x8d0, 0x2259aa8, provider)
        self.w(provider, vt)
        self.w(vt + 8, self.stop + 0x600)
        self.w(0x2944720, 0)
        self.w(self.role + 0x3dc, 0)
        self.uc.mem_write(self.role + 0x218, b'\x02')
        self.stop_after_weather_lookup = True
        self.run_until(0x1219ff0, self.role, (signed_b & 0xffffffff, *([0] * 7)))
        assert self.uc.mem_read(self.role + 0x218, 1)[0] == 2
        return self.weather_lookup

    def scene_preload_gate(self, *, missing_main=False, map_id=1007):
        self.w(self.scene + 0x110, map_id)
        if missing_main:
            self.w(0x294454c, 0)
        self.uc.reg_write(UC_X86_REG_ESI, self.scene)
        self.uc.reg_write(UC_X86_REG_EDI, self.scene + 0x110)
        self.uc.reg_write(UC_X86_REG_EBX, 0)
        self.halt_at = {0x11e2592, 0x11e2e95}
        self.uc.emu_start(0x11e257b, self.stop, count=100)
        result = self.uc.reg_read(UC_X86_REG_EIP)
        assert result in self.halt_at
        return hex(result)


def main():
    results = []
    for a, b in ((0, 0), (1, 0), (2, 0), (255, 0), (0, 1), (0, 127), (0, 128), (0, 255)):
        payload, decoded = probe(0xdac580, 0xe50b00, 0xf74260, fields={
            0x28: struct.pack('<hh', 100, 120), 0x2c: bytes([a]),
            0x30: struct.pack('<i', 0), 0x38: struct.pack('<Q', 1007), 0x40: bytes([b])})
        assert payload == b'\0' + struct.pack('>hhBiQB', 100, 120, a, 0, 1007, b) + b'\0'
        assert decoded[0x2c] == a and decoded[0x40] == b
        run = SceneStateProbe()
        observed = run.process_prefix(a, b)
        assert observed == [
            {'operation': 'scene_load_boundary', 'scene_id': 1007, 'position': (100, 120),
                'reason': 0, 'normalized_byte_a': int(a == 1)},
            {'operation': 'weather_boundary', 'signed_byte_b': b if b < 128 else b - 256}]
        results.append({'case': 'codec_Process', 'a': a, 'b': b,
            'payload_hex': payload.hex(), 'observed': observed})

    for name, kwargs in (('app_20', {'app_gate': True}), ('scene_null', {'scene_absent': True})):
        assert SceneStateProbe().process_prefix(**kwargs) == []
        results.append({'case': 'Process_gate_' + name, 'load_and_weather_calls': 0})

    for prior in (0, 1, 2):
        for a in (0, 1, 2, 255):
            run = SceneStateProbe()
            # Feed the bool actually built by the original Process into the
            # loader's post-resource slice, rather than a Python replacement.
            observed = run.process_prefix(a)
            normalized = observed[0]['normalized_byte_a']
            result = run.scene_success_slice(normalized, prior)
            assert result['branch'] == '0x11e26de'
            assert result['state_218'] == normalized
            assert result['mask'] == (8 if normalized else 1)
            assert result['position_sets_projected'] == [(150, 120), (150, 120)]
            results.append({'case': 'success_scene_state', 'a': a, 'prior': prior, 'result': result})

    for name, kwargs, expected_branch in (
        ('load_failure', {'success': 0}, '0x11e2e7a'),
        ('reason_516023', {'reason': 0x7dfb7}, '0x11e272d'),
        ('map_1404', {'map_id': 1404}, '0x11e272d')):
        result = SceneStateProbe().scene_success_slice(0, 2, **kwargs)
        assert result['branch'] == expected_branch
        assert result['state_218'] == 2 and result['mask'] == 8
        assert result['position_sets_projected'] == []
        results.append({'case': name, 'result': result})

    run = SceneStateProbe()
    result = run.scene_success_slice(0, 2, reason=516015)
    assert result['branch'] == '0x11e26de' and result['state_218'] == 0 and result['mask'] == 1
    results.append({'case': 'first_world_reason_516015_uses_same_state_setter', 'result': result})

    for name, kwargs, branch in (
        ('valid', {}, '0x11e2592'),
        ('missing_main', {'missing_main': True}, '0x11e2e95'),
        ('invalid_config', {'map_id': -1}, '0x11e2e95')):
        assert SceneStateProbe().scene_preload_gate(**kwargs) == branch
        results.append({'case': 'scene_preload_' + name, 'branch': branch})

    for b in (-1, 0, 1, 127, -128):
        found = SceneStateProbe().weather_prefix(b)
        assert found == ([] if b == -1 else [b])
        results.append({'case': 'weather_original_getter_wrapper', 'signed_b': b, 'lookup': found})

    # CCharacter ctor embeds the original role-state value object at +160.
    # Execute its initialization write with two nonzero poison prior bytes.
    for prior in (1, 255):
        run = SceneStateProbe()
        run.uc.mem_write(run.role + 0x218, bytes([prior]))
        run.uc.reg_write(UC_X86_REG_ESI, run.role + 0x160)
        run.uc.reg_write(UC_X86_REG_EBX, 0)
        run.uc.emu_start(0x11d50d9, 0x11d50df, count=1)
        assert run.uc.mem_read(run.role + 0x218, 1)[0] == 0
        results.append({'case': 'embedded_ctor_initial_state', 'prior': prior, 'state_218': 0})

    archive = PfsArchive(Path(__file__).resolve().parent / 'runtime/client/artres/config.pfs')
    entry = 'autoconfig/knight.gsp.map.CMapWeatherConfig.xml'
    # Entry names in this original archive are lower-case.
    entry = next(n for n in archive.entries if n.lower() == entry.lower())
    raw = archive.read(entry)
    rows = [dict(row.attrib) for row in decode(raw)]
    assert {'id', 'weathername', 'weatherTIPS', 'magic'} <= rows[0].keys()
    results.append({'case': 'weather_original_config_CRC', 'entry': entry,
        'sha256': hashlib.sha256(raw).hexdigest(), 'rows': rows})

    print(json.dumps({'image_sha256': hashlib.sha256(DATA).hexdigest(),
        'all_passed': True, 'cases': len(results), 'results': results}, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
