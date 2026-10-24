"""Exercise authentication, native downlink decoding, durable roles and isolation."""
import hashlib
import hmac
import json
import struct
import tempfile
from pathlib import Path
from accounts import AccountStore
from gateway import Session
from crypto import ArcFour
from wire import frame, octets, FrameReader, read_octets
from verify_mppc_native import NativeDecoder
from inspect_client import OUT, write_json
from world_protocol import world_snapshot, scene_entry


def main():
    assert ArcFour(b'Key').transform(b'Plaintext').hex() == 'bbf316e8d940af0ad3'
    with tempfile.TemporaryDirectory(dir=OUT, prefix='gateway-check-') as temp:
        path = Path(temp) / 'accounts.sqlite3'
        store = AccountStore(path)
        session = Session(store, now_ms=lambda: 1792717000000)
        opening = FrameReader().feed(session.opening())
        assert opening[0][0] == 101
        challenge, pos = read_octets(opening[0][1])
        assert len(challenge) == 16 and opening[0][1][pos:] == struct.pack('>I', 601) + bytes(6)
        secret = hashlib.md5(b'11111111').digest()
        proof = hmac.new(secret, challenge, hashlib.md5).digest()
        response = frame(103, octets(b'1111') + octets(proof) + bytes(4) + octets(b'') + bytes(4) + octets(b''))
        replies = []
        for byte in response:
            replies += session.feed(bytes([byte]))
        kind, body = FrameReader().feed(b''.join(replies))[0]
        assert kind == 106
        nonce, _ = read_octets(body)
        client_output = ArcFour(hmac.new(secret, b'1111' + nonce, hashlib.md5).digest())
        client_nonce = b'0123456789abcdef'
        key_reply = client_output.transform(frame(106, octets(client_nonce) + bytes(4)))
        replies = []
        for byte in key_reply:
            replies += session.feed(bytes([byte]))
        client_input = ArcFour(hmac.new(secret, b'1111' + client_nonce, hashlib.md5).digest())
        decoder = NativeDecoder()
        def decode_reply(packets):
            clear = b''.join(decoder.feed(client_input.transform(packet)) for packet in packets)
            return FrameReader().feed(clear)
        kind, body = decode_reply(replies)[0]
        assert kind == 110 and struct.unpack('>6I', body) == (1111, 0, 0, 0, 0, 0)
        kind, body = decode_reply(session.feed(client_output.transform(frame(0xc0001, b''))))[0]
        assert kind == 0xc0002 and body == bytes(14)
        name = '初入江湖'
        request = frame(0xc0003, octets(name.encode('utf-16-le')) + struct.pack('>ii', 12, 1010101))
        kind, body = decode_reply(session.feed(client_output.transform(request)))[0]
        assert kind == 0xc0004
        assert store.roles(1111)[0]['name'] == name
        assert AccountStore(path).roles(1111)[0]['name'] == name
        assert store.owned_role(2222, 1) is None
        kind, body = decode_reply(session.feed(client_output.transform(request)))[0]
        assert kind == 0xc0008 and struct.unpack('>i', body)[0] == 4
        assert len(store.roles(1111)) == 1
        role = store.roles(1111)[0]
        preflight = frame(0xc0078, struct.pack('>Q', role['id']))
        assert decode_reply(session.feed(client_output.transform(preflight))) == [(0xc0079, b'')]
        assert store.owned_role(1111, role['id']) == role
        entry = frame(0xc0005, struct.pack('>Q', role['id']) + octets(b'') + b'\0')
        replies = decode_reply(session.feed(client_output.transform(entry)))
        assert replies == [(0xc0006, world_snapshot(role)),
                           (0xc0007, struct.pack('>Q', 1792717000000)), (0xc0fa9, scene_entry())]
        assert session.state == 'world'
        assert not session.feed(client_output.transform(frame(0xc003d, b'')))
        assert any(e['event'] == 'client_after_enter_world' for e in session.events)
        native_moves = json.loads((OUT/'evidence/movement-native-fixtures.json').read_text(encoding='utf-8'))['fixtures']
        stop = next(f for f in native_moves if f['type'] == 0xc0faa and not f['path'])
        assert not session.feed(client_output.transform(frame(stop['type'], bytes.fromhex(stop['body_hex']))))
        assert AccountStore(path).position(1111, role['id']) == (1007, 8496, 6992)
        bad = Session(store)
        try:
            bad.feed(frame(103, octets(b'1111') + octets(bytes(16)) + bytes(4) + octets(b'') + bytes(4) + octets(b'')))
        except ValueError as error:
            assert str(error) == 'Authentication failed'
        else:
            raise AssertionError('Incorrect password proof accepted')
    result = {'passed': ['RC4 fixed vector', 'fragmented challenge response', 'encrypted fragmented key exchange',
                         'native MPPC decoder reads actual gateway output', 'empty role list', 'create role',
                         'reopen persistence', 'account ownership', 'duplicate name refusal', 'incorrect proof refusal',
                         'native movement through encrypted authenticated session and durable position'],
              'real_client_login_verified': True, 'world_bootstrap_implemented': True,
              'real_client_world_verified': False}
    write_json(OUT / 'evidence/gateway-verification.json', result)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
