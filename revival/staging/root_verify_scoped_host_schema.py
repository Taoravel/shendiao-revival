"""Execute only the actual new host's schema guards against disposable data."""
import ast
from contextlib import nullcontext
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    root=Path(__file__).resolve().parents[1]
    output=root/'evidence/root-task-pve-scoped-host-schema-20261024-r2'
    output.mkdir(parents=True,exist_ok=False)
    host=root/'staging/launch_detached_scoped_release.py'
    helper=root/'staging/master_ready_preflight.py'
    original=root/'staging/launch_detached_release.py'
    health=root/'staging/service_health_probe.py'
    expected={str(p):sha(p) for p in (host,helper,original,health)}
    if sha(host)!='6f9147b259eba43b798d191283d1d08a5f3ad3642e8c69454daf9d1478a48045':
        raise ValueError('Unexpected scoped host')
    for p in (host,helper,original,health):
        (output/p.name).write_bytes(p.read_bytes())
    (output/'executed-runner.py').write_bytes(Path(__file__).read_bytes())
    tree=ast.parse(host.read_text(encoding='utf-8'))
    body=next(n.body for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    candidate_at=next(i for i,n in enumerate(body) if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='candidate')
    flags_at=next(i for i,n in enumerate(body) if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='flags')
    before_nodes=body[candidate_at:flags_at]
    after_node=next(n for n in body if isinstance(n,ast.With) and any(
        isinstance(v,ast.Assign) and isinstance(v.targets[0],ast.Name) and v.targets[0].id=='added_empty_tables' for v in ast.walk(n)))
    require=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='require')
    before_code=compile(ast.Module(body=before_nodes,type_ignores=[]),str(host),'exec')
    after_code=compile(ast.Module(body=[after_node],type_ignores=[]),str(host),'exec')
    namespace={}
    exec(compile(ast.Module(body=[require],type_ignores=[]),str(host),'exec'),namespace)
    spec=importlib.util.spec_from_file_location('root_frozen_preflight_helper',output/helper.name)
    loaded=importlib.util.module_from_spec(spec);spec.loader.exec_module(loaded)
    allowed=['role_other_skill_baseline_migrations','role_other_skills','task_battle_admissions','task_first_skills','task_pve_runtime_battles']
    cases=[]
    with nullcontext(output/'fixtures') as folder:
        temp=Path(folder)
        temp.mkdir()
        backup=temp/'before.sqlite3'
        with sqlite3.connect(backup) as db:
            db.executescript('CREATE TABLE kept(role_id INTEGER PRIMARY KEY,value INTEGER); INSERT INTO kept VALUES(4,120); CREATE TABLE empty_old(value TEXT);')
            before=loaded.table_state(db)
            schemas=dict(db.execute("SELECT name,sql FROM sqlite_master WHERE type='table'"))
        db.close()
        for kind in ('valid','changed_old_row','missing_old_table','unknown_new_table','populated_new_table','changed_empty_old_schema'):
            current=temp/kind;current.mkdir();(current/'runtime').mkdir()
            target=current/'runtime/accounts.sqlite3';shutil.copyfile(backup,target)
            with sqlite3.connect(target) as db:
                for name in allowed:db.execute('CREATE TABLE "'+name+'"(id INTEGER)')
                if kind=='changed_old_row':db.execute('UPDATE kept SET value=999')
                if kind=='missing_old_table':db.execute('DROP TABLE kept')
                if kind=='unknown_new_table':db.execute('CREATE TABLE unwanted(id INTEGER)')
                if kind=='populated_new_table':db.execute('INSERT INTO task_first_skills VALUES(1)')
                if kind=='changed_empty_old_schema':
                    db.executescript('DROP TABLE empty_old; CREATE TABLE empty_old(value BLOB NOT NULL);')
            db.close()
            env=dict(ROOT=current,sqlite3=sqlite3,before=before,before_schema=schemas,
                candidate={'new_empty_tables':allowed},verify_preserved_tables=loaded.verify_preserved_tables,
                table_state=loaded.table_state,require=namespace['require'])
            rejected=False
            try:exec(after_code,env)
            except ValueError:rejected=True
            finally:
                if env.get('db') is not None:env['db'].close()
            if rejected!=(kind!='valid'):raise AssertionError('Actual postflight guard mismatch: '+kind)
            cases.append(dict(kind=kind,guard='actual_postflight_AST',rejected=rejected))
        for kind in ('valid','different_release','different_new_table_scope','different_old_table_set','different_source_count'):
            current=temp/('pre-'+kind);current.mkdir();release=current/'approved';release.mkdir()
            recovery=current/'recovery';recovery.mkdir();shutil.copyfile(backup,recovery/'accounts-before.sqlite3')
            candidate={'release':str(release),'new_empty_tables':allowed}
            preflight={'tables':before,'candidate_hashes_verified':1}
            manifest={'new_empty_tables':allowed,'sha256':{'fixed.py':'immutable'}}
            if kind=='different_release':candidate['release']=str(current/'unapproved')
            if kind=='different_new_table_scope':candidate['new_empty_tables']=['unwanted']
            if kind=='different_old_table_set':preflight['tables']={'unwanted':{}}
            if kind=='different_source_count':preflight['candidate_hashes_verified']=2
            (release/'candidate.json').write_text(json.dumps(candidate),encoding='utf-8')
            (release/'preflight.json').write_text(json.dumps(preflight),encoding='utf-8')
            env=dict(release=release,json=json,sqlite3=sqlite3,recovery=recovery,
                manifest=manifest,before=before,require=namespace['require'])
            rejected=False
            try:exec(before_code,env)
            except ValueError:rejected=True
            finally:
                if env.get('saved') is not None:env['saved'].close()
            if rejected!=(kind!='valid'):raise AssertionError('Actual preflight guard mismatch: '+kind)
            cases.append(dict(kind=kind,guard='actual_prelaunch_AST',rejected=rejected))
    if any(sha(Path(p))!=h for p,h in expected.items()):raise ValueError('Host inputs changed')
    result=dict(passed=True,cases=cases,groups=len(cases),source_sha256=expected,
        parent_runner_sha256=sha(Path(__file__)),actual_new_guard_AST_executed=True,
        launch_or_kernel_code_executed=False,old_schema_and_rows_negatives_verified=True,
        live_database=False,live_socket=False,service_changed=False,activation_authorized=False)
    (output/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(passed=True,groups=len(cases),launch_or_kernel_code_executed=False)))


if __name__=='__main__':
    main()
