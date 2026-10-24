"""Execute original Start tail/commit/close; no live client, GUI or network.

Fixtures replace resource lookup and terminal endpoints only. The original
dialogue exhaustion, submit and close phase checks all execute unchanged.
"""
import hashlib
import json
from pathlib import Path
import sys
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parent))
from native_inspect import DATA
from research_task_jiaxing_scenario import Probe
from pfs import PfsArchive
from bxml import decode
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ESI

ROOT = Path(__file__).resolve().parent.parent
NPC_KEY = 0x1122334455667788


def main():
    assert hashlib.sha256(DATA).hexdigest() == '2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791'
    raw = PfsArchive(ROOT / 'artres/config.pfs').read('autoconfig/knight.gsp.task.cmainmissioninfo.xml')
    assert len(raw) == 2026233 and zlib.crc32(raw) == 0x3f7ab7b3
    rows = {int(x.get('id')): x for x in decode(raw)}
    routes = json.loads((ROOT / 'revival/catalogs/newbie-master-cards.json').read_text(encoding='utf-8'))['routes']
    masters = sorted({r['master_task_id'] for r in routes})
    carts = sorted({int(rows[int(rows[q].find('PostMissionList')[0].text)].find('PostMissionList')[0].text) for q in masters})
    assert len(masters) == 43 and len(carts) == 10
    p = Probe(masters[0])
    p.e.mem_map(0, 4096)  # Independent FS:[0] exception-chain storage.
    p.w(p.ui + 4, 0x500b000)
    p.w(0x500b004, 0x1644b50)  # Original close function, not a return stub.
    p.w(p.ui + 0x38, NPC_KEY & 0xffffffff, NPC_KEY >> 32)
    p.w(0x29586d4, 0)  # Separate NPC-notification mode disabled in fixture.
    trace = []

    def hook(emu, address, size, unused):
        if address in (0x164b530, 0x164bb51, 0x1643360, 0x1644b50, 0x1644c1d, 0x1644cf8):
            trace.append(hex(address))
        if address in (0x1919184, 0x800980, 0x1614740):
            p.ret()
        elif address == 0x8015e0:
            p.ret(0, 4)

    p.e.hook_add(UC_HOOK_CODE, hook)
    results = []
    for q in masters:
        row = rows[q]
        assert row.get('MissionType') == '10' and row.get('ProcessBarTime') == '0'
        assert len(row.find('ScenarioInfoNpcConversationList')) == 3
        assert row.find('ScenarioInfoFinishConversationList') is None
        assert not row.get('ScenarioInfoBranchNote')
        p.quest_id = q
        p.w(p.task, q)
        p.w(p.task + 0x164, 10)
        p.w(p.task + 0xd8, 0)
        p.w(p.task + 0x2e4, 0x500a000, 0x500a000 + 3 * 28)
        p.w(p.ui + 0x48, q, 0, 3)
        p.w(p.ui + 0x64, 2)
        p.calls = []
        trace.clear()
        p.e.reg_write(UC_X86_REG_ESI, p.ui)
        calls = p.span(0x164c3d6, 0x164c584)
        assert calls == [{'sent_type': '0xc4a44', 'quest_id': q, 'npc_key': NPC_KEY, 'option': 0}], calls
        assert trace == ['0x164b530', '0x164bb51', '0x1643360', '0x1644b50', '0x1644c1d', '0x1644cf8'], trace
        results.append({'kind': 'master_start_tail', 'task_id': q, 'trace': list(trace), 'sent': list(calls)})
    for q in carts:
        row = rows[q]
        assert row.get('MissionType') == '10' and row.get('ProcessBarTime') == '0'
        assert len(row.find('ScenarioInfoNpcConversationList')) == 2
        assert row.find('ScenarioInfoFinishConversationList') is None
        assert row.get('ScenarioInfoBranchNote') and len(row.find('ScenarioInfoBranchOptionList')) == 1
        assert row.get('RewardMapJumpType') == '1' and row.get('ScenarioInfoAnimationID') == '0'
        p.quest_id = q
        p.w(p.ui + 0x48, q, 0, 2)
        p.w(p.ui + 0x64, 5)
        p.w(p.stack + 0x3c, 0)
        p.calls = []
        trace.clear()
        p.e.reg_write(UC_X86_REG_ESI, p.ui)
        p.e.reg_write(UC_X86_REG_EAX, 5)
        calls = p.span(0x1648e88, 0x164904a)
        assert calls == [{'sent_type': '0xc4a44', 'quest_id': q, 'npc_key': NPC_KEY, 'option': 0}], calls
        assert trace == ['0x1644b50', '0x1644c1d', '0x1644cf8'], trace
        results.append({'kind': 'cart_phase5_choice_close', 'task_id': q, 'trace': list(trace), 'sent': list(calls)})
    output = {
        'native_image_sha256': hashlib.sha256(DATA).hexdigest(),
        'config_sha256': hashlib.sha256(raw).hexdigest(),
        'master_passed': 43, 'cart_passed': 10, 'quest_dialog_end_sent': 0,
        'scope': 'Original bounded x86 instructions; synthetic resource/UI state; lookup, network and terminal UI endpoints hooked. No GUI, client, service, real database or battle. Cart menu rendering not executed.',
        'cases': results,
    }
    target = ROOT / 'revival/evidence/first-master-dialogue-tail-native.json'
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'master_passed': 43, 'cart_passed': 10, 'quest_dialog_end_sent': 0, 'evidence': str(target)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
