"""Static original CMapConfig position-field consumers, without gameplay edits."""
import hashlib
import json
from pathlib import Path
import struct

from bxml import decode
from inspect_client import ROOT
from native_inspect import BASE, DATA, refs
from pfs import PfsArchive
import capstone


OUT = Path(__file__).resolve().parent / 'evidence'
IMAGE_SHA256 = '2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791'
FIELDS = {'xjPos': (0x2259960, 0xb0, 0x87a1b9),
          'yjPos': (0x2259954, 0xb4, 0x87a1f2),
          'playerPosX': (0x2259878, 0x120, 0x87a409),
          'playerPosY': (0x2259860, 0x124, 0x87a442)}


def instructions(start, end):
    decoder = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    return list(decoder.disasm(DATA[start-BASE:end-BASE], start))


def wide_string(address):
    start = end = address-BASE
    while DATA[end:end+2] != b'\0\0':
        end += 2
    return DATA[start:end].decode('utf-16-le')


def ascii_string(address):
    start = address-BASE
    return DATA[start:DATA.index(b'\0', start)].decode('ascii')


def main():
    image_hash = hashlib.sha256(DATA).hexdigest()
    assert image_hash == IMAGE_SHA256
    archive_path = ROOT/'artres/config.pfs'
    archive = PfsArchive(archive_path)
    entry = 'autoconfig/knight.gsp.map.cmapconfig.xml'
    raw = archive.read(entry)
    rows = [dict(item.attrib) for item in decode(raw)]
    assert len(rows) == 304
    field_rows = []
    for name, (string_address, offset, store_address) in FIELDS.items():
        assert wide_string(string_address) == name
        store = instructions(store_address, store_address+6)[0]
        assert store.mnemonic == 'mov'
        assert store.op_str == f'dword ptr [edi + {hex(offset)}], eax'
        prior = instructions(store_address-9, store_address)
        # These stores follow the exact common integer-attribute reader.
        assert any(item.mnemonic == 'call' and item.op_str == '0x409ce0' for item in prior)
        field_rows.append(dict(field=name, string_address=hex(string_address),
            original_loader_store=hex(store_address), record_offset=hex(offset),
            string_absolute_reference_candidates=[hex(address) for address in refs(string_address)],
            store_bytes=store.bytes.hex(), store_instruction=store.op_str))

    # Byte-accurate field-load checks in the original Worldmap.layout consumer.
    checks = ((0x15f346b, 'fild', 'dword ptr [esp + 0x264]'),
              (0x15f3476, 'fild', 'dword ptr [esp + 0x268]'),
              (0x1601098, 'mov', 'eax, dword ptr [edi + 0xb0]'),
              (0x16010e6, 'mov', 'edi, dword ptr [edi + 0xb4]'))
    for address, mnemonic, operands in checks:
        actual = instructions(address, address+7)[0]
        assert (actual.mnemonic, actual.op_str) == (mnemonic, operands)
    rectangle_delta = struct.unpack_from('<d', DATA, 0x2474118-BASE)[0]
    assert rectangle_delta == 25.0
    strings = {hex(address): ascii_string(address) for address in
               (0x22c17e4, 0x24465c0, 0x2453b9c)}
    assert strings == {'0x22c17e4': 'Worldmap.layout',
                       '0x24465c0': 'UnifiedAreaRect', '0x2453b9c': 'Image'}
    assert wide_string(0x22c2348) == 'MapName'
    assert wide_string(0x224bdc4) == '%d'
    chunks = {}
    for label, start, end in (
        ('original_map_attribute_loader', 0x879e30, 0x87a6af),
        ('table_registry_descriptor', 0xd42bcd, 0xd42be9),
        ('table_accessor', 0x89dd50, 0x89dd5b),
        ('scene_copies_selected_map_config', 0x11e255e, 0x11e257b),
        ('config_copy_xj_yj', 0x11c5a0d, 0x11c5a25),
        ('config_copy_player_x_y', 0x11c5a9a, 0x11c5ab8),
        ('worldmap_layout_constructor', 0x15f3320, 0x15f335a),
        ('worldmap_get_current_map_and_copy', 0x15f339a, 0x15f33e6),
        ('worldmap_player_rectangle', 0x15f346b, 0x15f349b),
        ('worldmap_rect_property', 0x15f34ad, 0x15f34e4),
        ('worldmap_rect_formatter', 0x15f2830, 0x15f29d0),
        ('xj_yj_named_value_construction', 0x160102c, 0x1601122),
        ('named_integer_formatter', 0x809e90, 0x809f49),
    ):
        chunks[label] = dict(start=hex(start), end_exclusive=hex(end),
            bytes_sha256=hashlib.sha256(DATA[start-BASE:end-BASE]).hexdigest(),
            instructions=[dict(address=hex(item.address), mnemonic=item.mnemonic,
                operands=item.op_str, bytes=item.bytes.hex()) for item in instructions(start, end)])

    focused = {1007, 1100, 1103, 1104, 1105, 1107, 1108,
               1301, 1304, 1305, 1306, 1308, 1309, 1393, 1394, 1395}
    result = dict(all_static_assertions_passed=True, method='fresh original PFS and static original mapped-image dataflow',
        image_sha256=image_hash, archive=str(archive_path), entry=entry,
        config_entry_sha256=hashlib.sha256(raw).hexdigest(), crc_checked=True,
        configured_maps=len(rows), original_attribute_names=list(rows[0]),
        focused_original_rows=[row for row in rows if int(row['id']) in focused],
        loader_fields=field_rows, ui_original_ascii_strings=strings,
        ui_rectangle_delta=rectangle_delta, ui_rect_local_record_base='caller ESP + 0x144',
        ui_playerPosX_local='caller ESP + 0x264', ui_playerPosY_local='caller ESP + 0x268',
        xj_yj_named_value_keys=['MapName', 'xjPos', 'yjPos'],
        original_instruction_chunks=chunks,
        conclusions=dict(player_fields_observed_worldmap_ui=True,
            xj_yj_named_integer_construction_observed=True,
            scene_spawn_authority_established=False,
            replacement_portal_landing_authorized=False),
        executed_original_instructions=False, live_server_changed=False, gui_verified=False,
        limitations=['Static dataflow, not original instruction execution or complete call-graph proof.',
            'Observed UI usage does not prove no other reader exists.',
            'xjPos/yjPos field units and final hyperlink/navigation consumer remain unproven.',
            'No original server landing, automatic fallback, portal replacement, or instance authority established.'],
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (OUT/'world-map-position-fields-research.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps(dict(all_static_assertions_passed=True, configured_maps=len(rows),
        fields=len(field_rows), worldmap_rectangle_delta=rectangle_delta,
        spawn_authority_established=False)), flush=True)


if __name__ == '__main__':
    main()
