"""Decode observed 0x89abcdef client XML; require full structural consumption.

The layout is inferred from shipped data, not yet checked against native code.
"""
import xml.etree.ElementTree as ET


def decode(data):
    if data[:4] != bytes.fromhex('89abcdef'):
        return ET.fromstring(data)
    pos = 4

    def take(n):
        nonlocal pos
        if n < 0 or pos + n > len(data):
            raise ValueError('Truncated BXML')
        result = data[pos:pos+n]
        pos += n
        return result

    def uint():
        first = take(1)[0]
        if first < 0x80:
            return first
        if first < 0xc0:
            return ((first & 0x3f) << 8) | take(1)[0]
        if first < 0xe0:
            return ((first & 0x1f) << 24) | int.from_bytes(take(3), 'big')
        if first == 0xe0:
            return int.from_bytes(take(4), 'big')
        raise ValueError('Unknown BXML integer prefix')

    count = uint()
    if count > len(data):
        raise ValueError('Invalid BXML dictionary count')
    strings = []
    for _ in range(count):
        raw = take(uint())
        if len(raw) < 2 or len(raw) % 2 or raw[-2:] != b'\0\0':
            raise ValueError('Invalid BXML string')
        strings.append(raw[:-2].decode('utf-16-le'))

    def string(index):
        if index >= len(strings):
            raise ValueError('Invalid BXML dictionary reference')
        return strings[index]

    def node(depth=0):
        if depth > 200:
            raise ValueError('Excessive BXML nesting')
        kind = uint()
        if kind not in (0, 1):
            raise ValueError(f'Unsupported BXML node type {kind} at {pos}')
        element = ET.Element(string(uint()))
        value = uint()
        if value != 0xffffffff:
            element.text = string(value)
        attrs = uint()
        if attrs > len(data) - pos:
            raise ValueError('Invalid BXML attribute count')
        for _ in range(attrs):
            key, value = string(uint()), string(uint())
            if key in element.attrib:
                raise ValueError('Duplicate BXML attribute')
            element.set(key, value)
        children = uint()
        if children > len(data) - pos:
            raise ValueError('Invalid BXML child count')
        for _ in range(children):
            child = node(depth + 1)
            if isinstance(child, str):
                if len(element):
                    element[-1].tail = (element[-1].tail or '') + child
                else:
                    element.text = (element.text or '') + child
            else:
                element.append(child)
        if kind == 1:
            if element.tag != '#text' or attrs or children or value == 0xffffffff:
                raise ValueError('Unsupported BXML text node')
            return element.text or ''
        return element

    root = node()
    if isinstance(root, str):
        raise ValueError('BXML root must be an element')
    if pos != len(data):
        raise ValueError(f'BXML trailing data at {pos}/{len(data)}')
    return root
