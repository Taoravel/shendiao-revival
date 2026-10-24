"""Bounded GNET compact integers and incremental protocol framing."""
import struct


class NeedMoreData(Exception):
    pass


def compact(value):
    if not 0 <= value <= 0xffffffff:
        raise ValueError('Compact integer outside uint32')
    if value < 0x80:
        return bytes([value])
    if value < 0x4000:
        return struct.pack('>H', value | 0x8000)
    if value < 0x20000000:
        return struct.pack('>I', value | 0xc0000000)
    return b'\xe0' + struct.pack('>I', value)


def read_compact(data, offset=0):
    if offset >= len(data):
        raise NeedMoreData()
    first = data[offset]
    size = 1 if first < 0x80 else 2 if first < 0xc0 else 4 if first < 0xe0 else 5
    if offset + size > len(data):
        raise NeedMoreData()
    if size == 5:
        value = int.from_bytes(data[offset+1:offset+5], 'big')
    else:
        mask = {1: 0x7f, 2: 0x3fff, 4: 0x3fffffff}[size]
        value = int.from_bytes(data[offset:offset+size], 'big') & mask
    return value, offset + size


def octets(value):
    return compact(len(value)) + value


def read_octets(data, offset=0, limit=65536):
    size, offset = read_compact(data, offset)
    if size > limit:
        raise ValueError('Octets limit exceeded')
    if offset + size > len(data):
        raise NeedMoreData()
    return bytes(data[offset:offset+size]), offset + size


def frame(kind, body):
    return compact(kind) + octets(body)


class FrameReader:
    def __init__(self, limit=1024*1024):
        self.buffer = bytearray()
        self.limit = limit

    def feed(self, data):
        if len(self.buffer) + len(data) > self.limit + 10:
            raise ValueError('Buffered protocol limit exceeded')
        self.buffer += data
        frames = []
        while self.buffer:
            try:
                kind, start = read_compact(self.buffer)
                size, start = read_compact(self.buffer, start)
                if size > self.limit:
                    raise ValueError('Protocol payload limit exceeded')
                if start + size > len(self.buffer):
                    break
                frames.append((kind, bytes(self.buffer[start:start+size])))
                del self.buffer[:start+size]
            except NeedMoreData:
                break
        return frames
