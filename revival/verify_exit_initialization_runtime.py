"""Real world initialization feeds the original offline WM_CLOSE gate.

No client process, OS window, live authentication or battle execution.
"""
import asyncio
from pathlib import Path
import struct
import tempfile
from accounts import AccountStore
from game_runtime import GameRuntime
from inspect_client import OUT,write_json
from verify_runtime import Peer
from verify_role_exit_native import case as native_exit_case
from wire import octets
import runtime_storage


def native_mode(messages):
    modes=[body for kind,body in messages if kind==0xc0039]
    assert len(modes)==1,'World initialization never enables the original exit confirmation gate'
    assert modes[0]==bytes.fromhex('ffffffff'),'Zero selects the first-day exit feature instead of ordinary exit'
    result=native_exit_case(struct.unpack('>i',modes[0])[0])
    assert int(result['type'],16)==0xc0039 and bytes.fromhex(result['wire_hex'])==modes[0]
    assert result['before_initialization']['ui_calls']==[]
    assert result['after_native_decode_and_process']['ui_calls']==['ordinary_exit_dialog']
    return result


async def check(store,prepared,old,fresh):
    rt=GameRuntime(store,prepared)
    try:
        facts=[]
        for role in (old,fresh,fresh):
            peer=Peer(rt);await peer.login(role)
            facts.append(native_mode(peer.initial))
            if rt.roles[role['id']].newbie_pending:
                # Delivery belongs to world initialization, before the movie
                # authorization messages, rather than an intro completion.
                kinds=[kind for kind,body in peer.initial]
                assert kinds.index(0xc0039)<kinds.index(0xc0017)
            if role is old:
                assert (await peer.request(0xc002d,b''))[0][0]==0xc002e
                assert await peer.request(0xc0078,struct.pack('>Q',role['id']))==[(0xc0079,b'')]
                assert (await peer.request(0xc0005,struct.pack('>Q',role['id'])+octets(b'')+b'\0'))[0][0]==0xc0006
                facts.append(native_mode(await peer.request(0xc003d,b'')))
            assert await peer.request(0xc0011,b'')==[(0xc0031,b'')]
            assert role['id'] not in rt.roles
            await peer.connection.close()
        return facts
    finally:await rt.close()


def main():
    with tempfile.TemporaryDirectory(prefix='exit-initialization-') as directory:
        store=AccountStore(Path(directory)/'state.sqlite3')
        old=store.create_role(1111,'旧档退出入口',11,1010109)
        prepared=runtime_storage.prepare(store)
        fresh=store.create_role(1111,'新建退出入口',11,1010109)
        cases=asyncio.run(check(store,prepared,old,fresh))
    result=dict(passed=['actual encrypted world initialization sends ordinary exit mode after world entry',
        'actual emitted packet drives original decoder/Process and installed WndProc from no dialog to ordinary dialog',
        'legacy, pending new intro and reconnect each initialize once before intro messages',
        'original exit confirmation still cleans the current role and returns c0031'],
        native_cases=cases,database='disposable',native_gui_verified=False,live_server_changed=False,battle_executed=False,
        designed_policy='ordinary ExitGameDialog only; original first-day exit business feature not restored')
    write_json(OUT/'evidence/exit-initialization-runtime-verification.json',result);print(result)


if __name__=='__main__':main()
