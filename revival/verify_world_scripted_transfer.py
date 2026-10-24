"""Trusted quest transfers reuse the exact map-owner handoff lifecycle."""
from dataclasses import replace
from world_owner import MapOwner, MapAddress, Location


def refused(action):
    try:
        action()
    except ValueError:
        return
    raise AssertionError('Invalid or stale scripted transfer accepted')


def main():
    catalog = {7:dict(available=True,width=128,height=128,portals={}),
               8:dict(available=True,width=128,height=128,portals={})}
    a, b = MapAddress(7,1,0), MapAddress(8,1,0)
    source = MapOwner(a,catalog,capacity=2,transfer_capacity=2,mailbox_capacity=2)
    target = MapOwner(b,catalog,capacity=2,transfer_capacity=2,mailbox_capacity=2)
    position = source.join(Location(1,'quest-epoch',a,3,32,32))
    kwargs = dict(request_id='committed-quest-transfer',deadline_ms=100,now_ms=1)
    refused(lambda: source.prepare_transfer(replace(position,login_epoch='old'),(8,48,48),**kwargs))
    refused(lambda: source.prepare_transfer(position,(8,128,48),**kwargs))
    refused(lambda: source.prepare_transfer(position,(7,48,48),**kwargs))
    offer = source.prepare_transfer(position,(8,48,48),**kwargs)
    assert source.location(1) == position  # preparing never moves or freezes authority
    assert source.prepare_transfer(position,(8,48,48),**kwargs) == offer
    refused(lambda: source.prepare_transfer(position,(8,64,48),**kwargs))
    reservation = target.reserve(offer,now_ms=2)
    frozen = source.freeze(reservation,now_ms=3)
    refused(lambda: source.prepare_transfer(position,(8,48,48),**kwargs))
    committed = target.activate(frozen,now_ms=4)
    source.finalize(committed)
    active = target.ready(committed.location)
    assert source.location(1) is None and active.position == (8,48,48) and active.state == 'active'
    assert target.location(1) == active
    print('PASS trusted scripted offer: scope, bounds, retry, conflict and existing handoff')


if __name__ == '__main__':
    main()
