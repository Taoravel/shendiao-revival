"""Exclusive offline movie Setmap/Return identity and position contract replay.

Original Scene methods run; engine loading and unrelated Scene services are
explicit adapters. This does not render maps or mutate a running client.
"""
import hashlib
import json
import struct
from contextlib import redirect_stdout
from pathlib import Path
from native_inspect import DATA, u32, disasm
from unicorn import UC_HOOK_MEM_WRITE
from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_ESP
from verify_world_intro_dispatch_native import IntroReplay
from inspect_client import ROOT
from pfs import PfsArchive
from bxml import decode

OUT = Path(__file__).parent / 'evidence'


class ReturnReplay(IntroReplay):
    player, actor, actor_vt = 0x5420000, 0x5421000, 0x5422000

    def __init__(self, maps, sound, origin, position):
        self.return_trace = []
        self.config_writes = []
        self.maps = maps
        self.position = position
        self.engine_map = maps[origin]['resdir']
        self.engine_position = position
        super().__init__(b'\xff\xfe', sound)
        self.w(0x294454c, self.player)
        self.w(self.player, 0x2299344)  # actual CMainCharacter vtable
        self.w(self.player + 0x48, self.actor)
        self.w(self.actor, self.actor_vt)
        self.w(self.actor_vt + 0x38, 0x500f210)
        self.w(self.evt + 0x134, 0x500f220)
        self.w(self.evt + 0x34, 0x500f230)
        self.w(self.evt + 0x38, 0x500f240)
        self.w(0x540b104, 0x500f250)
        self.w(0x5423000, 0x5423100)
        self.w(0x5423108, 0x500f260)
        self.bean_addresses = {}
        for index, (map_id, row) in enumerate(maps.items()):
            bean = 0x5424000 + index * 0x200
            self.bean_addresses[map_id] = bean
            self.w(bean, map_id)
            for offset in (4, 0x20, 0x3c, 0x58, 0x74, 0xc8, 0xe4, 0x100, 0x128, 0x144):
                self.set_ws(bean + offset, row['resdir'] if offset == 0x58 else '')
        # Original bean copy establishes id/resdir at Scene+110/+168. This
        # validates the embedded layout without pretending to replay login.
        self.execute(0xc34710, ecx=self.scene + 0x110, args=(self.bean_addresses[origin],))
        self.execute(0x12c3f70, ecx=self.manager)
        self.w(self.manager + 0x40, origin)
        self.uc.hook_add(UC_HOOK_MEM_WRITE, self.observe_write)

    def observe_write(self, emu, access, address, size, value, user):
        if self.scene + 0x110 <= address < self.scene + 0x184:
            self.config_writes.append({'address': hex(address), 'size': size, 'value': value})

    def hook(self, emu, address, size, user):
        sp = emu.reg_read(UC_X86_REG_ESP)
        if address in (0x11e0c70, 0x11e0a80):
            argc = 4 if address == 0x11e0c70 else 1
            self.return_trace.append({'native_entry': hex(address),
                'args': [self.r(sp + 4 + 4 * i) for i in range(argc)]})
            return  # execute original Scene body, overriding parent adapter
        if address == 0x89dd50:
            self.ret(value=0x5423000)
        elif address == 0x500f260:
            map_id = self.r(sp + 4)
            self.return_trace.append({'map_config_lookup': map_id})
            self.ret(4, self.bean_addresses[map_id])
        elif address == 0x837060:
            self.set_ws(self.r(sp + 4), 'fixture_movie_camera')
            self.ret(value=self.r(sp + 4))
        elif address == 0x11d6050:
            # Optional temporary camera actor is not created by the engine
            # creation adapter. Preserve original null actor branch.
            self.ret(8, 0)
        elif address == 0x500f210:
            self.w(self.r(sp + 4), *self.position)
            self.return_trace.append({'engine_main_character_position': list(self.position)})
            self.ret(4, self.r(sp + 4))
        elif address == 0x500f220:
            self.ret(value=0)  # transition screenshot texture
        elif address == 0x500f230:
            event, delay = self.r(sp + 4), self.r(sp + 8)
            self.return_trace.append({'engine_schedule': {'event_code': self.r(event + 4), 'delay': delay}})
            self.ret(8)
        elif address == 0x500f240:
            self.ret(4)
        elif address == 0x500f250:
            directory, maze, pos, flag = [self.r(sp + n) for n in (4, 8, 12, 16)]
            self.engine_map = self.ws(directory)
            self.engine_position = (self.r(pos + 4), self.r(pos + 8))
            self.return_trace.append({'engine_world_load': {'directory': self.engine_map,
                'maze_path': self.ws(maze), 'position': list(self.engine_position), 'flag': flag}})
            self.ret(16, 1)
        elif address == 0x11d16f0:
            self.return_trace.append({'scene_remove_actor_kind': self.r(sp + 4)})
            self.ret(4)
        elif address in (0x11df320, 0x11dec90):
            self.return_trace.append({'external_scene_service': hex(address)})
            self.ret(4 if address == 0x11df320 else 0)
        else:
            super().hook(emu, address, size, user)

    def state(self):
        return {'scene_id': self.r(self.scene + 0x110),
            'scene_resdir': self.ws(self.scene + 0x168),
            'manager_40': self.r(self.manager + 0x40),
            'engine_map': self.engine_map, 'engine_position': list(self.engine_position)}


