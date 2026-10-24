"""EOF, fragmentation and total deadline checks, without a live socket or DB."""
from pathlib import Path
import socket,sys
from service_health_probe import read_frames

SOURCE=Path(__file__).resolve().parents[1]/'runtime/deployments/world-collision-20261023T204238Z/source'
sys.path.insert(0,str(SOURCE))
from wire import FrameReader,frame


def check(condition,message):
    if not condition:raise AssertionError(message)


class Socket:
    def __init__(self,chunks,*,clock=None,cost=.0):
        self.chunks=iter(chunks);self.calls=0;self.timeouts=[];self.clock=clock;self.cost=cost
    def settimeout(self,value):self.timeouts.append(value)
    def recv(self,count):
        self.calls+=1
        if self.clock is not None:self.clock[0]+=self.cost
        chunk=next(self.chunks)
        if isinstance(chunk,BaseException):raise chunk
        return chunk


def fails(kind,fn):
    try:fn()
    except kind:return
    raise AssertionError('Required probe failure did not occur: '+kind.__name__)


def main():
    clock=[0.0]
    closed=Socket([b''])
    fails(ConnectionError,lambda:read_frames(closed,FrameReader(),5,clock=lambda:clock[0]))
    check(closed.calls==1,'EOF was retried instead of terminating')
    raw=frame(101,b'fragmented challenge')
    fragmented=Socket([raw[:1],raw[1:3],raw[3:]])
    check(read_frames(fragmented,FrameReader(),5,clock=lambda:0)==[(101,b'fragmented challenge')],
        'Fragmented real frames were not reassembled')
    timed=Socket([socket.timeout('controlled timeout')])
    fails(TimeoutError,lambda:read_frames(timed,FrameReader(),5,clock=lambda:0))
    expired=Socket([])
    fails(TimeoutError,lambda:read_frames(expired,FrameReader(),0,clock=lambda:0))
    check(expired.calls==0,'Expired total deadline performed I/O')
    # Two phases share one budget; receiving a first frame must not reset it.
    clock=[0.0]
    first=Socket([frame(101,b'first')],clock=clock,cost=4)
    check(read_frames(first,FrameReader(),5,clock=lambda:clock[0])==[(101,b'first')],'First phase failed')
    second=Socket([frame(100,b'ping')[:1],frame(100,b'ping')[1:]],clock=clock,cost=.75)
    fails(TimeoutError,lambda:read_frames(second,FrameReader(),5,clock=lambda:clock[0]))
    check(second.timeouts==[1.0,.25],'Later phase reset or exceeded the shared budget')
    print({'all_passed':True,'groups':5,'live_socket':False,'database':False})


if __name__=='__main__':main()
