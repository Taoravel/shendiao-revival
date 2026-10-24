"""Execute original grid search and path wrapper offline; no Python path search."""
import hashlib
import json
import struct
from pathlib import Path
from contextlib import redirect_stdout
from native_inspect import BASE, DATA, u32, disasm
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_EDX,
    UC_X86_REG_ESI, UC_X86_REG_ESP, UC_X86_REG_EIP)

OUT = Path(__file__).parent / 'evidence'


class NativePath:
    query, cells, workspace = 0x5001000, 0x5002000, 0x5010000
    output, scratch, start_vec = 0x5030000, 0x5031000, 0x5032000
    stack, stop, heap = 0x5100000, 0x500f000, 0x5200000

    def __init__(self, width, height, cells, mask=1):
        self.uc = Uc(UC_ARCH_X86, UC_MODE_32)
        self.uc.mem_map(0, 4096)
        self.uc.mem_map(BASE, (len(DATA) + 4095) & ~4095)
        self.uc.mem_write(BASE, DATA)
        self.uc.mem_map(0x5000000, 0x1000000)
        self.allocations = 0
        self.expansions = 0
        self.kernel_calls = 0
        self.pop_trace = []
        self.push_trace = []
        self.w(self.query, width, height, self.cells, mask, 0, 0, width, height, self.workspace)
        self.uc.mem_write(self.cells, bytes(cells))
        self.make_list(self.output)
        self.make_list(self.scratch, floats=True)
        for p in (0x29b8edc, 0x29b8ee0, 0x29b8ee4, 0x29b8ee8):
            self.w(p, 0)
        for addr in (u32(0x2244890), u32(0x2244894), u32(0x2244898)):
            page = addr & ~4095
            if not any(a <= page <= b for a, b, _ in self.uc.mem_regions()):
                self.uc.mem_map(page, 4096)
        self.uc.hook_add(UC_HOOK_CODE, self.hook)

    def w(self, p, *values):
        self.uc.mem_write(p, struct.pack('<' + 'I' * len(values), *(v & 0xffffffff for v in values)))

    def r(self, p):
        return struct.unpack('<I', self.uc.mem_read(p, 4))[0]

    def alloc(self, n):
        p = self.heap
        self.heap += (n + 15) & ~15
        assert self.heap < 0x5ff0000
        self.allocations += 1
        return p

    def make_list(self, obj, floats=False):
        head = self.alloc(32 if floats else 16)
        self.w(obj, 0, head, 0)
        self.w(head, head, head)

    def points(self, obj, floats=False):
        head, values = self.r(obj + 4), []
        p = self.r(head)
        while p != head:
            assert len(values) < 10000
            values.append(struct.unpack('<ff' if floats else '<ii', self.uc.mem_read(p + 8, 8)))
            p = self.r(p)
        assert len(values) == self.r(obj + 8)
        return values

    def ret(self, pop=0, value=None):
        sp = self.uc.reg_read(UC_X86_REG_ESP)
        if value is not None:
            self.uc.reg_write(UC_X86_REG_EAX, value)
        self.uc.reg_write(UC_X86_REG_ESP, sp + 4 + pop)
        self.uc.reg_write(UC_X86_REG_EIP, self.r(sp))

    def hook(self, e, a, size, user):
        sp = e.reg_read(UC_X86_REG_ESP)
        if a in (0x1919178, u32(0x2244890)):
            self.ret(value=self.alloc(self.r(sp + 4)))
        elif a in (0x191910c, 0x1919184, u32(0x2244894)):
            self.ret()
        elif a == 0x1919386:  # cdecl memset
            dst, value, count = (self.r(sp + n) for n in (4, 8, 12))
            e.mem_write(dst, bytes([value & 255]) * count); self.ret(value=dst)
        elif a == 0x19191c2:  # cdecl memcpy
            dst, src, count = (self.r(sp + n) for n in (4, 8, 12))
            e.mem_write(dst, bytes(e.mem_read(src, count))); self.ret(value=dst)
        elif a == u32(0x2244898):
            raise AssertionError('Original STL invalid iterator')
        elif a == 0x6212f0:
            self.kernel_calls += 1
        elif a == 0x6213de:
            self.expansions += 1
            node = e.reg_read(UC_X86_REG_EAX)
            self.pop_trace.append({'xy': list(struct.unpack('<hh', e.mem_read(node, 4))),
                'g': self.r(node + 8), 'f': self.r(node + 0xc)})
        elif a == 0x5f8bb0:
            node = self.r(sp + 4)
            self.push_trace.append({'xy': list(struct.unpack('<hh', e.mem_read(node, 4))),
                'g': self.r(node + 8), 'f': self.r(node + 0xc)})

    def execute(self, at, eax=0, ecx=0, edx=0, args=()):
        self.w(self.stack, self.stop, *args)
        for reg, value in ((UC_X86_REG_ESP, self.stack), (UC_X86_REG_EAX, eax),
                           (UC_X86_REG_ECX, ecx), (UC_X86_REG_EDX, edx)):
            self.uc.reg_write(reg, value & 0xffffffff)
        self.uc.emu_start(at, self.stop, count=2000000)
        assert self.uc.reg_read(UC_X86_REG_EIP) == self.stop, hex(self.uc.reg_read(UC_X86_REG_EIP))
        return self.uc.reg_read(UC_X86_REG_EAX)

    def kernel(self, start, end):
        result = self.execute(0x6212f0, eax=end[1], args=(self.workspace, self.query,
             start[0], start[1], end[0], self.output))
        return {'return_AL': result & 255, 'grid_path': self.points(self.output),
                'expanded_nodes': self.expansions, 'pop_trace': self.pop_trace,
                'push_trace': self.push_trace}

    def wrapper(self, start, end, mode=0):
        self.uc.mem_write(self.start_vec, struct.pack('<6f', *start, 0., 0., 0., 0.))
        result = self.execute(0x6138d0, ecx=end[0], edx=self.query,
            args=(self.start_vec, end[1], mode, self.output, self.scratch, 0, 0))
        return {'return_EAX': result, 'grid_path': self.points(self.output),
                'float_path': self.points(self.scratch, floats=True),
                'kernel_calls': self.kernel_calls, 'expanded_nodes': self.expansions}

    def heap_order(self, scores):
        """Execute original heap push/pop; labels are node x, g is deliberately distinct."""
        obj = self.workspace + 0xe108
        self.execute(0x5f8b70, eax=obj)
        for label, score in enumerate(scores):
            node = self.alloc(32)
            self.uc.mem_write(node, struct.pack('<hh', label, 0))
            self.w(node + 8, 1000 - label, score)
            self.execute(0x5f8bb0, eax=obj, args=(node,))
        labels = []
        for _ in scores:
            self.uc.reg_write(UC_X86_REG_ESI, obj)
            node = self.execute(0x5f8c20)
            labels.append(struct.unpack('<h', self.uc.mem_read(node, 2))[0])
        return labels


