"""Disposable role/connection wallet slice with the native MPPC decoder.

No live listener, process, character, client window or battle is touched.
"""
import asyncio
from pathlib import Path
import struct
import tempfile
from accounts import AccountStore
from game_runtime import GameRuntime
from currency_protocol import REFRESH_MONEY,REFRESH_SMONEY
from inspect_client import OUT,write_json
from verify_runtime import Peer
import runtime_storage


def balances(frames):
    result={}
    for kind,body in frames:
        if kind==REFRESH_MONEY:
            slot,amount=struct.unpack('>iq',body)
            assert slot==1
            result['cash']=amount
        elif kind==REFRESH_SMONEY:
            result['bound_silver']=struct.unpack('>q',body)[0]
    return result


async def check(store,prepared,legacy,new):
    runtime=GameRuntime(store,prepared)
    try:
        old_peer=Peer(runtime); await old_peer.login(legacy)
        assert balances(old_peer.initial)=={}, 'Unknown legacy wallet was displayed as zero'
        new_peer=Peer(runtime); await new_peer.login(new)
        assert balances(new_peer.initial)=={'cash':0,'bound_silver':0}
        owner=runtime.roles[legacy['id']]
        baseline=(2**32+7,5000,123456,654321)
        initialized=await owner.mailbox.call('initialize_wallet',baseline,'explicit_migration')
        assert tuple(x.balance for x in initialized)==baseline
        await old_peer.connection.close()
        old_peer=Peer(runtime); await old_peer.login(legacy)
        assert balances(old_peer.initial)=={'cash':2**32+7,'bound_silver':5000}
        await old_peer.connection.close()
        await new_peer.connection.close()
    finally:
        await runtime.close()
    runtime=GameRuntime(store,prepared)
    try:
        peer=Peer(runtime); await peer.login(legacy)
        assert balances(peer.initial)=={'cash':2**32+7,'bound_silver':5000}
    finally:
        await runtime.close()
    return {'passed':['legacy role has no fabricated zero-balance refresh',
        'provenance-marked new role receives explicit zero-wallet displays',
        'trusted role-owner wallet initialization survives reconnect',
        'cash larger than 32 bits and separate bound silver traverse continuous native-decoded RC4/MPPC',
        'rebuilt runtime reloads durable current balances'],
        'database':'disposable','live_server_changed':False,'native_gui_verified':False,
        'battle_executed':False}


def main():
    with tempfile.TemporaryDirectory(prefix='currency-runtime-') as folder:
        store=AccountStore(Path(folder)/'state.sqlite3')
        legacy=store.create_role(1111,'旧档检查',11,1010109)
        prepared=runtime_storage.prepare(store)
        new=store.create_role(1111,'新档检查',11,1010109)
        result=asyncio.run(check(store,prepared,legacy,new))
    write_json(OUT/'evidence/currency-runtime-verification.json',result)
    print(result)


if __name__=='__main__': main()
