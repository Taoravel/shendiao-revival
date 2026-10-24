"""Original current/history/snapshot quantizers and float32 boundary probes.

Only reads the original image. Outputs JSON to stdout; never starts the client,
opens sockets, mutates accounts, or writes production policy/module files.
"""
import hashlib
import json
import math
import struct
from fractions import Fraction

from native_inspect import DATA
from verify_movement_reports_native import OriginalReports
from unicorn.x86_const import UC_X86_REG_XMM0


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def adjacent_f32(value, direction):
    value = f32(value)
    assert math.isfinite(value) and direction in (-1, 1)
    if value == 0:
        return struct.unpack('<f', struct.pack('<I', 1 if direction > 0 else 0x80000001))[0]
    bits = struct.unpack('<I', struct.pack('<f', value))[0]
    bits += direction if value > 0 else -direction
    return struct.unpack('<f', struct.pack('<I', bits))[0]


def trunc_interval(n):
    if n > 0:
        return Fraction(n), True, Fraction(n + 1), False
    if n < 0:
        return Fraction(n - 1), False, Fraction(n), True
    return Fraction(-1), False, Fraction(1), False


def current_x_interval(m):
    """Projected float preimage before wire16 narrowing, ordinary finite range.

    This is a research assertion against original instructions, not a movement
    acceptance policy. The full set is the stated interval intersect float32.
    """
    if m == 0:
        return trunc_interval(0)
    k = abs(m)
    ns = [3 * (k // 2)] if k % 2 == 0 else [3 * (k // 2) + 1, 3 * (k // 2) + 2]
    ns = [n if m > 0 else -n for n in ns]
    intervals = [trunc_interval(n) for n in ns]
    low = min(v[0] for v in intervals)
    high = max(v[2] for v in intervals)
    return low, m > 0, high, m < 0


def reached_interval(m):
    return Fraction(2*m - 1, 2), m > 0, Fraction(2*m + 1, 2), m < 0


def snapshot_x_interval(m):
    if m == 0:
        return Fraction(-2), False, Fraction(2), False
    k = abs(m)
    if k % 2 == 0:
        ns = [3 * (k // 2), 3 * (k // 2) + 1]
    else:
        ns = [3 * (k // 2) + 2]
    ns = [n if m > 0 else -n for n in ns]
    intervals = [trunc_interval(n) for n in ns]
    return min(v[0] for v in intervals), m > 0, max(v[2] for v in intervals), m < 0


def contains(interval, value):
    low, closed_low, high, closed_high = interval
    value = Fraction(value)
    return (value > low or closed_low and value == low) and (value < high or closed_high and value == high)


def interval_record(interval, *, scale=1):
    low, lc, high, hc = interval
    return {'low': str(low / scale), 'low_closed': lc, 'high': str(high / scale), 'high_closed': hc}


class QuantizationProbe(OriginalReports):
    output = 0x500b000

    def __init__(self):
        super().__init__()
        self.dynamic_current = True
        self.preprojection_x = []

    def hook(self, emu, addr, size, user):
        if addr == 0x6bc9b7:
            raw = emu.reg_read(UC_X86_REG_XMM0)
            self.preprojection_x.append(struct.unpack('<f', struct.pack('<I', raw & 0xffffffff))[0])
        super().hook(emu, addr, size, user)

    def current_quantized(self, px, py):
        self.uc.mem_write(self.path + 8, struct.pack('<ff', px, py))
        self.call(0x12061a0, (self.output,))
        return struct.unpack('<ii', self.uc.mem_read(self.output, 8))

    def reached(self, x, y=10.):
        self.w(self.role + 0x358, 999, 999)
        self.make_list(self.role + 0x340, ((x, y), (100., 100.)), floats=True)
        self.make_list(self.role + 0x34c, ())
        self.consume()
        result = self.points(self.role + 0x34c)
        assert len(result) == 1
        return result[0]

    def initial(self, px, py=10.):
        self.uc.mem_write(self.path + 8, struct.pack('<ff', px, py))
        self.make_list(self.path + 0x2c, ((100., 100.),), floats=True)
        self.make_list(self.role + 0x34c, ())
        snapshot = self.actor_path_snapshot()
        self.initial_consume()
        return snapshot[0], self.points(self.role + 0x34c)[0]


def main():
    results = []
    for axis, edges in (('x', (90., 91., 93., -90., -91., -1., 1.)),
                        ('y', (74., 75., -74., -75.))):
        run = QuantizationProbe()
        for edge in edges:
            observed = []
            for value in (adjacent_f32(edge, -1), edge, adjacent_f32(edge, 1)):
                actual = run.current_quantized(value if axis == 'x' else 90., value if axis == 'y' else 74.)
                m = actual[0 if axis == 'x' else 1]
                interval = current_x_interval(m) if axis == 'x' else trunc_interval(m)
                assert contains(interval, value), (axis, value, m, interval)
                # Neighbour reports' preimages are disjoint at this point.
                for other in (m-1, m+1):
                    candidate = current_x_interval(other) if axis == 'x' else trunc_interval(other)
                    assert not contains(candidate, value)
                observed.append({'input_f32': value, 'current': actual})
            assert observed[0]['current'] != observed[-1]['current']
            results.append({'case': 'current_float32_boundary', 'axis': axis, 'edge': edge, 'observed': observed})

    for axis, edges in (('x', (23.5, 24.5, -23.5, -24.5, -.5, .5)), ('y', (23.5, -23.5))):
        run = QuantizationProbe()
        for edge in edges:
            observed = []
            for value in (adjacent_f32(edge, -1), edge, adjacent_f32(edge, 1)):
                actual = run.reached(value, 10.) if axis == 'x' else run.reached(10., value)
                m = actual[0 if axis == 'x' else 1]
                assert contains(reached_interval(m), value), (axis, value, m)
                observed.append({'input_f32': value, 'history': actual})
            assert observed[0]['history'] != observed[-1]['history']
            results.append({'case': 'arrived_node_float32_boundary', 'axis': axis, 'edge': edge, 'observed': observed})

    for edge in (36., 38., -36., -38., -2., 2.):
        run = QuantizationProbe()
        observed = []
        for value in (adjacent_f32(edge, -1), edge, adjacent_f32(edge, 1)):
            snapshot, history = run.initial(value)
            assert snapshot == tuple(map(float, history))
            assert contains(snapshot_x_interval(history[0]), value), (value, history)
            observed.append({'projected_x_f32': value, 'snapshot': snapshot, 'initial_history': history})
        assert observed[0]['snapshot'] != observed[-1]['snapshot']
        results.append({'case': 'initial_snapshot_float32_boundary', 'edge': edge, 'observed': observed})

    run = QuantizationProbe()
    snapshot, initial = run.initial(37.5, 88.)
    current = run.current_quantized(37.5, 88.)
    arrived = run.reached(25., 88.)
    assert snapshot == (24., 88.) and initial == (24, 88)
    assert current == arrived == (25, 88)
    results.append({'case': 'same_logical_25_three_producers', 'projected': (37.5, 88.),
        'snapshot': snapshot, 'initial_history': initial, 'current': current, 'arrived_history': arrived})

    run = QuantizationProbe()
    run.uc.mem_write(run.path + 8, struct.pack('<ff', 37.5, 88.))
    run.uc.mem_write(run.path + 0x1c, struct.pack('<f', 1.))
    run.make_list(run.path + 0x2c, ((73., 70.),), floats=True)
    run.actor_path_snapshot()
    run.initial_consume()
    actual_logical = run.engine_tick(38)
    px, py = struct.unpack('<ff', run.uc.mem_read(run.path + 8, 8))
    run.call(0x12171d0, (0, 1))
    packet = run.sent[-1]
    assert packet['current'] == (60, 74) and packet['points'] == [(24, 88)]
    assert contains(current_x_interval(60), px) and contains(trunc_interval(74), py)
    assert contains(snapshot_x_interval(24), 37.5)
    assert not contains(reached_interval(24), 25.)
    assert run.dda((25, 88), (73, 70)) == 0
    clear_trace = list(run.dda_trace)
    assert run.dda((25, 88), packet['current']) == 1
    assert run.dda_trace[-1] == (47, 79)
    source_wall = run.dda_trace[-1]
    assert run.dda(packet['points'][0], packet['current']) == 1
    history_wall = run.dda_trace[-1]
    assert (history_wall[0] // 16, history_wall[1] // 16) == (2, 4)
    results.append({'case': 'original_counterexample_intervals', 'projected_float32': (px, py),
        'logical_interpolation_scratch_float32': run.preprojection_x,
        'logical_from_stored_projection': actual_logical, 'sent': packet,
        'current_x_projected_preimage': interval_record(current_x_interval(60)),
        'current_x_logical_preimage': interval_record(current_x_interval(60), scale=Fraction(3, 2)),
        'current_y_preimage': interval_record(trunc_interval(74)),
        'history_24_initial_logical_preimage': interval_record(snapshot_x_interval(24), scale=Fraction(3, 2)),
        'history_24_arrived_logical_preimage': interval_record(reached_interval(24)),
        'original_leg_clear': True, 'recomputed_source_report_wall': source_wall,
        'recomputed_history_report_wall': history_wall,
        'original_leg_sample_count': len(clear_trace)})

    # Wire is signed16 while current getter returns int32: demonstrate an alias,
    # without accepting it as a map position or inventing a server policy.
    run = QuantizationProbe()
    internal = run.current_quantized(98394., 74.)  # 3*(60+65536)/2, finite/exact float32.
    assert internal == (65596, 74)
    run.call(0x12171d0, (0, 1))
    assert run.sent[-1]['current'] == (60, 74)
    results.append({'case': 'wire16_current_alias', 'internal_current_i32': internal, 'wire_current': run.sent[-1]['current']})
    run = QuantizationProbe()
    history = run.reached(65560.)
    assert history == (24, 10)
    results.append({'case': 'wire16_arrived_history_alias', 'node_x_float32': 65560., 'wire_history': history})

    print(json.dumps({'image_sha256': hashlib.sha256(DATA).hexdigest(),
        'all_passed': True, 'cases': len(results),
        'scope': 'ordinary current branch; finite float32; normal conversion range; explicit wire16 aliases',
        'results': results}, indent=2))


if __name__ == '__main__':
    main()
