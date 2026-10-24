"""Reproduce scene-grid findings using original x86 instructions offline."""
import hashlib
import json
from pathlib import Path
import struct
from native_inspect import BASE, DATA, capstone
from world_collision import maze_clear
from world_grids import SceneGrid, maze_grid, monster_grid
from pfs import PfsArchive

ROOT = Path(__file__).resolve().parent


def main():
    from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
    from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_ECX
    uc = Uc(UC_ARCH_X86, UC_MODE_32)
    uc.mem_map(BASE, (len(DATA)+4095)&~4095)
    uc.mem_write(BASE, DATA)
    uc.mem_map(0x5000000, 0x10000)
    stack, stop, wrapper, layout, cells = 0x5001000, 0x500f000, 0x5002000, 0x5002100, 0x5003000
    def put(a, *v): uc.mem_write(a, struct.pack('<'+'I'*len(v), *(n&0xffffffff for n in v)))
    put(wrapper, 0, layout)
    # Full extent 16x16, row-major, each possible flag once.
    flags = bytes(range(256))
    grid = SceneGrid(16, 16, flags, 12)
    uc.mem_write(cells, flags)
    total = 0
    for mask in (0, 1, 2, 3, 4, 8, 11, 15, 16, 128, 255):
        put(layout, 16, 16, cells, mask, 0, 0, 16, 16)
        coordinates = [(x*16, y*16) for y in range(16) for x in range(16)]
        coordinates += [(-1, -1), (-15, 0), (-16, 0), (0, -16), (255, 255), (256, 0), (0, 256)]
        for x, y in coordinates:
            put(stack, stop, wrapper, y)
            uc.reg_write(UC_X86_REG_EAX, x&0xffffffff)
            uc.reg_write(UC_X86_REG_ESP, stack)
            uc.emu_start(0x6284f0, stop, count=1000)
            assert uc.reg_read(UC_X86_REG_EIP) == stop
            actual = bool(uc.reg_read(UC_X86_REG_EAX)&255)
            assert actual == maze_clear(grid, x, y, mask=mask), (x, y, mask)
            total += 1
    # Execute unmodified loader's header-validation prefix. Host adapters stand
    # in only for resource-buffer Length/Data accessors, then stop before copy.
    holder, source, vt, raw = 0x5004000, 0x5004100, 0x5004200, 0x5005000
    get_length, get_data = 0x500e000, 0x500e010
    put(holder, 0, source)
    put(source, vt)
    put(vt+0x1c, get_length)
    put(vt+0x14, get_data)
    length = [0]
    def hook(emu, addr, size, user):
        if addr == 0x6724cf:
            emu.emu_stop()
        elif addr in (get_length, get_data):
            sp = emu.reg_read(UC_X86_REG_ESP)
            ret = struct.unpack('<I', emu.mem_read(sp, 4))[0]
            emu.reg_write(UC_X86_REG_EAX, length[0] if addr == get_length else raw)
            emu.reg_write(UC_X86_REG_ESP, sp+4)
            emu.reg_write(UC_X86_REG_EIP, ret)
    uc.hook_add(UC_HOOK_CODE, hook)
    headers = []
    for offset, payload_len, expected in ((12, 6, True), (16, 10, True), (11, 5, False), (12, 5, False), (16, 6, False)):
        candidate = struct.pack('<III', offset, 3, 2)+bytes(payload_len)
        uc.mem_write(raw, candidate)
        length[0] = len(candidate)
        put(stack, stop)
        uc.reg_write(UC_X86_REG_EBX, holder)
        uc.reg_write(UC_X86_REG_ESP, stack)
        uc.emu_start(0x672490, stop, count=1000)
        accepted = uc.reg_read(UC_X86_REG_EIP) == 0x6724cf
        assert accepted == expected
        headers.append({'header_size': offset, 'length': len(candidate), 'accepted': accepted})
    # Real CCharacter vtable getter and real actor mask setter: no hook
    # substitutes the state selection or writes to the movement object.
    role, actor, movement = 0x5007000, 0x5008000, 0x5009000
    mask_cases = []
    from world_collision import character_movement_mask
    for state in (0, 1, 2, 255):
        put(role, 0x2298bcc)
        uc.mem_write(role+0x218, bytes([state]))
        put(role+0x26c, actor)
        put(actor, 0x2462544)
        put(actor+0x1a8, movement)
        put(movement+0x48, 0xcccccccc)
        put(stack, stop)
        uc.reg_write(UC_X86_REG_ESI, role)
        uc.reg_write(UC_X86_REG_ESP, stack)
        uc.emu_start(0x12028f7, 0x120291b, count=1000)
        assert uc.reg_read(UC_X86_REG_EIP) == 0x120291b
        selected = struct.unpack('<I',uc.mem_read(movement+0x48,4))[0]
        assert selected == character_movement_mask(state)
        uc.reg_write(UC_X86_REG_ESI, movement)
        uc.reg_write(UC_X86_REG_EDI, layout)
        uc.emu_start(0x6bc33d, 0x6bc343, count=100)
        installed = struct.unpack('<I',uc.mem_read(layout+0xc,4))[0]
        assert installed == selected
        mask_cases.append({'role_state_0x218':state,'movement_mask':selected,
                           'native_getter_setter_and_query_install':True})
    archive = PfsArchive(ROOT/'runtime/client/artres/map.pfs')
    counts = {'maze': 0, 'monster': 0}
    anomalies = []
    for name in archive.entries:
        if name.endswith('/maze.dat'):
            maze_grid(archive.read(name)); counts['maze'] += 1
        elif name.endswith('/monster.dat'):
            grid = monster_grid(archive.read(name)); counts['monster'] += 1
            positions = [(x,y) for x,y,v in grid.records]
            repeated = len(positions)-len(set(positions))
            outside = sum(x >= grid.width or y >= grid.height for x,y,v in grid.records)
            if repeated or outside: anomalies.append({'path':name,'duplicate_records':repeated,'outside_declared_extent':outside})
    result = {'image_sha256':hashlib.sha256(DATA).hexdigest(), 'native_query':hex(0x6284f0),
              'native_query_differential_cases':total,'native_loader_header_cases':headers,
              'archive_crc_parsed':counts,'monster_preserved_anomalies':anomalies,
              'character_mask_native_cases':mask_cases, 'movement_mask_default':None,'monster_region_semantics':'unproven'}
    (ROOT/'evidence/scene-grid-native.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    cs = capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
    ranges = ((0x6284f0,0x52),(0x672490,0xa2),(0x672410,0x78),(0x11e0363,0x49),(0x12028f7,0x24),(0x1209d10,7),
              (0x652af0,0xe),(0x6bc33d,6),(0x6bc3d9,0x2b),(0x626bc7,0x15))
    text = 'native-image.bin SHA256 '+result['image_sha256']+'\n'
    for start,size in ranges:
        text += '\n'+ '\n'.join(f'{i.address:08x} {i.mnemonic:8} {i.op_str}' for i in cs.disasm(DATA[start-BASE:start-BASE+size],start))+'\n'
    (ROOT/'evidence/scene-grid-native-disassembly.txt').write_text(text,encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))

if __name__ == '__main__': main()
