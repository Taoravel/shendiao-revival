"""Offline, source-only starter equipment catalogue and original-instruction probes.

No item grant policy is selected here. No game process, owner, database or GUI is
started. Re-read PFS/BXML rather than treating a previous catalogue as evidence.
"""
from pathlib import Path
import hashlib
import json
import re
import struct

from bxml import decode
from pfs import PfsArchive

ROOT = Path(__file__).resolve().parent


def main():
    archive = PfsArchive(ROOT / 'runtime/client/artres/config.pfs')
    sources = {}

    def table(name):
        path = 'autoconfig/' + name + '.xml'
        raw = archive.read(path)
        rows = decode(raw)
        sources[path] = {'sha256': hashlib.sha256(raw).hexdigest(),
                         'crc_checked': True, 'rows': len(rows)}
        decoded = (ROOT / 'decoded/config' / path).read_text(encoding='utf-8').splitlines()
        lines = {int(m[1]): i + 1 for i, line in enumerate(decoded)
                 if (m := re.search(r'<record id="(\d+)"(?: |>)', line))}
        return {int(row.attrib['id']): {'attributes': dict(row.attrib),
                'lists': {c.tag: [v.text for v in c] for c in row},
                'source_path': path, 'source_line': lines[int(row.attrib['id'])]}
                for row in rows}

    missions = table('knight.gsp.task.cmainmissioninfo')
    roles = table('knight.gsp.role.createroleconfig')
    items = table('knight.gsp.item.citemattr')
    equips = table('knight.gsp.item.cequipeffect')
    npcs = table('knight.gsp.npc.cnpcconfig')
    cards = table('knight.gsp.task.ccardeffect')
    routes = json.loads((ROOT / 'catalogs/newbie-routes.json').read_text(encoding='utf-8'))['routes']
    checks = sorted({int(missions[r['successor_task_id']]['lists']['PostMissionList'][0]) for r in routes})
    assert len(routes) == 43 and len(checks) == 10
    assert all(missions[i]['attributes']['MissionType'] == '59' for i in checks)
    assert all(missions[i]['attributes'][field] == '0' for i in checks for field in
               ('ActiveInfoTargetID', 'ActiveInfoTargetNum', 'ActiveInfoUseItemID', 'ScenarioInfoAnimationID'))
    relevant = checks + sorted({r['successor_task_id'] for r in routes})
    assert len(relevant) == 53
    # These original records do not name any item reward. Preserve all lists and
    # attributes in the report so a future source discovery can falsify this.
    for ident in relevant:
        assert not any('RewardItem' in key for key in missions[ident]['lists'])
        assert not any('RewardItem' in key for key in missions[ident]['attributes'])
    ui = npcs[10390]
    assert ui['attributes']['mapid'] == '0'
    card_ids = {int(missions[r['successor_task_id']]['attributes']['ScenarioInfoAnimationID']) for r in routes}
    reward_ids = {int(cards[i]['attributes'][f'item{n}']) for i in card_ids for n in range(1, 5)
                  if int(cards[i]['attributes'][f'item{n}'])}
    assert len(card_ids) == 43 and len(reward_ids) == 10

    candidates = []
    for ident, row in items.items():
        a = row['attributes']
        if not ((40100 <= ident <= 41099 or ident in reward_ids) and a.get('level') == '1' and a.get('needLevel') == '1'):
            continue
        if ident not in equips:
            continue
        e = equips[ident]
        candidates.append({'template_id': ident, 'name': a['name'],
            'itemtypeid': int(a['itemtypeid']), 'equipment_slot': (int(a['itemtypeid']) >> 4) & 15,
            'role_need': [int(v) for v in e['lists'].get('roleNeed', [])],
            'effect_description': a.get('effectdes', ''),
            'classification': ('mentor_card_reward' if ident in reward_ids else
                'gift_pack_label' if '新手大礼包' in a.get('effectdes', '') else 'other_level_1'),
            'item_source': row, 'equipment_source': e})
    candidates.sort(key=lambda v: v['template_id'])
    assert all(c['equipment_slot'] == 0 for c in candidates)
    role_table = []
    for ident, row in roles.items():
        a = row['attributes']
        compatible = [c['template_id'] for c in candidates if ident in c['role_need']]
        role_table.append({'role_id': ident, 'name': a['name'],
            'weapon_type_1': int(a['weapon1']), 'weapon_type_2': int(a['weapon2']),
            'create_preview_template': int(a['weapon']),
            'create_preview_is_reward_evidence': False,
            'level_1_role_need_candidates': compatible,
            'mentor_card_reward_templates': [i for i in compatible if i in reward_ids], 'source': row})
        assert compatible
    output_routes = []
    for r in routes:
        mentor = missions[r['successor_task_id']]
        check = int(mentor['lists']['PostMissionList'][0])
        card_id = int(mentor['attributes']['ScenarioInfoAnimationID'])
        card = cards[card_id]['attributes']
        choices = [{'button_index': n, 'template_id': int(card[f'item{n}']),
                    'count': int(card[f'num{n}']), 'button_text': card.get(f'button{n}', '')}
                   for n in range(1, 5) if int(card[f'item{n}'])]
        assert len(choices) == 2 and all(v['count'] == 1 for v in choices)
        assert all(r['role_id'] in list(map(int, equips[v['template_id']]['lists']['roleNeed'])) for v in choices)
        output_routes.append({'role_id': r['role_id'], 'school_id': r['school_id'],
            'mentor_task_id': r['successor_task_id'], 'mentor_npc_id': r['first_npc_id'],
            'equipment_task_id': check, 'post_equipment_task_ids':
                list(map(int, missions[check]['lists']['PostMissionList'])),
            'card_effect_id': card_id, 'reward_choices': choices,
            'reward_template_source': 'client_verified_ccardeffect',
            'reward_count_source': 'client_verified_ccardeffect',
            'reward_binding_source': 'unresolved', 'grant_policy': None})

    # Independently extracted by the entity research owner. Cross-check the
    # actual reward choices, not a create-role preview or a numeric ID range.
    cross = json.loads((ROOT / 'catalogs/newbie-master-cards.json').read_text(encoding='utf-8'))
    cross_routes = {(r['character_id'], r['school_id']): r for r in cross['routes']}
    for r in output_routes:
        other = cross_routes[(r['role_id'], r['school_id'])]
        assert other['card_effect_id'] == r['card_effect_id']
        assert [(v['template_id'], v['count']) for v in r['reward_choices']] == [
            (v['item_id'], v['quantity']) for v in other['choices']]

    native = native_probe([c['itemtypeid'] for c in candidates])
    result = {'schema': 1, 'source_status': 'client_verified', 'sources': sources,
        'routes': output_routes, 'roles': role_table, 'candidate_items': candidates,
        'task_sources': {i: missions[i] for i in relevant},
        'card_sources': {i: cards[i] for i in sorted(card_ids)}, 'bag_ui_link_10390': ui,
        'reward_template_and_count_resolved': True, 'reward_policy_resolved': False,
        'reward_selection_protocol_evidence': 'evidence/WORLD_MASTER_CARD_PROTOCOL.md',
        'unresolved': ['exact server grant timing', 'binding interpretation', 'type59 exact original completion predicate'],
        'completion_predicate_source': 'not located in original server; asset-owner equipment event required by recovery design',
        'native': native, 'no_client_gui_or_service_started': True}
    (ROOT / 'catalogs/newbie-equipment-sources.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'routes': len(output_routes), 'task_sources': len(relevant),
        'equipment_tasks': checks, 'candidate_templates': len(candidates),
        'native_slot_cases': len(native['slot_cases']), 'native_codec_cases': len(native['codec_cases']),
        'reward_template_and_count_resolved': True, 'reward_policy_resolved': False}))


