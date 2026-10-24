"""Reproduce task wire evidence from the original mapped client image."""
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import re
import struct

from native_inspect import DATA, BASE, capstone, disasm, refs, u32, vtables

OUT = Path(__file__).parent / 'evidence'
FUNCTIONS = {
    'commit_ctor_decode': (0xdd4780, 0x192),
    'accept_ctor': (0xdd8570, 0x30),
    'quest_info_marshal': (0xe57b10, 0x10e),
    'quest_info_decode': (0xdd86e0, 0x114),
    'accept_decode': (0xdd8820, 0x48),
    'accept_process': (0x125d5c0, 0x27),
    'state_ctor': (0xddbae0, 0x18),
    'state_decode': (0xddbb80, 0xb4),
    'state_process': (0x125ea00, 0x20),
    'state_scenario_update': (0x125c020, 0x3d0),
    'value_ctor': (0xddbca0, 0x1b),
    'value_decode': (0xddbd40, 0xef),
    'value_process': (0x1258c90, 0x36),
    'can_accept_ctor': (0xe72770, 0x66),
    'can_accept_marshal': (0xe72810, 0x5d),
    'can_accept_decode': (0xe72870, 0x5e),
    'can_accept_container_factory': (0x82d360, 0x1b),
    'can_accept_list_marshal': (0x82db40, 0x170),
    'can_accept_list_decode': (0x82e0e0, 0x130),
    'npc_key_use': (0x125d124, 0x18),
    'npc_refresh': (0x125a950, 0xc0),
    'client_quest_status': (0x1257b20, 0x72),
    'ui_commit_send': (0x16433e9, 0x43),
    'track_ctor': (0xdd8140, 0x32),
    'track_decode': (0xdd81f0, 0xa9),
    'dialog_end_ctor_decode': (0xdd6430, 0xeb),
    'reach_scene_ctor_decode': (0xdd6580, 0x36),
    'tracked_ctor': (0xfa87d0, 0x7b),
    'tracked_map_factory': (0xfa8b40, 0x1b),
    'tracked_map_marshal': (0xfa8ec0, 0x170),
    'tracked_bean_marshal': (0xfa8c70, 0x1a),
    'tracked_bean_decode': (0xfa8a60, 0x1a),
    'track_reply_ctor': (0xddd2b0, 0x18),
    'track_reply_marshal': (0xe586d0, 0x44),
    'visit_npc_ctor': (0xdb3450, 0x18),
    'visit_npc_marshal': (0xe52020, 0x37),
    'npc_service_ctor': (0x837400, 0x27),
    'npc_service_marshal': (0x83b5a0, 0x27),
}


def native_scalar_probe():
    """Three representative payloads through original scalar decoders only."""
    from unicorn import Uc, UC_ARCH_X86, UC_MODE_32
    from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_ESP, UC_X86_REG_EIP
    cases = [
        ('accept', 0xdd8820, struct.pack('>iiiiQ', 100184, 2, 11, 22, 0x1122334455667788)),
        ('state', 0xddbb80, struct.pack('>ii', 100184, 3)),
        ('values', 0xddbd40, struct.pack('>iii', 100184, 11, 22)),
    ]
    results = []
    for name, decoder, payload in cases:
        emu = Uc(UC_ARCH_X86, UC_MODE_32)
        emu.mem_map(BASE, (len(DATA)+0xfff)&~0xfff)
        emu.mem_write(BASE, DATA)
        emu.mem_map(0x5000000, 0x20000)
        obj, stream, buf, stack, stop = 0x5001000, 0x5002000, 0x5003000, 0x5010000, 0x500f000
        def w(addr, *values): emu.mem_write(addr, struct.pack('<'+'I'*len(values), *values))
        w(obj+8, 0x227df68)
        w(stream, 0x224c100, buf, 0)
        w(buf-12, len(payload), len(payload), 1)
        emu.mem_write(buf, payload)
        w(stack, stop, stream)
        emu.reg_write(UC_X86_REG_ECX, obj)
        emu.reg_write(UC_X86_REG_ESP, stack)
        emu.emu_start(decoder, stop, count=10000)
        consumed = struct.unpack('<I', emu.mem_read(stream+8, 4))[0]
        completed = emu.reg_read(UC_X86_REG_EIP) == stop
        assert completed and consumed == len(payload)
        decoded = (struct.unpack('<iiii', emu.mem_read(obj+12, 16)) +
                   struct.unpack('<Q', emu.mem_read(obj+32, 8))) if name == 'accept' else struct.unpack('<'+'i'*(len(payload)//4), emu.mem_read(obj+8, len(payload)))
        assert decoded == struct.unpack('>iiiiQ' if name == 'accept' else '>'+'i'*(len(payload)//4), payload)
        results.append(dict(name=name, decoder=hex(decoder), payload_hex=payload.hex(),
                            consumed=consumed, completed=completed, decoded=decoded))
    return results


def catalog():
    c = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    result = []
    for m in re.finditer(rb'\.\?AV[^\0]+@task@gsp@knight@@\0', DATA):
        name = m.group()[:-1].decode('ascii')
        if '@@' not in name or 'Table@' in name or '?$' in name:
            continue
        for vt in vtables(name):
            kind = None
            evidence = None
            for ref in refs(vt):
                # RTTI-vtable reference points at mov immediate; decode immediately after it.
                for ins in c.disasm(DATA[ref-BASE+4:ref-BASE+44], ref+4):
                    if ins.mnemonic == 'mov' and re.fullmatch(r'dword ptr \[[a-z]+ \+ 4\], 0x[cC][0-9a-fA-F]{4}', ins.op_str):
                        kind = int(ins.op_str.rsplit(' ', 1)[-1], 16)
                        evidence = hex(ins.address)
                        break
                if kind is not None:
                    break
            if kind is not None:
                result.append(dict(name=name, type=kind, type_hex=hex(kind),
                                   type_write=evidence, vtable=hex(vt),
                                   marshal=hex(u32(vt)), unmarshal=hex(u32(vt+4)),
                                   process=hex(u32(vt+24))))
    return result


if __name__ == '__main__':
    output = io.StringIO()
    with redirect_stdout(output):
        for name, (address, size) in FUNCTIONS.items():
            print('\n###', name, hex(address))
            disasm(address, size)
    (OUT/'task-native-disassembly.txt').write_text(output.getvalue(), encoding='utf-8')
    report = {'source': 'native-image.bin', 'sha256': hashlib.sha256(DATA).hexdigest(),
              'method': 'Original RTTI, constructor type writes, marshal/unmarshal and handler tracing.',
              'protocols': catalog(), 'native_scalar_probes': native_scalar_probe()}
    (OUT/'task-protocol-evidence.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'protocols': len(report['protocols']), 'native_scalar_probes': report['native_scalar_probes']}, indent=2))
