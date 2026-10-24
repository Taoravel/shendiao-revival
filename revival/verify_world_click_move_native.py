"""Original held-ground-input tick -> actor path -> actual CRoleMove builder.

No GUI/client/service starts. Mouse-device input and rendering side effects are
explicit host seams; planning, main-character queue and wire builder run native.
"""
import hashlib
import json
import struct
from pathlib import Path

from native_inspect import DATA, u32
from native_gameplay_probe import probe
from verify_world_blocked_goal_adjustment import BlockedGoalProbe
from pfs import PfsArchive
from world_grids import maze_grid
from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_EIP,
    UC_X86_REG_ESI, UC_X86_REG_ESP)


class ClickMoveProbe(BlockedGoalProbe):
    modal, session, input_factory, input_device, input_vt, device_vt = (
        0x5040000, 0x5041000, 0x5042000, 0x5043000, 0x5044000, 0x5045000)
    options, query, stream, stream_buffer, packet_copy = 0x5046000, 0x5047000, 0x5050000, 0x5051000, 0x5058000

    def __init__(self, width, height, flags, current, *, render_size):
        self.visited, self.role_moves, self.disposed, self.mouse_reads = [], [], [], 0
        super().__init__(width, height, flags, current=current)
        self.w(self.map_record + 0xc, *render_size)
        self.w(self.canvas + 4, 0x29a4a74)
        self.w(self.path + 4, 0x29a4a74)
        self.w(0x29a4a70 + 0x48, self.options)
        self.w(0x29a4a70 + 0x28, self.engine_receiver)
        self.w(0x29a4a70 + 0x164, self.query)
        for a in (0x29b8edc, 0x29b8ee0, 0x29b8ee4, 0x29b8ee8):
            self.w(a, 0)
        for a in (0x2945620, 0x29455c0, 0x294d190, 0x2945770):
            self.w(a, 0)
        self.w(0x2945594, self.modal)
        self.w(0x294556c, self.session)
        self.w(0x2945090, self.input_factory)
        self.w(self.input_factory, self.input_vt)
        self.w(self.input_vt + 0x50, self.stop + 0x800)
        self.w(self.input_device, self.device_vt)
        self.w(self.device_vt + 0x40, self.stop + 0x810)
        self.mouse_position = (48, 48)
        # A fixture camera origin; original World camera getter and scene
        # screen->world addition remain active.
        self.w(self.canvas + 0x488, 2208, 1104, 0, 0)
        self.make_list(self.role + 0x340, (), floats=True)
        self.make_list(self.role + 0x34c, ())
        for off in (0x20, 0x38, 0x2c):
            self.make_list(self.path + off, (), floats=True)
        self.make_list(self.role + 0x2f8, ())
        self.w(self.role + 0x2f4, 0x228a0b0)
        self.w(self.role + 0x26c, self.actor)
        self.uc.reg_write(UC_X86_REG_ESI, self.query)
        self.call(0x5aed50)  # Original query/workspace constructor.
        self.uc.reg_write(UC_X86_REG_EAX, self.canvas)
        self.call(0x672410, ecx=self.map_record + 0x84)  # Original Maze installation.
        self.uc.reg_write(UC_X86_REG_ESI, self.role)
        self.uc.reg_write(UC_X86_REG_ESP, self.stack)
        self.uc.emu_start(0x12028f7, 0x120291b, count=1000)  # Original state->mask.
        assert self.read(self.path + 0x48) == 1

    def hook(self, emu, addr, size, user):
        sp = emu.reg_read(UC_X86_REG_ESP)
        if addr in (0x1214bd0, 0x1211db0, 0x81ae00, 0x11c5b40, 0x12143b0,
            0x11f8800, 0x652a40, 0x6bc2f0, 0x6138d0, 0x6212f0, 0x120f9a0,
            0x1214a89, 0x12b9a10, 0x12bc870, 0x11d3a10, 0xe50840):
            self.visited.append(hex(addr))
        if addr == 0x11f8800:
            # Continue through actor/path; do not retain the old probe's stop.
            return
        if addr == 0x1174f80:
            return  # Keep the actual actor-moving getter, not the base fixture adapter.
        if addr == self.stop + 0x100:
            packet = self.read(sp + 4)
            assert self.read(packet + 4) == 0xc0fa1
            raw = bytes(emu.mem_read(packet, 32))
            self.role_moves.append({'raw_object_hex': raw.hex(),
                'message_type': 0xc0fa1, 'sender_return': hex(self.read(sp)),
                'start': struct.unpack_from('<hh', raw, 12), 'end': struct.unpack_from('<hh', raw, 20),
                'scene_u64': struct.unpack_from('<Q', raw, 24)[0]})
            emu.mem_write(self.packet_copy, raw)
            self.ret(4, 1)
            return
        if addr == self.stop + 0x800:
            self.ret(value=self.input_device)
            return
        if addr == self.stop + 0x810:
            self.mouse_reads += 1
            out = self.read(sp + 4)
            self.w(out, *self.mouse_position)
            self.ret(4, out)
            return
        if addr == 0x11d37d0:
            self.disposed.append(self.read(sp + 4))
            self.ret(4)
            return
        if addr in (0x19191c2, 0x1919386):
            dst, a, count = (self.read(sp + x) for x in (4, 8, 12))
            emu.mem_write(dst, bytes(emu.mem_read(a, count)) if addr == 0x19191c2 else bytes([a & 255]) * count)
            self.ret(value=dst)
            return
        if addr == 0x120fe50:
            self.ret(8)  # Ground-click visual marker after the movement call.
            return
        super().hook(emu, addr, size, user)

    def input_tick(self):
        self.uc.mem_write(self.role + 0x308, b'\1')  # Held ground input already latched.
        self.w(self.role + 0x304, 9)  # Deterministic tick whose original throttle opens.
        self.call(0x1214bd0)
        self.call(0x12061a0, (self.packet + 0x100,), ecx=self.role)
        return {'sent_count': len(self.role_moves), 'mouse_reads': self.mouse_reads,
            'original_current': struct.unpack('<ii', self.uc.mem_read(self.packet + 0x100, 8)),
            'actor_stored_projected': struct.unpack('<ff', self.uc.mem_read(self.path + 8, 8)),
            'future_engine': self.points(self.path + 0x2c, floats=True),
            'future_character': self.points(self.role + 0x340, floats=True),
            'history_character': self.points(self.role + 0x34c),
            'app_intro_flag': self.uc.mem_read(0x2945438, 1)[0]}

    def marshal_captured(self):
        # Same original object captured at the sender seam, not a host builder.
        assert self.role_moves
        self.w(self.stream, 0x224c100, self.stream_buffer, 0)
        self.w(self.stream_buffer - 12, 4096, 0, 1)
        self.call(0xe50840, (self.stream,), ecx=self.packet_copy)
        body = bytes(self.uc.mem_read(self.stream_buffer, self.read(self.stream_buffer - 8)))
        sent = self.role_moves[-1]
        assert body == struct.pack('>hhhhQ', *sent['start'], *sent['end'], sent['scene_u64'])
        return body


