"""Offline type40 catalog statistics and original battle-admission sender/codec.

Reads original PFS/mapped image only; writes an independent evidence JSON.
"""
import collections
import hashlib
import json
from pathlib import Path
import struct
from native_inspect import BASE, DATA
from native_gameplay_probe import probe
from pfs import PfsArchive
from bxml import decode
from research_task_display import classify
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_ESP, UC_X86_REG_EIP

ROOT = Path(__file__).parent.parent
FIELDS = ('AIInfoAIID', 'AIInfoBattleResult', 'AIInfoDeathPunish', 'AIInfoTeamSteate', 'ScenarioInfoAnimationID', 'ScenarioInfoBranchNpcID', 'ProcessBarTime', 'ActiveInfoUseItemID', 'ActiveInfoTimeLimit', 'ActiveInfoIsRestartTimer', 'ActiveInfoTeamState', 'ActiveInfoNpcID', 'ActiveInfoMapID', 'ActiveInfoOtherType', 'ActiveInfoTargetID', 'ActiveInfoTargetNum', 'ActiveInfoMiniStep', 'ActiveInfoStepProbability', 'ActiveInfoMaxStep', 'BattleInfoBattleMapType', 'BattleInfoBattleZoneID', 'BattleInfoMonsterNum', 'BattleInfoBattleTimes', 'BattleInfoDrop', 'BattleInfoDropItemID', 'BattleInfoDropItemNum', 'RewardMapJumpType')
CHILDREN = ('ScenarioInfoNpcConversationList', 'ScenarioInfoFinishConversationList', 'ScenarioInfoBranchOptionList', 'RewardItemIDList', 'PostMissionList')


def original_battle_sender(task_id, npc_key):
    e = Uc(UC_ARCH_X86, UC_MODE_32)
    e.mem_map(BASE, (len(DATA) + 4095) & ~4095)
    e.mem_write(BASE, DATA)
    e.mem_map(0x5000000, 0x10000)
    stack, ui, config, net, vt, send = 0x500f000, 0x5001000, 0x5002000, 0x5003000, 0x5004000, 0x5000500
    def w(addr, *values):
        e.mem_write(addr, struct.pack('<' + 'I' * len(values), *values))
    def r(addr):
        return struct.unpack('<I', e.mem_read(addr, 4))[0]
    def ret(value=0, cleanup=0):
        sp = e.reg_read(UC_X86_REG_ESP)
        target = r(sp)
        e.reg_write(UC_X86_REG_EAX, value)
        e.reg_write(UC_X86_REG_ESP, sp + 4 + cleanup)
        e.reg_write(UC_X86_REG_EIP, target)
    w(ui + 0x48, task_id)
    w(ui + 0x38, npc_key & 0xffffffff, npc_key >> 32)
    w(config + 0xd8, 0)
    w(net, vt)
    w(vt + 0x3c, send)
    sent = []
    def hook(emu, addr, size, _):
        if addr == 0x1137dc0:
            ret(1)  # choose the original direct path; predicate policy not emulated
        elif addr == 0x813860:
            ret(net)
        elif addr == send:
            obj = r(e.reg_read(UC_X86_REG_ESP) + 4)
            sent.append({'type': r(obj + 4), 'quest_id': r(obj + 8), 'npc_key': r(obj + 0x10) | r(obj + 0x14) << 32})
            ret(0, 4)
    e.hook_add(UC_HOOK_CODE, hook)
    e.reg_write(UC_X86_REG_ESP, stack)
    e.reg_write(UC_X86_REG_ESI, ui)
    e.reg_write(UC_X86_REG_EDI, config)
    e.reg_write(UC_X86_REG_EAX, 40)
    e.emu_start(0x164343c, 0x16434f0, count=100)
    assert e.reg_read(UC_X86_REG_EIP) == 0x16434f0
    assert sent == [{'type': 0xc4a4c, 'quest_id': task_id, 'npc_key': npc_key}], sent
    return sent


def extra_reasons(row):
    zero_fields = ('ScenarioInfoAnimationID', 'ScenarioInfoBranchNpcID', 'ProcessBarTime', 'ActiveInfoUseItemID', 'ActiveInfoTimeLimit', 'ActiveInfoIsRestartTimer', 'RewardMapJumpType', 'ActiveInfoTargetID', 'ActiveInfoTargetNum', 'BattleInfoMonsterNum')
    reasons = [key for key in zero_fields if row.get(key, '0') != '0']
    if row.get('AIInfoBattleResult') != '1':
        reasons.append('AIInfoBattleResult_not_1')
    reasons += [key for key in ('ScenarioInfoBranchNote', 'NoteInfo') if row.get(key)]
    if row.find('ScenarioInfoBranchOptionList') is not None and len(row.find('ScenarioInfoBranchOptionList')):
        reasons.append('ScenarioInfoBranchOptionList')
    return reasons


