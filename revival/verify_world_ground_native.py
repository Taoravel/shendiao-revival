"""Replay original background-tile submission with explicit offline fixtures.

The renderer is a recording Adapter. This checks culling and submission, not GPU
output. No process, client launch, server, or runtime resource is touched.
"""
import hashlib
import json
from pathlib import Path
import struct
from native_inspect import BASE, DATA, u32
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_EDI


def replay(*, camera=(0, 0, 1024, 768), layers=True, textures=True,
           bounds=(0, 0, 1024, 768)):
    e = Uc(UC_ARCH_X86, UC_MODE_32)
    e.mem_map(BASE, (len(DATA)+4095)&~4095)
    e.mem_write(BASE, DATA)
    e.mem_map(0x5000000, 0x100000)
    world, engine, evt, renderer, rvt, mapobj, layer, cells, tile = (
        0x5001000, 0x5002000, 0x5003000, 0x5004000, 0x5005000,
        0x5006000, 0x5007000, 0x5008000, 0x5009000)
    stack, stop, getter, submit = 0x5080000, 0x500f000, 0x500f100, 0x500f200

    def w(a, *values):
        e.mem_write(a, struct.pack('<'+'I'*len(values), *values))

    def r(a):
        return struct.unpack('<I', e.mem_read(a, 4))[0]

    w(world+8, engine)
    w(engine, evt)
    w(evt+0x5c, getter)
    w(renderer, rvt)
    # Keep the real descriptor Adapter too; record at the following generic
    # textured-quad Interface instead of replacing its default fields.
    w(rvt+0xfc, 0x6d3940)
    w(rvt+0x100, submit)
    w(world+0x298, mapobj)
    w(mapobj+0xc, 1024, 768)
    w(mapobj+0x6c, layer)
    w(mapobj+0x70, layer+0x38 if layers else layer)
    w(world+0x488, *camera)
    e.mem_write(world+0x4a8, struct.pack('<f', 1))
    # Native layer: center XY, camera-relative factors XY, cull bounds,
    # tile dimensions, tile counts, pointer array, repeat bytes.
    w(layer, 512, 384)
    e.mem_write(layer+8, struct.pack('<ff', 0, 0))
    w(layer+0x10, *bounds)
    w(layer+0x20, 256, 256, 4, 3, cells)
    for i in range(12):
        w(cells+i*4, tile if textures else 0)
    w(tile+0x20, 0x12345678)
    w(stack, stop, world)
    invalid = u32(0x2244898)
    if not BASE <= invalid < BASE+len(DATA):
        e.mem_map(invalid&~4095, 4096)
    descriptors = []

    def ret(n, value=0):
        sp = e.reg_read(UC_X86_REG_ESP)
        dest = r(sp)
        e.reg_write(UC_X86_REG_ESP, sp+4+n)
        e.reg_write(UC_X86_REG_EAX, value)
        e.reg_write(UC_X86_REG_EIP, dest)

    def hook(uc, address, size, user):
        if address == stop:
            uc.emu_stop()
        elif address == invalid:
            raise AssertionError('Original iterator guard failed')
        elif address == getter:
            ret(4, renderer)
        elif address == submit:
            ptr = r(uc.reg_read(UC_X86_REG_ESP)+4)
            assert r(ptr+0xc) == 1
            assert r(ptr+0x14) == 0  # Native generic draw defaults this to white.
            descriptors.append({'texture_handle': hex(r(ptr)),
                'screen_rect': list(struct.unpack('<4f', uc.mem_read(r(ptr+8), 16))),
                'quad_count': r(ptr+0xc), 'explicit_vertex_colors_pointer': r(ptr+0x14)})
            ret(4)

    e.hook_add(UC_HOOK_CODE, hook)
    e.reg_write(UC_X86_REG_ESP, stack)
    e.emu_start(0x605110, stop, count=100000)
    assert e.reg_read(UC_X86_REG_EIP) == stop
    return {'camera': camera, 'layer_bounds': bounds, 'layers_present': layers,
            'tile_pointers_present': textures, 'submissions': descriptors}


def main():
    cases = [replay(), replay(layers=False), replay(textures=False),
             replay(camera=(12032, 6592, 13056, 7360)),
             replay(bounds=(2048, 0, 3072, 768))]
    assert [len(c['submissions']) for c in cases] == [12, 0, 0, 0, 0]
    assert cases[0]['submissions'][0]['screen_rect'] == [0, 0, 256, 256]
    assert cases[0]['submissions'][-1]['screen_rect'] == [768, 512, 1024, 768]
    colours = [vertex_colours(None), vertex_colours((0xff123456,)),
               vertex_colours((0xff000001, 0xff000002, 0xff000003, 0xff000004))]
    assert colours[0]['native_argb'] == [0xffffffff]*4
    assert colours[1]['native_argb'] == [0xff123456]*4
    assert colours[2]['native_argb'] == [0xff000001, 0xff000002, 0xff000003, 0xff000004]
    result = {'image_sha256': hashlib.sha256(DATA).hexdigest(),
              'native_method': '0x605110', 'cases': cases,
              'native_vertex_colour_cases': colours,
              'scope': 'Original culling/descriptor code; synthetic layer and recording renderer only',
              'live_black_cause_proven': False, 'client_launched': False}
    target = Path(__file__).parent/'evidence/world-ground-native.json'
    target.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({'cases': len(cases), 'colour_cases': len(colours),
                      'submissions': [len(c['submissions']) for c in cases],
                      'all_passed': True, 'client_launched': False}))


def vertex_colours(supplied):
    """Original 0x6d28ac default/per-vertex colour branch, no GPU Adapter."""
    e = Uc(UC_ARCH_X86, UC_MODE_32)
    e.mem_map(BASE, (len(DATA)+4095)&~4095)
    e.mem_write(BASE, DATA)
    e.mem_map(0x5000000, 0x100000)
    descriptor, colours, stack = 0x5001000, 0x5002000, 0x5080000
    if supplied:
        e.mem_write(colours, struct.pack('<'+'I'*len(supplied), *supplied))
    e.mem_write(descriptor+0x14, struct.pack('<II', colours if supplied else 0,
                                          len(supplied) if supplied else 0))
    e.reg_write(UC_X86_REG_EDI, descriptor)
    e.reg_write(UC_X86_REG_ESP, stack)
    e.emu_start(0x6d28ac, 0x6d290a, count=100)
    assert e.reg_read(UC_X86_REG_EIP) == 0x6d290a
    actual = list(struct.unpack('<4I', e.mem_read(stack+0x74, 16)))
    return {'explicit_argb': supplied, 'native_argb': actual}


if __name__ == '__main__':
    main()
