"""Offline original NPC navigation entry and bounded protected consumer probe."""
import hashlib
import json
import struct
from pathlib import Path
from collections import deque
from native_inspect import DATA, BASE, disasm, u32
from verify_world_native_pathfinding import NativePath
from unicorn.x86_const import UC_X86_REG_EIP, UC_X86_REG_ESP, UC_X86_REG_ECX, UC_X86_REG_EAX
from pfs import PfsArchive
from bxml import decode
from inspect_client import ROOT

OUT = Path(__file__).parent / 'evidence'


class Reached(Exception):
    pass


class Approach(NativePath):
    role, scene = 0x5501000, 0x5502000

    def __init__(self, grid, *, radius=1, side=0, final_radius=1, final_side=0, intro_lock=False, stop_before_consumer=False):
        self.events, self.tail = [], deque(maxlen=32)
        self.instructions = 0
        self.stop_before_consumer = stop_before_consumer
        self.rand_values = deque([radius - 1, side, 0, 0, 0, 0])
        self.radius, self.side, self.grid = radius, side, grid
        self.final_radius, self.final_side = final_radius, final_side
        self.queries = []
        self.helper_query_starts = []
        super().__init__(1, 1, b'\0')
        self.auto = self.role + 0x378
        self.w(0x294454c, self.role)
        self.w(self.role, 0x2299344)
        self.w(0x2944564, self.scene)
        self.w(self.scene + 0x110, 1006)
        self.w(0x2944550, 0x5505000)
        self.w(0x2945594, 0x5503000)
        self.w(0x294556c, 0x5504000)
        self.w(0x29455c0, 0)
        self.w(0x2945620, 0)
        self.w(0x294d190, 0)
        self.uc.mem_write(0x2945438, bytes([int(intro_lock)]))
        self.w(self.auto, 0, 0, 0, 0, 0, 0xffffffff, 0xffffffff)
        self.w(self.auto + 0x3c, 0x5506000)
        self.w(0x5506000, 0x5506000, 0x5506000, 0x5506000)
        self.uc.mem_write(0x5506019, b'\1')  # empty route-region tree sentinel
        self.uc.mem_map(u32(0x22448cc) & ~4095, 4096)
        self.w(0x5507000, 0x5507100)
        self.w(0x5507148, 0x550f100)
        self.w(0x5508000, 0x5508100)
        self.w(0x5508128, 0x6036e0)
        self.w(0x5508298, 0x5509000)
        cells = self.alloc(len(grid[2]))
        self.uc.mem_write(cells, grid[2])
        self.w(0x550908c, grid[0], grid[1], cells)

    def hook(self, emu, address, size, user):
        self.instructions += 1
        self.tail.append(hex(address))
        sp = emu.reg_read(UC_X86_REG_ESP)
        if address == u32(0x22448cc):
            value = self.rand_values.popleft() if self.rand_values else 0
            self.events.append({'adapter': 'rand', 'value': value})
            self.ret(value=value)
        elif address == u32(0x2299344 + 0xd0):
            output = self.r(sp + 4)
            self.w(output, 360, 2264)
            self.ret(4, output)
        elif address == 0x5a6660:
            self.ret(value=0x5507000)
        elif address == 0x550f100:
            self.ret(value=0x5508000)
        elif address == 0x6036e0:
            x, y = self.r(sp + 4), self.r(sp + 8)
            self.queries.append([x, y])
        elif address == 0x11cad00:
            self.helper_query_starts.append(len(self.queries))
            self.events.append({'original_npc_point_helper': [self.r(sp + i * 4) for i in range(2, 6)]})
        elif address == 0x1135590:
            self.events.append({'adapter': 'level', 'value': 10})
            self.ret(value=10)
        elif address in (0x11ca760, 0x11ca730):
            self.events.append({'adapter': 'ordinary_non_school_scene', 'address': hex(address)})
            self.ret(value=0)
        elif address == 0x120f1b0:
            self.events.append({'adapter': 'prepare_navigation_animation'})
            self.ret()
        elif address == 0x1141f90:
            self.events.append({'consumer_entry': hex(address)})
            if self.stop_before_consumer:
                raise Reached('before consumer body')
        elif address in (0x12143b0, 0x6138d0, 0x6212f0, 0x120eea0, 0x11deaa0):
            self.events.append({'downstream_entry': hex(address),
                'stack_words': [self.r(sp + i * 4) for i in range(1, 9)]})
            raise Reached('downstream native entry')
        elif address == 0x18da612:
            self.events.append({'protected_dispatch': hex(address)})
            self.rand_values = deque([self.final_radius-1, self.final_side, 0, 0, 0, 0])
        elif address >= 0x60000000:
            raise Reached('unadapted external import ' + hex(address))
        else:
            super().hook(emu, address, size, user)

    def run(self, args):
        self.w(self.stack, self.stop, *args)
        self.uc.reg_write(UC_X86_REG_ESP, self.stack)
        self.uc.reg_write(UC_X86_REG_ECX, self.auto)
        try:
            self.uc.emu_start(0x1142620, self.stop, count=200000)
            verdict = 'returned' if self.uc.reg_read(UC_X86_REG_EIP) == self.stop else 'instruction_budget'
        except Exception as exc:
            verdict = type(exc).__name__ + ': ' + str(exc)
        return {'arguments': list(args), 'radius_rand_mod3_plus1': self.radius, 'helper_side_rand': self.side,
            'final_radius': self.final_radius, 'final_side': self.final_side, 'stop': verdict,
            'EIP': hex(self.uc.reg_read(UC_X86_REG_EIP)), 'instructions': self.instructions,
            'auto_words_0_to_28': [self.r(self.auto + i) for i in range(0, 0x2c, 4)],
            'events': self.events, 'world_query_points': self.queries,
            'helper_query_starts': self.helper_query_starts, 'last_instruction_addresses': list(self.tail)}


