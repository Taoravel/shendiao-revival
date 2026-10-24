"""Two disposable startup processes around reviewed native-adapter schemas.

No real server or database is stopped, started, authenticated or modified.
Default exit1 is the actual startup refusal; --expect-blocker classifies the
observed baseline without counting it as a functioning restart.
"""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
CONTEXT=ROOT/'staging/npc-repair-native-context-v1/context'
PVE=ROOT/'runtime/deployments/task-pve-20261024T053218Z'


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',default='parent_baseline')
    parser.add_argument('--phase',choices=('parent','child'),default='parent')
    parser.add_argument('--database',type=Path);parser.add_argument('--report',type=Path)
    parser.add_argument('--expect-blocker',action='store_true');args=parser.parse_args()
    manifest=json.loads((CONTEXT.parent/'manifest.json').read_text(encoding='utf8'))
    def verify():
        for name,digest in manifest['files'].items():assert sha(CONTEXT/name)==digest,name
        for name,digest in manifest['inputs'].items():assert sha(Path(name))==digest,name
    verify();sys.path.insert(0,str(CONTEXT))
    import inspect_client
    inspect_client.ROOT,inspect_client.OUT=ROOT.parent,CONTEXT
    from accounts import AccountStore
    import runtime_storage
    import equipment_gem_storage as sockets
    import equipment_gem_score_storage as scores
    if args.phase=='child':
        database=args.database.resolve();report=args.report.resolve()
        assert database.name=='disposable.sqlite3' and database.is_relative_to(ROOT/'evidence/npc-native-schema-reprepare')
        assert report.parent==database.parent and not report.exists()
        result=dict(process_id=__import__('os').getpid(),startup_completed=False,error=None)
        try:
            runtime_storage.prepare(AccountStore(database));result['startup_completed']=True
        except Exception as error:
            result['error']=type(error).__name__+': '+str(error)
            raise
        finally:
            verify();report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        return
    assert args.label.replace('_','').isalnum()
    output=ROOT/'evidence/npc-native-schema-reprepare'/args.label
    assert not output.exists(),'Preserve previous observations';output.mkdir(parents=True)
    database=output/'disposable.sqlite3';store=AccountStore(database)
    runtime_storage.prepare(store)
    with closing(store.connect()) as db,db:
        db.execute('BEGIN IMMEDIATE');sockets.prepare(db);scores.prepare(db)
    current_modules={}
    for name in ('npc_depot.py','npc_gameplay.py'):
        assert sha(PVE/'source'/name)==sha(CONTEXT/name),name
        current_modules[name]=sha(PVE/'source'/name)
    command=[sys.executable,'-X','utf8','-B',str(Path(__file__).resolve()),'--phase','child',
        '--database',str(database),'--report',str(output/'child.json')]
    child=subprocess.run(command,capture_output=True,text=True,encoding='utf8',timeout=100)
    (output/'child.stdout.txt').write_text(child.stdout,encoding='utf8')
    (output/'child.stderr.txt').write_text(child.stderr,encoding='utf8')
    recorded=json.loads((output/'child.json').read_text(encoding='utf8'))
    blocker=child.returncode==1 and recorded['error'].startswith('ValueError: Warehouse metadata preservation required for ')
    verify()
    result=dict(observed_blocker=blocker,actual_second_process_exit_code=child.returncode,
        second_process=recorded,parent_process_id=__import__('os').getpid(),
        original_prepare_passed=True,reviewed_native_source_tables_prepared=True,
        source_context=str(CONTEXT),context_manifest_sha256=sha(CONTEXT.parent/'manifest.json'),
        current_PVE_identical_consumers_sha256=current_modules,
        actual_current_PVE_startup_executed=False,real_server_restart_claimed=False,
        runtime_depot_data_or_permission_changed=False,
        real_database_or_service_or_GUI_access=False,probe_sha256=sha(Path(__file__)))
    assert result['parent_process_id']!=recorded['process_id']
    (output/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('Actual second disposable startup:',recorded['error'] or 'PASS')
    if args.expect_blocker:assert blocker,'Expected precise Warehouse metadata startup refusal'
    else:assert child.returncode==0,'Native dependency schemas currently prevent the next NPC startup'


if __name__=='__main__':main()
