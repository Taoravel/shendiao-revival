"""Queued map commands retain player-view checks at the actual dequeue seam."""
import struct
from unittest.mock import patch
from inspect_client import OUT,write_json
from world_owner import MapOwner,MapAddress,Location,MoveCommand
from world_roles import RoleScene
from world_role_protocol import RoleBasic,S_ROLE_MOVE


def main():
    catalog={mid:dict(available=True,width=1024,height=1024,portals={}) for mid in (7,8)}
    address=MapAddress(7,1,0)
    owner=MapOwner(address,catalog,capacity=2,transfer_capacity=2,mailbox_capacity=2)
    view=RoleScene(address,catalog,radius=64,role_capacity=2,pair_capacity=1,batch_size=2)
    current=Location(1,'epoch-a',address,1,100,100)
    owner.join_with_view(current,RoleBasic(1,'队列甲',9,100,100,0x71),view)
    peer=Location(2,'epoch-b',address,1,120,100)
    owner.join_with_view(peer,RoleBasic(2,'队列乙',10,120,100,0x32),view)
    wrong_view=RoleScene(MapAddress(8,1,0),catalog,radius=64,
        role_capacity=2,pair_capacity=1,batch_size=2)
    def command(expected,key,x,deadline=100):
        return MoveCommand(expected,key,deadline,0xc0faa,b'\0'+struct.pack('>hhQ',x,100,0))
    assert owner.process_one_with_view(0,view) is None
    assert owner.submit(command(current,'first',110),0)=='accepted'
    try:owner.process_one_with_view(1,wrong_view)
    except ValueError:pass
    else:raise AssertionError('Foreign projection consumed a queued map command')
    with patch('builtins.open',side_effect=AssertionError('Map dequeue file I/O')), \
         patch('io.open',side_effect=AssertionError('Map dequeue file I/O')):
        result,change=owner.process_one_with_view(1,view)
    assert not result.rejection and result.location.position==(7,110,100)
    assert owner.location(1)==view.snapshot(1).location==change.presence.location==result.checkpoint
    assert len(change.deliveries)==1 and change.deliveries[0].recipient_role_id==2
    assert change.deliveries[0].packets==((S_ROLE_MOVE,struct.pack('>Qhh',1,110,100)),)
    current=result.location
    assert owner.submit(command(current,'second',120),2)=='accepted'
    assert owner.submit(command(current,'stale-after-second',130),2)=='accepted'
    assert owner.submit(command(current,'over-budget',140),2)=='backpressure'
    result,change=owner.process_one_with_view(3,view)
    assert not result.rejection and result.location.position==(7,120,100)
    before=owner.location(1),view.snapshot(1),view.snapshot(2)
    result,change=owner.process_one_with_view(3,view)
    assert result.rejection=='stale_position' and change is None
    assert before==(owner.location(1),view.snapshot(1),view.snapshot(2))
    assert owner.process_one_with_view(3,view) is None
    assert owner.submit(command(owner.location(1),'expired-in-queue',130,5),4)=='accepted'
    result,change=owner.process_one_with_view(5,view)
    assert result.rejection=='deadline' and change is None
    assert before==(owner.location(1),view.snapshot(1),view.snapshot(2))
    report=dict(passed=['empty dequeue returns no command',
        'foreign view rejected without consuming queued command',
        'accepted dequeue publishes authority and native peer move together without file I/O',
        'bounded queue and dequeue position-version check',
        'dequeue deadline check preserves authority and projection'],
        shared_runtime_integrated=False,gui_verified=False,live_server_changed=False)
    write_json(OUT/'evidence/world-mailbox-view-verification.json',report)
    print(report)


if __name__=='__main__':main()
