"""Original bag container identity through repair selection and native requests.

This bounded offline probe does not run CEGUI, a client, a server or a battle.
"""
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import struct
import xml.etree.ElementTree as ET

from bxml import decode
from native_gameplay_probe import probe
from native_inspect import BASE, DATA, disasm, u32
from pfs import PfsArchive
from research_npc_submenu import Machine
from verify_social_native import native_payload

ROOT = Path(__file__).resolve().parent
OLD = ('research_npc_special_repair_menu.py', 'evidence/NPC_SPECIAL_REPAIR_MENU_RESEARCH.md',
    'evidence/npc-special-repair-menu-native.json', 'evidence/npc-special-repair-menu-disassembly.txt',
    'research_npc_special_repairs.py', 'evidence/NPC_SPECIAL_REPAIRS_NATIVE_RESEARCH.md',
    'evidence/npc-special-repairs-native.json', 'evidence/npc-special-repairs-native-disassembly.txt',
    'research_npc_special_repair_cost.py', 'evidence/NPC_SPECIAL_REPAIR_COST_RESEARCH.md',
    'evidence/npc-special-repair-cost-native.json', 'evidence/npc-special-repair-cost-native-disassembly.txt')
WATCHED = OLD + ('npc_repairs.py', 'world_npcs.py', 'npc_lifecycle.py', 'inventory.py',
    'equipment_condition.py', 'evidence/npc-equipment-identification-ready.json',
    'evidence/npc-placement-direction-ready.json', 'native_gameplay_probe.py',
    'research_npc_submenu.py', 'verify_social_native.py', 'native_inspect.py', 'bxml.py', 'pfs.py')
WATCHED += (Path(__file__).name,)
BLOCKS = ((0x10a9054, 0x18), (0x10a4957, 0x27), (0x1081790, 0x66),
    (0x109c810, 0x1e7), (0x109ca00, 0x1e7), (0x10ddb30, 0x176), (0x10ddcb0, 0x176),
    (0x10dda40, 0xa4), (0x1636d38, 0x31), (0x10ecaf0, 0x81),
    (0x1108280, 0xa6), (0x110b9bf, 0x2d), (0x1103df3, 0x56), (0x10cf2d0, 0x9f),
    (0x10cf6d4, 0x17), (0x10d327b, 0x54), (0x10cf4d1, 0x18), (0x1098070, 0x6c))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bag_input(column, position, binding):
    """Complete original SGetBagInfo decoder, then actual process call boundary."""
    from unicorn import UC_HOOK_CODE
    from unicorn.x86_const import UC_X86_REG_ESI, UC_X86_REG_ESP, UC_X86_REG_EIP
    item = struct.pack('>iiiiQiQiQ', 49009, binding, 701, position, 0, 1, 0, 0, 0)
    wire = struct.pack('>iQi', column, 0x100000007, 40) + b'\x01' + item + b'\0'
    observed = {}

    def observe(emu, obj):
        def r(address): return struct.unpack('<I', emu.mem_read(address, 4))[0]
        begin, end = r(obj + 0x28), r(obj + 0x2c)
        assert end - begin == 64
        observed.update(column=r(obj + 8), bean=bytes(emu.mem_read(begin, 64)))
        stack = 0x5100000
        emu.mem_write(stack, struct.pack('<II', 0x500f000, 0))
        emu.mem_write(0x2944628, struct.pack('<I', 0x5300000))
        emu.reg_write(UC_X86_REG_ESI, obj)
        emu.reg_write(UC_X86_REG_ESP, stack)
        calls = []

        def boundary(uc, address, size, user):
            if address == 0x10a4840:
                sp = uc.reg_read(UC_X86_REG_ESP)
                calls.append((r(sp + 4), r(sp + 8)))
                uc.emu_stop()

        token = emu.hook_add(UC_HOOK_CODE, boundary)
        emu.emu_start(0x10a9054, 0x10a906c, count=1000)
        emu.hook_del(token)
        assert calls == [(column, obj + 0x10)]
        assert emu.reg_read(UC_X86_REG_EIP) == 0x10a4840
        observed['process_call_column'] = calls[0][0]

    probe(0xef6220, 0xef62d0, 0xef6350, payload=wire, observer=observe)
    assert observed['column'] == column
    assert struct.unpack_from('<IIII', observed['bean'], 4) == (49009, binding, 701, position)
    return observed, wire


