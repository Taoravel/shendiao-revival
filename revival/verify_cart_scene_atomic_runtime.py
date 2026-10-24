"""Natural cart Owner: late scene encoding must roll back the whole decision.

Uses the root's unchanged natural-prefix helper. No live port, GUI or battle.
Also checks new-lease recovery in the same live runtime after the fault.
"""
import asyncio
from contextlib import closing
import json
from pathlib import Path
import struct
import tempfile
from unittest.mock import patch
from accounts import AccountStore
from inspect_client import OUT,write_json
from task_protocol import C_COMMIT_SCENARIO_QUEST
from verify_newbie_cart_runtime import cart_visit
from verify_growth_runtime import GrowthPeer,role_values
from world_entity_protocol import VISIT_NPC
from world_newbie import load_newbie_routes
import runtime_storage


def state(store):
    with closing(store.connect()) as db:
        tables=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        return {table:tuple(sorted(map(repr,db.execute('SELECT * FROM "'+table+'"'))))
                for table in tables if table not in ('world_handoffs',)}


async def check(store,prepared,role,route,witness):
    async with cart_visit(store,prepared,role,route,witness) as visit:
        runtime,peer,owner,driver,key,definition,_=visit
        # Freeze the precise accepted source as required by the new contract.
        await owner.mailbox.call('tick')
        await owner.checkpoint()
        before=state(store)
        with patch.object(runtime_storage,'scene_entry',side_effect=ValueError('controlled late target scene encoding')) as encoder:
            assert await peer.request(C_COMMIT_SCENARIO_QUEST,struct.pack('>iQi',driver,key,0))==[]
            assert encoder.call_count==1, 'The real cart transaction did not reach target scene encoding'
        assert state(store)==before, 'Late scene encoding leaked task, assets, target or receipt writes'
        assert owner.poisoned, 'Uncertain loading map membership must fence its old role owner'
        with closing(store.connect()) as db:
            assert db.execute('SELECT stage FROM world_handoffs WHERE role_id=?',(owner.id,)).fetchone()==('prepared',)
            assert db.execute('SELECT count(*) FROM task_cart_transfers').fetchone()==(0,)
            source=db.execute('SELECT map_id,x,y FROM role_positions WHERE role_id=?',(owner.id,)).fetchone()
        old_epoch=owner.epoch
        await peer.connection.close()
        resumed=GrowthPeer(runtime);await resumed.login(role)
        current=runtime.roles[role['id']]
        assert current.epoch!=old_epoch and current.position.value==source
        assert runtime.map(1006).domain.location(current.id) is None
        await resumed.request(VISIT_NPC,struct.pack('>q',key))
        replies=await resumed.request(C_COMMIT_SCENARIO_QUEST,struct.pack('>iQi',driver,key,0))
        a=definition['attributes']
        target=(int(a['RewardMapID']),int(a['RewardMapXPos'])*16,int(a['RewardMapYPos'])*16)
        assert current.position.value==target and current.transfer is None
        assert tuple(role_values(replies)[k] for k in (80,810,1230))==(45,35,8)
        with closing(store.connect()) as db:
            assert db.execute('SELECT state FROM task_journal WHERE role_id=? AND task_id=?',
                (current.id,driver)).fetchone()==('completed',)
            assert db.execute('SELECT count(*) FROM task_cart_transfers').fetchone()==(1,)
        await resumed.connection.close()


def main():
    route=load_newbie_routes()[(9,11)]
    audit=json.loads((OUT/'evidence/newbie-birth-sites-audit.json').read_text(encoding='utf-8'))
    witness=next(r for r in audit['routes'] if (r['character_id'],r['school_id'])==(9,11))
    with tempfile.TemporaryDirectory(prefix='cart-scene-atomic-') as folder:
        store=AccountStore(Path(folder)/'state.sqlite3');prepared=runtime_storage.prepare(store)
        role=store.create_role(1111,'车夫失败回滚',11,1010109)
        asyncio.run(check(store,prepared,role,route,witness))
    result=dict(passed=['natural original cart Owner reaches the target scene encoder inside its transaction',
        'late scene encoding failure rolls back target position, task/rewards/assets and cart receipt together',
        'only prepared world intent remains and old loading role is fenced',
        'new lease reconnect in the same runtime retires old members and a fresh cart choice succeeds once'],database='disposable',
        same_runtime_reconnect_verified=True,native_gui_verified=False,live_server_changed=False,battle_executed=False)
    write_json(OUT/'evidence/cart-scene-atomic-runtime-verification.json',result);print(result)


if __name__=='__main__':main()
