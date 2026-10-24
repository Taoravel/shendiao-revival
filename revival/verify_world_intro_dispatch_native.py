"""Exclusive offline SStartPlayCG dispatch/parser reachability research."""
import hashlib
import json
import struct
import re
import argparse
from collections import Counter
from pathlib import Path
from contextlib import redirect_stdout
from native_inspect import BASE, DATA, u32, disasm
from pfs import PfsArchive
from inspect_client import ROOT
from bxml import decode
from verify_world_native_pathfinding import NativePath
from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_EDX,
    UC_X86_REG_ESP, UC_X86_REG_EIP)

OUT = Path(__file__).parent / 'evidence'


class IntroReplay(NativePath):
    manager, scene, packet = 0x5400000, 0x5401000, 0x5402000
    engine, evt, renderer, rvt = 0x5403000, 0x5404000, 0x5405000, 0x5406000
    panel, gui, stream_vt = 0x5407000, 0x5408000, 0x5409000
    observed = {0xd57540: 'decoder', 0x12c43b0: 'process',
        0x12c4140: 'dispatch', 0x12c3be0: 'load_parse',
        0x12bec50: 'dispatch_line', 0x12c2d90: 'factory_start',
        0x12c0b00: 'queue_tick', 0x12b9a10: 'section_start',
        0x12bc870: 'clear_intro', 0x11d3a10: 'clear_scene_effect',
        0x12c1060: 'play_sound', 0x1211db0: 'ordinary_input_gate',
        0x123f160: 'event_dispatch', 0x12c2f50: 'skip_movie',
        0x12b99d0: 'section_return', 0x12b9ae0: 'section_end',
        0x12c0970: 'end_cleanup'}

    def __init__(self, raw, sound_alias):
        self.events = []
        self.native_hits = Counter()
        self.lines = raw.decode('utf-16le').split('\n')  # preserve BOM/CR for native parser
        self.line_index = 0
        self.library_strings = {}
        self.file_opened = False
        self.last_read_succeeded = False
        self.wstring_iat = {
            0x22443f0: 'literal', 0x2244414: 'literal', 0x2244450: 'default', 0x22443ec: 'destroy',
            0x224446c: 'copy', 0x22444b4: 'copy', 0x22445a0: 'append_obj',
            0x2244528: 'append_literal', 0x22443e8: 'data',
            0x22444ac: 'size', 0x2244410: 'size', 0x22445d4: 'erase',
            0x22445f4: 'first_of', 0x22445fc: 'first_not_of',
            0x22445f8: 'last_not_of', 0x22445d0: 'find_obj',
            0x22444e8: 'find_literal', 0x22444c0: 'substr', 0x2244520: 'concat',
            0x2244580: 'less',
        }
        self.imports = {u32(iat): kind for iat, kind in self.wstring_iat.items()}
        super().__init__(1, 1, b'\0')
        for address in [*self.imports, u32(0x2244664), u32(0x2244660), u32(0x224465c),
                        u32(0x224464c), u32(0x2244924), u32(0x22444c8), u32(0x22448a4)]:
            page = address & ~4095
            if not any(a <= page <= b for a, b, _ in self.uc.mem_regions()):
                self.uc.mem_map(page, 4096)
        self.w(u32(0x22444c8), 0xffffffff)
        self.w(0x2945620, self.manager)
        self.w(0x2944564, self.scene)
        self.w(0x294454c, 0)  # mainchar UI preparation is optional in original dispatcher
        self.w(0x2945618, 0)
        self.w(self.scene + 0x110, 1100)
        self.w(self.scene + 0x39c, 0x12345678)
        self.w(self.scene + 0xc8, 0, 0x540c000, 0)
        self.w(0x540c000, 0x540c000, 0x540c000, 0x540c000)
        self.uc.mem_write(0x540c021, b'\1')
        self.uc.mem_write(0x2945438, b'\1')
        self.w(self.engine, self.evt)
        self.w(self.evt + 0x50, 0x500f100)
        self.w(self.evt + 0x48, 0x500f130)
        self.w(0x540b000, 0x540b100)
        for offset, target in ((0xa4, 0x500f140), (0xa8, 0x500f150), (0xac, 0x500f160)):
            self.w(0x540b100 + offset, target)
        self.w(self.renderer, self.rvt)
        self.w(self.rvt + 0x124, 0x500f110)
        self.w(self.stream_vt + 4, 0)
        self.w(0x2945aec, 0x540a000)
        self.w(0x540a000, 0x540a100)
        self.w(0x540a104, 0x500f120)
        self.w(0x540a108, 0x500f170)
        self.w(0x29b77a0, 0x5410000)
        self.w(self.panel, 0x5410100)
        self.w(0x541011c, 0x500f1c0)
        self.w(0x2944798, 0x5410200)
        self.w(0x2945594, 0x5410300)
        self.w(0x294556c, 0x5410400)
        self.w(0x29455c0, 0)
        self.w(0x294d190, 0)
        self.w(0x2945074, 0x5410500)
        self.w(0x5410500, 0x5410600)
        self.w(0x541063c, 0x500f1d0)
        self.w(0x540a200, 2004)
        self.w(0x540a300, 2004)
        assert sound_alias['id'] == '2004'
        self.set_ws(0x540a304, sound_alias['Name'])
        self.set_ws(0x540a320, sound_alias['Patn'])
        for offset, target in ((0x64, 0x500f180), (0x6c, 0x500f190), (0x70, 0x500f1a0)):
            self.w(self.evt + offset, target)
        self.w(self.rvt + 0x188, 0x500f1b0)

    def wz(self, pointer):
        raw = bytearray()
        while True:
            unit = bytes(self.uc.mem_read(pointer, 2))
            if unit == b'\0\0':
                return raw.decode('utf-16le')
            raw.extend(unit); pointer += 2
            assert len(raw) < 100000

    def z8(self, pointer):
        raw = bytearray()
        while True:
            unit = bytes(self.uc.mem_read(pointer, 1))
            if unit == b'\0':
                return raw.decode('utf-8')
            raw.extend(unit); pointer += 1
            assert len(raw) < 100000

    def ws(self, obj):
        count = self.r(obj + 20)
        assert count < 100000
        ptr = obj + 4 if self.r(obj + 24) < 8 else self.r(obj + 4)
        return bytes(self.uc.mem_read(ptr, count * 2)).decode('utf-16le')

    def set_ws(self, obj, text):
        raw = text.encode('utf-16le')
        n = len(raw) // 2
        self.uc.mem_write(obj, bytes(28))
        self.w(obj + 20, n, max(7, n))
        ptr = obj + 4 if n <= 7 else self.alloc(len(raw) + 2)
        if n > 7:
            self.w(obj + 4, ptr)
        self.uc.mem_write(ptr, raw + b'\0\0')

    def hook(self, e, a, size, user):
        sp, this = e.reg_read(UC_X86_REG_ESP), e.reg_read(UC_X86_REG_ECX)
        if a in self.observed:
            self.native_hits[self.observed[a]] += 1
            if a in (0x12b9a10, 0x12bc870, 0x11d3a10):
                self.events.append({'native': self.observed[a], 'address': hex(a),
                    'caller_return': hex(self.r(sp)), 'this': hex(this)})
        kind = self.imports.get(a)
        if kind in ('default', 'literal', 'copy', 'append_obj', 'append_literal'):
            value = '' if kind == 'default' else (self.wz(self.r(sp + 4)) if kind in ('literal', 'append_literal') else self.ws(self.r(sp + 4)))
            if kind.startswith('append'):
                value = self.ws(this) + value
            self.set_ws(this, value); self.ret(0 if kind == 'default' else 4, this)
        elif kind == 'destroy':
            self.ret()
        elif kind == 'data':
            self.ret(value=this + 4 if self.r(this + 24) < 8 else self.r(this + 4))
        elif kind == 'size':
            self.ret(value=self.r(this + 20))
        elif kind == 'erase':
            pos, count = self.r(sp + 4), self.r(sp + 8)
            text = self.ws(this); self.set_ws(this, text[:pos] + text[pos + count:]); self.ret(8, this)
        elif kind in ('first_of', 'first_not_of', 'last_not_of', 'find_obj', 'find_literal'):
            text, pos = self.ws(this), self.r(sp + 8)
            needle = self.ws(self.r(sp + 4)) if kind == 'find_obj' else self.wz(self.r(sp + 4))
            if kind in ('find_obj', 'find_literal'):
                index = text.find(needle, pos)
            elif kind == 'last_not_of':
                index = next((i for i in range(min(pos, len(text)-1), -1, -1) if text[i] not in needle), -1)
            else:
                index = next((i for i in range(pos, len(text)) if (text[i] in needle) == (kind == 'first_of')), -1)
            self.ret(8, index & 0xffffffff)
        elif kind == 'substr':
            dest, pos, count = (self.r(sp + n) for n in (4, 8, 12))
            self.set_ws(dest, self.ws(this)[pos:pos + count]); self.ret(12, dest)
        elif kind == 'concat':
            dest, left, right = (self.r(sp + n) for n in (4, 8, 12))
            self.set_ws(dest, self.ws(left) + self.wz(right)); self.ret(value=dest)
        elif kind == 'less':
            self.ret(value=int(self.ws(self.r(sp + 4)) < self.ws(self.r(sp + 8))))
        elif a == u32(0x2244924):
            left, right = self.wz(self.r(sp + 4)), self.wz(self.r(sp + 8))
            self.ret(value=(left > right) - (left < right))
        elif a == u32(0x22448a4):
            dest, capacity, source, count = (self.r(sp + n) for n in (4, 8, 12, 16))
            assert count <= capacity
            e.mem_write(dest, bytes(e.mem_read(source, count)))
            self.ret(value=0)
        elif a == 0x1016030:
            dest, number = self.r(sp + 4), self.r(self.r(sp + 8))
            self.set_ws(dest, str(number)); self.ret(value=dest)
        elif a == 0x473b40:
            self.ret(value=self.gui)
        elif a == 0x453e10:
            self.library_strings[this] = self.z8(self.r(sp + 4))
            self.ret(4, this)
        elif a == 0x455580:
            self.events.append({'gui_load_layout': self.library_strings[self.r(sp + 4)]})
            self.ret(20, self.panel)
        elif a == 0x4552c0:
            self.events.append({'gui_find_window': self.library_strings[self.r(sp + 4)]})
            self.ret(4, 0x5410800)
        elif a == 0x500f1c0:
            self.events.append({'gui_panel_destroy': True})
            self.ret()
        elif a == 0x500f1d0:
            packet = self.r(sp + 4)
            self.uc.mem_write(0x5410900, bytes(self.uc.mem_read(packet, 12)))
            self.events.append({'native_end_send': {'type': self.r(packet + 4),
                'movie_id': self.r(packet + 8)}})
            self.ret(4, 1)
        elif a == 0x4663b0:
            self.ret(value=0x5411000)
        elif a == 0x466120:
            self.ret(4)
        elif a == 0x4720a0:
            self.ret(4)
        elif a == 0x5a6660:
            self.ret(value=self.engine)
        elif a == 0x500f100:
            self.ret(value=self.renderer)
        elif a == 0x500f110:
            self.ret(4)
        elif a == 0x500f120:
            # Host table adapter contains exactly the original prefix's alias.
            self.w(self.r(sp + 4), 0, 0x540a200, 0x540a204, 0x540a204)
            self.ret(4)
        elif a == 0x500f170:
            assert self.r(sp + 4) == 2004
            self.ret(4, 0x540a300)
        elif a == 0x500f180:
            self.ret(4)
        elif a == 0x500f190:
            self.ret(8, 0)
        elif a == 0x500f1a0:
            self.events.append({'engine_audio_play': self.ws(self.r(sp + 4))})
            self.ret(24, 0)
        elif a == 0x500f1b0:
            self.ret(value=1)
        elif a == 0x500f130:
            self.ret(value=0x540b000)
        elif a == 0x500f140:
            self.ret(4)
        elif a == 0x500f150:
            self.w(self.r(sp + 4), 0, 0, 1024, 768)
            self.ret(4)
        elif a == 0x500f160:
            self.events.append({'camera_move': [self.r(self.r(sp + 4) + n) for n in (0, 4)]})
            self.ret(8)
        elif a in (0x11d8910,):
            self.events.append({'boundary': hex(a)}); self.ret()
        elif a == 0x11e0c70:
            self.events.append({'scene_load': [self.r(sp + n) for n in (4, 8, 12, 16)]})
            self.ret(16)
        elif a == 0x11daa10:
            values = [self.r(sp + n) for n in range(4, 40, 4)]
            values[2] = self.ws(values[2])
            self.events.append({'scene_create_actor': values})
            self.ret(36)
        elif a == 0x11e0a80:
            self.events.append({'scene_restore_request': self.r(sp + 4)})
            self.ret(4)
        elif a == 0x11d3620:
            self.events.append({'scene_restore_ui': True})
            self.ret()
        elif a == 0x12c3580:
            path = self.ws(self.r(sp + 4))
            self.events.append({'resource_stream': path})
            self.file_opened = True
            self.w(this, self.stream_vt)
            self.ret(8, this)
        elif a == u32(0x2244664):
            self.ret(value=0)
        elif a == u32(0x2244660):
            stream, output = self.r(sp + 4), self.r(sp + 8)
            self.last_read_succeeded = self.line_index < len(self.lines)
            if self.last_read_succeeded:
                self.set_ws(output, self.lines[self.line_index]); self.line_index += 1
            else:
                self.set_ws(output, '')
            self.ret(value=stream)
        elif a == u32(0x224465c):
            self.ret(value=int(self.last_read_succeeded))
        elif a in (0x12bfcb0, u32(0x224464c)):
            self.ret()
        elif a == 0x4c1b40:
            self.library_strings[this] = self.wz(self.r(sp + 4))[:self.r(sp + 8)]
            self.ret(8, this)
        elif a == 0x48fdc0:
            text = self.library_strings.get(self.r(sp + 4), '')
            match = re.match(r'\s*([+-]?\d+)', text)
            self.ret(value=(int(match[1]) if match else 0) & 0xffffffff)
        elif a == 0x459ef0:
            self.ret()
        elif a == 0x11d37d0:
            self.events.append({'dispose_intro_effect': self.r(sp + 4)})
            self.ret(4)
        else:
            if a >= 0x60000000:
                raise AssertionError(('unadapted external import', hex(a), hex(self.r(sp))))
            super().hook(e, a, size, user)


