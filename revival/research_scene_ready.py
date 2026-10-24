"""Read-only original scene branch and relocation-response CPU probes.

No process handles, sockets, client files, server state, or accounts are touched.
Only the mapped image is read. Results go to evidence/scene-ready-native-probe.json.
"""
from pathlib import Path
import hashlib
import json
import struct
import sys

sys.path.insert(0, 'D:/Downloads/LCJDTClient/LCJDTClient/revival/.deps')
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_EIP, UC_X86_REG_ESP, UC_X86_REG_EBX
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

ROOT = Path(__file__).parent
IMAGE = ROOT / 'evidence/native-image.bin'
DATA = IMAGE.read_bytes()
BASE = 0x400000
AREA = 0x5000000
STACK = AREA + 0x3f000
STOP = AREA + 0x3fff0
SEND = AREA + 0x3ffe0


class Probe:
    def __init__(self):
        self.u = Uc(UC_ARCH_X86, UC_MODE_32)
        self.u.mem_map(0, 0x1000)
        self.u.mem_map(BASE, (len(DATA) + 0xfff) & ~0xfff)
        self.u.mem_write(BASE, DATA)
        self.u.mem_map(AREA, 0x40000)
        self.u.mem_write(SEND, b'\xc2\x04\x00')
        self.u.mem_write(STOP, b'\xc3')
        self.sent = []
        self.visited = set()
        self.model_position_adapter = False
        self.u.hook_add(UC_HOOK_CODE, self.hook)
        self.client, self.client_vt = AREA + 0x100, AREA + 0x200
        self.w(self.client, self.client_vt)
        self.w(self.client_vt + 0x3c, SEND)
        self.w(0x2945074, self.client)

    def w(self, addr, *values):
        self.u.mem_write(addr, struct.pack('<' + 'I' * len(values), *values))

    def read(self, addr):
        return struct.unpack('<I', self.u.mem_read(addr, 4))[0]

    def ret(self, args=0, value=None):
        sp = self.u.reg_read(UC_X86_REG_ESP)
        dest = self.read(sp)
        if value is not None:
            self.u.reg_write(UC_X86_REG_EAX, value)
        self.u.reg_write(UC_X86_REG_ESP, sp + 4 + args)
        self.u.reg_write(UC_X86_REG_EIP, dest)

    def hook(self, u, addr, size, _):
        self.visited.add(addr)
        sp = u.reg_read(UC_X86_REG_ESP)
        if addr == STOP:
            u.emu_stop()
        elif addr == SEND:
            ptr = self.read(sp + 4)
            self.sent.append(bytes(u.mem_read(ptr, 0x20)))
            self.ret(4, 1)
        elif addr == 0x19191c2:  # CRT memcpy only, original stream codec retained.
            dst, src, count = (self.read(sp + x) for x in (4, 8, 12))
            if count:
                u.mem_write(dst, bytes(u.mem_read(src, count)))
            self.ret(value=dst)
        elif addr == 0x1919184:  # Process-specific security cookie check.
            self.ret()
        elif addr == 0x12061a0 and self.model_position_adapter:
            # Model-renderer boundary only; not a replay of the engine/rendering.
            actor = u.reg_read(UC_X86_REG_ECX)
            out = self.read(sp + 4)
            self.w(out, self.read(actor + 0x1b8), self.read(actor + 0x1bc))
            self.ret(4, out)

    def run(self, addr, obj=0, args=()):
        self.w(STACK, STOP, *args)
        self.u.reg_write(UC_X86_REG_ESP, STACK)
        self.u.reg_write(UC_X86_REG_ECX, obj)
        self.u.emu_start(addr, STOP, count=200000)
        assert self.u.reg_read(UC_X86_REG_EIP) == STOP

    def marshal(self, method, obj):
        stream, buf = AREA + 0x1000, AREA + 0x2000
        self.w(stream, 0x224c100, buf, 0)
        self.w(buf - 12, 0x1000, 0, 1)
        self.run(method, obj, (stream,))
        return bytes(self.u.mem_read(buf, self.read(buf - 8)))


