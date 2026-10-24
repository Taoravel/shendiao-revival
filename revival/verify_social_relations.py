"""Friend request ownership, durable acceptance, grouping and blacklist checks."""
import json
import struct
import tempfile
from pathlib import Path
from types import MappingProxyType
from accounts import AccountStore
from social_owner import *
from inspect_client import OUT,write_json
import social_protocol as p


def main():
    with tempfile.TemporaryDirectory() as d:
        accounts=AccountStore(Path(d)/'t.db')
        roles=[accounts.create_role(1111,n,12,1010101) for n in ('申请甲','审批乙','旁观丙')]
        snapshots=[RoleSnapshot(r['id'],i+10,r['name'],1,12,1010101,1007) for i,r in enumerate(roles)]
        with closing(accounts.connect()) as db,db:
            db.executemany('INSERT INTO role_leases VALUES(?,?,1)',[(s.role_id,str(s.login_epoch)) for s in snapshots])
        online=MappingProxyType({s.role_id:s for s in snapshots})
        store=SQLiteSocialStore(accounts.path);store.initialize()
        owners=[RoleSocialOwner(s,store,2,256) for s in snapshots]
        a,b,c=owners;ra,rb,rc=roles
        def execute(owner,kind,body,key='cmd'):
            s=owner.snapshot
            return owner.execute(SocialCommand(s.role_id,s.login_epoch,key,1000,kind,body),online,0)
        req=p.text('一起闯江湖')+struct.pack('>Q',rb['id'])
        result=execute(a,p.REQUEST_SEND,req,'application-1')
        assert result.effects==(Delivery(rb['id'],11,p.REQUEST_RECEIVE,p.request_notice(ra,'一起闯江湖')),)
        assert store.friends(ra['id'])==[] and store.friends(rb['id'])==[]
        assert execute(a,p.REQUEST_SEND,req,'application-1').effects==()
        assert execute(a,p.REQUEST_SEND,p.text('篡改')+struct.pack('>Q',rb['id']),'application-1').rejection=='request_id_conflict'
        assert execute(c,p.AGREE_SEND,struct.pack('>Q',ra['id'])).rejection=='request_not_pending'
        assert b.pending_notices().effects==result.effects
        accepted=execute(b,p.AGREE_SEND,struct.pack('>Q',ra['id']))
        assert len(accepted.effects)==1 and isinstance(accepted.effects[0],RelationWake)
        assert store.friends(ra['id'])==[]
        reopen=SQLiteSocialStore(accounts.path)
        wake=reopen.relation_events(ra['id'])[0]
        assert a.apply_relation(RelationWake(rc['id'],wake.event_id),online).rejection=='wrong_owner'
        applied=a.apply_relation(wake,online)
        assert applied.effects==(Delivery(ra['id'],10,p.ADD_RECEIVE,p.friend_added(rb,True,p.GROUP_FRIEND)),)
        assert len(reopen.friends(ra['id']))==1 and reopen.friends(rb['id'])==[]
        assert a.apply_relation(wake,online).effects==() and reopen.relation_events(ra['id'])==()
        assert execute(b,p.AGREE_SEND,struct.pack('>Q',ra['id'])).effects==accepted.effects
        assert execute(a,p.REQUEST_SEND,req,'application-1').effects==() and b.pending_notices().effects==()
        assert execute(c,p.REQUEST_SEND,p.text('你好')+struct.pack('>Q',rb['id']),'application-c').effects
        refusal=execute(b,p.REFUSE_SEND,p.text('')+struct.pack('>Q',rc['id']))
        assert c.apply_relation(refusal.effects[0],online).effects[0].kind==p.REFUSE_RECEIVE
        assert reopen.friends(rc['id'])==[]
        move=p.text(p.GROUP_BLACK)+struct.pack('>Q',rb['id'])+p.text('')
        assert execute(a,p.MOVE_GROUP_SEND,move).effects[0].body==p.moved_group(rb['id'],p.GROUP_BLACK)
        assert reopen.blocked(ra['id'],rb['id'])
        assert reopen.friends(ra['id'])[0]['group_name']==p.GROUP_BLACK
        assert a.initial(online).effects[0].body==b'\x01'+p.friend_info(rb,True,p.GROUP_BLACK)+bytes(4)
        incoming=Delivery(ra['id'],10,p.PRIVATE_RECEIVE,p.private_message(rb,'你好'))
        assert not a.filter_delivery(incoming)
        assert not a.filter_delivery(Delivery(ra['id'],10,p.REQUEST_RECEIVE,p.request_notice(rb,'排队中的申请')))
        assert not a.filter_delivery(Delivery(ra['id'],9,p.PRIVATE_RECEIVE,p.private_message(rc,'旧会话')))
        assert a.filter_delivery(Delivery(ra['id'],10,p.PRIVATE_RECEIVE,p.private_message(rc,'你好')))
        assert not a.filter_delivery(Delivery(ra['id'],10,p.CHAT_RECEIVE,p.chat_message(rb,5,'世界')))
        private=struct.pack('>Q',ra['id'])+p.text('你好')+p.text('')+bytes(5)
        assert execute(b,p.PRIVATE_SEND,private).rejection=='peer_blocked'
        assert execute(b,p.REQUEST_SEND,p.text('')+struct.pack('>Q',ra['id']),'blocked-request').rejection=='recipient_blocked'
        assert reopen.watchers(rb['id'])==()
        unblocked=execute(a,p.UNBLOCK_SEND,struct.pack('>Q',rb['id']))
        assert unblocked.effects[0].kind==p.UNBLOCK_RECEIVE
        assert not reopen.blocked(ra['id'],rb['id']) and reopen.friends(ra['id'])==[]
        assert a.filter_delivery(incoming)
        # Offline requests remain pending; no unbounded in-memory notification queue.
        without_b=MappingProxyType({s.role_id:s for s in snapshots if s.role_id!=rb['id']})
        offline=a.execute(SocialCommand(ra['id'],10,'offline-request',1000,p.REQUEST_SEND,req),without_b,0)
        assert offline.effects==() and b.pending_notices().effects
        # Receiver inbox capacity is explicit, checked transactionally.
        store.request(ra['id'],rc['id'],'甲',1,'capacity-a')
        try: store.request(rb['id'],rc['id'],'乙',1,'capacity-b')
        except ValueError as error: assert str(error)=='request_inbox_full'
        else: raise AssertionError('Pending request capacity was ignored')
        # A failed contact grant leaves its durable acceptance event available.
        retry_wake=execute(b,p.AGREE_SEND,struct.pack('>Q',ra['id'])).effects[0]
        try: store.apply_relation_event(ra['id'],retry_wake.event_id,0)
        except ValueError as error: assert str(error)=='contact_limit'
        else: raise AssertionError('Contact limit was ignored')
        assert retry_wake in store.relation_events(ra['id'])
        assert a.apply_relation(retry_wake,online).effects[0].kind==p.ADD_RECEIVE
        assert execute(a,p.MOVE_GROUP_SEND,p.text('任意注入组')+struct.pack('>Q',rb['id'])+p.text('')).rejection
        assert execute(a,p.AGREE_SEND,b'\0').rejection
        assert execute(a,p.REQUEST_SEND,p.text('你好')+b'\0').rejection
        # Same old in-memory snapshot after reconnect must not write to storage.
        with closing(accounts.connect()) as db,db:
            db.execute('UPDATE role_leases SET epoch=? WHERE role_id=?',('replacement-epoch',ra['id']))
        result=execute(a,p.DELETE_SEND,struct.pack('>Q',rb['id'])+p.text(''),'stale-delete')
        assert result.rejection=='StaleEpoch'
        assert reopen.friends(ra['id'])[0]['id']==rb['id']
    result={'passed':['pending requests survive reopen','request id retries and conflicts',
        'approval restricted to recipient','approval durable outbox before applicant-owned write',
        'idempotent application and forged wake refusal','refuse without contacts','native named groups',
        'persistent blacklist','recipient filter for private/public chat','stale epoch filter',
        'block friend requests','unblock removal','offline pending recovery',
        'bounded request inbox','failed grant preserves outbox retry','malformed packets rejected',
        'old snapshot cannot write after database lease replacement'],
        'shared_runtime_integrated':False,'real_client_verified':False}
    write_json(OUT/'evidence/social-relations-verification.json',result)
    print(json.dumps(result))


if __name__=='__main__':main()
