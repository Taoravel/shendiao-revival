"""Bounded offline original ordinary map load and resource request evidence."""
import hashlib
import json
import struct
from pathlib import Path
from contextlib import redirect_stdout
from native_inspect import DATA, u32, disasm
from verify_world_intro_dispatch_native import IntroReplay
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ESP
from pfs import PfsArchive
from bxml import decode
from inspect_client import ROOT

OUT = Path(__file__).parent / 'evidence'


class ResourceReached(Exception):
    pass


class MapLoadReplay(IntroReplay):
    def __init__(self, row, sound, map_archive):
        self.requests, self.native_load_hits, self.file_checks = [], [], []
        self.map_archive = map_archive
        super().__init__(b'\xff\xfe', sound)
        self.w(self.scene + 0x110, int(row['id']))
        self.set_ws(self.scene + 0x168, row['resdir'])
        self.set_ws(0x540b220, '')
        self.w(0x540b008, 0x5440000)
        self.w(0x5440004, 0x5440100)
        self.w(0x544010c, 0x500f330)
        self.w(0x5440200, 0x5440300)
        self.w(0x5440304, 0x500f350)
        self.w(0x5441204, 0x500f340)
        self.w(0x540b104, 0x5f9770)  # actual World vtable load
        self.w(0x540b1cc, 0x500f320)
        self.w(0x29994fc, 0)  # exact preserved-image value; optional branch tested separately
        self.extra = {u32(0x2244518): 'concat_left', u32(0x22444e0): 'equal',
                      u32(0x2244254): 'thread_id'}
        for address in self.extra:
            page = address & ~4095
            if not any(a <= page <= b for a, b, _ in self.uc.mem_regions()):
                self.uc.mem_map(page, 4096)

    def hook(self, emu, address, size, user):
        sp = emu.reg_read(UC_X86_REG_ESP)
        if address in (0x11e0310, 0x5f9770, 0x5fcd50, 0x672ff0, 0x5f9b70):
            self.native_load_hits.append(hex(address))
        kind = self.extra.get(address)
        if kind == 'concat_left':
            dest, left, right = [self.r(sp + n) for n in (4, 8, 12)]
            self.set_ws(dest, self.wz(left) + self.ws(right)); self.ret(value=dest)
        elif kind == 'equal':
            self.ret(value=int(self.ws(self.r(sp + 4)) == self.ws(self.r(sp + 8))))
        elif kind == 'thread_id':
            self.ret(value=1)
        elif address in (0x11ca2f0, 0x5fca50, 0x5b6ec0, 0x5b6f80, 0x500f320):
            self.ret()  # scene clear, progress and logging boundaries
        elif address == 0x5f99b0:
            obj = self.r(sp + 4)
            self.w(obj, 0x5441200, 0x5440004)
            self.ret(8, obj)  # map parser object allocation boundary only
        elif address == 0x500f330:
            self.ret(value=0x5440200)
        elif address == 0x500f340:
            self.ret(4)
        elif address == 0x500f350:
            path = self.ws(self.r(sp + 4))
            assert path.startswith('/map/')
            member = path[len('/map/'):]
            loose = ROOT / 'artres/map' / member
            record = {'virtual_path': path, 'archive_member': member,
                'pfs_entry_exists': member in self.map_archive.entries,
                'loose_path': str(loose), 'loose_exists': loose.is_file()}
            self.requests.append(record)
            if record['pfs_entry_exists'] or record['loose_exists']:
                # Stop before returning success, not a synthetic parsed map.
                raise ResourceReached(path)
            self.ret(12, 0)
        elif address == 0x741f40:
            path = self.wz(self.r(sp + 4))
            exists = (ROOT / path).is_file()
            self.file_checks.append({'relative_path': path, 'exists': exists})
            self.ret(value=int(exists))  # cdecl physical-file existence boundary
        else:
            super().hook(emu, address, size, user)


