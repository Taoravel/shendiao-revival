"""Read the original PFS archives without modifying the game installation."""
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import struct
import zlib


@dataclass(frozen=True)
class Entry:
    name: str
    offset: int
    stored: int
    size: int
    crc: int
    method: int
    raw_name: bytes


class PfsArchive:
    """Interface: entries plus read(name); reject corrupt/unsupported records."""

    def __init__(self, path):
        self.path = Path(path)
        self.entries = {}
        with self.path.open('rb') as stream:
            stream.seek(-22, 2)
            tail = stream.read(22)
            sig, disk, start_disk, count_disk, count, length, offset, comment = struct.unpack('<4s4H2IH', tail)
            if sig != b'PFSD' or disk or start_disk or count != count_disk or comment:
                raise ValueError('Unsupported PFS directory trailer')
            if offset + length != self.path.stat().st_size - 22:
                raise ValueError('Invalid PFS directory extent')
            self.directory_offset = offset
            stream.seek(offset)
            for _ in range(count):
                record = stream.read(46)
                if len(record) != 46 or record[:4] != b'PFSF':
                    raise ValueError('Invalid PFS central record')
                fields = struct.unpack('<4s6H3I5H2I', record)
                _, made, needed, flags, method, time, date, crc, stored, size, nl, el, cl, disk, internal, external, local = fields
                if flags & ~0x800 or method not in (0, 8) or disk:
                    raise ValueError('Unsupported PFS encoding')
                raw = stream.read(nl)
                name = raw.decode('utf-8' if flags & 0x800 else 'gb18030')
                safe = PurePosixPath(name.replace('\\', '/'))
                if safe.is_absolute() or '..' in safe.parts or ':' in name or '\x00' in name:
                    raise ValueError('Unsafe PFS path')
                if name in self.entries or local + 30 + nl + stored > offset:
                    raise ValueError('Duplicate or invalid PFS entry')
                stream.seek(el + cl, 1)
                self.entries[name] = Entry(name, local, stored, size, crc, method, raw)
            if stream.tell() != offset + length:
                raise ValueError('PFS directory length mismatch')

    def read(self, name, max_size=128 * 1024 * 1024):
        entry = self.entries[name]
        if entry.size > max_size:
            raise ValueError('PFS entry exceeds output limit')
        with self.path.open('rb') as stream:
            stream.seek(entry.offset)
            header = stream.read(30)
            if len(header) != 30 or header[:4] != b'PFSH':
                raise ValueError('Invalid PFS local record')
            _, version, flags, method, time, date, crc, stored, size, nl, el = struct.unpack('<4s5H3I2H', header)
            if (method, crc, stored, size) != (entry.method, entry.crc, entry.stored, entry.size):
                raise ValueError('PFS local/central mismatch')
            if stream.read(nl) != entry.raw_name:
                raise ValueError('PFS local name mismatch')
            stream.seek(el, 1)
            if stream.tell() + stored > self.directory_offset:
                raise ValueError('PFS payload crosses directory')
            payload = stream.read(stored)
        if name.endswith('/') and stored == size == crc == 0:
            data = b''
        elif method == 8:
            decoder = zlib.decompressobj(-15)
            data = decoder.decompress(payload, max_size + 1)
            if len(data) > max_size or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
                raise ValueError('Invalid or oversized PFS deflate stream')
        else:
            data = payload
        if len(data) != size or zlib.crc32(data) != crc:
            raise ValueError('PFS size/CRC mismatch')
        return data
