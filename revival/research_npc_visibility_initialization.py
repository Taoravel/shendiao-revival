"""Offline original CNpc hide loading/copy and visibility branches; no live state."""
import argparse
from collections import Counter
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import struct

from native_inspect import BASE, DATA, disasm, u32
from research_npc_submenu import Machine
from unicorn.x86_const import UC_X86_REG_EBX, UC_X86_REG_ESI, UC_X86_REG_EDI

ROOT = Path(__file__).parent
SAMPLES = (10000, 10003, 10006, 10017, 10380, 10142, 10259, 10512, 10082, 10083)
BLOCKS = {
    'hide_loader': (0xbaeccb, 0x39),
    'ordinary_init_lookup_copy': (0x1201c36, 0x2c),
    'ordinary_config_copy': (0x11f3000, 0x122),
    'config_getter': (0x89df90, 11),
    'hide_nonzero_predicate': (0x11fc200, 12),
    'visibility_update_entry': (0x11fe390, 0x104),
    'visibility_other_branches': (0x11fe495, 0x125),
    'visibility_setter': (0x11f6ee0, 0x7b),
    'scene_refresh_caller': (0x11d366c, 0x2c),
    'instance_refresh_caller': (0x11d9ccd, 0x2f),
    'task_display_loader': (0xbb6921, 0x25),
    'task_display_vector_consumer': (0x1258f52, 0xd5),
    'task_refresh_caller': (0x125a981, 0x33),
    'disappear_compare': (0x11fcc78, 0x1f),
    'original_config_table_type': (0x87ecd0, 6),
}


def utf16_literal(address):
    raw = bytearray()
    for cursor in range(address-BASE, len(DATA), 2):
        pair = DATA[cursor:cursor+2]
        if pair == b'\0\0':
            return raw.decode('utf-16le')
        raw.extend(pair)
    raise ValueError('Unterminated original literal')


def map_import_boundaries(machine, *slots):
    """Map only external import entries so Unicorn can reach adapter hooks."""
    for slot in slots:
        address = u32(slot)
        if not any(first <= address <= last for first, last, _ in machine.uc.mem_regions()):
            machine.uc.mem_map(address & ~4095, 4096)
        machine.uc.mem_write(address, b'\xc3')


def initialized_hide(row):
    """Original field-name/read/store -> original getter/lookup/copy -> predicate.

    These are explicitly joined entry slices, not a whole constructor/model run.
    String/vector ownership operations and XML reader/table lookup are adapters.
    The numeric hide assignment and its copy at +108 execute original bytes.
    """
    m = Machine()
    map_import_boundaries(m, 0x22443f0, 0x22444b4)
    uc = m.uc
    bean, reader, manager, vt, lookup, info = (0x5020000, 0x5021000, 0x5022000,
                                              0x5023000, 0x5024000, 0x5025000)
    a = row['attributes']
    ident, hide = int(a['id']), int(a['hide'])
    m.w(bean, ident)
    m.w(bean+0x108, 0x7fffffff)  # sentinel; original loader must overwrite it
    m.w(m.ui+0x258, 0x7ffffffe)  # independently detect original copy
    m.w(info+8, ident)
    m.w(0x2945aec, manager)
    m.w(manager+0x9e8, vt)
    m.w(vt+8, lookup)
    events = []
    string_ctor, string_copy = u32(0x22443f0), u32(0x22444b4)
    phase = 'loader'

    def hook(emu, address, size, user):
        nonlocal phase
        sp = emu.reg_read(m.spreg)
        if address == string_ctor:
            literal = utf16_literal(m.r(sp+4))
            assert literal == 'hide'
            m.string(emu.reg_read(m.cxreg), literal, 0x5026000)
            events.append({'xml_field_name': literal})
            m.ret(emu.reg_read(m.cxreg), 4)
        elif address == 0x409ce0:
            assert emu.reg_read(m.cxreg) == reader
            assert m.read_string(m.r(sp+4)) == 'hide' and m.r(sp+8) == 0
            events.append({'xml_reader_adapter_result': hide})
            m.ret(hide, 8)
        elif address == 0xbaecfd:
            assert m.r(bean+0x108) == hide
            events.append({'original_loader_store': m.r(bean+0x108)})
            phase = 'lookup_copy'
            emu.reg_write(UC_X86_REG_ESI, m.ui)
            emu.reg_write(UC_X86_REG_EBX, info)
            emu.reg_write(m.spreg, m.stack)
            emu.reg_write(m.ipreg, 0x1201c44)
        elif address == lookup:
            assert emu.reg_read(m.cxreg) == manager+0x9e8
            assert m.r(sp+4) == ident
            events.append({'table_lookup_adapter_id': ident})
            m.ret(bean, 4)
        elif address == string_copy or address in (0x82c950, 0xf441c0):
            destination, source = emu.reg_read(m.cxreg), m.r(sp+4)
            length = 28 if address == string_copy else 16
            assert not source <= bean+0x108 < source+length
            assert not destination <= m.ui+0x258 < destination+length
            uc.mem_write(destination, bytes(uc.mem_read(source, length)))
            m.ret(destination, 4)
        elif address == 0x1201c62:
            assert m.r(m.ui+0x258) == hide
            events.append({'original_copy_to_npc_258': m.r(m.ui+0x258)})
            phase = 'predicate'
            m.w(m.stack, m.stop)
            emu.reg_write(m.spreg, m.stack)
            emu.reg_write(m.cxreg, m.ui)
            emu.reg_write(m.ipreg, 0x11fc200)
        elif address == m.stop:
            assert phase == 'predicate'
            emu.emu_stop()

    uc.reg_write(UC_X86_REG_ESI, reader)
    uc.reg_write(UC_X86_REG_EDI, bean)
    uc.reg_write(UC_X86_REG_EBX, 0)
    m.run(0xbaeccb, hook)
    assert uc.reg_read(m.ipreg) == m.stop
    predicate = uc.reg_read(m.axreg)
    assert predicate == int(hide != 0)
    return {'npc_id': ident, 'name': a.get('name'), 'hide': hide,
            'bean_108': m.r(bean+0x108), 'npc_258': m.r(m.ui+0x258),
            'native_nonzero_predicate': predicate, 'events': events,
            'whole_initialization_executed': False,
            'visibility_setter_called_in_this_slice': False}