def native_probe(itemtypes):
    from native_inspect import BASE, DATA, capstone
    from native_gameplay_probe import probe
    from unicorn import Uc, UC_ARCH_X86, UC_MODE_32
    from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ESI

    emu = Uc(UC_ARCH_X86, UC_MODE_32)
    emu.mem_map(BASE, (len(DATA) + 4095) & ~4095)
    emu.mem_write(BASE, DATA)
    obj = 0x5001000
    emu.mem_map(0x5000000, 0x2000)
    cases = []
    # Counterfactuals exercise every slot nibble, so this cannot pass merely
    # because all starter candidates happen to be weapons.
    for value in sorted(set(itemtypes) | {0xA000 | (slot << 4) | 8 for slot in range(16)}):
        emu.mem_write(obj + 8, struct.pack('<I', value))
        emu.reg_write(UC_X86_REG_ESI, obj)
        emu.emu_start(0x10e1dd4, 0x10e1ddd, count=3)
        actual = emu.reg_read(UC_X86_REG_EAX)
        assert actual == (value >> 4) & 15
        cases.append({'itemtypeid': value, 'original_slot': actual})
    codecs = []
    for key, slot in ((1, 0), (0x12345678, 0), (0x7fffffff, 15)):
        payload, decoded = probe(0xd90f70, 0xe4c2d0, 0xd91020,
            fields={8: struct.pack('<I', key), 12: struct.pack('<I', slot)})
        assert payload == struct.pack('>ii', key, slot)
        assert struct.unpack_from('<ii', decoded, 8) == (key, slot)
        codecs.append({'instance_key': key, 'slot': slot, 'wire_hex': payload.hex()})
    names = re.findall(rb'\.\?AV[^\x00]{1,180}', DATA)
    matches = [n.decode('ascii', errors='replace') for n in names if b'CReqTaskCheck' in n or b'TaskCheck' in n]
    assert not matches
    sha = hashlib.sha256(DATA).hexdigest()
    cs = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    text = 'native-image.bin SHA256 ' + sha + '\n'
    for start, size in ((0x10e1dbb, 0x55), (0xd90f70, 0x31), (0xe4c2d0, 0x45), (0xd91020, 0xaa)):
        text += '\n' + '\n'.join(f'{i.address:08x} {i.mnemonic:8} {i.op_str}'
            for i in cs.disasm(DATA[start-BASE:start-BASE+size], start)) + '\n'
    (ROOT / 'evidence/newbie-equipment-native-disassembly.txt').write_text(text, encoding='utf-8')
    return {'image_sha256': sha, 'slot_cases': cases, 'codec_cases': codecs,
        'original_constructor': '0xd90f70', 'original_serializer': '0xe4c2d0',
        'original_decoder': '0xd91020', 'CEquipement_type': '0xc03f5',
        'slot_instruction_range': ['0x10e1dd4', '0x10e1ddd'],
        'CReqTaskCheck_or_TaskCheck_RTTI_matches': matches,
        'absence_limitation': 'RTTI name absence does not prove no generic task report exists',
        'codec_adapter': 'native_gameplay_probe allocator/stream memory adapters; original codec instructions executed'}


if __name__ == '__main__':
    main()
