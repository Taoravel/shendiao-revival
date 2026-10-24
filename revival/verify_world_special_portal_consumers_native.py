"""Exclusive offline special-portal consumers; no world runtime or GUI calls."""
import hashlib
import json
import struct
from collections import defaultdict
from contextlib import redirect_stdout
from pathlib import Path

from native_inspect import BASE, DATA, u32, disasm
from inspect_client import ROOT
from pfs import PfsArchive
from bxml import decode
from native_gameplay_probe import probe
from verify_world_native_pathfinding import NativePath
from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_EDI,
    UC_X86_REG_ESI, UC_X86_REG_EBP, UC_X86_REG_ESP, UC_X86_REG_EIP)

OUT = Path(__file__).parent / 'evidence'


class PortalReplay(NativePath):
    scene, sentinel, node, world = 0x5400000, 0x5401000, 0x5402000, 0x5403000
    endpoint, endpoint_vt, send_sink = 0x5404000, 0x5405000, 0x500f100
    marker = 0x5406000

    def __init__(self, map_id):
        self.end_at = None
        self.calls = []
        self.marker_entry = u32(0x2461754 + 0x94)
        super().__init__(1, 1, b'\0')
        self.w(self.scene + 0x110, map_id)
        self.w(0x2944564, self.scene)
        self.w(0x2945618, 0)
        self.w(0x29a4a70 + 0x40, self.world)
        self.w(self.world, 0x2461754)
        self.w(self.endpoint, self.endpoint_vt)
        self.w(self.endpoint_vt + 0x3c, self.send_sink)

    def tree(self, key, present_q64):
        header, node = self.sentinel, self.node
        self.w(self.scene + 0x454, 0, header, 1)
        self.w(header, node, node, node)
        self.uc.mem_write(header + 0x51, b'\1')
        self.w(node, header, header, header)
        self.w(node + 0x10, key)
        self.w(node + 0x18, 0x226f030)
        self.w(node + 0x20, present_q64 & 0xffffffff, present_q64 >> 32)

    def hook(self, e, a, size, user):
        sp = e.reg_read(UC_X86_REG_ESP)
        if a == self.end_at:
            e.reg_write(UC_X86_REG_EIP, self.stop)
        elif a == self.marker_entry:
            self.calls.append({'kind': 'world_marker_boundary', 'entry': hex(a),
                'arguments': [self.r(sp + n) for n in (4, 8, 12, 16, 20)]})
            self.ret(20, self.marker)
        elif a == 0x11dc960:
            self.calls.append({'kind': 'scene_marker_list_boundary',
                'this': e.reg_read(UC_X86_REG_ECX), 'marker': self.r(self.r(sp + 4))})
            self.ret(4)
        elif a == 0xe78ee0:
            self.calls.append({'kind': 'clear_house_table_boundary'}); self.ret()
        elif a == 0x11dec90:
            self.calls.append({'kind': 'goto_refresh_boundary'}); self.ret()
        elif a == 0x813860:
            self.ret(value=self.endpoint)
        elif a == self.send_sink:
            message = self.r(sp + 4)
            item = {'kind': 'outbound_message_boundary',
                    'vtable': hex(self.r(message)), 'type': hex(self.r(message + 4))}
            if self.r(message + 4) == 0xc4fd2:
                item['field_8'] = self.r(message + 8)
            self.calls.append(item)
            self.ret(4, 1)
        elif a == 0x11e0f80:
            self.calls.append({'kind': 'house_table_update_boundary',
                'this': e.reg_read(UC_X86_REG_ECX), 'map_argument': self.r(sp + 4)})
            self.ret(4)
        else:
            super().hook(e, a, size, user)

    def marker_branch(self, source, destx):
        self.w(self.stack + 0x14, destx)
        self.w(self.stack + 0x1c, source[0])
        self.w(self.stack + 0x24, self.scene)
        self.uc.reg_write(UC_X86_REG_ESI, self.scene)
        self.uc.reg_write(UC_X86_REG_EDI, source[1])
        self.end_at = 0x11df0d7
        self.execute(0x11def6d)
        return self.calls

    def load_branch(self):
        self.uc.reg_write(UC_X86_REG_ESI, self.scene)
        self.uc.reg_write(UC_X86_REG_EBP, 0)
        self.end_at = 0x11e04bd
        self.execute(0x11e0449)
        return self.calls


