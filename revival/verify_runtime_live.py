"""Real loopback TCP regression; reads an existing role without granting assets.

This is a network/native-decoder check, not native GUI visual acceptance.
"""
from contextlib import closing
import hashlib
import hmac
import socket
import sqlite3
import struct
from crypto import ArcFour
from wire import FrameReader,frame,octets,read_octets
from verify_mppc_native import NativeDecoder
from inspect_client import OUT,write_json
from social_protocol import FRIENDS_INIT


def main():
    with closing(sqlite3.connect(f'file:{OUT / "runtime/accounts.sqlite3"}?mode=ro',uri=True)) as db:
        role_id=db.execute('SELECT id FROM roles WHERE account_id=1111 ORDER BY id LIMIT 1').fetchone()[0]
    with closing(socket.create_connection(('127.0.0.1',28993),timeout=5)) as peer:
        reader=FrameReader(); incoming=outgoing=decoder=None; buffered=[]
        def read(count):
            while len(buffered)<count:
                data=peer.recv(65536)
                if not data: raise ConnectionError('Gateway closed')
                if incoming: data=decoder.feed(incoming.transform(data))
                buffered.extend(reader.feed(data))
            result=buffered[:count]; del buffered[:count]
            return result
        def send(kind,body):
            data=frame(kind,body)
            peer.sendall(outgoing.transform(data) if outgoing else data)
        challenge,_=read_octets(read(1)[0][1]); secret=hashlib.md5(b'11111111').digest()
        proof=hmac.new(secret,challenge,hashlib.md5).digest()
        send(103,octets(b'1111')+octets(proof)+bytes(4)+octets(b'')+bytes(4)+octets(b''))
        reply=read(1); assert reply[0][0]==106
        nonce,_=read_octets(reply[0][1]); outgoing=ArcFour(hmac.new(secret,b'1111'+nonce,hashlib.md5).digest())
        nonce=b'live-probe-nonce'; incoming=ArcFour(hmac.new(secret,b'1111'+nonce,hashlib.md5).digest()); decoder=NativeDecoder()
        send(106,octets(nonce)+bytes(4)); assert read(1)[0][0]==110
        send(0xc0001,b''); assert read(1)[0][0]==0xc0002
        send(0xc0078,struct.pack('>Q',role_id)); assert read(1)==[(0xc0079,b'')]
        send(0xc0005,struct.pack('>Q',role_id)+octets(b'')+b'\0')
        assert [k for k,b in read(3)]==[0xc0006,0xc0007,0xc0fa9]
        send(0xc003d,b''); assert read(1)[0][0]==FRIENDS_INIT
        send(100,b'test')
        # Scene NPC/EXP initialization can follow friends in the same stream.
        for _ in range(128):
            reply=read(1)
            if reply[0][0]==100:
                assert reply==[(100,b'test')]
                break
        else: raise AssertionError('Heartbeat not found within initialization budget')
    result={'transport':'real TCP 127.0.0.1:28993','passed':['authentication','role list','preflight',
            'world/time/scene order','after-enter friends initialization','continuous native decrypt/decompress','heartbeat'],
            'existing_role_id':role_id,'assets_changed':False,'native_gui_visual_verified':False}
    write_json(OUT/'evidence/runtime-live-network.json',result)
    print(result)


if __name__=='__main__': main()
