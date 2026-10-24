"""Execute shipped movement serializers; no alternate game's protocol involved."""
import contextlib
import hashlib
import io
import json
import struct
from native_inspect import BASE, DATA, disasm, u32
from inspect_client import OUT, write_json
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_EAX


def native_packet(kind, start=(8480, 6976), end=(8496, 6992), path=()):
    uc = Uc(UC_ARCH_X86, UC_MODE_32)
    uc.mem_map(0, 0x1000)
    uc.mem_map(BASE, (len(DATA)+4095)&~4095)
    uc.mem_write(BASE, DATA)
    uc.mem_map(0x5000000, 0x200000)
    obj, stream, buf, head, stack, stop = 0x5001000, 0x5002000, 0x5003000, 0x5005000, 0x5100000, 0x500f000
    def w(addr, *values): uc.mem_write(addr, struct.pack('<'+'I'*len(values), *values))
    def read(addr): return struct.unpack('<I', uc.mem_read(addr, 4))[0]
    def pos(addr, value):
        w(addr, 0x2278e54)
        uc.mem_write(addr+4, struct.pack('<hh', *value))
    functions = {0xc0fa1: 0xe50840, 0xc0fa3: 0xe9cd00, 0xc0faa: 0xe9d6d0}
    w(obj+4, kind)
    if kind == 0xc0fa1:
        pos(obj+8, start); pos(obj+16, end)
        w(obj+24, 0x55667788, 0x11223344)
    else:
        list_addr = obj+(16 if kind == 0xc0fa3 else 8)
        w(list_addr+4, head); w(list_addr+8, len(path))
        nodes = [head+0x40+i*0x20 for i in range(len(path))]
        w(head, nodes[0] if nodes else head, nodes[-1] if nodes else head)
        for i, node in enumerate(nodes):
            w(node, nodes[i+1] if i+1<len(nodes) else head, nodes[i-1] if i else head)
            pos(node+8, path[i])
        pos(obj+(8 if kind == 0xc0fa3 else 20), end)
        w(obj+32, 0x55667788, 0x11223344)
    w(stream, 0x224c100, buf, 0); w(buf-12, 0x1000, 0, 1)
    w(stack, stop, stream)
    def ret():
        sp = uc.reg_read(UC_X86_REG_ESP)
        uc.reg_write(UC_X86_REG_EIP, read(sp)); uc.reg_write(UC_X86_REG_ESP, sp+4)
    def hook(_, addr, size, user):
        if addr == stop: uc.emu_stop()
        elif addr == 0x1919184: ret()  # process-specific security cookie only
        elif addr == 0x19191c2:
            sp = uc.reg_read(UC_X86_REG_ESP)
            dst, src, count = read(sp+4), read(sp+8), read(sp+12)
            if count: uc.mem_write(dst, bytes(uc.mem_read(src, count)))
            uc.reg_write(UC_X86_REG_EAX, dst); ret()
    uc.hook_add(UC_HOOK_CODE, hook)
    uc.reg_write(UC_X86_REG_ECX, obj); uc.reg_write(UC_X86_REG_ESP, stack)
    uc.emu_start(functions[kind], stop, count=200000)
    assert uc.reg_read(UC_X86_REG_EIP) == stop
    return bytes(uc.mem_read(buf, read(buf-8)))


def main():
    fixtures = []
    for kind in (0xc0fa1, 0xc0fa3, 0xc0faa):
        for path in ((), ((8480, 6976), (8496, 6992))) if kind != 0xc0fa1 else ((),):
            body = native_packet(kind, path=path)
            fixtures.append({'type': kind, 'path': path, 'body_hex': body.hex()})
    write_json(OUT/'evidence/movement-native-fixtures.json', {
        'image_sha256': hashlib.sha256(DATA).hexdigest(), 'fixtures': fixtures,
        'scope': 'original serializers executed; does not verify live client movement'})
    capture = io.StringIO()
    with contextlib.redirect_stdout(capture):
        for addr, size in ((0xdaac30, 0x43), (0xe50840, 0x34), (0xe50690, 0xa0),
                           (0xe9cd00, 0x99), (0xe9ce50, 0xcd), (0xe9d6d0, 0xa9),
                           (0x12160b0, 0x8d), (0xe9d615, 0x30)):
            print('RANGE', hex(addr)); disasm(addr, size)
    (OUT/'evidence/movement-disassembly.txt').write_text(capture.getvalue(), encoding='utf-8')
    print(json.dumps(fixtures))


if __name__ == '__main__': main()
