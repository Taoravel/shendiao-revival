"""Actual read-only query establishes a bounded, generation-scoped confirmation."""
from pathlib import Path
from dataclasses import replace,FrozenInstanceError
import struct
import tempfile
import time
from accounts import AccountStore
from inventory import Inventory
from inspect_client import OUT,write_json
from world_npcs import NpcScene
from world_owner import MapAddress,Location
from world_role_delivery import RoleViewBinding
import npc_identification_query
import runtime_storage


def refused(action):
    try:action()
    except ValueError:return
    raise AssertionError('Invalidated original confirmation was accepted')


def main():
    try:import npc_equipment_identification as identification
    except ModuleNotFoundError:
        write_json(OUT/'evidence/npc-identification-dialogue-baseline.json',{
            'failure':'NPC confirmation has no server query dialogue Module',
            'seam':'accepted actual query -> frozen dialogue -> original confirmation',
            'live_database_modified':False})
        raise
    with tempfile.TemporaryDirectory(prefix='npc-identification-dialogue-') as directory:
        store=AccountStore(Path(directory)/'state.sqlite3')
        role=store.create_role(1111,'鉴定会话期限',12,1010101);prepared=runtime_storage.prepare(store)
        npc_identification_query.prepare(store)
        epoch=store.acquire_lease(1111,role['id'])
        inventory=Inventory(store.leased(1111,role['id'],epoch),1111,role['id'])
        inventory.grant_item(40200);snapshot=inventory.immutable_snapshot();key=snapshot.items[0].id
        npc=next(p for p in store.npc_resources[0][1007] if p.npc_id==10890 and p.placement_id==75)
        address=MapAddress(1007,1007,0);entity=(1007<<32)|75
        scene=NpcScene(address,(npc,),prepared[3],binding_capacity=1,interaction_rules=store.npc_interaction_rules)
        scene.bind(entity,75)
        location=Location(role['id'],epoch,address,1,npc.x,npc.y)
        binding=RoleViewBinding(address,'known-map-owner',role['id'],epoch,1,1)
        now=int(time.monotonic()*1000)
        def proof(identity,clock):return scene.interact(struct.pack('>q',entity),location,location,
            request_id=identity,now_ms=clock,deadline_ms=clock+5000)
        rules=identification.load_rules(store.npc_identification_query_rules,store.inventory_config)
        body=b'\1'+struct.pack('>iQi',key,entity,1)
        dialogue=identification.query(inventory,body,proof('query',now),location,binding,
            rules=rules,request_id='known-query-dialogue',now_ms=now,deadline_ms=now+5000)
        expected=struct.pack('>Q',entity)+b'\1'+struct.pack('>iii',key,1,1)
        assert dialogue.messages==((0xc04cd,expected),)
        assert dialogue.ticket.expires_ms==now+300000
        # The original one-I/O deadline has passed, but the separately bounded
        # dialogue is valid; a fresh map proof and I/O budget are supplied.
        intent=identification.confirm(dialogue.ticket,struct.pack('>iii',key,0,1),
            proof('confirmation',now+6000),location,binding,now_ms=now+6000,deadline_ms=now+11000)
        assert intent.item_key==key and intent.deadline_ms==now+11000
        repeated=identification.confirm(dialogue.ticket,struct.pack('>iii',key,0,1),
            proof('repeat',now+6001),location,binding,now_ms=now+6001,deadline_ms=now+11001)
        assert repeated.ticket.request_id==intent.ticket.request_id
        rejected=0
        def confirm(body=struct.pack('>iii',key,0,1),*,ticket=dialogue.ticket,position=location,
                    member=binding,clock=now+6000,deadline=now+11000,evidence=None):
            return identification.confirm(ticket,body,evidence or proof('guard',clock),position,member,
                now_ms=clock,deadline_ms=deadline)
        for member in (replace(binding,connection_generation=2),replace(binding,owner_generation='replaced-map'),
                replace(binding,membership_revision=2)):
            refused(lambda:confirm(member=member));rejected+=1
        for position in (replace(location,version=2),replace(location,x=location.x+1),
                replace(location,login_epoch='old-epoch'),replace(location,state='loading'),
                replace(location,address=MapAddress(1007,1007,1))):
            refused(lambda:confirm(position=position));rejected+=1
        for body in (struct.pack('>iii',key+1,0,1),struct.pack('>iii',-1,0,1),
                struct.pack('>iii',key,1,1),struct.pack('>iii',key,0,2),b'',struct.pack('>iii',key,0,1)+b'\0'):
            refused(lambda:confirm(body));rejected+=1
        refused(lambda:confirm(clock=now+300000,deadline=now+305000));rejected+=1
        refused(lambda:confirm(deadline=now+6000));rejected+=1
        refused(lambda:confirm(evidence=replace(proof('foreign-key',now+6000),entity_key=entity+1)));rejected+=1
        refused(lambda:replace(dialogue.ticket,request_id=''));rejected+=1
        try:dialogue.ticket.expires_ms=now+900000
        except FrozenInstanceError:pass
        else:raise AssertionError('NPC dialogue is mutable')
        assert inventory.immutable_snapshot()==snapshot
    write_json(OUT/'evidence/npc-identification-dialogue-verification.json',{
        'passed':['actual read-only query returns original current state plus frozen dialogue',
            'five-minute dialogue lifetime remains separate from fresh per-I/O deadline',
            'current connection/map/member, movement/epoch/address/state and original confirmation guards'],
        'rejected_confirmation_cases':rejected,
        'settlement_verified_by_this_script':False,'shared_route_implemented':False,'deployed':False,
        'live_database_modified':False,'native_gui_verified':False})
    print('PASS original query dialogue and separate confirmation I/O budget')


if __name__=='__main__':main()
