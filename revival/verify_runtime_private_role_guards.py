"""Actual login-storage Seam rejects unknown or foreign private identity."""
import asyncio
from contextlib import closing
from pathlib import Path
import tempfile
from accounts import AccountStore
from inspect_client import OUT,write_json
from verify_runtime_private_role import fixtures
import runtime_storage


def state(store):
    with closing(store.connect()) as db:
        names=[row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        return tuple((name,tuple(db.execute('SELECT * FROM "'+name.replace('"','""')+'" ORDER BY rowid')))
            for name in names)


def main():
    with tempfile.TemporaryDirectory(prefix='private-role-guards-') as folder:
        store=AccountStore(Path(folder)/'roles.sqlite3');prepared=runtime_storage.prepare(store)
        entries,_=asyncio.run(fixtures(store,prepared))
        role,entry=entries[0];role_id=role['id']
        epoch=store.acquire_lease(1111,role_id)
        recovered=runtime_storage.prepare_login_map_recovery(store,1111,role_id,epoch)
        assert recovered.checkpoint.address==entry.address
        def refused(account=1111,lease=epoch):
            before=state(store)
            try:runtime_storage.prepare_login_map_recovery(store,account,role_id,lease)
            except ValueError:pass
            else:raise AssertionError('Unknown, stale or foreign private checkpoint was admitted')
            assert state(store)==before, 'Rejected private login rewrote durable state'
        refused(account=2222)
        new_epoch=store.acquire_lease(1111,role_id)
        refused(lease=epoch)
        epoch=new_epoch
        with closing(store.connect()) as db,db:
            db.execute('UPDATE world_instance_positions SET instance_id=? WHERE role_id=?',
                (entries[1][1].address.instance_id,role_id))
        refused(lease=epoch)
        with closing(store.connect()) as db,db:
            db.execute('UPDATE world_instance_positions SET instance_id=? WHERE role_id=?',
                (entry.address.instance_id,role_id))
            db.execute('DELETE FROM world_story_instances WHERE role_id=?',(role_id,))
        refused(lease=epoch)
    report=dict(passed=['current exact checkpoint validates its durable original chapter and directory',
        'foreign account and old lease reject without writes',
        'another role instance and missing directory reject without public fallback, allocation or repair'],
        controlled_persistence_faults=True,native_gui_verified=False,live_server_changed=False,battle_executed=False)
    write_json(OUT/'evidence/runtime-private-role-guards-verification.json',report);print(report)


if __name__=='__main__':main()
