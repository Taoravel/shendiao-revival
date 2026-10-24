"""Original codecs are the oracle; no NPC permission or asset operation."""
import importlib
from dataclasses import FrozenInstanceError
import struct
from unittest.mock import patch
from inspect_client import OUT,write_json
from research_npc_identification import roundtrip


def main():
    try:protocol=importlib.import_module('npc_identification_protocol')
    except ModuleNotFoundError:
        raise AssertionError('NPC identification has no original request/response protocol Interface') from None
    key=0xfedcba9800002a8a
    body=bytes.fromhex('03')+struct.pack('>3iQi',92,91,92,key,1)
    roundtrip(0xe6c980,0xe6cae0,0xe6ca20,body)
    query=protocol.decode_identification_query(body,max_items=128)
    assert (query.item_keys,query.npc_key,query.mode)==((92,91,92),key,1)
    assert protocol.QUERY_IDENTIFICATION==0xc04cc
    assert hasattr(protocol,'encode_identification_states'), 'NPC identification cannot encode the original state response'
    states=((92,1),(91,0),(92,-0x80000000))
    response=protocol.encode_identification_states(key,states,1,max_items=128)
    expected=struct.pack('>Q',key)+b'\3'+struct.pack('>7i',92,1,91,0,92,-0x80000000,1)
    assert response==expected
    roundtrip(0xf04490,0xf04e70,0xf04f10,response)
    assert protocol.IDENTIFICATION_STATES==0xc04cd
    assert hasattr(protocol,'decode_identification_request'), 'NPC identification has no original confirmation decoder'
    for fields in ((91,0,1),(-1,-2,-3)):
        body=struct.pack('>iii',*fields)
        roundtrip(0xdc78e0,0xe55760,0xdc7980,body)
        request=protocol.decode_identification_request(body)
        assert (request.item_key,request.auxiliary_argument,request.mode)==fields
    assert protocol.IDENTIFY_EQUIPMENT==0xc4276
    for count,prefix in ((0,b'\0'),(127,b'\x7f'),(128,b'\x80\x80')):
        keys=tuple(range(1,count+1))
        body=prefix+b''.join(struct.pack('>i',k) for k in keys)+struct.pack('>Qi',key,-2**31)
        roundtrip(0xe6c980,0xe6cae0,0xe6ca20,body)
        query=protocol.decode_identification_query(body,max_items=128)
        assert query.item_keys==keys and query.mode==-2**31
        response=protocol.encode_identification_states(key,tuple((k,1) for k in keys),2**31-1,max_items=128)
        assert response[8:8+len(prefix)]==prefix
        roundtrip(0xf04490,0xf04e70,0xf04f10,response)
    signed=struct.pack('>3iQi',-2**31,0,2**31-1,0,2**31-1)
    body=b'\3'+signed
    roundtrip(0xe6c980,0xe6cae0,0xe6ca20,body)
    assert protocol.decode_identification_query(body,max_items=3).item_keys==(-2**31,0,2**31-1)

    def refused(action):
        try:action()
        except ValueError:return
        raise AssertionError('Malformed or over-budget identification packet accepted')

    for truncated in (b'',b'\x80',body[:-1],body+b'\0'):
        refused(lambda:protocol.decode_identification_query(truncated,max_items=128))
    refused(lambda:protocol.decode_identification_query(body,max_items=2))
    for budget in (None,True,0,-1,1.0):
        refused(lambda:protocol.decode_identification_query(body,max_items=budget))
        refused(lambda:protocol.encode_identification_states(key,(),1,max_items=budget))
    for states in (((0,0),),((-1,0),),((2**31,0),),((True,0),),((1,True),),((1,2**31),),[],((1,0,1),)):
        refused(lambda:protocol.encode_identification_states(key,states,1,max_items=128))
    refused(lambda:protocol.encode_identification_states(key,((1,0),(2,1)),1,max_items=1))
    for bad_key in (-1,2**64,True):
        refused(lambda:protocol.encode_identification_states(bad_key,(),1,max_items=128))
    for bad_mode in (-2**31-1,2**31,True):
        refused(lambda:protocol.encode_identification_states(key,(),bad_mode,max_items=128))
    for bad in (b'',bytes(11),bytes(13),bytearray(12)):
        refused(lambda:protocol.decode_identification_request(bad))
    for command in (query,request):
        try:command.mode=1
        except FrozenInstanceError:pass
        else:raise AssertionError('Identification wire command is mutable')
    with patch('builtins.open',side_effect=AssertionError('Protocol file I/O')), \
         patch('io.open',side_effect=AssertionError('Protocol file I/O')):
        assert protocol.decode_identification_query(body,max_items=3).npc_key==0
        assert protocol.decode_identification_request(struct.pack('>iii',91,0,1)).item_key==91
        assert protocol.encode_identification_states(key,((91,0),),1,max_items=1)
    result={'passed':['original query preserves vector order, duplicates and all NPC key bits',
        'original response vector and positive-key contract match native decode and marshal',
        'confirmation keeps three signed integers without inventing NPC key or column',
        'empty/127/128 vectors use original compact counts; signed query fields are preserved',
        'exact sizes, caller budgets and original response key bounds reject invalid packets',
        'frozen commands and no file I/O; wire data grants no NPC or asset authority'],
        'runtime_integrated':False,'native_gui_verified':False,'live_database_modified':False}
    write_json(OUT/'evidence/npc-identification-protocol-verification.json',result)
    print(result)


if __name__=='__main__':main()
