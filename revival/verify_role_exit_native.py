"""Offline original x86 exit-menu gate; every UI/OS endpoint is intercepted.

No process, window, network, service, account or real role is accessed.
"""
import hashlib
import json
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from native_gameplay_probe import probe
from native_inspect import DATA
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_ESP, UC_X86_REG_EIP


def case(value):
    result = {'wire_signed_i32': value}

    def observe(emu, target):
        stack, stop, state = 0x5100000, 0x500f000, 0x5005000
        seen = []

        def r(addr):
            return struct.unpack('<I', emu.mem_read(addr, 4))[0]

        def w(addr, *values):
            emu.mem_write(addr, struct.pack('<' + 'I' * len(values), *values))

        def host(uc, addr, size, _):
            if addr in (0x15f5410, 0x15f6190):
                seen.append('ordinary_exit_dialog' if addr == 0x15f5410 else 'first_day_exit_dialog')
                sp = uc.reg_read(UC_X86_REG_ESP)
                uc.reg_write(UC_X86_REG_EIP, r(sp))
                uc.reg_write(UC_X86_REG_ESP, sp + 4)
                uc.reg_write(UC_X86_REG_EAX, 0)

        emu.hook_add(UC_HOOK_CODE, host)

        def run(addr, *, ecx=0, args=()):
            w(stack, stop, *args)
            emu.reg_write(UC_X86_REG_ECX, ecx)
            emu.reg_write(UC_X86_REG_ESP, stack)
            emu.emu_start(addr, stop, count=5000)
            assert emu.reg_read(UC_X86_REG_EIP) == stop

        # Trusted offline world-state fixture. Native WM_CLOSE branching remains
        # unchanged. A null battle manager selects the original nonbattle arm.
        w(0x2945540, state)
        w(state + 4, 2)
        w(0x2944798, 0)
        run(0x15f5230)  # Original application-reset callee: mode=-1.
        assert r(0x28e6bc8) == 0xffffffff
        run(0x822490, args=(0x1234, 0x10, 0, 0))  # Actual installed WndProc.
        assert seen == [], 'Reset WM_CLOSE must reproduce no confirmation window'
        result['before_initialization'] = {'mode': -1, 'ui_calls': list(seen), 'wndproc_return': emu.reg_read(UC_X86_REG_EAX)}
        run(0x15f5500, ecx=target, args=(0, 0))  # Actual decoded message handler.
        expected = int(value >= 0)
        assert r(0x28e6bc8) == expected
        run(0x822490, args=(0x1234, 0x10, 0, 0))
        selected = 'first_day_exit_dialog' if expected else 'ordinary_exit_dialog'
        assert seen == [selected]
        result['after_native_decode_and_process'] = {'mode': expected, 'ui_calls': list(seen), 'wndproc_return': emu.reg_read(UC_X86_REG_EAX)}

    wire, decoded = probe(0xd53a00, 0xe40a00, 0xd53a90,
                          fields={8: struct.pack('<i', value)}, observer=observe)
    assert wire == struct.pack('>i', value)
    assert struct.unpack_from('<I', decoded, 4)[0] == 0xc0039
    assert struct.unpack_from('<i', decoded, 8)[0] == value
    result['type'] = '0xc0039'
    result['wire_hex'] = wire.hex()
    return result


def main():
    cases = [case(value) for value in (-1, -2147483648, 0, 1, 2147483647)]
    doc = {
        'date': '2026-10-23',
        'native_image_sha256': hashlib.sha256(DATA).hexdigest(),
        'original_functions': {'reset': '0x15f5230', 'constructor': '0xd53a00', 'marshal': '0xe40a00',
                               'unmarshal': '0xd53a90', 'process': '0x15f5500', 'installed_wndproc': '0x822490'},
        'cases': cases,
        'scope': 'Original reset, wire codec, SFirstDayExitGame Process and installed WM_CLOSE WndProc execute offline; UI creation endpoints only record calls and return; world state2/null battle manager are explicit fixtures.',
        'not_verified': ['real GUI/resource rendering', 'actual client state', 'server delivery or deployment', 'original first-day business policy', 'battle exit branch'],
        'no_live_client_or_os_window_calls': True,
    }
    out = Path(__file__).parent / 'evidence/role-exit-native-reaudit-check.json'
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'cases': len(cases), 'pass': True, 'output': str(out)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
