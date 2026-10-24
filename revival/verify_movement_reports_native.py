"""Original CHECK/STOP builders and +340 -> +34c consumption, offline only."""
from pathlib import Path
import hashlib
import json
import struct

from native_inspect import BASE, DATA, u32, capstone
from research_movement import native_packet
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX,
    UC_X86_REG_EDI, UC_X86_REG_EDX, UC_X86_REG_EBP, UC_X86_REG_ESI, UC_X86_REG_ESP, UC_X86_REG_EIP)

ROOT = Path(__file__).resolve().parent


class OriginalReports:
    role, scene, sender = 0x5001000, 0x5002000, 0x5003000
    path, engine_world, engine_vtable, engine_receiver = 0x5004000, 0x5005000, 0x5006000, 0x5007000
    actor = 0x5008000
    stack, stop, heap_start = 0x5100000, 0x500f000, 0x5200000

    def __init__(self):
        self.uc = Uc(UC_ARCH_X86, UC_MODE_32)
        self.uc.mem_map(0, 0x1000)
        self.uc.mem_map(BASE, (len(DATA) + 4095) & ~4095)
        self.uc.mem_write(BASE, DATA)
        self.uc.mem_map(0x5000000, 0x400000)
        self.heap = self.heap_start
        self.current = (8, 8)
        self.actor_moving = True
        self.sent = []
        self.events = []
        self.callback_calls = []
        self.engine_events = []
        self.dda_trace = []
        self.integrated_events = False
        self.dynamic_current = False
        self.w(self.role, 0x2299344)
        self.w(0x2944564, self.scene)
        self.w(self.scene + 0x30, 0x55667788, 0x11223344)
        self.w(self.sender, self.sender + 0x100)
        self.w(self.sender + 0x100 + 0x3c, self.stop + 0x100)
        self.w(self.path, 12345, self.engine_world)
        self.w(self.actor, 0x2462544)
        self.w(self.actor + 0x1a8, self.path)
        self.w(self.role + 0x48, self.actor)
        self.w(self.engine_world, self.engine_vtable)
        self.w(self.engine_vtable + 0x18, self.stop + 0x300)
        self.w(self.engine_vtable + 0x88, self.stop + 0x300)
        self.w(self.engine_vtable + 0x54, self.stop + 0x310)
        self.w(self.engine_receiver, self.engine_receiver + 0x100)
        self.w(self.engine_receiver + 0x100 + 0x20, self.stop + 0x320)
        for addr in (u32(0x2244890), u32(0x2244894)):
            if not BASE <= addr < BASE + len(DATA):
                page = addr & ~4095
                if page not in getattr(self, 'mapped_imports', set()):
                    self.uc.mem_map(page, 4096)
                    self.mapped_imports = getattr(self, 'mapped_imports', set()) | {page}
        # Host CRT sqrt adapter: x87 fsqrt; ret. This code lives in fixture
        # memory, never modifies an original-image instruction.
        self.uc.mem_write(self.stop + 0x200, b'\xd9\xfa\xc3')
        self.uc.hook_add(UC_HOOK_CODE, self.hook)
        self.make_list(self.role + 0x340, (), floats=True)
        self.make_list(self.role + 0x34c, ())

    def w(self, addr, *values):
        self.uc.mem_write(addr, struct.pack('<' + 'I' * len(values), *(v & 0xffffffff for v in values)))

    def read(self, addr):
        return struct.unpack('<I', self.uc.mem_read(addr, 4))[0]

    def alloc(self, count):
        result = self.heap
        self.heap += (count + 15) & ~15
        assert self.heap < 0x53f0000
        return result

    def make_list(self, address, points, *, floats=False):
        head = self.alloc(16)
        nodes = [self.alloc(32 if floats else 16) for _ in points]
        self.w(address, 0, head, len(points))
        self.w(head, nodes[0] if nodes else head, nodes[-1] if nodes else head)
        for i, (node, point) in enumerate(zip(nodes, points)):
            self.w(node, nodes[i+1] if i+1 < len(nodes) else head, nodes[i-1] if i else head)
            if floats:
                self.uc.mem_write(node + 8, struct.pack('<6f', *point, 0., 1., 0., 0.))
            else:
                self.w(node + 8, 0x2278e54)
                self.uc.mem_write(node + 12, struct.pack('<hh', *point))

    def points(self, address, *, floats=False):
        head = self.read(address + 4)
        result, node = [], self.read(head)
        while node != head:
            assert len(result) < 100
            result.append(struct.unpack('<ff' if floats else '<hh',
                self.uc.mem_read(node + (8 if floats else 12), 8 if floats else 4)))
            node = self.read(node)
        assert len(result) == self.read(address + 8)
        return result

    def ret(self, pop=0, value=None):
        sp = self.uc.reg_read(UC_X86_REG_ESP)
        if value is not None:
            self.uc.reg_write(UC_X86_REG_EAX, value)
        self.uc.reg_write(UC_X86_REG_ESP, sp + 4 + pop)
        self.uc.reg_write(UC_X86_REG_EIP, self.read(sp))

    def hook(self, emu, addr, size, user):
        sp = emu.reg_read(UC_X86_REG_ESP)
        if addr in (0x1919178, u32(0x2244890)):
            self.ret(value=self.alloc(self.read(sp + 4)))
        elif addr in (0x191910c, u32(0x2244894), 0x1919184):
            self.ret()
        elif addr == u32(0x2244898):
            raise AssertionError('Original STL invalid iterator')
        elif addr == 0x19196a4:
            emu.reg_write(UC_X86_REG_EIP, self.stop + 0x200)
        elif addr == 0x12061a0 and not self.dynamic_current:
            out = self.read(sp + 4)
            current = self.current
            emu.mem_write(out, struct.pack('<ii', *current))
            self.ret(4, out)
        elif addr == 0x1174f80 and not self.integrated_events:
            self.ret(value=int(self.actor_moving))
        elif addr == 0x120c350:
            self.callback_calls.append(self.read(sp + 4))
            self.ret(4)
        elif addr == 0x813860:
            self.ret(value=self.sender)
        elif addr == self.stop + 0x100:
            packet = self.read(sp + 4)
            kind = self.read(packet + 4)
            points = self.points(packet + (16 if kind == 0xc0fa3 else 8))
            offset = 12 if kind == 0xc0fa3 else 24
            current = struct.unpack('<hh', emu.mem_read(packet + offset, 4))
            self.sent.append({'kind': hex(kind), 'points': points, 'current': current,
                'body_hex': native_packet(kind, end=current, path=points).hex()})
            self.ret(4, 1)
        elif addr == self.stop + 0x300:
            self.ret(value=0)  # No map/navmesh recomputation in this fixture.
        elif addr == self.stop + 0x310:
            self.ret(value=self.engine_receiver)
        elif addr == self.stop + 0x320:
            object_id, event = self.read(sp + 4), self.read(sp + 8)
            point = struct.unpack('<ff', emu.mem_read(self.path + 8, 8))
            self.engine_events.append({'raw_actor_argument': object_id, 'event': event,
                'logical_current': (point[0] / 1.5, point[1])})
            self.ret(8)
        elif addr == 0x81c670 and self.integrated_events:
            actor, event = self.read(sp + 4), self.read(sp + 8)
            point = struct.unpack('<ff', emu.mem_read(self.path + 8, 8))
            self.engine_events.append({'actor_pointer': hex(actor), 'event': event,
                'logical_current': (point[0] / 1.5, point[1])})
        elif addr == 0x11d1db0 and self.integrated_events:
            assert self.read(sp + 4) == self.actor
            self.ret(4, self.role)
        elif addr == 0x11d5260 and self.integrated_events:
            self.ret(8, 0)  # Unrelated special scene-object lookup.
        elif addr == 0x1217580:
            self.events.append({'operation': 'actual_maincharacter_callback', 'event': self.read(sp + 4)})
        elif addr == 0x6284f0:
            self.dda_trace.append((emu.reg_read(UC_X86_REG_EAX), self.read(sp + 8)))
        elif addr == 0x1214110:
            self.events.append({'operation': 'append_history',
                'point': struct.unpack('<hh', emu.mem_read(self.read(sp + 4) + 4, 4))})
        elif addr == 0x621f40:
            self.events.append({'operation': 'erase_plan_head',
                'point': struct.unpack('<ff', emu.mem_read(self.read(sp + 12) + 8, 8))})

    def call(self, address, args=(), *, ecx=None):
        self.w(self.stack, self.stop, *args)
        self.uc.reg_write(UC_X86_REG_ESP, self.stack)
        self.uc.reg_write(UC_X86_REG_ECX, self.role if ecx is None else ecx)
        try:
            self.uc.emu_start(address, self.stop, count=150000)
        except Exception as error:
            raise RuntimeError(f'Native execution at {self.uc.reg_read(UC_X86_REG_EIP):x}') from error
        assert self.uc.reg_read(UC_X86_REG_EIP) == self.stop

    def consume(self, event=1):
        # Slice begins immediately after the actor-path UI preflight, retains
        # original base-callback call, event test and every consumption gate.
        self.uc.reg_write(UC_X86_REG_ESI, self.role)
        self.uc.reg_write(UC_X86_REG_EDI, event)
        self.uc.reg_write(UC_X86_REG_EBX, 0)
        self.uc.reg_write(UC_X86_REG_EBP, 0xffffffff)
        self.uc.reg_write(UC_X86_REG_ESP, self.stack - 0x100)
        self.uc.emu_start(0x1217633, 0x121797e, count=150000)
        assert self.uc.reg_read(UC_X86_REG_EIP) == 0x121797e

    def initial_consume(self):
        self.uc.reg_write(UC_X86_REG_ESI, self.role)
        self.uc.reg_write(UC_X86_REG_EDI, self.role + 0x340)
        self.uc.reg_write(UC_X86_REG_EBP, 0x2278e54)
        self.uc.reg_write(UC_X86_REG_ESP, self.stack - 0x100)
        self.uc.emu_start(0x1214aa9, 0x1214b99, count=100000)
        assert self.uc.reg_read(UC_X86_REG_EIP) == 0x1214b99

    def actor_path_snapshot(self):
        self.uc.reg_write(UC_X86_REG_ESI, self.role + 0x340)
        self.uc.reg_write(UC_X86_REG_EDI, self.path)
        self.call(0x6bc6c0)
        return self.points(self.role + 0x340, floats=True)

    def engine_tick(self, distance_budget):
        self.uc.reg_write(UC_X86_REG_ESI, self.path)
        self.call(0x6bc7a0, (distance_budget,))
        point = struct.unpack('<ff', self.uc.mem_read(self.path + 8, 8))
        return (point[0] / 1.5, point[1])

    def connect_original_dispatch(self):
        self.integrated_events = self.dynamic_current = True
        self.w(self.path, self.actor)
        self.uc.mem_write(self.path + 0x44, b'\x01')
        self.w(self.engine_world + 0x28, 0x2945060)
        self.w(self.engine_vtable + 0x54, 0x5a62b0)
        for addr in (0x29455e8, 0x2945628, 0x2944798):
            self.w(addr, 0)  # Other mode-specific event recipients absent.
        self.w(self.role + 0x358, 999, 999)

    def dda(self, start, end, *, wall=(2, 4)):
        self.dda_trace.clear()
        layout, cells = 0x5009000, 0x500a000
        flags = bytearray(64)
        flags[wall[1] * 8 + wall[0]] = 1
        self.uc.mem_write(cells, bytes(flags))
        self.w(layout, 8, 8, cells, 1, 0, 0, 8, 8)
        self.w(self.stack, self.stop, end[1], layout, layout)
        self.uc.reg_write(UC_X86_REG_ESP, self.stack)
        self.uc.reg_write(UC_X86_REG_EAX, end[0])
        self.uc.reg_write(UC_X86_REG_EDX, start[0])
        self.uc.reg_write(UC_X86_REG_ECX, start[1])
        self.uc.emu_start(0x626b40, self.stop, count=1000000)
        return self.uc.reg_read(UC_X86_REG_EAX)


