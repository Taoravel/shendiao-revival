"""Read-only original ordinary equipment additional-property research.

Executes the original complete detail parser with nonempty triples, its actual
native tree, two original UI consumption fragments and description selection.
No game process, socket, production database or player account is accessed.
"""
from pathlib import Path
import hashlib
import json
import struct

from native_inspect import BASE, DATA, u32
from research_equipment_detail_full import NativeEquipmentDetail, basic_payload
from research_npc_submenu import Machine
from pfs import PfsArchive
from bxml import decode

ROOT = Path(__file__).parent


def signed(value):
    return value if value < 0x80000000 else value - 0x100000000


def with_additional(triples, *, template=40100, prefix=1, score=0):
    # The baseline supplies two base pairs. Replace only the next BE32 count.
    payload = basic_payload(prefix=prefix, score=score)
    at = 41 + 4 + 2 * 8
    return (payload[:at] + struct.pack('>i', len(triples))
            + b''.join(struct.pack('>iii', *values) for values in triples)
            + payload[at + 4:])


class NativeAdditional(NativeEquipmentDetail):
    def additional(self):
        head = self.r(self.obj + 0x90)
        result = []

        def visit(node):
            if node == head:
                return
            visit(self.r(node))
            result.append((signed(self.r(node + 12)),
                           tuple(signed(self.r(node + offset)) for offset in (16, 20, 24)), node))
            visit(self.r(node + 8))

        visit(self.r(head + 4))
        assert len(result) == self.r(self.obj + 0x94)
        return result

    def native_ui_arguments(self, node):
        """Execute actual 1335e5b callsite, stop on the real formatter entry."""
        from unicorn import UC_HOOK_CODE
        from unicorn.x86_const import UC_X86_REG_ESI, UC_X86_REG_EBX
        captured = []

        def observe(uc, address, size, user):
            if address == 0x12fa810:
                sp = uc.reg_read(self.regs[0])
                captured.append(tuple(signed(self.r(sp + offset)) for offset in (8, 12, 16, 20)))
                uc.emu_stop()

        handle = self.emu.hook_add(UC_HOOK_CODE, observe)
        try:
            self.w(self.stack, self.stop)
            self.emu.reg_write(self.regs[0], self.stack)
            self.emu.reg_write(UC_X86_REG_ESI, node)
            self.emu.reg_write(UC_X86_REG_EBX, 0)
            self.emu.emu_start(0x1335e5b, self.stop, count=100)
        finally:
            self.emu.hook_del(handle)
        assert len(captured) == 1
        return captured[0]

    def native_refine_cap_branch(self, ordinal, cap):
        """Original map lookup + third-i32 comparison; no refinement action."""
        from unicorn import UC_HOOK_CODE
        from unicorn.x86_const import UC_X86_REG_EBP
        # The original prefix row +24 is maxrefinetime (XML store86af13).
        self.w(self.rows[0] + 0x24, cap)
        wrapper = 0x5010000
        self.w(wrapper, self.obj)
        branch = []

        def observe(uc, address, size, user):
            if address in (0x131b8da, 0x131b909):
                branch.append('at_cap' if address == 0x131b8da else 'below_cap')
                uc.emu_stop()

        handle = self.emu.hook_add(UC_HOOK_CODE, observe)
        try:
            self.w(self.stack, self.stop)
            self.w(self.stack + 0x14, ordinal)
            self.emu.reg_write(self.regs[0], self.stack)
            self.emu.reg_write(UC_X86_REG_EBP, wrapper)
            self.emu.emu_start(0x131b8ad, self.stop, count=1000)
        finally:
            self.emu.hook_del(handle)
        assert len(branch) == 1
        return branch[0]


