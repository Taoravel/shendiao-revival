"""Actual original menu requests through disposable role/connection owners."""
import asyncio
from contextlib import closing
import hashlib,hmac
from pathlib import Path
import struct,tempfile
from accounts import AccountStore
import role_lifecycle
from unittest.mock import patch
from crypto import ArcFour
from game_runtime import GameRuntime
from inventory import AssetChange
from inspect_client import OUT,write_json
from runtime_core import StaleEpoch
from verify_runtime import Peer
from verify_mppc_native import NativeDecoder
from wire import octets,read_octets
import runtime_storage


async def authenticate(peer):
    challenge,_=read_octets((await peer.take())[0][1])
    secret=hashlib.md5(b'11111111').digest()
    proof=hmac.new(secret,challenge,hashlib.md5).digest()
    response=await peer.request(103,octets(b'1111')+octets(proof)+bytes(4)+octets(b'')+bytes(4)+octets(b''))
    nonce,_=read_octets(response[0][1])
    peer.output=ArcFour(hmac.new(secret,b'1111'+nonce,hashlib.md5).digest())
    nonce=b'0123456789abcdef'
    peer.input=ArcFour(hmac.new(secret,b'1111'+nonce,hashlib.md5).digest())
    peer.decoder=NativeDecoder()
    assert (await peer.request(106,octets(nonce)+bytes(4)))[0][0]==110


async def check(store,prepared,role,other,fresh):
    runtime=GameRuntime(store,prepared)
    try:
        # Exit must work even while the new role's intro write gate is active.
        pending=Peer(runtime);await pending.login(fresh)
        assert runtime.roles[fresh['id']].newbie_pending
        reply=await pending.request(0xc0011,b'')
        assert reply==[(0xc0031,b'')], 'Original exit-game request gets no SRoleOffline confirmation'
        assert fresh['id'] not in runtime.roles
        assert runtime_storage.newbie_state(store,1111,fresh['id'],store.acquire_lease(1111,fresh['id'])).phase=='playing'
        await pending.connection.close()
        menu=Peer(runtime);await authenticate(menu)
        body=struct.pack('>Q',fresh['id'])
        assert await menu.request(0xc0028,body)==[(0xc0029,body)], 'Original delete-role request gets no matching confirmation'
        assert all(r['id']!=fresh['id'] for r in store.roles(1111))
        assert store.owned_role(1111,fresh['id']) is None
        with closing(store.connect()) as db:
            assert db.execute('SELECT 1 FROM roles WHERE id=?',(fresh['id'],)).fetchone()==(1,)
            assert db.execute('SELECT phase FROM task_newbie_chapters WHERE role_id=?',(fresh['id'],)).fetchone()==('playing',)
        assert await menu.request(0xc0028,body)==[(0xc0029,body)]
        for malformed in (body[:-1],body+b'\0',bytes(8),struct.pack('>Q',2**63)):
            assert await menu.request(0xc0028,malformed)==[]
        with closing(store.connect()) as db,db:
            db.execute('INSERT INTO accounts SELECT 2222,?,login_secret FROM accounts WHERE id=1111',(b'2222',))
        foreign=store.create_role(2222,'其他账号',11,1010109)
        assert await menu.request(0xc0028,struct.pack('>Q',foreign['id']))==[]
        stale=store.deletion_candidate(2222,foreign['id'])
        store.acquire_lease(2222,foreign['id'])
        try:store.delete_role(stale)
        except ValueError:pass
        else:raise AssertionError('Delete raced a newly acquired lease')
        active=Peer(runtime);await active.login(other)
        assert await menu.request(0xc0028,struct.pack('>Q',other['id']))==[]
        assert await active.request(100,b'aliv')==[(100,b'aliv')]
        owner_peer=Peer(runtime);await owner_peer.login(role)
        owner=runtime.roles[role['id']]
        epoch=owner.epoch
        await owner.mailbox.call('settle',AssetChange('retained-receipt',grants=((32000,2),)))
        x,y=owner.position.value[1:]
        assert await owner_peer.request(0xc0fa1,struct.pack('>hhhhQ',x,y,x+16,y,0))==[]
        assert await owner_peer.request(0xc0fa3,struct.pack('>hhBhhQ',x+16,y,1,x,y,0))==[]
        expected_position=owner.position.value
        assert owner.dirty and expected_position==(1007,x+16,y)
        result=await owner_peer.request(0xc002d,b'')
        assert result and result[0][0]==0xc002e
        assert owner_peer.connection.codec.state=='roles' and role['id'] not in runtime.roles
        assert store.position(1111,role['id'])==expected_position
        original_retire=role_lifecycle.retire
        def rollback(*args):
            original_retire(*args)
            raise ValueError('controlled failure after retirement')
        with patch.object(role_lifecycle,'retire',rollback):
            assert await owner_peer.request(0xc0028,struct.pack('>Q',role['id']))==[]
        assert store.owned_role(1111,role['id']) is not None
        assert await owner_peer.request(0xc0028,struct.pack('>Q',role['id']))==[(0xc0029,struct.pack('>Q',role['id']))]
        with closing(store.connect()) as db:
            assert db.execute('SELECT quantity FROM inventory_items WHERE role_id=?',(role['id'],)).fetchone()==(2,)
            assert db.execute('SELECT 1 FROM role_settlements WHERE role_id=?',(role['id'],)).fetchone()==(1,)
        try:store.acquire_lease(1111,role['id'])
        except ValueError:pass
        else:raise AssertionError('Deleted role acquired a login lease')
        try:store.save_checkpoint(1111,role['id'],epoch,(1007,8480,6976),999)
        except StaleEpoch:pass
        else:raise AssertionError('Old deleted role callback wrote position')
        replacement=store.create_role(1111,'空位新角',11,1010109)
        assert replacement['id'] not in (role['id'],fresh['id'])
        assert await active.request(100,b'aliv')==[(100,b'aliv')]
        assert await active.request(0xc0032,b'')==[(0xc0033,b'')]
        assert other['id'] not in runtime.roles
    finally:await runtime.close()


def main():
    with tempfile.TemporaryDirectory(prefix='role-lifecycle-') as folder:
        store=AccountStore(Path(folder)/'state.sqlite3')
        role=store.create_role(1111,'退出保存',11,1010109)
        other=store.create_role(1111,'另一个角色',11,1010109)
        prepared=runtime_storage.prepare(store)
        fresh=store.create_role(1111,'剧情中退出',11,1010109)
        asyncio.run(check(store,prepared,role,other,fresh))
    result=dict(passed=['native exit confirmation works during pending intro and cleans only current role',
        'native delete request/confirmation removes owned roster entry and preserves audit/assets',
        'duplicate deletion is idempotent; malformed/foreign/online deletion refused',
        'return-to-role-list preserves continuous codec and allows subsequent deletion',
        'return-to-login emits the real native confirmation; latest movement checkpoint persists before leaving',
        'lease acquisition races reject deletion and late retirement failure rolls back the marker',
        'deleted role cannot log in or accept old callbacks; deletion frees a creation slot',
        'other connected role heartbeat continues'],database='disposable',native_gui_verified=False,live_data_changed=False)
    write_json(OUT/'evidence/role-lifecycle-runtime-verification.json',result)
    print(result)


if __name__=='__main__':main()
