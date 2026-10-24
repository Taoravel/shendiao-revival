"""Original repair-menu references and bounded native item-list predicates.

No server allocation, live save, running client, service or asset mutation.
"""
from collections import Counter, defaultdict
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import struct

from bxml import decode
from native_inspect import BASE, DATA, disasm
from pfs import PfsArchive
from research_npc_submenu import Machine

ROOT = Path(__file__).resolve().parent
HISTORY = (
    'research_npc_special_repairs.py', 'evidence/NPC_SPECIAL_REPAIRS_NATIVE_RESEARCH.md',
    'evidence/npc-special-repairs-native.json', 'evidence/npc-special-repairs-native-disassembly.txt',
    'research_npc_special_repair_cost.py', 'evidence/NPC_SPECIAL_REPAIR_COST_RESEARCH.md',
    'evidence/npc-special-repair-cost-native.json', 'evidence/npc-special-repair-cost-native-disassembly.txt')
WATCHED = HISTORY + ('npc_services.py', 'npc_gameplay.py', 'npc_repairs.py', 'world_npcs.py',
    'npc_lifecycle.py', 'inventory.py', 'equipment_condition.py',
    'evidence/npc-equipment-identification-ready.json', 'evidence/npc-placement-direction-ready.json')
WATCHED = tuple(dict.fromkeys(WATCHED + (Path(__file__).name,) + tuple(p.name for p in ROOT.glob('npc_*.py'))))
BLOCKS = ((0x10dce00, 0xbb), (0x109c914, 0x49), (0x109cb04, 0x49),
    (0x10745a0, 0x40), (0x89daa0, 0xb), (0x1639cec, 0x20), (0x1638029, 0x30),
    (0x10de1e0, 0x45), (0x10dd7e0, 0x20), (0x1635f10, 0xe0),
    (0x10ddc78, 0x13), (0x10dddf8, 0x13), (0x10dda40, 0xba))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def projection(root):
    return [{'attributes': dict(row.attrib),
             'lists': {child.tag: [entry.text for entry in child] for child in row}}
            for row in root]


def child_tree(node):
    return normalized_tree(dict(tag=node.tag, attributes=dict(node.attrib), text=node.text,
        tail=node.tail, children=[child_tree(child) for child in node]))


def normalized_tree(node):
    node = dict(node)
    node['children'] = [normalized_tree(child) for child in node['children']]
    if node['children'] and (node['text'] is None or not node['text'].strip()):
        node['text'] = None
    if node['tail'] is None or not node['tail'].strip():
        node['tail'] = None
    return node


def list_predicate(attr, family, flag, lookup_present, null_item=False):
    """Run actual list predicate and10745a0, adapting only config lookup.

    Wrapper id/type are copied by original1080720/1072890 prefix. This is not
    full wrapper construction, a legal saved instance or an identified table.
    """
    from unicorn.x86_const import UC_X86_REG_EBX, UC_X86_REG_EBP
    m = Machine()
    wrapper, bean, manager, vt, lookup, row, node, config = (
        0x5003000 + i * 0x1000 for i in range(8))
    template, kind = int(attr['id']), int(attr['itemtypeid'])
    m.ui = wrapper
    # First copy exactly the real source id/type integers, before wstring copy.
    m.w(config, template, kind)
    m.w(manager, vt); m.w(vt + 8, lookup)
    m.w(m.stack, m.stop, template)
    phase = ['copy']; lookups = []; result = []
    select, reject = ((0x109c954, 0x109c959) if family == 3 else (0x109cb44, 0x109cb49))
    def hook(uc, address, size, user):
        sp = uc.reg_read(m.spreg)
        if phase[0] == 'copy':
            if address == 0x89d730:
                m.ret(manager)
            elif address == lookup:
                assert m.r(sp + 4) == template
                m.ret(config, 4)
            elif address == 0x10728a5:
                assert (m.r(wrapper + 4), m.r(wrapper + 8)) == (template, kind)
                uc.emu_stop()
        else:
            if address == lookup:
                lookups.append(m.r(sp + 4))
                assert lookups[-1] == template
                m.ret(row, 4)
            elif address in (select, reject):
                result.append(address == select)
                uc.emu_stop()
    m.run(0x1080720, hook)
    phase[0] = 'predicate'
    # Actual89daa0 getter obtains manager+770, whose dependent table lookup is
    # controlled as missing(-1) or present(template); no predicate is replaced.
    m.w(0x2945aec, manager); m.w(manager + 0x770, vt)
    m.w(row, template if lookup_present else 0xffffffff)
    m.w(wrapper, bean); m.w(bean + 0xc, template)
    m.w(node + 0x10, 0 if null_item else wrapper)
    m.w(m.stack + 0x3c, flag)
    m.uc.reg_write(UC_X86_REG_EBX, node)
    m.uc.reg_write(UC_X86_REG_EBP, 0x5020000)
    m.w(m.stack, m.stop)
    m.run(0x109c914 if family == 3 else 0x109cb04, lambda *args: None)
    ordinary = (kind & 15) == 8 and (kind & 0xf0) <= 0x50
    extra = (kind & 15) == 8 and (kind & 0xf0) <= 0xa0 and not lookup_present
    expected = not null_item and (ordinary or bool(flag) and extra)
    assert result == [expected], (attr, family, flag, lookup_present, result)
    expected_lookup = not null_item and not ordinary and bool(flag) and (kind & 15) == 8 and (kind & 0xf0) <= 0xa0
    assert lookups == ([template] if expected_lookup else [])
    return dict(template=template, name=attr.get('name'), itemtypeid=kind,
        family=family, include_extra_flag=flag, lookup_present=lookup_present,
        null_item=null_item, selected=expected, actual_lookup_keys=lookups,
        native_predicate_replaced=False, full_wrapper_or_legal_instance_verified=False)


