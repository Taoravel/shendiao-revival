"""Offline cart branch evidence: execute original menu index/commit instructions.

No live process, socket, account database, or production module is opened.
The optional --expect-first-option 1 deliberately catches a one-based assumption.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from native_inspect import BASE, DATA
from pfs import PfsArchive
from bxml import decode
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_ESI, UC_X86_REG_EBP, UC_X86_REG_ESP, UC_X86_REG_EIP


ROOT = Path(__file__).parent.parent
TASK_IDS = (100104, 100203, 100303, 100403, 100503, 100603, 100703, 100803, 100903, 103204)


def machine():
    emu = Uc(UC_ARCH_X86, UC_MODE_32)
    emu.mem_map(BASE, (len(DATA) + 4095) & ~4095)
    emu.mem_write(BASE, DATA)
    emu.mem_map(0x5000000, 0x10000)
    return emu


def write32(emu, addr, *values):
    emu.mem_write(addr, struct.pack('<' + 'I' * len(values), *values))


def read32(emu, addr):
    return struct.unpack('<I', emu.mem_read(addr, 4))[0]


def original_menu_index(index):
    """Original instructions store loop index into the clickable item's data."""
    emu = machine()
    stack, item = 0x500f000, 0x5002000
    write32(emu, stack + 0x14, index)
    emu.reg_write(UC_X86_REG_ESP, stack)
    emu.reg_write(UC_X86_REG_EBP, item)
    emu.reg_write(UC_X86_REG_ESI, 0)
    emu.emu_start(0x164b8b5, 0x164b8bf, count=5)
    assert emu.reg_read(UC_X86_REG_EIP) == 0x164b8bf
    return read32(emu, item + 0x30), read32(emu, item + 0x34)


def original_branch_commit(choice, quest_id=100104, npc_key=0x1122334455667788):
    """Run original phase5 sender; adapt only network lookup/send and stop cleanup."""
    emu = machine()
    stack, ui, network, vtable, send_stub = 0x500f000, 0x5001000, 0x5003000, 0x5004000, 0x5000500
    write32(emu, ui + 0x38, npc_key & 0xffffffff, npc_key >> 32)
    write32(emu, ui + 0x48, quest_id)
    write32(emu, stack + 0x3c, choice)
    write32(emu, network, vtable)
    write32(emu, vtable + 0x3c, send_stub)
    sent = []

    def ret(uc, value, cleanup):
        sp = uc.reg_read(UC_X86_REG_ESP)
        target = read32(uc, sp)
        uc.reg_write(UC_X86_REG_EAX, value)
        uc.reg_write(UC_X86_REG_ESP, sp + 4 + cleanup)
        uc.reg_write(UC_X86_REG_EIP, target)

    def hook(uc, addr, size, _):
        if addr in (0x1649037, 0x164903f):
            uc.emu_stop()
        elif addr == 0x813860:
            ret(uc, network, 0)
        elif addr == send_stub:
            packet = read32(uc, uc.reg_read(UC_X86_REG_ESP) + 4)
            sent.append({
                'type': read32(uc, packet + 4),
                'quest_id': read32(uc, packet + 8),
                'npc_key': read32(uc, packet + 0x10) | read32(uc, packet + 0x14) << 32,
                'choice': read32(uc, packet + 0x18),
            })
            ret(uc, 0, 4)

    emu.hook_add(UC_HOOK_CODE, hook)
    emu.reg_write(UC_X86_REG_ESP, stack)
    emu.reg_write(UC_X86_REG_ESI, ui)
    emu.reg_write(UC_X86_REG_EAX, 5)
    emu.emu_start(0x1648e88, 0x164904a, count=100)
    assert emu.reg_read(UC_X86_REG_EIP) in (0x1649037, 0x164903f)
    return sent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--expect-first-option', type=int, default=0)
    args = parser.parse_args()
    archive = PfsArchive(ROOT / 'artres/config.pfs')
    raw = archive.read('autoconfig/knight.gsp.task.cmainmissioninfo.xml')
    records = {int(row.get('id')): row for row in decode(raw)}
    rows = []
    for task_id in TASK_IDS:
        row = records[task_id]
        options = [child.text for child in row.find('ScenarioInfoBranchOptionList')]
        assert len(options) == 1 and row.get('MissionType') == '10'
        assert len(row.find('ScenarioInfoNpcConversationList')) == 2
        assert row.get('RewardMapJumpType') == '1' and row.get('RewardMapID') == '1006'
        actual, high = original_menu_index(0)
        assert (actual, high) == (args.expect_first_option, 0), f'first option is {actual}, expected {args.expect_first_option}'
        packet, = original_branch_commit(actual, task_id)
        assert packet == {'type': 0xc4a44, 'quest_id': task_id, 'npc_key': 0x1122334455667788, 'choice': 0}
        rows.append({'id': task_id, 'active_npc': int(row.get('ActiveInfoNpcID')), 'branch_npc': int(row.get('ScenarioInfoBranchNpcID')), 'options': options, 'native_choice': packet['choice']})
    assert original_menu_index(1) == (1, 0)
    packet, = original_branch_commit(1)
    assert packet['choice'] == 1
    assert original_branch_commit(10003) == []
    print(json.dumps({'native_image_sha256': hashlib.sha256(DATA).hexdigest(), 'config_entry_sha256': hashlib.sha256(raw).hexdigest(), 'rows': rows, 'synthetic_second_choice_preserved': True, 'reserved_10003_sends_commit': False, 'scope': 'original menu-index store and phase5 packet construction; network calls adapted; no GUI or online state'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