def run_case(name, maps, sound, *, origin=1100, movies=(1009,), mutation=None, position=(1800, 1200)):
    replay = ReturnReplay(maps, sound, origin, position)
    before = replay.state()
    for movie in movies:
        replay.execute(0x12bc780, ecx=replay.manager, args=(movie, 240, 2192))
    after_setmap = replay.state()
    assert after_setmap['scene_id'] == origin and after_setmap['scene_resdir'] == maps[origin]['resdir']
    assert replay.config_writes == []
    if mutation == 'scene_id_only':
        replay.w(replay.scene + 0x110, movies[-1])
    elif mutation == 'scene_path_only':
        replay.set_ws(replay.scene + 0x168, maps[movies[-1]]['resdir'])
    elif mutation == 'manager_40_only':
        replay.w(replay.manager + 0x40, origin)
    elif mutation == 'position_only':
        replay.position = (1920, 1280)
    replay.config_writes.clear()
    pre_return = replay.state()
    replay.execute(0x12c0bf0, ecx=replay.manager)
    after_return = replay.state()
    assert replay.config_writes == []
    loads = [event['engine_world_load'] for event in replay.return_trace if 'engine_world_load' in event]
    same_map = origin == movies[-1]
    should_reload_home = not same_map and mutation not in ('scene_id_only', 'manager_40_only', 'scene_path_only')
    expected = maps[origin]['resdir'] if should_reload_home or same_map else maps[movies[-1]]['resdir']
    assert after_return['engine_map'] == expected, (name, after_return)
    if should_reload_home:
        assert loads[-1]['position'] == list(replay.position)
    return {'name': name, 'origin': origin, 'movies': list(movies), 'mutation': mutation,
        'before': before, 'after_setmap': after_setmap, 'pre_return': pre_return,
        'after_return': after_return, 'trace': replay.return_trace}


def main():
    archive = PfsArchive(ROOT / 'artres/config.pfs')
    map_path = 'autoconfig/knight.gsp.map.cmapconfig.xml'
    raw = archive.read(map_path)
    maps = {int(e.attrib['id']): dict(e.attrib) for e in decode(raw) if e.attrib['id'] in ('1100', '1009', '1007')}
    sound = next(dict(e.attrib) for e in decode(archive.read('autoconfig/knight.gsp.effectpath.ceffectpath.xml')) if e.attrib['id'] == '2004')
    cases = [run_case('home_1100_movie_1009_return', maps, sound),
        run_case('home_1007_movie_1009_return', maps, sound, origin=1007),
        run_case('movie_chain_1009_1007_return', maps, sound, movies=(1009, 1007)),
        run_case('same_map_movie_no_reload', maps, sound, movies=(1100,)),
        *[run_case('counterfactual_' + mutation, maps, sound, mutation=mutation)
          for mutation in ('scene_id_only', 'scene_path_only', 'manager_40_only', 'position_only')]]
    result = {'image_sha256': hashlib.sha256(DATA).hexdigest(),
        'map_source': {'path': map_path, 'sha256': hashlib.sha256(raw).hexdigest(),
            'records': maps}, 'cases': cases,
        'scope': 'Original manager Setmap/Return wrappers, entire original Scene Setmap/Return and original MainCharacter position getter; engine/config/auxiliary scene service adapters. No rendering or scene entry replay.'}
    (OUT / 'world-intro-return-native.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf8')
    with (OUT / 'world-intro-return-disassembly.txt').open('w', encoding='utf8') as stream, redirect_stdout(stream):
        for address, length in ((0x12bc780, 0x28), (0x12c0bf0, 0x2e),
            (0x11e0c70, 0x308), (0x11e0a80, 0x1ee), (0x12060d0, 0xb0),
            (0x11f6450, 0x2e), (0x879f4e, 0x34), (0xc34710, 0x244)):
            print('\nFUNCTION', hex(address)); disasm(address, length)
    print(json.dumps({'cases': len(cases), 'passed': True}))


if __name__ == '__main__':
    main()
