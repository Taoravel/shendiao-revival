"""Bounded original skill namespace and Qinggong state feedback, entirely offline.

Original instructions choose dispatch, decode bodies and mutate native trees.
Heap/CRT adapters are inherited from research_battle. Update execution stops
after the actual tree assignment, before unrelated cache and UI work.
Synthetic values below are sensitivity fixtures, never learning authorization.
"""
from pathlib import Path
import hashlib
import json
import struct
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from native_inspect import DATA
from research_battle import NativeBattleDecoder
from inspect_client import ROOT, catalog_rows
from pfs import PfsArchive
from bxml import decode
from verify_social_native import native_payload
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EBX

IMAGE_SHA = '2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791'


def sources():
    archive = PfsArchive(ROOT / 'artres/config.pfs')
    result = {}
    for name in ('cskillshowlist', 'cskillshowlistclient'):
        path = 'autoconfig/knight.gsp.skill.' + name + '.xml'
        raw = archive.read(path)
        result[name] = (catalog_rows(decode(raw)), hashlib.sha256(raw).hexdigest())
    return result


def native_namespace_rows():
    """Execute numeric classifier and actual exists-dispatch for all UI class6 IDs.

    Stops at native container lookup entry (or class7 list branch entry), so
    this proves selected storage, not a particular ID's learned status.
    """
    source = sources()
    row = next(r for r in source['cskillshowlist'][0] if r['attributes']['id'] == '6')
    p = NativeBattleDecoder()
    manager = p.allocate(0x200)
    selected = []

    def hook(uc, address, _size, _user):
        if address in (0x108e030, 0x1090770):
            selected.append((address, uc.reg_read(p.cx) - manager))
            uc.emu_stop()
        elif address == 0x12d4cd0:
            assert uc.reg_read(p.cx) == manager
            selected.append((address, 0x74))
            uc.emu_stop()
        elif address == 0x12d5677:
            selected.append((address, 0x80))
            uc.emu_stop()

    p.u.hook_add(UC_HOOK_CODE, hook)
    names = {int(r['attributes']['id']): r['attributes'].get('skillname')
             for r in source['cskillshowlistclient'][0]}
    results = []
    for text in row['lists']['skillnumber']:
        skill_id = int(text)
        p.call(0x1070ea0, skill_id)
        native_class = p.u.reg_read(p.ax)
        p.write(p.stack, p.stop, skill_id)
        p.u.reg_write(p.sp, p.stack)
        p.u.reg_write(p.cx, manager)
        selected.clear()
        p.u.emu_start(0x12d55f0, p.stop, count=500)
        assert len(selected) == 1
        entry, offset = selected[0]
        results.append(dict(skill_id=skill_id, name=names.get(skill_id), native_class=native_class,
                            exists_storage_offset=hex(offset), reached=hex(entry)))
    assert len(results) == 26
    assert {r['skill_id'] for r in results if r['exists_storage_offset'] == '0x40'} == {
        100007, 100008, 100009, 310202, 700004}
    assert next(r for r in results if r['skill_id'] == 350001)['exists_storage_offset'] == '0x74'
    return dict(rows=results, resource_sha256={k: v[1] for k, v in source.items()})


