"""Frozen-release pending journal -> current public recovery, temp database only.

Tests the user's already-completed storyteller state rather than asking for a
second completion. It grants no private transfer, battle, skill or reward.
"""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def rows(store):
    with closing(store.connect()) as db:
        names=[row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        selected=[name for name in names if name in ('roles','role_progress','role_growth','role_positions',
            'position_versions','role_resources') or name.startswith(('inventory_','currency_','role_wallet'))]
        return {name:tuple(sorted(map(repr,db.execute('SELECT * FROM "'+name+'"')))) for name in selected}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True)
    args=parser.parse_args()
    root=Path(__file__).resolve().parent
    current=('task_prologue_touch.py','task_domain.py','task_conversation.py','runtime_storage.py')
    hashes={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in current}
    from accounts import AccountStore
    from task_persistence import load_task_state
    from task_protocol import decode_accept_scenario_quest
    import runtime_storage
    with tempfile.TemporaryDirectory(prefix='jiaxing-frozen-to-recovery-') as folder:
        folder=Path(folder);database=folder/'new-isolated.sqlite3';old_report=folder/'old.json'
        command=[sys.executable,'-B','-X','utf8',str(root/'verify_jiaxing_pending_release.py'),
            '--source',str(args.source.resolve()),'--report',str(old_report),'--database',str(database)]
        old=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',timeout=60)
        assert old.returncode==1 and old_report.exists(), old.stdout+old.stderr
        original=json.loads(old_report.read_text(encoding='utf-8'))
        assert not original['continuation_available'] and original['active_tasks']==[]
        store=AccountStore(database);runtime_storage.prepare(store)
        before=rows(store);rid=original['test_role_id'];epoch=store.acquire_lease(1111,rid)
        runtime_storage.load_role(store,1111,rid,epoch,store.task_resources)
        with closing(store.leased(1111,rid,epoch).connect()) as db,db:
            db.execute('BEGIN');old_state=load_task_state(db,1111,rid,epoch)[1]
            assert 100160 in old_state.completed and 100106 not in old_state.active|old_state.completed
        first=runtime_storage.prologue_resume(store,1111,rid,epoch)
        assert tuple((decode_accept_scenario_quest(body).quest_id,decode_accept_scenario_quest(body).state)
            for _,body in first)==((100106,0),)
        second=runtime_storage.prologue_resume(store,1111,rid,epoch)
        assert second==first, 'Recovery reset or lost the existing bloodmark bean'
        with closing(store.leased(1111,rid,epoch).connect()) as db,db:
            db.execute('BEGIN');state=load_task_state(db,1111,rid,epoch)[1]
            assert state.completed==old_state.completed and state.active==frozenset((100106,))
            assert db.execute('SELECT COUNT(*) FROM task_effects WHERE role_id=? AND task_id=100160',(rid,)).fetchone()==(1,)
            assert db.execute('SELECT COUNT(*) FROM task_prologue_touches WHERE role_id=?',(rid,)).fetchone()==(0,)
        assert rows(store)==before, 'Pending recovery changed assets, growth or position'
        report=dict(passed=['Frozen36632 natural prefix reproduces completed100160 with empty active journal',
            'Current public load and explicit prologue_resume restore only original100106 active0',
            'Repeated recovery preserves completed journal, original100160 receipt and current assets/position'],
            frozen_reproduction=original,source_sha256=hashes,
            database='disposable frozen-release state retained across two interpreter processes',
            live_server_changed=False,real_database_opened=False,native_gui_verified=False,battle_executed=False,
            limits=['Public task/persistence recovery only; shared opt-in and deployment remain integrator work',
                'No claim of automatic CG or private-map entry immediately after storyteller'])
    assert hashes=={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in hashes}
    report['source_unchanged_during_check']=True
    (root/'evidence/jiaxing-pending-recovery-verification.json').write_text(
        json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({key:report[key] for key in ('passed','source_unchanged_during_check')},ensure_ascii=False))


if __name__=='__main__':main()
