"""Original G-link coordinate assignment and click navigation, offline only.

Host adapts XML/STL attribute lookup; original component field assignments,
click handler, registered callback and coordinate shifts remain executable.
"""
import hashlib
import json
from pathlib import Path
import struct
import sys
import xml.etree.ElementTree as ET

from bxml import decode
from inspect_client import ROOT
from native_inspect import BASE, DATA, u32
from pfs import PfsArchive
from verify_world_native_pathfinding import NativePath
from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_EDI,
    UC_X86_REG_ESI, UC_X86_REG_ESP, UC_X86_REG_EIP)
import capstone


OUT = Path(__file__).resolve().parent/'evidence'
IMAGE_HASH = '2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791'


def instructions(start, end):
    machine = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    return [dict(address=hex(i.address), mnemonic=i.mnemonic, operands=i.op_str,
                 bytes=i.bytes.hex()) for i in machine.disasm(DATA[start-BASE:end-BASE], start)]


class NavigationProbe(NativePath):
    component, attributes, manager = 0x5400000, 0x5401000, 0x5402000
    scene, actor, mouse_event = 0x5403000, 0x5404000, 0x5405000
    config_manager, config_vt, config_sink = 0x5406000, 0x5408000, 0x500f100
    iterator, found_node, sentinel = 0x5409000, 0x540a000, 0x540b000
    parser_end = 0x5167b9

    def __init__(self, attributes, configs, *, current_map=1007, control=False):
        self.attribute_values = dict(attributes)
        self.configs = configs
        self.control = control
        self.phase = 'setup'
        self.events, self.trace = [], []
        super().__init__(1, 1, b'\0')
        for slot in (0x224446c, 0x22443ec, 0x2244c9c):
            address = u32(slot)
            page = address & ~4095
            if not any(a <= page <= b for a, b, _ in self.uc.mem_regions()):
                self.uc.mem_map(page, 4096)
        self.w(self.component, 0x245a62c)
        self.w(0x29b77a4, self.manager)
        self.w(self.manager+0x154, 0x1571b50)
        self.w(0x2944564, self.scene)
        self.w(self.scene+0x110, current_map)
        self.w(0x294454c, self.actor)
        self.w(0x29455c0, 0)
        self.w(0x2945aec, self.config_manager)
        self.w(self.config_manager+0x8c8, self.config_vt)
        self.w(self.config_vt+8, self.config_sink)
        self.w(self.attributes+8, self.sentinel)
        self.end_at = None

    def key(self, pointer):
        length, capacity = self.r(pointer), self.r(pointer+4)
        assert length <= 32 and capacity == 32
        return bytes(self.uc.mem_read(pointer+20, length*2)).decode('utf-16-le')

    def hook(self, machine, address, size, user):
        sp = machine.reg_read(UC_X86_REG_ESP)
        self.trace.append(address)
        if address == self.end_at:
            machine.reg_write(UC_X86_REG_EIP, self.stop)
        elif address == 0x46d790:
            # STL attribute existence is an explicit adapter; original parser
            # comparison and conditional default selection still execute.
            result, key_pointer = self.r(sp+4), self.r(sp+8)
            name = self.key(key_pointer)
            owner = machine.reg_read(UC_X86_REG_EAX)
            self.w(result, owner, self.found_node if name in self.attribute_values else self.sentinel)
            self.ret(8, result)
        elif address == 0x519f90:
            # Only canonical decimal fixture values are used. Integer lexical
            # parsing and CEGUI/STL internals are not claimed as native proof.
            name = self.key(self.r(sp+4))
            value = int(self.attribute_values.get(name, self.r(sp+8)))
            self.events.append(dict(kind='adapted_attribute_integer', key=name, value=value))
            self.ret(8, value)
        elif address == 0x5211b0:
            self.ret(4)  # base UI mouse bookkeeping, not coordinate logic
        elif address == u32(0x2244c9c):
            key = self.r(sp+4)
            self.events.append(dict(kind='adapted_key_state', virtual_key=key))
            self.ret(4, 0x8000 if self.control and key == 0x11 else 0)
        elif address == self.config_sink:
            map_id = self.r(sp+4)
            row = self.configs[map_id]
            record = self.alloc(0x180)
            self.w(record, map_id)
            self.w(record+0xb0, int(row['xjPos']), int(row['yjPos']))
            self.events.append(dict(kind='adapted_original_config_lookup', map_id=map_id,
                xjPos=int(row['xjPos']), yjPos=int(row['yjPos'])))
            self.ret(4, record)
        elif address == u32(0x224446c):
            destination, source = machine.reg_read(UC_X86_REG_ECX), self.r(sp+4)
            machine.mem_write(destination, bytes(machine.mem_read(source, 28)))
            self.ret(4, destination)  # empty string copy only, scalar copy native
        elif address == u32(0x22443ec):
            self.ret()  # empty fixture string destructor
        elif address == 0x1142620:
            self.events.append(dict(kind='original_navigation_entry_boundary',
                entry=hex(address), owner=hex(machine.reg_read(UC_X86_REG_ECX)),
                arguments=[self.r(sp+offset) for offset in range(4, 32, 4)]))
            self.ret(28)
        elif address == 0x1567ad0:
            self.events.append(dict(kind='original_control_click_boundary',
                arguments=[self.r(sp+offset) for offset in (4, 8, 12)]))
            self.ret()
        elif address == 0x813860:
            raise AssertionError('Unexpected protocol-send path in ordinary navigation fixture')
        else:
            super().hook(machine, address, size, user)

    def parse(self):
        self.phase = 'bounded_original_G_attribute_assignment'
        self.end_at = self.parser_end
        self.w(self.stack+0x14, self.attributes)
        self.uc.reg_write(UC_X86_REG_ESI, self.attributes+4)
        self.uc.reg_write(UC_X86_REG_EDI, self.component)
        self.execute(0x5165cb)
        self.end_at = None
        return {key: self.r(self.component+offset) for key, offset in
                (('m', 0xfc), ('x', 0x100), ('y', 0x104),
                 ('npcid', 0x108), ('j', 0x10c), ('mapkey', 0x110))}

    def click(self, button=0):
        self.phase = 'original_G_click_and_registered_callback'
        self.w(self.mouse_event+0x1c, button)
        self.execute(0x5665a0, ecx=self.component, args=(self.mouse_event,))
        return self.uc.reg_read(UC_X86_REG_EAX) & 255