def run_case(movie_id, raw, sound_alias, *, remove_start=False, manager_present=True,
             cold_ui=False, event_skip=False):
    if remove_start:
        # Single-variable counterfactual in emulator input only. Original PFS
        # remains untouched and its independent source hash is reported below.
        lines = raw.decode('utf-16le').split('\n')
        index = next(i for i, line in enumerate(lines) if line.strip() == 'Start')
        lines[index] = ''
        raw = '\n'.join(lines).encode('utf-16le')
    r = IntroReplay(raw, sound_alias)
    r.execute(0x12c3f70, ecx=r.manager)
    assert r.r(r.manager) == 0x229f178
    if not cold_ui:
        r.w(r.manager + 0x48, r.panel)  # installed UI panel external boundary
    stream, buf = 0x540d000, 0x540e000
    body = struct.pack('>i', movie_id)  # exact body emitted by world_newbie.py
    r.w(stream, 0, buf, 0)
    r.w(buf - 12, 4, 4, 1)
    r.uc.mem_write(buf, body)
    r.execute(0xd57540, ecx=r.packet, args=(stream,))
    assert r.r(r.packet + 8) == movie_id and r.r(stream + 8) == 4
    if not manager_present:
        r.w(0x2945620, 0)
    r.execute(0x12c43b0, ecx=r.packet, args=(0, 0))
    begin, end = r.r(r.manager + 0x20), r.r(r.manager + 0x24)
    count = (end - begin) // 4
    first_sections = [{'vtable': hex(r.r(r.r(begin + i * 4))),
                       'param8_signed': struct.unpack('<i', r.uc.mem_read(r.r(begin + i * 4) + 8, 4))[0]}
                      for i in range(min(9, count))]
    initial = {'intro_flag': r.r(0x2945438) & 255,
               'scene_effect': r.r(r.scene + 0x39c)}
    assert initial == {'intro_flag': 1, 'scene_effect': 0x12345678}
    ticks = []
    if manager_present:
        for i in range(7):
            r.execute(0x12c0b00, ecx=r.manager, args=(16,))
            ticks.append({'tick': i + 1, 'intro_flag': r.r(0x2945438) & 255,
                          'scene_effect': r.r(r.scene + 0x39c),
                          'current_vtable': hex(r.r(r.r(r.manager + 0x60)))})
    final = {'intro_flag': r.r(0x2945438) & 255,
             'scene_effect': r.r(r.scene + 0x39c)}
    movie_active = bytes(r.uc.mem_read(r.manager + 0x3c, 1))[0]
    assert movie_active == int(manager_present)
    # Original gate reads fake player's default-zero +2e4, then the *actual*
    # MovieManager+3c written by original dispatch. No gate adapter is installed.
    input_allowed = r.execute(0x1211db0, ecx=0x540f000) & 255
    assert input_allowed == 0
    should_unlock = manager_present and not remove_start
    assert final == ({'intro_flag': 0, 'scene_effect': 0} if should_unlock else initial)
    assert r.native_hits['section_start'] == int(should_unlock)
    assert r.native_hits['clear_intro'] == int(should_unlock)
    assert r.native_hits['clear_scene_effect'] == int(should_unlock)
    assert r.file_opened == manager_present
    if manager_present:
        assert {'resource_stream': f'/config/movie/{movie_id}.txt'} in r.events
    skip = None
    if event_skip:
        assert should_unlock
        # Native event dispatcher, not a direct Section/skip/cleanup call.
        r.execute(0x123f160, ecx=0x5412000, args=(0x7b8a4,))
        skip_begin, skip_end = r.r(r.manager + 0x20), r.r(r.manager + 0x24)
        skip_queue = [hex(r.r(r.r(p))) for p in range(skip_begin, skip_end, 4)]
        assert skip_queue == ['0x229ed64', '0x229ed9c']
        r.execute(0x12c0b00, ecx=r.manager, args=(500,))
        r.execute(0x12c0b00, ecx=r.manager, args=(1500,))
        assert r.r(0x5410904) == 0xc0018 and r.r(0x5410908) == movie_id
        # Serialize the object actually constructed and passed to native send.
        native_stream, native_buf = 0x5413000, 0x5414000
        r.w(native_stream, 0, native_buf, 0)
        r.w(native_buf - 12, 64, 0, 1)
        r.execute(u32(0x226fab8), ecx=0x5410900, args=(native_stream,))
        body_size = r.r(r.r(native_stream + 4) - 8)
        actual_body = bytes(r.uc.mem_read(r.r(native_stream + 4), body_size))
        after_allowed = r.execute(0x1211db0, ecx=0x540f000) & 255
        skip = {'event_entry': '0x123f160', 'event_id': '0x7b8a4',
            'replacement_queue': skip_queue, 'tick_deltas_ms': [500, 1500],
            'actual_end_type': r.r(0x5410904), 'actual_end_body_hex': actual_body.hex(),
            'movie_id': r.r(0x5410908), 'manager_3c_after': r.r(r.manager + 0x3c) & 255,
            'ordinary_input_allowed': bool(after_allowed)}
        assert actual_body == body and skip['manager_3c_after'] == 0 and after_allowed == 1
    return {'movie_id': movie_id, 'remove_start': remove_start,
        'manager_present': manager_present, 'cold_ui': cold_ui, 'wire_body_hex': body.hex(),
        'decoded_movie_id': r.r(r.packet + 8), 'decoder_consumed': r.r(stream + 8),
        'loaded_lines': r.line_index, 'queued_sections': count,
        'first_sections': first_sections, 'initial': initial, 'ticks': ticks,
        'final': final, 'movie_active': movie_active,
        'ordinary_input_allowed': bool(input_allowed),
        'skip_event_result': skip, 'native_hits': dict(r.native_hits), 'events': r.events}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--movie-id', type=int, help='Limit original-resource positive replay to one ID')
    parser.add_argument('--no-controls', action='store_true', help='Skip two single-variable controls')
    args = parser.parse_args()
    archive = PfsArchive(ROOT / 'artres/config.pfs')
    effect_path = 'autoconfig/knight.gsp.effectpath.ceffectpath.xml'
    effect_raw = archive.read(effect_path)
    sound = next(dict(e.attrib) for e in decode(effect_raw) if e.attrib.get('id') == '2004')
    assert sound == {'id': '2004', 'Name': '杀阵', 'Patn': '/sound/music/huashanzhidian.ogg'}
    routes_path = Path(__file__).parent / 'catalogs/newbie-routes.json'
    route_bytes = routes_path.read_bytes()
    routes = json.loads(route_bytes)['routes']
    task_path = 'autoconfig/knight.gsp.task.cmainmissioninfo.xml'
    task_raw = archive.read(task_path)
    tasks = {int(e.attrib['id']): e.attrib for e in decode(task_raw)}
    for route in routes:
        task = tasks[route['intro_task_id']]
        assert task['MissionType'] == '50'
        assert int(task['ScenarioInfoAnimationID']) == route['intro_movie_id']
    ui_archive = PfsArchive(ROOT / 'artres/ui.pfs')
    ui_resources = []
    for ui_path in ('layouts/sceneaniback.layout', 'layouts/scenemovieexitconfirmdlg.layout'):
        ui_raw = ui_archive.read(ui_path)
        windows = [dict(e.attrib) for e in decode(ui_raw).iter() if e.tag == 'Window']
        ui_resources.append({'path': ui_path, 'sha256': hashlib.sha256(ui_raw).hexdigest(), 'windows': windows})
    movie_ids = sorted({r['intro_movie_id'] for r in routes})
    assert len(routes) == 43 and len(movie_ids) == 10
    if args.movie_id is not None:
        assert args.movie_id in movie_ids
        movie_ids = [args.movie_id]
    cases, resources = [], []
    for movie_id in movie_ids:
        path = f'movie/{movie_id}.txt'
        raw = archive.read(path)
        lines = raw.decode('utf-16').splitlines()
        start_line = next(i + 1 for i, line in enumerate(lines) if line.strip() == 'Start')
        resources.append({'path': path, 'sha256': hashlib.sha256(raw).hexdigest(),
            'bytes': len(raw), 'first_start_line': start_line, 'prefix_lines': lines[:start_line],
            'roles': [r['role_id'] for r in routes if r['intro_movie_id'] == movie_id]})
        cases.append(run_case(movie_id, raw, sound))
        print(json.dumps({'movie_id': movie_id, 'final': cases[-1]['final']}, ensure_ascii=True), flush=True)
    controls = []
    if not args.no_controls:
        raw = archive.read('movie/11001.txt')
        controls = [run_case(11001, raw, sound, remove_start=True),
                    run_case(11001, raw, sound, manager_present=False)]
    cold_case = run_case(11001, archive.read('movie/11001.txt'), sound, cold_ui=True, event_skip=True)
    result = {'image_sha256': hashlib.sha256(DATA).hexdigest(),
        'route_catalog_sha256': hashlib.sha256(route_bytes).hexdigest(),
        'route_count': len(routes), 'source_movie_count': 10,
        'original_task_source': {'path': task_path, 'sha256': hashlib.sha256(task_raw).hexdigest(),
            'checked_routes': len(routes), 'all_type50_animation_matches': True},
        'ui_resource_sources': ui_resources,
        'resource_sources': resources, 'effect_path_source': {'path': effect_path,
            'sha256': hashlib.sha256(effect_raw).hexdigest(), 'record': sound},
        'cases': cases, 'controls': controls, 'cold_ui_and_skip_event': cold_case,
        'scope': 'Original decoder, Process, constructor, parser/factories and queue/Start/clear; external library, UI and world/engine adapters. No live client or full rendering.'}
    suffix = '' if args.movie_id is None else f'-{args.movie_id}'
    (OUT / f'world-intro-dispatch-native{suffix}.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    with (OUT / 'world-intro-dispatch-native-disassembly.txt').open('w', encoding='utf-8') as output, redirect_stdout(output):
        for address, length in ((0xd57540, 0x66), (0x12c43b0, 0x20), (0x12c4140, 0x2d0),
            (0x12c3be0, 0x330), (0x12c3f10, 0x60), (0x12bec50, 0x150),
            (0x12c2d90, 0x80), (0x12c0b00, 0x5c), (0x12bc6c0, 0x80),
            (0x12b9a10, 0x20), (0x12bc870, 0x40), (0x11d3a10, 0x40), (0x1211db0, 0xc0),
            (0x123f160, 0x250), (0x12c2f50, 0x150), (0x12c0970, 0x17c), (0xe3fd70, 0x2d),
            (0x12bb0f0, 0x80), (0x12baec0, 0x20)):
            print('\nFUNCTION', hex(address)); disasm(address, length)
    print(json.dumps({'positive_cases': len(cases), 'controls': len(controls), 'cold_ui_and_skip': 1, 'passed': True}))


if __name__ == '__main__':
    main()
