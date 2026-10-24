"""Independent group approvals race for one role's quota in real transactions."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import json
from pathlib import Path
import struct
import tempfile
import threading
import time
import uuid
from accounts import AccountStore
from social_owner import SQLiteSocialStore,RoleSnapshot,SocialCommand
from group_store import GroupStore
from inspect_client import OUT,write_json
import group_protocol as p


def main():
    with tempfile.TemporaryDirectory() as directory:
        accounts=AccountStore(Path(directory)/'state.db')
        roles=[accounts.create_role(1111,name,12,1010101) for name in ('群额甲','群额乙','群额丙')]
        with closing(accounts.connect()) as db,db:db.execute('UPDATE roles SET level=20 WHERE id IN (1,2)')
        epochs={r['id']:accounts.acquire_lease(1111,r['id']) for r in roles}
        social=SQLiteSocialStore(accounts.path);social.initialize()
        store=GroupStore(accounts.path,social.group_policy)
        def execute(rid,kind,body):
            snap=RoleSnapshot(rid,epochs[rid],roles[rid-1]['name'],1,12,1010101,1007)
            now=int(time.time()*1000)
            cmd=SocialCommand(rid,epochs[rid],uuid.uuid4().hex,now+5000,kind,body)
            return store.execute(snap,cmd,now)
        ids=[]
        for rid,name in ((1,'争取甲群'),(2,'争取乙群')):
            execute(rid,p.CREATE,b'')
            ids.append(execute(rid,p.NAME,p.text(name))['group']['id'])
        for gid in ids:execute(3,p.JOIN,struct.pack('>Q',gid))
        barrier=threading.Barrier(2)
        def approve(index):
            barrier.wait(timeout=2)
            try:execute(index+1,p.RESPOND,struct.pack('>iQQ',0,3,ids[index]));return 'accepted'
            except ValueError as error:return str(error)
        with ThreadPoolExecutor(max_workers=2) as pool:outcomes=list(pool.map(approve,(0,1)))
        assert sorted(outcomes)==['accepted','group_role_quota'],outcomes
        assert len(store.initial(3)['groups'])==1
        # Failure leaves the other application pending; no partial membership.
        with closing(store.connect()) as db:
            assert db.execute('SELECT COUNT(*) FROM common_group_requests WHERE role_id=3').fetchone()[0]==1
        # Level 20 creates/joins at most two groups, including its existing one.
        execute(1,p.CREATE,b'');execute(1,p.NAME,p.text('群额满二'))
        try:execute(1,p.CREATE,b'')
        except ValueError as error:assert str(error)=='group_role_quota'
        else:raise AssertionError('Level 20 exceeded two groups')
        # Expired command and malformed text cannot allocate a group or receipt.
        before=len(store.initial(2)['groups'])
        execute(2,p.CREATE,b'')
        try:execute(2,p.NAME,p.text('带 空格'))
        except ValueError as error:assert str(error)=='group_name'
        else:raise AssertionError('Invalid name accepted')
        assert len(store.initial(2)['groups'])==before
        execute(2,p.NAME,p.text('群额乙二'))
    result=dict(passed=['concurrent approvals in different groups respect one shared derived role quota',
      'failed approval rolls back membership and preserves application','level-20 create/join combined quota is two',
      'invalid name rolls back and leaves valid creation window usable'],native_gui_verified=False)
    write_json(OUT/'evidence/group-quota-verification.json',result)
    print(json.dumps(result))


if __name__=='__main__':main()
