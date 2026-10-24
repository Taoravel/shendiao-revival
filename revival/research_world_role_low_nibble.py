"""Narrow offline xref audit and original CCharacter getter execution.

Does not change production code, policies, files outside its evidence outputs,
or inspect/start any client process. Candidate scans do not establish receiver
types and do not claim that dynamic/packed call sites are absent.
"""
import hashlib
import json
import re
import struct
from pathlib import Path
from native_inspect import DATA, BASE, u32, refs
import capstone
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_ESP

OUT = Path(__file__).parent / 'evidence'
TEXT_START, TEXT_END = 0x401000, 0x2243781
GETTER = 0x1209d80


def direct_branches(target):
    result = []
    for opcode, name in ((b'\xe8', 'call_rel32'), (b'\xe9', 'jmp_rel32')):
        offset = TEXT_START - BASE
        while True:
            offset = DATA.find(opcode, offset, TEXT_END - BASE)
            if offset < 0:
                break
            destination = BASE + offset + 5 + struct.unpack_from('<i', DATA, offset + 1)[0]
            if destination == target:
                result.append({'address': hex(BASE + offset), 'kind': name})
            offset += 1
    return result


def virtual_slot_candidates():
    """Decode exact disp32 candidates; capture loaded-register calls within 35B.

    Byte scanning intentionally over-approximates instruction starts. Receiver
    identity and instruction alignment must be checked at the actual function.
    """
    cs = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    cs.detail = True
    found = {}
    code = DATA[TEXT_START - BASE:TEXT_END - BASE]
    for match in re.finditer(re.escape(struct.pack('<I', 0x19c)), code):
        at = match.start() + TEXT_START - BASE
        for start in range(max(TEXT_START - BASE, at - 10), at - 1):
            ins = next(cs.disasm(DATA[start:start + 15], BASE + start, count=1), None)
            if ins is None or not any(o.type == capstone.x86_const.X86_OP_MEM
                    and o.mem.disp == 0x19c
                    and o.mem.base not in (capstone.x86_const.X86_REG_ESP,
                                           capstone.x86_const.X86_REG_EBP)
                    for o in ins.operands):
                continue
            candidate = None
            if ins.mnemonic in ('call', 'jmp'):
                candidate = ins
            elif ins.mnemonic == 'mov' and ins.operands[0].type == capstone.x86_const.X86_OP_REG:
                reg = ins.operands[0].reg
                for following in cs.disasm(DATA[start + ins.size:start + ins.size + 35],
                                           ins.address + ins.size):
                    if following.mnemonic in ('call', 'jmp') and following.operands[0].type == 1 and following.operands[0].reg == reg:
                        candidate = following
                        break
                    if following.operands and following.operands[0].type == 1 and following.operands[0].reg == reg:
                        break
            if candidate:
                found[ins.address] = {'slot_load': hex(ins.address),
                    'instruction': ins.mnemonic + ' ' + ins.op_str,
                    'branch': hex(candidate.address), 'receiver_type': 'unresolved_candidate'}
    return list(v for _, v in sorted(found.items()))


def original_getter(value):
    # No imports or game methods are adapted. Only original-image and synthetic
    # object/stack memory are mapped; the return address is the emulation stop.
    uc = Uc(UC_ARCH_X86, UC_MODE_32)
    uc.mem_map(BASE, (len(DATA) + 4095) & ~4095)
    uc.mem_write(BASE, DATA)
    obj, stack, stop = 0x5000000, 0x5001000, 0x5002000
    uc.mem_map(obj, 0x3000)
    uc.mem_write(obj, struct.pack('<I', 0x2298bcc))
    uc.mem_write(obj + 0x1a8, struct.pack('<I', value))
    uc.mem_write(stack, struct.pack('<I', stop))
    uc.reg_write(UC_X86_REG_ECX, obj)
    uc.reg_write(UC_X86_REG_ESP, stack)
    uc.emu_start(GETTER, stop, count=8)
    result = uc.reg_read(UC_X86_REG_EAX)
    assert result == value
    assert uc.reg_read(UC_X86_REG_ESP) == stack + 4
    return {'stored_player_1a8': value, 'original_getter_result': result,
            'imports_adapted': False, 'game_dependencies_stubbed': False}


def main():
    slot_rows = []
    for name, table in (('CCharacter', 0x2298bcc), ('CMainCharacter', 0x2299344)):
        assert u32(table + 0x19c) == GETTER
        slot_rows.append({'class': name, 'vtable': hex(table), 'slot': '0x19c',
                          'method': hex(GETTER)})
    result = {'image_sha256': hashlib.sha256(DATA).hexdigest(),
              'scope': 'original .text static candidate audit and native getter only',
              'text_range': [hex(TEXT_START), hex(TEXT_END)],
              'vtable_slots': slot_rows,
              'absolute_getter_refs': [hex(a) for a in refs(GETTER)],
              'direct_rel32_calls_jumps': direct_branches(GETTER),
              'slot_call_candidates': virtual_slot_candidates(),
              'native_getter_cases': [original_getter(n) for n in (10, 11, 25, 111)],
              'limits': ['Candidate receiver types require manual classification.',
                         'No vmp/compat sections, computed slots, short/indirect branches or external DLLs audited.',
                         '111 is a synthetic stored value, not a value encodable by the low nibble.',
                         'No new wire default or school mapping is selected.']}
    path = OUT / 'world-role-low-nibble-audit.json'
    path.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({'native_getter_cases_passed': len(result['native_getter_cases']),
        'direct_getter_branches': result['direct_rel32_calls_jumps'],
        'slot_call_candidate_count': len(result['slot_call_candidates']), 'output': str(path)}))


if __name__ == '__main__':
    main()
