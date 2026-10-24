"""Independent post-publication audit; only OS evidence and offline DB copies."""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def db_state(path):
    with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro&immutable=1',uri=True)) as db:
        ok=db.execute('PRAGMA quick_check').fetchone()[0]
        schema={(kind,name,table):sql for kind,name,table,sql in db.execute(
            "SELECT type,name,tbl_name,sql FROM sqlite_master WHERE type IN ('table','index','trigger','view')")}
        tables={}
        for (name,) in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND (name NOT LIKE 'sqlite_%' OR name='sqlite_sequence') ORDER BY name"):
            quote='"'+name.replace('"','""')+'"'
            rows=sorted(repr(tuple(row)).encode('utf-8') for row in db.execute('SELECT * FROM '+quote))
            digest=hashlib.sha256()
            for row in rows:digest.update(len(row).to_bytes(8,'big'));digest.update(row)
            tables[name]=dict(rows=len(rows),sha256=digest.hexdigest())
        return ok,tables,schema


def main():
    root=Path(__file__).resolve().parents[1]
    release=root/'runtime/deployments/task-pve-20261024T053218Z'
    review=root/'evidence/reviews/task-pve-root-20261024-r1'
    output=root/'evidence/root-task-pve-release-postflight-20261024-r1'
    output.mkdir(parents=True,exist_ok=False)
    (output/'executed-runner.py').write_bytes(Path(__file__).read_bytes())
    receipt_path=review/'acceptance-root.json'
    receipt=json.loads(receipt_path.read_text(encoding='utf-8'))
    if sha(receipt_path)!='9c45a69b66861230360dc1a33705b4e8651942c656d50e6dda2cec1a807d33a7':
        raise ValueError('Root release approval changed')
    manifest=json.loads((release/'manifest.json').read_text(encoding='utf-8'))
    current=json.loads((release/'candidate.json').read_text(encoding='utf-8'))
    original=json.loads((review/'reviewed-candidate.json').read_text(encoding='utf-8'))
    allowed=set(receipt['allowed_candidate_metadata_updates'])
    if ({k:v for k,v in current.items() if k not in allowed}!={k:v for k,v in original.items() if k not in allowed}
            or current.get('started') is not True or current.get('status')!='deployed' or current.get('pid')!=37096):
        raise ValueError('Candidate update exceeded the approved metadata-only change')
    if sha(release/'manifest.json')!=receipt['manifest_sha256'] or sha(release/'preflight.json')!=receipt['preflight_sha256']:
        raise ValueError('Approved release inputs changed')
    for name,wanted in receipt['deployment_tools_sha256'].items():
        if sha(root/name)!=wanted:raise ValueError('Deployed tooling changed: '+name)
    for name,wanted in receipt['review_sha256'].items():
        if sha(review/name)!=wanted:raise ValueError('Independent review input changed: '+name)
    sets=((release/'source',manifest['sha256']),(release/'harness',current['harness_sha256']),
        (release/'harness',current['harness_resource_sha256']),(release/'harness/workspace',current['workspace_sha256']))
    for directory,entries in sets:
        for name,wanted in entries.items():
            if sha(directory/name)!=wanted:raise ValueError('Frozen runtime/harness changed: '+str(directory/name))
    startup=json.loads((root/'runtime/deployment.json').read_text(encoding='utf-8'))
    expected={n:v for n,v in manifest['sha256'].items() if n.endswith('.py') and '/' not in n}
    if startup['pid']!=37096 or startup['source_sha256_at_startup']!=expected or len(expected)!=454:
        raise ValueError('Actual startup is not the complete approved 454-Python-file version')
    deployment=release/'deployment-verification.json'
    post=json.loads(deployment.read_text(encoding='utf-8'))
    if (post['pid']!=37096 or post['previous_pid']!=7456 or post['version']!=601
            or post['unauthenticated_heartbeat']!='passed' or post['source_hashes_verified']!=1454
            or post['release']!=str(release/'run_release.py') or post['quick_check']!='ok'):
        raise ValueError('Main postflight identity/health/data proof missing')
    lifetime=root/'evidence/detached-service-recovery.json'
    host=json.loads(lifetime.read_text(encoding='utf-8'))
    if (host['pid']!=37096 or host['release']!=str(release) or host['caller_pid']!=45984
            or host['target_in_caller_job'] or 37096 in host['caller_job_process_ids_at_launch']
            or host['source_files_verified']!=1454 or host['startup_python_hashes']!=454
            or not host['preexisting_table_schema_unchanged']):
        raise ValueError('Actual detached startup receipt mismatch')
    liveness=root/'evidence/root-service-liveness-task-pve-37096-postflight-20261024.json'
    observed=json.loads(liveness.read_text(encoding='utf-8'))
    if (not observed['healthy'] or observed['startup_recorded_pid']!=37096 or observed['listener_pids']!=[37096]
            or not observed['expected_runner_matches'] or Path(observed['expected_release'])!=release):
        raise ValueError('Parent OS observation did not prove the exact unique running listener')
    old_copy=release/'accounts-at-stop.sqlite3';after_copy=release/'accounts-after-startup.sqlite3'
    old_ok,before,old_schema=db_state(old_copy)
    new_ok,after,new_schema=db_state(after_copy)
    added=set(after)-set(before)
    if (old_ok!='ok' or new_ok!='ok' or len(before)!=110
            or any(after.get(n)!=v for n,v in before.items())
            or any(new_schema.get(n)!=v for n,v in old_schema.items())
            or added!=set(current['new_empty_tables']) or any(after[n]['rows'] for n in added)):
        raise ValueError('Offline before/after startup copies do not preserve all old rows and SQL')
    result=dict(status='published_exact_task_pve_release_independently_verified',passed=True,
        release=str(release),pid=37096,previous_pid=7456,source_files=1454,startup_python_files=454,
        source_harness_input_counts=[len(v) for _,v in sets],unique_listener_verified=True,
        caller_process_exited_observed_in_parent_tool=True,actual_target_in_any_windows_job=host['actual_target_in_windows_job'],
        target_absent_from_actual_caller_job_list=True,complete_startup_hashes_match=True,
        manifest_sha256=sha(release/'manifest.json'),runner_sha256=manifest['runner_sha256'],
        reviewed_candidate_sha256=sha(review/'reviewed-candidate.json'),deployed_candidate_sha256=sha(release/'candidate.json'),
        only_started_status_pid_metadata_changed=True,old_table_count=110,all_old_rows_preserved=True,
        all_old_tables_indexes_triggers_views_sql_preserved=True,added_empty_tables=sorted(added),quick_check='ok',
        proof_sha256={str(p):sha(p) for p in (receipt_path,deployment,lifetime,liveness,old_copy,after_copy)},
        main_network_health_version=601,main_unauthenticated_heartbeat_verified=True,
        root_actual_live_database_opened=False,root_live_socket=False,root_service_changed=False,
        native_gui_verified=False,full_growth_or_full_restoration_complete=False,
        cross_next_goal_turn_liveness_pending=True,parent_runner_sha256=sha(Path(__file__)))
    (output/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('status','pid','source_files','startup_python_files','old_table_count','added_empty_tables','native_gui_verified')}))


if __name__=='__main__':
    main()
