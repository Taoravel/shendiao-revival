"""Social owner isolation and immutable effect contracts, without Sessions."""
import json
import struct
import tempfile
from pathlib import Path
from threading import Event
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from types import MappingProxyType
from accounts import AccountStore
from social_owner import (RoleSnapshot,SocialCommand,RoleSocialOwner,SQLiteSocialStore,
                          RoleMailbox,Delivery,Publish)
import social_protocol as p
from inspect_client import OUT,write_json


def main():
    with tempfile.TemporaryDirectory() as d:
        path=Path(d)/'accounts.db'
        accounts=AccountStore(path)
        a=accounts.create_role(1111,'所有者甲',12,1010101)
        b=accounts.create_role(1111,'所有者乙',12,1010101)
        def snapshot(r,epoch):
            return RoleSnapshot(r['id'],epoch,r['name'],r['level'],r['school'],r['shape'],1007)
        sa,sb=snapshot(a,7),snapshot(b,8)
        with closing(accounts.connect()) as db,db:
            db.executemany('INSERT INTO role_leases VALUES(?,?,1)',[(sa.role_id,'7'),(sb.role_id,'8')])
        online=MappingProxyType({sa.role_id:sa,sb.role_id:sb})
        store=SQLiteSocialStore(path);store.initialize()
        policy=json.loads((OUT/'design/recovery-baseline.json').read_text(encoding='utf-8'))['social']
        def owner(s,repository=store):
            return RoleSocialOwner(s,repository,policy['max_contacts_per_role'],policy['max_text_characters'])
        def command(s,k,body,epoch=None,deadline=100):
            return SocialCommand(s.role_id,s.login_epoch if epoch is None else epoch,'request-1',deadline,k,body)
        mailbox=RoleMailbox(sa.role_id,sa.login_epoch,1)
        lookup=command(sa,p.SEARCH_ID_SEND,struct.pack('>Q',b['id']))
        assert mailbox.submit(lookup)=='accepted' and mailbox.submit(lookup)=='backpressure'
        assert mailbox.submit(command(sa,p.SEARCH_ID_SEND,bytes(8),epoch=6))=='stale_epoch'
        oa,ob=owner(sa),owner(sb)
        assert oa.execute(lookup,online,101).rejection=='deadline'
        assert oa.execute(command(sa,p.ADD_SEND,struct.pack('>Q',b['id'])+p.text(''),epoch=6),online,0).rejection=='stale_epoch'
        assert store.friends(a['id'])==[]
        add=command(sa,p.ADD_SEND,struct.pack('>Q',b['id'])+p.text(''))
        assert oa.execute(add,online,0).effects[0].kind==p.ADD_RECEIVE
        assert oa.execute(add,online,0).effects[0].kind==p.ADD_RECEIVE
        assert len(SQLiteSocialStore(path).friends(a['id']))==1
        assert store.watchers(b['id'])==(a['id'],)
        private=command(sa,p.PRIVATE_SEND,struct.pack('>Q',b['id'])+p.text('你好')+p.text('')+bytes(5))
        result=oa.execute(private,online,0)
        assert result.effects==(Delivery(b['id'],8,p.PRIVATE_RECEIVE,p.private_message(a,'你好')),)
        chat=command(sa,p.CHAT_SEND,struct.pack('>i',2)+p.text('当前')+p.text('')+b'\0')
        assert oa.execute(chat,online,0).effects==(Publish('scene',1007,a['id'],p.CHAT_RECEIVE,p.chat_message(a,2,'当前')),)
        assert oa.initial(online).effects[0].body==b'\x01'+p.friend_info(b,True,p.GROUP_FRIEND)+bytes(4)
        # Controlled slow persistence on one role must not serialize another owner.
        entered,released=Event(),Event()
        class SlowStore:
            def find(self,*args):
                entered.set()
                if not released.wait(3): raise TimeoutError('test release missing')
                return store.find(*args)
        slow=owner(sa,SlowStore())
        with ThreadPoolExecutor(max_workers=2) as workers:
            pending=workers.submit(slow.execute,lookup,online,0)
            try:
                assert entered.wait(1)
                fast=workers.submit(ob.execute,command(sb,p.SEARCH_ID_SEND,struct.pack('>Q',a['id'])),online,0)
                assert fast.result(timeout=1).effects[0].kind==p.SEARCH_ID_RECEIVE
                assert not pending.done()
            finally: released.set()
            assert pending.result(timeout=1).effects[0].kind==p.SEARCH_ID_RECEIVE
    result={'passed':['bounded per-role mailbox','stale login epoch rejected before persistence',
        'deadline rejected','durable idempotent contacts','presence paged index',
        'immutable epoch-addressed private delivery','channel partition effect',
        'friend initialization','independent owners during controlled slow persistence'],
        'shared_network_runtime_migrated':False,'commercial_capacity_tested':False}
    write_json(OUT/'evidence/social-owner-verification.json',result)
    print(json.dumps(result))


if __name__=='__main__':main()