def open_equivalence(service):
    """Compare855 and513 original branches to the common UI-opening call."""
    from unicorn.x86_const import UC_X86_REG_ESI, UC_X86_REG_EBP
    m = Machine(); key = 0x1234567800000357; events = []
    m.w(m.ui + 0xd0, key & 0xffffffff, key >> 32)
    m.w(m.stack, m.stop)
    m.uc.reg_write(UC_X86_REG_ESI, m.ui); m.uc.reg_write(UC_X86_REG_EBP, 0)
    def hook(uc, address, size, user):
        if address == 0x16299a0:
            sp = uc.reg_read(m.spreg)
            events.append([m.r(sp + 4), m.r(sp + 8), m.r(sp + 12)])
            uc.emu_stop()
    m.run({855: 0x1639cec, 513: 0x1638029}[service], hook)
    assert events == [[2, key & 0xffffffff, key >> 32]]
    return dict(service=service, opening_call='0x16299a0', args=events[0],
        original_branch_executed=True, gui_constructed=False)


def selected_column(column):
    """Original click tail assigns wire column, original confirmation sends it.

    Start after item/label setup: this does not prove complete click eligibility.
    """
    from unicorn.x86_const import UC_X86_REG_ESI
    from verify_social_native import native_payload
    m = Machine(); anchor = m.ui; key = 0x1234567800000357
    window, item, bean, net, vt, send = (0x5003000 + i * 0x1000 for i in range(6))
    m.w(anchor + 0x34, window); m.w(window + 0x278, item)
    m.w(item, bean); m.w(bean + 0x14, 91)
    m.w(anchor + 0x1b8, key & 0xffffffff, key >> 32, 2)
    m.w(net, vt); m.w(vt + 0x3c, send)
    stage = ['tail']; sent = []
    m.uc.reg_write(UC_X86_REG_ESI, anchor); m.w(m.stack, m.stop)
    def hook(uc, address, size, user):
        if stage[0] == 'tail':
            if address == 0x10dd800: m.ret()
            elif address == (0x10ddc89 if column == 1 else 0x10dde09):
                assert m.r(anchor + 0x1c4) == column
                uc.emu_stop()
        else:
            if address == 0x813860: m.ret(net)
            elif address == send:
                packet = m.r(uc.reg_read(m.spreg) + 4)
                assert m.r(packet + 4) == 0xc0413
                fields = [m.r(packet + 8), m.r(packet + 0x10) | m.r(packet + 0x14) << 32,
                          m.r(packet + 0x18), m.r(packet + 0x1c)]
                sent.append(fields); m.ret(1, 4)
            elif address == 0x10ddae1: uc.emu_stop()
    m.run(0x10ddc78 if column == 1 else 0x10dddf8, hook)
    stage[0] = 'confirm'; m.ui = anchor + 0x20; m.w(m.stack, m.stop, 0)
    m.run(0x10dda40, lambda *args: None)
    assert sent == [[2, key, column, 91]]
    wire = native_payload(0xe4cf30, scalars=[(8, 2), (0x18, column), (0x1c, 91)],
        raw=[(0x10, struct.pack('<q', key))])
    assert wire == struct.pack('>iqii', *sent[0])
    return dict(column=column, original_tail_assignment=True, original_confirmation_fields=sent[0],
        wire=wire.hex(), item_and_UI_selection_fixture=True, redraw_skipped=True,
        full_click_eligibility_verified=False)


