"""Bounded original NPC navigation and exact ordered-map route feedback."""
from pathlib import Path
import hashlib
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from native_inspect import DATA, u32
from research_battle import NativeBattleDecoder
from pfs import PfsArchive
from bxml import decode
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EBX, UC_X86_REG_EBP


def native_npc_navigation(npc_record, current_map):
    p = NativeBattleDecoder()
    cfg, scene, main, table, vt, npc, metadata = [p.allocate(size) for size in (0x200, 0x500, 0x500, 0x40, 0x40, 4, 4)]
    template = int(npc_record['id'])
    p.write(cfg, template)
    p.write(cfg + 0xfc, *(int(npc_record[k]) for k in ('mapid', 'xPos', 'yPos')))
    p.write(table, vt)
    p.write(vt + 8, 0x5000500)
    p.write(npc, template)
    p.write(0x2944564, scene)
    p.write(0x294454c, main)
    p.write(scene + 0x110, current_map)
    p.write(scene + 0x364, 0)  # Explicit non-mode2 fixture, not actual live mode.
    key_state = u32(0x2244c9c)
    p.u.mem_map(key_state & ~4095, 4096)

    def hook(uc, address, _size, _user):
        sp = uc.reg_read(p.sp)

        def ret(value, cleanup=0):
            uc.reg_write(p.ax, value)
            uc.reg_write(p.ip, p.read(sp))
            uc.reg_write(p.sp, sp + 4 + cleanup)

        if address == 0x89df90:
            ret(table)
        elif address == 0x5000500:
            assert p.read(sp + 4) == template
            ret(cfg, 4)
        elif address == key_state:
            ret(0, 4)  # Ctrl not pressed.

    p.u.hook_add(UC_HOOK_CODE, hook)
    p.u.reg_write(p.sp, p.stack)
    p.write(p.stack + 0x14, metadata)
    p.u.reg_write(UC_X86_REG_EBX, npc)
    p.u.reg_write(UC_X86_REG_EBP, 2)
    p.u.emu_start(0x15725e7, 0x1142620, count=1000)
    assert p.u.reg_read(p.ip) == 0x1142620
    sp = p.u.reg_read(p.sp)
    return tuple(p.read(sp + i) for i in range(4, 32, 4))


def native_route_membership(pairs):
    p = NativeBattleDecoder()
    controller, scene, value = [p.allocate(size) for size in (0x100, 0x200, 4)]
    p.write(0x2944564, scene)
    p.obj = controller + 0x2c
    p.call(0x1141170)  # Original empty pair-map constructor.

    def query(source, destination):
        p.obj = controller
        p.write(scene + 0x110, source)
        p.write(value, destination)
        p.call(0x1141970, value)
        return p.u.reg_read(p.ax) & 255

    empty = {(a, b): query(a, b) for a, b in ((1007, 1007), (1376, 1376), (1007, 1376), (1376, 1007))}
    assert empty == {(1007, 1007): 1, (1376, 1376): 1, (1007, 1376): 0, (1376, 1007): 0}
    for row in pairs:
        p.obj = controller + 0x2c
        p.write(value, int(row['sourceMapID']) * 10000 + int(row['destMapID']))
        p.call(0x64fd50, value)  # Original pair-map insertion, not Python membership.
        p.write(p.u.reg_read(p.ax), int(row['xPos']), int(row['yPos']))
    present = {(a, b): query(a, b) for a, b in ((1007, 1376), (1376, 1007))}
    assert present == {(1007, 1376): 1, (1376, 1007): 1}
    return {'empty': {str(k): v for k, v in empty.items()}, 'exact_pairs_present': {str(k): v for k, v in present.items()}}


def main():
    root = Path(__file__).resolve().parents[2]
    pfs = PfsArchive(root / 'artres/config.pfs')
    npc = next(dict(row.attrib) for row in decode(pfs.read('autoconfig/knight.gsp.npc.cnpcconfig.xml')) if row.get('id') == '10157')
    pairs = [dict(row.attrib) for row in decode(pfs.read('paths.xml'))
        if (row.get('sourceMapID'), row.get('destMapID')) in {('1007', '1376'), ('1376', '1007')}]
    navigation = {source: native_npc_navigation(npc, source) for source in (1007, 1376)}
    assert all(args == (528, 912, 1376, 10157, 0, 0, 1) for args in navigation.values())
    print(json.dumps(dict(image_sha256=hashlib.sha256(DATA).hexdigest(), navigation=navigation,
        original_pairs=pairs, route_membership=native_route_membership(pairs),
        gui_verified=False, server_acceptance_verified=False), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
