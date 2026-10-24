"""Native ordinary socket requests and proven source-column mapping."""
from equipment_gems import decode
from native_gameplay_probe import probe
import struct


def refused(fn):
    try:fn()
    except ValueError:return
    raise AssertionError('Invalid gem request accepted')


def main():
    for source,column in ((0,1),(1,4)):
        body=struct.pack('>iBi',701,source,901)
        probe(0xd8d0d0,0xe4b710,0xd8d100,payload=body)
        added=decode(0xc0425,body)
        assert (added.operation,added.equipment_key,added.source_column,added.gem_key,added.selection)==('embed',701,column,901,None)
        for selection in (35001,-1):
            body=struct.pack('>iiB',selection,701,source)
            probe(0xd94dc0,0xe4ce00,0xd94df0,payload=body)
            removed=decode(0xc04ea,body)
            assert (removed.operation,removed.equipment_key,removed.source_column,removed.gem_key,removed.selection)==('remove',701,column,None,selection)
    for kind,body in ((0xc0533,bytes(12)),(0xc0424,bytes(8)),(0xc0425,bytes(9)),
            (0xc0425,struct.pack('>iBi',701,2,901)),(0xc04ea,struct.pack('>iiB',0,701,0)),
            (0xc04ea,struct.pack('>iiB',-2,701,0)),(0xc04ea,struct.pack('>iiB',35001,-1,0))):
        refused(lambda:decode(kind,body))
    for body in (bytes(8),bytes(10),bytearray(9)):refused(lambda:decode(0xc0425,body))
    print('PASS6 actual original socket codecs, source0=carried1/source1=worn4, strict selected/all fields')


if __name__=='__main__':main()