def main():
    results = []
    # The actual actor +174 getter copies future nodes, then HEAD-inserts its
    # current position. This establishes the first +340 point's identity.
    for current in ((8., 8.), (31.9, 17.9)):
        runner = OriginalReports()
        runner.uc.mem_write(runner.path + 8, struct.pack('<ff', current[0] * 1.5, current[1]))
        runner.make_list(runner.path + 0x2c, ((56., 8.), (56., 56.)), floats=True)
        snapshot = runner.actor_path_snapshot()
        expected = (float(int(int(current[0] * 1.5) / 1.5)), float(int(current[1])))
        assert snapshot == [expected, (56., 8.), (56., 56.)]
        runner.initial_consume()
        assert runner.points(runner.role + 0x34c) == [tuple(map(int, expected))]
        results.append({'case': 'actual_actor_getter_head_inserts_current', 'fixture_current': current,
            'snapshot': snapshot, 'history': runner.points(runner.role + 0x34c),
            'remaining_plan': runner.points(runner.role + 0x340, floats=True)})

    for current in ((15., 8.), (31.9, 17.9), (16., 16.)):
        runner = OriginalReports()
        runner.dynamic_current = True
        runner.uc.mem_write(runner.path + 8, struct.pack('<ff', current[0] * 1.5, current[1]))
        runner.make_list(runner.path + 0x2c, ((56., 8.),), floats=True)
        snapshot = runner.actor_path_snapshot()
        runner.initial_consume()
        runner.call(0x12171d0, (0, 1))
        history_first = runner.sent[-1]['points'][0]
        reported_current = runner.sent[-1]['current']
        assert abs(history_first[0] - reported_current[0]) <= 1
        assert history_first[1] == reported_current[1]
        if current == (15., 8.):
            assert history_first == (14, 8) and reported_current == (15, 8)
        results.append({'case': 'original_snapshot_vs_report_quantization', 'fixture_current': current,
            'snapshot_head': snapshot[0], 'sent': runner.sent[-1]})

    # A clear original straight leg can report a quantized midpoint whose
    # recomputed DDA crosses an extra cell. This is an actual false rejection
    # counterexample for mandatory source->reported-current revalidation.
    runner = OriginalReports()
    runner.dynamic_current = True
    start, end = (25, 88), (73, 70)
    runner.uc.mem_write(runner.path + 8, struct.pack('<ff', 37.5, 88.))
    runner.uc.mem_write(runner.path + 0x1c, struct.pack('<f', 1.))
    runner.make_list(runner.path + 0x2c, (end,), floats=True)
    runner.actor_path_snapshot()
    runner.initial_consume()
    original_float = runner.engine_tick(38)
    runner.call(0x12171d0, (0, 1))
    current = runner.sent[-1]['current']
    history = runner.sent[-1]['points']
    assert current == (60, 74) and history == [(24, 88)]
    assert runner.dda(start, end) == 0
    intended_trace = list(runner.dda_trace)
    assert runner.dda(start, current) == 1
    current_trace = list(runner.dda_trace)
    assert runner.dda(history[0], current) == 1
    history_trace = list(runner.dda_trace)
    from world_collision import _segment_samples
    samples = list(_segment_samples(start, current))
    wall_samples = [p for p in samples if (p[0] // 16, p[1] // 16) == (2, 4)]
    assert wall_samples
    assert current_trace[-1] == wall_samples[0] == (47, 79)
    assert (history_trace[-1][0] // 16, history_trace[-1][1] // 16) == (2, 4)
    assert all((x // 16, y // 16) != (2, 4) for x, y in intended_trace)
    results.append({'case': 'original_clear_leg_quantized_check_false_rejection',
        'start': start, 'intended_end': end, 'budget': 38, 'original_engine_float_current': original_float,
        'sent': runner.sent[-1], 'wall_cell': (2, 4), 'wall_pixel_range': (32, 64, 47, 79),
        'native_dda_start_to_intended_end': 0, 'native_dda_start_to_reported_current': 1,
        'native_dda_history_to_reported_current': 1, 'recomputed_wall_samples': wall_samples,
        'native_observed_start_current_wall_sample': current_trace[-1],
        'native_observed_history_current_wall_sample': history_trace[-1],
        'native_observed_intended_samples': intended_trace,
        'scope': 'original DDA-clear straight leg + original float tick + original current getter/report; A* generator not run'})

    # ROLE_MOVE's selected destination may skip multiple path corners: original
    # lookahead accumulates segment lengths until >500 or queue exhaustion.
    for plan, selected in ((((8., 8.), (56., 8.), (56., 56.)), (56, 56)),
                           (((8., 8.), (408., 8.), (408., 408.), (8., 408.)), (408, 408))):
        runner = OriginalReports()
        runner.make_list(runner.role + 0x340, plan, floats=True)
        runner.w(runner.role + 0x358, 8, 8)
        runner.call(0x1213f80)
        target = struct.unpack('<ii', runner.uc.mem_read(runner.role + 0x358, 8))
        assert target == selected
        p0, p1, packet = 0x500b000, 0x500b010, 0x500c000
        for ptr, point in ((p0, (8, 8)), (p1, target)):
            runner.w(ptr, 0x2278e54)
            runner.uc.mem_write(ptr + 4, struct.pack('<hh', *point))
        runner.call(0x120f9a0, (p0, p1, 0x55667788, 0x11223344), ecx=packet)
        actual_start = struct.unpack('<hh', runner.uc.mem_read(packet + 12, 4))
        actual_end = struct.unpack('<hh', runner.uc.mem_read(packet + 20, 4))
        assert actual_start == (8, 8) and actual_end == selected
        results.append({'case': 'original_role_move_destination_lookahead', 'planned_points': plan,
            'threshold': 500.0, 'selected_destination': target,
            'original_builder_start': actual_start, 'original_builder_end': actual_end,
            'first_future_corner': plan[1], 'not_authorized_as_direct_straight_leg': True})

    # Original engine loop: interpolation vs reached-node event. Single changes
    # in budget or pause byte distinguish future plans from consumed nodes.
    for budget, paused in ((24, False), (48, False), (49, False), (120, False), (49, True)):
        runner = OriginalReports()
        runner.uc.mem_write(runner.path + 8, struct.pack('<ff', 12., 8.))
        runner.uc.mem_write(runner.path + 0x1c, struct.pack('<f', 1.))
        runner.uc.mem_write(runner.path + 0x46, bytes([paused]))
        runner.make_list(runner.path + 0x2c, ((56., 8.), (56., 56.)), floats=True)
        actual = runner.engine_tick(budget)
        events = len(runner.engine_events)
        assert events == (0 if paused or budget <= 48 else 1 if budget == 49 else 2)
        assert len(runner.points(runner.path + 0x2c, floats=True)) == 2 - events
        if paused:
            assert actual == (8., 8.)
        results.append({'case': 'engine_tick', 'budget': budget, 'pause_46': paused,
            'current_after': actual, 'events': runner.engine_events,
            'remaining_future': runner.points(runner.path + 0x2c, floats=True)})

    # Execute the real engine -> App -> Scene virtual call -> MainCharacter.
    # Only actor-pointer lookup and unrelated base-character side effects are
    # adapted; node arrival, event value, dispatch and buffer mutation are real.
    runner = OriginalReports()
    runner.connect_original_dispatch()
    runner.uc.mem_write(runner.path + 8, struct.pack('<ff', 12., 8.))
    runner.uc.mem_write(runner.path + 0x1c, struct.pack('<f', 1.))
    runner.make_list(runner.path + 0x2c, ((56., 8.), (56., 56.)), floats=True)
    runner.actor_path_snapshot()
    runner.initial_consume()
    before = runner.points(runner.role + 0x34c)
    current = runner.engine_tick(49)
    assert runner.points(runner.role + 0x34c) == [(8, 8), (56, 8)]
    assert runner.points(runner.role + 0x340, floats=True) == [(56., 56.)]
    assert len(runner.engine_events) == 1 and runner.engine_events[0]['event'] == 1
    results.append({'case': 'original_engine_app_scene_maincharacter_chain', 'history_before': before,
        'current_after': current, 'history_after': runner.points(runner.role + 0x34c),
        'remaining_plan': runner.points(runner.role + 0x340, floats=True),
        'events': runner.engine_events, 'operations': runner.events})

    runner = OriginalReports()
    runner.connect_original_dispatch()
    runner.uc.mem_write(runner.path + 8, struct.pack('<ff', 12., 8.))
    runner.uc.mem_write(runner.path + 0x1c, struct.pack('<f', 1.))
    runner.make_list(runner.path + 0x2c, ((56., 8.), (56., 56.), (8., 56.)), floats=True)
    runner.actor_path_snapshot()
    runner.initial_consume()
    runner.engine_tick(49)
    runner.call(0x12171d0, (0, 1))
    assert runner.sent[-1]['points'] == [(8, 8), (56, 8)]
    assert runner.sent[-1]['current'] == (56, 9)
    assert runner.points(runner.role + 0x34c) == []
    runner.engine_tick(49)
    runner.call(0x1217f00)
    assert runner.sent[-1]['points'] == [(56, 56)]
    assert runner.sent[-1]['current'] == (54, 56)
    assert runner.points(runner.role + 0x340, floats=True) == []
    results.append({'case': 'ordinary_two_reports_form_ordered_travel_polyline',
        'initial_current': (8, 8), 'sent': runner.sent,
        'history_after': [], 'local_plan_after_stop': [],
        'engine_plan_before_outer_stop': runner.points(runner.path + 0x2c, floats=True)})
    # Native transfer loop baseline: no sender/get-current/actor adapter used.
    original = OriginalReports()
    original.make_list(original.role + 0x340, ((8.0, 8.0), (56.0, 8.0)), floats=True)
    original.initial_consume()
    assert original.points(original.role + 0x34c) == [(8, 8)]
    assert original.points(original.role + 0x340, floats=True) == [(56.0, 8.0)]
    results.append({'case': 'initial_consume_before_actor_progress', 'history': original.points(original.role + 0x34c),
        'remaining_plan': original.points(original.role + 0x340, floats=True), 'events': original.events})

    # Single-variable callback gates. Target deliberately differs from current
    # position: there is no current-position equality test in this callback.
    for name, field, value, event, expected in (
        ('ordinary_event_1', 0x36c, 0, 1, True),
        ('mode_1_skip_record', 0x36c, 1, 1, False),
        ('field_284_skip_record', 0x284, 1, 1, False),
        ('special_13c_skip_record', 0x13c, 1, 1, False),
        ('other_callback_event', 0x36c, 0, 2, False)):
        runner = OriginalReports()
        runner.make_list(runner.role + 0x340, ((56.0, 8.0), (56.0, 56.0)), floats=True)
        runner.w(runner.role + field, value)
        runner.w(runner.role + 0x358, 999, 999)  # Avoid unrelated next-destination sender.
        runner.consume(event)
        history = runner.points(runner.role + 0x34c)
        remaining = runner.points(runner.role + 0x340, floats=True)
        assert bool(history) == expected
        assert len(remaining) == (1 if event == 1 else 2)
        results.append({'case': name, 'fixture_current': runner.current, 'history': history,
            'remaining_plan': remaining, 'events': runner.events})

    # Actual top-level report builders: current comes from one position-getter
    # adapter; original list clone, constructor, sender call and clears run.
    for kind, function in (('check', 0x12171d0), ('stop', 0x1217f00)):
        for history in ((), ((8, 8), (56, 8))):
            runner = OriginalReports()
            runner.current = (56, 24)
            runner.make_list(runner.role + 0x340, ((56., 56.), (8., 56.)), floats=True)
            runner.make_list(runner.role + 0x34c, history)
            runner.call(function, (0, 1) if kind == 'check' else ())
            assert len(runner.sent) == 1
            assert runner.sent[0]['points'] == list(history)
            assert runner.sent[0]['current'] == runner.current
            assert runner.points(runner.role + 0x34c) == []
            remaining = runner.points(runner.role + 0x340, floats=True)
            assert len(remaining) == (2 if kind == 'check' else 0)
            results.append({'case': kind + '_builder_' + str(len(history)), 'sent': runner.sent,
                'remaining_plan': remaining, 'history_after': []})

    report = {'image_sha256': hashlib.sha256(DATA).hexdigest(), 'cases': results,
        'adapters': ['allocator/free/security cookie', 'current position getter', 'actor moving getter',
                     'base character callback side effects', 'CRT x87 sqrt', 'network send capture',
                     'scene actor-pointer lookup and unrelated special-object lookup', 'no map/navmesh recomputation'],
        'scope': 'original actor snapshot + engine tick + App/Scene/MainCharacter event dispatch + report builders; scene actor lookup/base-character side effects adapted',
        'no_game_gui_service_started': True}
    out = ROOT / 'evidence'
    (out / 'movement-reports-native.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    cs = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    text = 'native-image.bin SHA256 ' + report['image_sha256'] + '\n'
    for start, length in ((0x12149c1, 0x1d8), (0x1217633, 0x34b), (0x12171d0, 0x110),
                          (0x1217f00, 0xfb), (0x1214110, 0x32), (0x621f40, 0x60),
                          (0x6bc6c0, 0x90), (0x6bc7a0, 0x23c), (0x6bc5e0, 0xd5),
                          (0x81c670, 0x11c), (0x11d57f0, 0x29), (0x5a62b0, 4),
                          (0x12061a0, 0x52), (0x11f6540, 0x8c), (0x6528d0, 0x1a),
                          (0x1213f80, 0xcd), (0x120f9a0, 0x100)):
        text += '\n' + '\n'.join(f'{i.address:08x} {i.mnemonic:8} {i.op_str}'
            for i in cs.disasm(DATA[start-BASE:start-BASE+length], start)) + '\n'
    (out / 'movement-reports-native-disassembly.txt').write_text(text, encoding='utf-8')
    print(json.dumps({'cases': len(results), 'original_report_builders': 4, 'callback_producer_proven': True}))


if __name__ == '__main__':
    main()
