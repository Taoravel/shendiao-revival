"""Read-only final release, check/import closure and offline migration audit."""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    root=Path(__file__).resolve().parents[1]
    release=root/'runtime/deployments/task-pve-20261024T053218Z'
    output=root/'evidence/root-task-pve-final-bundle-20261024-r1'
    output.mkdir(parents=True,exist_ok=False)
    (output/'executed-runner.py').write_bytes(Path(__file__).read_bytes())
    source,harness=release/'source',release/'harness'
    manifest_path,candidate_path=release/'manifest.json',release/'candidate.json'
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    candidate=json.loads(candidate_path.read_text(encoding='utf-8'))
    preflight_path=release/'preflight.json'
    preflight=json.loads(preflight_path.read_text(encoding='utf-8'))
    pinned={str(p):sha(p) for p in (manifest_path,candidate_path,preflight_path,
        release/'run_release.py',release/'accounts-before.sqlite3',release/'migration-check.sqlite3')}
    sets=((source,manifest['sha256']),(harness,candidate['harness_sha256']),
          (harness,candidate['harness_resource_sha256']),(harness/'workspace',candidate['workspace_sha256']))
    def verify():
        for directory,entries in sets:
            for name,wanted in entries.items():
                if sha(directory/name)!=wanted:raise ValueError('Frozen input differs: '+str(directory/name))
        for name,wanted in pinned.items():
            if sha(Path(name))!=wanted:raise ValueError('Final metadata/backup changed: '+name)
    verify()
    if sha(release/'run_release.py')!=manifest['runner_sha256']:raise ValueError('Runner differs')
    bundle=dict(production=manifest['sha256'],runner=manifest['runner_sha256'],
        harness=candidate['harness_sha256'],resources=candidate['harness_resource_sha256'],
        workspace=candidate['workspace_sha256'],checks=candidate['checks_required'],
        arguments=candidate.get('check_arguments',{}))
    seal=hashlib.sha256(json.dumps(bundle,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if seal!=candidate['acceptance_input_sha256']:raise ValueError('Final input seal mismatch')
    checks={};production_shadowing=[]
    for name in candidate['checks_required']:
        path=release/'checks'/(name+'.result.json')
        record=json.loads(path.read_text(encoding='utf-8'))
        if (not record['passed'] or record['acceptance_input_sha256']!=seal
                or record['script']!=name or record['production_inputs_preserved']!=len(sets[0][1])
                or record['harness_inputs_preserved']!=len(sets[1][1])):
            raise ValueError('Check was not green against these exact inputs: '+name)
        for module,filename in record['production_and_harness_module_origins'].items():
            origin=Path(filename).resolve()
            if origin.is_relative_to(source):
                relative=origin.relative_to(source).as_posix();wanted=manifest['sha256'].get(relative)
            elif origin.is_relative_to(harness):
                relative=origin.relative_to(harness).as_posix()
                wanted=candidate['harness_sha256'].get(relative)
                if wanted is None and origin.is_relative_to(harness/'workspace'):
                    wanted=candidate['workspace_sha256'].get(origin.relative_to(harness/'workspace').as_posix())
                if (source/origin.name).is_file() and not module.startswith(('verify_','research_','native_')):
                    production_shadowing.append((name,module,str(origin)))
            else:raise ValueError('Unfrozen application import: '+filename)
            if wanted is None or sha(origin)!=wanted:raise ValueError('Import SHA is not frozen: '+filename)
        checks[name]=dict(path=str(path),sha256=sha(path),imports=len(record['production_and_harness_module_origins']))
    if len(checks)!=20 or production_shadowing:
        raise ValueError('Unexpected checks or gameplay shadowing: '+repr(production_shadowing))
    if (preflight['release']!=str(release) or preflight['quick_check']!='ok'
            or preflight['candidate_hashes_verified']!=1454
            or preflight['checks_passed']!=candidate['checks_required']
            or preflight['added_empty_tables']!=candidate['new_empty_tables']
            or candidate['new_empty_tables']!=manifest['new_empty_tables']):
        raise ValueError('Exact preflight identity or table scope mismatch')
    # These are frozen offline preflight copies. Never open the real game DB.
    def state(path):
        with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro&immutable=1',uri=True)) as db:
            integrity=db.execute('PRAGMA quick_check').fetchone()[0]
            schema={(kind,name,table):sql for kind,name,table,sql in db.execute(
                "SELECT type,name,tbl_name,sql FROM sqlite_master WHERE type IN ('table','index','view','trigger')")}
            tables={}
            for (name,) in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND (name NOT LIKE 'sqlite_%' OR name='sqlite_sequence') ORDER BY name"):
                quoted='"'+name.replace('"','""')+'"'
                rows=sorted(repr(tuple(row)).encode('utf-8') for row in db.execute('SELECT * FROM '+quoted))
                digest=hashlib.sha256()
                for row in rows:digest.update(len(row).to_bytes(8,'big'));digest.update(row)
                tables[name]=dict(rows=len(rows),sha256=digest.hexdigest())
            return integrity,tables,schema
    old_ok,before,old_schema=state(release/'accounts-before.sqlite3')
    new_ok,after,new_schema=state(release/'migration-check.sqlite3')
    added=set(after)-set(before)
    if (old_ok!='ok' or new_ok!='ok' or len(before)!=110 or before!=preflight['tables']
            or any(after.get(n)!=v for n,v in before.items())
            or added!=set(manifest['new_empty_tables']) or any(after[n]['rows'] for n in added)
            or any(new_schema.get(k)!=v for k,v in old_schema.items())):
        raise ValueError('Offline migration changed old schema/data or unexpected new tables')
    base=Path(candidate['base_release'])
    base_manifest=json.loads((base/'manifest.json').read_text(encoding='utf-8'))
    delta={n:h for n,h in manifest['sha256'].items() if base_manifest['sha256'].get(n)!=h}
    if delta!=manifest['changed_modules'] or not set(base_manifest['sha256'])<=set(manifest['sha256']):
        raise ValueError('Declared production delta mismatch')
    verify()
    result=dict(passed=True,release=str(release),acceptance_input_sha256=seal,
        manifest_sha256=sha(manifest_path),candidate_sha256=sha(candidate_path),preflight_sha256=sha(preflight_path),
        runner_sha256=sha(release/'run_release.py'),input_counts=[len(entries) for _,entries in sets],
        checks=checks,all20_checks_sealed_green=True,all_import_paths_and_sha_verified=True,
        no_gameplay_shadowing=True,production_delta=delta,all_base_files_retained=True,
        preexisting_table_count=len(before),all_old_rows_preserved=True,
        all_old_tables_indexes_views_triggers_sql_preserved=True,added_empty_tables=sorted(added),
        pinned_metadata_and_backup_sha256=pinned,all_frozen_inputs_stable=True,
        real_database_opened=False,live_socket=False,service_changed=False,native_gui_verified=False,
        activation_authorized=False,parent_runner_sha256=sha(Path(__file__)))
    (output/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('passed','acceptance_input_sha256','input_counts','all20_checks_sealed_green','preexisting_table_count','added_empty_tables')}))


if __name__=='__main__':
    main()
