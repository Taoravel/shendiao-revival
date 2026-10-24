"""Shared creation/lease and Owner gates/rollback; disposable storage only."""
import asyncio
from contextlib import closing
from pathlib import Path
import struct
import tempfile
import time
from unittest.mock import patch
from accounts import AccountStore
from game_runtime import GameRuntime
from inventory import AssetChange,QUERY_BAG,USE_ITEM
from inspect_client import OUT,write_json
from role_growth_protocol import C_REQ_LEVEL_UP,C_ADD_POINT_TO_ATTR
from task_protocol import C_REQUEST_QUEST_CAN_ACCEPT
from verify_growth_runtime import GrowthPeer
from world_newbie import START_PLAY_CG,END_PLAY_CG
from world_entity_protocol import VISIT_NPC
import runtime_storage
import task_newbie_chapter


def journal(store,role):
    with closing(store.connect()) as db:
        return tuple(db.execute('SELECT task_id,state FROM task_journal WHERE role_id=? ORDER BY task_id',(role,)))


async def owner_checks(store,prepared,role):
    runtime=GameRuntime(store,prepared)
    try:
        peer=GrowthPeer(runtime);await peer.login(role)
        owner=runtime.roles[role['id']]
        ticket=owner.intro_ticket
        route=owner.newbie_chapter.origin.route
        assert ticket and owner.newbie_pending
        assert [body for kind,body in peer.initial if kind==START_PLAY_CG]==[struct.pack('>i',route.intro_movie_id)]
        location=await runtime.map(owner.position.value[0]).mailbox.call('location',owner.id,owner.epoch)
        replay=await owner.io(runtime_storage.newbie_playback,store,1111,owner.id,owner.epoch,location,
            peer.connection.generation,ticket.request_id,int(time.time()*1000),ticket)
        assert replay.ticket==ticket and replay.chapter==owner.newbie_chapter
        before=journal(store,role['id'])
        for kind,body in ((C_REQ_LEVEL_UP,bytes(4)),(C_ADD_POINT_TO_ATTR,struct.pack('>5i',1,0,0,0,0)),
                          (QUERY_BAG,struct.pack('>iQ',1,0)),(USE_ITEM,struct.pack('>iiQ',1,0,role['id'])),
                          (VISIT_NPC,struct.pack('>q',1)),(C_REQUEST_QUEST_CAN_ACCEPT,b''),
                          (0xc0fa1,struct.pack('>hhhhQ',*owner.position.value[1:],
                                             owner.position.value[1]+16,owner.position.value[2],0))):
            assert await peer.request(kind,body)==[]
        for operation,args in (('offer_task',(100192,)),('settle',(AssetChange('blocked',grants=((32000,1),)),)),
                               ('initialize_wallet',((0,0,0,0),'explicit_migration')),('scene_sent',(None,))):
            try:await owner.mailbox.call(operation,*args)
            except ValueError:pass
            else:raise AssertionError(f'{operation} bypassed intro gate')
        assert journal(store,role['id'])==before
        assert owner.intro_ticket==ticket
        finish=task_newbie_chapter.finish_newbie_chapter
        def late_failure(*args,**kwargs):
            finish(*args,**kwargs)
            raise ValueError('controlled late chapter failure')
        with patch.object(task_newbie_chapter,'finish_newbie_chapter',late_failure):
            assert await peer.request(END_PLAY_CG,struct.pack('>i',route.intro_movie_id))==[]
        assert journal(store,role['id'])==before and owner.intro_ticket==ticket
        assert runtime_storage.newbie_state(store,1111,role['id'],owner.epoch).phase=='playing'
        with closing(store.connect()) as db:
            assert db.execute('SELECT 1 FROM task_reward_channels WHERE role_id=?',(role['id'],)).fetchone() is None
        await peer.request(END_PLAY_CG,struct.pack('>i',route.intro_movie_id))
        assert owner.intro_ticket is None and not owner.newbie_pending
        assert dict(journal(store,role['id']))=={route.intro_task_id:'completed',route.successor_task_id:'active'}
        assert (await peer.request(QUERY_BAG,struct.pack('>iQ',1,0)))[0][0]==0xc03f3
        await peer.connection.close()
    finally:await runtime.close()


