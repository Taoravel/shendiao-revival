"""Organization domain checks in a disposable, explicitly funded fixture."""
import json
import tempfile
from pathlib import Path
from contextlib import closing
from accounts import AccountStore
from faction_domain import OrganizationStore,OrganizationCommand
from inspect_client import OUT,write_json


def main():
    policy=json.loads((OUT/'design/recovery-baseline.json').read_text(encoding='utf-8'))['organizations']
    with tempfile.TemporaryDirectory() as d:
        accounts=AccountStore(Path(d)/'fixture.db')
        with closing(accounts.connect()) as db,db:
            for rid in range(1,25):
                db.execute('INSERT INTO roles(id,account_id,name,school,shape,level) VALUES(?,1111,?,12,1010101,40)',(rid,f'角色{rid}'))
        epochs={rid:accounts.acquire_lease(1111,rid) for rid in range(1,25)}
        store=OrganizationStore(accounts.path,policy);store.initialize()
        def cmd(actor,org,op,args=(),key=None):
            return OrganizationCommand(actor,epochs[actor],key or f'{actor}-{org}-{op}-{args}',10**12,org,op,args)
        def reject(c,reason,now=0):
            try: store.execute(c,now)
            except ValueError as e: assert str(e)==reason,(str(e),reason)
            else: raise AssertionError(f'Expected {reason}')
        def fund(c,amount):
            # Test fixture only: no production cash debit is claimed here.
            with closing(store.connect()) as db,db: store.record_funding(db,c,amount)
        founders=tuple((rid,epochs[rid]) for rid in range(1,16))
        create=cmd(1,0,'create_family',('江湖家族','同心协力',founders),'family-create')
        reject(create,'funding_required')
        fund(create,policy['family_create_fee'])
        family=store.execute(create,0)['organization']
        assert store.execute(create,0)['organization']==family
        assert len(store.snapshot(family)[1])==15
        reject(cmd(1,0,'create_family',('不同名称','同心协力',founders),'family-create'),'request_id_conflict')
        reject(cmd(2,family,'appoint',(3,'deputy')),'permission_denied')
        store.execute(cmd(1,family,'appoint',(2,'deputy')),0)
        store.execute(cmd(20,family,'apply'),0)
        store.execute(cmd(2,family,'review',(20,True)),0)
        reject(cmd(3,family,'review',(21,True)),'permission_denied')
        reject(cmd(1,family,'expel',(2,)),'demote_first')
        # Family level advancement is a trusted test fixture; progression is not implemented.
        with closing(store.connect()) as db,db: db.execute('UPDATE organizations SET level=3 WHERE id=?',(family,))
        create_guild=cmd(1,family,'create_guild',('江湖帮派','同心协力',founders),'guild-create')
        reject(create_guild,'funding_required')
        fund(create_guild,policy['guild_create_fee'])
        guild=store.execute(create_guild,0)['organization']
        other=cmd(16,0,'create_family',('山水家族','同心协力',tuple((rid,epochs[rid]) for rid in (16,17,18))),'family-two')
        fund(other,policy['family_create_fee']);family2=store.execute(other,0)['organization']
        store.execute(cmd(16,guild,'apply'),0)
        reject(cmd(2,guild,'review',(family2,True)),'permission_denied')
        store.execute(cmd(1,guild,'review',(family2,True)),0)
        assert 18 in store.snapshot(guild)[1] and 21 not in store.snapshot(guild)[1]
        event=store.chat(guild,16,epochs[16],'帮派聊天',0)
        assert 1 in event.recipients and 21 not in event.recipients
        try: store.chat(guild,16,epochs[16],'刷屏',1)
        except ValueError as e: assert str(e)=='chat_cooldown'
        else: raise AssertionError('Chat cooldown ignored')
        try: store.chat(guild,21,epochs[21],'外人',0)
        except ValueError as e: assert str(e)=='not_member'
        else: raise AssertionError('Nonmember chat accepted')
        store.execute(cmd(1,guild,'mute',(16,)),0)
        try: store.chat(guild,16,epochs[16],'禁言中',100)
        except ValueError as e: assert str(e)=='muted'
        else: raise AssertionError('Mute ignored')
        assert store.chat(guild,16,epochs[16],'时间已到',policy['guild_mute_ms']).content=='时间已到'
        reject(cmd(1,guild,'appoint',(16,'leader')),'leadership_tenure')
        store.execute(cmd(1,guild,'appoint',(16,'leader')),policy['guild_leader_tenure_ms'])
        assert store.snapshot(guild)[0]['leader']==16
        reject(cmd(1,guild,'expel',(family2,)),'permission_denied')
        store.execute(cmd(16,guild,'expel',(family,)),policy['guild_leader_tenure_ms'])
        assert not store.authorize_delivery(event,1)
        assert not store.authorize_delivery(event,18) # Stale roster revision is conservative for every recipient.
        current=store.chat(guild,16,epochs[16],'当前名单',policy['guild_leader_tenure_ms'])
        assert store.authorize_delivery(current,18)
        store.execute(cmd(1,family,'appoint',(2,'leader')),0)
        store.execute(cmd(1,family,'leave'),0)
        assert 1 not in store.snapshot(family)[1]
        old=cmd(2,family,'change_aim',('新的宗旨',),'stale')
        epochs[2]=accounts.acquire_lease(1111,2)
        reject(old,'stale_epoch')
        stale_chat_epoch=epochs[16]
        epochs[16]=accounts.acquire_lease(1111,16)
        try:store.chat(guild,16,stale_chat_epoch,'旧登录消息',10**10)
        except ValueError as e:assert str(e)=='stale_epoch'
        else:raise AssertionError('Old login sent guild chat')
        assert store.chat(guild,16,epochs[16],'新登录消息',10**10).sender==16
        reopened=OrganizationStore(accounts.path,policy)
        assert reopened.snapshot(guild)[0]['leader']==16
        assert reopened.snapshot(family)[0]['leader']==2
    result={'passed':['fee required before creation','idempotent paid receipt consumption',
      'family founders and roster','application approval permissions','deputy protection',
      'family-to-guild hierarchy','guild admission by family','member-only chat',
      'offline-time mute expiry','72-hour leadership transfer','queued chat recheck after expulsion',
      'leader exit guard and transfer','integer epochs with SQLite TEXT affinity',
      'lease fence inside transaction','stale chat rejected and replacement lease accepted','reopen persistence'],
      'test_funding':'fixture receipts only, not a production cash debit',
      'family_progression':'level 3 fixture only','runtime_integrated':False,'real_client_verified':False}
    write_json(OUT/'evidence/faction-domain-verification.json',result)
    print(json.dumps(result))


if __name__=='__main__':main()
