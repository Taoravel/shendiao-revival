"""Original successful scene-landing setter versus maze flags, offline only."""
import hashlib
import json
import struct
from pathlib import Path

from native_inspect import DATA, u32
from native_gameplay_probe import probe
from verify_world_scene_movement_state_native import SceneStateProbe
from world_grids import maze_grid
from pfs import PfsArchive
from bxml import decode
from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_EBP, UC_X86_REG_EBX,
    UC_X86_REG_ECX, UC_X86_REG_EDI, UC_X86_REG_EIP, UC_X86_REG_ESI, UC_X86_REG_ESP)


class SceneLandingProbe(SceneStateProbe):
    map_record, maze_cells = 0x5030000, 0x5031000

    def __init__(self, width, height, flags, *, render_size=None):
        super().__init__()
        assert len(flags) == width * height
        self.w(self.canvas, 0x2461754)
        self.w(self.canvas + 0x298, self.map_record)
        self.w(self.map_record + 0xc, *(render_size or (width * 24, height * 16)))
        self.w(self.map_record + 0x8c, width, height, self.maze_cells)
        self.uc.mem_write(self.maze_cells, bytes(flags))
        self.phase = 'setup'
        self.landing_queries, self.setter_logical_inputs, self.adjustment_calls = [], [], []
        self.landing_collision_entries = []

    def hook(self, emu, addr, size, user):
        sp = emu.reg_read(UC_X86_REG_ESP)
        if addr == u32(0x22443f0):
            # Diagnostic name/string construction for render-bound warnings.
            dst = emu.reg_read(UC_X86_REG_ECX)
            emu.mem_write(dst, bytes(28))
            self.ret(4, dst)
            return
        if self.phase == 'landing':
            if addr in (0x11c5c00, 0x6036e0, 0x6284f0, 0x626b40):
                self.landing_collision_entries.append(hex(addr))
            if addr == 0x11c5c00:
                self.landing_queries.append({'point': struct.unpack('<ii', emu.mem_read(sp + 4, 8)),
                    'mask': self.read(sp + 12)})
            elif addr == 0x11f6480:
                self.setter_logical_inputs.append(struct.unpack('<ii', emu.mem_read(self.read(sp + 4), 8)))
            elif addr in (0x1212080, 0x12143b0):
                self.adjustment_calls.append(hex(addr))
                raise AssertionError('Scene landing unexpectedly entered a separate adjustment routine')
        super().hook(emu, addr, size, user)

    def point_blocked(self, point):
        self.phase = 'audit'
        self.call(0x11c5c00, (*point, 1), ecx=self.scene)
        return bool(self.uc.reg_read(UC_X86_REG_EAX) & 255)

    def land(self, point, *, map_id=1007, a=0, success=1, reason=0, special=None):
        # Execute original codec and original Process bool/position argument construction.
        body, decoded = probe(0xdac580, 0xe50b00, 0xf74260, fields={
            0x28: struct.pack('<hh', *point), 0x2c: bytes([a]),
            0x30: struct.pack('<i', reason), 0x38: struct.pack('<Q', map_id), 0x40: b'\0'})
        self.uc.mem_write(self.packet, bytes(0x80))
        self.uc.mem_write(self.packet + 0x28, decoded[0x28:0x42])
        self.halt_at = {0x11e3219}
        self.run_until(0x11e3140, self.packet, (0, 0))
        captured = self.captured[0]
        assert captured['position'] == point
        if special == '158':
            self.w(self.role + 0x2c0, 1)
        elif special == '15c':
            self.w(self.role + 0x2cc, 1)
        self.uc.mem_write(self.role + 0x218, b'\2')
        self.uc.mem_write(self.stack + 0x17, bytes([success]))
        self.w(self.stack + 0xb0, reason, captured['normalized_byte_a'])
        self.w(self.scene + 0x110, map_id)
        for reg, value in ((UC_X86_REG_ESP, self.stack), (UC_X86_REG_EBX, 0),
            (UC_X86_REG_ESI, self.scene), (UC_X86_REG_EBP, point[0]), (UC_X86_REG_EDI, point[1])):
            self.uc.reg_write(reg, value & 0xffffffff)
        self.halt_at = {0x11e26de, 0x11e272d, 0x11e2e7a}
        self.phase = 'landing'
        self.uc.emu_start(0x11e269b, self.stop, count=150000)
        branch = self.uc.reg_read(UC_X86_REG_EIP)
        assert branch in self.halt_at
        self.phase = 'getter'
        self.halt_at = set()
        self.call(0x12061a0, (self.packet + 0x100,), ecx=self.role)
        current = struct.unpack('<ii', self.uc.mem_read(self.packet + 0x100, 8))
        return {'packet_position': point, 'packet_byte_a': a, 'map_id': map_id,
            'body_hex': body.hex(), 'branch': hex(branch),
            'actual_actor_projected': struct.unpack('<ff', self.uc.mem_read(self.path + 8, 8)),
            'original_getter_current': current, 'state_218': self.uc.mem_read(self.role + 0x218, 1)[0],
            'role_target_328': struct.unpack('<ii', self.uc.mem_read(self.role + 0x328, 8)),
            'setter_logical_inputs': self.setter_logical_inputs, 'actual_actor_set_inputs': self.position_sets,
            'maze_queries_during_landing': self.landing_queries, 'collision_entries_during_landing': self.landing_collision_entries,
            'separate_adjustment_calls': self.adjustment_calls}


