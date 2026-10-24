"""Recover shipped task graphs and dialogue; keep unknown server rules explicit."""
from collections import Counter, defaultdict
import hashlib
import json
from inspect_client import OUT, write_json


def load(name):
    return json.loads((OUT / 'catalogs' / f'knight.gsp.{name}.json').read_text(encoding='utf-8'))


def main():
    source = OUT / 'catalogs/knight.gsp.task.cmainmissioninfo.json'
    rows = load('task.cmainmissioninfo')
    offers = {int(r['attributes']['id']): r for r in load('task.cacceptabletask')}
    npcs = {int(r['attributes']['id']): r['attributes'] for r in load('npc.cnpcconfig')}
    maps = {int(r['attributes']['id']): r['attributes'] for r in load('map.cmapconfig')}
    ids = {int(r['attributes']['id']) for r in rows}
    if len(ids) != len(rows):
        raise ValueError('Duplicate mission IDs')
    incoming = defaultdict(list)
    for row in rows:
        for dest in row['lists'].get('PostMissionList', []):
            incoming[int(dest)].append(int(row['attributes']['id']))
    records, issues = [], []
    for row in rows:
        a, lists = row['attributes'], row['lists']
        ident = int(a['id'])
        npc, map_id = int(a.get('ActiveInfoNpcID', 0)), int(a.get('ActiveInfoMapID', 0))
        dialogue = {}
        for label, text_key, npc_key in (
                ('start', 'ScenarioInfoNpcConversationList', 'ScenarioInfoNpcID'),
                ('finish', 'ScenarioInfoFinishConversationList', 'ScenarioInfoFinishNpcID')):
            texts, speakers = lists.get(text_key, []), lists.get(npc_key, [])
            if len(texts) != len(speakers):
                issues.append({'id': ident, 'issue': 'dialogue_length_mismatch', 'part': label})
            dialogue[label] = [{'speaker': int(speakers[i]) if i < len(speakers) else None,
                                'text': text} for i, text in enumerate(texts)]
        next_ids = [int(v) for v in lists.get('PostMissionList', [])]
        missing = [v for v in next_ids if v not in ids and v != 0]
        if missing:
            issues.append({'id': ident, 'issue': 'successor_not_in_client_table', 'targets': missing})
        item_ids, item_nums = lists.get('RewardItemIDList', []), lists.get('RewardItemNumList', [])
        if len(item_ids) != len(item_nums):
            issues.append({'id': ident, 'issue': 'reward_length_mismatch'})
        records.append({
            'id': ident, 'name': a['MissionName'], 'category': a.get('MissionTypeString', ''),
            'type': int(a['MissionType']),
            'level': {'min': int(a.get('MinLevel', 0)), 'max': int(a.get('MaxLevel', 0))},
            'role_config_ids': [int(v) for v in lists.get('RequestRoleIDList', [])],
            'request_mission_ids': [int(v) for v in lists.get('RequestMissionList', [])],
            'incoming_ids': sorted(incoming[ident]), 'next_ids': next_ids,
            'unresolved_next_ids': missing,
            'target': {'npc_id': npc, 'npc_name': npcs.get(npc, {}).get('name'),
                       'map_id': map_id, 'map_name': maps.get(map_id, {}).get('mapName'),
                       'id': int(a.get('ActiveInfoTargetID', 0)),
                       'count': int(a.get('ActiveInfoTargetNum', 0))},
            'text': {k: a.get(v, '') for k, v in (
                ('description', 'TaskInfoDescriptionListA'), ('purpose', 'TaskInfoPurposeListA'),
                ('trace', 'TaskInfoTraceListA'), ('note', 'NoteInfo'))},
            'dialogue': dialogue,
            'display_rewards': {k: int(a.get(k, 0)) for k in (
                'ExpReward', 'MoneyReward', 'PetExpReward', 'ShengWang', 'SMoney')},
            'display_items': [{'id': int(v), 'count': int(item_nums[i]) if i < len(item_nums) else None,
                              'bind': int(lists['RewardItemIsBindList'][i])
                              if i < len(lists.get('RewardItemIsBindList', [])) else None}
                             for i, v in enumerate(item_ids)],
            'offer': offers.get(ident),
            'source': {'catalog': source.name, 'id': ident},
            'attributes': a, 'lists': lists,
        })
    by_npc, by_map, by_type = defaultdict(list), defaultdict(list), defaultdict(list)
    for task in records:
        by_type[str(task['type'])].append(task['id'])
        if task['target']['npc_id']:
            by_npc[str(task['target']['npc_id'])].append(task['id'])
        if task['target']['map_id']:
            by_map[str(task['target']['map_id'])].append(task['id'])
    doc = {'schema': 1, 'missions': records, 'offers': list(offers.values()),
           'indexes': {'npc': dict(by_npc), 'map': dict(by_map), 'type': dict(by_type)},
           'rules': {'rewards': 'client display configuration; no grant performed',
                     'request_lists': 'original literals; AND/OR and server activation rules unconfirmed',
                     'incoming_edges': 'graph links, not automatic prerequisites',
                     'missing_successors': 'preserved as unresolved; never replaced or silently completed'}}
    write_json(OUT / 'catalogs/tasks.json', doc)
    counts = {'missions': len(records), 'offers': len(offers),
              'dialogue_lines': sum(len(r['dialogue'][k]) for r in records for k in ('start', 'finish')),
              'successor_links': sum(len(r['next_ids']) for r in records),
              'task_types': dict(Counter(str(r['type']) for r in records)),
              'npcs': len(by_npc), 'maps': len(by_map)}
    write_json(OUT / 'evidence/task-recovery.json', {
        'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'summary': counts, 'issues': issues, 'runtime_verified': False})
    print(json.dumps(counts, ensure_ascii=False))


if __name__ == '__main__':
    main()
