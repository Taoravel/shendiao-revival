"""Reproduce a frozen release's missing Jiaxing continuation in a temp DB.

Imports the requested source without starting its runner/listener. Original
resources are read only, and no client or real account database is opened.
Exit 1 means the expected next task is missing; that is the reported defect.
"""
import argparse
import asyncio
from contextlib import closing,nullcontext
import hashlib
import json
from pathlib import Path
import sys
import tempfile


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--database',type=Path,help='Optional NEW disposable DB retained for a recovery check')
    args=parser.parse_args()
    source=args.source.resolve();report_path=args.report.resolve()
    if source==report_path or source in report_path.parents:
        raise ValueError('Report must be outside the frozen source')
    database=args.database.resolve() if args.database else None
    if database is not None and (database.exists() or source in database.parents):
        raise ValueError('Probe database must be a new disposable path outside the release')
    names=('game_runtime.py','runtime_storage.py','task_chains.py','task_master_card.py')
    hashes={name:hashlib.sha256((source/name).read_bytes()).hexdigest() for name in names}
    sys.path.insert(0,str(source))
    import inspect_client
    inspect_client.ROOT=Path(__file__).resolve().parents[1]
    inspect_client.OUT=source
    from accounts import AccountStore
    from verify_jiaxing_story_boundary_runtime import check
    from verify_master_commit_card_runtime import check as native_master_prefix
    import verify_newbie_cart_runtime
    from world_newbie import load_newbie_routes
    import runtime_storage
    if Path(runtime_storage.__file__).resolve().parent!=source:
        raise ValueError('Probe accidentally imported workspace runtime')
    # This release retained an outdated test helper waiting for DialogEnd.
    # Use the task-owned original-CCommit checker, importing the frozen runtime.
    # This is an explicit harness replacement, not a gameplay-source overlay.
    import verify_master_commit_card_runtime
    helper=Path(verify_master_commit_card_runtime.__file__).resolve()
    helper_hash=hashlib.sha256(helper.read_bytes()).hexdigest()
    verify_newbie_cart_runtime.master_prefix=native_master_prefix
    route=load_newbie_routes()[(9,11)]
    audit=json.loads((source/'evidence/newbie-birth-sites-audit.json').read_text(encoding='utf-8'))
    witness=next(row for row in audit['routes'] if (row['character_id'],row['school_id'])==(9,11))
    folder=nullcontext(str(database.parent)) if database else tempfile.TemporaryDirectory(prefix='jiaxing-release-continuation-')
    with folder as directory:
        store=AccountStore(database or Path(directory)/'isolated.sqlite3')
        prepared=runtime_storage.prepare(store)
        role=store.create_role(1111,'嘉兴断点复现',11,1010109)
        boundary=asyncio.run(check(store,prepared,role,route,witness))
        with closing(store.connect()) as db:
            active=[row[0] for row in db.execute(
                "SELECT task_id FROM task_journal WHERE role_id=? AND state='active'",(role['id'],))]
            effect=json.loads(db.execute('SELECT payload FROM task_effects WHERE role_id=? AND task_id=100160',
                (role['id'],)).fetchone()[0])
        record=dict(source=str(source),source_sha256=hashes,original_boundary=boundary,test_role_id=role['id'],
            active_tasks=active,expected_continuation=100106,
            chain={key:effect[key] for key in ('chain_status','chain_reason','chain_target','chain_resolved')},
            harness_adaptation='Replace stale synthetic-DialogEnd master test prefix with task-owned native-CCommit checker; all gameplay imports from frozen release',
            harness_helper=dict(path=str(helper),sha256=helper_hash),
            continuation_available=100106 in active,database='disposable',
            live_server_changed=False,real_database_opened=False,client_launched=False,battle_executed=False,
            limits=['Natural server/codec prefix uses original-clear movement witnesses, not native GUI',
                'Historical frozen release reproduction; no claim that the workspace candidate is deployed'])
    assert hashes=={name:hashlib.sha256((source/name).read_bytes()).hexdigest() for name in hashes}
    assert hashlib.sha256(helper.read_bytes()).hexdigest()==helper_hash
    record['source_unchanged_during_check']=True
    report_path.parent.mkdir(parents=True,exist_ok=True)
    report_path.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({key:record[key] for key in
        ('active_tasks','expected_continuation','chain','continuation_available','source_unchanged_during_check')},
        ensure_ascii=False))
    assert record['continuation_available'], 'Storyteller completed but no next task100106: reported Jiaxing blockage reproduced'


if __name__=='__main__':main()
