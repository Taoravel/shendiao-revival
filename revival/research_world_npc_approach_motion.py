"""Bounded offline public NPC navigation -> original actor/path continuation.

No live client, network, persistent state or production module is used.
"""
import hashlib
import json
import struct
from collections import deque
from pathlib import Path

from native_inspect import BASE, DATA, u32
from native_gameplay_probe import probe
from bxml import decode
from inspect_client import ROOT
from pfs import PfsArchive
from world_grids import maze_grid
from verify_world_click_arrival_native import ClickArrivalProbe
from unicorn.x86_const import UC_X86_REG_EIP, UC_X86_REG_ESP, UC_X86_REG_ECX, UC_X86_REG_EAX


class Motion(ClickArrivalProbe):
    # Keep the full real maze outside the reusable harness's small fixed buffers.
    maze_cells = 0x5400000

    def alloc(self, count):
        if not getattr(self, 'maze_fixture_mapped', False):
            self.uc.mem_map(self.maze_cells, 0x20000)
            self.maze_fixture_mapped = True
        return super().alloc(count)

    def call(self, address, args=(), *, ecx=None):
        self.w(self.stack, self.stop, *args)
        self.uc.reg_write(UC_X86_REG_ESP, self.stack)
        self.uc.reg_write(UC_X86_REG_ECX, self.role if ecx is None else ecx)
        self.uc.emu_start(address, self.stop, count=4000000)
        assert self.uc.reg_read(UC_X86_REG_EIP) == self.stop, 'instruction budget'

    def __init__(self, grid, size, final_radius, final_side):
        self.navigation_events, self.tail = [], deque(maxlen=48)
        self.rand_values = deque([0, 0, 0, 0, 0, 0])
        self.final_radius, self.final_side = final_radius, final_side
        self.now = 1000
        super().__init__(grid.width, grid.height, grid.cells, (360, 2264), render_size=size)
        self.auto = self.role + 0x378
        self.w(self.scene + 0x110, 1006)
        self.w(self.scene + 0x30, 1006, 0)
        self.w(self.role + 0x330, 0xffffffff, 0xffffffff)
        # Native base constructor 120a3c9..120a3f3 initializes absent action
        # destinations to -1. Zero would invent an unrelated queued action.
        self.w(self.role + 0x140, *([0xffffffff] * 8))
        self.w(0x2944550, self.alloc(1024))
        self.w(self.auto, 0, 0, 0, 0, 0, 0xffffffff, 0xffffffff)
        head = self.alloc(32)
        self.w(self.auto + 0x3c, head)
        self.w(head, head, head, head)
        self.uc.mem_write(head + 0x19, b'\1')
        page = u32(0x22448cc) & ~4095
        self.uc.mem_map(page, 4096)
        clock_page = u32(0x2244db8) & ~4095
        if clock_page != page:
            self.uc.mem_map(clock_page, 4096)
        self.npc = self.alloc(1024)
        npc_actor, npc_path = self.alloc(1024), self.alloc(256)
        self.w(self.npc, 0x22985e4)
        self.w(self.npc + 0x10, 0x10203040, 0x50607080)
        self.uc.mem_write(self.npc + 0x18, b'\1')
        self.uc.mem_write(self.npc + 0x148, b'\1')
        self.w(self.npc + 0x150, 10498)
        self.w(self.npc + 0x48, npc_actor)
        self.w(npc_actor, 0x2462544)
        self.w(npc_actor + 0x1a8, npc_path)
        self.uc.mem_write(npc_path + 8, struct.pack('<ff', 1668 * 1.5, 970))

    def hook(self, emu, addr, size, user):
        self.tail.append(hex(addr))
        sp = emu.reg_read(UC_X86_REG_ESP)
        if addr == 0x29d6f58:
            self.navigation_events.append({'native_visit_integer_distance': emu.reg_read(UC_X86_REG_EAX),
                'compare_limit_exclusive': 13})
        if addr == u32(0x2244db8):
            self.navigation_events.append({'adapter': 'clock', 'value': self.now})
            self.ret(value=self.now)
            return
        if addr == 0x12172f0:
            self.navigation_events.append({'entry': hex(addr), 'return': hex(self.read(sp)),
                'npc_314': self.read(self.role + 0x314)})
            return  # Retain original target-completion consumer, no old UI seam.
        if addr == 0x11d1870:
            key = self.read(sp + 4)
            assert key == 10498
            self.navigation_events.append({'adapter': 'scene_NPC_template_lookup', 'key': key,
                'fixture_npc': hex(self.npc)})
            self.ret(4, self.npc)
            return
        if addr == self.stop + 0x100 and self.read(self.read(sp + 4) + 4) == 0xc2329:
            packet = self.read(sp + 4)
            emu.mem_write(self.packet_copy + 0x100, bytes(emu.mem_read(packet, 16)))
            self.messages.append({'kind': 0xc2329, 'sender_return': hex(self.read(sp)),
                'npc_key': struct.unpack('<Q', emu.mem_read(packet + 8, 8))[0],
                'object_hex': bytes(emu.mem_read(packet, 16)).hex()})
            self.ret(4, 1)
            return
        if addr == self.stop + 0x100 and self.read(self.read(sp + 4) + 4) == 0xc0fa7:
            packet = self.read(sp + 4)
            self.messages.append({'kind': 0xc0fa7, 'sender_return': hex(self.read(sp)),
                'object_prefix_hex': bytes(emu.mem_read(packet, 32)).hex(),
                'semantics': 'opaque follow-up packet; no business identity asserted'})
            self.ret(4, 1)
            return
        if addr == u32(0x22448cc):
            value = self.rand_values.popleft() if self.rand_values else 0
            self.navigation_events.append({'adapter': 'rand', 'value': value})
            self.ret(value=value)
            return
        if addr == 0x18da612:
            self.rand_values = deque([self.final_radius-1, self.final_side, 0, 0, 0, 0])
        if addr == 0x1135590:
            self.ret(value=10)
            return
        if addr in (0x11ca760, 0x11ca730):
            self.ret(value=0)
            return
        if addr == 0x120f1b0:
            self.ret()
            return
        if addr in (0x1142620, 0x1141f90, 0x12143b0, 0x11f8800,
                    0x6138d0, 0x6212f0, 0x1214d80, 0x1215790, 0x120eea0,
                    0x1140b50, 0x12170b0):
            self.navigation_events.append({'entry': hex(addr), 'return': hex(self.read(sp)),
                'args': [self.read(sp + i*4) for i in range(1, 5)],
                'npc_314': self.read(self.role + 0x314)})
        super().hook(emu, addr, size, user)

    def navigate(self):
        self.call(0x1142620, (1664, 960, 1006, 10498, 0, 0, 1), ecx=self.auto)
        return self.snapshot()