def main():
    assert hashlib.sha256(DATA).hexdigest() == IMAGE_HASH
    config = PfsArchive(ROOT/'artres/config.pfs')
    map_entry = 'autoconfig/knight.gsp.map.cmapconfig.xml'
    quest_entry = 'autoconfig/knight.gsp.specialquest.cspecialquestconfig.xml'
    map_raw, quest_raw = config.read(map_entry), config.read(quest_entry)
    maps = {int(item.attrib['id']): dict(item.attrib) for item in decode(map_raw)}
    quests = {int(item.attrib['id']): dict(item.attrib) for item in decode(quest_raw)}
    original_template = quests[801004]['aim']
    node = next(item for item in ET.fromstring('<root>'+original_template+'</root>')
                if item.tag == 'G' and item.attrib.get('m') == '$mapid$')
    assert node.attrib['x'] == '$xjPos$' and node.attrib['y'] == '$yjPos$'
    fixtures = [
        ('original_task_map_link_1007', dict(m='1007', x=maps[1007]['xjPos'], y=maps[1007]['yjPos']), False, 0),
        ('original_task_map_link_1103', dict(m='1103', x=maps[1103]['xjPos'], y=maps[1103]['yjPos']), False, 0),
        ('explicit_unit_control', dict(m='1103', x='1', y='2'), False, 0),
        ('map_only_default_1007', dict(m='1007'), False, 0),
        ('map_only_default_1304', dict(m='1304'), False, 0),
        ('nonzero_mouse_event_control', dict(m='1007', x='211', y='170'), False, 1),
        ('control_key_branch', dict(m='1007', x='211', y='170'), True, 0),
    ]
    cases = []
    for name, attrs, control, button in fixtures:
        probe = NavigationProbe(attrs, maps, control=control)
        parsed = probe.parse()
        assert parsed == {key: int(attrs.get(key, 0)) for key in parsed}
        assert 0x516785 in probe.trace and 0x516799 in probe.trace
        result = probe.click(button)
        navigation = [e for e in probe.events if e['kind']=='original_navigation_entry_boundary']
        control_calls = [e for e in probe.events if e['kind']=='original_control_click_boundary']
        if button:
            assert result == 0 and not navigation and not control_calls
        elif control:
            assert result == 1 and not navigation
            assert [e['arguments'] for e in control_calls] == [[1007, 211, 170]]
        else:
            map_id = int(attrs['m'])
            x, y = (int(attrs.get(k, maps[map_id][field])) for k, field in
                    (('x', 'xjPos'), ('y', 'yjPos')))
            assert result == 1 and len(navigation)==1 and not control_calls
            assert navigation[0]['arguments'] == [x*16, y*16, map_id, 0, 0, 0, 1]
            assert navigation[0]['owner'] == hex(probe.actor+0x378)
            assert 0x1571b50 in probe.trace and 0x5665a0 in probe.trace
        cases.append(dict(name=name, fixture_attributes=attrs, current_scene_map=1007,
            control_key=control, event_field_1c=button, original_assigned_component=parsed,
            click_return=result, events=probe.events, original_trace=sorted(set(hex(a) for a in probe.trace))))
    chunks = {}
    for name, start, end in (
        ('field_substitution_builder', 0x160102c, 0x1601160),
        ('G_dispatch', 0x514a31, 0x514a65),
        ('G_numeric_attribute_assignment', 0x5165cb, 0x5167b9),
        ('G_click', 0x5665a0, 0x56662e),
        ('callback_registration', 0x1572d67, 0x1572d76),
        ('callback_argument_capture_and_special_map_guard', 0x1571b8b, 0x1571bda),
        ('callback_nonzero_mapkey_branch_static_only', 0x1571efa, 0x1571fee),
        ('callback_default_and_explicit', 0x1572699, 0x157281e),
        ('navigation_gate', 0x1142620, 0x1142681),
    ):
        chunks[name] = dict(start=hex(start), end_exclusive=hex(end),
            bytes_sha256=hashlib.sha256(DATA[start-BASE:end-BASE]).hexdigest(),
            instructions=instructions(start, end))
    result = dict(all_passed=True, image_sha256=IMAGE_HASH, cases=cases,
        original_sources=[dict(entry=entry, crc_checked=True, sha256=hashlib.sha256(raw).hexdigest())
                          for entry, raw in ((map_entry,map_raw),(quest_entry,quest_raw))],
        original_quest_801004=quests[801004], template_selected_G_attributes=dict(node.attrib),
        original_instruction_chunks=chunks,
        adapters=['Host reads and substitutes one original template G attribute set; full native quest formatter/XML parse not executed.',
            'Bounded original G parser executes attribute existence/default branches and component assignments; CEGUI/STL lookup/integer lexical parsing adapted.',
            'Base mouse bookkeeping, OS modifier state, empty string copies/destructors and exact original config-table lookup are controlled fixtures.',
            'Original G mouse handler and its registered callback run; normal navigation stops at original 1142620 entry with exact arguments.',
            'Path selection, server transport, movement outcome, GPU and original server landing are not executed.'],
        original_callback_executed=True, full_native_XML_parser_executed=False,
        original_navigation_entry_executed=False, native_scene_spawn_proven=False,
        executed_link_context=dict(npcid=0, j=0, mapkey=0, instance_identity_proven=False),
        dependency_sha256={name: hashlib.sha256(Path(sys.modules[name].__file__).read_bytes()).hexdigest()
            for name in ('pfs', 'bxml', 'native_inspect', 'verify_world_native_pathfinding')},
        portal_landing_policy_applied=False, live_server_changed=False, gui_verified=False,
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (OUT/'world-map-navigation-fields-research.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps(dict(all_passed=True, cases=len(cases), original_G_callback=True,
        coordinate_scale=16, scene_spawn_authority=False)), flush=True)


if __name__ == '__main__':
    main()