def main():
    archive = PfsArchive(ROOT / 'artres/config.pfs')
    path = 'autoconfig/knight.gsp.npc.cnpcconfig.xml'
    raw = archive.read(path)
    npc = next(dict(e.attrib) for e in decode(raw) if e.attrib['id'] == '10498')
    args = (int(npc['xPos']) * 16, int(npc['yPos']) * 16, int(npc['mapid']), 10498, 0, 0, 1)
    assert args == (1664, 960, 1006, 10498, 0, 0, 1)
    grid_raw = PfsArchive(ROOT / 'artres/map.pfs').read('map_1006_jiaxing/maze.dat')
    header, width, height = struct.unpack_from('<III', grid_raw)
    assert header == 12 and len(grid_raw) == 12 + width * height
    grid = width, height, grid_raw[12:]
    cases = [Approach(grid, intro_lock=True).run(args)]
    cases += [Approach(grid, radius=r, side=s, stop_before_consumer=True).run(args) for r in (1, 2, 3) for s in (0, 1)]
    cases += [Approach(grid, final_radius=r, final_side=s).run(args) for r in (1, 2, 3) for s in (0, 1)]
    assert cases[0]['stop'] == 'returned' and not any('consumer_entry' in e for e in cases[0]['events'])
    assert cases[1]['auto_words_0_to_28'][:5] == [2, 0, 0, 10498, 1006]
    assert cases[1]['auto_words_0_to_28'][10] & 255 == 1
    import math
    for index, case in enumerate(cases[1:], 1):
        if index < 7:
            assert case['stop'] == 'Reached: before consumer body'
            x, y = case['auto_words_0_to_28'][5:7]
        else:
            assert case['stop'] == 'Reached: downstream native entry'
            event = next(e for e in case['events'] if e.get('downstream_entry') == '0x12143b0')
            x, y = event['stack_words'][:2]
            helpers = [e['original_npc_point_helper'] for e in case['events'] if 'original_npc_point_helper' in e]
            assert len(helpers) == 2 and helpers[-1][2] == case['final_radius']
        case['selected'] = {'xy': [x, y], 'maze_byte': grid[2][(y // 16) * width + x // 16],
            'distance_to_navigation_target': math.hypot(x-1664, y-960),
            'distance_to_placement': math.hypot(x-1668, y-970),
            'clear_mask1': (grid[2][(y // 16) * width + x // 16] & 1) == 0,
            'within_placement_48': (x-1668)**2 + (y-970)**2 <= 48**2}
    result = {'image_sha256': hashlib.sha256(DATA).hexdigest(),
        'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'source': {'path': path, 'sha256': hashlib.sha256(raw).hexdigest(), 'record': npc},
        'grid_source': {'path': 'map_1006_jiaxing/maze.dat', 'sha256': hashlib.sha256(grid_raw).hexdigest(), 'width': width, 'height': height},
        'instruction_sources': [{'address': hex(a), 'bytes_hex': DATA[a-BASE:a-BASE+n].hex()}
            for a,n in ((0x1142620,0x50),(0x1142bb6,0x48),(0x1142d93,0x65),
                        (0x1141f90,0x3e),(0x18da612,10),(0x121535f,0xb6),
                        (0x11cad00,0xa0),(0x11cb6b7,0x15),(0x6036e0,0x5f))],
        'cases': cases, 'scope': 'Original entry, actual ordinary input gate; level/scene-category/animation preparation adapters. Protected consumer runs bounded until original downstream entry, unsupported environment or budget. No live process.'}
    (OUT / 'world-npc-approach-native.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps({'cases': len(cases), 'stops': [c['stop'] for c in cases]}))


if __name__ == '__main__':
    main()
