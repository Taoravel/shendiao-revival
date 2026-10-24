"""Original CMainCharacter blocked-click adjustment, stopped at path entry.

The host supplies fixture object/map bytes, not adjusted destinations. Scene
flag lookup, region membership comparison, current getter and candidate loops
all execute original image instructions. No sockets, GUI or persistent writes.
"""
import hashlib
import json
import struct

from native_inspect import DATA
from verify_world_movement_reconciliation_native import Reconciliation
from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_EIP,
    UC_X86_REG_ESP)


class BlockedGoalProbe(Reconciliation):
    map_record, maze_cells = 0x5030000, 0x5031000
    point_returns = {0x1214449, 0x121447a, 0x121456a, 0x121464c, 0x12146bc, 0x1214875}

    def __init__(self, width, height, flags, *, current=(24, 40), mask=1, state=0):
        super().__init__()
        assert len(flags) == width * height
        self.queries, self.region_queries, self.path_entries, self.loop_entries = [], [], [], []
        self.dda_calls = 0
        self.w(self.canvas, 0x2461754)
        self.w(self.canvas + 0x298, self.map_record)
        self.w(self.map_record + 0x8c, width, height, self.maze_cells)
        self.uc.mem_write(self.maze_cells, bytes(flags))
        self.uc.mem_write(self.path + 8, struct.pack('<ff', current[0] * 1.5, current[1]))
        self.w(self.role + 0x50, mask)
        self.uc.mem_write(self.role + 0x218, bytes([state]))
        self.w(self.role + 0x328, 1000, 1000)
        self.w(0x29455c0, 0)
        self.w(0x2945570, self.guard + 0x1000)
        self.uc.mem_write(self.guard + 0x1000 + 0x3cc, b'\0')
        self.region_maps = []
        for offset in (0x2d0, 0x2e8):
            obj = self.scene + offset + 0xc
            head = self.alloc(32)
            self.w(obj, 0, head, 0)
            self.w(head, head, head, head)
            self.uc.mem_write(head + 0x15, b'\1')
            self.region_maps.append(obj)

    def hook(self, emu, addr, size, user):
        sp = emu.reg_read(UC_X86_REG_ESP)
        if addr == 0x12143b0:
            return  # Do not use Reconciliation's replan-call adapter here.
        if addr == 0x11c5c00:
            self.queries.append({'caller_return': hex(self.read(sp)),
                'point': struct.unpack('<ii', emu.mem_read(sp + 4, 8)), 'mask': self.read(sp + 12)})
        elif addr in self.point_returns:
            self.queries[-1]['blocked'] = bool(emu.reg_read(UC_X86_REG_EAX) & 255)
        elif addr == 0x11deaa0:
            self.region_queries.append({'from': struct.unpack('<ii', emu.mem_read(sp + 4, 8)),
                'to': struct.unpack('<ii', emu.mem_read(sp + 12, 8)), 'mode_byte': self.read(sp + 20) & 255})
        elif addr in (0x121475c, 0x12148aa):
            self.region_queries[-1]['same_value'] = bool(emu.reg_read(UC_X86_REG_EAX) & 255)
        elif addr == 0x626b40:
            self.dda_calls += 1
        elif addr in (0x1214502, 0x1214688, 0x1214850):
            self.loop_entries.append(hex(addr))
        elif addr == 0x11f8800:
            self.path_entries.append({'goal': struct.unpack('<ii', emu.mem_read(sp + 4, 8)),
                'adjusted_source_local': struct.unpack('<ii', emu.mem_read(sp + 0x44, 8)),
                'original_current_local': struct.unpack('<ii', emu.mem_read(sp + 0x4c, 8)),
                'actor_stored_projected': struct.unpack('<ff', emu.mem_read(self.path + 8, 8))})
            emu.emu_stop()
            return
        elif addr == 0x15bb820:
            self.ret(12)  # UI message only; preserve original rejection branch.
            return
        super().hook(emu, addr, size, user)

    def add_region_cell(self, x, y, value, *, mode=0):
        # Original map insertion; host only supplies an input cell/value.
        key = ((x & 0xffff) << 16) | (y & 0xffff)
        self.w(self.packet + 0x100, key)
        self.call(0x11d8f60, (self.packet + 0x100,), ecx=self.region_maps[mode])
        out = self.uc.reg_read(UC_X86_REG_EAX)
        self.uc.mem_write(out, bytes([value]))

    def run_goal(self, goal, *, arg3=0):
        self.w(self.stack, self.stop, *goal, arg3)
        self.uc.reg_write(UC_X86_REG_ESP, self.stack)
        self.uc.reg_write(UC_X86_REG_ECX, self.role)
        self.uc.emu_start(0x12143b0, self.stop, count=250000)
        ended = self.uc.reg_read(UC_X86_REG_EIP)
        assert ended in (self.stop, 0x11f8800), hex(ended)
        return {'requested_goal': goal, 'reached_path_entry': bool(self.path_entries),
            'mask_50': self.read(self.role + 0x50), 'state_218': self.uc.mem_read(self.role + 0x218, 1)[0],
            'return_AL_if_early': (self.uc.reg_read(UC_X86_REG_EAX) & 255) if ended == self.stop else None,
            'path_entry': self.path_entries, 'flag_3e4': self.uc.mem_read(self.role + 0x3e4, 1)[0],
            'point_queries': self.queries, 'region_queries': self.region_queries,
            'loop_entries': self.loop_entries, 'original_DDA_calls_before_path_entry': self.dda_calls}


