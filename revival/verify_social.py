"""Exercise social features through encrypted Session.feed on disposable accounts."""
import hashlib
import hmac
import json
import struct
import tempfile
from contextlib import closing
from pathlib import Path
from accounts import AccountStore
from gateway import Session
from social import SocialHub
import social_protocol as p
from crypto import ArcFour
from wire import frame, octets, FrameReader, read_octets
from verify_mppc_native import NativeDecoder
from inspect_client import OUT, write_json


class Peer:
    def __init__(self, store, hub, role, identity=b'1111'):
        self.pushed = []
        self.session = Session(store, social=hub, deliver=self.pushed.append)
        self.role = role
        secret = hashlib.md5(identity+b'1111').digest()
        challenge, _ = read_octets(FrameReader().feed(self.session.opening())[0][1])
        proof = hmac.new(secret, challenge, hashlib.md5).digest()
        reply = self.session.feed(frame(103, octets(identity)+octets(proof)+bytes(4)+octets(b'')+bytes(4)+octets(b'')))
        nonce, _ = read_octets(FrameReader().feed(b''.join(reply))[0][1])
        self.out = ArcFour(hmac.new(secret, identity+nonce, hashlib.md5).digest())
        client_nonce = b'0123456789abcdef'
        self.incoming = ArcFour(hmac.new(secret, identity+client_nonce, hashlib.md5).digest())
        self.decoder = NativeDecoder()
        self.frames = FrameReader()
        assert self.request(106, octets(client_nonce)+bytes(4))[0][0] == 110
        assert self.request(0xc0005, struct.pack('>Q',role['id'])+octets(b'')+b'\0')[0][0] == 0xc0006
        self.initial = self.request(0xc003d, b'')

    def decode(self, packets):
        return self.frames.feed(b''.join(self.decoder.feed(self.incoming.transform(x)) for x in packets))

    def request(self, kind, body):
        return self.decode(self.session.feed(self.out.transform(frame(kind, body))))

    def receive(self):
        packets = self.pushed[:]
        self.pushed.clear()
        return self.decode(packets)

    def close(self): self.session.close()


def main():
    with tempfile.TemporaryDirectory() as d:
        path = Path(d)/'accounts.db'
        store = AccountStore(path)
        with closing(store.connect()) as db, db:
            db.execute('INSERT INTO accounts VALUES(?,?,?)', (2222,b'2222',hashlib.md5(b'22221111').digest()))
        a = store.create_role(1111, '社交甲', 12, 1010101)
        b = store.create_role(2222, '社交乙', 12, 1010101)
        c = store.create_role(2222, '社交丙', 11, 1010109)
        hub = SocialHub(store)
        pa, pb, pc = Peer(store, hub, a), Peer(store, hub, b, b'2222'), Peer(store, hub, c, b'2222')
        assert pa.initial == [(p.FRIENDS_INIT, bytes(5))]
        assert pa.request(p.SEARCH_ID_SEND, struct.pack('>Q',b['id'])) == [(p.SEARCH_ID_RECEIVE,p.profile(b))]
        assert pa.request(p.SEARCH_NAME_SEND,p.text(b['name'])+bytes(12)) == [(p.SEARCH_NAME_RECEIVE,p.profile(b,True))]
        assert pa.request(p.SEARCH_ID_SEND, struct.pack('>Q',9999)) == [(p.SEARCH_ID_RECEIVE,p.profile())]
        add = struct.pack('>Q',b['id'])+p.text('')
        assert pa.request(p.ADD_SEND, add) == [(p.ADD_RECEIVE,p.friend_added(b,True))]
        pa.request(p.ADD_SEND, add)
        assert len(SocialHub(AccountStore(path)).friends(a['id'])) == 1
        assert hub.friends(b['id']) == []  # Caller cannot edit recipient's list.
        private = struct.pack('>Q',b['id'])+p.text('你好')+p.text('')+bytes(5)
        assert pa.request(p.PRIVATE_SEND,private) == []
        assert pb.receive() == [(p.PRIVATE_RECEIVE,p.private_message(a,'你好'))]
        assert pc.receive() == []
        # Mix pushes and direct responses: both must consume the same RC4/MPPC stream.
        assert pb.request(p.SEARCH_ID_SEND,struct.pack('>Q',a['id']))[0][0] == p.SEARCH_ID_RECEIVE
        for channel, recipients in ((p.WORLD_CHANNEL,(pb,pc)),(p.SCHOOL_CHANNEL,(pb,))):
            expected = (p.CHAT_RECEIVE,p.chat_message(a,channel,'江湖好'))
            assert pa.request(p.CHAT_SEND,struct.pack('>i',channel)+p.text('江湖好')+p.text('')+b'\0') == [expected]
            for peer in (pb,pc): assert peer.receive() == ([expected] if peer in recipients else [])
        pc.session.world.position=(1008,0,0)
        pa.request(p.CHAT_SEND,struct.pack('>i',p.CURRENT_CHANNEL)+p.text('同地图')+p.text('')+b'\0')
        assert len(pb.receive()) == 1 and pc.receive() == []
        for body in (b'', struct.pack('>Q',b['id'])+p.text('你好')+p.text('')+bytes(4)+b'\x01', private+b'\0'):
            assert pa.request(p.PRIVATE_SEND,body) == [] and pb.receive() == []
        assert pa.request(p.CHAT_SEND,struct.pack('>i',1)+p.text('队伍不可外泄')+p.text('')+b'\0') == []
        assert pb.receive() == [] and pc.receive() == []
        pb.close()
        assert pa.receive() == [(p.ONLINE,struct.pack('>Qi',b['id'],0))]
        assert pa.request(p.PRIVATE_SEND,private) == []
        pb = Peer(store,hub,b,b'2222')
        assert pa.receive() == [(p.ONLINE,struct.pack('>Qi',b['id'],1))]
        pa.close()
        pa = Peer(store,hub,a)
        assert pa.initial == [(p.FRIENDS_INIT,b'\x01'+p.friend_info(b,True)+bytes(4))]
        assert pa.request(p.DELETE_SEND,add) == [(p.DELETE_RECEIVE,struct.pack('>Q',b['id']))]
        assert SocialHub(AccountStore(path)).friends(a['id']) == []
        pa.close(); pb.close(); pc.close()
        assert hub.online == {}
    result = {'passed':['encrypted authenticated cross-account lookup','name and missing lookup',
        'durable idempotent directed contacts','private recipient isolation',
        'interleaved push/reply cipher continuity','world/school/map routing',
        'invalid and unimplemented channels rejected','disconnect/reconnect presence',
        'relogin friend initialization','durable delete','online cleanup'],
        'real_client_social_verified':False}
    write_json(OUT/'evidence/social-verification.json',result)
    print(json.dumps(result))


if __name__ == '__main__': main()