def chain(source, family, attr):
    """Actual outer map lookup and item predicate, selected-item click and send.

    Map layout/one-item STL copy and CEGUI widgets are dependency fixtures.
    No map lookup, predicate, selected-item assignment, column assignment or
    final request fields are replaced.
    """
    from unicorn.x86_const import UC_X86_REG_ESI, UC_X86_REG_EBX, UC_X86_REG_EDI
    m = Machine()
    wrapper, obj, bean, manager, head, node, innerhead, innernode, vector, config, cfgmanager, vt, lookup, event, cell, window, net, netvt, send = (
        0x5010000 + i * 0x1000 for i in range(19))
    column = source['column']; item_key = struct.unpack_from('<I', source['bean'], 12)[0]
    template, kind = int(attr['id']), int(attr['itemtypeid'])
    stage = ['prefix']; selected = []; sent = []
    m.ui = wrapper; m.w(config, template, kind)
    m.w(cfgmanager, vt); m.w(vt + 8, lookup)
    m.w(m.stack, m.stop, template)

    def hook(uc, address, size, user):
        sp = uc.reg_read(m.spreg)
        if stage[0] == 'prefix':
            if address == 0x89d730: m.ret(cfgmanager)
            elif address == lookup: m.ret(config, 4)
            elif address == 0x10728a5: uc.emu_stop()
        elif stage[0] == 'properties' and address == 0x10817cc:
            uc.emu_stop()
        elif stage[0] == 'enumerate':
            if address == 0x108e150: m.ret(0, 20)  # Empty output-vector clear.
            elif address == 0x1091d30:
                target = uc.reg_read(m.cxreg); original = m.r(sp + 4)
                assert original == node + 0x10
                # Shallow one-item map-copy fixture, not a lookup/selection.
                m.w(target, 0, m.r(original + 4), 1)
                m.ret(target, 4)
            elif address == 0x10998a0:
                selected.append(m.r(m.r(sp + 4))); uc.emu_stop()
            elif address == (0x109c9ae if family == 3 else 0x109cb9e):
                uc.emu_stop()
        elif stage[0] == 'click':
            if address == lookup: m.ret(config, 4)
            elif address == 0x1088ca0: m.ret(0, 8)  # Tooltip/UI state only.
            elif address in (0x48d4d0, 0x48d270): m.ret(0, 4)
            elif address == 0x15865c0: m.ret(0, 4)
            elif address == (0x10ddc16 if family == 1 else 0x10ddd96):
                # The selected ItemRef was already assigned by original code.
                assert m.r(window + 0x278) == wrapper
                uc.reg_write(m.ipreg, 0x10ddc78 if family == 1 else 0x10dddf8)
            elif address == 0x10dd800: m.ret()  # Price/UI refresh, not this mapping.
        elif stage[0] == 'confirm':
            if address == 0x813860: m.ret(net)
            elif address == send:
                packet = m.r(sp + 4)
                sent.append([m.r(packet + 8), m.r(packet + 0x10) | m.r(packet + 0x14) << 32,
                    m.r(packet + 0x18), m.r(packet + 0x1c)])
                m.ret(1, 4)
            elif address == 0x10ddae1: uc.emu_stop()

    m.run(0x1080720, hook)
    assert (m.r(wrapper + 4), m.r(wrapper + 8)) == (template, kind)
    m.w(wrapper, obj); m.uc.mem_write(bean, source['bean'])
    stage[0] = 'copy'; m.ui = obj + 8; m.w(m.stack, m.stop, bean)
    m.run(0x81a760, lambda *args: None)
    stage[0] = 'properties'; m.w(m.stack, m.stop)
    m.uc.reg_write(UC_X86_REG_ESI, wrapper)
    m.uc.reg_write(UC_X86_REG_EBX, bean)
    m.uc.reg_write(UC_X86_REG_EDI, column)
    m.run(0x10817bc, lambda *args: None)
    assert (m.r(obj + 0x14), m.r(obj + 0x48), m.r(obj + 0x4c)) == (item_key,
        struct.unpack_from('<I', source['bean'], 16)[0], column)
    # One real decoded container and one decoded ItemRef; no other-column alias.
    m.w(manager + 0xa4, 0, head, 1); m.w(head, node, node, node)
    m.uc.mem_write(head + 0x1d, b'\1'); m.w(node, head, head, head, column)
    m.w(node + 0x10, 0, innerhead, 1)
    m.w(innerhead, innernode, innernode, innernode); m.uc.mem_write(innerhead + 0x15, b'\1')
    m.w(innernode, innerhead, innerhead, innerhead, item_key, wrapper)
    m.w(vector, 0, 0, 0, 0); m.ui = manager
    m.w(m.stack, m.stop, vector, 1)
    stage[0] = 'enumerate'
    m.run(0x109c810 if family == 3 else 0x109ca00, lambda *args: None)
    assert selected == ([wrapper] if column == family else [])
    row = dict(column=column, process_call_column=source['process_call_column'],
        repair_list_container=family, selected=bool(selected), item_key=item_key,
        object_column=m.r(obj + 0x4c), original_lookup_and_predicate=True,
        manual_one_item_map_layout=True, map_copy_adapter=True)
    if not selected: return row
    anchor = 0x5030000; npc_key = 0x1234567800000513
    m.w(0x2944628, manager); m.w(0x2944920, 0)
    m.w(event + 8, cell); m.w(cell + 0x278, selected[0])
    m.w(anchor + 0x34, window); m.w(anchor + 0x1b8, npc_key & 0xffffffff, npc_key >> 32, 2)
    m.w(0x2945aec, cfgmanager); m.w(cfgmanager + 0x570, vt)
    m.w(config, 0xffffffff)  # Explicit not-in-blocking-config dependency.
    m.ui = anchor; m.w(m.stack, m.stop, event); stage[0] = 'click'
    m.run(0x10ddb30 if family == 1 else 0x10ddcb0, lambda *args: None)
    assert m.r(anchor + 0x1c4) == family
    assert m.r(window + 0x278) == wrapper
    m.w(net, netvt); m.w(netvt + 0x3c, send)
    stage[0] = 'confirm'; m.ui = anchor + 0x20; m.w(m.stack, m.stop, 0)
    m.run(0x10dda40, lambda *args: None)
    assert sent == [[2, npc_key, family, item_key]]
    wire = native_payload(0xe4cf30, scalars=[(8, 2), (0x18, family), (0x1c, item_key)],
        raw=[(0x10, struct.pack('<Q', npc_key))])
    assert wire == struct.pack('>iqii', *sent[0])
    row.update(original_click_started_at_entry=True, selected_ref_from_original_enumerator=True,
        original_sent_fields=sent[0], wire=wire.hex(),
        click_config_lookup_controlled_missing=True, label_rendering_and_price_refresh_skipped=True)
    return row