def original_sources():
    config = PfsArchive(ROOT / 'artres/config.pfs')
    maps = PfsArchive(ROOT / 'artres/map.pfs')
    raw_config = config.read('autoconfig/knight.gsp.map.cmapconfig.xml')
    configs = {int(r.attrib['id']): dict(r.attrib) for r in decode(raw_config)}
    sources, gotos, tables = [], {}, {}
    for name in ('chouseweizhi', 'chousegoup', 'cxiaoqu'):
        entry = 'autoconfig/knight.gsp.home.' + name + '.xml'
        raw = config.read(entry)
        tables[name] = [dict(r.attrib) for r in decode(raw)]
        sources.append({'entry': entry, 'sha256': hashlib.sha256(raw).hexdigest(),
                        'rows': len(tables[name])})
    for mid in (1594, 1595, 1596, 1597, 1598, 1627):
        entry = configs[mid]['resdir'] + '/goto.xml'
        raw = maps.read(entry)
        gotos[mid] = [dict(r.attrib) for r in decode(raw)]
        sources.append({'entry': entry, 'sha256': hashlib.sha256(raw).hexdigest(),
                        'rows': len(gotos[mid]), 'map_attributes': configs[mid]})
    groups = defaultdict(list)
    for row in gotos[1594]:
        assert row['destmap'] == '1594' and row['destx'] == row['desty']
        groups[int(row['destx'])].append((int(row['posx']), int(row['posy'])))
    house_match = []
    for house in tables['chouseweizhi']:
        hid = int(house['id']); cells = groups[hid]
        assert len(cells) == 25
        center = ((min(x for x,y in cells) + max(x for x,y in cells)) // 2,
                  (min(y for x,y in cells) + max(y for x,y in cells)) // 2)
        assert center == (int(house['xchuansong']), int(house['ychuansong']))
        house_match.append({'house_table_row': house, 'goto_destx_key': hid,
                            'portal_center': center, 'cells': len(cells)})
    assert set(groups) == set(range(1, 26))
    communities = tables['cxiaoqu']
    assert {r['housenum'] for r in communities} == {'25'}
    return {'config_sha256': hashlib.sha256(raw_config).hexdigest(), 'sources': sources,
            'house_portal_config_matches': house_match, 'home_group_rows': tables['chousegoup'],
            'community_summary': {'rows': len(communities),
                'zoneids': sorted({int(r['zoneid']) for r in communities}),
                'housenum_values': [25], 'first_id': communities[0]['id'],
                'last_id': communities[-1]['id'],
                'all_ids_equal_xiaoquid': all(r['id'] == r['xiaoquid'] for r in communities)}}, gotos


def marker_cases(gotos):
    rows = []
    for key, nonzero, lookup_key, expected in ((1, 1, 1, True), (9, 1, 9, True),
            (25, 0x100000000, 25, True), (9, 0, 9, False), (9, 1, 10, False)):
        source_row = next(r for r in gotos[1594] if int(r['destx']) == key)
        source = (int(source_row['posx']), int(source_row['posy']))
        r = PortalReplay(1594); r.tree(lookup_key, nonzero)
        actual = r.marker_branch(source, key)
        marker = [c for c in actual if c['kind'] == 'world_marker_boundary']
        assert bool(marker) == expected
        if marker:
            assert marker[0]['arguments'][1:] == [0, source[0] * 24, source[1] * 16, 1]
        rows.append({'map_id': 1594, 'raw_destx': key, 'table_key': lookup_key,
                      'MapHouseInfo_first_q64': nonzero, 'calls': actual})
    for mid in (1595, 1596, 1597, 1598, 1627):
        raw = gotos[mid][0]; source = (int(raw['posx']), int(raw['posy']))
        r = PortalReplay(mid)
        actual = r.marker_branch(source, int(raw['destx']))
        marker = next(c for c in actual if c['kind'] == 'world_marker_boundary')
        assert marker['arguments'][1:] == [int(1595 <= mid <= 1598),
                                         source[0] * 24, source[1] * 16, 1]
        rows.append({'map_id': mid, 'raw_row': raw, 'calls': actual})
    return rows


def lifecycle_cases():
    rows = []
    for mid in (1594, 1595, 1627):
        r = PortalReplay(mid)
        actual = r.load_branch()
        messages = [c for c in actual if c['kind'] == 'outbound_message_boundary']
        assert len(messages) == int(mid == 1594)
        if messages:
            assert messages[0]['type'] == '0xc0fdb'
        else:
            assert [c['kind'] for c in actual] == ['clear_house_table_boundary', 'goto_refresh_boundary']
        rows.append({'phase': 'post_original_map_load_slice', 'map_id': mid, 'calls': actual})
    for mid in (1594, 1595, 1627):
        r = PortalReplay(mid); packet = 0x5407000
        r.execute(0x11e1970, ecx=packet, args=(0, 0))
        assert len(r.calls) == int(mid == 1594)
        if r.calls:
            assert r.calls[0]['map_argument'] == packet + 8
        rows.append({'phase': 'SRequestXiaoquMapInfo_Process', 'map_id': mid, 'calls': r.calls})
    return rows


def visit_builder_case():
    r = PortalReplay(1594)
    dialog = 0x5409000
    r.w(dialog + 0x34, 101)
    r.uc.reg_write(UC_X86_REG_ESI, dialog)
    r.end_at = 0x154e3e2
    r.execute(0x154e3b0)
    assert r.calls == [{'kind': 'outbound_message_boundary', 'vtable': '0x2274648',
                        'type': '0xc4fd2', 'field_8': 101}]
    return [{'slice': ['0x154e3b0', '0x154e3e2'], 'dialog_field_34': 101,
             'calls': r.calls, 'scope': 'Builder after preceding UI eligibility checks, not full click'}]


class SceneNotificationReplay(PortalReplay):
    def __init__(self):
        super().__init__(1627)
        self.copy_string = u32(0x224446c)
        page = self.copy_string & ~4095
        if not any(begin <= page <= end for begin, end, _ in self.uc.mem_regions()):
            self.uc.mem_map(page, 4096)

    def hook(self, e, a, size, user):
        sp = e.reg_read(UC_X86_REG_ESP)
        if a == 0x813830:
            self.ret(value=0x540a000)  # fixture app's byte20 is clear
        elif a == self.copy_string:
            dest, source = e.reg_read(UC_X86_REG_ECX), self.r(sp + 4)
            assert self.r(source + 20) == 0
            e.mem_write(dest, bytes(e.mem_read(source, 28)))
            self.ret(4, dest)
        elif a == 0x11e21f0:
            self.calls.append({'kind': 'normal_scene_notification_boundary',
                'this': e.reg_read(UC_X86_REG_ECX),
                'scene_q64': struct.unpack('<Q', e.mem_read(sp + 4, 8))[0],
                'position': list(struct.unpack('<ii', e.mem_read(sp + 12, 8)))})
            e.reg_write(UC_X86_REG_EIP, self.stop)
        else:
            super().hook(e, a, size, user)


def same_scene_notification_case():
    r = SceneNotificationReplay(); packet = 0x540b000
    r.w(packet + 0x20, 7)  # empty native wstring's capacity
    r.uc.mem_write(packet + 0x28, struct.pack('<hh', 1616, 1840))
    r.w(packet + 0x30, 516015)
    r.w(packet + 0x38, 1627, 0)
    r.execute(0x11e3140, ecx=packet, args=(0, 0))
    assert r.calls == [{'kind': 'normal_scene_notification_boundary', 'this': r.scene,
                        'scene_q64': 1627, 'position': [1616, 1840]}]
    return [{'current_map': 1627, 'notification_map': 1627, 'calls': r.calls,
        'scope': 'Original Process accepts same map and forwards ordinary scene notification; downstream scene callback not executed'}]


def codec_cases():
    rows = []
    for name, ctor, marshal, decoder, fields, expected in (
        ('CRequestXiaoquMapInfo', 0xdaa9b0, 0xdaa9d0, 0xdaa9e0, {}, b''),
        ('CEnterCommunity', 0xd80d00, 0xe49860, 0xd80da0, {8: struct.pack('<i', 101)}, struct.pack('>i', 101)),
        ('CBaifang', 0xd7fb20, 0xe495f0, 0xd7fbc0, {8: struct.pack('<i', 205)}, struct.pack('>i', 205)),
        ('CHomeResetPosition', 0xdaa400, 0xe50720, 0xdaa4a0,
            {8: struct.pack('<ii', 132, 76)}, struct.pack('>ii', 132, 76))):
        payload, decoded = probe(ctor, marshal, decoder, fields=fields)
        assert payload == expected, (name, payload.hex())
        rows.append({'protocol': name, 'type': hex(struct.unpack_from('<I', decoded, 4)[0]),
                     'body_hex': payload.hex(), 'original_roundtrip': True})
    for first, last in ((1, 2), (0x100000007, 0x200000009)):
        name = 'Home'
        fields = {8: struct.pack('<Q', first), 0x14: name.encode('utf-16le') + b'\0\0',
                  0x24: struct.pack('<I', len(name)), 0x30: struct.pack('<Q', last)}
        payload, decoded = probe(0xd49880, 0xe3cc90, 0xf55e50, fields=fields)
        expected = struct.pack('>Q', first) + bytes([len(name) * 2]) + name.encode('utf-16le') + struct.pack('>Q', last)
        assert payload == expected
        assert struct.unpack_from('<Q', decoded, 8)[0] == first
        assert struct.unpack_from('<Q', decoded, 0x30)[0] == last
        rows.append({'bean': 'MapHouseInfo', 'first_q64': first, 'last_q64': last,
                     'body_hex': payload.hex(), 'original_roundtrip': True})
    # Original one-leaf map serializer/decoder, including real native tree iteration.
    header, node = 0x5001300, 0x5001400
    h = bytearray(0x58); struct.pack_into('<III', h, 0, node, node, node); h[0x51] = 1
    n = bytearray(0x58); struct.pack_into('<III', n, 0, header, header, header)
    struct.pack_into('<I', n, 0x10, 9); struct.pack_into('<I', n, 0x18, 0x226f030)
    struct.pack_into('<Q', n, 0x20, 0x100000007)
    n[0x2c:0x36] = 'House'.encode('utf-16le')
    struct.pack_into('<II', n, 0x3c, 5, 7); struct.pack_into('<Q', n, 0x48, 0x200000009)
    n[0x50] = 1
    fields = {0xc: struct.pack('<II', header, 1), 0x300: bytes(h), 0x400: bytes(n)}
    def observe(emu, target):
        read = lambda at: struct.unpack('<I', emu.mem_read(at, 4))[0]
        assert read(target + 0x10) == 1
        decoded_node = read(read(target + 0xc) + 4)
        assert read(decoded_node + 0x10) == 9
        assert struct.unpack('<Q', emu.mem_read(decoded_node + 0x20, 8))[0] == 0x100000007
        assert struct.unpack('<Q', emu.mem_read(decoded_node + 0x48, 8))[0] == 0x200000009
    payload, decoded = probe(0xf976c0, 0xf97c80, 0xf97d00, fields=fields, observer=observe)
    expected = b'\1' + struct.pack('>iQ', 9, 0x100000007) + b'\x0a' + 'House'.encode('utf-16le') + struct.pack('>Q', 0x200000009)
    assert payload == expected
    rows.append({'protocol': 'SRequestXiaoquMapInfo', 'type': '0xc0fdc', 'entries': 1,
                 'body_hex': payload.hex(), 'original_roundtrip': True})
    return rows


def main():
    sources, gotos = original_sources()
    result = {'image_sha256': hashlib.sha256(DATA).hexdigest(), **sources,
        'marker_cases': marker_cases(gotos), 'lifecycle_cases': lifecycle_cases(),
        'codec_cases': codec_cases(), 'visit_builder_cases': visit_builder_case(),
        'same_scene_notification_cases': same_scene_notification_case(),
        'adapters': ['NativePath CRT allocation/free, cookie, memset/memcpy',
            'Graphics marker/list boundary recorded, not rendered',
            'Map clear/goto refresh/map assignment boundaries recorded, not substituted as successful GUI lifecycle',
            'Network endpoint is an offline capture sink; nothing transmitted',
            'Codec probe string/CRT/interlocked host adapters; original scalar and bean wire instructions run'],
        'scope': 'Only native isolated consumers/codecs and fresh original resources; no production or GUI changes'}
    result['structural_cases_passed'] = sum(len(result[k]) for k in ('marker_cases', 'lifecycle_cases', 'codec_cases', 'visit_builder_cases', 'same_scene_notification_cases'))
    (OUT / 'world-special-portal-consumers-native.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    with (OUT / 'world-special-portal-consumers-disassembly.txt').open('w', encoding='utf-8') as f:
        with redirect_stdout(f):
            for at, n in ((0x11dec90, 0x479), (0x11e0449, 0x74), (0x11e1970, 0x23),
                    (0x11e0f80, 0x51), (0x11cf0b0, 0x67), (0x1230850, 0x2c7),
                    (0xa6bb9a, 0x160), (0x89d200, 11), (0xc993d1, 16),
                    (0x865430, 0x5c), (0x11e3140, 0x5e), (0x11e21f0, 0x480),
                    (0x87a5b7, 0x2b), (0x154e368, 0xd0), (0x17902f0, 0x101),
                    (0x12309b7, 0x43), (0xe3cc90, 0xc3), (0xf97a70, 0x279)):
                print(hex(at)); disasm(at, n)
    print(json.dumps({'structural_cases_passed': result['structural_cases_passed'],
        'house_portal_config_matches': len(result['house_portal_config_matches'])}))


if __name__ == '__main__':
    main()
