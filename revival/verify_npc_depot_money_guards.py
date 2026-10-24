"""Actual depot-money access expiry, movement and fresh-command behavior.

Disposable known legacy baseline. A scoped runtime clock dependency advances
expiry without sleeping or changing the event loop's clock. No battle or GUI.
"""
import asyncio
from contextlib import closing
from pathlib import Path
import struct
import tempfile
import time
from types import SimpleNamespace
from unittest.mock import patch

from accounts import AccountStore
from game_runtime import GameRuntime
from inspect_client import OUT,write_json
from verify_runtime import Peer
from verify_npc_depot_money_runtime import balances
from world_movement import ROLE_MOVE,ROLE_STOP
import game_runtime
import npc_gameplay
import runtime_storage


def state(store,rid):
    with closing(store.connect()) as db:
        return (tuple(db.execute('SELECT currency,balance,revision FROM role_wallet_balances WHERE role_id=? ORDER BY currency',(rid,))),
            tuple(db.execute('SELECT cash,origin FROM npc_depot_profiles WHERE role_id=?',(rid,))),
            tuple(db.execute('SELECT settlement_id,fingerprint,receipt FROM role_wallet_receipts WHERE role_id=? ORDER BY settlement_id',(rid,))),
            tuple(db.execute('SELECT request_id,fingerprint FROM npc_command_receipts WHERE role_id=? ORDER BY request_id',(rid,))),
            tuple(db.execute('SELECT request_id,amount,cash_after,depot_after FROM npc_depot_cash_journal WHERE role_id=? ORDER BY request_id',(rid,))))


async def check(store,prepared,role,npc):
    runtime=GameRuntime(store,prepared)
    try:
        peer=Peer(runtime);await peer.login(role);owner=runtime.roles[role['id']]
        await owner.io(runtime_storage.initialize_role_wallet,store,1111,role['id'],owner.epoch,
            (100,321,0,0),'explicit_migration')
        await owner.io(npc_gameplay.initialize_depot,owner.inventory,50,'explicit_migration')
        key=(npc.map_id<<32)|npc.placement_id
        one=struct.pack('>qq',key,1)
        await peer.request(0xc04f0,struct.pack('>q',key))
        before=state(store,role['id'])
        future=owner.npc_depot_ticket.deadline_ms/1000+1
        clock=SimpleNamespace(monotonic=lambda:future,time=time.time)
        with patch.object(game_runtime,'time',clock):
            assert await peer.request(0xc03fb,one)==[]
        assert owner.npc_depot_ticket is None and state(store,role['id'])==before
        assert await peer.request(0xc03fc,one)==[]
        assert state(store,role['id'])==before
        await peer.request(0xc04f0,struct.pack('>q',key))
        assert balances(await peer.request(0xc03fb,one))=={1:99,2:51}
        # Identical new wire requests are separate accepted operations. Only a
        # retry of the same internal command identity is deduplicated.
        assert balances(await peer.request(0xc03fb,one))=={1:98,2:52}
        before=state(store,role['id'])
        for body in (one[:-1],one+b'\0',struct.pack('>qq',key,0),
                     struct.pack('>qq',key,-1),struct.pack('>qq',key+1,1)):
            assert await peer.request(0xc03fb,body)==[]
            assert state(store,role['id'])==before
        current=owner.position.value
        await peer.request(ROLE_MOVE,struct.pack('>hhhhQ',*current[1:],*current[1:],0))
        await peer.request(ROLE_STOP,b'\0'+struct.pack('>hhQ',*current[1:],0))
        assert owner.npc_depot_ticket is None
        assert await peer.request(0xc03fc,one)==[] and state(store,role['id'])==before
        await peer.request(0xc04f0,struct.pack('>q',key))
        assert balances(await peer.request(0xc03fc,one))=={1:99,2:51}
        await peer.connection.close()
        return dict(passed=['expired real access ticket rejects deposit and revokes later draw without any asset/receipt mutation',
            'opening again restores legitimate access',
            'identical fresh native requests each transfer once rather than being globally deduplicated',
            'malformed/zero/negative/wrong NPC actual money requests leave both balances and all receipts unchanged',
            'native movement cancels access; draw rejects unchanged until warehouse reopens'],
            clock_scope='only game_runtime time dependency advanced past its ticket; no event-loop clock replacement',
            database='disposable',native_gui_verified=False,live_server_changed=False,battle_executed=False)
    finally:
        await runtime.close()


def main():
    with tempfile.TemporaryDirectory(prefix='depot-money-guards-') as directory:
        store=AccountStore(Path(directory)/'state.sqlite3')
        role=store.create_role(1111,'存取访问检查',11,1010109)
        prepared=runtime_storage.prepare(store)
        npc=next(p for ps in store.npc_resources[0].values() for p in ps if p.npc_id==10003)
        store.save_position(1111,role['id'],(npc.map_id,npc.x,npc.y))
        report=asyncio.run(check(store,prepared,role,npc))
    write_json(OUT/'evidence/npc-depot-money-guards-verification.json',report);print(report)


if __name__=='__main__':
    main()