def visibility_branch(hide, state, caller_flag, visible_before):
    """Original updater prologue/switch/comparisons + real CNpc vt30 setter.

    Stop before task-marker text building, after the visibility side effect.
    Both model vt54 calls are boundaries; their bytes are not simulated GPU work.
    """
    m = Machine()
    map_import_boundaries(m, 0x2244450)
    uc = m.uc
    model1, model2, modelvt, model_show = 0x5020000, 0x5021000, 0x5022000, 0x5023000
    m.w(m.ui, 0x22985e4)
    m.w(m.ui+0x258, hide)
    m.w(m.ui+0x44, model1, model2)
    m.w(model1, modelvt)
    m.w(model2, modelvt)
    m.w(modelvt+0x54, model_show)
    uc.mem_write(m.ui+0x18, bytes([visible_before]))
    m.w(0x2945620, 0)  # unrelated cinematic visibility override absent
    m.w(m.stack, m.stop, state, caller_flag)
    setters, models = [], []
    stops = (0x11fe5f3, 0x11fe4a9, 0x11fe4ee, 0x11fe533, 0x11fe578, 0x11fe5ba)

    def hook(emu, address, size, user):
        sp = emu.reg_read(m.spreg)
        if address == u32(0x2244450):
            uc.mem_write(emu.reg_read(m.cxreg), bytes(28))
            m.ret(emu.reg_read(m.cxreg))
        elif address == 0x11f6ee0:
            assert emu.reg_read(m.cxreg) == m.ui
            setters.append(m.r(sp+4))  # observer only; original setter executes
        elif address == model_show:
            models.append({'receiver': 'secondary' if emu.reg_read(m.cxreg) == model2 else 'primary',
                           'visible': m.r(sp+4)})
            m.ret(cleanup=4)
        elif address in stops:
            emu.emu_stop()

    m.run(0x11fe390, hook)
    assert uc.reg_read(m.ipreg) in stops
    # Independent expectations checked AFTER the original switch/setter ran.
    expected = ([0] if hide == 1 or hide > 1 and caller_flag == 1 else []) if state == 0 else (
        [1] if state <= 6 and hide >= 1 else [])
    assert setters == expected, (hide, state, initial_refresh, setters)
    assert m.r(m.ui+0x258) == hide, 'Visibility update must not rewrite hide mode'
    assert m.r(m.ui+0x144) == state
    visible_after = uc.mem_read(m.ui+0x18, 1)[0]
    assert visible_after == (expected[-1] if expected else visible_before)
    assert [e['visible'] for e in models] == expected*2
    return {'hide_fixture': hide, 'state_argument': state, 'caller_flag_argument': caller_flag,
            'visible_before_fixture': visible_before, 'original_setter_arguments': setters,
            'object_18_after': visible_after, 'npc_258_after': m.r(m.ui+0x258),
            'model_vt54_adapters': models, 'stopped_before_marker_at': hex(uc.reg_read(m.ipreg))}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--disasm', choices=tuple(BLOCKS))
    args = parser.parse_args()
    if args.disasm:
        disasm(*BLOCKS[args.disasm])
        return
    from pfs import PfsArchive
    from bxml import decode
    from inspect_client import catalog_rows
    archive = PfsArchive(ROOT.parent/'artres/config.pfs')
    sources = []
    tables = {}
    for stem in ('cnpcconfig', 'cscenenpcconfig', 'cmainmissioninfo'):
        namespace = 'task' if stem == 'cmainmissioninfo' else 'npc'
        name = f'autoconfig/knight.gsp.{namespace}.{stem}.xml'
        raw = archive.read(name)
        rows = catalog_rows(decode(raw))
        saved = json.loads((ROOT/f'catalogs/knight.gsp.{namespace}.{stem}.json').read_text(encoding='utf-8'))
        project = lambda rs: [(r['attributes'], r['lists']) for r in rs]
        assert project(rows) == project(saved)
        tables[stem] = rows
        sources.append({'pfs': 'artres/config.pfs', 'entry': name, 'rows': len(rows),
                        'crc32': archive.entries[name].crc, 'sha256': hashlib.sha256(raw).hexdigest(),
                        'all_attributes_lists_match_catalog': True})
    catalog = {int(r['attributes']['id']): r for r in tables['cnpcconfig']}
    distribution = dict(sorted(Counter(int(r['attributes']['hide']) for r in catalog.values()).items()))
    assert distribution == {0: 2819, 1: 1268, 2: 29, 4: 3, 5: 8}
    initialized = [initialized_hide(catalog[ident]) for ident in SAMPLES]
    branches = [visibility_branch(hide, state, refresh, visible)
                for hide in distribution for state in range(8)
                for refresh in (0, 1) for visible in (0, 1)]
    assert utf16_literal(0x225aca4) == 'knight.gsp.npc.CNPCConfig'
    assert utf16_literal(0x226bd28) == 'DisPlayNPCID'
    display_rows = [{'task_id': int(r['attributes']['id']), 'display_npc_ids': r['lists']['DisPlayNPCID']}
                    for r in tables['cmainmissioninfo'] if r['lists'].get('DisPlayNPCID')]
    result = {'image_sha256': hashlib.sha256(DATA).hexdigest(), 'base': hex(BASE),
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'sources': sources, 'definition_hide_distribution': distribution,
              'initialization_cases': initialized, 'visibility_cases': branches,
              'original_switch_targets': [hex(u32(0x11fe6d8+i*4)) for i in range(7)],
              'display_lists': display_rows,
              'instruction_sources': [{'name': name, 'address': hex(a), 'length': length,
                                       'sha256': hashlib.sha256(DATA[a-BASE:a-BASE+length]).hexdigest()}
                                      for name, (a, length) in BLOCKS.items()],
              'adapters': ['UTF16 field-name constructor', 'XML numeric getter supplies actual PFS hide',
                           'config table lookup supplies row identity', 'unrelated string/vector ownership copies',
                           'explicit joined entry slices for loader/init/predicate',
                           'absent unrelated cinematic override', 'task-marker string default constructor',
                           'model vt54 visibility boundary; no GPU/model implementation'],
              'passed': len(initialized)+len(branches),
              'scope': {'original_hide_assignment_and_copy_executed': True,
                        'whole_npc_initialization_executed': False, 'original_visibility_branches_executed': True,
                        'display_task_qualification_executed': False, 'activity_protocol_executed': False,
                        'server_lifecycle_verified': False, 'production_modified': False,
                        'gui_verified': False, 'network_or_db_used': False}}
    output = io.StringIO()
    with redirect_stdout(output):
        for name, (address, length) in BLOCKS.items():
            print(f'[{name}]')
            disasm(address, length)
    (ROOT/'evidence/npc-visibility-initialization-native.txt').write_text(output.getvalue(), encoding='utf-8')
    (ROOT/'evidence/npc-visibility-initialization-native.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'passed': result['passed'], 'initialization_cases': len(initialized),
                      'visibility_cases': len(branches), 'definition_hide_distribution': distribution,
                      'display_lists': len(display_rows), 'scope': result['scope']}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