def main():
    root = Path(__file__).resolve().parent
    archive = PfsArchive(ROOT / 'artres/map.pfs')
    names = ('map_1006_jiaxing/maze.dat', 'map_1006_jiaxing/map.rmp')
    raw = [archive.read(n) for n in names]
    config_name = 'autoconfig/knight.gsp.npc.cnpcconfig.xml'
    config_raw = PfsArchive(ROOT / 'artres/config.pfs').read(config_name)
    config = next(dict(e.attrib) for e in decode(config_raw) if e.attrib.get('id') == '10498')
    assert (int(config['xPos'])*16, int(config['yPos'])*16, int(config['mapid'])) == (1664,960,1006)
    placement_name = 'map_1006_jiaxing/npc.xml'
    placement_raw = archive.read(placement_name)
    placement = next(dict(e.attrib) for e in decode(placement_raw).iter()
        if e.attrib.get('id') == '10498')
    assert (int(placement['posx']), int(placement['posy'])) == (1668,970)
    grid = maze_grid(raw[0])
    size = struct.unpack_from('<II', raw[1], 8)
    cases = []
    for radius, side in ((1, 0), (3, 1)):
        run = Motion(grid, size, radius, side)
        result = {'ticks': []}
        try:
            initial = run.navigate()
            result.update(status='returned', initial=initial)
            run.call(0x6529b0, (0x3f800000,), ecx=run.actor)
            for now, delta in ((2000, 1000), (3000, 1000), (4000, 1000), (4001, 1)):
                run.now = now
                result['ticks'].append({'clock': now, 'budget': delta,
                    'snapshot': run.actor_tick(now, delta)})
            run.w(run.stream, 0x224c100, run.stream_buffer, 0)
            run.w(run.stream_buffer - 12, 4096, 0, 1)
            run.call(0xe52020, (run.stream,), ecx=run.packet_copy + 0x100)
            body = bytes(run.uc.mem_read(run.stream_buffer, run.read(run.stream_buffer - 8)))
            assert body == struct.pack('>Q', 0x5060708010203040)
            _, decoded = probe(0xdb3450,0xe52020,0xdb3500,payload=body)
            assert struct.unpack_from('<Q',decoded,8)[0] == 0x5060708010203040
            result['visit_native_body_hex'] = body.hex()
            result['visit_native_decoder_verified'] = True
        except Exception as exc:
            result['status'] = type(exc).__name__ + ': ' + str(exc)
        result.update(final_radius=radius, final_side=side,
            eip=hex(run.uc.reg_read(UC_X86_REG_EIP)), events=run.navigation_events,
            messages=run.messages, tail=list(run.tail), queries=run.queries,
            engine_events=run.engine_events, arrival_trace=run.arrival_trace,
            final_npc_314=run.read(run.role + 0x314),
            heap_end=hex(run.heap),
            maze_unchanged=bytes(run.uc.mem_read(run.maze_cells,len(grid.cells))) == bytes(grid.cells))
        cases.append(result)
    for case, incoming, adjusted, planned, distance in zip(cases,
            ((1664,960),(1616,1008)), ((1664,1008),(1616,1008)),
            ((1672,1016),(1624,1016)), (3,4)):
        assert case['status'] == 'returned', case['status']
        assert case['maze_unchanged'] and case['final_npc_314'] == 0
        entry = next(e for e in case['events'] if e.get('entry') == '0x12143b0')
        assert tuple(entry['args'][:2]) == incoming and entry['npc_314'] == 10498
        actor_entries = [e for e in case['events'] if e.get('entry') == '0x11f8800']
        assert len(actor_entries) == 1 and tuple(actor_entries[0]['args'][:2]) == adjusted
        assert tuple(case['initial']['future_engine'][-1]) == planned
        assert case['initial']['future_engine'] == case['initial']['future_character']
        assert case['initial']['messages'] == 1  # No early Visit; first MOVE only.
        final = case['ticks'][-1]['snapshot']
        assert tuple(final['current']) == planned
        assert final['future_engine'] == final['future_character'] == final['history_character'] == []
        kinds = [m['kind'] for m in case['messages']]
        assert kinds[-3:] == [0xc0faa,0xc2329,0xc0fa7]
        assert all(k == 0xc0fa1 for k in kinds[:-3])
        assert [e['native_visit_integer_distance'] for e in case['events']
            if 'native_visit_integer_distance' in e] == [distance]
        assert case['visit_native_decoder_verified']
    result = {'image_sha256': hashlib.sha256(DATA).hexdigest(),
        'all_passed': True, 'source_logical': [360,2264], 'map_id': 1006,
        'navigation_arguments': [1664,960,1006,10498,0,0,1],
        'fixture_npc_key': 0x5060708010203040,
        'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'sources': [{'path': n, 'sha256': hashlib.sha256(b).hexdigest(), 'CRC_checked': True}
            for n,b in [*zip(names,raw),(config_name,config_raw),(placement_name,placement_raw)]],
        'original_config': config, 'original_placement': placement,
        'instruction_sources': [{'address': hex(a), 'bytes_hex': DATA[a-BASE:a-BASE+n].hex()}
            for a,n in ((0x12143b0,0x100),(0x1214502,0x112),(0x121491d,0x40),
                (0x12149c1,0x59),(0x120a364,0xa0),(0x1217633,0x126),
                (0x12172f0,0x161),(0x11f8800,0x6c),(0x12153d6,0x40))],
        'dependency_scripts': [{'path': n, 'sha256': hashlib.sha256((root/n).read_bytes()).hexdigest()}
            for n in ('verify_world_click_arrival_native.py','verify_world_click_move_native.py',
                'verify_world_blocked_goal_adjustment.py','verify_world_movement_reconciliation_native.py',
                'verify_movement_reports_native.py','native_gameplay_probe.py','pfs.py','world_grids.py')],
        'scope': 'Original public navigation -> native plan -> same actor real tick -> completion consumer -> native Visit builder/send/marshal. Scene template lookup and environment are explicit adapters; not GUI/OS/full App loop or production networking.',
        'tick_fixture': {'speed_setter': '0x6529b0', 'multiplier': 1.0,
            'clock_and_delta': [[2000,1000],[3000,1000],[4000,1000],[4001,1]],
            'units': 'deterministic native inputs, not original server speed/time evidence'},
        'cases': cases}
    out = root / 'evidence/world-npc-approach-motion.json'
    out.write_text(json.dumps(result, indent=2), encoding='utf8')
    print(json.dumps({'all_passed': True, 'cases': len(cases),
        'message_types': [[hex(m['kind']) for m in c['messages']] for c in cases],
        'final_points': [c['ticks'][-1]['snapshot']['current'] for c in cases],
        'maze_unchanged': all(c['maze_unchanged'] for c in cases), 'result': str(out)}))


if __name__ == '__main__':
    main()