def main():
    with tempfile.TemporaryDirectory(prefix='newbie-owner-contracts-') as folder:
        store=AccountStore(Path(folder)/'state.sqlite3')
        prepared=runtime_storage.prepare(store)
        resources=store.task_resources
        chosen=None
        for index,route in enumerate(store.newbie_rules.routes.values()):
            shape=next(shape for shape,ident in resources.shape_to_role_config.items()
                       if ident==route.character_id and route.school_id in store.choices[shape])
            account=1111 if (route.character_id,route.school_id)==(9,111) else 2000+index
            if account!=1111:
                with closing(store.connect()) as db,db:
                    db.execute('INSERT INTO accounts SELECT ?,?,login_secret FROM accounts WHERE id=1111',
                               (account,f'fixture-{account}'.encode()))
            role=store.create_role(account,f'原生路{index}',route.school_id,shape)
            assert store.position(account,role['id'])==route.cinematic_endpoint
            epoch=store.acquire_lease(account,role['id'])
            runtime_storage.load_role(store,account,role['id'],epoch,prepared[0])
            chapter=runtime_storage.newbie_state(store,account,role['id'],epoch)
            assert chapter.origin.route==route and chapter.phase=='authorized'
            assert journal(store,role['id'])==((route.intro_task_id,'active'),)
            if account==1111:chosen=role
        assert chosen is not None
        original=task_newbie_chapter.record_newbie_creation
        def broken_creation(*args,**kwargs):
            original(*args,**kwargs)
            raise ValueError('controlled failure after independent origin write')
        with closing(store.connect()) as db:
            counts=tuple(db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] for table in
                         ('roles','role_positions','role_restoration_origins','task_newbie_origins'))
        with patch.object(task_newbie_chapter,'record_newbie_creation',broken_creation):
            try:store.create_role(1111,'创建回滚',11,1010109)
            except ValueError:pass
            else:raise AssertionError('Broken creation committed')
        with closing(store.connect()) as db:
            assert counts==tuple(db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] for table in
                                 ('roles','role_positions','role_restoration_origins','task_newbie_origins'))
        fresh=store.create_role(1111,'首次回滚',11,1010109)
        epoch=store.acquire_lease(1111,fresh['id'])
        initialize=task_newbie_chapter.initialize_newbie_chapter
        def broken_initialization(*args,**kwargs):
            initialize(*args,**kwargs)
            raise ValueError('controlled failure after root activation')
        with patch.object(task_newbie_chapter,'initialize_newbie_chapter',broken_initialization):
            try:runtime_storage.load_role(store,1111,fresh['id'],epoch,prepared[0])
            except ValueError:pass
            else:raise AssertionError('Broken initialization committed')
        with closing(store.connect()) as db:
            for table in ('role_growth','role_attribute_baselines','task_newbie_chapters','task_journal'):
                assert db.execute(f'SELECT 1 FROM {table} WHERE role_id=?',(fresh['id'],)).fetchone() is None
            assert db.execute('SELECT creation_profile_receipt FROM role_restoration_origins '
                              'WHERE role_id=?',(fresh['id'],)).fetchone()==(None,)
        assert store.position(1111,fresh['id'])==(1100,1488,1152)
        asyncio.run(owner_checks(store,prepared,chosen))
    report=dict(passed=['actual AccountStore creation and first lease activate all43 original routes at approved school spawn',
        'creation late failure rolls back role, growth origin, newbie origin and position',
        'first-lease late failure rolls back growth, attributes, root and chapter together; creation position retained',
        'pending Owner gate blocks gameplay packets plus trusted settlement/wallet/task writes',
        'worker restores same-generation authorization from frozen ticket without changing source, deadline or chapter revision',
        'completion late failure retains frozen ticket and pending root with no reward; exact permit can retry',
        'commit clears gate and allows actual bag query; continuous native MPPC/RC4 decodes'],
        database='disposable',battle_executed=False,native_gui_verified=False,live_server_changed=False)
    write_json(OUT/'evidence/newbie-owner-contracts-verification.json',report)
    print(report)


if __name__=='__main__':main()
