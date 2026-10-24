"""Bounded startup frame reads through the external socket Interface."""
import time


def read_frames(client,reader,deadline,*,clock=time.monotonic):
    while True:
        remaining=deadline-clock()
        if remaining<=0:raise TimeoutError('Service health probe deadline expired')
        client.settimeout(remaining)
        data=client.recv(65536)
        if not data:raise ConnectionError('Service closed during health probe')
        if clock()>=deadline:raise TimeoutError('Service health probe deadline expired')
        frames=reader.feed(data)
        if frames:return frames