def main():
    archive = PfsArchive(ROOT / 'artres/config.pfs')
    sources = {}
    tables = {}
    for key in ('task.cmainmissioninfo', 'battle.cbattleaiconfig', 'npc.cmonsterconfig', 'battle.cmonstertypeconfig'):
        path = 'autoconfig/knight.gsp.' + key + '.xml'
        raw = archive.read(path)
        tables[key] = decode(raw)
        sources[path] = {'sha256': hashlib.sha256(raw).hexdigest(), 'rows': len(tables[key])}
    rows = [row for row in tables['task.cmainmissioninfo'] if row.get('MissionType') == '40']
    assert len(rows) == 362
    ai_ids = {int(row.get('AIInfoAIID')) for row in rows}
    client_ai_ids = {int(row.get('id')) for row in tables['battle.cbattleaiconfig']}
    assert len(ai_ids) == 244 and not ai_ids.intersection(client_ai_ids)
    selected = []
    for row in rows:
        selected.append({'id': int(row.get('id')), 'name': row.get('MissionName'), **{key: row.get(key) for key in FIELDS}, 'children': {key: [child.text for child in row.find(key)] if row.find(key) is not None else [] for key in CHILDREN}, 'NoteInfo': row.get('NoteInfo'), 'extra_reasons': extra_reasons(row)})
    body, decoded = probe(0xdd3b30, 0xe57320, 0xdd3be0, {8: struct.pack('<i', 100107), 0x10: struct.pack('<Q', 0x1122334455667788)})
    assert body == struct.pack('>iQ', 100107, 0x1122334455667788)
    assert struct.unpack_from('<i', decoded, 8)[0] == 100107
    assert struct.unpack_from('<Q', decoded, 0x10)[0] == 0x1122334455667788
    ui = []
    for state, expected in ((None, 1), (0, 3), (2, 3), (3, 3)):
        actual = classify(state, 40)
        assert actual == expected
        ui.append({'bean_state': state, 'menu_class': actual})
    native = {'codec_wire': body.hex(), 'codec_bytes': len(body), 'original_senders': [original_battle_sender(task_id, 0x1122334455667788) for task_id in (100107, 100113)], 'menu_predicates': ui, 'note': 'state2 is not called normal active: menu classification and tracker rendering are separate; current integration identifies tracker state2 as failure'}
    output = {'sources': sources, 'native_image_sha256': hashlib.sha256(DATA).hexdigest(), 'type40_count': len(rows), 'distinct_task_ai_ids': len(ai_ids), 'task_ai_range': [min(ai_ids), max(ai_ids)], 'client_ai_id_range': [min(client_ai_ids), max(client_ai_ids)], 'direct_ai_join_matches': sorted(ai_ids & client_ai_ids), 'field_distributions': {key: dict(collections.Counter(row.get(key, '<absent>') for row in rows)) for key in FIELDS}, 'nonempty_child_counts': {key: sum(bool(row.find(key) is not None and len(row.find(key))) for row in rows) for key in CHILDREN}, 'zero_extra_metadata_count': sum(not extra_reasons(row) for row in rows), 'zero_extra_metadata_ids': [int(row.get('id')) for row in rows if not extra_reasons(row)], 'ai_fields': sorted({key for row in tables['battle.cbattleaiconfig'] for key in row.attrib}), 'monster_fields': sorted({key for row in tables['npc.cmonsterconfig'] for key in row.attrib}), 'native': native, 'tasks': selected, 'scope': 'read-only original PFS and isolated native codecs/menu/sender; no authoritative battle simulation, server, GUI, production edit, or active-bean projection'}
    target = ROOT / 'revival/evidence/task-battle-admission-static.json'
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'evidence': str(target), 'type40_count': len(rows), 'distinct_task_ai_ids': len(ai_ids), 'direct_ai_join_count': len(ai_ids & client_ai_ids), 'zero_extra_metadata_count': output['zero_extra_metadata_count'], 'native': native}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
