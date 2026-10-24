"""Natural cart: a post-commit source-finalize fault must recover the target.

Actual map/role owners and original connection codecs, disposable storage.
This injects source cleanup failure, not a real TCP outage or GUI action.
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
from verify_first_master_runtime import state
from verify_growth_runtime import GrowthPeer,role_values
from verify_newbie_cart_runtime import cart_visit
from world_newbie import load_newbie_routes
import runtime_storage


async def check(store,prepared,role,route,witness):
    async with cart_visit(store,prepared,role,route,witness) as visit:
        runtime,peer,owner,driver,key,definition,before=visit
        source=runtime.map(owner.position.value[0])
        body=struct.pack('>iQi',driver,key,0)
        a=definition['attributes']
        target=(int(a['RewardMapID']),int(a['RewardMapXPos'])*16,int(a['RewardMapYPos'])*16)
        with patch.object(source.domain,'finalize',side_effect=ValueError('controlled post-commit source cleanup')) as cleanup:
            assert await peer.request(C_COMMIT_SCENARIO_QUEST,body)==[]
            assert cleanup.call_count==1
        assert owner.poisoned
        assert source.domain.location(owner.id).state=='frozen'
        assert runtime.map(target[0]).domain.location(owner.id).state=='loading'
        with closing(store.connect()) as db:
            assert db.execute('SELECT map_id,x,y FROM role_positions WHERE role_id=?',(owner.id,)).fetchone()==target
            assert db.execute('SELECT stage FROM world_handoffs WHERE role_id=?',(owner.id,)).fetchone()==('committed',)
            assert db.execute('SELECT count(*) FROM task_cart_transfers').fetchone()==(1,)
        paid=state(store,owner.id)
        expected=dict(before[0]);expected[driver]='completed';expected[definition['next_ids'][0]]='active'
        assert dict(paid[0])==expected and paid[1]==before[1]
        old_epoch=owner.epoch
        await peer.connection.close()
        peer=GrowthPeer(runtime);await peer.login(role)
        current=runtime.roles[role['id']]
        assert current.epoch!=old_epoch and current.position.value==target
        assert source.domain.location(current.id) is None and current.id not in source.positions
        assert runtime.map(target[0]).domain.location(current.id).state=='active'
        assert runtime.map(target[0]).positions[current.id].epoch==current.epoch
        assert tuple(role_values(peer.initial)[k] for k in (80,810,1230))==(45,35,8)
        assert state(store,current.id)==paid
        assert await peer.request(C_COMMIT_SCENARIO_QUEST,body)==[]
        assert state(store,current.id)==paid
        await peer.connection.close()


def main():
    route=load_newbie_routes()[(9,11)]
    audit=json.loads((OUT/'evidence/newbie-birth-sites-audit.json').read_text(encoding='utf-8'))
    witness=next(r for r in audit['routes'] if (r['character_id'],r['school_id'])==(9,11))
    with tempfile.TemporaryDirectory(prefix='cart-committed-recovery-') as folder:
        store=AccountStore(Path(folder)/'state.sqlite3');prepared=runtime_storage.prepare(store)
        role=store.create_role(1111,'车夫提交后恢复',11,1010109)
        asyncio.run(check(store,prepared,role,route,witness))
    result=dict(passed=['natural cart durable target/task/reward commits before injected source-finalize failure',
        'old frozen/loading memberships and adapter caches retire through public recovery on the new lease',
        'same-runtime reconnect preserves committed Jiaxing target, unique task receipt and weapon totals45/35/8',
        'fresh duplicate old choice cannot repeat reward or pull the role back'],database='disposable',
        fault='post-commit source cleanup, not actual socket outage',same_runtime_reconnect_verified=True,
        native_gui_verified=False,live_server_changed=False,battle_executed=False)
    write_json(OUT/'evidence/cart-committed-recovery-runtime-verification.json',result);print(result)


if __name__=='__main__':main()