def main():
    root = Path(__file__).resolve().parent
    archive = PfsArchive(root / 'runtime/client/artres/map.pfs')
    maze_name, rmp_name = 'map_1100_gumupai/maze.dat', 'map_1100_gumupai/map.rmp'
    maze_raw, rmp_raw = archive.read(maze_name), archive.read(rmp_name)
    grid = maze_grid(maze_raw)
    size = struct.unpack_from('<II', rmp_raw, 8)
    current, goal = (1488, 1152), (1504, 1152)
    routes = json.loads((root / 'catalogs/newbie-routes.json').read_text(encoding='utf-8'))
    route = next(r for r in routes['routes'] if r['role_id'] == 9 and r['school_id'] == 11)
    assert route['home_map_id'] == 1100 and tuple(route['cinematic_endpoint']['logical_pixels']) == current
    assert grid.cell(93, 72) & 1 == grid.cell(94, 72) & 1 == 0
    run = ClickMoveProbe(grid.width, grid.height, grid.cells, current, render_size=size)
    run.w(run.scene + 0x30, 1100, 0)
    run.uc.mem_write(0x2945438, b'\1')
    run.w(run.scene + 0x39c, 0x12345678)
    before = run.input_tick()
    assert before['sent_count'] == before['mouse_reads'] == 0
    assert '0x1211db0' in run.visited and '0x12143b0' not in run.visited
    run.call(0x12b9a10, ecx=run.packet)
    assert run.uc.mem_read(0x2945438, 1)[0] == 0 and run.read(run.scene + 0x39c) == 0
    assert run.disposed == [0x12345678]
    after = run.input_tick()
    assert after['sent_count'] == after['mouse_reads'] == 1
    sent = run.role_moves[0]
    assert sent['start'] == current and sent['end'] == goal and sent['scene_u64'] == 1100
    body = run.marshal_captured()
    _, decoded = probe(0xdaac40, 0xe50840, 0xdaad20, payload=body)
    assert struct.unpack_from('<hh', decoded, 12) == current
    assert struct.unpack_from('<hh', decoded, 20) == goal
    assert struct.unpack_from('<Q', decoded, 24)[0] == 1100
    assert after['original_current'] == current
    assert after['future_engine'] == after['future_character'] == [tuple(map(float, goal))]
    assert after['history_character'] == [current]
    assert sent['sender_return'] == '0x1214aa9'
    required = {hex(a) for a in (0x1214bd0,0x1211db0,0x81ae00,0x11c5b40,0x12143b0,
        0x11f8800,0x652a40,0x6bc2f0,0x6138d0,0x120f9a0,0xe50840)}
    assert required <= set(run.visited)
    result = {'image_sha256': hashlib.sha256(DATA).hexdigest(), 'all_passed': True,
        'map_id': 1100, 'source': current, 'raw_device_position': run.mouse_position,
        'birth_fixture': {'character_config_id': 9, 'school_id': 11, 'coordinate_source': 'original cinematic endpoint',
            'spawn_selection': 'designed by existing newbie-opening-v1; original server spawn unconfirmed'},
        'fixture_camera_origin_projected': (2208,1104), 'expected_goal': goal,
        'source_and_goal_maze_flags': (grid.cell(93,72),grid.cell(94,72)),
        'before_original_intro_cleanup': before, 'after_original_intro_cleanup': after,
        'original_sender_object': sent, 'original_body_hex': body.hex(),
        'native_decoder_verified': True, 'native_DDA_samples': run.dda_trace,
        'visited': run.visited, 'kernel_entered': '0x6212f0' in run.visited,
        'sources': [{'entry': n, 'sha256': hashlib.sha256(raw).hexdigest(), 'CRC_checked': True}
            for n,raw in ((maze_name,maze_raw),(rmp_name,rmp_raw))],
        'scope': 'original held-ground-input tick with mouse-device seam, not OS button dispatch or GUI'}
    out = root / 'evidence/world-click-move-native.json'
    out.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({'all_passed': True, 'sent_count': after['sent_count'],
        'body_hex': body.hex(), 'kernel_entered': result['kernel_entered'], 'result': str(out)}))


if __name__ == '__main__':
    main()
