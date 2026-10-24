"""Exclusive kernel-port research; frozen pathfinding verifier is imported only."""
import hashlib
import json
import math
import struct
from array import array
from pathlib import Path
from contextlib import redirect_stdout

from verify_world_native_pathfinding import NativePath
from native_inspect import BASE, DATA, disasm
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32
from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_EBP,
    UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_ESP, UC_X86_REG_EIP,
    UC_X86_REG_ECX, UC_X86_REG_EDX)

OUT = Path(__file__).parent / 'evidence'
TABLE = DATA[0x2461268 - BASE:0x2461268 - BASE + 256]


def original_distance_formula(n):
    """Only the proven ordinary grid domain, not arbitrary uint32 inputs."""
    assert 0 <= n <= 2 * 1919 ** 2
    if n < 0x3fd:
        guess = TABLE[(n + 3) >> 2] >> 3
    elif n < 0x3fe4:
        guess = TABLE[(n + 0x1c) >> 6] >> 1
    elif n < 0x10000:
        guess = TABLE[n >> 8]
    elif n < 0x100000:
        seed = TABLE[n >> 12]
        guess = ((n // seed) >> 3) + 2 * seed
    else:
        seed = TABLE[n >> 16]
        guess = ((n // seed) >> 5) + 8 * seed
    return guess - int(n < guess * guess)


def distance_sweep():
    u = Uc(UC_ARCH_X86, UC_MODE_32)
    u.mem_map(BASE, (len(DATA) + 4095) & ~4095)
    u.mem_write(BASE, DATA)
    u.mem_map(0x5000000, 0x1000000)
    code, source, target, stack = 0x5000000, 0x5010000, 0x5500000, 0x5fff000
    # Host batch driver only: ECX=*ESI; call ORIGINAL; ESI+=4; *EDI++=EAX; --EBX.
    driver = (b'\x8b\x0e\xe8' + struct.pack('<i', 0x5f87e0 - (code + 7))
              + b'\x83\xc6\x04\xab\x4b\x75\xf2')
    u.mem_write(code, driver)
    maximum, batch = 2 * 1919 ** 2, 65536
    formula_differences, floor_differences = [], []
    digest = hashlib.sha256()
    for start in range(0, maximum + 1, batch):
        values = array('I', range(start, min(start + batch, maximum + 1)))
        u.mem_write(source, values.tobytes())
        for reg, value in ((UC_X86_REG_ESI, source), (UC_X86_REG_EDI, target),
                (UC_X86_REG_EBX, len(values)), (UC_X86_REG_ESP, stack)):
            u.reg_write(reg, value)
        u.emu_start(code, code + len(driver), count=6000000)
        assert u.reg_read(UC_X86_REG_EBX) == 0
        output = bytes(u.mem_read(target, len(values) * 4))
        digest.update(output)
        actual = array('I'); actual.frombytes(output)
        for n, result in zip(values, actual):
            if result != original_distance_formula(n):
                formula_differences.append([n, result, original_distance_formula(n)])
            if result != math.isqrt(n):
                floor_differences.append([n, result, math.isqrt(n)])
    assert not formula_differences, formula_differences[:10]
    return {'domain': [0, maximum], 'original_calls': maximum + 1,
            'formula_differences': len(formula_differences),
            'isqrt_differences': len(floor_differences),
            'first_isqrt_differences': floor_differences[:10],
            'output_sha256': digest.hexdigest(), 'table_va': '0x2461268',
            'table_hex': TABLE.hex(), 'batch_driver_hex': driver.hex()}


class BranchPath(NativePath):
    def __init__(self):
        self.branch_stop = None
        self.decrease_calls = 0
        self.branch_seen = None
        self.termination_mode = False
        super().__init__(8, 8, bytes(64))

    def hook(self, e, a, size, user):
        if a == self.branch_stop:
            e.reg_write(UC_X86_REG_EIP, self.stop)
            return
        if self.termination_mode and a in (0x6213b0, 0x621cb5):
            self.branch_seen = 'continue_search' if a == 0x6213b0 else 'backtrack_success'
            e.reg_write(UC_X86_REG_EIP, self.stop)
            return
        if a == 0x5f8e50:
            self.decrease_calls += 1
        super().hook(e, a, size, user)


def neighbor_updates():
    rows = []
    branches = [('NW', 0x6214e9, 0x62153f, 7), ('N', 0x621598, 0x621628, 5),
        ('NE', 0x62170c, 0x621768, 7), ('W', 0x6217bd, 0x62184d, 5),
        ('E', 0x6218a2, 0x621932, 5), ('SW', 0x621a12, 0x621a6e, 7),
        ('S', 0x621ac3, 0x621b53, 5), ('SE', 0x621c51, 0x621ca7, 7)]
    for direction, start, end, cost in branches:
        for scenario, state, candidate in [('unseen', 0, 10 + cost),
                ('open_better', 1, 10 + cost), ('open_equal', 1, 20),
                ('open_worse', 1, 21), ('closed_better', 2, 10 + cost)]:
            r = BranchPath()
            obj = r.workspace + 0xe108
            r.execute(0x5f8b70, eax=obj)
            root, child, parent, goal = [r.alloc(32) for _ in range(4)]
            r.w(root + 8, 0, 48)
            r.execute(0x5f8bb0, eax=obj, args=(root,))
            r.uc.mem_write(child, struct.pack('<hh', 1, 1))
            r.w(child + 4, 0x12345678, 20, 50, state)
            if state == 1:
                r.execute(0x5f8bb0, eax=obj, args=(child,))
            r.uc.mem_write(goal, struct.pack('<hh', 7, 7))
            r.w(parent + 8, candidate - cost)
            r.w(r.stack + 0x30, r.workspace, 0)
            r.w(r.stack + 0x40, goal)
            r.uc.reg_write(UC_X86_REG_EDI, r.workspace)
            r.uc.reg_write(UC_X86_REG_EBP, parent)
            r.branch_stop, r.decrease_calls = end, 0
            r.execute(start, eax=child)
            actual = {'parent': r.r(child + 4), 'g': r.r(child + 8),
                'f': r.r(child + 0xc), 'state': r.r(child + 0x10)}
            if state == 0:
                assert actual == {'parent': parent, 'g': candidate, 'f': candidate + 40, 'state': 1}
                assert r.decrease_calls == 1  # native insertion's sift-up
            elif scenario == 'open_better':
                assert actual == {'parent': parent, 'g': candidate, 'f': 50 + candidate - 20, 'state': 1}
                assert r.decrease_calls == 1
                assert r.r(r.r(obj + 4)) == child  # original decrease-key moved it to root
                assert r.r(child + 0x14) == 0 and r.r(root + 0x14) == 1
            else:
                assert actual == {'parent': 0x12345678, 'g': 20, 'f': 50, 'state': state}
                assert r.decrease_calls == 0
            count = (r.r(obj + 8) - r.r(obj + 4)) // 4
            assert count == (2 if state in (0, 1) else 1)
            rows.append({'direction': direction, 'slice': [hex(start), hex(end)],
                'scenario': scenario, 'step_cost': cost, 'candidate_g': candidate,
                'after': actual, 'sift_up_calls': r.decrease_calls, 'heap_size': count})
    return rows


def termination_cases():
    rows = []
    for state in (0, 1, 2):
        r = BranchPath()
        goal = r.alloc(32)
        r.w(goal + 0x10, state)
        r.w(r.stack + 0x40, goal)
        r.termination_mode = True
        r.execute(0x621ca7)
        assert r.branch_seen == ('backtrack_success' if state == 1 else 'continue_search')
        rows.append({'goal_state': state, 'branch': r.branch_seen})
    r = NativePath(8, 6, bytes(48))
    actual = r.kernel((1, 2), (5, 2))
    assert (5, 2) not in [tuple(item['xy']) for item in actual['pop_trace']]
    goal_push = next(i for i, item in enumerate(r.push_trace) if item['xy'] == [5, 2])
    assert r.push_trace[goal_push + 1:]
    rows.append({'full_kernel_goal_not_popped': True,
        'goal_push_index': goal_push, 'pushes_after_goal': r.push_trace[goal_push + 1:],
        'last_popped': actual['pop_trace'][-1], 'path': actual['grid_path']})
    return rows


class CompressionPath(NativePath):
    def __init__(self, width, height, cells):
        self.dda = []
        super().__init__(width, height, cells)

    def hook(self, e, a, size, user):
        if a == 0x626b40:
            self.dda.append({'from': [e.reg_read(UC_X86_REG_EDX), e.reg_read(UC_X86_REG_ECX)],
                'to': [e.reg_read(UC_X86_REG_EAX), self.r(e.reg_read(UC_X86_REG_ESP) + 4)]})
        elif a == 0x623d64:
            self.dda[-1]['result'] = e.reg_read(UC_X86_REG_EAX)
        super().hook(e, a, size, user)


def compression_cases():
    rows = []
    wall = bytearray(48)
    for y in range(4):
        wall[y * 8 + 3] = 1
    for name, cells, expected in [('clear', bytes(48), [(88., 40.)]),
            ('wall', wall, [(56., 72.), (88., 40.)])]:
        r = CompressionPath(8, 6, cells)
        grid_result = r.kernel((1, 2), (5, 2))
        r.uc.mem_write(r.start_vec, struct.pack('<6f', 24., 40., 0., 0., 0., 0.))
        for reg, value in ((UC_X86_REG_ESI, r.output), (UC_X86_REG_EDI, r.scratch),
                          (UC_X86_REG_EBX, 0xffffffff)):
            r.uc.reg_write(reg, value)
        r.execute(0x61bc60, args=(r.query, r.start_vec))
        assert r.points(r.scratch, floats=True) == expected
        assert r.points(r.output) == []
        payloads = []
        head = r.r(r.scratch + 4)
        node = r.r(head)
        while node != head:
            payloads.append(struct.unpack('<6f', r.uc.mem_read(node + 8, 24)))
            node = r.r(node)
        rows.append({'case': name, 'input_grid_path': grid_result['grid_path'],
            'original_6float_output': payloads, 'DDA_calls': r.dda})
    return rows


class LongPath(NativePath):
    def __init__(self, cells):
        self.wrapper_trace = []
        super().__init__(32, 6, cells)

    def hook(self, e, a, size, user):
        if a == 0x61b8f0:
            self.wrapper_trace.append({'entry': hex(a), 'EAX': e.reg_read(UC_X86_REG_EAX)})
        elif a == 0x61bc60:
            self.wrapper_trace.append({'entry': hex(a), 'EBX': e.reg_read(UC_X86_REG_EBX),
                'input_grid_count': self.r(e.reg_read(UC_X86_REG_ESI) + 8)})
        super().hook(e, a, size, user)


def long_wrapper_cases():
    wall = bytearray(32 * 6)
    for y in range(4):
        wall[y * 32 + 15] = 1
    rows = []
    for mode in (0, 1):
        r = LongPath(wall)
        result = r.wrapper((24., 40.), (456, 40), mode=mode)
        assert result['return_EAX'] == 0
        assert r.wrapper_trace[0] == {'entry': '0x61b8f0', 'EAX': 0}
        assert r.wrapper_trace[1]['input_grid_count'] >= 25
        assert r.wrapper_trace[1]['EBX'] == mode
        if mode == 0:
            assert result['float_path'][-1] == (456., 40.) and not result['grid_path']
        else:
            assert result['float_path'] == [(40., 40.)] and result['grid_path']
        rows.append({'third_parameter': mode, 'sixth_parameter': 0,
                     'trace': r.wrapper_trace, **result})
    return rows


def main():
    result = {'image_sha256': hashlib.sha256(DATA).hexdigest(),
              'distance': distance_sweep(), 'native_domain': 'Both grid axes 0..1919',
              'neighbor_updates': neighbor_updates(), 'termination': termination_cases(),
              'compression': compression_cases(),
              'long_wrapper': long_wrapper_cases(),
              'adapters': ['Distance batch loop only calls unmodified original function',
                  'Neighbor fixtures inherit frozen NativePath allocation/free, cookie, memset/memcpy adapters',
                  'Branch boundary observers stop before unrelated next-neighbor work'],
              'scope': 'Offline research; no production modules or frozen verifier changed'}
    (OUT / 'world-path-kernel-port-native.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    with (OUT / 'world-path-kernel-port-disassembly.txt').open('w', encoding='utf-8') as f:
        with redirect_stdout(f):
            for at, size in ((0x5f87e0, 0x180), (0x6212f0, 0xa22),
                    (0x5f8e50, 180), (0x61bc60, 40), (0x623c00, 0x324),
                    (0x61b7d0, 0x46a), (0x6138d0, 0x4bd)):
                print(hex(at)); disasm(at, size)
    print(json.dumps({'distance_calls': result['distance']['original_calls'],
        'neighbor_cases': len(result['neighbor_updates']), 'termination_cases': len(result['termination']),
        'compression_cases': len(result['compression']),
        'long_wrapper_cases': len(result['long_wrapper']),
        'isqrt_differences': result['distance']['isqrt_differences'],
        'first_isqrt_differences': result['distance']['first_isqrt_differences']}))


if __name__ == '__main__':
    main()