def main():
    watched = {name: sha(ROOT / name) for name in WATCHED}
    assert watched['evidence/npc-equipment-identification-ready.json'] == '9b05ab14fd786558a2e320a70ae5a9579b578b3c4170ecb241fac8e2bab98794'
    assert watched['evidence/npc-placement-direction-ready.json'] == '761c97193b18d92e860aa8cbfeac045a34d9c10057c792d586b0484c7df62d82'
    pfs = PfsArchive(ROOT.parent / 'artres/config.pfs')
    sources = {}; npc_table_scan = {}; tables = {}
    names = sorted(name for name in pfs.entries if name.startswith('autoconfig/knight.gsp.npc.') and name.endswith('.xml'))
    names.append('autoconfig/knight.gsp.item.citemattr.xml')
    for name in names:
        raw = pfs.read(name); entry = pfs.entries[name]; root = decode(raw)
        original = projection(root)
        cache_path = ROOT / 'catalogs' / (Path(name).stem + '.json')
        cached = json.loads(cache_path.read_text(encoding='utf8'))
        assert original == [{'attributes': row['attributes'], 'lists': row.get('lists', {})} for row in cached], name
        assert [[child_tree(child) for child in row] for row in root] == [[normalized_tree(child) for child in row['children']] for row in cached], name
        sources[name] = dict(length=len(raw), crc32=hex(entry.crc), sha256=hashlib.sha256(raw).hexdigest(),
            records=len(root), complete_attributes_and_lists_match_cache=True,
            complete_nested_children_match_cache_except_formatting_whitespace=True, cache_sha256=sha(cache_path))
        tables[Path(name).stem] = original
        if '.npc.' in name:
            fields = Counter(k for row in original for k in row['attributes'])
            children = Counter(k for row in original for k in row['lists'])
            npc_table_scan[name] = dict(attribute_fields=dict(fields), list_fields=dict(children),
                service_named_fields=sorted(k for k in set(fields) | set(children) if 'serv' in k.lower()))
    npc = tables['knight.gsp.npc.cnpcconfig']; services = tables['knight.gsp.npc.cnpcserverconfig']
    attrs = tables['knight.gsp.item.citemattr']
    children = {int(row['attributes']['id']): tuple(map(int, row['lists'].get('childservice', ()))) for row in services}
    parents = defaultdict(list)
    for parent, ids in children.items():
        for child in ids:
            parents[child].append(parent)
    def paths(target, trail=()):
        assert target not in trail and len(trail) < 32
        if not parents[target]: return [(target,) + trail]
        return [path for parent in parents[target] for path in paths(parent, (target,) + trail)]
    service_paths = {str(target): paths(target) for target in (93, 160, 855, 513)}
    assert service_paths == {'93': [(93,)], '160': [(160,)], '855': [(1774, 855)], '513': [(513,)]}, service_paths
    by_tag = {}
    for row in attrs:
        attr = row['attributes']; kind = int(attr['itemtypeid'])
        if (kind & 15) == 8:
            tag = (kind >> 4) & 15
            if tag not in by_tag or kind < int(by_tag[tag]['itemtypeid']):
                by_tag[tag] = attr
    assert all(tag in by_tag for tag in range(12))
    selected = [by_tag[tag] for tag in range(12)]
    selected.append(next(row['attributes'] for row in attrs if (int(row['attributes']['itemtypeid']) & 15) != 8))
    cases = [list_predicate(attr, family, flag, present) for attr in selected
        for family in (1, 3) for flag in (0, 1) for present in (False, True)]
    cases += [list_predicate(selected[0], family, flag, False, null_item=True)
        for family in (1, 3) for flag in (0, 1)]
    opened = [open_equivalence(service) for service in (855, 513)]
    columns = [selected_column(column) for column in (1, 3)]
    output = io.StringIO()
    with redirect_stdout(output):
        for address, length in BLOCKS:
            print('REGION', hex(address)); disasm(address, length)
    assert watched == {name: sha(ROOT / name) for name in WATCHED}, 'Other owner changed watched input; rerun coherent batch'
    result = dict(method='research: original CRC/BXML table audit and bounded original x86 predicates',
        native_image_sha256=hashlib.sha256(DATA).hexdigest(), sources=sources, npc_table_scan=npc_table_scan,
        npc_config_records=len(npc), service_records=len(services), service_tree_paths=service_paths,
        service_labels={row['attributes']['id']: row for row in services if int(row['attributes']['id']) in (93, 160, 855, 513, 1774)},
        npc_to_service_allocation_found=False, known_allocated_npcs=[], known_allocated_placements=[],
        allocation_scope='50 original npc configuration tables, with full attribute/list cache equality; no real historical server menus',
        allocation_unknown=True, server_menu_message='Original SVisitNpc carries per-key service vector; prior native channel evidence only, not replayed here',
        list_population_sources={'container_key3': '10dce00 calls109c810(vector,1)', 'container_key1': '10dce60 calls109ca00(vector,1)'},
        native_filter_cases=cases, native_opening_cases=opened, native_column_cases=columns,
        new_native_case_count=len(cases)+len(opened)+len(columns),
        config_lookup_adapter='ConfigManager+770 table identity/real row population unknown; sentinel -1 versus present fixture only',
        pending_fields=['Real NPC allocation and placement for93/160/855', 'ConfigManager+770 table identity and real entries',
            'Full wrapper/UI construction, condition/identification/affordability/qualification flow',
            'Special asset legal sources, payment currency/materials/probabilities and server settlement'],
        watched_sha256=watched, historical_cases_replayed=0, production_modified=False,
        service_or_gui_operated=False, live_database_accessed=False, shared_runtime_verified=False)
    (ROOT / 'evidence/npc-special-repair-menu-native.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    (ROOT / 'evidence/npc-special-repair-menu-disassembly.txt').write_text(output.getvalue(), encoding='utf8')
    print('PASS', len(cases)+len(opened)+len(columns), 'new native cases;', len(sources), 'original tables; no NPC allocation invented')


if __name__ == '__main__':
    main()
