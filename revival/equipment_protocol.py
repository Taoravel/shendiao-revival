"""Confirmed ordinary equipment endurance updates; logical messages only."""
import struct
from wire import compact

REQUEST_ENDURES=0xc04c6
REFRESH_ENDURE=0xc0412
REFRESH_MAX_ENDURE=0xc0414


def _column(column):
    if type(column) is not int or column not in (1,4):
        raise ValueError('Unrestored equipment column')


def endurance_refresh(column, entries):
    _column(column)
    if type(entries) is not tuple or len(entries)>256:
        raise ValueError('Immutable endurance entries required')
    seen=set();body=[]
    for pair in entries:
        if (type(pair) is not tuple or len(pair)!=2 or any(type(v) is not int for v in pair)
                or not 1<=pair[0]<=0x7fffffff or pair[0] in seen or not 0<=pair[1]<=0x7fffffff):
            raise ValueError('Invalid endurance entry')
        seen.add(pair[0]);body.append(struct.pack('>ii',*pair))
    return REFRESH_ENDURE,struct.pack('>i',column)+compact(len(entries))+b''.join(body)


def maximum_refresh(column,key,maximum):
    _column(column)
    if any(type(v) is not int or not 1<=v<=0x7fffffff for v in (key,maximum)):
        raise ValueError('Invalid maximum endurance entry')
    return REFRESH_MAX_ENDURE,struct.pack('>iii',column,key,maximum)