def first_reason_gate(reason):
    p = Probe()
    p.w(STACK + 0xb0, reason)
    p.u.reg_write(UC_X86_REG_ESP, STACK)
    p.u.reg_write(UC_X86_REG_EBX, 0)
    p.u.emu_start(0x11e2d00, 0x11e2d39, count=1000)
    assert p.u.reg_read(UC_X86_REG_EIP) == 0x11e2d39
    return {'reason': reason, 'sent_types': [struct.unpack_from('<I', x, 4)[0] for x in p.sent]}


def relocation_response(state, flag, scene_id=0x1122334455667788, x=8480, y=6976):
    p = Probe()
    actor, scene, query = AREA + 0x4000, AREA + 0x5000, AREA + 0x6000
    p.w(0x294454c, actor)
    p.w(0x2944564, scene)
    p.w(actor, 0x2299344)
    p.w(actor + 0x13c, state)
    p.w(actor + 0x1b8, x, y)
    p.w(actor + 0x150, x, y)  # state1 position fields
    p.w(actor + 0x158, x, y)  # state2 position fields
    p.u.mem_write(actor + 0x218, bytes([flag]))
    p.u.mem_write(actor + 0x3d6, bytes([flag]))
    p.w(scene + 0x30, scene_id & 0xffffffff, scene_id >> 32)
    p.run(0xdabe80, query)
    assert p.read(query + 4) == 0xc0fbb
    assert p.marshal(0xdabea0, query) == b''
    p.model_position_adapter = state == 0
    p.run(0x11c9f90, query, (0, 0))
    assert len(p.sent) == 1
    snapshot = p.sent[0]
    assert struct.unpack_from('<I', snapshot, 4)[0] == 0xc0faf
    obj = AREA + 0x7000
    p.u.mem_write(obj, snapshot)
    payload = p.marshal(0xe50770, obj)
    expected = struct.pack('>QHHB', scene_id, x & 0xffff, y & 0xffff, int(flag != 0))
    assert payload == expected
    # Original response decoder; verifies complete consumption and field widths.
    stream, buf, decoded = AREA + 0x1000, AREA + 0x2000, AREA + 0x8000
    p.w(stream, 0x224c100, buf, 0)
    p.w(buf - 12, 0x1000, len(payload), 1)
    p.u.mem_write(buf, payload)
    p.w(decoded, 0x2278f20, 0xc0faf)
    p.w(decoded + 0x10, 0x2278e54)
    p.run(0xdaa7a0, decoded, (stream,))
    assert p.read(stream + 8) == 13
    return {'state': state, 'flag_input': flag, 'scene_id': scene_id,
            'payload_hex': payload.hex(), 'payload_size': len(payload),
            'decoded_scene': struct.unpack('<Q', p.u.mem_read(decoded + 8, 8))[0],
            'decoded_position_u16': list(struct.unpack('<HH', p.u.mem_read(decoded + 0x14, 4))),
            'decoded_flag': p.u.mem_read(decoded + 0x18, 1)[0],
            'consumed': p.read(stream + 8),
            'native_handler_and_response_builder_visited': all(a in p.visited for a in (0x11c9f90, 0x1212890)),
            'model_position_getter_adapter': p.model_position_adapter}


def main():
    result = {'image_sha256': hashlib.sha256(DATA).hexdigest(),
              'scope': 'Offline original branch/codec execution; no renderer or live FIFO test.',
              'reason_gate': [first_reason_gate(n) for n in (0, 516015)],
              'relocation_response': [relocation_response(s, f) for s in (0, 1, 2) for f in (0, 1, 2)]}
    out = ROOT / 'evidence/scene-ready-native-probe.json'
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    spans = [(0xdabe80, 0x40), (0xe50770, 0x50), (0xe50690, 0x88),
             (0x11c9f90, 0x12), (0x1212890, 0x1df), (0x11e225b, 0x15),
             (0x11e25ee, 0x40), (0x11e269b, 0x50), (0x11e2d00, 0x39),
             (0x11e3140, 0x75), (0x77c987, 0xa2), (0x7710d0, 0x11),
             (0x775f89, 0x16)]
    lines = []
    for address, length in spans:
        lines.append('\n# ' + hex(address))
        lines.extend(f'{i.address:08x}: {i.mnemonic:8} {i.op_str}' for i in md.disasm(DATA[address-BASE:address-BASE+length], address))
    (ROOT / 'evidence/scene-ready-native-disassembly.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(json.dumps({'gate': result['reason_gate'], 'response_cases': len(result['relocation_response']), 'all_passed': True, 'evidence': str(out)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
