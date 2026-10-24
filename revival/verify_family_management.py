"""Original family management through encrypted runtime; no live game process.

Family setup uses a declared temporary funding grant, not native cash/consent
acceptance. Every management action below then enters the native request route.
"""
import asyncio
from contextlib import closing
import json
from pathlib import Path
import struct
import tempfile
import uuid
from unittest.mock import patch
from accounts import AccountStore
from game_runtime import GameRuntime
from faction_domain import OrganizationCommand
from family_runtime import FamilyWake
from verify_runtime import Peer
from verify_faction_runtime import now
from wire import read_compact
from inspect_client import OUT,write_json
import runtime_storage
import faction_protocol as p
import social_protocol as sp


def members(body):
    count,pos=read_compact(body);rows={}
    for _ in range(count):
        rid=struct.unpack_from('>Q',body,pos)[0];pos+=8
        name,pos=sp.read_text(body,pos)
        metadata,first,second,level,position=struct.unpack_from('>iiiii',body,pos);pos+=20
        offline,pos=sp.read_text(body,pos)
        rows[rid]=dict(name=name,metadata=metadata,prestige=(first,second),level=level,position=position,offline=offline)
    assert pos==len(body)
    return rows


def latest(frames,kind):return next(body for k,body in reversed(frames) if k==kind)
def roster(frames):return members(latest(frames,p.ADD_FAMILY_MEMBERS))


def panel(body,*,include_history=False):
    identity=struct.unpack_from('>i',body)[0];pos=4;names=[]
    for _ in range(3):value,pos=sp.read_text(body,pos);names.append(value)
    level,funds,pop,cap,build,target,reserved=struct.unpack_from('>iQiiiiQ',body,pos)
    count,pos=read_compact(body,pos+36);history=[]
    for _ in range(count):
        template=struct.unpack_from('>i',body,pos)[0];pos+=4
        size,pos=read_compact(body,pos);parameters=[]
        for _ in range(size):value,pos=sp.read_text(body,pos);parameters.append(value)
        history.append((template,tuple(parameters)))
    assert pos==len(body)
    values=(identity,*names,level,funds,pop,cap,build,target,reserved)
    return values+(tuple(history),) if include_history else values


