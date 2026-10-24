"""Bounded original 100008 selection/target/sender and direct PFS source audit.

Synthetic selected UI ID/target object and config-table lookup are explicit
adapters. Original config copy, target-mask reader/test, command selection,
CSendAction field writes, marshal and decoder run unchanged. No gameplay.
"""
from pathlib import Path
import hashlib
import json
import struct
import sys
import zlib
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from native_inspect import DATA
from inspect_client import ROOT, catalog_rows
from pfs import PfsArchive
from bxml import decode
from research_battle import NativeBattleDecoder
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESI, UC_X86_REG_EDI

IMAGE_SHA = '2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791'


def source_audit():
    archive = PfsArchive(ROOT / 'artres/config.pfs')
    sources, selected, absent = {}, {}, {}
    ids = {'100008', '600005', '500001', '500067', '10011', '10012'}
    for suffix in ('skill.cskillitem', 'skill.cskillshowlistclient', 'skill.cskillshowlist',
                   'skill.cskilltypeconfig', 'skill.cskillbase', 'skill.cskillconsume',
                   'skill.cskillcost', 'skill.cskilleffectextra', 'battle.cbattlemagicconfig'):
        path = 'autoconfig/knight.gsp.' + suffix + '.xml'
        raw = archive.read(path)
        rows = catalog_rows(decode(raw))
        sources[path] = dict(sha256=hashlib.sha256(raw).hexdigest(), crc32=f'{zlib.crc32(raw):08x}',
                             size=len(raw), rows=len(rows))
        selected[suffix] = [r for r in rows if r['attributes']['id'] in ids]
        absent[suffix] = not any(r['attributes']['id'] == '100008' for r in rows)
        if suffix == 'skill.cskillshowlist':
            selected[suffix] = [r for r in rows if '100008' in r['lists'].get('skillnumber', ())]
    item = next(r['attributes'] for r in selected['skill.cskillitem'] if r['attributes']['id'] == '100008')
    assert item['targettype'] == '480' and item['effectid'] == '10011' and item['bCanUseInBattle'] == '1'
    return dict(sources=sources, rows=selected, no_id100008=absent)


def native_taizu_action(target_position=21, *, target_mask=480):
    """Return actual manual-player 14-byte body from a synthetic selected target.

    The target has original object-class discriminator3 and position21; this
    exercises target-mask bit8. No claim about every legal target is made.
    """
    assert target_position == 21
    assert target_mask in (0, 480)
    p = NativeBattleDecoder()
    manager, target, cfg, table, table_vt, net, net_vt = [p.allocate(n) for n in (0x400, 0x220, 0x100, 0x20, 0x20, 0x30, 0x50)]
    p.obj = manager + 0x9c
    p.call(0xd598c0)
    p.write(0x2944798, manager)
    p.write(0x29448a4, p.allocate(0x100))
    p.write(0x29455b8, 0)
    p.write(manager + 0x54, 3)  # Original role/manual command phase.
    p.write(target + 0x140, target_position)
    p.write(target + 0x17c, 3)  # Original validation branch, not a server type enum.
    p.write(cfg, 100008)
    p.write(cfg + 0xc4, target_mask)
    p.write(cfg + 0xc8, 1)
    p.write(cfg + 0xcc, 10011)
    p.write(table, table_vt)
    p.write(table_vt + 8, 0x5000500)
    p.write(net, net_vt)
    p.write(net_vt + 0x3c, 0x5000510)
    captured, hits = [], []

    def hook(uc, address, _size, _user):
        sp = uc.reg_read(p.sp)
        def ret(value=0, cleanup=0):
            uc.reg_write(p.ax, value)
            uc.reg_write(p.ip, p.read(sp))
            uc.reg_write(p.sp, sp + 4 + cleanup)
        if address == 0x89ea00:
            ret(table)
        elif address == 0x5000500:
            assert p.read(sp + 4) == 100008
            ret(cfg, 4)
        elif address == 0x8ae9e0:
            ret()  # Temporary copied config string destruction only.
        elif address == 0x813860:
            ret(net)
        elif address == 0x5000510:
            packet = p.read(sp + 4)
            captured.append((p.read(packet + 4), packet))
            uc.emu_stop()
        elif address in (0x12cc180, 0x119acd0, 0x119ab00, 0x1196060):
            hits.append(hex(address))

    p.u.hook_add(UC_HOOK_CODE, hook)
    # Original skill-list selection tail: ESI is the UI-selected ID fixture.
    p.write(p.stack, p.stop)
    p.u.reg_write(p.sp, p.stack)
    p.u.reg_write(UC_X86_REG_ESI, 100008)
    p.u.emu_start(0x11b1cd6, 0x11b1d4c, count=3000)
    assert p.u.reg_read(p.ip) == 0x11b1d4c
    assert p.read(manager + 0xe0) == 100008
    # Actual target-click branch validates original mask480, pushes operation2,
    # then executes the original sender all the way to its network boundary.
    p.write(p.stack, p.stop)
    p.u.reg_write(p.sp, p.stack)
    p.u.reg_write(UC_X86_REG_ESI, manager)
    p.u.reg_write(UC_X86_REG_EDI, target_position)
    p.u.reg_write(p.cx, target)
    p.u.emu_start(0x1196b2a, 0x1196b46, count=10000)
    if target_mask == 0:
        assert not captured and p.u.reg_read(p.ip) == 0x1196b46
        return dict(sensitivity_fixture='only config target mask changed480 to0',
                    target=target_position, sent=False, native_calls=hits)
    assert len(captured) == 1 and captured[0][0] == 0xc1b5c, captured
    p.obj = captured[0][1]
    p.write(p.stream, 0x224c100, p.buf, 0)
    p.write(p.buf - 12, 4096, 0, 1)
    p.call(0xe41550, p.stream)
    body = bytes(p.u.mem_read(p.buf, p.read(p.buf - 8)))
    assert body == struct.pack('>iiiBB', 2, target_position, 100008, 1, 0)
    decoder = NativeBattleDecoder().decode('CSendAction', body)
    assert tuple(decoder.read(decoder.obj + off) for off in (12, 16, 20)) == (2, target_position, 100008)
    assert bytes(decoder.u.mem_read(decoder.obj + 24, 2)) == b'\x01\x00'
    return dict(packet_type='0xc1b5c', body_hex=body.hex(), body_length=len(body),
                operation=2, target=target_position, operation_id=100008, is_role=1, is_auto=0,
                selection_entered_target_mode=True, native_calls=hits,
                target_fixture=dict(object_class=3, position=target_position),
                ui_renderer_executed=False, server_combat_authorized=False)


def native_numeric_classes():
    p = NativeBattleDecoder()
    result = {}
    for skill_id in (100008, 600005, 500001, 500067):
        p.call(0x1070ea0, skill_id)
        result[skill_id] = p.u.reg_read(p.ax)
    assert result == {100008: 1, 600005: 6, 500001: 2, 500067: 2}
    return result


if __name__ == '__main__':
    assert hashlib.sha256(DATA).hexdigest() == IMAGE_SHA
    print(json.dumps(dict(image_sha256=IMAGE_SHA, original_sources=source_audit(),
                          native_action=native_taizu_action(),
                          target_mask_sensitivity=native_taizu_action(target_mask=0),
                          native_numeric_classes=native_numeric_classes()), ensure_ascii=False, indent=2))
