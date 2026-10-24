"""Original x86 role-growth request codecs, including asymmetric point order."""
import struct
from inspect_client import OUT,write_json
from native_gameplay_probe import probe
from role_growth_protocol import (C_REQ_LEVEL_UP,C_ADD_POINT_TO_ATTR,
                                   decode_level_request,decode_allocation_request)


def main():
    level,raw=probe(0xd57d30,0xe411a0,0xd57dd0,{8:bytes(4)})
    assert level==bytes(4) and decode_level_request(level)==0
    assert struct.unpack_from('<I',raw,4)[0]==C_REQ_LEVEL_UP
    wire_values=(1,2,3,4,5)
    fields={8+i*4:struct.pack('<i',value) for i,value in enumerate(wire_values)}
    body,raw=probe(0xd4e0e0,0xe3f940,0xd4e1b0,fields)
    assert body==struct.pack('>5i',*wire_values)
    assert struct.unpack_from('<I',raw,4)[0]==C_ADD_POINT_TO_ATTR
    assert decode_allocation_request(body)==(1,2,3,5,4)
    assert decode_allocation_request(bytes(20))==(0,0,0,0,0)
    for invalid in (bytes(19),bytes(21),struct.pack('>5i',0,0,0,0,-1)):
        try:decode_allocation_request(invalid)
        except ValueError:pass
        else:raise AssertionError('Invalid role allocation request accepted')
    result={'passed':['CReqLevelUp type and single BE32 match original constructor/marshal/decoder',
        'CAddPointToAttr type and five signed BE32 match original constructor/marshal/decoder',
        'asymmetric native V/I/S/AGI/END maps to internal V/I/S/END/AGI',
        'zero codec accepted for domain no-op refusal; negative/truncated/trailing data rejected'],
        'role_level_request':hex(C_REQ_LEVEL_UP),'role_allocation_request':hex(C_ADD_POINT_TO_ATTR),
        'allocation_body_bytes':20,'battle_executed':False,'live_client_tested':False}
    write_json(OUT/'evidence/role-growth-request-verification.json',result)
    print(result)


if __name__=='__main__':main()