def main():
    config = PfsArchive(ROOT / 'artres/config.pfs')
    map_archive = PfsArchive(ROOT / 'artres/map.pfs')
    source = 'autoconfig/knight.gsp.map.cmapconfig.xml'
    raw = config.read(source)
    ids = (1302, 1307, 1593, 1422)
    rows = {int(e.attrib['id']): dict(e.attrib) for e in decode(raw) if int(e.attrib['id']) in ids}
    sound = next(dict(e.attrib) for e in decode(config.read('autoconfig/knight.gsp.effectpath.ceffectpath.xml')) if e.attrib['id'] == '2004')
    cases = []
    for map_id in ids:
        replay = MapLoadReplay(rows[map_id], sound, map_archive)
        try:
            returned = replay.execute(0x11e0310, ecx=replay.scene, args=(120, 160)) & 255
            stop = 'original_scene_load_returned'
        except ResourceReached:
            returned = None
            stop = 'before_resource_provider_success_or_parse'
        assert replay.requests[0]['virtual_path'] == f"/map/{rows[map_id]['resdir']}/map.rmp"
        assert replay.native_load_hits[:5] == ['0x11e0310', '0x5f9770', '0x5fcd50', '0x672ff0', '0x5f9b70']
        assert (returned == 0) if map_id in (1302, 1307) else (returned is None)
        cases.append({'map_id': map_id, 'resdir': rows[map_id]['resdir'], 'stop': stop,
            'scene_load_return_AL': returned, 'requests': replay.requests,
            'native_load_hits': replay.native_load_hits,
            'world_66c_after': replay.r(0x540b66c) & 255})
    replay = MapLoadReplay(rows[1302], sound, map_archive)
    segmented_init = replay.execute(0x7418a0, ecx=0x5445000) & 255
    assert segmented_init == 0 and replay.r(0x29994fc) == 0
    assert replay.file_checks == [{'relative_path': 'cfg/dicFile.dfl', 'exists': False}]
    target_words = ('quanzhenjiaozhenwudian', 'taohuadaoxuanjitang')
    targeted_members = {word: [name for name in map_archive.entries if word in name.casefold()] for word in target_words}
    mount_path = ROOT / 'cfg/mount.xml'
    result = {'image_sha256': hashlib.sha256(DATA).hexdigest(),
        'source': {'path': source, 'sha256': hashlib.sha256(raw).hexdigest(), 'records': rows},
        'cases': cases, 'segmented_resource_manager': {'original_entry': '0x7418a0',
            'returned_AL': segmented_init, 'global_after': replay.r(0x29994fc),
            'original_dump_global': u32(0x29994fc), 'file_checks': replay.file_checks,
            'secondary_config_exists': (ROOT / 'cfg/segm.cfg').is_file(),
            'exact_installation_checks': [{'path': str(ROOT / prefix / name),
                'exists': (ROOT / prefix / name).is_file()}
                for prefix in ('cfg', 'bin/cfg') for name in ('dicFile.dfl', 'segm.cfg')]},
        'mount': {'path': str(mount_path), 'sha256': hashlib.sha256(mount_path.read_bytes()).hexdigest(),
            'text': mount_path.read_text(encoding='utf8')},
        'targeted_map_archive_members': targeted_members,
        'scope': 'Original Scene ordinary load through World and map resource path builder; exact installed-resource absence returns false. Known resources stop before provider success/parser. VFS mount provider and OS boundaries adapted; no renderer/client launch.'}
    (OUT / 'world-missing-map-load-native.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf8')
    with (OUT / 'world-missing-map-load-disassembly.txt').open('w', encoding='utf8') as out, redirect_stdout(out):
        for address, length in ((0x11e0310, 0x128), (0x11e07b7, 0x49), (0x5f9770, 0x1d),
            (0x5fcd50, 0x400), (0x5fd0c9, 0xb8), (0x672ff0, 0x1c1), (0x5f9b70, 0x87),
            (0x62b470, 0x1f), (0x742490, 0x88), (0x7418a0, 0x112), (0x7420d0, 0x1f5),
            (0x4021e0, 0x59), (0x403f30, 0x70), (0x62a535, 0xab),
            (0x62a865, 0x286), (0x62a0e0, 0x193)):
            print('\nFUNCTION', hex(address)); disasm(address, length)
    print(json.dumps({'map_cases': len(cases), 'segment_init': 1, 'passed': True}))


if __name__ == '__main__':
    main()
