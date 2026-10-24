"""Original client rows for the blocked first story battle; read-only sources."""
from pathlib import Path
import hashlib
import json
import sys
import zlib

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'revival'))
from pfs import PfsArchive
from bxml import decode


def main():
    archive_path = ROOT/'artres/config.pfs'
    archive = PfsArchive(archive_path)
    tables, sources = {}, {}
    for suffix in ('task.cmainmissioninfo', 'npc.cnpcconfig', 'npc.cmonsterconfig',
                   'battle.cbattlebackground', 'battle.cbattlebackmusic'):
        name = 'autoconfig/knight.gsp.'+suffix+'.xml'
        raw = archive.read(name)
        tables[suffix] = decode(raw)
        sources[name] = dict(sha256=hashlib.sha256(raw).hexdigest(),
            crc32=f'{zlib.crc32(raw)&0xffffffff:08x}', length=len(raw), rows=len(tables[suffix]))
    tasks = []
    for row in tables['task.cmainmissioninfo']:
        if row.get('AIInfoAIID') == '8001':
            tasks.append(dict(attributes=dict(row.attrib), lists={child.tag:
                [item.get('value', item.text) for item in child] for child in row}))
    def selected(suffix, ids):
        return [dict(row.attrib) for row in tables[suffix] if row.get('id') in ids]
    result = dict(source_status='client_verified rows; battle AI mapping and numeric design not proved',
        archive=str(archive_path), archive_sha256=hashlib.sha256(archive_path.read_bytes()).hexdigest(),
        sources=sources, task_ai8001=tasks,
        npcs=selected('npc.cnpcconfig', {'10908','10909','10910','10911','10912'}),
        monsters=selected('npc.cmonsterconfig', {'29104','29112','29129'}),
        backgrounds=selected('battle.cbattlebackground', {'5'}),
        music=selected('battle.cbattlebackmusic', {'1'}),
        task_ai_enemy_association_verified=False, enemy_combat_stats_in_source=False,
        live_server_changed=False, live_database_accessed=False, game_started=False,
        program_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    output = ROOT/'revival/evidence/task-pve-ai8001-root-client-sources-20261024.json'
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(task_ids=[r['attributes']['id'] for r in tasks],
        count=len(tasks), selected_monsters=result['monsters'],
        selected_npcs=[{k:r.get(k) for k in ('id','name','modelID','mapid')} for r in result['npcs']],
        original_tables_verified=len(sources), output=str(output)),ensure_ascii=False))


if __name__ == '__main__':
    main()
