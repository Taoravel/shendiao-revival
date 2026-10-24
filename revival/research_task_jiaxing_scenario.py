"""Offline original 60001 display branches; resource load/UI/network are captured.

No live process, server, socket, role database or production module is accessed.
"""
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
TASKS = (100105, 100204, 100304, 100404, 100504, 100604, 100704, 100804, 100904, 103205)


class Probe:
    def __init__(self, quest_id):
        self.e = Uc(UC_ARCH_X86, UC_MODE_32)
        self.e.mem_map(BASE, (len(DATA) + 4095) & ~4095)
        self.e.mem_write(BASE, DATA)
        self.e.mem_map(0x5000000, 0x20000)
        self.stack, self.ui, self.task, self.effect, self.manager, self.scene = 0x501f000, 0x5001000, 0x5002000, 0x5003000, 0x5004000, 0x5005000
        self.factory, self.factory_vt, self.engine, self.engine_vt, self.net, self.net_vt = 0x5006000, 0x5006100, 0x5007000, 0x5007100, 0x5008000, 0x5008100
        self.quest_id = quest_id
        self.calls = []
        self.w(self.task, quest_id)
        self.w(self.task + 0x2ac, 60001)
        self.w(self.effect, 60001)
        self.w(self.factory, self.factory_vt)
        self.w(self.factory_vt + 8, 0x5000200)
        self.w(self.engine, self.engine_vt)
        self.w(self.engine_vt + 0x120, 0x5000300)
        self.w(self.net, self.net_vt)
        self.w(self.net_vt + 0x3c, 0x5000400)
        self.w(0x2945584, self.manager)
        self.w(0x2944564, self.scene)
        self.e.hook_add(UC_HOOK_CODE, self.hook)

    def w(self, addr, *values):
        self.e.mem_write(addr, struct.pack('<' + 'I' * len(values), *values))

    def r(self, addr):
        return struct.unpack('<I', self.e.mem_read(addr, 4))[0]

    def ret(self, value=0, cleanup=0):
        sp = self.e.reg_read(UC_X86_REG_ESP)
        target = self.r(sp)
        self.e.reg_write(UC_X86_REG_EAX, value)
        self.e.reg_write(UC_X86_REG_ESP, sp + 4 + cleanup)
        self.e.reg_write(UC_X86_REG_EIP, target)

    def hook(self, emu, addr, size, _):
        sp = emu.reg_read(UC_X86_REG_ESP)
        if addr in (0x89ebd0, 0x89ec50):
            self.ret(self.factory)
        elif addr == 0x5000200:
            record_id = self.r(sp + 4)
            assert record_id in (self.quest_id, 60001)
            if record_id == 60001:
                self.calls.append({'quest_effect_lookup': 60001})
            self.ret(self.effect if record_id == 60001 else self.task, 4)
        elif addr == 0x5a6660:
            self.ret(self.engine)
        elif addr == 0x5000300:
            assert self.r(sp + 4) == self.effect + 4
            assert self.r(sp + 8) == 0
            self.calls.append({'engine_effect_load': 'CQuestEffect[60001].Path', 'flag': 0})
            # Deliberately stop at engine/resource boundary: no GPU load.
            self.ret(0, 8)
        elif addr == 0x11d1870:
            self.ret(0, 4)
        elif addr == 0x813860:
            self.ret(self.net)
        elif addr == 0x5000400:
            packet = self.r(sp + 4)
            kind = self.r(packet + 4)
            item = {'sent_type': hex(kind), 'quest_id': self.r(packet + 8)}
            if kind == 0xc4a44:
                item.update(npc_key=self.r(packet + 0x10) | self.r(packet + 0x14) << 32, option=self.r(packet + 0x18))
            self.calls.append(item)
            self.ret(0, 4)

    def span(self, start, end):
        self.e.reg_write(UC_X86_REG_ESP, self.stack)
        self.e.emu_start(start, end, count=600)
        assert self.e.reg_read(UC_X86_REG_EIP) == end
        return self.calls


