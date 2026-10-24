"""GNET's byte-aligned MPPC literal blocks for server-to-client transport.

Keep one Encoder per connection; encode plaintext protocol frames, then pass
results through the connection's continuous RC4 stream. No PPP header or
length prefix is added.
The deliberately literal-only encoding never references the 8192-byte history.
"""


def _block(plaintext: bytes) -> bytes:
    """Encode at most 8192 literals, EOS 1111000000 and zero alignment bits."""
    out = bytearray()
    for start in range(0, max(1, len(plaintext)), 8192):
        accumulator = 0
        count = 0
        block = plaintext[start:start + 8192]
        for byte in block:
            width = 8 if byte < 128 else 9
            token = byte if byte < 128 else 0x100 | (byte & 127)
            accumulator = (accumulator << width) | token
            count += width
            while count >= 8:
                count -= 8
                out.append((accumulator >> count) & 255)
            accumulator &= (1 << count) - 1
        accumulator = (accumulator << 10) | 0x3c0
        count += 10
        padding = -count % 8
        accumulator <<= padding
        count += padding
        out.extend(accumulator.to_bytes(count // 8, 'big'))
    return bytes(out)


class Encoder:
    """One encoder per connection, retaining the native history write position."""

    def __init__(self):
        self._position = 0

    def encode(self, plaintext: bytes) -> bytes:
        if not plaintext:
            return _block(b'')
        result = bytearray()
        start = 0
        while start < len(plaintext):
            length = min(8192 - self._position, len(plaintext) - start)
            result.extend(_block(plaintext[start:start + length]))
            self._position = (self._position + length) % 8192
            start += length
        return bytes(result)


def encode(plaintext: bytes) -> bytes:
    """Encode an independent stream. Use Encoder for consecutive sends."""
    return Encoder().encode(plaintext)
