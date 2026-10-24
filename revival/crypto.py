"""Stateful legacy ARCFour used by the original game transport."""


class ArcFour:
    def __init__(self, key):
        if not key:
            raise ValueError('RC4 key must not be empty')
        self.state = list(range(256))
        j = 0
        for i in range(256):
            j = (j + self.state[i] + key[i % len(key)]) & 255
            self.state[i], self.state[j] = self.state[j], self.state[i]
        self.i = self.j = 0

    def transform(self, data):
        result = bytearray()
        s = self.state
        for byte in data:
            self.i = (self.i + 1) & 255
            self.j = (self.j + s[self.i]) & 255
            s[self.i], s[self.j] = s[self.j], s[self.i]
            result.append(byte ^ s[(s[self.i] + s[self.j]) & 255])
        return bytes(result)