def shop_service_and_query():
    """Real service2 call boundary and real CNpcSellItemDlg column4 sender."""
    from unicorn.x86_const import UC_X86_REG_ESI, UC_X86_REG_EBP
    m = Machine(); key = 0x1234567800000042; dialog = 0x5003000
    net, vt, send = 0x5005000, 0x5006000, 0x5007000
    m.w(m.ui + 0xd0, key & 0xffffffff, key >> 32, 7)
    m.w(0x29455c0, 0); m.uc.reg_write(UC_X86_REG_ESI, m.ui)
    m.uc.reg_write(UC_X86_REG_EBP, 0); m.w(m.stack, m.stop)
    phase = ['open']; opened = []; captured = []

    def hook(uc, address, size, user):
        sp = uc.reg_read(m.spreg)
        if phase[0] == 'open':
            if address == 0x10ecaf0: m.ret(dialog)
            elif address == 0x110a690:
                opened.append([m.r(sp + i) for i in (4, 8, 12, 16)]); uc.emu_stop()
        elif phase[0] == 'store':
            if address == 0x110b9ec: uc.emu_stop()
        else:
            if address == 0x813860: m.ret(net)
            elif address == send:
                packet = m.r(sp + 4)
                captured.append([m.r(packet + 8), m.r(packet + 0x10) | m.r(packet + 0x14) << 32])
                assert m.r(packet + 4) == 0xc03f2
                uc.emu_stop()

    m.run(0x1636d38, hook)
    assert opened == [[7, key & 0xffffffff, key >> 32, 0]]
    # Preserve actual open arguments in the original callee frame and execute
    # the real source-field copies; skip the intervening CEGUI construction.
    phase[0] = 'store'; m.w(m.stack + 0x114, *opened[0][:3])
    m.uc.reg_write(UC_X86_REG_ESI, dialog)
    m.w(m.stack, m.stop); m.run(0x110b9bf, lambda *args: None)
    assert (m.r(dialog + 0xe8), m.r(dialog + 0xec)) == tuple(opened[0][1:3])
    m.w(net, vt); m.w(vt + 0x3c, send)
    phase[0] = 'query'; m.uc.reg_write(UC_X86_REG_ESI, dialog)
    m.w(m.stack, m.stop); m.run(0x1103df3, lambda *args: None)
    assert captured == [[4, key]]
    wire = native_payload(0xe4c430, scalars=[(8, 4)], raw=[(0x10, struct.pack('<Q', key))])
    assert wire == struct.pack('>iQ', 4, key)
    return dict(service_id=2, original_open_parameters=opened[0], original_factory='0x10ecaf0',
        actual_class='CNpcSellItemDlg', class_vtable='0x2290118', singleton_vtable='0x228ffe8',
        actual_query_fields=captured[0], wire=wire.hex(),
        gui_setup_not_executed=True, original_open_arguments_to_UI_fields_copy_executed=True,
        captured_call_arguments_bridge_original_callee_frame=True)