def main():
    rows = []
    width, height = 8, 6
    clear = bytes(width * height)
    blocked = bytes(1 if (x, y) == (5, 2) else 0 for y in range(height) for x in range(width))
    for name, flags, point, options, expected in (
        ('clear_goal', clear, (88, 40), {}, (88, 40)),
        ('blocked_goal', blocked, (88, 40), {}, (88, 40)),
        ('all_maze_blocked', bytes([1]) * len(clear), (88, 40), {}, (88, 40)),
        ('blocked_goal_a1', blocked, (88, 40), {'a': 1}, (88, 40)),
        ('render_upper_clamp', clear, (200, 100), {}, (127, 95)),
        ('render_lower_clamp', clear, (-10, -10), {}, (0, 0)),
        ('special_virtual_158', blocked, (88, 40), {'special': '158'}, (8, 8)),
        ('special_virtual_15c', blocked, (88, 40), {'special': '15c'}, (8, 8)),
        ('resource_failure_skip', blocked, (88, 40), {'success': 0}, (8, 8))):
        run = SceneLandingProbe(width, height, flags)
        before = run.point_blocked(point)
        result = run.land(point, **options)
        assert result['original_getter_current'] == expected, (name, result)
        assert result['maze_queries_during_landing'] == [] and result['separate_adjustment_calls'] == []
        assert result['collision_entries_during_landing'] == []
        assert result['state_218'] == (2 if options.get('success') == 0 else int(options.get('a', 0) == 1))
        assert result['role_target_328'] == ((56, 56) if options.get('success') == 0 else point)
        if name.startswith('special_') or options.get('success') == 0:
            assert result['actual_actor_set_inputs'] == []
        else:
            assert len(result['actual_actor_set_inputs']) == 2
        rows.append({'case': name, 'requested_point_blocked_mask1': before, **result})

    root = Path(__file__).resolve().parent
    archive = PfsArchive(root / 'runtime/client/artres/map.pfs')
    configs = PfsArchive(root / 'runtime/client/artres/config.pfs')
    config_raw = configs.read('autoconfig/knight.gsp.map.cmapconfig.xml')
    config = {int(row.attrib['id']): dict(row.attrib) for row in decode(config_raw)}
    names = {n.lower(): n for n in archive.entries}
    for source_id, target_id in ((1301,1100),(1304,1103),(1305,1104),(1306,1105),(1308,1107),
        (1309,1108),(1393,1007),(1394,1007),(1395,1007)):
        goto_name = names[(config[source_id]['resdir'] + '/goto.xml').lower()]
        goto_raw = archive.read(goto_name)
        portals = [dict(r.attrib) for r in decode(goto_raw) if int(r.attrib['destmap']) == target_id]
        destinations = {(int(p['destx']) * 16, int(p['desty']) * 16) for p in portals}
        assert len(destinations) == 1 and len(portals) == 25
        point = next(iter(destinations))
        resdir = config[target_id]['resdir']
        maze_name, rmp_name = (names[(resdir + suffix).lower()] for suffix in ('/maze.dat', '/map.rmp'))
        maze_raw, rmp_raw = archive.read(maze_name), archive.read(rmp_name)
        grid = maze_grid(maze_raw)
        assert rmp_raw[:4] == b'RMAP'
        render_size = struct.unpack_from('<II', rmp_raw, 8)
        run = SceneLandingProbe(grid.width, grid.height, grid.cells, render_size=render_size)
        assert run.point_blocked(point)
        result = run.land(point, map_id=target_id)
        assert result['original_getter_current'] == point
        assert result['state_218'] == 0 and result['role_target_328'] == point
        assert result['maze_queries_during_landing'] == [] and result['separate_adjustment_calls'] == []
        assert result['collision_entries_during_landing'] == []
        assert len(result['actual_actor_set_inputs']) == 2
        assert run.point_blocked(result['original_getter_current'])
        rows.append({'case': 'original_portal_scene_landing', 'source_id': source_id,
            'target_id': target_id, 'source_goto_rows': len(portals), 'maze_size': (grid.width, grid.height),
            'original_dest_cell': (int(portals[0]['destx']), int(portals[0]['desty'])),
            'render_size': render_size, 'requested_and_actual_blocked_mask1': True,
            'original_target_cell_flag': grid.cell(point[0] // 16, point[1] // 16),
            'sources': [{'entry': n, 'sha256': hashlib.sha256(raw).hexdigest(), 'CRC_checked': True}
                for n, raw in ((goto_name, goto_raw), (maze_name, maze_raw), (rmp_name, rmp_raw))], **result})

    print(json.dumps({'image_sha256': hashlib.sha256(DATA).hexdigest(),
        'original_config_sha256': hashlib.sha256(config_raw).hexdigest(),
        'all_passed': True, 'cases': len(rows), 'results': rows}, indent=2))


if __name__ == '__main__':
    main()