def main():
    width, height = 8, 6
    clear = bytes(width * height)
    wall = bytearray(clear)
    for y in range(4):
        wall[y * width + 3] = 1
    rows = []
    for name, flags, start, goal, expected in (
        ('clear', clear, (1, 2), (5, 2), True),
        ('wall_bottom_gap', wall, (1, 2), (5, 2), True),
        ('wall_closed', bytes(1 if x == 3 else 0 for y in range(height) for x in range(width)), (1, 2), (5, 2), False),
        ('blocked_goal', bytes(1 if (x, y) == (5, 2) else 0 for y in range(height) for x in range(width)), (1, 2), (5, 2), False),
        ('same_grid', clear, (1, 2), (1, 2), False),
        ('blocked_start', bytes(1 if (x, y) == (1, 2) else 0 for y in range(height) for x in range(width)), (1, 2), (5, 2), True)):
        r = NativePath(width, height, flags)
        result = r.kernel(start, goal)
        assert bool(result['return_AL']) == expected, (name, result)
        if expected:
            assert tuple(result['grid_path'][-1]) == goal
            assert all(not flags[y * width + x] for x, y in result['grid_path'])
        if name == 'wall_bottom_gap':
            assert any(y >= 4 for x, y in result['grid_path']), result
        rows.append({'case': name, 'start': start, 'requested_goal': goal, **result})
    for name, flags, expected, minimum in (
        ('wrapper_clear', clear, 0, 1), ('wrapper_around_wall', wall, 0, 2),
        ('wrapper_blocked_goal', bytes(1 if (x, y) == (5, 2) else 0 for y in range(height) for x in range(width)), 1, 0)):
        r = NativePath(width, height, flags)
        result = r.wrapper((24., 40.), (88, 40))
        assert result['return_EAX'] == expected, (name, result)
        assert len(result['float_path']) >= minimum
        rows.append({'case': name, 'start': [24, 40], 'requested_goal': [88, 40], **result})
    for name, scores, expected in (
        ('heap_equal_f', [10, 10, 10], [0, 2, 1]),
        ('heap_equal_children', [0, 10, 10, 20, 30], [0, 2, 1, 3, 4])):
        r = NativePath(1, 1, b'\0')
        actual = r.heap_order(scores)
        assert actual == expected, (name, actual)
        rows.append({'case': name, 'f_scores': scores, 'pop_labels': actual})
    r = NativePath(1921, 1, bytes(1921))
    result = r.kernel((0, 0), (1, 0))
    assert result['return_AL'] == 0 and result['expanded_nodes'] == 0
    rows.append({'case': 'width_above_native_cap', **result})
    r = NativePath(width, height, wall, mask=8)
    result = r.kernel((1, 2), (5, 2))
    assert result['grid_path'] == [(2, 2), (3, 2), (4, 2), (5, 2)]
    rows.append({'case': 'same_wall_mask8', 'mask': 8, **result})
    r = NativePath(width, height, clear)
    r.uc.reg_write(UC_X86_REG_ESI, r.query)
    r.execute(0x5aed50)
    assert [r.r(r.query + 4 * n) for n in range(8)] == [0] * 8
    r.workspace = r.r(r.query + 0x20)
    assert r.workspace
    world, maze = 0x5033000, 0x5034000
    r.w(0x29a4a70 + 0x164, r.query)
    r.w(world + 4, 0x29a4a70 + 4)
    r.w(maze + 8, width, height, r.cells)
    r.execute(0x672410, eax=world, ecx=maze)
    installed = [r.r(r.query + n * 4) for n in range(9)]
    assert installed == [width, height, r.cells, 0, 0, 0, width, height, r.workspace]
    r.w(r.query + 0xc, 1)  # caller-selected mask, not a constructor default
    result = r.kernel((1, 2), (5, 2))
    assert result['grid_path'] == [(2, 2), (3, 2), (4, 2), (5, 2)]
    rows.append({'case': 'original_query_constructor_and_map_install',
                 'installed_query_words': installed, **result})
    r = NativePath(2, 2, bytes([0, 1, 1, 0]))
    result = r.kernel((0, 0), (1, 1))
    assert result['return_AL'] == 0
    rows.append({'case': 'kernel_no_diagonal_corner_cut', **result})
    r = NativePath(2, 2, bytes([0, 1, 1, 0]))
    result = r.wrapper((8., 8.), (24, 24))
    assert result['return_EAX'] == 0 and result['kernel_calls'] == 0
    rows.append({'case': 'wrapper_DDA_diagonal_corner_shortcut', **result})
    r = NativePath(width, height, clear)
    result = r.wrapper((24., 40.), (24, 40))
    assert result['return_EAX'] == 3 and not result['float_path']
    rows.append({'case': 'wrapper_same_point', **result})
    r = NativePath(width, height, clear)
    result = r.wrapper((24., 40.), (88, 40), mode=1)
    assert result['return_EAX'] == 0 and result['kernel_calls'] == 1
    rows.append({'case': 'wrapper_mode1_forces_kernel', **result})
    result = {'image_sha256': hashlib.sha256(DATA).hexdigest(), 'cases_passed': len(rows),
              'cases': rows, 'algorithm': 'Original 0x6212f0 and 0x6138d0; no host path algorithm',
              'adapters': ['allocation/free', 'security cookie', 'memset', 'memcpy'],
              'scope': 'Original grid search, DDA, heap and short-path smoothing executed; actor/mouse high-level correction not executed',
              'host_instruction_limit': 2000000, 'native_request_budget': None}
    (OUT / 'world-native-pathfinding.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    with (OUT / 'world-native-pathfinding-disassembly.txt').open('w', encoding='utf-8') as f:
        with redirect_stdout(f):
            for address, size in ((0x6212f0, 2580), (0x6138d0, 1040), (0x6bc2f0, 400),
                    (0x5f8a00, 300), (0x5f8bb0, 850), (0x5f8e50, 170),
                    (0x5aed50, 140), (0x5a63c0, 7), (0x5fcd50, 1600),
                    (0x672410, 120), (0x5a785a, 60),
                    (0x12143b0, 0x860), (0x11f8800, 110), (0x652a40, 35)):
                print('\n' + hex(address)); disasm(address, size)
    print(json.dumps({'cases_passed': result['cases_passed'], 'output': str(OUT / 'world-native-pathfinding.json')}))


if __name__ == '__main__':
    main()