def equipment_slot_drag(slot):
    """Original registered equipment-slot callback passes container3 and slot.

    The event, cell and drag-manager state are controlled UI dependencies.
    Stop at the real ItemManager call rather than pretending a completed move.
    """
    m = Machine()
    event, cell, drag, manager = 0x5010000, 0x5011000, 0x5012000, 0x5013000
    m.w(m.ui + 0x20 + slot * 4, cell)
    m.w(event + 8, cell); m.w(event + 0x1c, 0)
    m.w(0x294555c, drag); m.w(drag + 4, 0x1e)
    m.w(0x2944628, manager)
    key_state = u32(0x2244c9c)
    existing_host_page = u32(0x2244554) & ~0xfff
    if not BASE <= key_state < BASE + len(DATA) and key_state & ~0xfff != existing_host_page:
        m.uc.mem_map(key_state & ~0xfff, 4096)
    calls = []

    def hook(uc, address, size, user):
        sp = uc.reg_read(m.spreg)
        if address == key_state: m.ret(0, 4)  # Ctrl is not held.
        elif address == 0x845450: m.ret()  # UI drag-selection clear.
        elif address == 0x10aa3d0:
            calls.append([m.r(sp + i) for i in (4, 8, 12)])
            assert uc.reg_read(m.cxreg) == manager
            uc.emu_stop()

    m.w(m.stack, m.stop, event)
    m.run(0x10cf2d0, hook)
    assert calls == [[cell, 3, slot]], calls
    return dict(slot=slot, registered_callback='0x10cf2d0', actual_item_manager_call='0x10aa3d0',
        column=calls[0][1], original_slot=calls[0][2], controlled_ui_event_and_drag_state=True,
        move_request_or_server_mutation_executed=False)


