"""Per-group bounded owners, immutable delivery capabilities, no target waits."""
import time
import struct
import asyncio
from contextlib import closing
from dataclasses import dataclass,replace
from runtime_core import SerialOwner,Backpressure
from wire import NeedMoreData
from social_owner import Delivery,SocialResult
from group_store import GroupStore
import group_protocol as p


@dataclass(frozen=True)
class GroupDelivery(Delivery):
    group_id: int
    generation: str
    version: int
    sender: int = 0
    invitation_token: str = ''


@dataclass(frozen=True)
class GroupHistoryDelivery(GroupDelivery):
    # Frozen tuples only; no worker shares mutable row dictionaries.
    records: tuple = ()
    page: int = 1
    last: bool = True


class GroupRuntime:
    def __init__(self,social,policy):
        self.social,self.rt=social,social.rt
        self.store=GroupStore(self.rt.social_store.path,policy)
        self.policy=self.store.policy
        self.owners={}
        self.inflight=set()
        self.closing=False

    def _key(self,command):
        if command.kind in (p.CREATE,p.NAME,p.SEARCH):return ('group-role',command.role_id)
        if command.kind==p.RESPOND:gid=p.response_request(command.body)[2]
        elif command.kind==p.SEND:gid=p.message_request(command.body)[0]
        elif command.kind in (p.INVITE,p.EXPEL):gid=p.member_request(command.body)[1]
        elif command.kind==p.INVITE_REPLY:gid=p.invite_reply(command.body)[1]
        elif command.kind==p.MANAGER:gid=p.manager_request(command.body)[1]
        elif command.kind==p.CONFIG:gid=p.config_request(command.body)[0]
        elif command.kind==p.HISTORY:gid=p.history_request(command.body)[0]
        else:gid=p.identity(command.body)
        if not 0<gid<2**63:raise ValueError('group_id_range')
        return ('group',gid)

    async def request(self,snapshot,command,now):
        if self.closing:raise Backpressure('Group runtime closing')
        try:key=self._key(command)
        except (ValueError,NeedMoreData,struct.error):return SocialResult(rejection='group_invalid_packet')
        entry=self.owners.get(key)
        if entry is None:
            if len(self.owners)>=self.policy['owner_limit']:raise Backpressure('Active group owners full')
            entry=dict(refs=0,poisoned=False)
            async def handle(work):
                if entry['poisoned']:raise TimeoutError('Group commit outcome pending; reload required')
                s,cmd,stamp=work.args
                try:result=await self.rt.io.run(key,self.store.execute,s,cmd,stamp)
                except TimeoutError:
                    entry['poisoned']=True
                    raise
                except (ValueError,NeedMoreData,struct.error) as error:return SocialResult(rejection=str(error) or 'group_invalid_packet')
                # Fan-out is enqueue-only. The recipient alone checks its lease,
                # current member generation, group version and blacklist.
                for index,effect in enumerate(self.deliveries(result,s,self.rt.online_snapshot())):
                    self.social.offer(effect)
                    if index%32==31:
                        await asyncio.sleep(0)
                return SocialResult()
            entry['owner']=SerialOwner(key,handle,capacity=self.policy['mailbox_capacity'])
            self.owners[key]=entry
        entry['refs']+=1
        async def invoke():
            try:
                return await entry['owner'].call('request',snapshot,command,now,request_id=command.request_id,
                    deadline=time.monotonic()+max(0,(command.deadline_ms-int(time.time()*1000))/1000))
            finally:
                entry['refs']-=1
                if not entry['refs'] and not entry['poisoned']:
                    # Accepted work retains ownership even if its caller stops
                    # waiting. A replacement actor cannot overtake its commit.
                    del self.owners[key]
                    await entry['owner'].close()
        pending=asyncio.create_task(invoke())
        self.inflight.add(pending)
        def completed(task):
            self.inflight.discard(task)
            if not task.cancelled():task.exception()
        pending.add_done_callback(completed)
        return await asyncio.shield(pending)

    def deliveries(self,result,s,online):
        mode=result['mode']
        own=online.get(s.role_id)
        if own is None or own.login_epoch!=s.login_epoch:return ()
        if mode=='ready':return (Delivery(s.role_id,s.login_epoch,p.CREATE_READY,b''),)
        g=result['group']
        if mode=='searched':return (Delivery(s.role_id,s.login_epoch,p.SEARCHED,p.searched(g)),)
        if result['replayed']:
            # Durable state is recovered at login. Never rebroadcast cached chat,
            # pending notices or departure packets using stale roster snapshots.
            return ()
        if mode=='silent':return ()
        if mode=='invited':
            target=online.get(result['target'])
            effects=[Delivery(s.role_id,s.login_epoch,p.INVITE_ACK,struct.pack('>Q',result['target']))]
            if target:effects.append(GroupDelivery(target.role_id,target.login_epoch,p.INVITED,
                p.invited(g['id'],result['name'],g['name']),g['id'],'',g['version'],0,result['token']))
            return tuple(effects)
        if mode in ('personal_config','history'):
            membership=next(m for m in g['members'] if m['id']==s.role_id)
            if mode=='personal_config':return (GroupDelivery(s.role_id,s.login_epoch,p.CONFIGURED,p.configured(g,s.role_id),
                g['id'],membership['generation'],g['version']),)
            records=tuple((r['sender'],r['plain'],r['name'],r['timestamp']) for r in result['records'])
            return (GroupHistoryDelivery(s.role_id,s.login_epoch,p.HISTORY_PAGE,b'',g['id'],membership['generation'],
                g['version'],records=records,page=result['page'],last=result['last']),)
        effects=[]
        if mode=='created':effects.append(Delivery(s.role_id,s.login_epoch,p.CREATED,p.created(g['id'],g['name'])))
        if mode=='left':
            departed=online.get(result['departed'])
            if departed:effects.append(GroupDelivery(departed.role_id,departed.login_epoch,p.LEFT,
                struct.pack('>Q',g['id']),g['id'],'',0))
        if mode=='dissolved':
            targets=g['members']
            kind,body=p.LEFT,struct.pack('>Q',g['id'])
        elif mode=='requested':
            targets=[m for m in g['members'] if m['id']==g['owner'] or m['manager']]
            kind,body=p.JOIN_NOTICE,p.join_notice(result['applicant'],g['id'],result['name'])
        elif mode=='message':
            targets=g['members']
            kind,body=p.MESSAGE,p.message(g['id'],result['name'],result['plain'],result['timestamp'])
        else:
            targets=g['members']
            kind,body=p.UPDATED,p.updated(g,online)
        for member in targets:
            target=online.get(member['id'])
            if target:
                if kind==p.UPDATED:body=p.updated(g,online,target.role_id)
                if mode=='configured':effects.append(GroupDelivery(target.role_id,target.login_epoch,p.CONFIGURED,
                    p.configured(g,target.role_id),g['id'],member['generation'],g['version']))
                effects.append(GroupDelivery(target.role_id,target.login_epoch,kind,body,g['id'],
                    '' if mode=='dissolved' else member['generation'],g['version'],result.get('sender',0)))
        return tuple(effects)

    async def initial(self,endpoint):
        data=await endpoint.io(self.store.initial,endpoint.snapshot.role_id)
        if data['groups']:
            await endpoint.deliver(Delivery(endpoint.snapshot.role_id,endpoint.snapshot.login_epoch,
                p.INITIAL,p.initial(data['groups'],self.rt.online_snapshot(),endpoint.snapshot.role_id)))
        groups={g['id']:g for g in data['groups']}
        for pending in data['pending']:
            g=groups[pending['group_id']]
            member=next(m for m in g['members'] if m['id']==endpoint.snapshot.role_id)
            await endpoint.deliver(GroupDelivery(endpoint.snapshot.role_id,endpoint.snapshot.login_epoch,p.JOIN_NOTICE,
                p.join_notice(pending['role_id'],g['id'],pending['name']),g['id'],member['generation'],g['version']))
        for invitation in data['invitations']:
            await endpoint.deliver(GroupDelivery(endpoint.snapshot.role_id,endpoint.snapshot.login_epoch,p.INVITED,
                p.invited(invitation['group_id'],invitation['sender_name'],invitation['group_name']),
                invitation['group_id'],'',invitation['version'],0,invitation['token']))

    def prepare_delivery(self,delivery):
        if delivery.invitation_token:
            return delivery if self.store.invitation_allowed(delivery.role_id,delivery.group_id,delivery.invitation_token) else None
        if isinstance(delivery,GroupHistoryDelivery):
            if not self.store.allowed(delivery.role_id,delivery.group_id,delivery.generation,None):return None
            rows=[dict(sender=r[0],plain=r[1],name=r[2],timestamp=r[3]) for r in delivery.records]
            rows=self.store.filter_history(delivery.role_id,rows)
            return replace(delivery,body=p.history_page(delivery.page,delivery.last,rows))
        return delivery if self.allowed(delivery) else None

    def allowed(self,delivery):
        if not delivery.generation:
            # Departure/dissolution must not remove a newly rejoined membership.
            with closing(self.store.connect()) as db:
                return not db.execute('SELECT 1 FROM common_group_members WHERE group_id=? AND role_id=?',
                    (delivery.group_id,delivery.role_id)).fetchone()
        return self.store.allowed(delivery.role_id,delivery.group_id,delivery.generation,delivery.version,delivery.sender)

    async def close(self):
        self.closing=True
        if self.inflight:await asyncio.gather(*tuple(self.inflight),return_exceptions=True)
        for entry in tuple(self.owners.values()):await entry['owner'].close()
        self.owners.clear()