def state1_display(task_id):
    p = Probe(task_id)
    p.e.reg_write(UC_X86_REG_ESI, p.task)
    p.e.reg_write(UC_X86_REG_EBP, p.manager)
    calls = p.span(0x125c168, 0x125c1cd)
    assert calls == [{'quest_effect_lookup': 60001}, {'engine_effect_load': 'CQuestEffect[60001].Path', 'flag': 0}], calls
    return calls


def dialogue_stage(stage):
    p = Probe(100105)
    p.w(p.ui + 0x44, 100105, 0)
    p.w(p.ui + 0x60, stage)
    p.e.reg_write(UC_X86_REG_ESI, p.ui)
    calls = p.span(0x1644c1a, 0x1644cf8)
    expected = [] if stage == 2 else [{'quest_effect_lookup': 60001}, {'engine_effect_load': 'CQuestEffect[60001].Path', 'flag': 0}, {'sent_type': '0xc4a52', 'quest_id': 100105}]
    assert calls == expected, calls
    return calls


def absent_bean_repeat():
    """State1's no-active-bean arm still invokes the same effect fallback."""
    p = Probe(100105)
    p.e.reg_write(UC_X86_REG_ESI, p.task)
    p.e.reg_write(UC_X86_REG_EBP, p.manager)
    p.span(0x125c058, 0x125c0db)
    p.e.reg_write(UC_X86_REG_ESI, p.task)
    p.span(0x125c058, 0x125c0db)
    expected = [{'quest_effect_lookup': 60001}, {'engine_effect_load': 'CQuestEffect[60001].Path', 'flag': 0}] * 2
    assert p.calls == expected, p.calls
    return p.calls


def ordinary_commit():
    p = Probe(100105)
    p.w(p.ui + 0x48, 100105)
    p.w(p.ui + 0x38, 0x55667788, 0x11223344)
    p.e.reg_write(UC_X86_REG_ESI, p.ui)
    p.e.reg_write(UC_X86_REG_ECX, 0)
    calls = p.span(0x16433e9, 0x164342c)
    assert calls == [{'sent_type': '0xc4a44', 'quest_id': 100105, 'npc_key': 0x1122334455667788, 'option': 0}], calls
    return calls


def main():
    pfs = PfsArchive(ROOT / 'artres/config.pfs')
    raw = pfs.read('autoconfig/knight.gsp.task.cmainmissioninfo.xml')
    rows = {int(row.get('id')): row for row in decode(raw)}
    effect_raw = pfs.read('autoconfig/knight.gsp.task.cquesteffect.xml')
    effects = {int(row.get('id')): row for row in decode(effect_raw)}
    assert effects[60001].get('Path') == 'geffect/chapters/xuzhangyuanqi'
    asset = PfsArchive(ROOT / 'artres/effect.pfs').read('geffect/chapters/xuzhangyuanqi.efct.xml')
    effect = decode(asset)
    assert effect.get('total_frames') == '61' and effect.get('fps') == '8.000000'
    cases = []
    for task_id in TASKS:
        row = rows[task_id]
        assert row.get('MissionType') == '10' and row.get('ScenarioInfoAnimationID') == '60001'
        assert row.get('RewardMapJumpType') == '0' and row.get('ActiveInfoMapID') == '1006'
        assert len(row.find('ScenarioInfoNpcConversationList')) == 3
        assert row.find('ScenarioInfoFinishConversationList') is None and not row.get('NoteInfo') and not row.get('ScenarioInfoBranchNote')
        cases.append({'quest_id': task_id, 'state1_display_calls': state1_display(task_id)})
    print(json.dumps({'config_sha256': hashlib.sha256(raw).hexdigest(), 'quest_effect_table_sha256': hashlib.sha256(effect_raw).hexdigest(), 'effect_asset_sha256': hashlib.sha256(asset).hexdigest(), 'cases': cases, 'ordinary_commit': ordinary_commit(), 'end_cleanup_stage2': dialogue_stage(2), 'synthetic_finish_dialogue_stage3': dialogue_stage(3), 'absent_bean_repeated_state1': absent_bean_repeat(), 'scope': 'original bounded display/commit instructions; lookups adapted; resource/GPU/network boundary captured, not executed'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