def main():
    watched = {name: sha(ROOT / name) for name in WATCHED}
    assert hashlib.sha256(DATA).hexdigest() == '2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791'
    archives = {}; config = PfsArchive(ROOT.parent / 'artres/config.pfs')
    raw = config.read('autoconfig/knight.gsp.item.citemattr.xml'); rows = decode(raw)
    cached = json.loads((ROOT / 'catalogs/knight.gsp.item.citemattr.json').read_text(encoding='utf8'))
    projection = lambda root: [dict(attributes=dict(r.attrib), lists={c.tag: [i.text for i in c] for c in r}) for r in root]
    assert projection(rows) == [dict(attributes=r['attributes'], lists=r.get('lists', {})) for r in cached]
    attr = next(dict(row.attrib) for row in rows if row.get('id') == '49009')
    assert int(attr['itemtypeid']) & 15 == 8 and (int(attr['itemtypeid']) & 0xf0) <= 0x50
    name = 'autoconfig/knight.gsp.item.citemattr.xml'
    archives[name] = dict(length=len(raw), crc32=hex(config.entries[name].crc), sha256=hashlib.sha256(raw).hexdigest(),
        records=len(rows), complete_attributes_lists_equal=True)
    ui = PfsArchive(ROOT.parent / 'artres/ui.pfs')
    for name in ('layouts/equipmentrepairsmiple.layout', 'layouts/npcsalemore.layout'):
        raw = ui.read(name); layout = ET.fromstring(raw)
        archives[name] = dict(length=len(raw), crc32=hex(ui.entries[name].crc), sha256=hashlib.sha256(raw).hexdigest(),
            root=layout.tag, text_labels=[p.get('Value') for p in layout.iter('Property') if p.get('Name') == 'Text'])
    cases = []
    for column in (1, 3, 4):
        for position in (0, 5):
            for binding in (0, 1):
                source, wire = bag_input(column, position, binding)
                for family in (1, 3):
                    row = chain(source, family, attr)
                    row.update(position=position, binding=binding, bag_wire_sha256=hashlib.sha256(wire).hexdigest())
                    cases.append(row)
    query = shop_service_and_query()
    equipment_drags = [equipment_slot_drag(slot) for slot in (0, 5)]
    # Actual RTTI identity, not a class label inferred from the address region.
    col = u32(0x2290118 - 4); td = u32(col + 12)
    assert DATA[td + 8 - BASE:].split(b'\0', 1)[0] == b'.?AVCNpcSellItemDlg@@'
    col = u32(0x228dce0 - 4); td = u32(col + 12)
    assert DATA[td + 8 - BASE:].split(b'\0', 1)[0] == b'.?AVCEquipDialog@@'
    output = io.StringIO()
    with redirect_stdout(output):
        for address, length in BLOCKS:
            print('REGION', hex(address)); disasm(address, length)
    assert watched == {name: sha(ROOT / name) for name in WATCHED}, 'Watched input changed; do not claim coherent evidence'
    result = dict(method='research: original decoder/source identity, exact container lookup, click and request construction',
        native_image_sha256=hashlib.sha256(DATA).hexdigest(), sources=archives,
        cases=cases, original_bag_decoder_cases=12, native_repair_chain_cases=len(cases),
        native_selected_click_and_send_cases=sum(r['selected'] for r in cases),
        native_shop_open_and_query=query, native_equipment_slot_drag_cases=equipment_drags,
        equipment_dialog_class_RTTI='CEquipDialog',
        new_native_case_count=len(cases) + 1 + len(equipment_drags),
        source_status='client_verified bounded original instructions; all dependency adapters declared',
        watched_sha256=watched, historical_cases_replayed=0, production_modified=False,
        no_4_to_3_container_conversion_observed=True,
        conclusions=['Original repair lists independently select map1/map3; map4 is not aliased',
            'Source bag3 selected ItemRef reaches original repair column3',
            'Original service2 opens CNpcSellItemDlg, whose examined query requests column4 and NPC key',
            'Existing four-as-own-equipment interpretation needs asset-domain correction; no compatibility alias authorized'],
        unverified=['Full original map insertion/STL-copy/CEGUI construction and rendering',
            'Complete service2 open-to-query UI lifecycle; captured arguments bridge its original callee frame',
            'Actual saved equipment qualification and server policies',
            'All other container meanings, authoritative migration and shared integration'],
        live_database_accessed=False, service_or_gui_operated=False, shared_runtime_verified=False)
    (ROOT / 'evidence/npc-repair-column-native.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    (ROOT / 'evidence/npc-repair-column-disassembly.txt').write_text(output.getvalue(), encoding='utf8')
    print('PASS', len(cases), 'native container/repair chains, one service2/query and two equipment-slot cases; no production change')


if __name__ == '__main__': main()
