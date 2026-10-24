"""Exercise real session dispatch and reopened storage with native wire fixtures."""
import json
from pathlib import Path
import struct
import tempfile
from accounts import AccountStore
from gateway import Session
from inspect_client import OUT, write_json
from wire import FrameReader, frame, octets, read_octets
from social import SocialHub


def enter(store, role_id):
    session = Session(store)
    # Authenticated fixture; the encrypted handshake is covered by verify_gateway.
    session.state, session.account_id = 'roles', 1111
    packets = session.feed(frame(0xc0005, struct.pack('>Q', role_id)+octets(b'')+b'\0'))
    scene = FrameReader().feed(b''.join(packets))[-1][1]
    _, offset = read_octets(scene)
    return session, struct.unpack_from('>hh', scene, offset)


def main():
    fixtures = json.loads((OUT/'evidence/movement-native-fixtures.json').read_text(encoding='utf-8'))['fixtures']
    with tempfile.TemporaryDirectory(dir=OUT, prefix='world-check-') as temp:
        path = Path(temp)/'accounts.sqlite3'
        store = AccountStore(path)
        role = store.create_role(1111, '行走验证', 12, 1010101)
        session, position = enter(store, role['id'])
        assert position == (8480, 6976)
        stop = next(f for f in fixtures if f['type'] == 0xc0faa and not f['path'])
        session.feed(frame(stop['type'], bytes.fromhex(stop['body_hex'])))
        _, restored = enter(AccountStore(path), role['id'])
        assert restored == (8496, 6992), f'Position lost after re-entry: {restored}'
        move = next(f for f in fixtures if f['type'] == 0xc0fa1)
        # The target is not proof of arrival, even if it is very far away.
        target = bytearray.fromhex(move['body_hex'])
        struct.pack_into('>hh', target, 4, 8600, 7100)
        session.feed(frame(move['type'], target))
        assert enter(AccountStore(path), role['id'])[1] == restored
        check = next(f for f in fixtures if f['type'] == 0xc0fa3 and f['path'])
        body = bytearray.fromhex(check['body_hex'])
        struct.pack_into('>hh', body, 0, 8512, 7008)
        session.feed(frame(check['type'], body))
        assert enter(AccountStore(path), role['id'])[1] == (8512, 7008)
        # Invalid complete frames must reject rather than silently hang or save.
        for invalid in (b'', b'\x80', bytes.fromhex(stop['body_hex'])+b'\0',
                        b'\0'+struct.pack('>hhQ', -1, 7000, 0),
                        b'\0'+struct.pack('>hhQ', 8704, 7000, 0),
                        b'\0'+struct.pack('>hhQ', 8000, 7424, 0)):
            try:
                session.feed(frame(0xc0faa, invalid))
            except ValueError:
                pass
            else:
                raise AssertionError('Malformed movement accepted')
        assert enter(AccountStore(path), role['id'])[1] == (8512, 7008)
        try:
            store.save_position(2222, role['id'], (1007, 1, 1))
        except ValueError:
            pass
        else:
            raise AssertionError('Foreign role position overwritten')
        social = SocialHub(store)
        session.social = social
        session.feed(frame(0xc003d, b''))
        session.feed(frame(stop['type'], bytes.fromhex(stop['body_hex'])))
        assert enter(AccountStore(path), role['id'])[1] == (8496, 6992)
        session.close()
        session, _ = enter(store, role['id'])
        portal = b'\0'+struct.pack('>hhQ', 8592, 7104, 0)
        packets = session.feed(frame(0xc0faa, portal))
        decoded = FrameReader().feed(b''.join(packets))
        assert len(decoded) == 1 and decoded[0][0] == 0xc0fa9, 'Original Linan -> Taihu portal did not transfer'
        scene = decoded[0][1]
        _, offset = read_octets(scene)
        assert struct.unpack_from('>hhBiQB', scene, offset) == (896, 3776, 0, 0, 1014, 0)
        assert enter(AccountStore(path), role['id'])[1] == (896, 3776)
        assert session.scene_id == 1014
    write_json(OUT/'evidence/world-movement-verification.json', {
        'native_stop_persisted_on_reentry': True,
        'move_intent_does_not_teleport': True,
        'check_position_not_path_destination_saved': True,
        'malformed_and_negative_inputs_rejected': True,
        'foreign_role_update_rejected': True,
        'movement_with_online_social_dispatch': True,
        'original_linan_taihu_portal_and_reentry': True,
        'real_client_movement_verified': False})
    print('PASS native stop -> durable position -> scene re-entry')


if __name__ == '__main__': main()