def description_selection(attributes, modifier, value):
    """Execute original ID grouping and sign/flat/percent description branch.

    Lookup/UTF16 memory are adapters using exact CRC-checked PFS row values;
    original12fa810..12fa938 performs all selection, not host Python logic.
    Number formatting, role attribute math and rendered UI are not executed.
    """
    from unicorn import UC_HOOK_CODE
    m = Machine()
    manager, vt, lookup, row = 0x5010000, 0x5011000, 0x5012000, 0x5013000
    selected, lookups = [], []
    fields = {0x40: 'numbasevalue', 0x5c: 'numpositivedes', 0x78: 'numnegativedes',
              0x98: 'percentpositivedes', 0xb4: 'percentnegativedes'}
    group = (modifier // 10) * 10
    attr = attributes[group]
    m.w(manager, vt)
    m.w(vt + 8, lookup)
    m.w(row, group)
    m.w(row + 0x20, int(attr.get('numid', '0')))
    m.w(row + 0x94, int(attr.get('percentid', '0')))
    for offset, name in fields.items():
        m.string(row + offset, attr.get(name, ''), 0x5014000 + offset * 16)
    imports = {u32(a): name for a, name in ((0x22443f0, 'ctor'),
               (0x22444b4, 'copy'), (0x2244414, 'empty'))}
    for address in imports:
        if not any(start <= address <= end for start, end, _ in m.uc.mem_regions()):
            m.uc.mem_map(address & ~4095, 4096)

    def hook(uc, address, size, user):
        sp = uc.reg_read(m.spreg)
        if address == 0x12fa938:
            uc.emu_stop()
        elif address == 0x89d340:
            m.ret(manager)
        elif address == lookup:
            key = m.r(sp + 4)
            assert key == group
            lookups.append(key)
            m.ret(row, 4)
        elif imports.get(address) == 'ctor':
            m.string(uc.reg_read(m.cxreg), '', 0x5020000)
            m.ret(uc.reg_read(m.cxreg), 4)
        elif imports.get(address) == 'copy':
            src = m.r(sp + 4)
            selected.append({'field': fields[src - row], 'text': m.read_string(src)})
            m.ret(uc.reg_read(m.cxreg), 4)
        elif imports.get(address) == 'empty':
            selected.append({'field': None, 'text': ''})
            m.ret(uc.reg_read(m.cxreg), 4)

    m.uc.hook_add(UC_HOOK_CODE, hook)
    m.w(m.stack, m.stop, 0x5021000, modifier, value & 0xffffffff, 0, 0)
    m.run(0x12fa810, lambda *args: None)
    assert m.uc.reg_read(m.ipreg) == 0x12fa938 and lookups == [group] and len(selected) == 1
    return {'modifier': modifier, 'value': value, 'row_id': lookups[0], **selected[0]}


def main():
    archive = PfsArchive(ROOT.parent / 'artres/config.pfs')
    sources = {}
    catalogs = {}
    for name in ('cattributedesconfig', 'cequipprefixconfig', 'cequipscoreconfig',
                 'ceffecttype', 'cequipjichu', 'cequipeffect', 'citemattr'):
        entry = 'autoconfig/knight.gsp.item.' + name + '.xml'
        raw = archive.read(entry)
        tree = decode(raw)
        sources[entry] = {'bytes': len(raw), 'crc32': hex(archive.entries[entry].crc),
                          'sha256': hashlib.sha256(raw).hexdigest(), 'rows': len(tree)}
        catalogs[name] = {int(r.get('id')): dict(r.attrib) for r in tree}
    inputs = ('research_equipment_detail_full.py', 'research_npc_submenu.py', 'pfs.py',
              'bxml.py', 'native_inspect.py', 'research_equipment_random_identification.py')
    hashes = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in inputs}
    refine_cap = int(catalogs['cequipprefixconfig'][1]['maxrefinetime'])
    assert refine_cap == 3
    triples = ((11, 7, 0), (81, 9, refine_cap), (11, -3, 1))
    parser_cases = []
    for template in (40100, 42000, 43000, 44000, 45000, 46000):
        native = NativeAdditional(template)
        supplied = with_additional(triples, template=template)
        before = native.parse(supplied)
        rows = native.additional()
        assert [(k, v) for k, v, _ in rows] == list(enumerate(triples))
        for _, value, node in rows:
            assert native.native_ui_arguments(node) == (value[0], value[1], 0, 0)
        branches = [native.native_refine_cap_branch(i, refine_cap) for i in range(3)]
        assert branches == ['below_cap', 'at_cap', 'below_cap']
        after = native.parse(with_additional(((141, 19, 0),), template=template))
        assert [(k, v) for k, v, _ in native.additional()] == [(0, (141, 19, 0))]
        assert before['score'] == after['score'] == 0 and before['color'] == after['color'] == 1
        parser_cases.append({'template': template, 'decoded': [(k, v) for k, v, _ in rows],
                             'ui_calls': [(v[0], v[1], 0, 0) for _, v, _ in rows],
                             'prefix_maxrefinetime': refine_cap, 'refine_cap_branches': branches,
                             'replacement': [(0, (141, 19, 0))],
                             'supplied_score_preserved': 0, 'color': 1})
    native = NativeAdditional()
    four = ((11, 1, 0), (21, 2, 0), (31, 3, 0), (41, 4, 0))
    native.parse(with_additional(four))
    assert [(k, v) for k, v, _ in native.additional()] == list(enumerate(four))
    extremes = ((0, -2147483648, -1), (2147483647, 2147483647, 2147483647))
    native.parse(with_additional(extremes))
    assert [(k, v) for k, v, _ in native.additional()] == list(enumerate(extremes))
    malformed = with_additional(((11, 7, 0),))
    # Stop the payload inside the first triple; must not be confused with a
    # complete empty tail or claimed as a server eligibility validation.
    triple_start = 41 + 4 + 2 * 8 + 4
    try:
        NativeAdditional().parse(malformed[:triple_start + 11])
    except RuntimeError as exc:
        assert 'Original equipment parser rejected' in str(exc)
    else:
        raise AssertionError('Original parser accepted a truncated triple')
    selections = []
    for modifier, value in ((11, 7), (11, -7), (12, 7), (81, 9), (81, -9),
                            (82, 9), (141, 19), (142, 19), (811, 11), (812, 11)):
        result = description_selection(catalogs['cattributedesconfig'], modifier, value)
        expected = ('percentpositivedes' if modifier % 10 == 2 else
                    ('numnegativedes' if value < 0 else 'numpositivedes'))
        assert result['field'] == expected
        selections.append(result)
    for name, expected in hashes.items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected
    result = {'image_sha256': hashlib.sha256(DATA).hexdigest(), 'inputs_sha256': hashes,
              'sources': sources, 'six_slot_parser_cases': parser_cases,
              'four_triples_native_parser_acceptance_not_server_limit': four,
              'extreme_wire_values_accepted_not_business_authorized': extremes,
              'truncated_triple_rejected': True, 'description_selection_cases': selections,
              'parser_entry': '107cf80 constructor; complete107d960 through natural return107fd97',
              'additional_wire': 'BE32 signed count then sequential signed-i32 triples; no transmitted ordinal key',
              'native_storage': 'EquipObject+8c std::map<ordinal,three-i32>; ordinal from loop index, not modifier ID',
              'ui_consumer': '1335e5b sends first/second triple to12fa810; 131b8ad uses third vs prefix.maxrefinetime',
              'adapters': 'existing original parser runtime/config adapters; UTF16 and table lookup for description selection; no host property/score/role calculation',
              'not_verified': ['generation distributions', 'role final attribute arithmetic',
                               'score calculation from properties', 'UI rendering', 'live server behavior'],
              'production_changed': False, 'native_gui_verified': False}
    target = ROOT / 'evidence/equipment-random-identification-native.json'
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf8')
    print('PASS six nonempty original full parsers, 18 native UI calls, 18 native cap branches, '
          'six replacement parses, four triples, extremes, truncation rejection and ten description branches')


if __name__ == '__main__':
    main()