async def check(store,checks):
    rt=GameRuntime(store,runtime_storage.prepare(store));roles=store.roles(1111)
    peers=[Peer(rt) for _ in roles]
    try:
        for peer,role in zip(peers,roles):await peer.login(role)
        a,b,c,d,e=peers;org=rt.social_runtime.organizations
        online=rt.online_snapshot()
        create=OrganizationCommand(1,online[1].login_epoch,uuid.uuid4().hex,now()+5000,0,'create_family',
            ('原生家族','同心协力',tuple((rid,online[rid].login_epoch) for rid in (1,2,3))))
        with closing(org.store.connect()) as db,db:org.store.record_funding(db,create,org.policy['family_create_fee'])
        made=await org.command(create,now());family=made.organization
        frames=await a.take();await b.take();await c.take()
        values=panel(latest(frames,p.UPDATE_FAMILY))
        assert values==(family,roles[0]['name'],'原生家族','同心协力',1,3000000,1000,5000,0,20,0)
        courses=panel(latest(frames,p.UPDATE_FAMILY),include_history=True)[-1]
        assert len(courses)==1 and courses[0][0]==1 and len(courses[0][1][0])==19
        assert set(roster(frames))=={1,2,3} and all(r['offline']=='' and r['level']==40 for r in roster(frames).values())
        assert await d.take()==[] and await e.take()==[]
        checks.append('trusted fixture creation broadcasts native family panel, popularity/build pairs and server-derived online roster')
        assert await d.request(p.JOIN_FAMILY,p.family_join_request((family,)))==[]
        pending=await a.take();assert p.ADD_FAMILY_APPLICATIONS in [k for k,_ in pending]
        assert not any(k in (p.ADD_FAMILY_APPLICATIONS,p.REMOVE_FAMILY_APPLICATIONS) for k,_ in await b.take())
        assert not any(k in (p.ADD_FAMILY_APPLICATIONS,p.REMOVE_FAMILY_APPLICATIONS) for k,_ in await c.take())
        assert await c.request(p.FAMILY_REVIEW,struct.pack('>Qi',4,1))==[]
        assert org.store.family_audience(family).applications==(4,)
        checks.append('native family application persists, reaches managers only, and ordinary self-approval rejects')
        frames=await a.request(p.FAMILY_POSITION,struct.pack('>Qi',2,1))
        assert roster(frames)[2]['position']==1
        assert p.ADD_FAMILY_APPLICATIONS in [k for k,_ in await b.take()]
        assert p.ADD_FAMILY_APPLICATIONS not in [k for k,_ in await c.take()]
        assert await b.request(p.FAMILY_REVIEW,struct.pack('>Qi',4,1))
        await a.take();await c.take()
        frames=await d.take();assert set(roster(frames))=={1,2,3,4}
        assert roster(frames)[4]['prestige']==(0,0) and org.store.family_audience(family).applications==()
        checks.append('native deputy appointment enables approval; acceptance publishes new full roster and clears application')
        old_generation=dict(org.store.family_audience(family).members)[4]
        old=FamilyWake(4,rt.online_snapshot()[4].login_epoch,0,b'',family,old_generation)
        assert await d.request(p.LEAVE_FAMILY,b'')==[(p.LEFT_FAMILY,b'')]
        frames=await a.take();assert (p.REMOVE_FAMILY_MEMBER,struct.pack('>Q',4)) in frames
        await b.take();await c.take()
        await d.request(p.JOIN_FAMILY,p.family_join_request((family,)));await a.take();await b.take();await c.take()
        await a.request(p.FAMILY_REVIEW,struct.pack('>Qi',4,1));await b.take();await c.take();await d.take()
        assert dict(org.store.family_audience(family).members)[4]!=old_generation
        rt.social_runtime.offer(old);assert await d.take()==[]
        checks.append('native leave clears departed client and remaining roster; rejoin rotates generation and drops queued old family snapshot')
        before=org.store.snapshot(family)
        for kind,body in ((p.FAMILY_POSITION,struct.pack('>Qi',3,9)),(p.FAMILY_REVIEW,struct.pack('>Qi',5,2)),
                          (p.JOIN_FAMILY,p.family_join_request((family,),1))):
            peer=e if kind==p.JOIN_FAMILY else a
            assert await peer.request(kind,body)==[]
        assert org.store.snapshot(family)==before
        assert await a.request(p.EXPEL_MEMBER,struct.pack('>Q',2))==[]
        await a.request(p.FAMILY_POSITION,struct.pack('>Qi',1,0))
        assert org.store.snapshot(family)[0]['leader']==2
        promoted=await b.take();await c.take();await d.take()
        courses=panel(latest(promoted,p.UPDATE_FAMILY),include_history=True)[-1]
        assert [row[0] for row in courses]==[1,4] and courses[-1][1][1]==roles[1]['name']
        assert await a.request(p.EXPEL_MEMBER,struct.pack('>Q',4))==[]
        await b.request(p.EXPEL_MEMBER,struct.pack('>Q',4))
        assert await d.take()==[(p.LEFT_FAMILY,b'')]
        frames=await a.take();assert 4 not in roster(frames)
        assert panel(latest(frames,p.UPDATE_FAMILY))[1]==roles[0]['name']
        await c.take()
        checks.append('invalid enums/mode preserve state; deputy protected; native abdication changes leader and expulsion retains founder identity')
        # Ordinary members must lose stale cached applications after demotion.
        await e.request(p.JOIN_FAMILY,p.family_join_request((family,)));await a.take();await b.take();await c.take()
        await b.request(p.FAMILY_POSITION,struct.pack('>Qi',1,1));await a.take();await c.take()
        frames=await b.request(p.FAMILY_POSITION,struct.pack('>Qi',1,0));await c.take()
        former=await a.take()
        assert (p.REMOVE_FAMILY_APPLICATIONS,p.removed_family_applications((5,))) in former
        assert p.ADD_FAMILY_APPLICATIONS not in [k for k,_ in former]
        assert await a.request(p.FAMILY_REVIEW,struct.pack('>Qi',5,1))==[]
        await b.request(p.FAMILY_REVIEW,struct.pack('>Qi',5,0));await a.take();await c.take()
        checks.append('manager demotion removes cached application data; rejection clears pending without joining applicant')
        old_snapshot=rt.online_snapshot()[3]
        await c.connection.close()
        frames=await b.take();assert len(roster(frames)[3]['offline'])==19
        await a.take()
        c=Peer(rt);await c.login(roles[2]);peers[2]=c
        assert roster(c.initial)[3]['offline']==''
        await a.take();await b.take()
        await org.family.presence(old_snapshot,False)
        assert await a.take()==[] and await b.take()==[]
        assert await e.request(100,b'fam!')==[(100,b'fam!')]
        checks.append('logout time persists and online uses empty native text; replacement epoch rejects stale presence; native stream remains continuous')
        with patch.object(org.store,'family_presence',side_effect=TimeoutError('controlled presence failure')):
            await c.connection.close()
        with closing(store.connect()) as db:assert db.execute('SELECT active FROM role_leases WHERE role_id=3').fetchone()[0]==0
        assert 3 not in rt.roles and await e.request(100,b'live')==[(100,b'live')]
        checks.append('failed organization presence persistence does not block role lease release or unrelated heartbeat')
    finally:await rt.close()
    rt=GameRuntime(store,runtime_storage.prepare(store))
    try:
        b=Peer(rt);await b.login(roles[1])
        assert b.initial[0][0]==sp.FRIENDS_INIT and roster(b.initial)[2]['position']==2
        values=panel(latest(b.initial,p.UPDATE_FAMILY));assert values[5:9]==(3000000,1000,5000,0)
        assert panel(latest(b.initial,p.UPDATE_FAMILY),include_history=True)[-1]==courses
        assert set(roster(b.initial))=={1,2,3} and all(r['offline'] for rid,r in roster(b.initial).items() if rid!=2)
        checks.append('runtime restart restores actual leader, funds/progress, roster and offline times after friend initialization')
    finally:await rt.close()


def main():
    checks=[]
    with tempfile.TemporaryDirectory() as directory:
        store=AccountStore(Path(directory)/'state.db')
        with closing(store.connect()) as db,db:
            for rid,name in enumerate(('创始甲','副族乙','成员丙','申请丁','申请戊'),1):
                db.execute('INSERT INTO roles(id,account_id,name,school,shape,level) VALUES(?,1111,?,12,1010101,40)',(rid,name))
        asyncio.run(check(store,checks))
    result=dict(passed=checks,native_management_source_integrated=True,native_history_source_integrated=True,native_gui_verified=False,
        native_paid_creation_integrated=False,creation_funding='explicit disposable fixture grant only',live_store_changed=False)
    write_json(OUT/'evidence/family-management-verification.json',result)
    print(json.dumps(result))


if __name__=='__main__':main()