def native_learning_updates():
    """Original SUpdateAssistSkill decode/Process to assignment, and original getters.

    Deliberately stops at 12d607d: cache erasure, level1 shortcut presentation,
    outer callbacks and gameplay are not executed. Values are fixture states.
    """
    p = NativeBattleDecoder()
    manager = p.allocate(0x200)
    # The learned-assist packet is a list; its Process constructs this temporary
    # native tree. Execute that actual empty-tree initialization block.
    p.write(p.stack, p.stop)
    p.u.reg_write(p.sp, p.stack)
    p.u.reg_write(UC_X86_REG_EBX, 0)
    p.u.emu_start(0x12d5bbd, 0x12d5bea, count=100)
    assert p.u.reg_read(p.ip) == 0x12d5bea
    p.u.mem_write(manager + 0x74, bytes(p.u.mem_read(p.stack + 0x1c, 12)))
    p.decode('SSendOtherSkills', b'\x00\x01')
    p.u.mem_write(manager + 0x40, bytes(p.u.mem_read(p.obj + 8, 12)))
    p.write(0x29448a4, manager)
    p.write(0x2945610, 0)
    p.write(0x2944564, 0)
    p.decode('SSendOtherSkills', b'\x01' + struct.pack('>ii', 350001, 91) + b'\x01')
    p.call(0x12d6810, 0, 0)
    packet = p.obj

    def query(address, skill_id=350001):
        p.obj = manager
        p.call(address, skill_id)
        result = p.u.reg_read(p.ax)
        p.obj = packet
        return result

    assert query(0x12d1d50) == 91
    assert query(0x12d4cd0) == 0
    results = []
    for level, experience in ((1, 0), (2, 123), (3, 456), (0, 0)):
        p.obj = packet
        p.call(0xdd0a30)
        body = struct.pack('>iii', 350001, level, experience)
        assert native_payload(0xdd0a80, scalars=[(8, 0x227cfac), (12, 350001),
                                              (16, level), (20, experience)]) == body
        p.write(p.stream, 0x224c100, p.buf, 0)
        p.write(p.buf - 12, len(body), len(body), 1)
        p.u.mem_write(p.buf, body)
        p.call(0xdd0c30, p.stream)
        assert p.read(p.stream + 8) == len(body)
        assert tuple(p.read(packet + n) for n in (12, 16, 20)) == (350001, level, experience)
        p.write(p.stack, p.stop, 0, 0)
        p.u.reg_write(p.sp, p.stack)
        p.u.reg_write(p.cx, packet)
        p.u.emu_start(0x12d7270, 0x12d607d, count=10000)
        assert p.u.reg_read(p.ip) == 0x12d607d
        native_level = query(0x12d4cd0)
        native_experience = query(0x12d4d40)
        other_value = query(0x12d1d50)
        assert (native_level, native_experience, other_value) == (level, experience, 91)
        results.append(dict(body_hex=body.hex(), level=native_level, experience=native_experience,
                            other_skills_value_unchanged=other_value))
    snapshots = []
    for values in (((350001, 2, 789), (360001, 5, 321)), ()):
        p.obj = packet
        p.call(0xea3bd0)
        body = bytes([len(values)]) + b''.join(struct.pack('>iii', *v) for v in values)
        # A separate synthetic linked-list fixture exercises original marshal.
        head = 0x5001400
        nodes = [0x5001500 + i * 0x40 for i in range(len(values))]
        raw = [(head - 0x5001000, struct.pack('<II', nodes[0] if nodes else head,
                                           nodes[-1] if nodes else head))]
        for index, (node, value) in enumerate(zip(nodes, values)):
            raw.append((node - 0x5001000, struct.pack('<6I',
                        nodes[index + 1] if index + 1 < len(nodes) else head,
                        nodes[index - 1] if index else head, 0x227cfac, *value)))
        assert native_payload(0xea4150, scalars=[(12, head), (16, len(values))], raw=raw) == body
        p.write(p.stream, 0x224c100, p.buf, 0)
        p.write(p.buf - 12, len(body), len(body), 1)
        p.u.mem_write(p.buf, body)
        p.call(0xea41d0, p.stream)
        assert p.read(p.stream + 8) == len(body)
        decoded = [tuple(p.read(bean + n) for n in (4, 8, 12))
                   for bean in p.list_items(packet + 8)]
        assert decoded == list(values)
        p.write(p.stack, p.stop, 0, 0)
        p.u.reg_write(p.sp, p.stack)
        p.u.reg_write(p.cx, packet)
        p.u.emu_start(0x12d5b80, 0x12d4b27, count=20000)
        assert p.u.reg_read(p.ip) == 0x12d4b27
        expected = {v[0]: v[1:] for v in values}
        actual = {key: (query(0x12d4cd0, key), query(0x12d4d40, key))
                  for key in (350001, 360001)}
        assert actual == {key: expected.get(key, (0, 0)) for key in actual}
        assert query(0x12d1d50) == 91
        snapshots.append(dict(body_hex=body.hex(), actual=actual))
    return dict(other_skills_only_assist_query=0, updates=results, snapshots=snapshots,
                update_stop_after_write='0x12d607d', snapshot_stop_after_copy='0x12d4b27')


def native_packed_presentation():
    p = NativeBattleDecoder()
    result = []
    for values in ((1, 2, 3), (10, 9, 8)):
        packed = (values[0] << 10) | (values[1] << 4) | values[2]
        p.call(0x1203de0, packed)
        actual = tuple(p.u.mem_read(p.obj + 0x21a, 3))
        assert actual == values
        result.append(dict(packed=packed, entity_bytes=list(actual)))
    return result


def main():
    assert hashlib.sha256(DATA).hexdigest() == IMAGE_SHA
    print(json.dumps(dict(image_sha256=IMAGE_SHA, namespaces=native_namespace_rows(),
                          learned_assist=native_learning_updates(),
                          packed_role_choices=native_packed_presentation(),
                          gui_verified=False, server_learning_authorized=False),
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