def main():
    width, height = 8, 6
    clear = bytes(width * height)
    def flags_for(blocked):
        return bytes(1 if (x, y) in blocked else 0 for y in range(height) for x in range(width))
    rows = []
    for name, flags, current, goal, expected_goal, expected_source in (
        ('clear', clear, (24, 40), (88, 40), (88, 40), (24, 40)),
        ('blocked_goal', flags_for({(5, 2)}), (24, 40), (88, 40), (88, 24), (24, 40)),
        ('blocked_goal_and_north', flags_for({(5, 2), (5, 1)}), (24, 40), (88, 40), (72, 40), (24, 40)),
        ('blocked_current', flags_for({(1, 2)}), (24, 40), (88, 40), (88, 40), (16, 48)),
        ('both_blocked', flags_for({(1, 2), (5, 2)}), (24, 40), (88, 40), (88, 24), (16, 48)),
        ('all_blocked', bytes([1]) * len(clear), (24, 40), (88, 40), None, None),
        ('blocked_goal_too_close', flags_for({(2, 2)}), (24, 40), (32, 40), None, None),
        ('adjusted_goal_distance16_allowed', flags_for({(2, 2)}), (24, 40), (40, 40), (40, 24), (24, 40)),
        ('first_clear_is_current', flags_for({(2, 2), (2, 1)}), (24, 40), (40, 40), None, None),
        ('current_ring_exhausted', flags_for({(1, 2), (2, 2), (1, 3), (2, 3)}), (24, 40), (88, 40), None, None),
        ('current_ring_corner', flags_for({(1, 2)}), (16, 32), (88, 40), (88, 40), (15, 31)),
        ('reverse_first_clear_is_current', flags_for({(5, 2), (5, 1)}), (104, 40), (88, 40), None, None),
        ('closed_intermediate_wall_still_reaches_path_entry', flags_for({(3, y) for y in range(height)}),
             (24, 40), (88, 40), (88, 40), (24, 40))):
        run = BlockedGoalProbe(width, height, flags, current=current)
        result = run.run_goal(goal)
        assert result['original_DDA_calls_before_path_entry'] == 0
        assert result['reached_path_entry'] == (expected_goal is not None), (name, result)
        if expected_goal is not None:
            assert result['path_entry'][0]['goal'] == expected_goal, (name, result)
            assert result['path_entry'][0]['adjusted_source_local'] == expected_source, (name, result)
            assert result['path_entry'][0]['actor_stored_projected'] == (current[0] * 1.5, current[1]), (name, result)
        else:
            assert result['return_AL_if_early'] == 0
        if name == 'blocked_goal_and_north':
            candidates = [q['point'] for q in result['point_queries'] if q['caller_return'] == '0x121456a']
            assert candidates == [(88, 24), (72, 40)]
        if name == 'blocked_current':
            candidates = [q['point'] for q in result['point_queries'] if q['caller_return'] == '0x12146bc']
            assert len(candidates) == 59 and candidates[:8] == [
                (23, 39), (23, 40), (23, 41), (24, 41), (25, 41), (25, 40), (25, 39), (24, 39)]
            assert candidates[-1] == (16, 48)
        if name == 'current_ring_exhausted':
            assert result['loop_entries'].count('0x1214688') == 64
        rows.append({'case': name, **result})

    for name, flags, mask, state, flag_3e5, expected_goal, expected_marker in (
        ('same_maze_mask8', flags_for({(5, 2)}), 8, 0, 0, (88, 40), 0),
        ('alternate_mask_clear_marker', flags_for({(5, 2)}), 1, 0, 1, (88, 24), 1),
        ('both_masks_block_marker_unchanged', bytes(9 if (x, y) == (5, 2) else 0
            for y in range(height) for x in range(width)), 1, 0, 1, (88, 24), 0)):
        run = BlockedGoalProbe(width, height, flags, mask=mask, state=state)
        run.uc.mem_write(run.role + 0x3e5, bytes([flag_3e5]))
        result = run.run_goal((88, 40))
        assert result['path_entry'][0]['goal'] == expected_goal
        assert result['flag_3e4'] == expected_marker
        rows.append({'case': name, **result})

    for mode in (0, 1):
        run = BlockedGoalProbe(width, height, clear, mask=1, state=mode)
        # Hold both map contents equal; these two cases change state only.
        for table_mode in (0, 1):
            run.add_region_cell(5, 2, 1, mode=table_mode)
        result = run.run_goal((88, 40))
        assert result['path_entry'][0]['goal'] == (88, 24)
        assert [q['same_value'] for q in result['region_queries']] == [False, True]
        assert result['loop_entries'] == ['0x1214850']
        rows.append({'case': 'clear_goal_region_value_mismatch_mode_' + str(mode), **result})

    run = BlockedGoalProbe(width, height, clear, mask=1, state=1)
    run.add_region_cell(5, 2, 1, mode=0)  # Other table remains empty.
    result = run.run_goal((88, 40))
    assert result['path_entry'][0]['goal'] == (88, 40)
    assert [q['same_value'] for q in result['region_queries']] == [True]
    rows.append({'case': 'state_1_selects_other_region_table', **result})

    for name, mutate in (
        ('repeat_goal_gate', lambda r: (r.w(r.role + 0x328, 88, 40), r.uc.mem_write(r.role + 0x308, b'\1'))),
        ('world_54_gate_after_adjustment', lambda r: r.w(r.guard + 0x54, 1)),
        ('role_2e4_gate_after_adjustment', lambda r: r.uc.mem_write(r.role + 0x2e4, b'\1'))):
        run = BlockedGoalProbe(width, height, clear)
        mutate(run)
        result = run.run_goal((88, 40))
        assert not result['reached_path_entry'] and result['return_AL_if_early'] == 0
        if name == 'repeat_goal_gate':
            assert result['point_queries'] == []
        else:
            assert len(result['point_queries']) == 2 and len(result['region_queries']) == 1
        rows.append({'case': name, **result})

    run = BlockedGoalProbe(width, height, clear)
    run.add_region_cell(5, 2, 1)
    run.uc.mem_write(run.guard + 0x1000 + 0x3cc, b'\1')
    result = run.run_goal((88, 40))
    assert not result['reached_path_entry'] and result['return_AL_if_early'] == 0
    assert result['loop_entries'] == [] and result['region_queries'][0]['same_value'] is False
    rows.append({'case': 'region_mismatch_settings_3cc_gate', **result})

    print(json.dumps({'image_sha256': hashlib.sha256(DATA).hexdigest(),
        'all_passed': True, 'cases': len(rows), 'results': rows}, indent=2))


if __name__ == '__main__':
    main()
