"""Native connection state only; no storage, gameplay, or peer references."""
import hashlib
import hmac
import secrets
import struct
from crypto import ArcFour
from mppc import Encoder
from wire import FrameReader, frame, octets, read_octets


class ConnectionCodec:
    def __init__(self):
        self.challenge = secrets.token_bytes(16)
        self.identity = self.secret = self.account_id = None
        self.in_cipher = self.out_cipher = None
        self.reader, self.encoder = FrameReader(), Encoder()
        self.state = 'response'

    def opening(self):
        return frame(101, octets(self.challenge)+struct.pack('>II',601,0)+bytes(2))

    def decode(self, data):
        return self.reader.feed(self.in_cipher.transform(data) if self.in_cipher else data)

    def send(self, kind, body):
        data = frame(kind, body)
        return self.out_cipher.transform(self.encoder.encode(data)) if self.out_cipher else data

    @staticmethod
    def auth_fields(body):
        identity, pos = read_octets(body, limit=128)
        proof, pos = read_octets(body, pos, limit=128)
        if pos+4 > len(body): raise ValueError('Truncated response')
        _, pos = read_octets(body, pos+4, limit=4096)
        if pos+4 > len(body): raise ValueError('Truncated response field')
        _, pos = read_octets(body, pos+4, limit=4096)
        if pos != len(body): raise ValueError('Response trailing data')
        return identity, proof

    def accept_auth(self, body, account):
        self.identity, proof = self.auth_fields(body)
        if not account or not hmac.compare_digest(proof, hmac.new(account[1],self.challenge,hashlib.md5).digest()):
            raise ValueError('Authentication failed')
        self.account_id, self.secret = account
        nonce = secrets.token_bytes(16)
        self.in_cipher = ArcFour(hmac.new(self.secret,self.identity+nonce,hashlib.md5).digest())
        self.state = 'key_exchange'
        return frame(106,octets(nonce)+bytes(4))  # immutable plain handshake frame

    def accept_key(self, body):
        nonce, pos = read_octets(body,limit=16)
        if len(nonce)!=16 or pos+4!=len(body): raise ValueError('Invalid client key exchange')
        self.out_cipher = ArcFour(hmac.new(self.secret,self.identity+nonce,hashlib.md5).digest())
        self.secret = None
        self.state = 'roles'
        return 110, struct.pack('>6I',self.account_id,0,0,0,0,0)
